"""Modul tahap Desain pembelajaran."""

from __future__ import annotations

import streamlit as st

import config
from ai import generator
from ai.ollama_client import OllamaClient
from modules import editor


def render_options(pembelajaran: dict, data: dict, key_prefix: str) -> dict:
    existing = (data.get("model") or {}).get("nama", "")
    opsi = ["Otomatis (rekomendasi sistem)"] + config.MODEL_PEMBELAJARAN
    if existing and existing not in opsi:
        opsi.insert(1, existing)
    indeks = opsi.index(existing) if existing in opsi else 0
    pilihan = st.selectbox(
        "Praktik pedagogis",
        options=opsi,
        index=indeks,
        key=f"{key_prefix}_model_pilih",
        help="Pilih 'Otomatis' agar sistem merekomendasikan model sesuai materi dan tujuan.",
    )
    if pilihan in config.MODEL_DESKRIPSI:
        st.caption(config.MODEL_DESKRIPSI[pilihan])
    return {"model": None if pilihan.startswith("Otomatis") else pilihan}


def generate(pembelajaran: dict, data: dict, options: dict, client: OllamaClient | None,
             use_ai: bool = True, rpm_id: int | None = None, identifikasi: dict | None = None):
    return generator.generate_desain(
        client,
        pembelajaran,
        identifikasi or {},
        model_pilihan=options.get("model"),
        use_ai=use_ai,
        rpm_id=rpm_id,
    )


def render_editor(data: dict, prefix: str) -> dict:
    return editor.render_editor("desain", data, prefix)
