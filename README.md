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
