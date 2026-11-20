"""Generator RPM — Asisten Perencanaan Pembelajaran Mendalam.

Jalankan dengan:
    streamlit run app.py
"""

from __future__ import annotations

import importlib
import sys
import traceback
from pathlib import Path

import streamlit as st

# Pastikan folder proyek ada di sys.path ketika dijalankan dari lokasi lain
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import config  # noqa: E402

st.set_page_config(
    page_title=f"{config.APP_NAME} — Pembelajaran Mendalam",
    page_icon="📘",
    layout="wide",
    initial_sidebar_state="expanded",
)

from database import db  # noqa: E402
from modules import komponen  # noqa: E402

db.init_db()
komponen.inject_css()

NAV_ITEMS = [
    ("Dashboard", "modules.dashboard", "🏠"),
    ("Profil Sekolah", "modules.profil", "🏫"),
    ("Data Pembelajaran", "modules.pembelajaran", "📚"),
    ("Bank CP dan ATP", "modules.bank_cp", "🗂️"),
    ("Generator RPM", "modules.generator", "⚙️"),
    ("Generator LKPD", "modules.lkpd", "📝"),
    ("Generator Asesmen", "modules.asesmen", "📋"),
    ("Validasi RPM", "modules.validasi", "✅"),
    ("Arsip Dokumen", "modules.arsip", "🗄️"),
    ("Pengaturan AI", "modules.pengaturan_ai", "🤖"),
    ("Backup Database", "modules.backup", "💾"),
]
NAV_LABELS = [item[0] for item in NAV_ITEMS]
NAV_MAP = {item[0]: (item[1], item[2]) for item in NAV_ITEMS}
ICON_MAP = {item[0]: item[2] for item in NAV_ITEMS}


# ---------------------------------------------------------------------------
# Navigasi antarhalaman
# ---------------------------------------------------------------------------
if "_nav_request" in st.session_state:
    requested = st.session_state.pop("_nav_request")
    if requested in NAV_LABELS:
        st.session_state["nav_page"] = requested

if "nav_page" not in st.session_state:
    st.session_state["nav_page"] = "Dashboard"


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown(
        """
        <div class="sidebar-brand">
            <div class="sidebar-logo">
                <div class="sidebar-logo-mark">RPM</div>
                <div class="sidebar-logo-text">GENERATOR RPM<small>Pembelajaran Mendalam</small></div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    halaman = st.radio(
        "Navigasi",
        options=NAV_LABELS,
        format_func=lambda label: f"{ICON_MAP.get(label, '•')}  {label}",
        key="nav_page",
        label_visibility="collapsed",
    )

    st.markdown('<div class="sidebar-label">Profil aktif</div>', unsafe_allow_html=True)
    profil_aktif = db.get_active_profile()
    if profil_aktif:
        st.markdown(
            f"""
            <div class="sidebar-profile">
                <b>{profil_aktif.get('nama_sekolah') or 'Sekolah belum diisi'}</b><br>
                {profil_aktif.get('nama_guru') or 'Guru belum diisi'}<br>
                TA {profil_aktif.get('tahun_pelajaran') or '-'} · Semester {profil_aktif.get('semester') or '-'}
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("Ganti / edit profil", key="sidebar_profil_btn", width="stretch"):
            st.session_state["_nav_request"] = "Profil Sekolah"
            st.rerun()
    else:
        st.caption("Belum ada profil sekolah.")
        if st.button("Isi profil sekarang", key="sidebar_isi_profil", width="stretch"):
            st.session_state["_nav_request"] = "Profil Sekolah"
            st.rerun()

    st.markdown('<div class="sidebar-label">Status AI lokal</div>', unsafe_allow_html=True)
    status = komponen.status_ollama()
    pengaturan = db.get_settings()
    model_aktif = pengaturan.get("ollama_model", "qwen2.5:7b")
    if status["ok"] and status["model_installed"]:
        dot, teks = "dot-ok", f"{model_aktif} siap"
    elif status["ok"]:
        dot, teks = "dot-warn", "Model belum terpasang"
    else:
        dot, teks = "dot-off", "Ollama tidak aktif"
    st.markdown(
        f'<div class="sidebar-status"><span class="dot {dot}"></span> {teks}</div>',
        unsafe_allow_html=True,
    )
    st.caption("Tanpa AI, generator tetap berjalan dengan draf offline yang dapat diedit.")
    if st.button("Pengaturan AI", key="sidebar_ai_btn", width="stretch"):
        st.session_state["_nav_request"] = "Pengaturan AI"
        st.rerun()

    st.markdown("---")
    st.caption(f"Versi {config.APP_VERSION} · Data lokal (SQLite)")
    st.caption("Bukan pengganti pengesahan resmi. Guru tetap melakukan reviu.")


# ---------------------------------------------------------------------------
# Dispatch halaman
# ---------------------------------------------------------------------------
module_path, _ = NAV_MAP.get(halaman, ("modules.dashboard", "🏠"))
try:
    module = importlib.import_module(module_path)
    render = getattr(module, "render")
    render()
except ModuleNotFoundError as exc:
    st.error(
        "Modul halaman belum tersedia. Pastikan seluruh berkas proyek tersalin dengan lengkap."
    )
    st.caption(f"Detail: {exc}")
except Exception:
    st.error("Terjadi kesalahan saat memuat halaman ini. Data Anda tidak terhapus.")
    with st.expander("Detail kesalahan (untuk perbaikan)"):
        st.code(traceback.format_exc())
    st.caption("Coba muat ulang halaman. Bila masalah berlanjut, cadangkan database terlebih dahulu.")
