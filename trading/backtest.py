"""Backtest sederhana: saham US (Senin-Jumat) dan kripto (Sabtu-Minggu).

Jalankan:  python trading/backtest.py
Hasil:     trading/report.html

Semua strategi memakai parameter tetap (tidak dioptimasi) supaya hasilnya
tidak overfit. Periode "uji" = 30% data terakhir, dilaporkan terpisah.
"""
from __future__ import annotations

import datetime as dt
import html
import sys
from pathlib import Path

import numpy as np
import pandas as pd

STOCKS = ["SPY", "QQQ", "NVDA", "AAPL", "MSFT", "TSLA"]
CRYPTO = ["BTC-USD", "ETH-USD", "SOL-USD"]
FEE = {"stock": 0.0005, "crypto": 0.001}  # biaya + slippage per transaksi (satu sisi)
TARGET_CAGR = (0.30, 0.50)  # target "sangat bagus": 30-50% per tahun
MAX_DD_OK = -0.25
TEST_FRAC = 0.30
OUT = Path(__file__).with_name("report.html")


# ---------- data ----------

def download(ticker: str, interval: str) -> pd.DataFrame:
    import yfinance as yf

    period = "10y" if interval == "1d" else "730d"
    df = yf.download(ticker, period=period, interval=interval, auto_adjust=True, progress=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df = df[["Open", "High", "Low", "Close"]].dropna()
    df.index = pd.to_datetime(df.index, utc=True)
    return df


# ---------- strategi (posisi 1 = beli, 0 = kas) ----------

def rsi(close: pd.Series, n: int) -> pd.Series:
    d = close.diff()
    up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    return 100 - 100 / (1 + up / dn.replace(0, np.nan))


def buy_hold(df):
    return pd.Series(1.0, index=df.index)


def trend(df):
    c = df.Close
    s20, s50 = c.rolling(20).mean(), c.rolling(50).mean()
    return ((c > s50) & (s20 > s50)).astype(float)


def mean_reversion(df):
    c = df.Close
    entry = (rsi(c, 2) < 10) & (c > c.rolling(200).mean())
    exit_ = c > c.rolling(5).mean()
    pos, holding = [], False
    for e, x in zip(entry, exit_):
        if holding and x:
            holding = False
        elif not holding and e:
            holding = True
        pos.append(float(holding))
    return pd.Series(pos, index=df.index)


DAILY = {"Beli & tahan": buy_hold, "Trend (SMA20/50)": trend, "Mean reversion (RSI2)": mean_reversion}


def daily_returns(df, pos, kind):
    """Sinyal dari penutupan hari t dipakai untuk hari t+1."""
    pos = pos.shift(1).fillna(0)
    if kind == "crypto":  # kripto hanya Sabtu-Minggu
        pos = pos.where(pos.index.dayofweek >= 5, 0.0)
    ret = df.Close.pct_change().fillna(0)
    cost = pos.diff().abs().fillna(pos.iloc[0]) * FEE[kind]
    return pos * ret - cost


def intraday_momentum(df_h, kind):
    """Day trade: jika candle 1 jam pertama naik, beli di penutupannya,
    jual di penutupan hari itu. Satu nilai return per hari."""
    if kind == "stock":
        df_h = df_h.tz_convert("America/New_York")
    day = df_h.index.normalize()
    out = {}
    for d, g in df_h.groupby(day):
        if len(g) < 3:
            continue
        if kind == "crypto" and d.dayofweek < 5:
            continue
        first = g.iloc[0]
        r = 0.0
        if first.Close > first.Open:
            r = g.Close.iloc[-1] / first.Close - 1 - 2 * FEE[kind]
        out[d.tz_localize(None)] = r
    return pd.Series(out, dtype=float)


# ---------- metrik ----------

def metrics(r: pd.Series, per_year: float) -> dict:
    r = r.dropna()
    if len(r) < 20:
        return {}
    eq = (1 + r).cumprod()
    years = len(r) / per_year
    cagr = eq.iloc[-1] ** (1 / years) - 1 if eq.iloc[-1] > 0 else -1.0
    dd = (eq / eq.cummax() - 1).min()
    active = r[r != 0]
    win = (active > 0).mean() if len(active) else np.nan
    sharpe = r.mean() / r.std() * np.sqrt(per_year) if r.std() > 0 else np.nan
    return {"cagr": cagr, "monthly": (1 + cagr) ** (1 / 12) - 1, "dd": dd,
            "win": win, "sharpe": sharpe, "trades": int((r != 0).sum())}


def verdict(m: dict, bh: dict | None) -> str:
    if not m:
        return "data kurang"
    ok_target = m["cagr"] >= TARGET_CAGR[0] and m["dd"] >= MAX_DD_OK
    beats = bh is None or (m["sharpe"] or 0) > (bh.get("sharpe") or 0)
    if ok_target and beats:
        return "LOLOS"
    if beats and m["cagr"] > 0:
        return "lumayan"
    return "tidak layak"


# ---------- laporan ----------

def pct(x):
    return "–" if x is None or (isinstance(x, float) and np.isnan(x)) else f"{x * 100:.1f}%"


def render(rows: list[dict], errors: list[str]) -> str:
    def tr(r):
        cls = {"LOLOS": "ok", "lumayan": "mid"}.get(r["verdict"], "bad")
        cells = [r["asset"], r["strategy"], r["period"]]
        m = r["m"]
        cells += [pct(m.get("cagr")), pct(m.get("monthly")), pct(m.get("dd")), pct(m.get("win")),
                  "–" if not m else f"{m['sharpe']:.2f}", str(m.get("trades", "–"))]
        return "<tr>" + "".join(f"<td>{html.escape(c)}</td>" for c in cells) + \
               f'<td class="{cls}">{r["verdict"]}</td></tr>'

    now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    err = "".join(f"<li>{html.escape(e)}</li>" for e in errors)
    return f"""<!doctype html><html lang="id"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>Hasil Backtest</title>
<style>
:root{{--bg:#f6f7f9;--card:#fff;--fg:#1b1f24;--muted:#5b6470;--line:#d9dde3;--ok:#2e7d32;--mid:#a66b00;--bad:#c62828}}
@media (prefers-color-scheme:dark){{:root{{--bg:#14171b;--card:#1d2127;--fg:#e8eaed;--muted:#9aa3ad;--line:#323840;--ok:#6fcf73;--mid:#f0b429;--bad:#ff6b6b}}}}
body{{margin:0;background:var(--bg);color:var(--fg);font:15px/1.5 system-ui,sans-serif}}
main{{max-width:1000px;margin:0 auto;padding:24px 16px}}
.note{{color:var(--muted);font-size:.875rem}}
.wrap{{overflow-x:auto;background:var(--card);border:1px solid var(--line);border-radius:10px}}
table{{border-collapse:collapse;width:100%;font-size:.85rem;white-space:nowrap}}
th,td{{padding:6px 10px;border-bottom:1px solid var(--line);text-align:right}}
th:nth-child(-n+3),td:nth-child(-n+3){{text-align:left}}
.ok{{color:var(--ok);font-weight:700}}.mid{{color:var(--mid);font-weight:600}}.bad{{color:var(--bad)}}
</style></head><body><main>
<h1>Hasil Backtest</h1>
<p class="note">Dibuat {now}. Saham US hanya Senin–Jumat, kripto hanya Sabtu–Minggu. Biaya: saham {FEE['stock']*100:.2f}%, kripto {FEE['crypto']*100:.2f}% per transaksi.<br>
<b>LOLOS</b> = untung ≥ {TARGET_CAGR[0]*100:.0f}%/tahun, rugi terdalam tidak lebih dari {abs(MAX_DD_OK)*100:.0f}%, dan Sharpe lebih baik dari beli &amp; tahan.
Yang penting adalah baris <b>uji</b> (30% data terakhir); baris <b>penuh</b> bisa terlihat lebih bagus dari kenyataan.</p>
<div class="wrap"><table><thead><tr><th>Aset</th><th>Strategi</th><th>Periode</th><th>Untung/thn</th><th>≈/bulan</th>
<th>Rugi terdalam</th><th>Win rate</th><th>Sharpe</th><th>Hari aktif</th><th>Hasil</th></tr></thead>
<tbody>{''.join(tr(r) for r in rows)}</tbody></table></div>
{f'<p class="note">Gagal diunduh:</p><ul class="note">{err}</ul>' if err else ''}
<p class="note">Hasil masa lalu tidak menjamin hasil masa depan. Ini bukan saran investasi.</p>
</main></body></html>"""


def evaluate(asset, strategy, r, per_year, bh_by_period):
    rows = []
    split = int(len(r) * (1 - TEST_FRAC))
    for period, part in (("penuh", r), ("uji", r.iloc[split:])):
        m = metrics(part, per_year)
        bh = bh_by_period.get(period) if strategy != "Beli & tahan" else None
        rows.append({"asset": asset, "strategy": strategy, "period": period, "m": m,
                     "verdict": "pembanding" if strategy == "Beli & tahan" else verdict(m, bh)})
    return rows


def main():
    rows, errors = [], []
    for kind, tickers in (("stock", STOCKS), ("crypto", CRYPTO)):
        per_year = 252 if kind == "stock" else 104  # kripto: hanya ±104 hari akhir pekan
        for t in tickers:
            try:
                d = download(t, "1d")
            except Exception as e:  # noqa: BLE001
                errors.append(f"{t} harian: {e}")
                continue
            bh = {}
            for name, fn in DAILY.items():
                r = daily_returns(d, fn(d), kind)
                if kind == "crypto":
                    r = r[r.index.dayofweek >= 5]
                res = evaluate(t, name, r, per_year, bh)
                if name == "Beli & tahan":
                    bh = {x["period"]: x["m"] for x in res}
                rows += res
            try:
                h = download(t, "1h")
                r = intraday_momentum(h, kind)
                rows += evaluate(t, "Day trade (momentum 1 jam)", r, per_year, bh)
            except Exception as e:  # noqa: BLE001
                errors.append(f"{t} per jam: {e}")
    OUT.write_text(render(rows, errors), encoding="utf-8")
    print(f"Laporan: {OUT} ({len(rows)} baris, {len(errors)} gagal)")
    return 0 if rows else 1


if __name__ == "__main__":
    sys.exit(main())
