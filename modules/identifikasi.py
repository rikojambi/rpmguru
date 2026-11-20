"""Modul tahap Identifikasi (kesiapan, materi, dimensi profil lulusan)."""

from __future__ import annotations

from ai import generator
from ai.ollama_client import OllamaClient
from modules import editor


def render_options(pembelajaran: dict, data: dict, key_prefix: str) -> dict:
    import streamlit as st

    existing = [row.get("nama") for row in (data.get("dimensi") or []) if row.get("nama")]
    pilihan = st.multiselect(
        "Dimensi profil lulusan yang relevan",
        options=config_dimensi(),
        default=[d for d in existing if d in config_dimensi()],
        key=f"{key_prefix}_dimensi_pilih",
        help="Pilih 1-4 dimensi yang benar-benar relevan. Tidak semua dimensi harus muncul di setiap pertemuan.",
    )
    st.caption(
        "Kosongkan bila ingin sistem mengusulkan 2-4 dimensi berdasarkan materi dan tujuan. "
        "Guru tetap dapat mengubah hasilnya pada tabel di bawah."
    )
    return {"dimensi": pilihan}


def config_dimensi() -> list[str]:
    import config

    return config.DIMENSI_PROFIL


def generate(pembelajaran: dict, data: dict, options: dict, client: OllamaClient | None,
             use_ai: bool = True, rpm_id: int | None = None):
    return generator.generate_identifikasi(
        client,
        pembelajaran,
        dimensi_pilihan=options.get("dimensi") or None,
        use_ai=use_ai,
        rpm_id=rpm_id,
    )


def render_editor(data: dict, prefix: str) -> dict:
    return editor.render_editor("identifikasi", data, prefix)
