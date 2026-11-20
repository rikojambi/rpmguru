"""Modul tahap Diferensiasi pembelajaran."""

from __future__ import annotations

from ai import generator
from ai.ollama_client import OllamaClient
from modules import editor


def generate(pembelajaran: dict, data: dict, options: dict, client: OllamaClient | None,
             use_ai: bool = True, rpm_id: int | None = None, desain: dict | None = None,
             pengalaman: dict | None = None):
    return generator.generate_diferensiasi(
        client, pembelajaran, desain or {}, pengalaman or {}, use_ai=use_ai, rpm_id=rpm_id
    )


def render_options(pembelajaran: dict, data: dict, key_prefix: str) -> dict:
    return {}


def render_editor(data: dict, prefix: str) -> dict:
    return editor.render_editor("diferensiasi", data, prefix)
