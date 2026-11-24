"""Ekspor laporan ke Excel (.xlsx) dan PDF."""
import io
from collections import Counter
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from fpdf import FPDF


def recs_dataframe(recs):
    return pd.DataFrame([{
        "Peringkat": i, "Judul": r["title"], "Artis": r["artist"],
        "Genre/Tag": ", ".join(r["tags"][:4]), "Kemiripan (%)": round(r["score"] * 100, 1),
        "Pendengar": r["playcount"], "Penjelasan AI": r["explanation"]}
        for i, r in enumerate(recs, 1)])


def to_excel_bytes(recs, mood, favorites, summary):
    buf = io.BytesIO()
    info = pd.DataFrame({"Keterangan": ["Mood/aktivitas", "Lagu favorit", "Ringkasan selera (AI)"],
                         "Isi": [mood or "-", "; ".join(f"{f['title']} - {f['artist']}" for f in favorites) or "-",
                                 summary or "-"]})
    with pd.ExcelWriter(buf, engine="openpyxl") as xw:
        info.to_excel(xw, sheet_name="Ringkasan", index=False)
        recs_dataframe(recs).to_excel(xw, sheet_name="Rekomendasi", index=False)
        for ws in xw.book.worksheets:
            for col in ws.columns:
                width = max(len(str(c.value or "")) for c in col)
                ws.column_dimensions[col[0].column_letter].width = min(width + 2, 60)
    return buf.getvalue()


def _charts(recs):
    top = recs[:10]
    fig, ax = plt.subplots(figsize=(7, 3.5))
    ax.barh([f"{r['title'][:28]}" for r in top][::-1], [r["score"] * 100 for r in top][::-1], color="#4a6fa5")
    ax.set_xlabel("Kemiripan (%)"); ax.set_title("Top rekomendasi")
    fig.tight_layout(); b1 = io.BytesIO(); fig.savefig(b1, format="png", dpi=130); plt.close(fig)
    cnt = Counter(r["genre"] for r in recs)
    fig, ax = plt.subplots(figsize=(5, 3.5))
    ax.pie(cnt.values(), labels=cnt.keys(), wedgeprops={"width": 0.45}, autopct="%1.0f%%")
    ax.set_title("Distribusi genre")
    fig.tight_layout(); b2 = io.BytesIO(); fig.savefig(b2, format="png", dpi=130); plt.close(fig)
    b1.seek(0); b2.seek(0)
    return b1, b2


def _s(text):  # font bawaan PDF hanya mendukung latin-1
    return str(text).encode("latin-1", "replace").decode("latin-1")


def to_pdf_bytes(recs, mood, favorites, summary):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(0, 10, "Laporan Rekomendasi TuneMatch", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 11)
    for line in [f"Mood/aktivitas: {mood or '-'}",
                 "Lagu favorit: " + ("; ".join(f"{f['title']} - {f['artist']}" for f in favorites) or "-"),
                 f"Ringkasan selera: {summary or '-'}"]:
        pdf.multi_cell(0, 6, _s(line), new_x="LMARGIN", new_y="NEXT")
    if recs:
        b1, b2 = _charts(recs)
        pdf.ln(2); pdf.image(b1, w=150); pdf.image(b2, w=110)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 8, "Daftar Rekomendasi", new_x="LMARGIN", new_y="NEXT")
    for i, r in enumerate(recs, 1):
        pdf.set_font("Helvetica", "B", 11)
        pdf.multi_cell(0, 6, _s(f"{i}. {r['title']} - {r['artist']} ({r['score']*100:.0f}%)"), new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 10)
        pdf.multi_cell(0, 5, _s(f"Tag: {', '.join(r['tags'][:4])}"), new_x="LMARGIN", new_y="NEXT")
        pdf.multi_cell(0, 5, _s(r["explanation"]), new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)
    return bytes(pdf.output())
