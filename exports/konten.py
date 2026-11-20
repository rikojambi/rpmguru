"""Pembentuk konten dokumen RPM/LKPD yang dipakai bersama oleh eksportir."""

from __future__ import annotations

from datetime import datetime
from typing import Any

import config


# ---------------------------------------------------------------------------
# Utilitas
# ---------------------------------------------------------------------------
def g(data: dict, *path: str, default: Any = "") -> Any:
    current: Any = data
    for part in path:
        if not isinstance(current, dict):
            return default
        current = current.get(part, default)
    return default if current is None else current


def text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (list, tuple)):
        return "\n".join(text(v) for v in value if text(v))
    if isinstance(value, dict):
        return "\n".join(f"{k.replace('_', ' ').title()}: {text(v)}" for k, v in value.items())
    return str(value).strip()


def numbered(items: list) -> str:
    if not items:
        return ""
    return "\n".join(f"{i}. {text(item)}" for i, item in enumerate(items, 1) if text(item))


def bullets(items: list) -> str:
    if not items:
        return ""
    return "\n".join(f"• {text(item)}" for item in items if text(item))


def table(headers: list[str], rows: list[list]) -> dict:
    return {"type": "table", "headers": headers, "rows": rows}


def heading(value: str) -> dict:
    return {"type": "heading", "text": value}


def subheading(value: str) -> dict:
    return {"type": "subheading", "text": value}


def paragraph(value: str) -> dict:
    return {"type": "paragraph", "text": value}


def bullet_block(items: list) -> dict:
    return {"type": "bullets", "items": [text(i) for i in items if text(i)]}


def rupiah_date() -> str:
    bulan = [
        "Januari", "Februari", "Maret", "April", "Mei", "Juni",
        "Juli", "Agustus", "September", "Oktober", "November", "Desember",
    ]
    now = datetime.now()
    return f"{now.day} {bulan[now.month - 1]} {now.year}"


# ---------------------------------------------------------------------------
# Blok RPM
# ---------------------------------------------------------------------------
def build_rpm_blocks(profil: dict, pemb: dict, data: dict) -> list[dict]:
    ident = data.get("identifikasi", {}) if isinstance(data.get("identifikasi"), dict) else {}
    desain = data.get("desain", {}) if isinstance(data.get("desain"), dict) else {}
    pengalaman = data.get("pengalaman", {}) if isinstance(data.get("pengalaman"), dict) else {}
    asesmen_data = data.get("asesmen", {}) if isinstance(data.get("asesmen"), dict) else {}
    dif = data.get("diferensiasi", {}) if isinstance(data.get("diferensiasi"), dict) else {}
    refleksi = data.get("refleksi", {}) if isinstance(data.get("refleksi"), dict) else {}

    blocks: list[dict] = []
    blocks.append({"type": "doc_title", "text": "RENCANA PEMBELAJARAN MENDALAM (RPM)"})
    blocks.append(paragraph(f"Nama Sekolah: {text(profil.get('nama_sekolah'))}"))
    blocks.append(paragraph(f"Tahun Pelajaran {text(profil.get('tahun_pelajaran'))} · Semester {text(profil.get('semester'))}"))

    # 1. Identitas
    blocks.append(heading("1. Identitas Pembelajaran"))
    ident_rows = [
        ["Nama Sekolah", text(profil.get("nama_sekolah"))],
        ["NPSN", text(profil.get("npsn"))],
        ["Alamat", text(profil.get("alamat"))],
        ["Kabupaten/Kota", text(profil.get("kabupaten"))],
        ["Provinsi", text(profil.get("provinsi"))],
        ["Mata Pelajaran", text(pemb.get("mata_pelajaran"))],
        ["Kelas / Fase", f"{text(pemb.get('kelas'))} / {text(pemb.get('fase'))}"],
        ["Semester", text(pemb.get("semester") or profil.get("semester"))],
        ["Tahun Pelajaran", text(profil.get("tahun_pelajaran"))],
        ["Materi Pokok", text(pemb.get("materi_pokok"))],
        ["Elemen", text(pemb.get("elemen"))],
    ]
    if text(pemb.get("konsentrasi")):
        ident_rows.append(["Konsentrasi Keahlian", text(pemb.get("konsentrasi"))])
    ident_rows.extend(
        [
            ["Alokasi Waktu", text(pemb.get("alokasi_waktu"))],
            ["Jumlah Peserta Didik", f"{text(pemb.get('jumlah_peserta'))} orang"],
            ["Guru Mata Pelajaran", text(profil.get("nama_guru"))],
            ["NIP/NUPTK", text(profil.get("nip"))],
            ["Kurikulum", text(profil.get("kurikulum"))],
            ["Capaian Pembelajaran (CP)", text(pemb.get("cp"))],
            ["Alur Tujuan Pembelajaran (ATP)", text(pemb.get("atp"))],
        ]
    )
    blocks.append(table(["Komponen", "Keterangan"], ident_rows))
    blocks.append(paragraph(
        "Catatan: CP dan ATP pada dokumen ini berasal dari data yang dimasukkan guru. "
        "Aplikasi tidak membuat CP resmi dan tidak mengklaim dokumen telah disahkan."
    ))

    # 2. Identifikasi peserta didik
    blocks.append(heading("2. Identifikasi Peserta Didik"))
    kesiapan = ident.get("kesiapan") or {}
    blocks.append(table(
        ["Aspek", "Uraian"],
        [
            ["Pengetahuan awal", text(kesiapan.get("pengetahuan_awal"))],
            ["Tingkat pemahaman", text(kesiapan.get("tingkat_pemahaman"))],
            ["Keterampilan awal", text(kesiapan.get("keterampilan_awal"))],
            ["Kesulitan belajar", text(kesiapan.get("kesulitan_belajar"))],
            ["Kebutuhan dukungan", text(kesiapan.get("kebutuhan_dukungan"))],
        ],
    ))

    # 3. Karakteristik materi
    blocks.append(heading("3. Karakteristik Materi"))
    materi = ident.get("materi") or {}
    konsep = materi.get("konsep_utama") or []
    blocks.append(table(
        ["Aspek", "Uraian"],
        [
            ["Jenis pengetahuan", text(materi.get("jenis_pengetahuan"))],
            ["Konsep utama", numbered(konsep) if isinstance(konsep, list) else text(konsep)],
            ["Keterkaitan antarmateri", text(materi.get("keterkaitan"))],
            ["Penerapan dalam kehidupan nyata", text(materi.get("penerapan"))],
            ["Potensi pembelajaran kontekstual", text(materi.get("potensi_kontekstual"))],
        ],
    ))
    if text(ident.get("catatan")):
        blocks.append(paragraph(f"Catatan identifikasi: {text(ident.get('catatan'))}"))

    # 4. Dimensi profil lulusan
    blocks.append(heading("4. Dimensi Profil Lulusan"))
    dimensi_rows = [
        [text(row.get("nama")), text(row.get("alasan")), text(row.get("wujud_aktivitas"))]
        for row in (ident.get("dimensi") or []) if isinstance(row, dict)
    ]
    if dimensi_rows:
        blocks.append(table(["Dimensi", "Alasan pemilihan", "Wujud dalam aktivitas peserta didik"], dimensi_rows))
    else:
        blocks.append(paragraph("Belum diisi."))

    # 5. Tujuan
    blocks.append(heading("5. Tujuan Pembelajaran"))
    tujuan_rows = [
        [str(i), text(row.get("tp")), text(row.get("indikator")), text(row.get("asesmen"))]
        for i, row in enumerate((desain.get("tujuan") or []), 1)
        if isinstance(row, dict)
    ]
    if tujuan_rows:
        blocks.append(table(["No", "Tujuan Pembelajaran", "Indikator", "Asesmen"], tujuan_rows))
    else:
        blocks.append(paragraph("Belum diisi."))

    # 6. Praktik pedagogis
    blocks.append(heading("6. Praktik Pedagogis"))
    model = desain.get("model") or {}
    blocks.append(table(
        ["Komponen", "Uraian"],
        [
            ["Model pembelajaran", text(model.get("nama"))],
            ["Alasan pemilihan", text(model.get("alasan"))],
            ["Sintaks", numbered(model.get("sintaks") or [])],
        ],
    ))

    # 7. Kemitraan
    blocks.append(heading("7. Kemitraan Pembelajaran"))
    kemitraan_rows = [
        [text(row.get("pihak")), text(row.get("peran"))]
        for row in (desain.get("kemitraan") or []) if isinstance(row, dict)
    ]
    blocks.append(table(["Pihak", "Peran"], kemitraan_rows) if kemitraan_rows else paragraph("Belum diisi."))

    # 8. Lingkungan
    blocks.append(heading("8. Lingkungan Pembelajaran"))
    lingkungan = desain.get("lingkungan") or []
    blocks.append(bullet_block(lingkungan) if lingkungan else paragraph("Belum diisi."))

    # 9. Pemanfaatan digital
    blocks.append(heading("9. Pemanfaatan Digital"))
    digital_rows = [
        [text(row.get("alat")), text(row.get("pemanfaatan"))]
        for row in (desain.get("digital") or []) if isinstance(row, dict)
    ]
    blocks.append(table(["Alat/Media", "Pemanfaatan"], digital_rows) if digital_rows else paragraph("Belum diisi."))

    # 10. Prinsip
    blocks.append(heading("10. Prinsip Pembelajaran"))
    prinsip_rows = [
        [text(row.get("prinsip")), text(row.get("wujud"))]
        for row in (desain.get("prinsip") or []) if isinstance(row, dict)
    ]
    blocks.append(table(["Prinsip", "Wujud dalam pembelajaran"], prinsip_rows) if prinsip_rows else paragraph("Belum diisi."))

    # 11. Pengalaman belajar
    blocks.append(heading("11. Pengalaman Belajar"))
    for key, label in (("memahami", "A. Memahami"), ("mengaplikasi", "B. Mengaplikasi"), ("merefleksi", "C. Merefleksi")):
        tahap = pengalaman.get(key) or {}
        blocks.append(subheading(label))
        blocks.append(table(
            ["Komponen", "Uraian"],
            [
                ["Aktivitas guru", text(tahap.get("aktivitas_guru"))],
                ["Aktivitas peserta didik", text(tahap.get("aktivitas_siswa"))],
                ["Alokasi waktu", text(tahap.get("alokasi"))],
                ["Media dan sumber", text(tahap.get("media"))],
                ["Dimensi profil lulusan", text(tahap.get("dimensi"))],
                ["Prinsip pembelajaran", text(tahap.get("prinsip"))],
                ["Bukti ketercapaian", text(tahap.get("bukti"))],
            ],
        ))
    if text(pengalaman.get("catatan")):
        blocks.append(paragraph(f"Catatan: {text(pengalaman.get('catatan'))}"))

    # 12. Langkah-langkah
    blocks.append(heading("12. Langkah-Langkah Pembelajaran"))
    langkah_rows = []
    for key, label in (("memahami", "Memahami"), ("mengaplikasi", "Mengaplikasi"), ("merefleksi", "Merefleksi")):
        tahap = pengalaman.get(key) or {}
        langkah_rows.append([
            label,
            text(tahap.get("aktivitas_guru")),
            text(tahap.get("aktivitas_siswa")),
            text(tahap.get("alokasi")),
        ])
    blocks.append(table(["Tahap", "Aktivitas Guru", "Aktivitas Peserta Didik", "Waktu"], langkah_rows))

    # 13-15. Asesmen
    for nomor, key, judul in (
        (13, "awal", "13. Asesmen Awal"),
        (14, "proses", "14. Asesmen Proses (Formatif)"),
        (15, "akhir", "15. Asesmen Akhir (Sumatif)"),
    ):
        blocks.append(heading(judul))
        item = asesmen_data.get(key) or {}
        soal = item.get("soal") or []
        kunci = item.get("kunci") or []
        blocks.append(table(
            ["Komponen", "Uraian"],
            [
                ["Tujuan asesmen", text(item.get("tujuan"))],
                ["Instrumen", text(item.get("instrumen"))],
                ["Soal/tugas", numbered(soal) if isinstance(soal, list) else text(soal)],
                ["Kunci/rambu jawaban", numbered(kunci) if isinstance(kunci, list) else text(kunci)],
                ["Pedoman penskoran", text(item.get("pedoman"))],
                ["KKTP", text(item.get("kktp"))],
            ],
        ))
        rubrik_rows = [
            [text(row.get("kriteria")), text(row.get("deskripsi"))]
            for row in (item.get("rubrik") or []) if isinstance(row, dict)
        ]
        if rubrik_rows:
            blocks.append(subheading("Rubrik"))
            blocks.append(table(["Kriteria", "Deskripsi capaian"], rubrik_rows))
    if text(asesmen_data.get("catatan")):
        blocks.append(paragraph(f"Catatan asesmen: {text(asesmen_data.get('catatan'))}"))

    # 16. Diferensiasi
    blocks.append(heading("16. Diferensiasi Pembelajaran"))
    if text(dif.get("ringkasan")):
        blocks.append(paragraph(text(dif.get("ringkasan"))))
    for level in (dif.get("tingkat") or []):
        if not isinstance(level, dict):
            continue
        blocks.append(subheading(text(level.get("tingkat")) or "Tingkat dukungan"))
        blocks.append(table(
            ["Aspek", "Penyesuaian"],
            [
                ["Ciri kesiapan", text(level.get("kesiapan"))],
                ["Kompleksitas tugas", text(level.get("kompleksitas"))],
                ["Scaffolding", text(level.get("scaffolding"))],
                ["Variasi sumber", text(level.get("sumber"))],
                ["Pengelompokan", text(level.get("pengelompokan"))],
                ["Pilihan produk", text(level.get("produk"))],
            ],
        ))
    if text(dif.get("catatan")):
        blocks.append(paragraph(f"Catatan: {text(dif.get('catatan'))}"))

    # 17. Media dan sumber
    blocks.append(heading("17. Media dan Sumber Belajar"))
    media_items = []
    for key in ("memahami", "mengaplikasi", "merefleksi"):
        media = text((pengalaman.get(key) or {}).get("media"))
        if media:
            media_items.append(media)
    if text(pemb.get("sarana")):
        media_items.append(f"Sarana dan prasarana: {text(pemb.get('sarana'))}")
    if text(pemb.get("sumber_belajar")):
        media_items.append(f"Sumber belajar: {text(pemb.get('sumber_belajar'))}")
    blocks.append(bullet_block(media_items) if media_items else paragraph("Belum diisi."))

    # 18. Refleksi siswa
    blocks.append(heading("18. Refleksi Peserta Didik"))
    siswa = refleksi.get("siswa") or []
    blocks.append(bullet_block(siswa) if siswa else paragraph("Belum diisi."))

    # 19. Refleksi guru
    blocks.append(heading("19. Refleksi Guru"))
    guru = refleksi.get("guru") or []
    blocks.append(bullet_block(guru) if guru else paragraph("Belum diisi."))

    if text(data.get("catatan")):
        blocks.append(heading("Catatan Akhir"))
        blocks.append(paragraph(text(data.get("catatan"))))

    blocks.append({"type": "signature", "profil": profil})
    return blocks


# ---------------------------------------------------------------------------
# Blok LKPD
# ---------------------------------------------------------------------------
def build_lkpd_blocks(profil: dict, pemb: dict, lkpd: dict, data: dict | None = None) -> list[dict]:
    blocks: list[dict] = []
    blocks.append({"type": "doc_title", "text": "LEMBAR KERJA PESERTA DIDIK (LKPD)"})
    blocks.append(paragraph(text(lkpd.get("judul")) or f"LKPD {text(pemb.get('mata_pelajaran'))}"))
    blocks.append(paragraph(
        f"{text(profil.get('nama_sekolah'))} · Tahun Pelajaran {text(profil.get('tahun_pelajaran'))} · "
        f"Semester {text(profil.get('semester'))}"
    ))

    blocks.append(heading("Identitas"))
    blocks.append(paragraph(text(lkpd.get("identitas")) or "Nama: ____________________  Kelas: ______  Tanggal: __________"))
    blocks.append(table(
        ["Komponen", "Keterangan"],
        [
            ["Mata pelajaran", text(pemb.get("mata_pelajaran"))],
            ["Kelas / Fase", f"{text(pemb.get('kelas'))} / {text(pemb.get('fase'))}"],
            ["Materi pokok", text(pemb.get("materi_pokok"))],
            ["Alokasi waktu", text(pemb.get("alokasi_waktu"))],
            ["Nama guru", text(profil.get("nama_guru"))],
        ],
    ))

    blocks.append(heading("A. Tujuan Pembelajaran"))
    blocks.append(paragraph(text(lkpd.get("tujuan"))))

    blocks.append(heading("B. Petunjuk Pengerjaan"))
    blocks.append(paragraph(text(lkpd.get("petunjuk"))))

    blocks.append(heading("C. Permasalahan Kontekstual"))
    blocks.append(paragraph(text(lkpd.get("masalah"))))

    blocks.append(heading("D. Aktivitas Memahami"))
    blocks.append(paragraph(text(lkpd.get("memahami"))))

    blocks.append(heading("E. Aktivitas Mengaplikasi"))
    blocks.append(paragraph(text(lkpd.get("mengaplikasi"))))

    blocks.append(heading("F. Aktivitas Merefleksi"))
    blocks.append(paragraph(text(lkpd.get("merefleksi"))))

    pertanyaan = lkpd.get("pertanyaan") or []
    if pertanyaan:
        blocks.append(heading("G. Pertanyaan Analisis"))
        blocks.append(bullet_block(pertanyaan))

    blocks.append(heading("H. Kesimpulan"))
    blocks.append(paragraph(text(lkpd.get("kesimpulan"))))

    blocks.append(heading("I. Penilaian"))
    blocks.append(paragraph(text(lkpd.get("penilaian"))))

    if data:
        desain = data.get("desain") or {}
        rubrik_rows = []
        for item in (data.get("asesmen") or {}).get("proses", {}).get("rubrik", []):
            if isinstance(item, dict):
                rubrik_rows.append([text(item.get("kriteria")), text(item.get("deskripsi"))])
        if rubrik_rows:
            blocks.append(heading("Rubrik Penilaian Proses"))
            blocks.append(table(["Kriteria", "Deskripsi capaian"], rubrik_rows))

    blocks.append({"type": "signature_lkpd", "profil": profil})
    return blocks


def build_signature(profil: dict) -> dict:
    return {"type": "signature", "profil": profil}
