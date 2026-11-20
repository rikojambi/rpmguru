"""Skema bagian RPM dan editor generik berbasis Streamlit."""

from __future__ import annotations

import copy
from typing import Any

import pandas as pd
import streamlit as st

from database import db
from modules import komponen


# Metadata tahapan RPM
STEPS = [
    {
        "key": "identifikasi",
        "label": "1. Identifikasi",
        "short": "Identifikasi",
        "icon": "🔎",
        "description": "Kesiapan peserta didik, karakteristik materi, dan dimensi profil lulusan.",
    },
    {
        "key": "desain",
        "label": "2. Desain",
        "short": "Desain",
        "icon": "🧭",
        "description": "Tujuan pembelajaran, model pedagogis, kemitraan, lingkungan, digital, dan prinsip.",
    },
    {
        "key": "pengalaman",
        "label": "3. Pengalaman Belajar",
        "short": "Pengalaman",
        "icon": "🔄",
        "description": "Memahami, mengaplikasi, dan merefleksi beserta bukti ketercapaian.",
    },
    {
        "key": "asesmen",
        "label": "4. Asesmen",
        "short": "Asesmen",
        "icon": "📋",
        "description": "Asesmen awal, proses, dan akhir beserta instrumen dan rubrik.",
    },
    {
        "key": "diferensiasi",
        "label": "5. Diferensiasi",
        "short": "Diferensiasi",
        "icon": "🪜",
        "description": "Tiga tingkat dukungan: perlu bimbingan, berkembang, dan mahir.",
    },
    {
        "key": "lkpd",
        "label": "6. LKPD",
        "short": "LKPD",
        "icon": "📝",
        "description": "Lembar kerja peserta didik berbasis pengalaman belajar.",
    },
    {
        "key": "refleksi",
        "label": "7. Refleksi",
        "short": "Refleksi",
        "icon": "🪞",
        "description": "Refleksi peserta didik dan guru.",
    },
]

STEP_KEYS = [step["key"] for step in STEPS]


# ---------------------------------------------------------------------------
# Utilitas path
# ---------------------------------------------------------------------------
def get_path(data: dict, path: str) -> Any:
    current: Any = data
    for part in path.split("."):
        if isinstance(current, dict):
            current = current.get(part, "")
        else:
            return ""
    return current


def set_path(data: dict, path: str, value: Any) -> None:
    parts = path.split(".")
    current = data
    for part in parts[:-1]:
        if not isinstance(current.get(part), dict):
            current[part] = {}
        current = current[part]
    current[parts[-1]] = value


# ---------------------------------------------------------------------------
# Spesifikasi bagian
# ---------------------------------------------------------------------------
SECTION_SPECS: dict[str, list[dict]] = {
    "identifikasi": [
        {
            "title": "A. Kesiapan Peserta Didik",
            "hint": "Gunakan data yang benar-benar diketahui. Tandai bagian yang masih perlu dipetakan melalui asesmen awal.",
            "fields": [
                {"path": "kesiapan.pengetahuan_awal", "label": "Pengetahuan awal", "type": "long"},
                {"path": "kesiapan.tingkat_pemahaman", "label": "Tingkat pemahaman", "type": "long"},
                {"path": "kesiapan.keterampilan_awal", "label": "Keterampilan awal", "type": "long"},
                {"path": "kesiapan.kesulitan_belajar", "label": "Kesulitan belajar", "type": "long"},
                {"path": "kesiapan.kebutuhan_dukungan", "label": "Kebutuhan dukungan", "type": "long"},
            ],
        },
        {
            "title": "B. Karakteristik Materi",
            "fields": [
                {"path": "materi.jenis_pengetahuan", "label": "Jenis pengetahuan (faktual/konseptual/prosedural/metakognitif)", "type": "text"},
                {"path": "materi.konsep_utama", "label": "Konsep utama (satu per baris)", "type": "lines"},
                {"path": "materi.keterkaitan", "label": "Keterkaitan antarmateri", "type": "long"},
                {"path": "materi.penerapan", "label": "Penerapan dalam kehidupan nyata", "type": "long"},
                {"path": "materi.potensi_kontekstual", "label": "Potensi pembelajaran kontekstual", "type": "long"},
            ],
        },
        {
            "title": "C. Dimensi Profil Lulusan",
            "hint": "Pilih dimensi yang relevan saja. Alasan dan wujud aktivitas harus konkret.",
            "tables": [
                {
                    "path": "dimensi",
                    "label": "Dimensi yang dikembangkan",
                    "columns": [
                        ("nama", "Dimensi", "medium"),
                        ("alasan", "Alasan pemilihan", "large"),
                        ("wujud_aktivitas", "Wujud dalam aktivitas siswa", "large"),
                    ],
                }
            ],
        },
        {
            "title": "Catatan Identifikasi",
            "fields": [{"path": "catatan", "label": "Catatan untuk guru", "type": "long"}],
        },
    ],
    "desain": [
        {
            "title": "A. Tujuan Pembelajaran",
            "hint": "Gunakan kata kerja operasional, muat kompetensi dan konteks, serta selaraskan dengan asesmen.",
            "tables": [
                {
                    "path": "tujuan",
                    "label": "Tujuan dan indikator",
                    "columns": [
                        ("tp", "Tujuan Pembelajaran", "large"),
                        ("indikator", "Indikator ketercapaian", "large"),
                        ("asesmen", "Asesmen yang selaras", "medium"),
                    ],
                }
            ],
        },
        {
            "title": "B. Praktik Pedagogis",
            "fields": [
                {"path": "model.nama", "label": "Model pembelajaran", "type": "text"},
                {"path": "model.alasan", "label": "Alasan pemilihan model", "type": "long"},
                {"path": "model.sintaks", "label": "Sintaks/langkah model (satu per baris)", "type": "lines"},
            ],
        },
        {
            "title": "C. Kemitraan Pembelajaran",
            "tables": [
                {
                    "path": "kemitraan",
                    "label": "Kemitraan",
                    "columns": [("pihak", "Pihak", "medium"), ("peran", "Peran konkret", "large")],
                }
            ],
        },
        {
            "title": "D. Lingkungan Pembelajaran",
            "fields": [{"path": "lingkungan", "label": "Lingkungan belajar (satu per baris)", "type": "lines"}],
        },
        {
            "title": "E. Pemanfaatan Digital",
            "hint": "Sesuaikan dengan fasilitas sekolah. Jangan mewajibkan internet bila koneksi terbatas.",
            "tables": [
                {
                    "path": "digital",
                    "label": "Alat dan pemanfaatan",
                    "columns": [("alat", "Alat/media", "medium"), ("pemanfaatan", "Pemanfaatan", "large")],
                }
            ],
        },
        {
            "title": "F. Prinsip Pembelajaran",
            "hint": "Tuliskan wujud konkret, bukan hanya nama prinsip.",
            "tables": [
                {
                    "path": "prinsip",
                    "label": "Prinsip dan wujud",
                    "columns": [("prinsip", "Prinsip", "small"), ("wujud", "Wujud dalam pembelajaran", "large")],
                }
            ],
        },
        {
            "title": "Catatan Desain",
            "fields": [{"path": "catatan", "label": "Catatan untuk guru", "type": "long"}],
        },
    ],
    "pengalaman": [],
    "asesmen": [],
    "diferensiasi": [
        {
            "title": "Ringkasan Diferensiasi",
            "fields": [{"path": "ringkasan", "label": "Prinsip dan strategi diferensiasi", "type": "long"}],
        },
        {
            "title": "Tiga Tingkat Dukungan",
            "hint": "Satu pembelajaran inti, dengan variasi dukungan dan produk. Tidak perlu tiga rencana terpisah.",
            "tables": [
                {
                    "path": "tingkat",
                    "label": "Tingkat dukungan",
                    "columns": [
                        ("tingkat", "Tingkat", "small"),
                        ("kesiapan", "Ciri kesiapan", "medium"),
                        ("kompleksitas", "Kompleksitas tugas", "medium"),
                        ("scaffolding", "Scaffolding", "medium"),
                        ("sumber", "Variasi sumber", "medium"),
                        ("pengelompokan", "Pengelompokan", "medium"),
                        ("produk", "Pilihan produk", "medium"),
                    ],
                }
            ],
        },
        {
            "title": "Catatan Pelaksanaan",
            "fields": [{"path": "catatan", "label": "Catatan untuk guru", "type": "long"}],
        },
    ],
    "lkpd": [
        {
            "title": "Identitas dan Tujuan",
            "fields": [
                {"path": "judul", "label": "Judul LKPD", "type": "text"},
                {"path": "identitas", "label": "Identitas peserta didik", "type": "long"},
                {"path": "tujuan", "label": "Tujuan pembelajaran", "type": "long"},
                {"path": "petunjuk", "label": "Petunjuk pengerjaan", "type": "long"},
            ],
        },
        {
            "title": "Permasalahan dan Aktivitas",
            "fields": [
                {"path": "masalah", "label": "Permasalahan kontekstual", "type": "long"},
                {"path": "memahami", "label": "Aktivitas memahami", "type": "long"},
                {"path": "mengaplikasi", "label": "Aktivitas mengaplikasi", "type": "long"},
                {"path": "merefleksi", "label": "Aktivitas merefleksi", "type": "long"},
                {"path": "pertanyaan", "label": "Pertanyaan analisis (satu per baris)", "type": "lines"},
            ],
        },
        {
            "title": "Kesimpulan dan Penilaian",
            "fields": [
                {"path": "kesimpulan", "label": "Panduan kesimpulan", "type": "long"},
                {"path": "penilaian", "label": "Penilaian", "type": "long"},
            ],
        },
    ],
    "refleksi": [
        {
            "title": "Refleksi Peserta Didik",
            "hint": "Pilih 2-3 pertanyaan yang paling relevan agar waktu refleksi tidak berlebihan.",
            "fields": [{"path": "siswa", "label": "Pertanyaan refleksi siswa (satu per baris)", "type": "lines"}],
        },
        {
            "title": "Refleksi Guru",
            "fields": [{"path": "guru", "label": "Pertanyaan refleksi guru (satu per baris)", "type": "lines"}],
        },
        {
            "title": "Catatan",
            "fields": [{"path": "catatan", "label": "Catatan penggunaan", "type": "long"}],
        },
    ],
}


def _tahap_fields(judul: str, key_prefix: str) -> dict:
    return {
        "title": judul,
        "fields": [
            {"path": f"{key_prefix}.aktivitas_guru", "label": "Aktivitas guru", "type": "long"},
            {"path": f"{key_prefix}.aktivitas_siswa", "label": "Aktivitas peserta didik", "type": "long"},
            {"path": f"{key_prefix}.alokasi", "label": "Alokasi waktu", "type": "text"},
            {"path": f"{key_prefix}.media", "label": "Media dan sumber belajar", "type": "long"},
            {"path": f"{key_prefix}.dimensi", "label": "Dimensi profil lulusan", "type": "text"},
            {"path": f"{key_prefix}.prinsip", "label": "Prinsip pembelajaran yang tampak", "type": "long"},
            {"path": f"{key_prefix}.bukti", "label": "Bukti ketercapaian", "type": "long"},
        ],
    }


SECTION_SPECS["pengalaman"] = [
    _tahap_fields("A. Memahami", "memahami"),
    _tahap_fields("B. Mengaplikasi", "mengaplikasi"),
    _tahap_fields("C. Merefleksi", "merefleksi"),
    {
        "title": "Catatan",
        "fields": [{"path": "catatan", "label": "Catatan alokasi dan pelaksanaan", "type": "long"}],
    },
]


def _asesmen_group(judul: str, key_prefix: str, hint: str = "") -> dict:
    return {
        "title": judul,
        "hint": hint,
        "fields": [
            {"path": f"{key_prefix}.tujuan", "label": "Tujuan asesmen", "type": "long"},
            {"path": f"{key_prefix}.instrumen", "label": "Instrumen", "type": "long"},
            {"path": f"{key_prefix}.soal", "label": "Soal/tugas (satu per baris)", "type": "lines"},
            {"path": f"{key_prefix}.kunci", "label": "Kunci/rambu jawaban (satu per baris)", "type": "lines"},
            {"path": f"{key_prefix}.pedoman", "label": "Pedoman penskoran", "type": "long"},
            {"path": f"{key_prefix}.kktp", "label": "Kriteria ketercapaian tujuan pembelajaran (KKTP)", "type": "long"},
        ],
        "tables": [
            {
                "path": f"{key_prefix}.rubrik",
                "label": "Rubrik penilaian",
                "columns": [("kriteria", "Kriteria", "medium"), ("deskripsi", "Deskripsi capaian", "large")],
            }
        ],
    }


SECTION_SPECS["asesmen"] = [
    _asesmen_group("A. Asesmen Awal", "awal", "Diagnostik kognitif, nonkognitif, dan pertanyaan pemantik."),
    _asesmen_group("B. Asesmen Proses (Formatif)", "proses", "Observasi, LKPD, kuis, dan umpan balik sebagai bagian proses perbaikan."),
    _asesmen_group("C. Asesmen Akhir (Sumatif)", "akhir", "Tes, praktik, produk, presentasi, atau portofolio."),
    {
        "title": "Catatan Asesmen",
        "fields": [{"path": "catatan", "label": "Catatan untuk guru", "type": "long"}],
    },
]


# ---------------------------------------------------------------------------
# Struktur kosong
# ---------------------------------------------------------------------------
def _empty_for_spec(spec: list[dict]) -> dict:
    data: dict = {}
    for group in spec:
        for field in group.get("fields", []):
            set_path(data, field["path"], [] if field["type"] == "lines" else "")
        for table in group.get("tables", []):
            set_path(data, table["path"], [])
    return data


def empty_section(step: str) -> dict:
    return _empty_for_spec(SECTION_SPECS.get(step, []))


def empty_all() -> dict:
    return {step: empty_section(step) for step in STEP_KEYS}


def ensure_structure(data: dict | None) -> dict:
    data = copy.deepcopy(data) if isinstance(data, dict) else {}
    for step in STEP_KEYS:
        existing = data.get(step)
        if not isinstance(existing, dict):
            existing = {}
        base = empty_section(step)
        for group in SECTION_SPECS.get(step, []):
            for field in group.get("fields", []):
                if get_path(existing, field["path"]) in (None, ""):
                    set_path(existing, field["path"], [] if field["type"] == "lines" else "")
            for table in group.get("tables", []):
                current = get_path(existing, table["path"])
                if not isinstance(current, list):
                    set_path(existing, table["path"], [])
        for extra in ("catatan",):
            if extra not in existing and extra in base:
                existing[extra] = ""
        data[step] = existing
    return data


# ---------------------------------------------------------------------------
# Renderer
# ---------------------------------------------------------------------------
def _clean_rows(df: pd.DataFrame, columns: list[tuple[str, str, str]]) -> list[dict]:
    if df is None:
        return []
    rows = []
    for record in df.to_dict("records"):
        row = {key: ("" if pd.isna(record.get(key)) else str(record.get(key)).strip()) for key, _, _ in columns}
        if any(row.values()):
            rows.append(row)
    return rows


def render_editor(step: str, data: dict, prefix: str) -> dict:
    """Render editor untuk satu tahap dan kembalikan data hasil edit."""
    edited = copy.deepcopy(data)
    spec = SECTION_SPECS.get(step, [])
    for group in spec:
        st.markdown(f"#### {group['title']}")
        if group.get("hint"):
            st.caption(group["hint"])
        for field in group.get("fields", []):
            path = field["path"]
            key = f"{prefix}__{path}"
            value = get_path(edited, path)
            if field["type"] == "lines":
                text_value = "\n".join(value) if isinstance(value, list) else str(value or "")
                result = st.text_area(
                    field["label"], value=text_value, key=key,
                    height=field.get("height", 110),
                    help=field.get("help"),
                )
                set_path(edited, path, [line.strip() for line in result.splitlines() if line.strip()])
            else:
                height = 90 if field["type"] == "text" else field.get("height", 130)
                result = st.text_input(field["label"], value=str(value or ""), key=key) if field["type"] == "text" else st.text_area(
                    field["label"], value=str(value or ""), key=key, height=height, help=field.get("help")
                )
                set_path(edited, path, result)
        for table in group.get("tables", []):
            path = table["path"]
            key = f"{prefix}__{path}"
            columns = table["columns"]
            current = get_path(edited, path)
            if not isinstance(current, list):
                current = []
            frame = pd.DataFrame(
                [{col: str(row.get(col, "") or "") for col, _, _ in columns} for row in current if isinstance(row, dict)],
                columns=[col for col, _, _ in columns],
            )
            config_map = {
                col: st.column_config.TextColumn(label, width=width)
                for col, label, width in columns
            }
            result = st.data_editor(
                frame,
                key=key,
                num_rows="dynamic",
                width="stretch",
                hide_index=True,
                column_config=config_map,
            )
            set_path(edited, path, _clean_rows(result, columns))
    return edited


# ---------------------------------------------------------------------------
# Pratinjau ringkas
# ---------------------------------------------------------------------------
def section_summary(data: dict, step: str) -> str:
    section = data.get(step) or {}
    if step == "desain":
        rows = section.get("tujuan") or []
        return f"{len(rows)} tujuan pembelajaran" if rows else "Belum disusun"
    if step == "pengalaman":
        terisi = sum(1 for key in ("memahami", "mengaplikasi", "merefleksi")
                     if isinstance(section.get(key), dict) and section[key].get("aktivitas_siswa"))
        return f"{terisi}/3 pengalaman belajar terisi"
    if step == "asesmen":
        terisi = sum(1 for key in ("awal", "proses", "akhir")
                     if isinstance(section.get(key), dict) and section[key].get("tujuan"))
        return f"{terisi}/3 jenis asesmen terisi"
    if step == "diferensiasi":
        rows = section.get("tingkat") or []
        return f"{len(rows)} tingkat dukungan"
    if step == "lkpd":
        return "LKPD tersusun" if section.get("judul") and section.get("masalah") else "Belum disusun"
    if step == "refleksi":
        jumlah = len(section.get("siswa") or []) + len(section.get("guru") or [])
        return f"{jumlah} pertanyaan refleksi" if jumlah else "Belum disusun"
    if step == "identifikasi":
        dimensi = len(section.get("dimensi") or [])
        return f"{dimensi} dimensi dipilih"
    return "Tersedia"


def step_completion(data: dict) -> dict[str, bool]:
    status = {}
    for step in STEP_KEYS:
        status[step] = section_summary(data, step) not in ("Belum disusun",)
    return status


def rpm_progress(data: dict) -> int:
    done = sum(1 for value in step_completion(data).values() if value)
    return int(round(done / len(STEP_KEYS) * 100))


def save_with_version(rpm_id: int, data: dict, catatan: str = "Penyimpanan manual") -> None:
    db.save_rpm(rpm_id, data)
    db.save_version(rpm_id, data, catatan)
