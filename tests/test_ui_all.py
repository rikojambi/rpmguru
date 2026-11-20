"""Uji antarmuka seluruh halaman dengan data contoh."""

from __future__ import annotations

import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

import config  # noqa: E402

TEST_DB = BASE / "data" / "test_ui.db"
for suffix in ("", "-wal", "-shm"):
    path = Path(str(TEST_DB) + suffix)
    if path.exists():
        path.unlink()
config.DB_PATH = TEST_DB

from database import db  # noqa: E402

db.init_db()

from modules import editor  # noqa: E402


def seed() -> None:
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
            "profile_id": pid, "judul": "RPM IPA Klasifikasi Makhluk Hidup",
            "jenjang": "SMP", "fase": "D", "kelas": "7", "semester": "Ganjil",
            "mata_pelajaran": "Ilmu Pengetahuan Alam", "elemen": "Pemahaman IPA",
            "cp": "Peserta didik memahami klasifikasi makhluk hidup berdasarkan ciri-ciri yang dapat diamati.",
            "atp": "Mengamati ciri; mengelompokkan; menyajikan hasil.",
            "materi_pokok": "Klasifikasi makhluk hidup",
            "tp": "Peserta didik dapat mengidentifikasi ciri-ciri makhluk hidup.\nPeserta didik dapat mengklasifikasikan makhluk hidup berdasarkan ciri.",
            "alokasi_waktu": "2 x 40 menit", "jumlah_peserta": 32,
            "karakteristik": "Peserta didik aktif dan beragam.",
            "pengetahuan_awal": "Mengenal hewan dan tumbuhan sekitar.",
            "kebutuhan_belajar": "Perlu contoh konkret.",
            "konteks_lingkungan": "Kebun sekolah",
            "sarana": "Ruang kelas, proyektor, lingkungan sekolah",
            "sumber_belajar": "Buku IPA dan benda nyata",
        }
    )
    db.save_bank_cp(
        {
            "jenjang": "SMP", "fase": "D", "mata_pelajaran": "Ilmu Pengetahuan Alam",
            "elemen": "Pemahaman IPA", "cp": "CP contoh dari guru untuk pengujian.",
            "atp": "ATP contoh dari guru.", "sumber": "Uji", "is_official": 1,
        }
    )
    pemb = db.get_pembelajaran(pm_id)
    profile = db.get_profile(pid)
    from ai import generator

    ident = generator.generate_identifikasi(None, pemb, ["Penalaran kritis", "Kolaborasi"])
    desain = generator.generate_desain(None, pemb, ident.data)
    pengalaman = generator.generate_pengalaman(None, pemb, desain.data)
    asesmen = generator.generate_asesmen(None, pemb, desain.data)
    dif = generator.generate_diferensiasi(None, pemb, desain.data, pengalaman.data)
    lkpd_data = generator.generate_lkpd(None, pemb, desain.data, pengalaman.data)
    ref = generator.generate_refleksi(None, pemb, desain.data)
    data = {
        "identifikasi": ident.data, "desain": desain.data, "pengalaman": pengalaman.data,
        "asesmen": asesmen.data, "diferensiasi": dif.data, "lkpd": lkpd_data.data,
        "refleksi": ref.data,
    }
    rpm_id = db.create_rpm(pm_id, pid, "RPM IPA Klasifikasi Makhluk Hidup", data)
    db.save_lkpd(rpm_id, lkpd_data.data, "LKPD Klasifikasi")
    db.log_activity("Uji antarmuka", "Data contoh dibuat")


def main() -> None:
    seed()
    from streamlit.testing.v1 import AppTest

    pages = [
        "Dashboard", "Profil Sekolah", "Data Pembelajaran", "Bank CP dan ATP",
        "Generator RPM", "Generator LKPD", "Generator Asesmen", "Validasi RPM",
        "Arsip Dokumen", "Pengaturan AI", "Backup Database",
    ]
    at = AppTest.from_file(str(BASE / "app.py"), default_timeout=120)
    at.run()
    assert not at.exception, at.exception
    print("OK  Dashboard")
    for page in pages[1:]:
        at.radio(key="nav_page").set_value(page).run()
        if at.exception:
            print(f"GAGAL halaman {page}")
            raise AssertionError(at.exception)
        print(f"OK  {page}")

    # Bersihkan database uji
    for row in db.list_rpm(include_archived=True):
        db.delete_rpm(row["id"])
    for row in db.list_pembelajaran():
        db.delete_pembelajaran(row["id"])
    for p in db.list_profiles():
        db.delete_profile(p["id"])
    for b in db.list_bank_cp():
        db.delete_bank_cp(b["id"])
    if TEST_DB.exists():
        TEST_DB.unlink()
    print("\nSEMUA HALAMAN BERHASIL DIMUAT")


if __name__ == "__main__":
    main()
