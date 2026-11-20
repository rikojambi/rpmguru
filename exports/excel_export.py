"""Ekspor instrumen asesmen, rubrik, dan ringkasan RPM ke XLSX."""

from __future__ import annotations

import io

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from exports import konten


GREEN = "12503C"
LIGHT = "E6F2EC"
AMBER = "FDF1DE"
LINE = Side(style="thin", color="CFD9D2")
BORDER = Border(left=LINE, right=LINE, top=LINE, bottom=LINE)


def _title(ws, text: str, ncols: int) -> None:
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=ncols)
    cell = ws.cell(row=1, column=1, value=text)
    cell.font = Font(bold=True, size=14, color=GREEN)
    cell.alignment = Alignment(vertical="center")
    ws.row_dimensions[1].height = 26


def _subtitle(ws, row: int, text: str, ncols: int) -> int:
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=ncols)
    cell = ws.cell(row=row, column=1, value=text)
    cell.font = Font(bold=True, size=10.5, color="FFFFFF")
    cell.fill = PatternFill("solid", fgColor=GREEN)
    cell.alignment = Alignment(vertical="center")
    ws.row_dimensions[row].height = 20
    return row + 1


def _headers(ws, row: int, headers: list[str]) -> int:
    for index, header in enumerate(headers, 1):
        cell = ws.cell(row=row, column=index, value=header)
        cell.font = Font(bold=True, color="FFFFFF", size=9.5)
        cell.fill = PatternFill("solid", fgColor=GREEN)
        cell.alignment = Alignment(vertical="center", wrap_text=True)
        cell.border = BORDER
    ws.row_dimensions[row].height = 22
    return row + 1


def _row(ws, row: int, values: list, alternate: bool = False) -> int:
    for index, value in enumerate(values, 1):
        cell = ws.cell(row=row, column=index, value=value)
        cell.alignment = Alignment(vertical="top", wrap_text=True)
        cell.border = BORDER
        cell.font = Font(size=9)
        if alternate:
            cell.fill = PatternFill("solid", fgColor="F7F9F7")
    return row + 1


def _widths(ws, widths: list[float]) -> None:
    for index, width in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(index)].width = width


def _field_table(ws, row: int, fields: list[tuple[str, str]]) -> int:
    for label, value in fields:
        cell_label = ws.cell(row=row, column=1, value=label)
        cell_label.font = Font(bold=True, size=9)
        cell_label.fill = PatternFill("solid", fgColor=LIGHT)
        cell_label.alignment = Alignment(vertical="top", wrap_text=True)
        cell_label.border = BORDER
        cell_value = ws.cell(row=row, column=2, value=value)
        cell_value.alignment = Alignment(vertical="top", wrap_text=True)
        cell_value.font = Font(size=9)
        cell_value.border = BORDER
        ws.merge_cells(start_row=row, start_column=2, end_row=row, end_column=4)
        row += 1
    return row


def build_asesmen_workbook(profil: dict, pemb: dict, data: dict) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = "Ringkasan"
    _title(ws, "INSTRUMEN ASESMEN DAN RUBRIK", 4)
    row = 3
    row = _subtitle(ws, row, "Identitas Pembelajaran", 4)
    row = _field_table(
        ws,
        row,
        [
            ("Sekolah", konten.text(profil.get("nama_sekolah"))),
            ("Guru", konten.text(profil.get("nama_guru"))),
            ("Mata pelajaran", konten.text(pemb.get("mata_pelajaran"))),
            ("Kelas / Fase", f"{konten.text(pemb.get('kelas'))} / {konten.text(pemb.get('fase'))}"),
            ("Materi pokok", konten.text(pemb.get("materi_pokok"))),
            ("Alokasi waktu", konten.text(pemb.get("alokasi_waktu"))),
            ("Tahun pelajaran", konten.text(profil.get("tahun_pelajaran"))),
            ("Semester", konten.text(profil.get("semester"))),
        ],
    )
    row += 1
    row = _subtitle(ws, row, "Tujuan Pembelajaran", 4)
    tujuan = konten.g(data, "desain", "tujuan", default=[]) or []
    if tujuan:
        row = _headers(ws, row, ["No", "Tujuan Pembelajaran", "Indikator", "Asesmen"])
        for index, item in enumerate(tujuan, 1):
            row = _row(ws, row, [
                index, konten.text(item.get("tp")), konten.text(item.get("indikator")),
                konten.text(item.get("asesmen")),
            ], alternate=index % 2 == 0)
    else:
        ws.cell(row=row, column=1, value="Belum diisi.")
        row += 1
    row += 1
    row = _subtitle(ws, row, "Catatan", 4)
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=4)
    cell = ws.cell(row=row, column=1, value=konten.text(konten.g(data, "asesmen", "catatan")))
    cell.alignment = Alignment(wrap_text=True, vertical="top")
    cell.font = Font(size=9)
    ws.row_dimensions[row].height = 46
    _widths(ws, [22, 46, 46, 32])
    ws.freeze_panes = "A3"

    for key, judul in (
        ("awal", "Asesmen Awal"),
        ("proses", "Asesmen Proses"),
        ("akhir", "Asesmen Akhir"),
    ):
        sheet = wb.create_sheet(judul)
        _title(sheet, judul.upper(), 3)
        item = konten.g(data, "asesmen", key, default={}) or {}
        row = 3
        row = _subtitle(sheet, row, "Informasi Asesmen", 3)
        row = _field_table(
            sheet,
            row,
            [
                ("Tujuan", konten.text(item.get("tujuan"))),
                ("Instrumen", konten.text(item.get("instrumen"))),
                ("Pedoman penskoran", konten.text(item.get("pedoman"))),
                ("KKTP", konten.text(item.get("kktp"))),
            ],
        )
        row += 1
        row = _subtitle(sheet, row, "Soal/Tugas dan Kunci", 3)
        soal = item.get("soal") or []
        kunci = item.get("kunci") or []
        row = _headers(sheet, row, ["No", "Soal/Tugas", "Kunci/Rambu Jawaban"])
        if soal:
            for index, teks_soal in enumerate(soal, 1):
                jawaban = kunci[index - 1] if index - 1 < len(kunci) else ""
                row = _row(sheet, row, [index, konten.text(teks_soal), konten.text(jawaban)], alternate=index % 2 == 0)
        else:
            sheet.cell(row=row, column=1, value="Belum ada soal.")
            row += 1
        _widths(sheet, [6, 62, 62])
        sheet.freeze_panes = "A3"

    rubrik = wb.create_sheet("Rubrik")
    _title(rubrik, "RUBRIK PENILAIAN", 4)
    row = 3
    row = _headers(rubrik, row, ["Jenis Asesmen", "Kriteria", "Deskripsi Capaian", "Skor/Skala"])
    for key, label in (("awal", "Awal"), ("proses", "Proses"), ("akhir", "Akhir")):
        for item in (konten.g(data, "asesmen", key, "rubrik", default=[]) or []):
            if not isinstance(item, dict):
                continue
            row = _row(rubrik, row, [
                label, konten.text(item.get("kriteria")), konten.text(item.get("deskripsi")), "1 - 4",
            ])
    _widths(rubrik, [16, 30, 80, 12])
    rubrik.freeze_panes = "A4"

    dif = wb.create_sheet("Diferensiasi")
    _title(dif, "DIFERENSIASI PEMBELAJARAN", 7)
    row = 3
    row = _headers(dif, row, [
        "Tingkat", "Ciri Kesiapan", "Kompleksitas Tugas", "Scaffolding",
        "Variasi Sumber", "Pengelompokan", "Pilihan Produk",
    ])
    for item in (konten.g(data, "diferensiasi", "tingkat", default=[]) or []):
        if not isinstance(item, dict):
            continue
        row = _row(dif, row, [
            konten.text(item.get("tingkat")), konten.text(item.get("kesiapan")),
            konten.text(item.get("kompleksitas")), konten.text(item.get("scaffolding")),
            konten.text(item.get("sumber")), konten.text(item.get("pengelompokan")),
            konten.text(item.get("produk")),
        ])
    _widths(dif, [16, 26, 30, 30, 26, 24, 26])
    dif.freeze_panes = "A4"

    info = wb.create_sheet("Petunjuk")
    _title(info, "PETUNJUK PENGGUNAAN", 2)
    lines = [
        "Berkas ini memuat instrumen asesmen dan rubrik dari dokumen RPM.",
        "Kunci/rambu jawaban perlu disesuaikan dengan sumber belajar yang benar-benar dipakai guru.",
        "Rubrik dapat diubah sesuai keputusan guru/sekolah. Skala 1-4 bukan ketentuan wajib.",
        "Dokumen ini bukan pengesahan resmi. Guru tetap melakukan reviu.",
        f"Diekspor dari Generator RPM pada {konten.rupiah_date()}.",
    ]
    row = 3
    for line in lines:
        info.cell(row=row, column=1, value=f"- {line}").font = Font(size=9.5)
        row += 1
    _widths(info, [110])

    buffer = io.BytesIO()
    wb.save(buffer)
    return buffer.getvalue()


def build_lkpd_workbook(profil: dict, pemb: dict, lkpd: dict) -> bytes:
    """Ekspor sederhana LKPD ke Excel (opsional, untuk pengarsipan)."""
    wb = Workbook()
    ws = wb.active
    ws.title = "LKPD"
    _title(ws, "LEMBAR KERJA PESERTA DIDIK", 2)
    row = 3
    fields = [
        ("Judul", konten.text(lkpd.get("judul"))),
        ("Sekolah", konten.text(profil.get("nama_sekolah"))),
        ("Mata pelajaran", konten.text(pemb.get("mata_pelajaran"))),
        ("Kelas", konten.text(pemb.get("kelas"))),
        ("Identitas", konten.text(lkpd.get("identitas"))),
        ("Tujuan", konten.text(lkpd.get("tujuan"))),
        ("Petunjuk", konten.text(lkpd.get("petunjuk"))),
        ("Permasalahan", konten.text(lkpd.get("masalah"))),
        ("Memahami", konten.text(lkpd.get("memahami"))),
        ("Mengaplikasi", konten.text(lkpd.get("mengaplikasi"))),
        ("Merefleksi", konten.text(lkpd.get("merefleksi"))),
        ("Pertanyaan", konten.numbered(lkpd.get("pertanyaan") or [])),
        ("Kesimpulan", konten.text(lkpd.get("kesimpulan"))),
        ("Penilaian", konten.text(lkpd.get("penilaian"))),
    ]
    for label, value in fields:
        cell = ws.cell(row=row, column=1, value=label)
        cell.font = Font(bold=True, size=9)
        cell.fill = PatternFill("solid", fgColor=LIGHT)
        cell.alignment = Alignment(vertical="top", wrap_text=True)
        cell.border = BORDER
        val = ws.cell(row=row, column=2, value=value)
        val.font = Font(size=9)
        val.alignment = Alignment(vertical="top", wrap_text=True)
        val.border = BORDER
        ws.row_dimensions[row].height = max(18, min(140, 15 * (value.count("\n") + 1)))
        row += 1
    _widths(ws, [22, 90])
    buffer = io.BytesIO()
    wb.save(buffer)
    return buffer.getvalue()
