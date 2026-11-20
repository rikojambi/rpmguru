"""Halaman Profil Sekolah dan Guru."""

from __future__ import annotations

import streamlit as st

import config
from database import db
from modules import komponen


def _blank_profile() -> dict:
    settings = db.get_settings()
    return {
        "label": "",
        "nama_sekolah": "",
        "npsn": "",
        "alamat": "",
        "kabupaten": "",
        "provinsi": "",
        "nama_kepala_sekolah": "",
        "nama_guru": "",
        "nip": "",
        "tahun_pelajaran": settings.get("tahun_pelajaran", "2025/2026"),
        "semester": settings.get("semester", "Ganjil"),
        "jenjang": "SMP",
        "status_sekolah": "Negeri",
        "kurikulum": "Kurikulum Merdeka (Pembelajaran Mendalam)",
    }


def render() -> None:
    komponen.page_header(
        "Profil Sekolah dan Guru",
        "Identitas ini otomatis digunakan pada kop dan bagian tanda tangan dokumen.",
        "🏫",
    )

    profiles = db.list_profiles()

    if "_profil_pending" in st.session_state:
        st.session_state["profil_selected"] = st.session_state.pop("_profil_pending")
    if "profil_selected" not in st.session_state:
        aktif = db.get_active_profile()
        st.session_state["profil_selected"] = aktif["id"] if aktif else 0

    opsi = [0] + [p["id"] for p in profiles]
    if st.session_state.get("profil_selected") not in opsi:
        st.session_state["profil_selected"] = 0

    def label_profil(pid: int) -> str:
        if pid == 0:
            return "➕ Profil baru"
        row = next((p for p in profiles if p["id"] == pid), None)
        if not row:
            return f"Profil #{pid}"
        active = " ★" if row.get("is_active") else ""
        return f"{row.get('nama_sekolah') or 'Tanpa nama'} — {row.get('nama_guru') or 'Guru belum diisi'}{active}"

    atas1, atas2 = st.columns([2.2, 1])
    with atas1:
        terpilih = st.selectbox(
            "Pilih profil",
            options=opsi,
            format_func=label_profil,
            key="profil_selected",
        )
    with atas2:
        st.write("")
        st.caption(f"{len(profiles)} profil tersimpan. Satu profil ditandai aktif.")

    existing = db.get_profile(terpilih) if terpilih else None
    data = dict(existing) if existing else _blank_profile()

    if existing and existing.get("is_active"):
        st.markdown(komponen.tag("Profil aktif", "ok"), unsafe_allow_html=True)

    with st.form(key=f"profil_form_{terpilih}", clear_on_submit=False):
        st.markdown("#### Identitas Sekolah")
        c1, c2, c3 = st.columns([2, 1, 1])
        with c1:
            nama_sekolah = st.text_input("Nama sekolah *", value=data.get("nama_sekolah", ""))
        with c2:
            npsn = st.text_input("NPSN", value=data.get("npsn", ""))
        with c3:
            jenjang = st.selectbox(
                "Jenjang",
                options=config.JENJANG,
                index=config.JENJANG.index(data.get("jenjang")) if data.get("jenjang") in config.JENJANG else 2,
            )

        alamat = st.text_input("Alamat sekolah", value=data.get("alamat", ""))
        c4, c5, c6 = st.columns(3)
        with c4:
            kabupaten = st.text_input("Kabupaten/kota", value=data.get("kabupaten", ""))
        with c5:
            provinsi = st.text_input("Provinsi", value=data.get("provinsi", ""))
        with c6:
            status_sekolah = st.selectbox(
                "Status sekolah",
                options=config.STATUS_SEKOLAH,
                index=config.STATUS_SEKOLAH.index(data.get("status_sekolah")) if data.get("status_sekolah") in config.STATUS_SEKOLAH else 0,
            )

        kurikulum = st.selectbox(
            "Kurikulum yang digunakan",
            options=config.KURIKULUM,
            index=config.KURIKULUM.index(data.get("kurikulum")) if data.get("kurikulum") in config.KURIKULUM else 0,
        )

        st.markdown("#### Identitas Guru dan Kepala Sekolah")
        c7, c8 = st.columns(2)
        with c7:
            nama_guru = st.text_input("Nama guru *", value=data.get("nama_guru", ""))
        with c8:
            nip = st.text_input("NIP/NUPTK", value=data.get("nip", ""))
        c9, c10 = st.columns(2)
        with c9:
            nama_kepala_sekolah = st.text_input("Nama kepala sekolah", value=data.get("nama_kepala_sekolah", ""))
        with c10:
            label = st.text_input(
                "Label profil (opsional)",
                value=data.get("label", ""),
                help="Contoh: SMPN 1 - Bu Rina - 2025/2026. Membantu membedakan beberapa profil.",
            )

        st.markdown("#### Tahun Pelajaran")
        c11, c12, c13 = st.columns(3)
        with c11:
            tahun_pelajaran = st.text_input("Tahun pelajaran", value=data.get("tahun_pelajaran", "2025/2026"))
        with c12:
            semester = st.selectbox(
                "Semester",
                options=config.SEMESTER,
                index=config.SEMESTER.index(data.get("semester")) if data.get("semester") in config.SEMESTER else 0,
            )
        with c13:
            jadikan_aktif = st.checkbox(
                "Jadikan profil aktif",
                value=bool(data.get("is_active")) or not profiles,
                help="Profil aktif dipakai sebagai identitas bawaan pada dokumen baru.",
            )

        disimpan = st.form_submit_button("💾 Simpan Profil", type="primary", width="stretch")

    if disimpan:
        if not nama_sekolah.strip():
            st.error("Nama sekolah wajib diisi.")
        elif not nama_guru.strip():
            st.error("Nama guru wajib diisi.")
        else:
            payload = {
                "label": label,
                "nama_sekolah": nama_sekolah,
                "npsn": npsn,
                "alamat": alamat,
                "kabupaten": kabupaten,
                "provinsi": provinsi,
                "nama_kepala_sekolah": nama_kepala_sekolah,
                "nama_guru": nama_guru,
                "nip": nip,
                "tahun_pelajaran": tahun_pelajaran,
                "semester": semester,
                "jenjang": jenjang,
                "status_sekolah": status_sekolah,
                "kurikulum": kurikulum,
            }
            new_id = db.save_profile(payload, terpilih or None)
            if jadikan_aktif or not profiles:
                db.set_active_profile(new_id)
            db.log_activity("Simpan profil", f"{nama_sekolah} — {nama_guru}")
            st.session_state["_profil_pending"] = new_id
            st.success("Profil berhasil disimpan.")
            st.rerun()

    if existing:
        st.write("")
        st.markdown("### Tindakan Profil")
        kolom = st.columns([1, 1, 1.2, 2])
        with kolom[0]:
            if not existing.get("is_active"):
                if st.button("★ Jadikan Aktif", width="stretch"):
                    db.set_active_profile(existing["id"])
                    db.log_activity("Aktifkan profil", existing.get("nama_sekolah", ""))
                    st.success("Profil dijadikan aktif.")
                    st.rerun()
            else:
                st.button("★ Profil Aktif", disabled=True, width="stretch")
        with kolom[1]:
            if st.button("Duplikasi", width="stretch"):
                salinan = {k: v for k, v in existing.items() if k not in ("id", "created_at", "updated_at", "is_active")}
                salinan["nama_sekolah"] = f"{existing.get('nama_sekolah', '')} (salinan)"
                salinan["label"] = f"{existing.get('label', '') or existing.get('nama_sekolah', '')} (salinan)"
                new_id = db.save_profile(salinan)
                db.log_activity("Duplikasi profil", salinan["nama_sekolah"])
                st.session_state["_profil_pending"] = new_id
                st.rerun()
        with kolom[2]:
            with st.popover("Hapus profil", width="stretch"):
                st.warning("Profil yang dihapus tidak dapat dikembalikan. Dokumen yang sudah dibuat tetap tersimpan.")
                centang = st.checkbox("Saya yakin ingin menghapus.", key=f"hapus_profil_{existing['id']}")
                if st.button("Hapus permanen", disabled=not centang, key=f"hapus_profil_btn_{existing['id']}"):
                    db.delete_profile(existing["id"])
                    db.log_activity("Hapus profil", existing.get("nama_sekolah", ""))
                    sisa = db.list_profiles()
                    if sisa and not any(p.get("is_active") for p in sisa):
                        db.set_active_profile(sisa[0]["id"])
                    st.session_state["_profil_pending"] = sisa[0]["id"] if sisa else 0
                    st.rerun()

    st.write("")
    with st.expander("Panduan pengisian profil"):
        st.markdown(
            """
            - **Nama sekolah, guru, dan NIP** dipakai pada bagian tanda tangan dokumen.
            - **Kepala sekolah** dipakai pada kolom tanda tangan persetujuan.
            - **Tahun pelajaran dan semester** menjadi nilai bawaan saat membuat data pembelajaran.
            - Anda dapat menyimpan beberapa profil, misalnya untuk dua sekolah atau dua tahun pelajaran.
            - Bila ada beberapa profil, profil bertanda **aktif** yang dipakai sebagai identitas bawaan.
            """
        )
