"""Halaman Bank CP dan ATP."""

from __future__ import annotations

import pandas as pd
import streamlit as st

import config
from database import db
from modules import komponen


def _blank() -> dict:
    return {
        "jenjang": "SMP", "fase": "D", "mata_pelajaran": "", "elemen": "",
        "cp": "", "atp": "", "sumber": "Input guru", "is_official": 1,
    }


def _prepare(rows: list[dict]) -> None:
    if "_bank_pending" in st.session_state:
        st.session_state["bank_selected"] = st.session_state.pop("_bank_pending")
    if "bank_selected" not in st.session_state:
        st.session_state["bank_selected"] = 0
    opsi = [0] + [row["id"] for row in rows]
    if st.session_state.get("bank_selected") not in opsi:
        st.session_state["bank_selected"] = 0


def _label_bank(row_id: int, rows: list[dict]) -> str:
    if row_id == 0:
        return "➕ Entri baru"
    row = next((r for r in rows if r["id"] == row_id), None)
    if not row:
        return f"Entri #{row_id}"
    return f"{row.get('mata_pelajaran') or '-'} · Fase {row.get('fase') or '-'} · {komponen.truncate(row.get('elemen') or row.get('cp'), 45)}"


def render() -> None:
    komponen.page_header(
        "Bank CP dan ATP",
        "Simpan CP dan ATP yang Anda masukkan sendiri agar dapat dipakai ulang. Bukan bank CP resmi dari pemerintah.",
        "🗂️",
    )
    rows = db.list_bank_cp()
    _prepare(rows)

    if "_bank_rev" not in st.session_state:
        st.session_state["_bank_rev"] = 0

    # Filter
    f1, f2, f3 = st.columns([2, 1, 1.2])
    with f1:
        cari = st.text_input("Cari mata pelajaran, elemen, atau isi CP", value="", key="bank_search")
    with f2:
        filter_fase = st.selectbox("Fase", ["Semua"] + config.FASE, key="bank_filter_fase")
    with f3:
        filter_jenjang = st.selectbox("Jenjang", ["Semua"] + config.JENJANG, key="bank_filter_jenjang")

    tampil = [
        row for row in rows
        if (filter_fase == "Semua" or row.get("fase") == filter_fase)
        and (filter_jenjang == "Semua" or row.get("jenjang") == filter_jenjang)
    ]
    if cari.strip():
        teks = cari.lower()
        tampil = [
            row for row in tampil
            if teks in " ".join(str(row.get(k, "")) for k in ("mata_pelajaran", "elemen", "cp", "atp")).lower()
        ]

    st.caption(f"{len(tampil)} entri ditampilkan dari {len(rows)} entri tersimpan.")

    if tampil:
        frame = pd.DataFrame(
            [
                {
                    "Mapel": row.get("mata_pelajaran", ""),
                    "Fase": row.get("fase", ""),
                    "Elemen": row.get("elemen", ""),
                    "CP": komponen.truncate(row.get("cp", ""), 90),
                    "Sumber": row.get("sumber", ""),
                }
                for row in tampil
            ]
        )
        st.dataframe(frame, width="stretch", height=min(260, 40 + len(frame) * 35))

    st.write("")
    if "_bank_prefill" in st.session_state:
        prefill = st.session_state.pop("_bank_prefill")
        st.session_state["_bank_applied"] = prefill
        st.session_state["_bank_rev"] = int(st.session_state.get("_bank_rev", 0)) + 1
    applied = st.session_state.pop("_bank_applied", None)

    terpilih = st.session_state["bank_selected"]
    existing = db.get_bank_cp(terpilih) if terpilih else None
    data = dict(existing) if existing else _blank()
    if applied:
        data.update({k: v for k, v in applied.items() if k in data})

    d1, d2 = st.columns([2.4, 1])
    with d1:
        st.selectbox(
            "Pilih entri untuk diedit",
            options=[0] + [row["id"] for row in rows],
            format_func=lambda x: _label_bank(x, rows),
            key="bank_selected",
        )
    with d2:
        st.write("")
        if st.button("➕ Entri baru", width="stretch"):
            st.session_state["_bank_prefill"] = _blank()
            st.session_state["_bank_pending"] = 0
            st.rerun()

    with st.form(key=f"bank_form_{terpilih}_{st.session_state.get('_bank_rev', 0)}"):
        st.markdown("#### Data CP dan ATP")
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            jenjang = st.selectbox(
                "Jenjang", config.JENJANG,
                index=config.JENJANG.index(data.get("jenjang")) if data.get("jenjang") in config.JENJANG else 2,
            )
        with c2:
            fase = st.selectbox(
                "Fase", config.FASE,
                index=config.FASE.index(data.get("fase")) if data.get("fase") in config.FASE else 3,
            )
        with c3:
            mapel = st.text_input("Mata pelajaran *", value=data.get("mata_pelajaran", ""))
        with c4:
            elemen = st.text_input("Elemen", value=data.get("elemen", ""))
        cp = st.text_area("Capaian Pembelajaran (CP) *", value=data.get("cp", ""), height=150)
        atp = st.text_area("Alur Tujuan Pembelajaran (ATP)", value=data.get("atp", ""), height=110)
        c5, c6 = st.columns([2, 1])
        with c5:
            sumber = st.text_input(
                "Sumber data", value=data.get("sumber", "Input guru"),
                help="Contoh: dokumen CP sekolah, keputusan guru, hasil impor. Bukan dibuat oleh AI.",
            )
        with c6:
            official = st.checkbox(
                "Data resmi dari guru/sekolah",
                value=bool(data.get("is_official", 1)),
                help="Tandai hanya bila Anda memverifikasi sumbernya.",
            )
        simpan = st.form_submit_button("💾 Simpan Entri", type="primary", width="stretch")

    if simpan:
        if not mapel.strip():
            st.error("Mata pelajaran wajib diisi.")
        elif not cp.strip():
            st.error("CP wajib diisi.")
        else:
            payload = {
                "jenjang": jenjang, "fase": fase, "mata_pelajaran": mapel.strip(),
                "elemen": elemen.strip(), "cp": cp.strip(), "atp": atp.strip(),
                "sumber": sumber.strip() or "Input guru", "is_official": official,
            }
            new_id = db.save_bank_cp(payload, terpilih or None)
            db.log_activity("Simpan bank CP", f"{mapel} · Fase {fase}")
            st.session_state["_bank_pending"] = new_id
            st.success("Entri bank CP tersimpan.")
            st.rerun()

    if existing:
        st.write("")
        k1, k2 = st.columns([1, 3])
        with k1:
            with st.popover("Hapus entri", width="stretch"):
                st.warning("Entri akan dihapus permanen. Data pembelajaran yang memakainya tidak berubah.")
                centang = st.checkbox("Saya yakin.", key=f"bank_hapus_{existing['id']}")
                if st.button("Hapus", disabled=not centang, key=f"bank_hapus_btn_{existing['id']}"):
                    db.delete_bank_cp(existing["id"])
                    db.log_activity("Hapus bank CP", existing.get("mata_pelajaran", ""))
                    sisa = db.list_bank_cp()
                    st.session_state["_bank_pending"] = sisa[0]["id"] if sisa else 0
                    st.rerun()

    st.write("")
    st.markdown("### Impor Massal")
    with st.expander("Impor dari Word/Excel", expanded=False):
        _render_import()


def _render_import() -> None:
    st.caption(
        "Excel: gunakan kolom bernama Mata Pelajaran/Mapel, Fase, Elemen, CP, ATP, dan Jenjang bila ada. "
        "Word/TXT: gunakan penanda 'CP:' dan 'ATP:'."
    )
    berkas = st.file_uploader(
        "Unggah berkas", type=["docx", "xlsx", "xlsm", "csv", "txt"], key="bank_import_file"
    )
    if not berkas:
        return

    nama = berkas.name.lower()
    if nama.endswith((".xlsx", ".xlsm")):
        try:
            frames = komponen.read_excel_bytes(berkas.getvalue())
        except Exception as exc:
            st.error(f"Gagal membaca Excel: {exc}")
            return
        pilihan_sheet = st.selectbox("Sheet", list(frames.keys()), key="bank_import_sheet")
        frame = frames[pilihan_sheet]
        st.dataframe(frame.head(20), width="stretch", height=240)
        if st.button("Impor semua baris pada sheet ini", type="primary", key="bank_import_xlsx"):
            jumlah = _import_dataframe(frame)
            if jumlah:
                db.log_activity("Impor massal bank CP", f"{jumlah} entri dari {berkas.name}")
                st.success(f"{jumlah} entri berhasil diimpor.")
                st.rerun()
            else:
                st.warning("Tidak ada baris dengan CP yang dapat diimpor. Periksa nama kolom.")
    else:
        parsed, keterangan = komponen.read_cp_atp_upload(berkas)
        st.caption(keterangan)
        cp = st.text_area("CP", value=parsed.get("cp", ""), height=150, key=f"bank_imp_cp_{berkas.name}")
        atp = st.text_area("ATP", value=parsed.get("atp", ""), height=100, key=f"bank_imp_atp_{berkas.name}")
        c1, c2 = st.columns(2)
        with c1:
            mapel = st.text_input("Mata pelajaran", value="", key=f"bank_imp_mapel_{berkas.name}")
        with c2:
            elemen = st.text_input("Elemen", value="", key=f"bank_imp_elemen_{berkas.name}")
        if st.button("Simpan ke bank", type="primary", key="bank_import_docx"):
            if not cp.strip() or not mapel.strip():
                st.error("Mata pelajaran dan CP wajib diisi.")
            else:
                db.save_bank_cp(
                    {
                        "jenjang": "SMP", "fase": "D", "mata_pelajaran": mapel,
                        "elemen": elemen, "cp": cp, "atp": atp,
                        "sumber": f"Impor {berkas.name}", "is_official": 1,
                    }
                )
                db.log_activity("Impor bank CP", berkas.name)
                st.success("Entri berhasil disimpan.")
                st.rerun()


def _import_dataframe(frame: pd.DataFrame) -> int:
    if frame is None or frame.empty:
        return 0
    kolom = {str(c).strip().lower(): c for c in frame.columns}

    def ambil(*names: str):
        for name in names:
            if name in kolom:
                return kolom[name]
        return None

    col_mapel = ambil("mata pelajaran", "mapel", "mata_pelajaran", "subject")
    col_cp = ambil("cp", "capaian pembelajaran", "capaian_pembelajaran")
    col_atp = ambil("atp", "alur tujuan pembelajaran", "alur_tujuan_pembelajaran")
    col_fase = ambil("fase", "phase")
    col_elemen = ambil("elemen", "elemen mata pelajaran")
    col_jenjang = ambil("jenjang", "level")
    if col_cp is None or col_mapel is None:
        return 0

    jumlah = 0
    for _, row in frame.iterrows():
        cp = str(row.get(col_cp, "") or "").strip()
        mapel = str(row.get(col_mapel, "") or "").strip()
        if not cp or not mapel or cp.lower() == "nan":
            continue
        fase = str(row.get(col_fase, "") or "D").strip() if col_fase else "D"
        if fase not in config.FASE:
            fase = "D"
        jenjang = str(row.get(col_jenjang, "") or "SMP").strip() if col_jenjang else "SMP"
        db.save_bank_cp(
            {
                "jenjang": jenjang,
                "fase": fase,
                "mata_pelajaran": mapel,
                "elemen": str(row.get(col_elemen, "") or "").strip() if col_elemen else "",
                "cp": cp,
                "atp": str(row.get(col_atp, "") or "").strip() if col_atp else "",
                "sumber": "Impor Excel",
                "is_official": 1,
            }
        )
        jumlah += 1
    return jumlah
