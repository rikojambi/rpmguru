"""Uji Tahap 1: database, profil, pengaturan, dan generator offline."""

from __future__ import annotations

import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

import config  # noqa: E402

# Gunakan database dan folder backup uji terpisah agar data pengguna tidak tersentuh
TEST_DB = BASE / "data" / "test_tahap1.db"
TEST_BACKUP_DIR = BASE / "data" / "test_tahap1_backups"
for suffix in ("", "-wal", "-shm"):
    path = Path(str(TEST_DB) + suffix)
    if path.exists():
        path.unlink()
TEST_BACKUP_DIR.mkdir(parents=True, exist_ok=True)
config.DB_PATH = TEST_DB
config.BACKUP_DIR = TEST_BACKUP_DIR

from database import db  # noqa: E402


def main() -> None:
    db.init_db()
    assert config.DB_PATH.exists(), "Database tidak terbentuk"
    print("OK  database:", config.DB_PATH)

    assert len(config.DIMENSI_PROFIL) == 8
    assert len(config.SINTAKS_MODEL) >= 8
    print("OK  konstanta kurikulum")

    # Profil
    pid = db.save_profile(
        {
            "label": "Uji",
            "nama_sekolah": "SMP Negeri 1 Uji",
            "npsn": "12345678",
            "alamat": "Jl. Uji No. 1",
            "kabupaten": "Kota Uji",
            "provinsi": "Jawa Barat",
            "nama_kepala_sekolah": "Drs. Kepala",
            "nama_guru": "Rina Guru",
            "nip": "198001012005011001",
            "tahun_pelajaran": "2025/2026",
            "semester": "Ganjil",
            "jenjang": "SMP",
            "status_sekolah": "Negeri",
            "kurikulum": "Kurikulum Merdeka",
        }
    )
    assert pid > 0
    db.set_active_profile(pid)
    profil = db.get_active_profile()
    assert profil and profil["nama_sekolah"] == "SMP Negeri 1 Uji"
    print("OK  profil CRUD + aktif:", pid)

    # Pengaturan
    db.set_setting("ollama_model", "qwen2.5:7b")
    assert db.get_settings()["ollama_model"] == "qwen2.5:7b"
    print("OK  pengaturan")

    # Data pembelajaran
    pm_id = db.save_pembelajaran(
        {
            "profile_id": pid,
            "judul": "Uji Pembelajaran",
            "jenjang": "SMP",
            "fase": "D",
            "kelas": "7",
            "semester": "Ganjil",
            "mata_pelajaran": "IPA",
            "elemen": "Pemahaman IPA",
            "cp": "CP contoh dari guru (bukan CP resmi).",
            "atp": "ATP contoh dari guru.",
            "materi_pokok": "Klasifikasi makhluk hidup",
            "tp": "Peserta didik dapat mengklasifikasikan makhluk hidup berdasarkan ciri-cirinya.",
            "alokasi_waktu": "2 x 40 menit",
            "jumlah_peserta": 32,
            "karakteristik": "Peserta didik aktif dan beragam.",
            "pengetahuan_awal": "Sebagian sudah mengenal ciri hewan dan tumbuhan.",
            "kebutuhan_belajar": "Perlu contoh konkret dan kerja kelompok.",
            "konteks_lingkungan": "Kebun sekolah",
            "sarana": "Ruang kelas, proyektor, lingkungan sekolah",
            "sumber_belajar": "Buku IPA dan benda nyata di kebun sekolah",
        }
    )
    assert pm_id > 0
    pm = db.get_pembelajaran(pm_id)
    assert pm and pm["mata_pelajaran"] == "IPA"
    print("OK  pembelajaran CRUD:", pm_id)

    # Bank CP
    bank_id = db.save_bank_cp(
        {
            "jenjang": "SMP", "fase": "D", "mata_pelajaran": "IPA",
            "elemen": "Pemahaman IPA", "cp": "CP dari guru", "atp": "ATP dari guru",
            "sumber": "Dokumen guru", "is_official": 1,
        }
    )
    assert bank_id > 0 and len(db.list_bank_cp()) >= 1
    print("OK  bank CP")

    # Generator offline
    from ai import generator

    hasil = generator.generate_identifikasi(None, pm, ["Penalaran kritis", "Kolaborasi"])
    assert hasil.mode == "offline"
    assert hasil.data["kesiapan"]["pengetahuan_awal"]
    assert len(hasil.data["dimensi"]) == 2
    print("OK  identifikasi offline")

    desain = generator.generate_desain(None, pm, hasil.data)
    assert desain.data["tujuan"]
    assert desain.data["model"]["sintaks"]
    assert len(desain.data["prinsip"]) == 3
    print("OK  desain offline")

    pengalaman = generator.generate_pengalaman(None, pm, desain.data)
    for tahap in ("memahami", "mengaplikasi", "merefleksi"):
        assert pengalaman.data[tahap]["aktivitas_siswa"]
        assert pengalaman.data[tahap]["bukti"]
    print("OK  pengalaman offline")

    asesmen = generator.generate_asesmen(None, pm, desain.data)
    for jenis in ("awal", "proses", "akhir"):
        assert asesmen.data[jenis]["rubrik"]
        assert asesmen.data[jenis]["kktp"]
    print("OK  asesmen offline")

    dif = generator.generate_diferensiasi(None, pm, desain.data, pengalaman.data)
    assert len(dif.data["tingkat"]) == 3
    print("OK  diferensiasi offline")

    lkpd = generator.generate_lkpd(None, pm, desain.data, pengalaman.data)
    assert lkpd.data["masalah"] and lkpd.data["pertanyaan"]
    print("OK  LKPD offline")

    refleksi = generator.generate_refleksi(None, pm, desain.data)
    assert len(refleksi.data["siswa"]) == 5
    print("OK  refleksi offline")

    # Parser JSON
    assert generator.extract_json('```json\n{"a": 1}\n```') == {"a": 1}
    assert generator.extract_json('Berikut hasilnya: {"a": {"b": 2}} selesai') == {"a": {"b": 2}}
    print("OK  parser JSON")

    # RPM dan versi
    data = {
        "identifikasi": hasil.data, "desain": desain.data,
        "pengalaman": pengalaman.data, "asesmen": asesmen.data,
        "diferensiasi": dif.data, "lkpd": lkpd.data, "refleksi": refleksi.data,
    }
    rpm_id = db.create_rpm(pm_id, pid, "RPM Uji", data)
    assert rpm_id > 0
    db.save_rpm(rpm_id, data)
    db.save_version(rpm_id, data, "Uji versi")
    assert len(db.list_versions(rpm_id)) >= 2
    assert "identifikasi" in db.get_rpm(rpm_id)["data_json"]
    print("OK  RPM + versi")

    # Backup
    cadangan = db.backup_database("Uji otomatis")
    assert cadangan.exists()
    ok, pesan = db.validate_sqlite_file(cadangan)
    assert ok, pesan
    print("OK  backup:", cadangan.name)

    # Bersihkan data dan berkas uji
    db.delete_rpm(rpm_id)
    db.delete_bank_cp(bank_id)
    db.delete_pembelajaran(pm_id)
    db.delete_profile(pid)
    for berkas in TEST_BACKUP_DIR.glob("*"):
        berkas.unlink()
    if TEST_BACKUP_DIR.exists():
        TEST_BACKUP_DIR.rmdir()
    for suffix in ("", "-wal", "-shm"):
        path = Path(str(TEST_DB) + suffix)
        if path.exists():
            path.unlink()
    print("OK  pembersihan data uji")
    print("\nSEMUA UJI TAHAP 1 LULUS")


if __name__ == "__main__":
    main()
