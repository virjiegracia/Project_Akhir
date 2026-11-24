"""TuneMatch - aplikasi rekomendasi lagu (Streamlit)."""
import os
from collections import Counter

import pandas as pd
import plotly.express as px
import streamlit as st

from tunematch.pages.algorithms import Stack, Queue, merge_sort, binary_search_prefix
from tunematch.pages.api_clients import LastFM, Deezer, GeminiAI, APIError
from tunematch.pages.exporter import to_excel_bytes, to_pdf_bytes
from tunematch.pages.recommender import build_recommendations, song_key

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

st.set_page_config(page_title="TuneMatch", page_icon="🎵", layout="wide")
PAGES = ["Beranda", "Rekomendasi", "Playlist & Dashboard", "Tentang"]


def secret(name, default=""):
    try:
        return st.secrets[name]
    except Exception:
        return os.getenv(name, default)


def init_state():
    defaults = dict(favorites=[], search_results=[], recs=[], mood_tags=[], summary="",
                    playlist=[], cache={}, undo=Stack(), queue=Queue(), now_playing=None,
                    mood="", page="Beranda", report={})
    for k, v in defaults.items():
        st.session_state.setdefault(k, v)


init_state()
S = st.session_state
lfm = LastFM(secret("LASTFM_API_KEY"), S.cache)
deezer = Deezer(S.cache)
ai = GeminiAI(secret("GEMINI_API_KEY"), secret("GEMINI_MODEL", "gemini-2.5-flash"))

if "goto" in S:  # pindah halaman secara terprogram
    S.page = S.pop("goto")
page = st.sidebar.radio("Menu", PAGES, key="page")
st.sidebar.title("🎵 TuneMatch")
if not lfm.api_key:
    st.sidebar.error("LASTFM_API_KEY belum diisi.")
if not ai.enabled:
    st.sidebar.warning("GEMINI_API_KEY belum diisi: fitur AI memakai mode sederhana.")


def add_favorite(song):
    if song_key(song["artist"], song["title"]) in {song_key(f["artist"], f["title"]) for f in S.favorites}:
        return False
    S.favorites.append({"title": song["title"], "artist": song["artist"]})
    return True


def add_to_playlist(rec):
    if rec["key"] in {p["key"] for p in S.playlist}:
        st.toast("Lagu sudah ada di playlist.")
    else:
        S.playlist.append(rec)
        st.toast(f"Ditambahkan: {rec['title']}")


# ---------------------------------------------------------------- Beranda
def page_home():
    st.title("Temukan Lagu yang Pas untuk Suasanamu")
    st.caption("Ceritakan mood atau aktivitasmu, pilih lagu favorit, dapatkan rekomendasi.")

    st.subheader("1. Ceritakan suasana hatimu")
    st.text_area("Mood / aktivitas", key="mood", label_visibility="collapsed",
                 placeholder="contoh: ingin lagu santai untuk belajar malam hari")

    st.subheader("2. Lagu / artis favorit")
    c1, c2 = st.columns([5, 1], vertical_alignment="bottom")
    q = c1.text_input("Cari lagu atau artis (Last.fm)", key="q")
    if c2.button("Cari") and q.strip():
        try:
            S.search_results = lfm.search_tracks(q.strip())
            if not S.search_results:
                st.info("Tidak ada hasil.")
        except APIError as e:
            st.error(str(e))
    if S.search_results:
        opts = S.search_results
        idx = st.selectbox("Hasil pencarian", range(len(opts)),
                           format_func=lambda i: f"{opts[i]['title']} - {opts[i]['artist']}")
        if st.button("➕ Tambah ke favorit"):
            st.success("Ditambahkan.") if add_favorite(opts[idx]) else st.info("Sudah ada di daftar.")

    up = st.file_uploader("Atau unggah CSV (kolom: judul, artis)", type="csv")
    if up is not None and st.button("Impor CSV"):
        try:
            df = pd.read_csv(up)
            df.columns = [c.strip().lower() for c in df.columns]
            df = df.rename(columns={"title": "judul", "lagu": "judul", "artist": "artis"})
            if not {"judul", "artis"} <= set(df.columns):
                st.error("CSV harus memiliki kolom 'judul' dan 'artis'.")
            else:
                df = df.dropna(subset=["judul", "artis"])
                n = sum(add_favorite({"title": str(r.judul).strip(), "artist": str(r.artis).strip()})
                        for r in df.itertuples())
                st.success(f"{n} lagu diimpor.")
        except Exception as e:
            st.error(f"Gagal membaca CSV: {e}")

    if S.favorites:
        st.dataframe(pd.DataFrame(S.favorites).rename(columns={"title": "Judul", "artist": "Artis"}),
                     hide_index=True, use_container_width=True)
        if st.button("Kosongkan favorit"):
            S.favorites = []
            st.rerun()

    st.subheader("3. Jumlah rekomendasi")
    n = st.slider("Jumlah", 5, 20, 10, label_visibility="collapsed")

    if st.button("Cari Rekomendasi", type="primary"):
        mood = S.mood.strip()
        if not S.favorites and not mood:
            st.warning("Isi deskripsi mood atau tambahkan minimal satu lagu favorit.")
            return
        try:
            with st.spinner("Mencari rekomendasi..."):
                S.mood_tags = ai.mood_to_tags(mood) if mood else []
                S.recs = build_recommendations(lfm, S.favorites, S.mood_tags, n)
                if not S.recs:
                    st.warning("Tidak ada kandidat ditemukan. Coba tambah lagu favorit atau ubah deskripsi.")
                    return
                S.summary, expl = ai.explain(mood, S.favorites, S.recs)
                for r, e in zip(S.recs, expl):
                    r["explanation"] = e
                S.report = {}
        except APIError as e:
            st.error(str(e))
            return
        S.goto = "Rekomendasi"
        st.rerun()


# ------------------------------------------------------------- Rekomendasi
def page_recs():
    st.title("Hasil Rekomendasi")
    if not S.recs:
        st.info("Belum ada rekomendasi. Mulai dari halaman Beranda.")
        return
    if S.summary:
        st.info(S.summary)
    if S.mood_tags:
        st.caption("Tag dari mood: " + ", ".join(S.mood_tags))
    if ai.last_error:
        st.caption("Catatan AI: sebagian fitur AI gagal dan memakai mode sederhana.")

    genres = ["Semua"] + sorted({r["genre"] for r in S.recs})
    c1, c2, c3 = st.columns(3)
    genre = c1.selectbox("Genre", genres)
    sort_by = c2.selectbox("Urutkan", ["Kemiripan", "Popularitas", "Judul (A-Z)"])
    search = c3.text_input("Cari judul (awalan)").strip().lower()

    items = [r for r in S.recs if genre == "Semua" or r["genre"] == genre]
    if sort_by == "Kemiripan":
        items = merge_sort(items, key=lambda r: r["score"], reverse=True)
    elif sort_by == "Popularitas":
        items = merge_sort(items, key=lambda r: r["playcount"], reverse=True)
    else:
        items = merge_sort(items, key=lambda r: r["title"].lower())
    if search:  # binary search pada list yang terurut menurut judul
        by_title = merge_sort(items, key=lambda r: r["title"].lower())
        items = binary_search_prefix(by_title, search, key=lambda r: r["title"].lower())

    if not items:
        st.warning("Tidak ada lagu yang cocok dengan filter.")
    for i, r in enumerate(items, 1):
        info = deezer.lookup(r["artist"], r["title"])
        with st.container(border=True):
            a, b, c = st.columns([1, 5, 1.4])
            if info.get("cover"):
                a.image(info["cover"])
            b.markdown(f"**{i}. {r['title']}** - {r['artist']}")
            b.caption(f"Tag: {', '.join(r['tags'][:4]) or '-'}  |  Kemiripan: {r['score']*100:.0f}%  |  "
                      f"Pendengar: {r['playcount']:,}")
            b.write(r["explanation"])
            if info.get("preview"):
                b.audio(info["preview"])
            if c.button("➕ Playlist", key=f"add_{r['key']}"):
                add_to_playlist(r)


# ------------------------------------------------------ Playlist & Dashboard
def page_dash():
    st.title("Playlist & Dashboard")
    left, right = st.columns([1, 1.2])

    with left:
        st.subheader("Playlist Saya")
        if not S.playlist:
            st.caption("Playlist kosong.")
        for i, s in enumerate(S.playlist):
            a, b, c = st.columns([6, 1, 1])
            a.write(f"{i+1}. {s['title']} - {s['artist']}")
            if b.button("🗑", key=f"del_{s['key']}", help="Hapus"):
                S.undo.push((i, S.playlist.pop(i)))  # stack
                st.rerun()
            if c.button("⏭", key=f"q_{s['key']}", help="Masukkan antrean"):
                S.queue.enqueue(s)  # queue
                st.toast("Masuk antrean.")
        if st.button(f"↩ Undo hapus ({len(S.undo)})", disabled=len(S.undo) == 0):
            pos, song = S.undo.pop()
            S.playlist.insert(min(pos, len(S.playlist)), song)
            st.rerun()

        st.subheader("Antrean Putar")
        if S.now_playing:
            st.success(f"Sedang diputar: {S.now_playing['title']} - {S.now_playing['artist']}")
        for i, s in enumerate(S.queue.items(), 1):
            st.write(f"{i}. {s['title']} - {s['artist']}")
        if st.button("▶ Putar berikutnya", disabled=len(S.queue) == 0):
            S.now_playing = S.queue.dequeue()
            st.rerun()

    with right:
        st.subheader("Dashboard")
        if not S.recs:
            st.info("Dashboard tampil setelah ada rekomendasi.")
            return
        df = pd.DataFrame([{"label": f"{r['title']} - {r['artist']}", "skor": r["score"] * 100,
                            "genre": r["genre"], "pendengar": r["playcount"]} for r in S.recs])
        top = df.sort_values("skor").tail(10)
        st.plotly_chart(px.bar(top, x="skor", y="label", orientation="h",
                               title="Skor kemiripan Top-10 (%)"), use_container_width=True)
        cnt = Counter(df["genre"])
        st.plotly_chart(px.pie(names=list(cnt.keys()), values=list(cnt.values()), hole=0.5,
                               title="Distribusi genre"), use_container_width=True)
        st.plotly_chart(px.scatter(df, x="pendengar", y="skor", hover_name="label", log_x=True,
                                   title="Popularitas vs kemiripan"), use_container_width=True)

        st.subheader("Ekspor laporan")
        if st.button("Siapkan laporan"):
            with st.spinner("Membuat laporan..."):
                S.report = {"pdf": to_pdf_bytes(S.recs, S.mood, S.favorites, S.summary),
                            "xlsx": to_excel_bytes(S.recs, S.mood, S.favorites, S.summary)}
        if S.report:
            d1, d2 = st.columns(2)
            d1.download_button("⬇ Unduh PDF", S.report["pdf"], "laporan_tunematch.pdf", "application/pdf")
            d2.download_button("⬇ Unduh Excel", S.report["xlsx"], "laporan_tunematch.xlsx",
                               "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


def page_about():
    st.title("Tentang TuneMatch")
    st.write("Proyek Besar Praktikum Algoritma dan Struktur Data. Data lagu dari Last.fm, "
             "cover dan pratinjau dari Deezer, penjelasan oleh Google Gemini.")
    st.markdown("- **Dictionary**: cache API dan penggabungan kandidat\n- **Set**: membuang duplikat dan tag\n"
                "- **List**: favorit, hasil, playlist\n- **Stack**: Undo playlist\n- **Queue**: antrean putar\n"
                "- **Merge sort**: pengurutan hasil\n- **Binary search**: pencarian judul\n"
                "- **Skor**: 0,5 x match + 0,3 x Jaccard tag + 0,2 x popularitas")


{"Beranda": page_home, "Rekomendasi": page_recs,
 "Playlist & Dashboard": page_dash, "Tentang": page_about}[page]()
