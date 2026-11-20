"""Ekspor dokumen RPM dan LKPD ke format DOCX."""

from __future__ import annotations

import io
from datetime import datetime
from typing import Iterable

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

from exports import konten


DARK_GREEN = RGBColor(0x0F, 0x51, 0x32)
INK = RGBColor(0x1C, 0x27, 0x22)
HEADER_FILL = "12503C"


# ---------------------------------------------------------------------------
# Utilitas DOCX
# ---------------------------------------------------------------------------
def _set_cell_shading(cell, color: str) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), color)
    tc_pr.append(shd)


def _set_cell_margins(cell, top=60, start=80, bottom=60, end=80) -> None:
    tc = cell._tc
    tc_pr = tc.get_or_add_tcPr()
    tc_mar = tc_pr.first_child_found_in("w:tcMar")
    if tc_mar is None:
        tc_mar = OxmlElement("w:tcMar")
        tc_pr.append(tc_mar)
    for tag, value in (("top", top), ("start", start), ("bottom", bottom), ("end", end)):
        node = OxmlElement(f"w:{tag}")
        node.set(qn("w:w"), str(value))
        node.set(qn("w:type"), "dxa")
        tc_mar.append(node)


def _repeat_header(row) -> None:
    tr_pr = row._tr.get_or_add_trPr()
    tbl_header = OxmlElement("w:tblHeader")
    tbl_header.set(qn("w:val"), "true")
    tr_pr.append(tbl_header)


def _no_borders(table) -> None:
    tbl = table._tbl
    tbl_pr = tbl.tblPr
    borders = OxmlElement("w:tblBorders")
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        element = OxmlElement(f"w:{edge}")
        element.set(qn("w:val"), "nil")
        borders.append(element)
    tbl_pr.append(borders)


def _paragraph_border_bottom(paragraph, size=12, color="12503C") -> None:
    p_pr = paragraph._p.get_or_add_pPr()
    p_bdr = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"), "single")
    bottom.set(qn("w:sz"), str(size))
    bottom.set(qn("w:space"), "1")
    bottom.set(qn("w:color"), color)
    p_bdr.append(bottom)
    p_pr.append(p_bdr)


def _add_page_number_footer(section) -> None:
    footer = section.footer
    paragraph = footer.paragraphs[0] if footer.paragraphs else footer.add_paragraph()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = paragraph.add_run("Halaman ")
    run.font.size = Pt(8.5)
    run.font.color.rgb = RGBColor(0x6B, 0x77, 0x70)

    def field(instr: str) -> None:
        fld_begin = OxmlElement("w:fldChar")
        fld_begin.set(qn("w:fldCharType"), "begin")
        instr_text = OxmlElement("w:instrText")
        instr_text.set(qn("xml:space"), "preserve")
        instr_text.text = instr
        fld_sep = OxmlElement("w:fldChar")
        fld_sep.set(qn("w:fldCharType"), "separate")
        fld_end = OxmlElement("w:fldChar")
        fld_end.set(qn("w:fldCharType"), "end")
        run_element = paragraph.add_run()._r
        run_element.append(fld_begin)
        run_element.append(instr_text)
        run_element.append(fld_sep)
        run_element.append(fld_end)
        paragraph.add_run(" ")

    field("PAGE")
    sep = paragraph.add_run(" dari ")
    sep.font.size = Pt(8.5)
    sep.font.color.rgb = RGBColor(0x6B, 0x77, 0x70)
    field("NUMPAGES")


def _style_document(document: Document) -> None:
    normal = document.styles["Normal"]
    normal.font.name = "Calibri"
    normal.font.size = Pt(10.5)
    normal.font.color.rgb = INK
    normal.paragraph_format.space_after = Pt(4)
    normal.paragraph_format.line_spacing = 1.12
    rpr = normal.element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts")
        rpr.append(rfonts)
    rfonts.set(qn("w:eastAsia"), "Calibri")

    h1 = document.styles["Heading 1"]
    h1.font.name = "Calibri"
    h1.font.size = Pt(12.5)
    h1.font.bold = True
    h1.font.color.rgb = DARK_GREEN
    h1.paragraph_format.space_before = Pt(14)
    h1.paragraph_format.space_after = Pt(5)
    h1.paragraph_format.keep_with_next = True

    h2 = document.styles["Heading 2"]
    h2.font.name = "Calibri"
    h2.font.size = Pt(11)
    h2.font.bold = True
    h2.font.color.rgb = DARK_GREEN
    h2.paragraph_format.space_before = Pt(9)
    h2.paragraph_format.space_after = Pt(3)
    h2.paragraph_format.keep_with_next = True


def _new_document(margins: tuple[float, float, float, float]) -> Document:
    document = Document()
    _style_document(document)
    section = document.sections[0]
    section.page_width = Cm(21.0)
    section.page_height = Cm(29.7)
    top, left, bottom, right = margins
    section.top_margin = Cm(top)
    section.left_margin = Cm(left)
    section.bottom_margin = Cm(bottom)
    section.right_margin = Cm(right)
    section.footer_distance = Cm(1.0)
    _add_page_number_footer(section)
    return document


def _add_kop(document: Document, profil: dict) -> None:
    nama = (profil.get("nama_sekolah") or "").upper()
    if not nama:
        return
    p = document.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run(nama)
    run.bold = True
    run.font.size = Pt(15)
    run.font.color.rgb = DARK_GREEN
    p.paragraph_format.space_after = Pt(1)

    alamat = " · ".join(
        item for item in [
            profil.get("alamat"),
            profil.get("kabupaten"),
            profil.get("provinsi"),
        ] if item
    )
    if alamat:
        p2 = document.add_paragraph()
        p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r2 = p2.add_run(alamat)
        r2.font.size = Pt(9)
        r2.font.color.rgb = RGBColor(0x45, 0x52, 0x4B)
        p2.paragraph_format.space_after = Pt(0)

    info = " · ".join(
        item for item in [
            f"NPSN {profil.get('npsn')}" if profil.get("npsn") else "",
            profil.get("status_sekolah"),
            profil.get("kurikulum"),
        ] if item
    )
    if info:
        p3 = document.add_paragraph()
        p3.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r3 = p3.add_run(info)
        r3.font.size = Pt(8.5)
        r3.font.color.rgb = RGBColor(0x6B, 0x77, 0x70)
        p3.paragraph_format.space_after = Pt(2)
        _paragraph_border_bottom(p3, size=14)
    else:
        _paragraph_border_bottom(p2, size=14)
    document.add_paragraph().paragraph_format.space_after = Pt(2)


def _add_table(document: Document, headers: list[str], rows: list[list]) -> None:
    if not rows:
        return
    table = document.add_table(rows=1, cols=len(headers))
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = True
    header_cells = table.rows[0].cells
    for index, header in enumerate(headers):
        cell = header_cells[index]
        cell.text = ""
        paragraph = cell.paragraphs[0]
        run = paragraph.add_run(str(header))
        run.bold = True
        run.font.size = Pt(9)
        run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
        _set_cell_shading(cell, HEADER_FILL)
        _set_cell_margins(cell)
    _repeat_header(table.rows[0])

    for row_values in rows:
        cells = table.add_row().cells
        for index, value in enumerate(row_values[: len(headers)]):
            cell = cells[index]
            cell.text = ""
            lines = str(value or "").split("\n")
            first = True
            for line in lines:
                if first:
                    paragraph = cell.paragraphs[0]
                    first = False
                else:
                    paragraph = cell.add_paragraph()
                paragraph.paragraph_format.space_after = Pt(0)
                paragraph.paragraph_format.line_spacing = 1.0
                run = paragraph.add_run(line)
                run.font.size = Pt(9)
                run.font.color.rgb = INK
            _set_cell_margins(cell)
    document.add_paragraph().paragraph_format.space_after = Pt(2)


def _add_signature(document: Document, profil: dict) -> None:
    document.add_paragraph()
    kota = profil.get("kabupaten") or profil.get("provinsi") or "………………"
    table = document.add_table(rows=3, cols=2)
    _no_borders(table)
    table.autofit = True

    def set_cell(cell, lines: list[str], bold_last: bool = False, align=WD_ALIGN_PARAGRAPH.LEFT):
        cell.text = ""
        first = True
        for line in lines:
            paragraph = cell.paragraphs[0] if first else cell.add_paragraph()
            first = False
            paragraph.alignment = align
            paragraph.paragraph_format.space_after = Pt(0)
            run = paragraph.add_run(line)
            run.font.size = Pt(10)
            if bold_last:
                run.bold = True

    set_cell(table.rows[0].cells[0], ["Mengetahui,", "Kepala Sekolah"])
    set_cell(table.rows[0].cells[1], [f"{kota}, ……………………… 20……"])
    set_cell(table.rows[1].cells[0], ["", "", "", ""])
    set_cell(table.rows[1].cells[1], ["", "", "", ""])
    set_cell(table.rows[2].cells[0], [profil.get("nama_kepala_sekolah") or "………………………………", "NIP. ………………………………………"])
    set_cell(table.rows[2].cells[1], [profil.get("nama_guru") or "………………………………", f"NIP. {profil.get('nip') or '……………………'}"])
    # Baris tanda tangan
    for cell in (table.rows[0].cells[0], table.rows[0].cells[1]):
        cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.LEFT
    document.add_paragraph(
        "Dokumen ini disusun dengan bantuan aplikasi Generator RPM. Guru tetap melakukan reviu dan penyesuaian."
    ).runs[0].font.size = Pt(8)


def _add_lkpd_signature(document: Document, profil: dict) -> None:
    document.add_paragraph()
    kota = profil.get("kabupaten") or "………………"
    table = document.add_table(rows=3, cols=2)
    _no_borders(table)
    table.rows[0].cells[0].text = ""
    cell_kanan = table.rows[0].cells[1]
    cell_kanan.text = f"{kota}, ……………………… 20……"
    table.rows[2].cells[0].text = ""
    cell_guru = table.rows[2].cells[1]
    cell_guru.text = ""
    p = cell_guru.paragraphs[0]
    p.add_run("Guru Mata Pelajaran\n\n\n").font.size = Pt(10)
    run = p.add_run(profil.get("nama_guru") or "………………………………")
    run.font.size = Pt(10)
    run.bold = True
    p2 = cell_guru.add_paragraph(f"NIP. {profil.get('nip') or '……………………'}")
    p2.runs[0].font.size = Pt(10)


def _render_blocks(document: Document, blocks: Iterable[dict], include_kop: bool,
                   profil: dict, include_signature: bool) -> None:
    for block in blocks:
        tipe = block.get("type")
        if tipe == "doc_title":
            p = document.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run = p.add_run(block.get("text", ""))
            run.bold = True
            run.font.size = Pt(14)
            run.font.color.rgb = DARK_GREEN
            p.paragraph_format.space_after = Pt(2)
        elif tipe == "heading":
            document.add_heading(block.get("text", ""), level=1)
        elif tipe == "subheading":
            document.add_heading(block.get("text", ""), level=2)
        elif tipe == "paragraph":
            value = block.get("text", "")
            if value:
                p = document.add_paragraph()
                for index, line in enumerate(str(value).split("\n")):
                    if index:
                        p.add_run().add_break()
                    p.add_run(line)
        elif tipe == "bullets":
            for item in block.get("items", []):
                p = document.add_paragraph(item, style="List Bullet")
                p.paragraph_format.space_after = Pt(1)
        elif tipe == "table":
            _add_table(document, block.get("headers", []), block.get("rows", []))
        elif tipe == "signature" and include_signature:
            _add_signature(document, block.get("profil") or profil)
        elif tipe == "signature_lkpd":
            _add_lkpd_signature(document, block.get("profil") or profil)


# ---------------------------------------------------------------------------
# API publik
# ---------------------------------------------------------------------------
def build_rpm_docx(profil: dict, pemb: dict, data: dict, include_kop: bool = True,
                   margins: tuple[float, float, float, float] = (2.0, 2.2, 2.0, 2.0),
                   include_signature: bool = True) -> bytes:
    document = _new_document(margins)
    if include_kop:
        _add_kop(document, profil)
    else:
        document.add_paragraph()
    blocks = konten.build_rpm_blocks(profil, pemb, data)
    _render_blocks(document, blocks, include_kop, profil, include_signature)
    props = document.core_properties
    props.title = "Rencana Pembelajaran Mendalam"
    props.author = profil.get("nama_guru") or "Generator RPM"
    props.subject = f"{pemb.get('mata_pelajaran','')} - {pemb.get('materi_pokok','')}"
    props.comments = "Dokumen draf; guru tetap melakukan reviu."
    buffer = io.BytesIO()
    document.save(buffer)
    return buffer.getvalue()


def build_lkpd_docx(profil: dict, pemb: dict, lkpd: dict, data: dict | None = None,
                    include_kop: bool = True,
                    margins: tuple[float, float, float, float] = (2.0, 2.2, 2.0, 2.0)) -> bytes:
    document = _new_document(margins)
    if include_kop:
        _add_kop(document, profil)
    blocks = konten.build_lkpd_blocks(profil, pemb, lkpd, data)
    _render_blocks(document, blocks, include_kop, profil, True)
    props = document.core_properties
    props.title = "Lembar Kerja Peserta Didik"
    props.author = profil.get("nama_guru") or "Generator RPM"
    buffer = io.BytesIO()
    document.save(buffer)
    return buffer.getvalue()
