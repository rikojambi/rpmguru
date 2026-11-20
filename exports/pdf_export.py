"""Ekspor RPM dan LKPD ke PDF menggunakan ReportLab."""

from __future__ import annotations

import io
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from exports import konten


GREEN = colors.HexColor("#12503C")
LIGHT_GREEN = colors.HexColor("#E6F2EC")
INK = colors.HexColor("#1C2722")
MUTED = colors.HexColor("#6B7770")
LINE = colors.HexColor("#CFD9D2")


def _bersih(value: str) -> str:
    return (
        str(value or "")
        .replace("…", "...")
        .replace("·", "|")
        .replace("–", "-")
        .replace("—", "-")
        .replace("“", '"')
        .replace("”", '"')
        .replace("’", "'")
        .replace("•", "-")
    )


def _p(value: str, style) -> Paragraph:
    teks = escape(_bersih(value)).replace("\n", "<br/>")
    return Paragraph(teks or " ", style)


def _styles():
    base = getSampleStyleSheet()
    styles = {
        "title": ParagraphStyle(
            "RpmTitle", parent=base["Title"], fontName="Helvetica-Bold",
            fontSize=14.5, leading=18, textColor=GREEN, spaceAfter=4,
        ),
        "school": ParagraphStyle(
            "School", parent=base["Normal"], fontName="Helvetica-Bold",
            fontSize=13, leading=16, alignment=TA_CENTER, textColor=GREEN,
        ),
        "kop": ParagraphStyle(
            "Kop", parent=base["Normal"], fontSize=8.5, leading=11,
            alignment=TA_CENTER, textColor=MUTED,
        ),
        "h1": ParagraphStyle(
            "H1Rpm", parent=base["Heading1"], fontName="Helvetica-Bold",
            fontSize=12, leading=15, textColor=GREEN, spaceBefore=10, spaceAfter=4,
            keepWithNext=True,
        ),
        "h2": ParagraphStyle(
            "H2Rpm", parent=base["Heading2"], fontName="Helvetica-Bold",
            fontSize=10.5, leading=13, textColor=GREEN, spaceBefore=7, spaceAfter=3,
            keepWithNext=True,
        ),
        "body": ParagraphStyle(
            "BodyRpm", parent=base["BodyText"], fontName="Helvetica",
            fontSize=9.2, leading=12.6, textColor=INK, spaceAfter=4,
        ),
        "cell": ParagraphStyle(
            "CellRpm", parent=base["BodyText"], fontName="Helvetica",
            fontSize=8.1, leading=10.4, textColor=INK,
        ),
        "cellhead": ParagraphStyle(
            "CellHeadRpm", parent=base["BodyText"], fontName="Helvetica-Bold",
            fontSize=8.1, leading=10.4, textColor=colors.white,
        ),
        "small": ParagraphStyle(
            "SmallRpm", parent=base["Normal"], fontName="Helvetica",
            fontSize=7.4, leading=9.5, textColor=MUTED,
        ),
    }
    return styles


def _footer(canvas, doc) -> None:
    canvas.saveState()
    width, _ = A4
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(MUTED)
    canvas.drawCentredString(width / 2, 1.05 * cm, f"Halaman {doc.page}")
    canvas.setStrokeColor(LINE)
    canvas.setLineWidth(0.4)
    canvas.line(2.2 * cm, 1.4 * cm, width - 2.0 * cm, 1.4 * cm)
    canvas.restoreState()


def _column_widths(headers: list[str], available: float) -> list[float]:
    jumlah = len(headers)
    if jumlah <= 1:
        return [available]
    if jumlah == 2:
        fractions = [0.27, 0.73]
    elif jumlah == 3:
        fractions = [0.22, 0.30, 0.48]
    elif jumlah == 4:
        fractions = [0.08, 0.36, 0.38, 0.18]
    elif jumlah == 5:
        fractions = [0.06, 0.26, 0.26, 0.26, 0.16]
    else:
        fractions = [1 / jumlah] * jumlah
    total = sum(fractions)
    return [available * f / total for f in fractions]


def _table_block(block: dict, styles, available: float) -> Table | None:
    headers = block.get("headers") or []
    rows = block.get("rows") or []
    if not headers or not rows:
        return None
    data = [[_p(str(h), styles["cellhead"]) for h in headers]]
    for row in rows:
        values = [str(value) for value in list(row)[: len(headers)]]
        if len(values) < len(headers):
            values.extend([""] * (len(headers) - len(values)))
        data.append([_p(value, styles["cell"]) for value in values])
    table = Table(
        data,
        colWidths=_column_widths(headers, available),
        repeatRows=1,
        splitByRow=1,
        hAlign="LEFT",
    )
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), GREEN),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.4, LINE),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F7F9F7")]),
            ]
        )
    )
    return table


def _signature_table(profil: dict, styles, available: float) -> Table:
    kota = profil.get("kabupaten") or profil.get("provinsi") or ".............."
    kiri = [
        Paragraph("Mengetahui,", styles["body"]),
        Paragraph("Kepala Sekolah", styles["body"]),
        Spacer(1, 46),
        Paragraph(escape(_bersih(profil.get("nama_kepala_sekolah") or "..............................")), styles["body"]),
        Paragraph("NIP. ........................", styles["body"]),
    ]
    kanan = [
        Paragraph(f"{escape(_bersih(kota))}, ........................ 20....", styles["body"]),
        Paragraph("Guru Mata Pelajaran", styles["body"]),
        Spacer(1, 46),
        Paragraph(escape(_bersih(profil.get("nama_guru") or "..............................")), styles["body"]),
        Paragraph(f"NIP. {escape(_bersih(profil.get('nip') or '........................'))}", styles["body"]),
    ]
    table = Table([[kiri, kanan]], colWidths=[available / 2, available / 2], hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    return table


def _render(blocks: list[dict], profil: dict, styles, available: float,
            include_kop: bool, kop_text: bool = True) -> list:
    story: list = []
    if include_kop and profil.get("nama_sekolah"):
        story.append(Paragraph(escape(_bersih((profil.get("nama_sekolah") or "").upper())), styles["school"]))
        alamat = " | ".join(
            item for item in [profil.get("alamat"), profil.get("kabupaten"), profil.get("provinsi")] if item
        )
        if alamat:
            story.append(Paragraph(escape(_bersih(alamat)), styles["kop"]))
        info = " | ".join(
            item for item in [
                f"NPSN {profil.get('npsn')}" if profil.get("npsn") else "",
                profil.get("status_sekolah"),
                profil.get("kurikulum"),
            ] if item
        )
        if info:
            story.append(Paragraph(escape(_bersih(info)), styles["kop"]))
        story.append(Spacer(1, 8))

    for block in blocks:
        tipe = block.get("type")
        if tipe == "doc_title":
            story.append(Paragraph(escape(_bersih(block.get("text", ""))), styles["title"]))
        elif tipe == "heading":
            story.append(Paragraph(escape(_bersih(block.get("text", ""))), styles["h1"]))
        elif tipe == "subheading":
            story.append(Paragraph(escape(_bersih(block.get("text", ""))), styles["h2"]))
        elif tipe == "paragraph":
            value = block.get("text", "")
            if str(value).strip():
                story.append(Paragraph(escape(_bersih(value)).replace("\n", "<br/>"), styles["body"]))
        elif tipe == "bullets":
            for item in block.get("items", []):
                story.append(Paragraph("&bull; " + escape(_bersih(item)), styles["body"]))
        elif tipe == "table":
            table = _table_block(block, styles, available)
            if table:
                story.append(table)
                story.append(Spacer(1, 5))
        elif tipe == "signature":
            story.append(Spacer(1, 14))
            story.append(_signature_table(block.get("profil") or profil, styles, available))
        elif tipe == "signature_lkpd":
            story.append(Spacer(1, 14))
            story.append(_signature_table(block.get("profil") or profil, styles, available))
    story.append(Spacer(1, 8))
    story.append(
        Paragraph(
            "Disusun dengan bantuan aplikasi Generator RPM. Dokumen bukan pengesahan resmi; "
            "guru tetap melakukan reviu dan penyesuaian.",
            styles["small"],
        )
    )
    return story


def _build(blocks: list[dict], profil: dict, margins: tuple[float, float, float, float],
           title: str, subject: str) -> bytes:
    buffer = io.BytesIO()
    top, left, bottom, right = margins
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=left * cm,
        rightMargin=right * cm,
        topMargin=top * cm,
        bottomMargin=bottom * cm,
        title=title,
        author=profil.get("nama_guru") or "Generator RPM",
        subject=subject,
        creator="Generator RPM",
        footerMargin=1.6 * cm,
    )
    styles = _styles()
    available = doc.width
    story = _render(blocks, profil, styles, available, include_kop=True)
    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return buffer.getvalue()


def build_rpm_pdf(profil: dict, pemb: dict, data: dict,
                  margins: tuple[float, float, float, float] = (2.0, 2.2, 2.0, 2.0)) -> bytes:
    blocks = konten.build_rpm_blocks(profil, pemb, data)
    return _build(
        blocks,
        profil,
        margins,
        title="Rencana Pembelajaran Mendalam",
        subject=f"{pemb.get('mata_pelajaran','')} - {pemb.get('materi_pokok','')}",
    )


def build_lkpd_pdf(profil: dict, pemb: dict, lkpd: dict, data: dict | None = None,
                   margins: tuple[float, float, float, float] = (2.0, 2.2, 2.0, 2.0)) -> bytes:
    blocks = konten.build_lkpd_blocks(profil, pemb, lkpd, data)
    return _build(
        blocks,
        profil,
        margins,
        title="Lembar Kerja Peserta Didik",
        subject=f"LKPD {pemb.get('mata_pelajaran','')}",
    )
