# TuneMatch - Rekomendasi Lagu

Aplikasi web Streamlit: rekomendasi lagu dari lagu favorit + mood, dengan penjelasan AI.

## Menjalankan
1. `pip install -r requirements.txt`
2. Salin `.streamlit/secrets.toml.example` menjadi `.streamlit/secrets.toml`, isi API key:
   - Last.fm: https://www.last.fm/api/account/create
   - Gemini: https://aistudio.google.com/apikey
3. `streamlit run app.py`
4. Uji logika inti: `python test_core.py`

## Struktur
- `app.py` antarmuka (Beranda, Rekomendasi, Playlist & Dashboard)
- `algorithms.py` stack, queue, merge sort, binary search, skor
- `recommender.py` alur kandidat -> skor -> Top-N
- `api_clients.py` Last.fm, Deezer, Gemini
- `exporter.py` laporan PDF dan Excel

## Deploy (untuk APK)
Deploy ke Streamlit Community Cloud, isi API key di menu Secrets, lalu bungkus URL-nya
dengan WebView/PWABuilder.

Catatan: data playlist disimpan di sesi browser (tanpa database) dan hilang saat halaman dimuat ulang.
