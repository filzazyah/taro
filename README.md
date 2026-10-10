# Cek Kebocoran

Halaman web statis (satu file `index.html`) untuk:

1. **Cek email**: daftar kebocoran data yang memuat email tersebut, via [XposedOrNot](https://xposedornot.com) (gratis, tanpa API key).
2. **Cek password**: apakah password pernah bocor, via [Pwned Passwords](https://haveibeenpwned.com/Passwords) dengan k-anonymity, jadi password tidak pernah dikirim.

## Cara pakai

Buka `index.html` langsung di browser, atau jalankan server lokal:

```
python3 -m http.server 8000
```

lalu buka http://localhost:8000.

Bisa juga di-hosting gratis lewat GitHub Pages (Settings → Pages → branch ini, folder root).

## Catatan

- Hasil "tidak ditemukan" bukan jaminan aman.
- Cek email milikmu sendiri saja.

# Backtest Trading (`trading/`)

Menguji beberapa strategi sederhana pada data historis:

- **Saham US** (SPY, QQQ, NVDA, AAPL, MSFT, TSLA): hanya Senin–Jumat.
- **Kripto** (BTC, ETH, SOL): hanya Sabtu–Minggu.
- Strategi: beli & tahan (pembanding), trend SMA20/50, mean reversion RSI(2), day trade momentum 1 jam pertama.
- Target "sangat bagus": untung 30–50%/tahun dengan rugi terdalam tidak lebih dari 25%.

Laporan dibuat otomatis oleh GitHub Actions (tab **Actions → Backtest → Run workflow**, juga tiap Minggu)
dan disimpan di `trading/report.html`, bisa dibuka di `https://filzazyah.github.io/taro/trading/report.html`.

Jalankan lokal:

```
pip install -r trading/requirements.txt
python trading/backtest.py
```

Hasil masa lalu tidak menjamin hasil masa depan. Ini bukan saran investasi.
