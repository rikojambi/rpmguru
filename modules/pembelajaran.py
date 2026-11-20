"""Halaman Data Pembelajaran dan impor CP/ATP."""

from __future__ import annotations

import streamlit as st

import config
from database import db
from modules import komponen


FIELDS = [
    "judul", "jenjang", "fase", "kelas", "semester", "mata_pelajaran", "konsentrasi",
    "elemen", "cp", "atp", "materi_pokok", "tp", "alokasi_waktu", "jumlah_peserta",
    "karakteristik", "pengetahuan_awal", "kebutuhan_belajar", "konteks_lingkungan",
    "sarana", "sumber_belajar",
]


def _blank() -> dict:
    profil = db.get_active_profile() or {}
    settings = db.get_settings()
    return {
        "judul": "",
        "jenjang": profil.get("jenjang") or "SMP",
        "fase": "D",
        "kelas": "7",
        "semester": profil.get("semester") or settings.get("semester", "Ganjil"),
        "mata_pelajaran": "",
        "konsentrasi": "",
        "elemen": "",
        "cp": "",
        "atp": "",
        "materi_pokok": "",
        "tp": "",
        "alokasi_waktu": "2 x 40 menit",
        "jumlah_peserta": 32,
        "karakteristik": "",
        "pengetahuan_awal": "",
        "kebutuhan_belajar": "",
        "konteks_lingkungan": "",
        "sarana": "",
        "sumber_belajar": "",
    }


def _prepare_state(rows: list[dict]) -> None:
    if "_pm_pending" in st.session_state:
        st.session_state["pm_selected"] = st.session_state.pop("_pm_pending")
    if "pm_selected" not in st.session_state:
        st.session_state["pm_selected"] = 0
    opsi = [0] + [row["id"] for row in rows]
    if st.session_state.get("pm_selected") not in opsi:
        st.session_state["pm_selected"] = 0


def _label_pm(pmid: int, rows: list[dict]) -> str:
    if pmid == 0:
        return "➕ Data pembelajaran baru"
    row = next((r for r in rows if r["id"] == pmid), None)
    if not row:
        return f"Data #{pmid}"
    mapel = row.get("mata_pelajaran") or "Tanpa mapel"
    materi = komponen.truncate(row.get("materi_pokok", ""), 45)
    return f"{mapel} · {materi} · Kelas {row.get('kelas','-')}"


def _form_payload(judul, mapel, jenjang, fase, kelas, semester, konsentrasi, elemen,
                  cp, atp, materi, tp, alokasi, jumlah, karakteristik, pengetahuan,
                  kebutuhan, konteks, sarana, sumber) -> dict:
    return {
        "judul": judul.strip() or f"RPM {mapel.strip()} - {komponen.truncate(materi.strip(), 50)}",
        "jenjang": jenjang,
        "fase": fase,
        "kelas": kelas,
        "semester": semester,
        "mata_pelajaran": mapel.strip(),
        "konsentrasi": konsentrasi.strip(),
        "elemen": elemen.strip(),
        "cp": cp.strip(),
        "atp": atp.strip(),
        "materi_pokok": materi.strip(),
        "tp": tp.strip(),
        "alokasi_waktu": alokasi.strip(),
        "jumlah_peserta": jumlah,
        "karakteristik": karakteristik.strip(),
        "pengetahuan_awal": pengetahuan.strip(),
        "kebutuhan_belajar": kebutuhan.strip(),
        "konteks_lingkungan": konteks.strip(),
        "sarana": sarana.strip(),
        "sumber_belajar": sumber.strip(),
    }


def render() -> None:
    komponen.page_header(
        "Data Pembelajaran",
        "Isi CP dan ATP dari dokumen guru. Aplikasi tidak membuat CP resmi secara otomatis.",
        "📚",
    )
    rows = db.list_pembelajaran()
    _prepare_state(rows)

    # Prefill dari impor, bank, atau salinan data lain
    if "_pm_prefill" in st.session_state:
        prefill = st.session_state.pop("_pm_prefill")
        if isinstance(prefill, dict):
            st.session_state["_pm_applied"] = prefill
            st.session_state["_pm_rev"] = int(st.session_state.get("_pm_rev", 0)) + 1
    applied = st.session_state.pop("_pm_applied", None)

    data = dict(_blank())
    terpilih = st.session_state["pm_selected"]
    existing = db.get_pembelajaran(terpilih) if terpilih else None
    if existing:
        data.update({k: existing.get(k, "") for k in FIELDS})
    if applied:
        data.update({k: v for k, v in applied.items() if k in FIELDS})
        data["judul"] = applied.get("judul", data["judul"])
        if terpilih:
            data["judul"] = existing.get("judul", "") if existing else data["judul"]

    rev = st.session_state.get("_pm_rev", 0)

    atas1, atas2, atas3 = st.columns([2.4, 1, 1])
    with atas1:
        st.selectbox(
            "Pilih data pembelajaran",
            options=[0] + [row["id"] for row in rows],
            format_func=lambda x: _label_pm(x, rows),
            key="pm_selected",
        )
    with atas2:
        st.write("")
        if st.button("➕ Data baru", width="stretch"):
            st.session_state["_pm_prefill"] = _blank()
            st.session_state["_pm_pending"] = 0
            st.rerun()
    with atas3:
        st.write("")
        if st.button("📄 Buat RPM", width="stretch", disabled=not existing,
                     type="primary"):
            rpm_id = db.create_rpm(
                existing["id"],
                existing.get("profile_id") or (db.get_active_profile() or {}).get("id"),
                existing.get("judul") or f"RPM {existing.get('mata_pelajaran','')}",
                {},
            )
            st.session_state["rpm_id"] = rpm_id
            st.session_state["_nav_request"] = "Generator RPM"
            st.rerun()

    if existing:
        st.markdown(
            komponen.tag(f"Kelas {existing.get('kelas','-')} · Fase {existing.get('fase','-')}", "info")
            + komponen.tag(existing.get("mata_pelajaran", ""), "neutral"),
            unsafe_allow_html=True,
        )
    else:
        komponen.info(
            "Anda sedang membuat data pembelajaran baru. Data disimpan setelah tombol Simpan ditekan.",
            "info",
        )

    # ------------------------------------------------------------------
    # Pengambilan CP/ATP dari bank dan salinan data lain
    # ------------------------------------------------------------------
    with st.expander("Ambil CP/ATP dari bank atau salin dari data sebelumnya", expanded=False):
        kolom1, kolom2 = st.columns(2)
        with kolom1:
            st.markdown("**Dari Bank CP & ATP**")
            bank = db.list_bank_cp()
            if bank:
                pilihan_bank = st.selectbox(
                    "Pilih entri bank",
                    options=[row["id"] for row in bank],
                    format_func=lambda x: next(
                        (
                            f"{r.get('mata_pelajaran','-')} · {komponen.truncate(r.get('elemen','') or r.get('cp',''), 50)}"
                            for r in bank if r["id"] == x
                        ),
                        f"Bank #{x}",
                    ),
                    key="pm_bank_pick",
                )
                entri = next((r for r in bank if r["id"] == pilihan_bank), None)
                if entri:
                    st.caption(komponen.truncate(entri.get("cp", ""), 220))
                    if st.button("Terapkan CP/ATP dari bank", key="pm_bank_apply"):
                        st.session_state["_pm_prefill"] = {
                            **data,
                            "mata_pelajaran": data.get("mata_pelajaran") or entri.get("mata_pelajaran", ""),
                            "fase": entri.get("fase") or data.get("fase"),
                            "elemen": entri.get("elemen") or data.get("elemen"),
                            "cp": entri.get("cp", ""),
                            "atp": entri.get("atp", ""),
                        }
                        st.rerun()
            else:
                st.caption("Bank masih kosong. Tambahkan melalui menu Bank CP dan ATP.")
                if st.button("Buka Bank CP & ATP", key="pm_bank_open"):
                    komponen.navigate("Bank CP dan ATP")
        with kolom2:
            st.markdown("**Salin dari data sebelumnya**")
            if rows:
                sumber = st.selectbox(
                    "Pilih data sumber",
                    options=[row["id"] for row in rows],
                    format_func=lambda x: _label_pm(x, rows),
                    key="pm_copy_pick",
                )
                if st.button("Muat ke formulir (belum disimpan)", key="pm_copy_apply"):
                    sumber_row = db.get_pembelajaran(sumber)
                    if sumber_row:
                        payload = {k: sumber_row.get(k, "") for k in FIELDS}
                        payload["judul"] = f"{sumber_row.get('judul','')} (salinan)"
                        st.session_state["_pm_prefill"] = payload
                        st.session_state["_pm_pending"] = 0
                        st.rerun()
            else:
                st.caption("Belum ada data sebelumnya.")

    st.write("")
    with st.form(key=f"pm_form_{terpilih}_{rev}", clear_on_submit=False):
        st.markdown("#### Identitas Pembelajaran")
        c1, c2 = st.columns([2, 2])
        with c1:
            mapel = st.text_input("Mata pelajaran *", value=data.get("mata_pelajaran", ""))
        with c2:
            judul = st.text_input(
                "Judul data/RPM",
                value=data.get("judul", ""),
                help="Kosongkan untuk dibuat otomatis dari mata pelajaran dan materi.",
            )

        c3, c4, c5, c6 = st.columns(4)
        with c3:
            jenjang = st.selectbox(
                "Jenjang", options=config.JENJANG,
                index=config.JENJANG.index(data.get("jenjang")) if data.get("jenjang") in config.JENJANG else 2,
            )
        with c4:
            fase = st.selectbox(
                "Fase", options=config.FASE,
                index=config.FASE.index(data.get("fase")) if data.get("fase") in config.FASE else 3,
                help="Fase A-F. Sesuaikan dengan kelas.",
            )
        with c5:
            kelas = st.selectbox(
                "Kelas", options=config.KELAS,
                index=config.KELAS.index(str(data.get("kelas"))) if str(data.get("kelas")) in config.KELAS else 6,
            )
        with c6:
            semester = st.selectbox(
                "Semester", options=config.SEMESTER,
                index=config.SEMESTER.index(data.get("semester")) if data.get("semester") in config.SEMESTER else 0,
            )

        c7, c8 = st.columns(2)
        with c7:
            konsentrasi = st.text_input(
                "Konsentrasi keahlian (khusus SMK/MAK)",
                value=data.get("konsentrasi", ""),
                placeholder="contoh: Teknik Komputer dan Jaringan",
            )
        with c8:
            elemen = st.text_input("Elemen mata pelajaran", value=data.get("elemen", ""))
        st.caption(f"Pemetaan fase: {config.FASE_KELAS.get(fase, '-')}")

        st.markdown("#### Capaian Pembelajaran dan Alur Tujuan Pembelajaran")
        komponen.info(
            "CP dan ATP harus berasal dari dokumen resmi atau keputusan guru/sekolah. "
            "Jangan menyalin CP dari saran AI tanpa memeriksa sumber aslinya.",
            "warning",
        )
        cp = st.text_area("Capaian Pembelajaran (CP) *", value=data.get("cp", ""), height=150)
        atp = st.text_area("Alur Tujuan Pembelajaran (ATP)", value=data.get("atp", ""), height=120)

        st.markdown("#### Materi dan Tujuan")
        materi = st.text_input("Materi pokok *", value=data.get("materi_pokok", ""))
        tp = st.text_area(
            "Tujuan Pembelajaran (TP)",
            value=data.get("tp", ""),
            height=120,
            help="Satu tujuan per baris. Gunakan kata kerja yang dapat diamati.",
        )
        c9, c10 = st.columns(2)
        with c9:
            alokasi = st.text_input(
                "Alokasi waktu", value=str(data.get("alokasi_waktu", "")),
                help="Contoh: 2 x 40 menit, 3 x 45 menit, atau 90 menit.",
            )
        with c10:
            try:
                jumlah_default = int(data.get("jumlah_peserta") or 0)
            except (TypeError, ValueError):
                jumlah_default = 0
            jumlah = st.number_input(
                "Jumlah peserta didik", min_value=0, max_value=200,
                value=jumlah_default, step=1,
            )

        st.markdown("#### Peserta Didik dan Konteks")
        c11, c12 = st.columns(2)
        with c11:
            karakteristik = st.text_area(
                "Karakteristik peserta didik", value=data.get("karakteristik", ""), height=100
            )
        with c12:
            pengetahuan = st.text_area(
                "Pengetahuan awal peserta didik", value=data.get("pengetahuan_awal", ""), height=100
            )
        c13, c14 = st.columns(2)
        with c13:
            kebutuhan = st.text_area(
                "Kebutuhan belajar", value=data.get("kebutuhan_belajar", ""), height=100
            )
        with c14:
            konteks = st.text_area(
                "Konteks lingkungan sekolah", value=data.get("konteks_lingkungan", ""), height=100
            )
        c15, c16 = st.columns(2)
        with c15:
            sarana = st.text_area(
                "Sarana dan prasarana", value=data.get("sarana", ""), height=90,
                help="Tuliskan fasilitas nyata. Generator AI akan menyesuaikan diri.",
            )
        with c16:
            sumber = st.text_area(
                "Sumber belajar", value=data.get("sumber_belajar", ""), height=90
            )

        simpan_bank = st.checkbox(
            "Simpan CP/ATP ini ke Bank CP & ATP",
            value=False,
            help="Berguna agar data resmi yang sama dapat dipakai ulang.",
        )
        submitted = st.form_submit_button("💾 Simpan Data Pembelajaran", type="primary", width="stretch")

    if submitted:
        if not mapel.strip():
            st.error("Mata pelajaran wajib diisi.")
        elif not materi.strip():
            st.error("Materi pokok wajib diisi.")
        elif not cp.strip():
            st.error("CP wajib diisi. Masukkan CP dari dokumen guru; aplikasi tidak membuat CP resmi.")
        else:
            payload = _form_payload(
                judul, mapel, jenjang, fase, kelas, semester, konsentrasi, elemen,
                cp, atp, materi, tp, alokasi, jumlah, karakteristik, pengetahuan,
                kebutuhan, konteks, sarana, sumber,
            )
            if not existing:
                payload["profile_id"] = (db.get_active_profile() or {}).get("id")
            else:
                payload["profile_id"] = existing.get("profile_id")
            new_id = db.save_pembelajaran(payload, terpilih or None)
            if simpan_bank and cp.strip():
                db.save_bank_cp(
                    {
                        "jenjang": jenjang, "fase": fase, "mata_pelajaran": mapel,
                        "elemen": elemen, "cp": cp, "atp": atp,
                        "sumber": "Data pembelajaran", "is_official": 1,
                    }
                )
            db.log_activity("Simpan data pembelajaran", f"{mapel} · {materi}")
            st.session_state["_pm_pending"] = new_id
            st.success("Data pembelajaran tersimpan.")
            st.rerun()

    if existing:
        st.write("")
        st.markdown("### Tindakan Data")
        k1, k2, k3, k4 = st.columns([1, 1, 1.1, 2])
        with k1:
            if st.button("Duplikasi", width="stretch"):
                new_id = db.duplicate_pembelajaran(existing["id"])
                db.log_activity("Duplikasi data pembelajaran", existing.get("mata_pelajaran", ""))
                st.session_state["_pm_pending"] = new_id
                st.rerun()
        with k2:
            jumlah_rpm = int(db.scalar(
                "SELECT COUNT(*) FROM rpm_documents WHERE pembelajaran_id = ?",
                (existing["id"],),
            ))
            st.metric("RPM terkait", jumlah_rpm, label_visibility="visible")
        with k3:
            with st.popover("Hapus data", width="stretch"):
                if jumlah_rpm:
                    st.warning("Data ini sudah dipakai oleh RPM. Arsipkan/hapus RPM terlebih dahulu.")
                else:
                    st.warning("Data pembelajaran akan dihapus permanen.")
                    centang = st.checkbox("Saya yakin.", key=f"pm_hapus_{existing['id']}")
                    if st.button("Hapus", disabled=not centang, key=f"pm_hapus_btn_{existing['id']}"):
                        db.delete_pembelajaran(existing["id"])
                        db.log_activity("Hapus data pembelajaran", existing.get("mata_pelajaran", ""))
                        sisa = db.list_pembelajaran()
                        st.session_state["_pm_pending"] = sisa[0]["id"] if sisa else 0
                        st.rerun()
        with k4:
            st.caption(
                "Menghapus data tidak menghapus profil sekolah. Dokumen RPM yang sudah ada tetap tersimpan "
                "dalam arsip, tetapi tautan datanya perlu diperiksa kembali."
            )

    st.write("")
    st.markdown("### Impor CP dan ATP")
    st.caption("Impor dari Word (.docx), Excel (.xlsx), CSV, atau teks. Periksa hasil ekstraksi sebelum disimpan.")
    with st.expander("Buka impor CP/ATP", expanded=False):
        _render_import(terpilih, existing, data, rows)


def _render_import(terpilih: int, existing: dict | None, data: dict, rows: list[dict]) -> None:
    berkas = st.file_uploader(
        "Unggah berkas CP/ATP",
        type=["docx", "xlsx", "xlsm", "csv", "txt"],
        key="pm_import_file",
    )
    if not berkas:
        st.caption("Belum ada berkas diunggah.")
        return

    with st.spinner("Membaca berkas..."):
        parsed, keterangan = komponen.read_cp_atp_upload(berkas)
    st.caption(keterangan)

    if berkas.name.lower().endswith((".xlsx", ".xlsm")):
        try:
            frames = komponen.read_excel_bytes(berkas.getvalue())
            for sheet, frame in list(frames.items())[:3]:
                with st.expander(f"Pratinjau sheet: {sheet} ({len(frame)} baris)"):
                    st.dataframe(frame.head(15), width="stretch", height=220)
        except Exception as exc:
            st.warning(f"Pratinjau tabel tidak dapat ditampilkan: {exc}")

    cp_key = f"import_cp_{abs(hash(berkas.name)) % 100000}"
    atp_key = f"import_atp_{abs(hash(berkas.name)) % 100000}"
    cp = st.text_area("Hasil ekstraksi CP", value=parsed.get("cp", ""), height=160, key=cp_key)
    atp = st.text_area("Hasil ekstraksi ATP", value=parsed.get("atp", ""), height=120, key=atp_key)

    aksi = st.columns(3)
    with aksi[0]:
        if st.button("Buat data baru dari impor", type="primary", width="stretch"):
            if not cp.strip():
                st.error("CP hasil ekstraksi kosong.")
            else:
                payload = dict(data)
                payload.update(
                    {
                        "judul": f"Impor - {berkas.name}",
                        "cp": cp.strip(),
                        "atp": atp.strip(),
                    }
                )
                st.session_state["_pm_prefill"] = payload
                st.session_state["_pm_pending"] = 0
                st.success("Hasil impor dimuat ke formulir data baru. Lengkapi identitas lalu simpan.")
                st.rerun()
    with aksi[1]:
        if st.button("Perbarui CP/ATP data terpilih", disabled=not existing, width="stretch"):
            if existing and cp.strip():
                payload = {k: existing.get(k, "") for k in FIELDS}
                payload["cp"] = cp.strip()
                payload["atp"] = atp.strip()
                payload["profile_id"] = existing.get("profile_id")
                db.save_pembelajaran(payload, existing["id"])
                db.log_activity("Impor CP/ATP", f"{existing.get('mata_pelajaran','')} dari {berkas.name}")
                st.success("CP/ATP data terpilih diperbarui.")
                st.rerun()
    with aksi[2]:
        if st.button("Simpan ke Bank CP & ATP", width="stretch"):
            if not cp.strip():
                st.error("CP kosong; tidak ada yang disimpan.")
            else:
                db.save_bank_cp(
                    {
                        "jenjang": data.get("jenjang", ""),
                        "fase": data.get("fase", ""),
                        "mata_pelajaran": data.get("mata_pelajaran", ""),
                        "elemen": data.get("elemen", ""),
                        "cp": cp.strip(),
                        "atp": atp.strip(),
                        "sumber": f"Impor {berkas.name}",
                        "is_official": 1,
                    }
                )
                db.log_activity("Impor ke bank CP", berkas.name)
                st.success("Tersimpan ke bank CP & ATP.")
