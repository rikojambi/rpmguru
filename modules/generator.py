"""Halaman Generator RPM: alur bertahap dengan AI lokal atau draf offline."""

from __future__ import annotations

import difflib
import json

import streamlit as st

import config
from ai.ollama_client import OllamaError
from database import db
from modules import (
    asesmen,
    desain,
    diferensiasi,
    editor,
    identifikasi,
    komponen,
    lkpd,
    pengalaman_belajar,
    refleksi,
)
from modules.editor import STEPS, STEP_KEYS, ensure_structure


STEP_MODULES = {
    "identifikasi": identifikasi,
    "desain": desain,
    "pengalaman": pengalaman_belajar,
    "asesmen": asesmen,
    "diferensiasi": diferensiasi,
    "lkpd": lkpd,
    "refleksi": refleksi,
}


# ---------------------------------------------------------------------------
# Utilitas halaman
# ---------------------------------------------------------------------------
def _rev_key(rpm_id: int) -> str:
    return f"wiz_rev_{rpm_id}"


def current_rev(rpm_id: int) -> int:
    return int(st.session_state.get(_rev_key(rpm_id), 0))


def bump_rev(rpm_id: int) -> None:
    st.session_state[_rev_key(rpm_id)] = current_rev(rpm_id) + 1


def _editor_for(step: str, section: dict, prefix: str) -> dict:
    if step == "lkpd":
        return lkpd.render_editor_step(section, prefix)
    module = STEP_MODULES[step]
    return module.render_editor(section, prefix)


def _options_for(step: str, pemb: dict, section: dict, prefix: str) -> dict:
    module = STEP_MODULES[step]
    renderer = getattr(module, "render_options", None)
    if not renderer:
        return {}
    return renderer(pemb, section, prefix) or {}


def _generate(step: str, pemb: dict, data: dict, options: dict, client, use_ai: bool,
              rpm_id: int):
    if step == "identifikasi":
        return identifikasi.generate(pemb, data.get(step, {}), options, client, use_ai, rpm_id)
    if step == "desain":
        return desain.generate(
            pemb, data.get("desain", {}), options, client, use_ai, rpm_id,
            identifikasi=data.get("identifikasi", {}),
        )
    if step == "pengalaman":
        return pengalaman_belajar.generate(
            pemb, data.get("pengalaman", {}), options, client, use_ai, rpm_id,
            desain=data.get("desain", {}),
        )
    if step == "asesmen":
        return asesmen.generate(
            pemb, data.get("asesmen", {}), options, client, use_ai, rpm_id,
            desain=data.get("desain", {}),
        )
    if step == "diferensiasi":
        return diferensiasi.generate(
            pemb, data.get("diferensiasi", {}), options, client, use_ai, rpm_id,
            desain=data.get("desain", {}), pengalaman=data.get("pengalaman", {}),
        )
    if step == "lkpd":
        return lkpd.generate_step(
            pemb, data.get("lkpd", {}), options, client, use_ai, rpm_id,
            desain=data.get("desain", {}), pengalaman=data.get("pengalaman", {}),
        )
    if step == "refleksi":
        return refleksi.generate(
            pemb, data.get("refleksi", {}), options, client, use_ai, rpm_id,
            desain=data.get("desain", {}),
        )
    raise ValueError(f"Tahap tidak dikenal: {step}")


def _step_pills(data: dict, active_index: int) -> None:
    kolom = st.columns(len(STEPS))
    for index, (col, step) in enumerate(zip(kolom, STEPS)):
        summary = editor.section_summary(data, step["key"])
        done = summary not in ("Belum disusun",)
        kelas = "active" if index == active_index else ("done" if done else "")
        with col:
            st.markdown(
                f"""
                <div class="step-pill {kelas}">
                    <div class="num">TAHAP {index + 1}</div>
                    <div class="name">{step['short']}</div>
                    <div class="summary">{summary}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def _save(rpm_id: int, data: dict, version_note: str | None = None) -> None:
    db.save_rpm(rpm_id, data)
    if version_note:
        db.save_version(rpm_id, data, version_note)


def _flash_and_rerun(message: str, tone: str = "success") -> None:
    komponen.set_flash(message, tone)
    st.rerun()


# ---------------------------------------------------------------------------
# Halaman
# ---------------------------------------------------------------------------
def render() -> None:
    komponen.page_header(
        "Generator RPM",
        "Susun RPM secara bertahap. Setiap bagian dapat digenerate, diedit, disimpan, dan dibandingkan versinya.",
        "⚙️",
    )
    komponen.show_flash()

    daftar_pm = db.list_pembelajaran()
    if not daftar_pm:
        komponen.empty_state(
            "Belum ada data pembelajaran",
            "Isi data pembelajaran terlebih dahulu: mata pelajaran, CP, ATP, materi, dan konteks kelas.",
        )
        if st.button("Isi Data Pembelajaran", type="primary"):
            komponen.navigate("Data Pembelajaran")
        return

    pm_ids = [row["id"] for row in daftar_pm]
    if st.session_state.get("gen_pm") not in pm_ids:
        st.session_state["gen_pm"] = pm_ids[0]

    kolom_pm, kolom_rpm = st.columns([1.5, 1.5])
    with kolom_pm:
        pm_id = st.selectbox(
            "Data pembelajaran",
            options=pm_ids,
            format_func=lambda x: next(
                (
                    f"{r.get('mata_pelajaran','-')} · Kelas {r.get('kelas','-')} · {komponen.truncate(r.get('materi_pokok',''), 40)}"
                    for r in daftar_pm if r["id"] == x
                ),
                f"Data #{x}",
            ),
            key="gen_pm",
        )
    pemb = db.get_pembelajaran(pm_id)
    if not pemb:
        st.error("Data pembelajaran tidak ditemukan.")
        return

    rpm_rows = [row for row in db.list_rpm() if row.get("pembelajaran_id") == pm_id]
    with kolom_rpm:
        if rpm_rows:
            rpm_ids = [row["id"] for row in rpm_rows]
            default_id = st.session_state.get("rpm_id")
            index = rpm_ids.index(default_id) if default_id in rpm_ids else 0
            pilih_rpm = st.selectbox(
                "Dokumen RPM",
                options=rpm_ids,
                index=index,
                format_func=lambda x: next(
                    (
                        f"{(r.get('judul') or 'RPM')[:60]} · {r.get('status','draf')} · {r.get('updated_at','')[:10]}"
                        for r in rpm_rows if r["id"] == x
                    ),
                    f"RPM #{x}",
                ),
                key=f"gen_rpm_{pm_id}",
            )
            st.session_state["rpm_id"] = pilih_rpm
        else:
            st.write("")
            st.caption("Belum ada dokumen RPM untuk data ini.")
            st.session_state["rpm_id"] = None

    aksi = st.columns([1, 1, 1, 2])
    with aksi[0]:
        if st.button("➕ Buat RPM baru", type="primary", width="stretch"):
            judul = pemb.get("judul") or f"RPM {pemb.get('mata_pelajaran','')} - {komponen.truncate(pemb.get('materi_pokok',''), 40)}"
            new_id = db.create_rpm(
                pm_id,
                pemb.get("profile_id") or (db.get_active_profile() or {}).get("id"),
                judul,
                editor.empty_all(),
            )
            st.session_state["rpm_id"] = new_id
            st.session_state["wiz_step"] = 0
            _flash_and_rerun("Dokumen RPM baru dibuat. Mulai dari tahap Identifikasi.", "success")
    with aksi[1]:
        if st.button("📚 Data pembelajaran", width="stretch"):
            komponen.navigate("Data Pembelajaran")
    with aksi[2]:
        if st.button("🗄️ Arsip dokumen", width="stretch"):
            komponen.navigate("Arsip Dokumen")

    if not rpm_rows and not st.session_state.get("rpm_id"):
        komponen.empty_state(
            "Belum ada RPM untuk data ini",
            "Klik 'Buat RPM baru' untuk memulai. Setelah itu setiap tahap dapat digenerate dan diedit.",
        )
        return

    rpm = db.get_rpm(st.session_state.get("rpm_id"))
    if not rpm:
        komponen.info("Dokumen RPM tidak ditemukan. Buat dokumen baru untuk melanjutkan.", "warning")
        return

    data = ensure_structure(json.loads(rpm.get("data_json") or "{}"))
    rev = current_rev(rpm["id"])

    st.write("")
    st.markdown(
        komponen.tag(rpm.get("judul") or "RPM", "info")
        + komponen.tag(f"{pemb.get('mata_pelajaran','-')} · Fase {pemb.get('fase','-')} · Kelas {pemb.get('kelas','-')}", "neutral")
        + komponen.badge_status(rpm.get("status", "draf")),
        unsafe_allow_html=True,
    )

    # Judul dokumen
    with st.expander("Ubah judul dokumen", expanded=False):
        judul_baru = st.text_input("Judul RPM", value=rpm.get("judul", ""), key=f"judul_{rpm['id']}")
        if st.button("Simpan judul", key=f"judul_btn_{rpm['id']}"):
            db.save_rpm(rpm["id"], data, judul=judul_baru.strip() or rpm.get("judul"))
            _flash_and_rerun("Judul dokumen diperbarui.")

    progress = editor.rpm_progress(data)
    st.progress(progress / 100, text=f"Kelengkapan tahap: {progress}%")

    if "wiz_step" not in st.session_state:
        st.session_state["wiz_step"] = 0
    step_index = max(0, min(int(st.session_state["wiz_step"]), len(STEPS) - 1))
    step_info = STEPS[step_index]
    step = step_info["key"]

    _step_pills(data, step_index)
    st.write("")

    st.markdown(f"### {step_info['icon']} {step_info['label']}")
    st.caption(step_info["description"])

    # ------------------------------------------------------------------
    # Opsi dan tombol generate
    # ------------------------------------------------------------------
    options = {}
    if step in ("identifikasi", "desain"):
        with st.expander("Pilihan sebelum generate", expanded=True):
            options = _options_for(step, pemb, data.get(step, {}), f"opt_{rpm['id']}")

    ai_siap, ai_pesan = komponen.ai_ready()
    kontrol = st.columns([1.1, 1, 1, 1.8])
    with kontrol[0]:
        pakai_ai = st.toggle(
            "Gunakan AI lokal",
            value=bool(st.session_state.get("gen_use_ai", ai_siap)),
            disabled=not ai_siap,
            key="gen_use_ai",
            help=ai_pesan if not ai_siap else "Hasil AI tetap harus diperiksa dan diedit.",
        )
    ada_isi = editor.section_summary(data, step) != "Belum disusun"
    label_ai = "♻️ Regenerate AI" if ada_isi else "⚙️ Generate AI"
    with kontrol[1]:
        generate_ai = st.button(
            label_ai, type="primary", width="stretch", disabled=not ai_siap or not pakai_ai,
            key=f"gen_ai_{step}",
        )
    with kontrol[2]:
        generate_offline = st.button(
            "Draf offline", width="stretch", key=f"gen_off_{step}",
            help="Membuat draf berbasis aturan tanpa AI. Tetap dapat diedit.",
        )
    with kontrol[3]:
        if not ai_siap:
            st.caption(f"AI tidak tersedia: {ai_pesan} Gunakan draf offline.")
        else:
            st.caption(f"Aktif: {db.get_setting('ollama_model','qwen2.5:7b')} · Hasil AI wajib diperiksa.")

    if generate_ai or generate_offline:
        client = komponen.get_ai_client() if (generate_ai and pakai_ai and ai_siap) else None
        with st.spinner("Menyusun draf. Proses AI lokal dapat memerlukan waktu..."):
            try:
                hasil = _generate(step, pemb, data, options, client, bool(client), rpm["id"])
            except OllamaError as exc:
                st.error(f"AI gagal: {exc}")
                hasil = None
            except Exception as exc:  # pragma: no cover - pengaman
                st.error(f"Gagal menyusun bagian ini: {exc}")
                hasil = None
        if hasil:
            data[step] = hasil.data
            _save(rpm["id"], data, f"Generate {step} ({hasil.mode})")
            db.log_activity(f"Generate {step}", rpm.get("judul", ""))
            bump_rev(rpm["id"])
            komponen.set_flash(hasil.message, "success" if hasil.mode == "ai" else "warning")
            st.rerun()

    komponen.info(
        "Periksa keselarasan dengan CP/ATP guru. AI tidak diberi izin mengarang CP resmi. "
        "Bagian yang belum yakin dapat dikosongkan dan dilengkapi manual.",
        "info",
    )

    # ------------------------------------------------------------------
    # Editor
    # ------------------------------------------------------------------
    prefix = f"{step}_{rpm['id']}_{rev}"
    with st.container():
        edited = _editor_for(step, data.get(step, {}), prefix)

    st.write("")
    navigasi = st.columns([1, 1, 1.2, 1.6])
    with navigasi[0]:
        prev = st.button("← Sebelumnya", disabled=step_index == 0, width="stretch")
    with navigasi[1]:
        simpan = st.button("💾 Simpan", type="primary", width="stretch")
    with navigasi[2]:
        next_label = "Validasi →" if step_index == len(STEPS) - 1 else "Selanjutnya →"
        nxt = st.button(next_label, width="stretch")
    with navigasi[3]:
        st.caption("Perpindahan tahap menyimpan perubahan. Validasi mengecek konsistensi, bukan pengesahan resmi.")

    if prev or simpan or nxt:
        data[step] = edited
        if simpan:
            _save(rpm["id"], data, f"Simpan manual: {step}")
            db.log_activity("Simpan RPM", rpm.get("judul", ""))
            bump_rev(rpm["id"])
            _flash_and_rerun("Bagian ini tersimpan beserta versinya.", "success")
        else:
            _save(rpm["id"], data)
            db.log_activity("Perbarui RPM", f"{rpm.get('judul','')} · {step}")
            if nxt and step_index == len(STEPS) - 1:
                st.session_state["validasi_rpm_id"] = rpm["id"]
                st.session_state["_nav_request"] = "Validasi RPM"
                st.rerun()
            st.session_state["wiz_step"] = step_index - 1 if prev else step_index + 1
            bump_rev(rpm["id"])
            st.rerun()

    # ------------------------------------------------------------------
    # Finalisasi
    # ------------------------------------------------------------------
    with st.expander("Finalisasi: status, persetujuan, dan validasi", expanded=False):
        st.markdown("**Status dokumen**")
        with st.form(key=f"status_form_{rpm['id']}"):
            status_sekarang = db.get_rpm(rpm["id"]).get("status", "draf")
            status_baru = st.selectbox(
                "Status", config.STATUS_DOKUMEN,
                index=config.STATUS_DOKUMEN.index(status_sekarang) if status_sekarang in config.STATUS_DOKUMEN else 0,
            )
            if st.form_submit_button("Perbarui status"):
                db.update_rpm_status(rpm["id"], status_baru)
                db.log_activity("Ubah status RPM", f"{rpm.get('judul','')} → {status_baru}")
                _flash_and_rerun("Status dokumen diperbarui.")

        st.markdown("**Persetujuan guru**")
        setuju_centang = st.checkbox(
            "Saya telah memeriksa isi RPM dan bertanggung jawab atas penyesuaiannya.",
            key=f"setuju_cek_{rpm['id']}",
        )
        if st.button("✅ Setujui dokumen", disabled=not setuju_centang, key=f"setuju_btn_{rpm['id']}"):
            db.update_rpm_status(rpm["id"], "disetujui")
            db.log_activity("Setujui RPM", rpm.get("judul", ""))
            _flash_and_rerun("Dokumen ditandai disetujui oleh guru. Ini bukan pengesahan resmi pemerintah.")
        st.caption(
            "Persetujuan di aplikasi hanya menandai bahwa guru telah mereviu. Dokumen tidak otomatis disahkan "
            "oleh sekolah atau pemerintah."
        )

        if st.button("🔍 Buka Validasi RPM", key=f"validasi_{rpm['id']}"):
            st.session_state["validasi_rpm_id"] = rpm["id"]
            komponen.navigate("Validasi RPM")

    # ------------------------------------------------------------------
    # Versi dan ekspor
    # ------------------------------------------------------------------
    with st.expander("Versi dokumen dan perbandingan", expanded=False):
        versi = db.list_versions(rpm["id"])
        if not versi:
            st.caption("Belum ada versi tersimpan.")
        else:
            st.dataframe(
                [
                    {
                        "Versi": f"v{v['version_no']}",
                        "Waktu": v.get("created_at", ""),
                        "Catatan": v.get("catatan", ""),
                    }
                    for v in versi
                ],
                width="stretch",
                hide_index=True,
                height=min(220, 40 + len(versi) * 32),
            )
            pilih_versi = st.selectbox(
                "Bandingkan dengan versi",
                options=[v["id"] for v in versi],
                format_func=lambda x: next(
                    (f"v{v['version_no']} · {v.get('created_at','')} · {v.get('catatan','')}" for v in versi if v["id"] == x),
                    f"Versi #{x}",
                ),
                key=f"versi_pilih_{rpm['id']}",
            )
            versi_row = db.get_version(pilih_versi)
            if versi_row:
                lama = json.dumps(json.loads(versi_row.get("data_json") or "{}"), ensure_ascii=False, indent=2, sort_keys=True).splitlines()
                baru = json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True).splitlines()
                diff = list(difflib.unified_diff(lama, baru, fromfile=f"Versi {versi_row['version_no']}", tofile="Saat ini", lineterm=""))
                if diff:
                    st.code("\n".join(diff[:500]), language="diff")
                    if len(diff) > 500:
                        st.caption("Perbedaan dipotong pada 500 baris pertama.")
                else:
                    st.caption("Tidak ada perbedaan dengan versi ini.")
                if st.button("Pulihkan versi ini", key=f"restore_{rpm['id']}"):
                    data_lama = ensure_structure(json.loads(versi_row.get("data_json") or "{}"))
                    _save(rpm["id"], data_lama, f"Restore versi {versi_row['version_no']}")
                    db.log_activity("Restore versi", f"{rpm.get('judul','')} v{versi_row['version_no']}")
                    bump_rev(rpm["id"])
                    _flash_and_rerun(f"Versi {versi_row['version_no']} dipulihkan sebagai isi saat ini.")

    with st.expander("Ekspor dokumen", expanded=False):
        from exports import docx_export, excel_export, pdf_export, txt_export

        profil = komponen.get_profile_for_document(pemb)
        opsi1, opsi2, opsi3 = st.columns(3)
        with opsi1:
            kop = st.checkbox("Sertakan kop sekolah (DOCX)", value=True, key=f"kop_{rpm['id']}")
        with opsi2:
            margin_atas = st.number_input("Margin atas (cm)", 1.5, 4.0, 2.0, 0.1, key=f"mt_{rpm['id']}")
            margin_kiri = st.number_input("Margin kiri (cm)", 1.5, 4.0, 2.2, 0.1, key=f"ml_{rpm['id']}")
        with opsi3:
            margin_kanan = st.number_input("Margin kanan (cm)", 1.5, 4.0, 2.0, 0.1, key=f"mr_{rpm['id']}")
            margin_bawah = st.number_input("Margin bawah (cm)", 1.5, 4.0, 2.0, 0.1, key=f"mb_{rpm['id']}")
        ttd = st.checkbox("Sertakan tempat tanda tangan", value=True, key=f"ttd_{rpm['id']}")

        unduhan = st.columns(4)
        try:
            payload_docx = docx_export.build_rpm_docx(
                profil, pemb, data,
                include_kop=kop, margins=(margin_atas, margin_kiri, margin_bawah, margin_kanan),
                include_signature=ttd,
            )
            with unduhan[0]:
                komponen.download_bytes(
                    "⬇️ DOCX",
                    payload_docx,
                    f"RPM_{pemb.get('mata_pelajaran','')}_{pemb.get('kelas','')}.docx",
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    "rpm_docx_dl",
                )
        except Exception as exc:
            st.error(f"Ekspor DOCX gagal: {exc}")

        try:
            payload_pdf = pdf_export.build_rpm_pdf(
                profil, pemb, data, margins=(margin_atas, margin_kiri, margin_bawah, margin_kanan)
            )
            with unduhan[1]:
                komponen.download_bytes(
                    "⬇️ PDF",
                    payload_pdf,
                    f"RPM_{pemb.get('mata_pelajaran','')}_{pemb.get('kelas','')}.pdf",
                    "application/pdf",
                    "rpm_pdf_dl",
                )
        except Exception as exc:
            st.error(f"Ekspor PDF gagal: {exc}")

        try:
            payload_xlsx = excel_export.build_asesmen_workbook(profil, pemb, data)
            with unduhan[2]:
                komponen.download_bytes(
                    "⬇️ XLSX Asesmen",
                    payload_xlsx,
                    f"Asesmen_{pemb.get('mata_pelajaran','')}_{pemb.get('kelas','')}.xlsx",
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    "rpm_xlsx_dl",
                )
        except Exception as exc:
            st.error(f"Ekspor XLSX gagal: {exc}")

        try:
            payload_txt = txt_export.build_rpm_txt(profil, pemb, data)
            with unduhan[3]:
                komponen.download_bytes(
                    "⬇️ TXT",
                    payload_txt,
                    f"RPM_{pemb.get('mata_pelajaran','')}_{pemb.get('kelas','')}.txt",
                    "text/plain",
                    "rpm_txt_dl",
                )
        except Exception as exc:
            st.error(f"Ekspor TXT gagal: {exc}")

        st.caption(
            "Dokumen mengikuti struktur 19 bagian yang dapat disesuaikan. Format ini bukan satu-satunya format resmi "
            "yang diwajibkan pemerintah."
        )

    st.write("")
    st.caption(
        "Dokumen ini disusun dengan bantuan aplikasi. Guru tetap bertanggung jawab memeriksa CP/ATP, konteks, "
        "dan seluruh isi sebelum digunakan di kelas."
    )
