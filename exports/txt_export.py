"""Ekspor RPM/LKPD ke teks biasa (TXT) yang mudah disalin."""

from __future__ import annotations

import io
import textwrap

from exports import konten


def _garis(char: str = "=", width: int = 78) -> str:
    return char * width


def _wrap(value: str, width: int = 78, indent: str = "") -> list[str]:
    lines: list[str] = []
    for part in str(value or "").split("\n"):
        if not part.strip():
            lines.append("")
            continue
        lines.extend(textwrap.wrap(part, width=width, subsequent_indent=indent) or [""])
    return lines


def _render_table(headers: list[str], rows: list[list]) -> list[str]:
    if not headers or not rows:
        return []
    jumlah = len(headers)
    total_width = 78
    if jumlah == 2:
        widths = [22, 54]
    elif jumlah == 3:
        widths = [16, 22, 38]
    elif jumlah == 4:
        widths = [8, 26, 28, 14]
    else:
        base = max(8, total_width // jumlah)
        widths = [base] * jumlah
    lines = []
    lines.append(" | ".join(headers[i][: widths[i]].ljust(widths[i]) for i in range(jumlah)))
    lines.append("-+-".join("-" * widths[i] for i in range(jumlah)))
    for row in rows:
        wrapped_cells = []
        for i in range(jumlah):
            value = str(row[i] if i < len(row) else "")
            wrapped_cells.append(textwrap.wrap(value, width=widths[i]) or [""])
        tinggi = max(len(cell) for cell in wrapped_cells)
        for line_index in range(tinggi):
            parts = []
            for i in range(jumlah):
                cell = wrapped_cells[i]
                text = cell[line_index] if line_index < len(cell) else ""
                parts.append(text.ljust(widths[i]))
            lines.append(" | ".join(parts))
        lines.append("-+-".join("-" * widths[i] for i in range(jumlah)))
    return lines


def _render(blocks: list[dict], profil: dict) -> str:
    lines: list[str] = []
    if profil.get("nama_sekolah"):
        lines.append(profil["nama_sekolah"].upper().center(78))
        alamat = " | ".join(
            item for item in [profil.get("alamat"), profil.get("kabupaten"), profil.get("provinsi")] if item
        )
        if alamat:
            lines.append(alamat.center(78))
        if profil.get("npsn"):
            lines.append(f"NPSN: {profil['npsn']}".center(78))
        lines.append(_garis())
        lines.append("")

    for block in blocks:
        tipe = block.get("type")
        if tipe == "doc_title":
            lines.append(str(block.get("text", "")).center(78))
            lines.append(_garis("-"))
        elif tipe == "heading":
            lines.append("")
            lines.append(str(block.get("text", "")).upper())
            lines.append(_garis("-"))
        elif tipe == "subheading":
            lines.append("")
            lines.append(f"[ {block.get('text','')} ]")
        elif tipe == "paragraph":
            lines.extend(_wrap(block.get("text", "")))
        elif tipe == "bullets":
            for item in block.get("items", []):
                wrapped = _wrap(item, 74, indent="    ")
                if wrapped:
                    lines.append("  - " + wrapped[0])
                    lines.extend("    " + line for line in wrapped[1:])
        elif tipe == "table":
            lines.extend(_render_table(block.get("headers", []), block.get("rows", [])))
        elif tipe == "signature":
            p = block.get("profil") or profil
            lines.append("")
            lines.append(f"{p.get('kabupaten') or '..............'}, ........................ 20....")
            lines.append("")
            lines.append("Mengetahui,".ljust(38) + "Guru Mata Pelajaran")
            lines.append("Kepala Sekolah".ljust(38))
            lines.append("")
            lines.append("")
            lines.append((p.get("nama_kepala_sekolah") or "........................").ljust(38) + (p.get("nama_guru") or "........................"))
            lines.append(("NIP. " + (p.get("nip") or "........................")).ljust(38) + "NIP. " + (p.get("nip") or "........................"))
        elif tipe == "signature_lkpd":
            p = block.get("profil") or profil
            lines.append("")
            lines.append(f"{p.get('kabupaten') or '..............'}, ........................ 20....")
            lines.append("Guru Mata Pelajaran")
            lines.append("")
            lines.append("")
            lines.append(p.get("nama_guru") or "........................")
            lines.append("NIP. " + (p.get("nip") or "........................"))
    lines.append("")
    lines.append(_garis())
    lines.append(
        "Disusun dengan bantuan aplikasi Generator RPM. Bukan pengesahan resmi; guru tetap melakukan reviu."
    )
    return "\n".join(lines)


def build_rpm_txt(profil: dict, pemb: dict, data: dict) -> bytes:
    blocks = konten.build_rpm_blocks(profil, pemb, data)
    return _render(blocks, profil).encode("utf-8")


def build_lkpd_txt(profil: dict, pemb: dict, lkpd: dict, data: dict | None = None) -> bytes:
    blocks = konten.build_lkpd_blocks(profil, pemb, lkpd, data)
    return _render(blocks, profil).encode("utf-8")
