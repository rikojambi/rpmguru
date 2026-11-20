"""Uji integrasi Tahap 2-5: data, generator offline, validasi, ekspor."""

from __future__ import annotations

import io
import json
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

import config  # noqa: E402

# Gunakan database uji terpisah
TEST_DB = BASE / "data" / "test_integration.db"
TEST_BACKUP_DIR = BASE / "data" / "test_integration_backups"
for suffix in ("", "-wal", "-shm"):
    path = Path(str(TEST_DB) + suffix)
    if path.exists():
        path.unlink()
TEST_BACKUP_DIR.mkdir(parents=True, exist_ok=True)
config.DB_PATH = TEST_DB
config.BACKUP_DIR = TEST_BACKUP_DIR

from database import db  # noqa: E402

db.init_db()


def main() -> None:
    pid = db.save_profile(
        {
            "nama_sekolah": "SMP Negeri 1 Contoh",
            "npsn": "20202020",
            "alamat": "Jl. Pendidikan No. 10",
            "kabupaten": "Kota Contoh",
            "provinsi": "Jawa Barat",
            "nama_kepala_sekolah": "Dra. Kepala Sekolah",
            "nama_guru": "Rina Pratama, S.Pd.",
            "nip": "198501012010012003",
            "tahun_pelajaran": "2025/2026",
            "semester": "Ganjil",
            "jenjang": "SMP",
            "status_sekolah": "Negeri",
            "kurikulum": "Kurikulum Merdeka (Pembelajaran Mendalam)",
        }
    )
    db.set_active_profile(pid)
    pm_id = db.save_pembelajaran(
        {
            "profile_id": pid,
            "judul": "RPM IPA Klasifikasi Makhluk Hidup",
            "jenjang": "SMP", "fase": "D", "kelas": "7", "semester": "Ganjil",
            "mata_pelajaran": "Ilmu Pengetahuan Alam",
            "elemen": "Pemahaman IPA",
            "cp": "Peserta didik memahami klasifikasi makhluk hidup berdasarkan ciri-ciri yang dapat diamati.",
            "atp": "Mengamati ciri makhluk hidup; mengelompokkan berdasarkan ciri; menyajikan hasil klasifikasi.",
            "materi_pokok": "Klasifikasi makhluk hidup",
            "tp": "Peserta didik dapat mengidentifikasi ciri-ciri makhluk hidup.\nPeserta didik dapat mengklasifikasikan makhluk hidup berdasarkan ciri yang diamati.",
            "alokasi_waktu": "2 x 40 menit",
            "jumlah_peserta": 32,
            "karakteristik": "Peserta didik aktif, senang bekerja kelompok, kemampuan membaca beragam.",
            "pengetahuan_awal": "Sebagian besar telah mengenal hewan dan tumbuhan di sekitar rumah.",
            "kebutuhan_belajar": "Perlu contoh konkret, gambar, dan pendampingan untuk istilah ilmiah.",
            "konteks_lingkungan": "Kebun dan halaman sekolah",
            "sarana": "Ruang kelas, proyektor, lingkungan sekolah, buku paket",
            "sumber_belajar": "Buku IPA kelas VII, benda nyata di kebun sekolah, gambar makhluk hidup",
        }
    )
    profile = db.get_profile(pid)
    pemb = db.get_pembelajaran(pm_id)

    from ai import generator

    ident = generator.generate_identifikasi(None, pemb, ["Penalaran kritis", "Kolaborasi"])
    desain = generator.generate_desain(None, pemb, ident.data)
    pengalaman = generator.generate_pengalaman(None, pemb, desain.data)
    asesmen = generator.generate_asesmen(None, pemb, desain.data)
    dif = generator.generate_diferensiasi(None, pemb, desain.data, pengalaman.data)
    lkpd = generator.generate_lkpd(None, pemb, desain.data, pengalaman.data)
    ref = generator.generate_refleksi(None, pemb, desain.data)

    data = {
        "identifikasi": ident.data, "desain": desain.data, "pengalaman": pengalaman.data,
        "asesmen": asesmen.data, "diferensiasi": dif.data, "lkpd": lkpd.data,
        "refleksi": ref.data, "catatan": "",
    }
    print("OK  seluruh bagian offline dibuat")

    # Validasi
    from modules.validasi import validate_rpm, ringkasan

    checks = validate_rpm(pemb, data)
    stat = ringkasan(checks)
    assert len(checks) >= 10
    print(f"OK  validasi: {stat}")

    # Ekspor
    from exports import docx_export, excel_export, pdf_export, txt_export

    docx_bytes = docx_export.build_rpm_docx(profile, pemb, data)
    assert docx_bytes[:2] == b"PK"
    from docx import Document

    document = Document(io.BytesIO(docx_bytes))
    assert len(document.tables) >= 8
    assert len(document.paragraphs) >= 20
    print(f"OK  DOCX: {len(docx_bytes)} bytes, {len(document.tables)} tabel")

    pdf_bytes = pdf_export.build_rpm_pdf(profile, pemb, data)
    assert pdf_bytes[:4] == b"%PDF"
    assert len(pdf_bytes) > 8000
    print(f"OK  PDF: {len(pdf_bytes)} bytes")

    xlsx_bytes = excel_export.build_asesmen_workbook(profile, pemb, data)
    assert xlsx_bytes[:2] == b"PK"
    from openpyxl import load_workbook

    wb = load_workbook(io.BytesIO(xlsx_bytes))
    assert "Asesmen Awal" in wb.sheetnames and "Rubrik" in wb.sheetnames
    print(f"OK  XLSX: sheet {wb.sheetnames}")

    txt_bytes = txt_export.build_rpm_txt(profile, pemb, data)
    txt = txt_bytes.decode("utf-8")
    assert "RENCANA PEMBELAJARAN MENDALAM" in txt
    assert "19. REFLEKSI GURU" in txt.upper()
    print(f"OK  TXT: {len(txt_bytes)} bytes")

    lkpd_docx = docx_export.build_lkpd_docx(profile, pemb, lkpd.data, data)
    assert lkpd_docx[:2] == b"PK"
    lkpd_pdf = pdf_export.build_lkpd_pdf(profile, pemb, lkpd.data, data)
    assert lkpd_pdf[:4] == b"%PDF"
    print("OK  ekspor LKPD DOCX & PDF")

    # Database dokumen
    rpm_id = db.create_rpm(pm_id, pid, "RPM IPA Klasifikasi Makhluk Hidup", data)
    assert rpm_id
    db.save_version(rpm_id, data, "Uji integrasi")
    assert len(db.list_versions(rpm_id)) >= 2
    salinan = db.duplicate_rpm(rpm_id)
    assert salinan and salinan != rpm_id
    db.archive_rpm(salinan, True)
    assert any(r["id"] == salinan and r.get("archived") for r in db.list_rpm(include_archived=True))
    db.save_lkpd(rpm_id, lkpd.data, "LKPD Uji")
    assert db.list_lkpd(rpm_id)
    print("OK  RPM, versi, duplikasi, arsip, LKPD")

    cadangan = db.backup_database("Uji integrasi")
    assert cadangan.exists()
    print("OK  backup")

    # Bersihkan
    for row in db.list_rpm(include_archived=True):
        db.delete_rpm(row["id"])
    for row in db.list_pembelajaran():
        db.delete_pembelajaran(row["id"])
    for p in db.list_profiles():
        db.delete_profile(p["id"])
    for berkas in TEST_BACKUP_DIR.glob("*"):
        berkas.unlink()
    if TEST_BACKUP_DIR.exists():
        TEST_BACKUP_DIR.rmdir()
    if TEST_DB.exists():
        TEST_DB.unlink()
    print("\nSEMUA UJI INTEGRASI LULUS")


if __name__ == "__main__":
    main()
