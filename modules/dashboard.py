"""Halaman Dashboard."""

from __future__ import annotations

import streamlit as st

import config
from database import db
from modules import komponen


def _stat(label: str, value: str, hint: str, tone: str = "green") -> str:
    return f"""
    <div class="stat-card stat-{tone}">
        <div class="stat-value">{value}</div>
        <div class="stat-label">{label}</div>
        <div class="stat-hint">{hint}</div>
    </div>
    """


def render() -> None:
    komponen.page_header(
        "Dashboard",
        "Ringkasan perencanaan pembelajaran mendalam Anda.",
        "🏠",
    )

    profile = db.get_active_profile()
    if profile:
        st.markdown(
            f"""
            <div class="profile-strip">
                <div>
                    <div class="profile-strip-label">PROFIL AKTIF</div>
                    <div class="profile-strip-name">{profile.get('nama_sekolah') or 'Sekolah belum diisi'}</div>
                    <div class="profile-strip-sub">{profile.get('nama_guru') or 'Guru belum diisi'} · NIP {profile.get('nip') or '-'} · {profile.get('tahun_pelajaran') or '-'} · Semester {profile.get('semester') or '-'}</div>
                </div>
                <div class="profile-strip-actions"></div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        komponen.info(
            "Belum ada profil sekolah. Lengkapi profil agar identitas otomatis muncul pada setiap dokumen.",
            "warning",
        )
        if st.button("Isi Profil Sekolah", type="primary"):
            komponen.navigate("Profil Sekolah")

    jumlah_rpm = db.count_rpm()
    jumlah_mapel = db.count_mata_pelajaran()
    jumlah_dokumen = db.count_documents()
    jumlah_pembelajaran = db.count_pembelajaran()
    jumlah_bank = len(db.list_bank_cp())

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(_stat("Dokumen RPM", komponen.format_number(jumlah_rpm), "termasuk yang diarsipkan"), unsafe_allow_html=True)
    with col2:
        st.markdown(_stat("Mata Pelajaran", komponen.format_number(jumlah_mapel), "dari data pembelajaran", "amber"), unsafe_allow_html=True)
    with col3:
        st.markdown(_stat("Dokumen Tersimpan", komponen.format_number(jumlah_dokumen), "RPM dan LKPD", "blue"), unsafe_allow_html=True)
    with col4:
        st.markdown(_stat("Bank CP & ATP", komponen.format_number(jumlah_bank), "entri guru", "purple"), unsafe_allow_html=True)

    st.write("")
    kiri, kanan = st.columns([1.15, 1])

    with kiri:
        st.markdown("### Status AI Lokal")
        status = komponen.status_ollama()
        settings = db.get_settings()
        model = settings.get("ollama_model", "qwen2.5:7b")
        if status["ok"] and status["model_installed"]:
            komponen.info(f"Ollama aktif di {settings.get('ollama_url')} dengan model <b>{model}</b>.", "success")
        elif status["ok"]:
            komponen.info(
                f"Ollama aktif, tetapi model <b>{model}</b> belum terpasang. "
                "AI tidak dapat dipakai sampai model tersedia; aplikasi tetap berjalan dengan draf offline.",
                "warning",
            )
        else:
            komponen.info(
                f"Ollama tidak aktif: {status['message']} Aplikasi tetap dapat digunakan secara manual "
                "dengan draf offline.",
                "warning",
            )
        baris = st.columns(2)
        with baris[0]:
            if st.button("Buka Pengaturan AI", width="stretch"):
                komponen.navigate("Pengaturan AI")
        with baris[1]:
            if st.button("Periksa Ulang Koneksi", width="stretch"):
                komponen.reset_ollama_cache()
                st.rerun()

        st.write("")
        st.markdown("### Data Pembelajaran")
        st.caption(
            f"{jumlah_pembelajaran} data pembelajaran tersimpan. Buat data baru atau gunakan kembali "
            "data sebelumnya sebagai titik awal."
        )
        aksi1, aksi2 = st.columns(2)
        with aksi1:
            if st.button("＋ Data Pembelajaran", type="primary", width="stretch"):
                komponen.navigate("Data Pembelajaran")
        with aksi2:
            if st.button("Buka Generator RPM", width="stretch"):
                komponen.navigate("Generator RPM")

    with kanan:
        st.markdown("### Aktivitas Terakhir")
        aktivitas = db.list_activities(8)
        if not aktivitas:
            st.caption("Belum ada aktivitas. Aktivitas akan tercatat saat Anda menyimpan data atau membuat dokumen.")
        else:
            for item in aktivitas:
                waktu = (item.get("created_at") or "")[5:16]
                st.markdown(
                    f"""
                    <div class="activity-row">
                        <div class="activity-dot"></div>
                        <div class="activity-body">
                            <div class="activity-title">{item.get('aksi','')}</div>
                            <div class="activity-detail">{komponen.truncate(item.get('detail',''), 90)}</div>
                        </div>
                        <div class="activity-time">{waktu}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

    st.write("")
    st.markdown("### Alur yang Disarankan")
    langkah = st.columns(4)
    alur = [
        ("1", "Lengkapi profil", "Identitas sekolah dan guru otomatis masuk ke dokumen.", "Profil Sekolah"),
        ("2", "Isi data pembelajaran", "CP dan ATP diisi guru, bukan dibuat AI.", "Data Pembelajaran"),
        ("3", "Susun RPM bertahap", "Setiap bagian dibuat, diedit, lalu disetujui.", "Generator RPM"),
        ("4", "Validasi & ekspor", "Periksa konsistensi, lalu ekspor DOCX/PDF.", "Validasi RPM"),
    ]
    for kolom, (nomor, judul, teks, halaman) in zip(langkah, alur):
        with kolom:
            st.markdown(
                f"""
                <div class="mini-step">
                    <div class="mini-step-num">{nomor}</div>
                    <div class="mini-step-title">{judul}</div>
                    <div class="mini-step-text">{teks}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if st.button("Buka", key=f"alur_{nomor}", width="stretch"):
                komponen.navigate(halaman)

    st.write("")
    st.caption(
        "Catatan: aplikasi ini adalah alat bantu perencanaan. Dokumen yang dihasilkan tidak otomatis disahkan "
        "dan tidak menjamin pemenuhan seluruh ketentuan pemerintah. Guru tetap melakukan reviu dan penyesuaian."
    )
