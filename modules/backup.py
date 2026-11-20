"""Halaman Backup dan Restore Database."""

from __future__ import annotations

import shutil
from pathlib import Path

import streamlit as st

import config
from database import db
from modules import komponen


def _ukuran(bytes_value: int) -> str:
    value = float(bytes_value or 0)
    for unit in ("B", "KB", "MB", "GB"):
        if value < 1024:
            return f"{value:.1f} {unit}"
        value /= 1024
    return f"{value:.1f} TB"


def render() -> None:
    komponen.page_header(
        "Backup Database",
        "Cadangkan seluruh data ke berkas SQLite, lalu pulihkan bila diperlukan.",
        "💾",
    )
    komponen.show_flash()

    ukuran_db = config.DB_PATH.stat().st_size if config.DB_PATH.exists() else 0
    info = st.columns(3)
    info[0].metric("Ukuran database", _ukuran(ukuran_db))
    info[1].metric("Dokumen RPM", db.count_rpm())
    info[2].metric("Berkas backup", len(db.list_backup_files()))

    st.write("")
    st.markdown("### Buat Backup")
    komponen.info(
        f"Backup disimpan di folder <code>{config.BACKUP_DIR}</code>. Salin juga berkas backup ke flashdisk "
        "atau penyimpanan lain secara berkala.",
        "info",
    )
    kiri, kanan = st.columns([1, 2])
    with kiri:
        catatan = st.text_input("Catatan backup (opsional)", value="", key="backup_note")
        if st.button("💾 Buat backup sekarang", type="primary", width="stretch"):
            try:
                path = db.backup_database(catatan.strip() or "Backup manual")
            except Exception as exc:
                st.error(f"Backup gagal: {exc}")
            else:
                komponen.set_flash(f"Backup berhasil: {path.name}", "success")
                st.rerun()
    with kanan:
        st.caption(
            "Database menyimpan profil, data pembelajaran, bank CP/ATP, RPM, LKPD, versi, dan riwayat AI. "
            "Data tidak dikirim ke internet."
        )

    st.write("")
    st.markdown("### Berkas Backup Tersedia")
    files = db.list_backup_files()
    if not files:
        st.caption("Belum ada backup.")
    else:
        for item in files[:30]:
            baris = st.columns([2.6, 1, 1, 1.2])
            with baris[0]:
                st.markdown(f"**{item['filename']}**")
                st.caption(f"{item['modified']} · {_ukuran(item['size'])}")
            with baris[1]:
                if st.button("Unduh", key=f"unduh_{item['filename']}", width="stretch"):
                    st.session_state["_unduh_backup"] = item["path"]
            with baris[2]:
                with st.popover("Hapus", width="stretch"):
                    st.warning("Berkas backup akan dihapus dari folder backup.")
                    if st.button("Hapus berkas", key=f"hapus_b_{item['filename']}"):
                        try:
                            Path(item["path"]).unlink()
                            komponen.set_flash("Berkas backup dihapus.", "success")
                            st.rerun()
                        except Exception as exc:
                            st.error(f"Gagal menghapus: {exc}")
            with baris[3]:
                st.caption("")

        if st.session_state.get("_unduh_backup"):
            path = Path(st.session_state["_unduh_backup"])
            if path.exists():
                st.download_button(
                    f"⬇️ Unduh {path.name}",
                    data=path.read_bytes(),
                    file_name=path.name,
                    mime="application/x-sqlite3",
                    key="backup_download_final",
                    width="stretch",
                )

    st.write("")
    st.markdown("### Restore Database")
    with st.expander("Pulihkan dari berkas backup", expanded=False):
        komponen.info(
            "Restore akan mengganti seluruh data saat ini. Aplikasi otomatis membuat backup sebelum restore. "
            "Pastikan berkas berasal dari aplikasi ini.",
            "warning",
        )
        berkas = st.file_uploader("Unggah berkas .db", type=["db", "sqlite", "sqlite3"], key="restore_file")
        if berkas:
            simpan = config.UPLOAD_DIR / komponen.safe_filename(f"restore_{berkas.name}")
            simpan.write_bytes(berkas.getvalue())
            valid, pesan = db.validate_sqlite_file(simpan)
            if valid:
                st.success(pesan)
            else:
                st.error(pesan)
            centang = st.checkbox(
                "Saya memahami seluruh data saat ini akan diganti.", key="restore_confirm"
            )
            if st.button("♻️ Restore sekarang", disabled=not (valid and centang), key="restore_btn"):
                ok, pesan = db.restore_database(simpan)
                if ok:
                    st.cache_data.clear()
                    st.session_state.pop("rpm_id", None)
                    st.session_state.pop("validasi_hasil", None)
                    komponen.set_flash(pesan, "success")
                    st.rerun()
                else:
                    st.error(pesan)

    st.write("")
    st.markdown("### Lokasi Data")
    st.code(str(config.DATA_DIR), language=None)
    st.caption(
        "Jangan menghapus folder data saat aplikasi berjalan. Untuk memindahkan aplikasi, salin seluruh folder "
        "proyek termasuk folder data."
    )
    komponen.info(
        "Aplikasi tidak memiliki server pusat. Backup adalah tanggung jawab pengguna. Simpan salinan di lokasi lain.",
        "info",
    )
