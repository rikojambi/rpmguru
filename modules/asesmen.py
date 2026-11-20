"""Modul Asesmen: tahap generator RPM dan halaman Generator Asesmen."""

from __future__ import annotations

import json

import streamlit as st

from ai import generator
from ai.ollama_client import OllamaClient
from database import db
from modules import editor, komponen
from modules.editor import ensure_structure


# ---------------------------------------------------------------------------
# Bagian untuk wizard RPM
# ---------------------------------------------------------------------------
def generate(pembelajaran: dict, data: dict, options: dict, client: OllamaClient | None,
             use_ai: bool = True, rpm_id: int | None = None, desain: dict | None = None):
    return generator.generate_asesmen(
        client, pembelajaran, desain or {}, use_ai=use_ai, rpm_id=rpm_id
    )


def render_options(pembelajaran: dict, data: dict, key_prefix: str) -> dict:
    return {}


def render_editor(data: dict, prefix: str) -> dict:
    return editor.render_editor("asesmen", data, prefix)


# ---------------------------------------------------------------------------
# Halaman mandiri: Generator Asesmen
# ---------------------------------------------------------------------------
def _select_rpm(key: str) -> dict | None:
    rows = db.list_rpm()
    if not rows:
        return None
    ids = [row["id"] for row in rows]
    pilih = st.selectbox(
        "Pilih dokumen RPM",
        ids,
        format_func=lambda x: next(
            (f"{r.get('judul') or 'RPM'} · {r.get('mata_pelajaran','')}" for r in rows if r["id"] == x),
            f"RPM #{x}",
        ),
        key=key,
    )
    return db.get_rpm(pilih)


def render() -> None:
    komponen.page_header(
        "Generator Asesmen",
        "Buat dan sunting asesmen awal, proses, dan akhir beserta rubrik. Selaras dengan tujuan pembelajaran.",
        "📋",
    )
    komponen.show_flash()

    rpm = _select_rpm("asesmen_page_rpm")
    if not rpm:
        komponen.empty_state(
            "Belum ada dokumen RPM",
            "Buat dokumen RPM terlebih dahulu melalui Data Pembelajaran atau Generator RPM.",
        )
        if st.button("Buka Generator RPM", type="primary"):
            komponen.navigate("Generator RPM")
        return

    pemb = db.get_pembelajaran(rpm.get("pembelajaran_id")) or {}
    data = ensure_structure(json.loads(rpm.get("data_json") or "{}"))
    profil = komponen.get_profile_for_document(pemb)
    st.markdown(
        komponen.tag(rpm.get("judul") or "RPM", "info")
        + komponen.tag(f"{pemb.get('mata_pelajaran','-')} · Kelas {pemb.get('kelas','-')}", "neutral")
        + komponen.badge_status(rpm.get("status", "draf")),
        unsafe_allow_html=True,
    )

    if not pemb:
        komponen.info(
            "Data pembelajaran yang terkait dokumen ini tidak ditemukan. Asesmen masih dapat disusun, "
            "tetapi konteksnya terbatas.",
            "warning",
        )

    if not data.get("desain", {}).get("tujuan"):
        komponen.info(
            "Desain/tujuan pembelajaran belum tersusun. Asesmen akan memakai TP dari data pembelajaran "
            "bila tersedia. Sebaiknya lengkapi tahap Desain terlebih dahulu.",
            "warning",
        )

    ai_siap, ai_pesan = komponen.ai_ready()
    k1, k2 = st.columns([1, 2])
    with k1:
        pakai_ai = st.toggle(
            "Gunakan AI lokal",
            value=ai_siap,
            disabled=not ai_siap,
            help=ai_pesan if not ai_siap else "AI hanya menerima data yang Anda masukkan.",
            key="asesmen_page_ai",
        )
    with k2:
        if not ai_siap:
            st.caption(f"AI tidak tersedia: {ai_pesan} Draf offline tetap dapat dibuat.")
        else:
            st.caption(f"Model: {db.get_setting('ollama_model', 'qwen2.5:7b')}")

    tombol = st.columns([1, 1, 2])
    with tombol[0]:
        buat = st.button("⚙️ Generate Asesmen", type="primary", width="stretch")
    with tombol[1]:
        buat_offline = st.button("Draf offline", width="stretch",
                                 help="Buat draf berbasis aturan tanpa AI.")
    with tombol[2]:
        st.caption("Hasil AI/offline adalah draf. Periksa kunci jawaban dan keselarasan dengan TP.")

    if buat or buat_offline:
        client = komponen.get_ai_client() if (buat and pakai_ai) else None
        with st.spinner("Menyusun asesmen..."):
            hasil = generator.generate_asesmen(
                client, pemb, data.get("desain", {}), use_ai=bool(client), rpm_id=rpm["id"]
            )
        data["asesmen"] = hasil.data
        db.save_rpm(rpm["id"], data)
        db.save_version(rpm["id"], data, f"Asesmen dibuat ({hasil.mode})")
        db.log_activity("Generate asesmen", rpm.get("judul", ""))
        komponen.set_flash(hasil.message, "success" if hasil.mode == "ai" else "warning")
        st.session_state["asesmen_page_rev"] = int(st.session_state.get("asesmen_page_rev", 0)) + 1
        st.rerun()

    rev = st.session_state.get("asesmen_page_rev", 0)
    st.write("")
    with st.expander("Ekspor instrumen asesmen ke Excel", expanded=False):
        from exports import excel_export

        try:
            payload = excel_export.build_asesmen_workbook(profil, pemb, data)
            komponen.download_bytes(
                "⬇️ Unduh XLSX Asesmen & Rubrik",
                payload,
                f"Asesmen_{pemb.get('mata_pelajaran','')}_{pemb.get('kelas','')}.xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                "asesmen_xlsx_dl",
            )
        except Exception as exc:
            st.error(f"Ekspor Excel gagal: {exc}")

    komponen.info(
        "Asesmen formatif (proses) adalah bagian dari perbaikan pembelajaran, bukan hanya penilaian akhir. "
        "Sesuaikan rubrik dan KKTP dengan keputusan guru/sekolah.",
        "info",
    )
    edited = render_editor(data.get("asesmen", {}), f"asesmen_page_{rpm['id']}_{rev}")
    st.write("")
    if st.button("💾 Simpan Asesmen", type="primary", width="stretch"):
        data["asesmen"] = edited
        db.save_rpm(rpm["id"], data)
        db.save_version(rpm["id"], data, "Asesmen disunting")
        db.log_activity("Simpan asesmen", rpm.get("judul", ""))
        komponen.set_flash("Asesmen tersimpan.", "success")
        st.session_state["asesmen_page_rev"] = rev + 1
        st.rerun()
