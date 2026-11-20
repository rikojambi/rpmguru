"""Halaman Arsip Dokumen: pencarian, duplikasi, arsip, hapus, dan ekspor."""

from __future__ import annotations

import json

import pandas as pd
import streamlit as st

from database import db
from modules import editor, komponen
from modules.editor import ensure_structure


def _label_rpm(row: dict) -> str:
    return f"{row.get('judul') or 'RPM'} · {row.get('mata_pelajaran') or '-'} · {row.get('updated_at','')[:16]}"


def _profil_untuk(rpm: dict, pemb: dict) -> dict:
    return komponen.get_profile_for_document(pemb)


def _export_rpm(rpm: dict, pemb: dict, data: dict, key_suffix: str) -> None:
    from exports import docx_export, excel_export, pdf_export, txt_export

    profil = _profil_untuk(rpm, pemb)
    kolom = st.columns(4)
    try:
        with kolom[0]:
            komponen.download_bytes(
                "⬇️ DOCX",
                docx_export.build_rpm_docx(profil, pemb, data),
                f"RPM_{pemb.get('mata_pelajaran','')}_{pemb.get('kelas','')}.docx",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                f"arsip_docx_{key_suffix}",
            )
    except Exception as exc:
        st.error(f"DOCX gagal: {exc}")
    try:
        with kolom[1]:
            komponen.download_bytes(
                "⬇️ PDF",
                pdf_export.build_rpm_pdf(profil, pemb, data),
                f"RPM_{pemb.get('mata_pelajaran','')}_{pemb.get('kelas','')}.pdf",
                "application/pdf",
                f"arsip_pdf_{key_suffix}",
            )
    except Exception as exc:
        st.error(f"PDF gagal: {exc}")
    try:
        with kolom[2]:
            komponen.download_bytes(
                "⬇️ XLSX Asesmen",
                excel_export.build_asesmen_workbook(profil, pemb, data),
                f"Asesmen_{pemb.get('mata_pelajaran','')}_{pemb.get('kelas','')}.xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                f"arsip_xlsx_{key_suffix}",
            )
    except Exception as exc:
        st.error(f"XLSX gagal: {exc}")
    try:
        with kolom[3]:
            komponen.download_bytes(
                "⬇️ TXT",
                txt_export.build_rpm_txt(profil, pemb, data),
                f"RPM_{pemb.get('mata_pelajaran','')}_{pemb.get('kelas','')}.txt",
                "text/plain",
                f"arsip_txt_{key_suffix}",
            )
    except Exception as exc:
        st.error(f"TXT gagal: {exc}")


def render() -> None:
    komponen.page_header(
        "Arsip Dokumen",
        "Cari, buka kembali, duplikasi, arsipkan, dan ekspor dokumen yang pernah dibuat.",
        "🗄️",
    )
    komponen.show_flash()

    tab_rpm, tab_lkpd = st.tabs(["Dokumen RPM", "Dokumen LKPD"])

    with tab_rpm:
        _render_rpm_tab()

    with tab_lkpd:
        _render_lkpd_tab()


def _render_rpm_tab() -> None:
    cari = st.text_input("Cari dokumen (judul, mata pelajaran, sekolah)", key="arsip_cari")
    tampil_arsip = st.checkbox("Tampilkan dokumen yang diarsipkan", value=False, key="arsip_tampil")
    rows = db.list_rpm(search=cari, include_archived=tampil_arsip)

    if not rows:
        komponen.empty_state(
            "Belum ada dokumen",
            "Dokumen RPM yang Anda simpan akan muncul di sini. Buat melalui Generator RPM.",
        )
        if st.button("Buka Generator RPM", type="primary", key="arsip_buka_gen"):
            komponen.navigate("Generator RPM")
        return

    frame = pd.DataFrame(
        [
            {
                "Judul": row.get("judul", ""),
                "Mapel": row.get("mata_pelajaran", ""),
                "Kelas": row.get("kelas", ""),
                "Status": row.get("status", ""),
                "Versi": row.get("jumlah_versi", 0),
                "Diarsipkan": "Ya" if row.get("archived") else "Tidak",
                "Diperbarui": row.get("updated_at", ""),
            }
            for row in rows
        ]
    )
    st.dataframe(frame, width="stretch", hide_index=True, height=min(300, 40 + len(frame) * 32))
    st.caption(f"{len(rows)} dokumen ditampilkan.")

    ids = [row["id"] for row in rows]
    rpm_id = st.selectbox(
        "Pilih dokumen",
        ids,
        format_func=lambda x: _label_rpm(next(r for r in rows if r["id"] == x)),
        key="arsip_rpm_pilih",
    )
    rpm = db.get_rpm(rpm_id)
    if not rpm:
        return
    pemb = db.get_pembelajaran(rpm.get("pembelajaran_id")) or {}
    data = ensure_structure(json.loads(rpm.get("data_json") or "{}"))

    st.markdown(
        komponen.tag(rpm.get("judul") or "RPM", "info")
        + komponen.tag(f"{pemb.get('mata_pelajaran','-')} · Kelas {pemb.get('kelas','-')}", "neutral")
        + komponen.badge_status(rpm.get("status", "draf"))
        + komponen.tag("Diarsipkan" if rpm.get("archived") else "Aktif", "warn" if rpm.get("archived") else "ok"),
        unsafe_allow_html=True,
    )

    with st.expander("Ringkasan dokumen", expanded=False):
        st.write(f"**Sekolah:** {rpm.get('nama_sekolah') or '-'}")
        st.write(f"**Guru:** {rpm.get('nama_guru') or '-'}")
        st.write(f"**Dibuat:** {rpm.get('created_at','-')} · **Diperbarui:** {rpm.get('updated_at','-')}")
        st.write(f"**Kelengkapan tahap:** {editor.rpm_progress(data)}%")
        st.write(f"**Catatan:** {rpm.get('catatan') or '-'}")

    aksi = st.columns([1, 1, 1, 1, 1.4])
    with aksi[0]:
        if st.button("📂 Buka & edit", type="primary", width="stretch"):
            st.session_state["rpm_id"] = rpm_id
            st.session_state["wiz_step"] = 0
            komponen.navigate("Generator RPM")
    with aksi[1]:
        if st.button("📄 Duplikasi", width="stretch"):
            new_id = db.duplicate_rpm(rpm_id)
            db.log_activity("Duplikasi RPM", rpm.get("judul", ""))
            st.session_state["rpm_id"] = new_id
            komponen.set_flash("Dokumen diduplikasi.", "success")
            st.rerun()
    with aksi[2]:
        arsip_label = "♻️ Batalkan arsip" if rpm.get("archived") else "📦 Arsipkan"
        if st.button(arsip_label, width="stretch"):
            db.archive_rpm(rpm_id, not bool(rpm.get("archived")))
            db.log_activity("Arsip RPM", rpm.get("judul", ""))
            komponen.set_flash("Status arsip diperbarui.", "success")
            st.rerun()
    with aksi[3]:
        with st.popover("Hapus dokumen", width="stretch"):
            st.warning("Dokumen, versi, dan LKPD terkait akan dihapus permanen.")
            centang = st.checkbox("Saya yakin.", key=f"arsip_hapus_cek_{rpm_id}")
            if st.button("Hapus permanen", disabled=not centang, key=f"arsip_hapus_{rpm_id}"):
                db.delete_rpm(rpm_id)
                db.log_activity("Hapus RPM", rpm.get("judul", ""))
                komponen.set_flash("Dokumen dihapus.", "success")
                st.rerun()
    with aksi[4]:
        st.caption("Data pembelajaran dan profil tidak ikut terhapus.")

    with st.expander("Ekspor dokumen", expanded=False):
        _export_rpm(rpm, pemb, data, str(rpm_id))

    with st.expander("Riwayat versi", expanded=False):
        versi = db.list_versions(rpm_id)
        if not versi:
            st.caption("Belum ada versi.")
        else:
            st.dataframe(
                [
                    {
                        "Versi": f"v{v['version_no']}",
                        "Waktu": v.get("created_at", ""),
                        "Catatan": v.get("catatan", ""),
                    }
                    for v in versi
                ],
                width="stretch",
                hide_index=True,
            )
            st.caption("Pemulihan versi dilakukan dari halaman Generator RPM agar perubahan dapat diperiksa.")

    with st.expander("Tautan data pembelajaran", expanded=False):
        if pemb:
            st.write(f"Mapel: **{pemb.get('mata_pelajaran','-')}** · Materi: **{pemb.get('materi_pokok','-')}**")
            st.caption(f"CP: {komponen.truncate(pemb.get('cp',''), 220)}")
        else:
            komponen.info(
                "Data pembelajaran tidak ditemukan. Dokumen masih tersimpan, tetapi konteks pembelajarannya perlu dilengkapi.",
                "warning",
            )


def _render_lkpd_tab() -> None:
    rows = db.list_lkpd()
    if not rows:
        komponen.empty_state("Belum ada LKPD", "LKPD yang dibuat melalui Generator LKPD akan muncul di sini.")
        if st.button("Buka Generator LKPD", type="primary", key="arsip_buka_lkpd"):
            komponen.navigate("Generator LKPD")
        return

    frame = pd.DataFrame(
        [
            {
                "Judul": row.get("judul", ""),
                "RPM": row.get("judul_rpm", ""),
                "Diperbarui": row.get("updated_at", ""),
            }
            for row in rows
        ]
    )
    st.dataframe(frame, width="stretch", hide_index=True, height=min(260, 40 + len(frame) * 32))

    ids = [row["id"] for row in rows]
    lkpd_id = st.selectbox(
        "Pilih LKPD",
        ids,
        format_func=lambda x: next((r.get("judul") or f"LKPD #{x}" for r in rows if r["id"] == x), f"LKPD #{x}"),
        key="arsip_lkpd_pilih",
    )
    row = db.get_lkpd(lkpd_id)
    if not row:
        return
    data_lkpd = json.loads(row.get("data_json") or "{}")
    rpm = db.get_rpm(row.get("rpm_id"))
    pemb = db.get_pembelajaran(rpm.get("pembelajaran_id")) if rpm else None
    if not pemb:
        komponen.info("RPM/LKPD ini tidak memiliki data pembelajaran yang lengkap; ekspor mungkin terbatas.", "warning")
        pemb = {}
    rpm_data = ensure_structure(json.loads(rpm.get("data_json") or "{}")) if rpm else {}
    profil = komponen.get_profile_for_document(pemb)

    aksi = st.columns([1, 1, 2])
    with aksi[0]:
        if st.button("📂 Buka generator LKPD", type="primary", width="stretch"):
            if rpm:
                st.session_state["rpm_id"] = rpm["id"]
            komponen.navigate("Generator LKPD")
    with aksi[1]:
        with st.popover("Hapus LKPD", width="stretch"):
            st.warning("LKPD akan dihapus permanen. RPM tidak terhapus.")
            centang = st.checkbox("Saya yakin.", key=f"lkpd_hapus_cek_{lkpd_id}")
            if st.button("Hapus", disabled=not centang, key=f"lkpd_hapus_{lkpd_id}"):
                db.delete_lkpd(lkpd_id)
                db.log_activity("Hapus LKPD", row.get("judul", ""))
                komponen.set_flash("LKPD dihapus.", "success")
                st.rerun()

    with st.expander("Ekspor LKPD", expanded=True):
        from exports import docx_export, pdf_export, txt_export

        kolom = st.columns(3)
        try:
            with kolom[0]:
                komponen.download_bytes(
                    "⬇️ DOCX",
                    docx_export.build_lkpd_docx(profil, pemb, data_lkpd, rpm_data),
                    f"LKPD_{pemb.get('mata_pelajaran','')}.docx",
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    f"arsip_lkpd_docx_{lkpd_id}",
                )
        except Exception as exc:
            st.error(f"DOCX gagal: {exc}")
        try:
            with kolom[1]:
                komponen.download_bytes(
                    "⬇️ PDF",
                    pdf_export.build_lkpd_pdf(profil, pemb, data_lkpd, rpm_data),
                    f"LKPD_{pemb.get('mata_pelajaran','')}.pdf",
                    "application/pdf",
                    f"arsip_lkpd_pdf_{lkpd_id}",
                )
        except Exception as exc:
            st.error(f"PDF gagal: {exc}")
        try:
            with kolom[2]:
                komponen.download_bytes(
                    "⬇️ TXT",
                    txt_export.build_lkpd_txt(profil, pemb, data_lkpd, rpm_data),
                    f"LKPD_{pemb.get('mata_pelajaran','')}.txt",
                    "text/plain",
                    f"arsip_lkpd_txt_{lkpd_id}",
                )
        except Exception as exc:
            st.error(f"TXT gagal: {exc}")
