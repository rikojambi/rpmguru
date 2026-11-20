"""Uji alur interaktif: profil, pembelajaran, bank CP, wizard RPM, validasi, arsip."""

from __future__ import annotations

import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

import config  # noqa: E402

TEST_DB = BASE / "data" / "test_flows.db"
TEST_BACKUP_DIR = BASE / "data" / "test_flows_backups"
for suffix in ("", "-wal", "-shm"):
    path = Path(str(TEST_DB) + suffix)
    if path.exists():
        path.unlink()
TEST_BACKUP_DIR.mkdir(parents=True, exist_ok=True)
config.DB_PATH = TEST_DB
config.BACKUP_DIR = TEST_BACKUP_DIR

from database import db  # noqa: E402

db.init_db()


def set_text(at, label: str, value: str) -> None:
    for widget in at.text_input:
        if widget.label == label:
            widget.set_value(value)
            return
    raise AssertionError(f"text_input '{label}' tidak ditemukan: {[w.label for w in at.text_input]}")


def set_area(at, label: str, value: str) -> None:
    for widget in at.text_area:
        if widget.label == label:
            widget.set_value(value)
            return
    raise AssertionError(f"text_area '{label}' tidak ditemukan: {[w.label for w in at.text_area]}")


def set_select(at, label: str, value: str) -> None:
    for widget in at.selectbox:
        if widget.label == label:
            widget.set_value(value)
            return
    raise AssertionError(f"selectbox '{label}' tidak ditemukan: {[w.label for w in at.selectbox]}")


def set_number(at, label: str, value) -> None:
    for widget in at.number_input:
        if widget.label == label:
            widget.set_value(value)
            return
    raise AssertionError(f"number_input '{label}' tidak ditemukan: {[w.label for w in at.number_input]}")


def click(at, label: str, index: int = 0) -> None:
    matches = [b for b in at.button if b.label == label]
    if len(matches) <= index:
        raise AssertionError(f"tombol '{label}' tidak ditemukan: {[b.label for b in at.button]}")
    matches[index].click().run()


def main() -> None:
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(BASE / "app.py"), default_timeout=180)
    at.run()
    assert not at.exception, at.exception
    print("OK  aplikasi berjalan")

    # ------------------------------------------------------------------
    # 1. Profil sekolah
    # ------------------------------------------------------------------
    at.radio(key="nav_page").set_value("Profil Sekolah").run()
    assert not at.exception, at.exception
    set_text(at, "Nama sekolah *", "SMP Negeri 1 Uji Alur")
    set_text(at, "NPSN", "99887766")
    set_text(at, "Alamat sekolah", "Jl. Uji Alur No. 5")
    set_text(at, "Kabupaten/kota", "Kota Uji")
    set_text(at, "Provinsi", "Jawa Barat")
    set_text(at, "Nama guru *", "Rina Uji, S.Pd.")
    set_text(at, "NIP/NUPTK", "198501012010012003")
    set_text(at, "Nama kepala sekolah", "Dra. Kepala Uji")
    set_text(at, "Tahun pelajaran", "2025/2026")
    click(at, "💾 Simpan Profil")
    assert not at.exception, at.exception
    profil = db.get_active_profile()
    assert profil and profil["nama_sekolah"] == "SMP Negeri 1 Uji Alur", profil
    print("OK  alur simpan profil")

    # ------------------------------------------------------------------
    # 2. Data pembelajaran
    # ------------------------------------------------------------------
    at.radio(key="nav_page").set_value("Data Pembelajaran").run()
    assert not at.exception, at.exception
    set_text(at, "Mata pelajaran *", "Ilmu Pengetahuan Alam")
    set_text(at, "Judul data/RPM", "RPM Uji Alur IPA")
    set_select(at, "Jenjang", "SMP")
    set_select(at, "Fase", "D")
    set_select(at, "Kelas", "7")
    set_text(at, "Elemen mata pelajaran", "Pemahaman IPA")
    set_area(
        at, "Capaian Pembelajaran (CP) *",
        "Peserta didik memahami klasifikasi makhluk hidup berdasarkan ciri yang dapat diamati.",
    )
    set_area(at, "Alur Tujuan Pembelajaran (ATP)", "Mengamati ciri; mengelompokkan; menyajikan hasil klasifikasi.")
    set_text(at, "Materi pokok *", "Klasifikasi makhluk hidup")
    set_area(
        at, "Tujuan Pembelajaran (TP)",
        "Peserta didik dapat mengidentifikasi ciri-ciri makhluk hidup.\n"
        "Peserta didik dapat mengklasifikasikan makhluk hidup berdasarkan ciri yang diamati.",
    )
    set_text(at, "Alokasi waktu", "2 x 40 menit")
    set_number(at, "Jumlah peserta didik", 32)
    set_area(at, "Karakteristik peserta didik", "Peserta didik aktif dan senang bekerja kelompok.")
    set_area(at, "Pengetahuan awal peserta didik", "Mengenal hewan dan tumbuhan di sekitar rumah.")
    set_area(at, "Kebutuhan belajar", "Perlu contoh konkret dan pendampingan istilah ilmiah.")
    set_area(at, "Konteks lingkungan sekolah", "Kebun dan halaman sekolah")
    set_area(at, "Sarana dan prasarana", "Ruang kelas, proyektor, lingkungan sekolah, buku paket")
    set_area(at, "Sumber belajar", "Buku IPA kelas VII dan benda nyata di kebun sekolah")
    click(at, "💾 Simpan Data Pembelajaran")
    assert not at.exception, at.exception
    daftar = db.list_pembelajaran()
    assert len(daftar) == 1, daftar
    pm_id = daftar[0]["id"]
    assert daftar[0]["mata_pelajaran"] == "Ilmu Pengetahuan Alam"
    print("OK  alur simpan data pembelajaran")

    # ------------------------------------------------------------------
    # 3. Bank CP
    # ------------------------------------------------------------------
    at.radio(key="nav_page").set_value("Bank CP dan ATP").run()
    assert not at.exception, at.exception
    set_text(at, "Mata pelajaran *", "Ilmu Pengetahuan Alam")
    set_text(at, "Elemen", "Pemahaman IPA")
    set_area(
        at, "Capaian Pembelajaran (CP) *",
        "CP dari dokumen guru untuk pengujian alur (bukan CP resmi).",
    )
    set_area(at, "Alur Tujuan Pembelajaran (ATP)", "ATP dari dokumen guru untuk pengujian alur.")
    click(at, "💾 Simpan Entri")
    assert not at.exception, at.exception
    assert len(db.list_bank_cp()) == 1
    print("OK  alur simpan bank CP")

    # ------------------------------------------------------------------
    # 4. Wizard RPM
    # ------------------------------------------------------------------
    at.radio(key="nav_page").set_value("Generator RPM").run()
    assert not at.exception, at.exception
    click(at, "➕ Buat RPM baru")
    assert not at.exception, at.exception
    assert db.count_rpm() == 1, db.count_rpm()
    rpm_id = at.session_state.get("rpm_id")
    assert rpm_id, "rpm_id tidak tersimpan pada session state"
    rpm_id = int(rpm_id)
    print("OK  buat RPM baru")

    langkah = ["Identifikasi", "Desain", "Pengalaman", "Asesmen", "Diferensiasi", "LKPD", "Refleksi"]
    for index, nama in enumerate(langkah, 1):
        # Generate draf offline untuk tahap ini
        click(at, "Draf offline")
        assert not at.exception, at.exception
        versi = len(db.list_versions(rpm_id))
        assert versi >= index + 1, f"versi tahap {nama}: {versi}"
        print(f"OK  generate offline tahap {index}: {nama} (versi {versi})")
        tombol_lanjut = "Validasi →" if index == len(langkah) else "Selanjutnya →"
        click(at, tombol_lanjut)
        assert not at.exception, at.exception

    # Setelah tahap terakhir, aplikasi berpindah ke halaman Validasi
    assert at.radio(key="nav_page").value == "Validasi RPM", at.radio(key="nav_page").value
    print("OK  navigasi akhir wizard menuju Validasi")

    # ------------------------------------------------------------------
    # 5. Validasi
    # ------------------------------------------------------------------
    click(at, "🔍 Jalankan Validasi")
    assert not at.exception, at.exception
    metrik = {m.label: m.value for m in at.metric}
    assert "Skor kesesuaian" in metrik, metrik
    jumlah = db.count_rpm()
    print("OK  validasi dijalankan:", metrik, "| RPM:", jumlah)

    # ------------------------------------------------------------------
    # 6. Arsip dokumen
    # ------------------------------------------------------------------
    at.radio(key="nav_page").set_value("Arsip Dokumen").run()
    assert not at.exception, at.exception
    assert len(at.dataframe) >= 1, "Tabel arsip tidak tampil"
    assert db.count_rpm() == 1
    print("OK  halaman arsip menampilkan dokumen")

    # ------------------------------------------------------------------
    # 7. Ekspor langsung dari data tersimpan
    # ------------------------------------------------------------------
    rpm = db.get_rpm(rpm_id)
    import json

    from modules import komponen

    data = json.loads(rpm["data_json"])
    pemb = db.get_pembelajaran(pm_id)
    profil = db.get_profile(profil["id"])
    from exports import docx_export, excel_export, pdf_export, txt_export

    assert docx_export.build_rpm_docx(profil, pemb, data)[:2] == b"PK"
    assert pdf_export.build_rpm_pdf(profil, pemb, data)[:4] == b"%PDF"
    assert excel_export.build_asesmen_workbook(profil, pemb, data)[:2] == b"PK"
    assert txt_export.build_rpm_txt(profil, pemb, data)[:3]
    print("OK  ekspor DOCX/PDF/XLSX/TXT dari dokumen hasil alur")

    # ------------------------------------------------------------------
    # 8. Backup via halaman
    # ------------------------------------------------------------------
    at.radio(key="nav_page").set_value("Backup Database").run()
    assert not at.exception, at.exception
    sebelum = len(db.list_backup_files())
    click(at, "💾 Buat backup sekarang")
    assert not at.exception, at.exception
    sesudah = len(db.list_backup_files())
    assert sesudah == sebelum + 1, (sebelum, sesudah)
    print("OK  alur backup database")

    # Bersihkan database uji
    for row in db.list_rpm(include_archived=True):
        db.delete_rpm(row["id"])
    for row in db.list_pembelajaran():
        db.delete_pembelajaran(row["id"])
    for row in db.list_profiles():
        db.delete_profile(row["id"])
    for row in db.list_bank_cp():
        db.delete_bank_cp(row["id"])
    db.execute("DELETE FROM backups")
    for berkas in TEST_BACKUP_DIR.glob("*.db"):
        berkas.unlink()
    if TEST_BACKUP_DIR.exists():
        TEST_BACKUP_DIR.rmdir()
    if TEST_DB.exists():
        TEST_DB.unlink()
    print("\nSEMUA UJI ALUR INTERAKTIF LULUS")


if __name__ == "__main__":
    main()
