"""Modul LKPD: tahap generator RPM dan halaman Generator LKPD."""

from __future__ import annotations

import json

import streamlit as st

from ai import generator
from ai.ollama_client import OllamaClient
from database import db
from modules import editor, komponen
from modules.editor import ensure_structure


def generate_step(pembelajaran: dict, data: dict, options: dict, client: OllamaClient | None,
                  use_ai: bool = True, rpm_id: int | None = None, desain: dict | None = None,
                  pengalaman: dict | None = None):
    return generator.generate_lkpd(
        client, pembelajaran, desain or {}, pengalaman or {}, use_ai=use_ai, rpm_id=rpm_id
    )


def render_options(pembelajaran: dict, data: dict, key_prefix: str) -> dict:
    return {}


def render_editor_step(data: dict, prefix: str) -> dict:
    return editor.render_editor("lkpd", data, prefix)


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
        "Generator LKPD",
        "Susun Lembar Kerja Peserta Didik dari RPM, lalu edit dan ekspor.",
        "📝",
    )
    komponen.show_flash()

    rpm = _select_rpm("lkpd_page_rpm")
    if not rpm:
        komponen.empty_state(
            "Belum ada dokumen RPM",
            "LKPD dibuat berdasarkan RPM. Buat RPM terlebih dahulu melalui Generator RPM.",
        )
        if st.button("Buka Generator RPM", type="primary"):
            komponen.navigate("Generator RPM")
        return

    pemb = db.get_pembelajaran(rpm.get("pembelajaran_id")) or {}
    data = ensure_structure(json.loads(rpm.get("data_json") or "{}"))
    profil = komponen.get_profile_for_document(pemb)

    st.markdown(
        komponen.tag(rpm.get("judul") or "RPM", "info")
        + komponen.tag(f"{pemb.get('mata_pelajaran','-')} · Kelas {pemb.get('kelas','-')}", "neutral"),
        unsafe_allow_html=True,
    )

    if not data.get("desain", {}).get("tujuan"):
        komponen.info("Tujuan pembelajaran belum tersedia pada RPM. LKPD akan tetap dibuat dari data pembelajaran.", "warning")

    ai_siap, ai_pesan = komponen.ai_ready()
    k1, k2 = st.columns([1, 2])
    with k1:
        pakai_ai = st.toggle(
            "Gunakan AI lokal", value=ai_siap, disabled=not ai_siap,
            help=ai_pesan if not ai_siap else "AI menerima konteks RPM yang tersimpan.",
            key="lkpd_page_ai",
        )
    with k2:
        if not ai_siap:
            st.caption(f"AI tidak tersedia: {ai_pesan} Draf offline tetap tersedia.")
        else:
            st.caption(f"Model: {db.get_setting('ollama_model', 'qwen2.5:7b')}")

    tombol = st.columns([1, 1, 2])
    with tombol[0]:
        buat = st.button("⚙️ Generate LKPD", type="primary", width="stretch")
    with tombol[1]:
        buat_offline = st.button("Draf offline", width="stretch")
    with tombol[2]:
        st.caption("Periksa keterbacaan, kesesuaian jenjang, dan kebenaran konsep sebelum dibagikan ke siswa.")

    if buat or buat_offline:
        client = komponen.get_ai_client() if (buat and pakai_ai) else None
        with st.spinner("Menyusun LKPD..."):
            hasil = generator.generate_lkpd(
                client, pemb, data.get("desain", {}), data.get("pengalaman", {}),
                use_ai=bool(client), rpm_id=rpm["id"],
            )
        data["lkpd"] = hasil.data
        db.save_rpm(rpm["id"], data)
        db.save_version(rpm["id"], data, f"LKPD dibuat ({hasil.mode})")
        db.save_lkpd(rpm["id"], hasil.data, hasil.data.get("judul") or f"LKPD {pemb.get('mata_pelajaran','')}")
        db.log_activity("Generate LKPD", rpm.get("judul", ""))
        komponen.set_flash(hasil.message, "success" if hasil.mode == "ai" else "warning")
        st.session_state["lkpd_page_rev"] = int(st.session_state.get("lkpd_page_rev", 0)) + 1
        st.rerun()

    rev = st.session_state.get("lkpd_page_rev", 0)
    st.write("")
    with st.expander("Ekspor LKPD", expanded=False):
        from exports import docx_export

        kolom = st.columns(2)
        try:
            docx_bytes = docx_export.build_lkpd_docx(
                profil, pemb, data.get("lkpd", {}), data
            )
            with kolom[0]:
                komponen.download_bytes(
                    "⬇️ LKPD DOCX",
                    docx_bytes,
                    f"LKPD_{pemb.get('mata_pelajaran','')}_{pemb.get('kelas','')}.docx",
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    "lkpd_docx_dl",
                )
        except Exception as exc:
            st.error(f"Ekspor DOCX gagal: {exc}")
        try:
            from exports import pdf_export

            pdf_bytes = pdf_export.build_lkpd_pdf(profil, pemb, data.get("lkpd", {}), data)
            with kolom[1]:
                komponen.download_bytes(
                    "⬇️ LKPD PDF",
                    pdf_bytes,
                    f"LKPD_{pemb.get('mata_pelajaran','')}_{pemb.get('kelas','')}.pdf",
                    "application/pdf",
                    "lkpd_pdf_dl",
                )
        except Exception as exc:
            st.error(f"Ekspor PDF gagal: {exc}")

    edited = render_editor_step(data.get("lkpd", {}), f"lkpd_page_{rpm['id']}_{rev}")
    st.write("")
    if st.button("💾 Simpan LKPD", type="primary", width="stretch"):
        data["lkpd"] = edited
        db.save_rpm(rpm["id"], data)
        db.save_version(rpm["id"], data, "LKPD disunting")
        db.save_lkpd(rpm["id"], edited, edited.get("judul") or "LKPD")
        db.log_activity("Simpan LKPD", rpm.get("judul", ""))
        komponen.set_flash("LKPD tersimpan.", "success")
        st.session_state["lkpd_page_rev"] = rev + 1
        st.rerun()
