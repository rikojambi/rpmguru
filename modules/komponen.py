"""Komponen antarmuka dan utilitas bersama."""

from __future__ import annotations

import io
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

import config
from ai.ollama_client import OllamaClient
from database import db


# ---------------------------------------------------------------------------
# AI dan status
# ---------------------------------------------------------------------------
def get_ai_client() -> OllamaClient:
    settings = db.get_settings()
    return OllamaClient(
        base_url=settings.get("ollama_url", "http://localhost:11434"),
        model=settings.get("ollama_model", "qwen2.5:7b"),
        temperature=settings.get("temperature", "0.4"),
        num_predict=settings.get("num_predict", "2000"),
        timeout=settings.get("timeout", "180"),
    )


@st.cache_data(ttl=20, show_spinner=False)
def cek_ollama(url: str, model: str) -> dict:
    client = OllamaClient(base_url=url, model=model)
    ok, message = client.is_available()
    models: list[str] = []
    if ok:
        try:
            models = client.list_models()
        except Exception as exc:  # pragma: no cover - defensif
            message = str(exc)
    return {
        "ok": ok,
        "message": message,
        "models": models,
        "model_installed": any(m == model or m.split(":")[0] == model.split(":")[0] for m in models) if ok else False,
    }


def status_ollama() -> dict:
    settings = db.get_settings()
    return cek_ollama(settings.get("ollama_url", "http://localhost:11434"), settings.get("ollama_model", "qwen2.5:7b"))


def reset_ollama_cache() -> None:
    cek_ollama.clear()


def ai_ready() -> tuple[bool, str]:
    status = status_ollama()
    if not status["ok"]:
        return False, status["message"]
    if not status["model_installed"]:
        return False, "Model belum terpasang di Ollama."
    return True, "Siap"


# ---------------------------------------------------------------------------
# Gaya dan komponen visual
# ---------------------------------------------------------------------------
def inject_css() -> None:
    css_path = config.ASSETS_DIR / "style.css"
    if css_path.exists():
        st.markdown(f"<style>{css_path.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)


def page_header(title: str, subtitle: str = "", icon: str = "") -> None:
    st.markdown(
        f"""
        <div class="page-head">
            <div class="page-head-icon">{icon or "◆"}</div>
            <div>
                <h1>{title}</h1>
                <p>{subtitle}</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def card_open(title: str = "", subtitle: str = "") -> None:
    st.markdown('<div class="rpm-card">', unsafe_allow_html=True)
    if title:
        st.markdown(f'<div class="rpm-card-title">{title}</div>', unsafe_allow_html=True)
    if subtitle:
        st.markdown(f'<div class="rpm-card-sub">{subtitle}</div>', unsafe_allow_html=True)


def card_close() -> None:
    st.markdown("</div>", unsafe_allow_html=True)


def tag(text: str, tone: str = "neutral") -> str:
    return f'<span class="tag tag-{tone}">{text}</span>'


def ai_badge(mode: str = "", model: str = "") -> None:
    if mode == "ai":
        st.markdown(
            tag(f"AI lokal: {model or 'Ollama'}", "ai") + " " + tag("Periksa & edit sebelum digunakan", "warn"),
            unsafe_allow_html=True,
        )
    elif mode == "offline":
        st.markdown(
            tag("Draf offline (tanpa AI)", "offline") + " " + tag("Wajib diperiksa guru", "warn"),
            unsafe_allow_html=True,
        )


def info(message: str, tone: str = "info") -> None:
    icons = {"info": "ℹ️", "success": "✅", "warning": "⚠️", "error": "⛔"}
    st.markdown(
        f'<div class="notice notice-{tone}">{icons.get(tone, "ℹ️")} {message}</div>',
        unsafe_allow_html=True,
    )


def empty_state(title: str, message: str) -> None:
    st.markdown(
        f"""
        <div class="empty-state">
            <div class="empty-icon">◇</div>
            <h3>{title}</h3>
            <p>{message}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def badge_status(status: str) -> str:
    mapping = {
        "draf": ("Draf", "warn"),
        "ditinjau": ("Ditinjau", "info"),
        "disetujui": ("Disetujui", "ok"),
        "final": ("Final", "ok"),
    }
    label, tone = mapping.get(status, (status or "Draf", "neutral"))
    return tag(label, tone)


# ---------------------------------------------------------------------------
# Navigasi
# ---------------------------------------------------------------------------
def navigate(page: str) -> None:
    st.session_state["_nav_request"] = page
    st.rerun()


def set_flash(message: str, tone: str = "success") -> None:
    st.session_state["_flash"] = (message, tone)


def show_flash() -> None:
    flash = st.session_state.pop("_flash", None)
    if flash:
        message, tone = flash
        fungsi = {"success": st.success, "warning": st.warning, "error": st.error}
        fungsi.get(tone, st.info)(message)


def set_active_pembelajaran(pembelajaran_id: int | None) -> None:
    st.session_state["active_pembelajaran"] = pembelajaran_id


def active_pembelajaran() -> dict | None:
    return db.get_pembelajaran(st.session_state.get("active_pembelajaran"))


# ---------------------------------------------------------------------------
# Profil
# ---------------------------------------------------------------------------
def profile_label(profile: dict) -> str:
    sekolah = profile.get("nama_sekolah") or "Sekolah belum diisi"
    guru = profile.get("nama_guru") or "Guru belum diisi"
    return f"{sekolah} — {guru}"


def get_profile_for_document(pembelajaran: dict | None = None) -> dict:
    if pembelajaran and pembelajaran.get("profile_id"):
        row = db.get_profile(pembelajaran["profile_id"])
        if row:
            return row
    active = db.get_active_profile()
    if active:
        return active
    return {
        "nama_sekolah": "", "nama_guru": "", "nip": "", "nama_kepala_sekolah": "",
        "npsn": "", "alamat": "", "kabupaten": "", "provinsi": "",
        "tahun_pelajaran": db.get_setting("tahun_pelajaran", "2025/2026"),
        "semester": db.get_setting("semester", "Ganjil"),
    }


# ---------------------------------------------------------------------------
# Berkas: unggah, baca, simpan
# ---------------------------------------------------------------------------
def safe_filename(name: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", name or "berkas")
    return cleaned[:120]


def save_uploaded_file(uploaded, prefix: str = "upload") -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    target = config.UPLOAD_DIR / f"{prefix}_{stamp}_{safe_filename(uploaded.name)}"
    target.write_bytes(uploaded.getvalue())
    return target


def read_docx_bytes(payload: bytes) -> str:
    from docx import Document

    document = Document(io.BytesIO(payload))
    parts: list[str] = []
    for paragraph in document.paragraphs:
        text = paragraph.text.strip()
        if text:
            parts.append(text)
    for table in document.tables:
        for row in table.rows:
            cells = [cell.text.strip() for cell in row.cells]
            if any(cells):
                parts.append(" | ".join(cells))
    return "\n".join(parts)


def read_excel_bytes(payload: bytes) -> dict[str, pd.DataFrame]:
    excel = pd.ExcelFile(io.BytesIO(payload))
    data = {}
    for sheet in excel.sheet_names:
        try:
            data[sheet] = excel.parse(sheet)
        except Exception:
            continue
    return data


def dataframe_to_text(df: pd.DataFrame) -> str:
    if df is None or df.empty:
        return ""
    cleaned = df.fillna("")
    lines = []
    headers = [str(c).strip() for c in cleaned.columns]
    for _, row in cleaned.iterrows():
        values = [str(v).strip() for v in row.tolist()]
        if not any(values):
            continue
        if any(headers):
            line = "; ".join(f"{h}: {v}" for h, v in zip(headers, values) if h and v)
        else:
            line = "; ".join(v for v in values if v)
        lines.append(line)
    return "\n".join(lines)


def parse_cp_atp_text(text: str) -> dict:
    """Memisahkan CP dan ATP dari teks bebas dengan penanda yang umum."""
    if not text:
        return {"cp": "", "atp": ""}
    normalized = text.replace("\r\n", "\n").strip()
    cp_match = re.search(r"(?im)^\s*(?:capaian pembelajaran|cp)\s*[:：-]?\s*", normalized)
    atp_match = re.search(r"(?im)^\s*(?:alur tujuan pembelajaran|atp)\s*[:：-]?\s*", normalized)
    cp, atp = "", ""
    if cp_match and atp_match:
        if cp_match.start() < atp_match.start():
            cp = normalized[cp_match.end():atp_match.start()].strip(" :：-\n")
            atp = normalized[atp_match.end():].strip(" :：-\n")
        else:
            atp = normalized[atp_match.end():cp_match.start()].strip(" :：-\n")
            cp = normalized[cp_match.end():].strip(" :：-\n")
    elif cp_match:
        cp = normalized[cp_match.end():].strip(" :：-\n")
    elif atp_match:
        atp = normalized[atp_match.end():].strip(" :：-\n")
    else:
        cp = normalized
    return {"cp": cp, "atp": atp}


def read_cp_atp_upload(uploaded) -> tuple[dict, str]:
    """Membaca Word/Excel/TXT dan mengembalikan (hasil, keterangan)."""
    name = uploaded.name.lower()
    payload = uploaded.getvalue()
    text = ""
    if name.endswith(".docx"):
        text = read_docx_bytes(payload)
    elif name.endswith(".txt") or name.endswith(".md"):
        text = payload.decode("utf-8", errors="replace")
    elif name.endswith((".xlsx", ".xlsm")):
        frames = read_excel_bytes(payload)
        chunks = []
        for sheet, frame in frames.items():
            chunks.append(f"## {sheet}")
            chunks.append(dataframe_to_text(frame))
        text = "\n".join(chunks)
    elif name.endswith(".csv"):
        try:
            frame = pd.read_csv(io.BytesIO(payload))
        except UnicodeDecodeError:
            frame = pd.read_csv(io.BytesIO(payload), encoding="latin-1")
        text = dataframe_to_text(frame)
    else:
        return {"cp": "", "atp": ""}, "Format berkas tidak didukung. Gunakan DOCX, XLSX, CSV, atau TXT."
    parsed = parse_cp_atp_text(text)
    return parsed, f"Teks terbaca: {len(text)} karakter."


# ---------------------------------------------------------------------------
# Unduhan
# ---------------------------------------------------------------------------
def download_bytes(label: str, payload: bytes, filename: str, mime: str, key: str) -> None:
    st.download_button(
        label=label,
        data=payload,
        file_name=safe_filename(filename),
        mime=mime,
        key=key,
        width="stretch",
    )


# ---------------------------------------------------------------------------
# Konfirmasi
# ---------------------------------------------------------------------------
def confirm_action(label: str, key: str, warning: str) -> bool:
    centang = st.checkbox(warning, key=key)
    return st.button(label, disabled=not centang, key=f"{key}_btn", type="secondary")


# ---------------------------------------------------------------------------
# Format
# ---------------------------------------------------------------------------
def format_number(value: Any) -> str:
    try:
        return f"{int(value):,}".replace(",", ".")
    except (TypeError, ValueError):
        return "0"


def truncate(text: str, length: int = 80) -> str:
    text = (text or "").strip().replace("\n", " ")
    return text if len(text) <= length else text[: length - 1] + "…"


def copy_to_temp(source: Path) -> Path:
    target = config.UPLOAD_DIR / f"restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{source.name}"
    shutil.copy2(source, target)
    return target
