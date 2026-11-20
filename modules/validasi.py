"""Validasi otomatis konsistensi RPM dan halaman validasi."""

from __future__ import annotations

import json
import re

import streamlit as st

import config
from ai import generator as ai_generator
from database import db
from modules import editor, komponen
from modules.editor import ensure_structure


# ---------------------------------------------------------------------------
# Aturan validasi
# ---------------------------------------------------------------------------
def _txt(value) -> str:
    if isinstance(value, list):
        return " ".join(_txt(v) for v in value)
    if isinstance(value, dict):
        return " ".join(_txt(v) for v in value.values())
    return str(value or "").strip()


def _words(value) -> set[str]:
    return {w for w in re.findall(r"[a-zA-ZÀ-ÿ]{4,}", _txt(value).lower())}


def _ceklis(aspek: str, status: str, catatan: str, rekomendasi: str) -> dict:
    return {
        "aspek": aspek,
        "status": status,
        "catatan": catatan,
        "rekomendasi": rekomendasi,
    }


def _tahap(data: dict, key: str) -> dict:
    section = data.get("pengalaman") or {}
    value = section.get(key) if isinstance(section, dict) else {}
    return value if isinstance(value, dict) else {}


def validate_rpm(pemb: dict, data: dict) -> list[dict]:
    data = ensure_structure(data)
    desain = data.get("desain") or {}
    pengalaman = data.get("pengalaman") or {}
    asesmen = data.get("asesmen") or {}
    ident = data.get("identifikasi") or {}
    dif = data.get("diferensiasi") or {}
    checks: list[dict] = []

    cp = _txt(pemb.get("cp"))
    atp = _txt(pemb.get("atp"))
    tp_teacher = _txt(pemb.get("tp"))
    tp_desain = " ".join(
        _txt(row.get("tp")) for row in (desain.get("tujuan") or []) if isinstance(row, dict)
    )
    materi = _txt(pemb.get("materi_pokok"))

    # 1. Keselarasan CP-ATP-TP
    if not cp:
        checks.append(_ceklis(
            "Keselarasan CP, ATP, dan TP", config.VALIDASI_BELUM,
            "CP belum diisi pada data pembelajaran.",
            "Masukkan CP dari dokumen guru/sekolah. Jangan memakai CP buatan AI.",
        ))
    elif not atp:
        checks.append(_ceklis(
            "Keselarasan CP, ATP, dan TP", config.VALIDASI_PERBAIKAN,
            "CP tersedia, tetapi ATP belum diisi.",
            "Tambahkan ATP yang diturunkan dari CP agar alur tujuan terlihat.",
        ))
    elif not (tp_teacher or tp_desain):
        checks.append(_ceklis(
            "Keselarasan CP, ATP, dan TP", config.VALIDASI_BELUM,
            "CP dan ATP tersedia, tetapi tujuan pembelajaran belum dirumuskan.",
            "Rumuskan TP pada tahap Desain, atau isi TP pada data pembelajaran.",
        ))
    else:
        irisan = _words(cp) & _words(tp_teacher + " " + tp_desain + " " + materi)
        if len(irisan) <= 1:
            checks.append(_ceklis(
                "Keselarasan CP, ATP, dan TP", config.VALIDASI_PERBAIKAN,
                "TP belum menunjukkan keterkaitan kata kunci yang jelas dengan CP/materi.",
                "Periksa apakah TP benar-benar diturunkan dari CP dan ATP. Gunakan istilah kunci materi secara konsisten.",
            ))
        else:
            checks.append(_ceklis(
                "Keselarasan CP, ATP, dan TP", config.VALIDASI_SESUAI,
                f"CP, ATP, dan TP tersedia serta memiliki keterkaitan kata kunci ({', '.join(sorted(irisan)[:5])}).",
                "Lakukan reviu manual untuk memastikan cakupan CP tidak terlewat.",
            ))

    # 2. Keterukuran tujuan
    tujuan_rows = [row for row in (desain.get("tujuan") or []) if isinstance(row, dict) and _txt(row.get("tp"))]
    if not tujuan_rows:
        checks.append(_ceklis(
            "Keterukuran tujuan pembelajaran", config.VALIDASI_BELUM,
            "Tujuan pembelajaran belum tersedia di tahap Desain.",
            "Susun TP dengan kata kerja operasional yang dapat diamati dan dinilai.",
        ))
    else:
        terukur, kabur = 0, []
        for row in tujuan_rows:
            teks = _txt(row.get("tp")).lower()
            punya_operasional = any(verb in teks for verb in config.KATA_KERJA_OPERASIONAL)
            punya_kabur = any(verb in teks for verb in config.KATA_TIDAK_TERUKUR)
            if punya_operasional and not (punya_kabur and not punya_operasional):
                terukur += 1
            else:
                kabur.append(_txt(row.get("tp"))[:80])
        if terukur == len(tujuan_rows):
            checks.append(_ceklis(
                "Keterukuran tujuan pembelajaran", config.VALIDASI_SESUAI,
                f"Semua ({terukur}) tujuan memuat kata kerja operasional.",
                "Pastikan indikator benar-benar dapat diamati saat pembelajaran.",
            ))
        else:
            checks.append(_ceklis(
                "Keterukuran tujuan pembelajaran", config.VALIDASI_PERBAIKAN,
                f"{len(kabur)} tujuan belum memuat kata kerja operasional yang jelas.",
                "Ganti kata seperti 'memahami' dengan kata kerja terukur, misalnya 'menjelaskan', 'menerapkan', atau 'menyusun'.",
            ))

    # 3. Kesesuaian model
    model = desain.get("model") or {}
    nama_model = _txt(model.get("nama"))
    sintaks = model.get("sintaks") or []
    if not nama_model:
        checks.append(_ceklis(
            "Kesesuaian model pembelajaran", config.VALIDASI_BELUM,
            "Model pembelajaran belum dipilih.",
            "Pilih model yang sesuai karakteristik materi dan ketersediaan waktu.",
        ))
    elif not sintaks:
        checks.append(_ceklis(
            "Kesesuaian model pembelajaran", config.VALIDASI_PERBAIKAN,
            f"Model {nama_model} dipilih, tetapi sintaks belum diuraikan.",
            "Tuliskan langkah model agar kegiatan dapat dilaksanakan secara konsisten.",
        ))
    else:
        checks.append(_ceklis(
            "Kesesuaian model pembelajaran", config.VALIDASI_SESUAI,
            f"Model {nama_model} memiliki {len(sintaks)} langkah sintaks.",
            "Pastikan setiap langkah sintaks benar-benar muncul pada pengalaman belajar.",
        ))

    # 4. Aktivitas selaras tujuan
    aktivitas_lengkap = 0
    for key in ("memahami", "mengaplikasi", "merefleksi"):
        tahap = _tahap(data, key)
        if _txt(tahap.get("aktivitas_siswa")) and _txt(tahap.get("aktivitas_guru")):
            aktivitas_lengkap += 1
    if aktivitas_lengkap == 3:
        checks.append(_ceklis(
            "Kesesuaian aktivitas dengan tujuan", config.VALIDASI_SESUAI,
            "Aktivitas guru dan peserta didik tersedia pada ketiga tahap.",
            "Cocokkan kembali setiap aktivitas dengan indikator tujuan; hapus aktivitas yang tidak mendukung.",
        ))
    elif aktivitas_lengkap:
        checks.append(_ceklis(
            "Kesesuaian aktivitas dengan tujuan", config.VALIDASI_PERBAIKAN,
            f"Baru {aktivitas_lengkap} dari 3 tahap yang memiliki aktivitas guru dan siswa.",
            "Lengkapi tahap yang masih kosong dan pastikan aktivitas mengarah pada TP.",
        ))
    else:
        checks.append(_ceklis(
            "Kesesuaian aktivitas dengan tujuan", config.VALIDASI_BELUM,
            "Aktivitas pembelajaran belum tersedia.",
            "Susun aktivitas pada tahap Memahami, Mengaplikasi, dan Merefleksi.",
        ))

    # 5. Tiga pengalaman
    jumlah_pengalaman = sum(
        1 for key in ("memahami", "mengaplikasi", "merefleksi")
        if _txt(_tahap(data, key).get("aktivitas_siswa"))
    )
    if jumlah_pengalaman == 3:
        checks.append(_ceklis(
            "Kehadiran memahami, mengaplikasi, merefleksi", config.VALIDASI_SESUAI,
            "Ketiga pengalaman belajar tersedia.",
            "Periksa porsi waktu: memahami membangun konsep, mengaplikasi memberi konteks nyata, merefleksi menutup proses.",
        ))
    elif jumlah_pengalaman:
        checks.append(_ceklis(
            "Kehadiran memahami, mengaplikasi, merefleksi", config.VALIDASI_PERBAIKAN,
            f"Baru {jumlah_pengalaman} dari 3 pengalaman belajar yang terisi.",
            "Lengkapi ketiga pengalaman; jangan hanya menambahkan label tanpa aktivitas.",
        ))
    else:
        checks.append(_ceklis(
            "Kehadiran memahami, mengaplikasi, merefleksi", config.VALIDASI_BELUM,
            "Pengalaman belajar belum disusun.",
            "Buat aktivitas untuk memahami, mengaplikasi, dan merefleksi.",
        ))

    # 6. Prinsip
    prinsip_rows = [row for row in (desain.get("prinsip") or []) if isinstance(row, dict)]
    prinsip_terisi = {
        _txt(row.get("prinsip")).split(":")[0].strip().lower(): _txt(row.get("wujud"))
        for row in prinsip_rows
    }
    sesuai_prinsip = []
    for prinsip in config.PRINSIP_PEMBELAJARAN:
        wujud = prinsip_terisi.get(prinsip.lower(), "")
        if len(wujud) >= 25:
            sesuai_prinsip.append(prinsip)
    if len(sesuai_prinsip) == 3:
        checks.append(_ceklis(
            "Prinsip berkesadaran, bermakna, menggembirakan", config.VALIDASI_SESUAI,
            "Ketiga prinsip memiliki wujud konkret pada desain.",
            "Pastikan wujud tersebut benar-benar muncul pada langkah kegiatan, bukan hanya di tabel desain.",
        ))
    elif sesuai_prinsip:
        checks.append(_ceklis(
            "Prinsip berkesadaran, bermakna, menggembirakan", config.VALIDASI_PERBAIKAN,
            f"Prinsip yang memiliki wujud konkret: {', '.join(sesuai_prinsip)}. Lengkapi sisanya.",
            "Tuliskan tindakan nyata guru/siswa untuk setiap prinsip; hindari sekadar label.",
        ))
    else:
        checks.append(_ceklis(
            "Prinsip berkesadaran, bermakna, menggembirakan", config.VALIDASI_BELUM,
            "Wujud konkret ketiga prinsip belum tersedia.",
            "Tambahkan wujud prinsip pada desain dan pastikan tercermin di kegiatan.",
        ))

    # 7. Dimensi
    dimensi_rows = [row for row in (ident.get("dimensi") or []) if isinstance(row, dict) and _txt(row.get("nama"))]
    if not dimensi_rows:
        checks.append(_ceklis(
            "Keterkaitan dimensi profil lulusan", config.VALIDASI_BELUM,
            "Belum ada dimensi profil lulusan yang dipilih.",
            "Pilih 1-4 dimensi yang relevan dan jelaskan wujudnya dalam aktivitas.",
        ))
    else:
        lengkap = [row for row in dimensi_rows if _txt(row.get("alasan")) and _txt(row.get("wujud_aktivitas"))]
        if lengkap:
            checks.append(_ceklis(
                "Keterkaitan dimensi profil lulusan", config.VALIDASI_SESUAI,
                f"{len(lengkap)} dimensi dipilih dengan alasan dan wujud aktivitas.",
                "Pastikan dimensi yang dipilih benar-benar tampak, bukan sekadar daftar.",
            ))
        else:
            checks.append(_ceklis(
                "Keterkaitan dimensi profil lulusan", config.VALIDASI_PERBAIKAN,
                "Dimensi dipilih, tetapi alasan/wujud aktivitas belum lengkap.",
                "Lengkapi alasan pemilihan dan aktivitas siswa yang menunjukkan dimensi tersebut.",
            ))

    # 8. Asesmen
    asesmen_lengkap = 0
    for key in ("awal", "proses", "akhir"):
        item = asesmen.get(key) or {}
        if _txt(item.get("tujuan")) and _txt(item.get("instrumen")) and (item.get("rubrik") or item.get("soal")):
            asesmen_lengkap += 1
    kktp_ada = sum(1 for key in ("awal", "proses", "akhir") if _txt((asesmen.get(key) or {}).get("kktp")))
    if asesmen_lengkap == 3 and kktp_ada >= 2:
        checks.append(_ceklis(
            "Kesesuaian asesmen dengan tujuan", config.VALIDASI_SESUAI,
            "Asesmen awal, proses, dan akhir tersedia dengan instrumen/rubrik; KKTP tersedia pada sebagian besar asesmen.",
            "Cocokkan butir soal/tugas dengan setiap indikator tujuan. Verifikasi kunci jawaban dengan sumber belajar.",
        ))
    elif asesmen_lengkap:
        checks.append(_ceklis(
            "Kesesuaian asesmen dengan tujuan", config.VALIDASI_PERBAIKAN,
            f"Baru {asesmen_lengkap} dari 3 jenis asesmen yang lengkap.",
            "Lengkapi tujuan, instrumen, soal/tugas, rubrik, dan KKTP untuk setiap jenis asesmen.",
        ))
    else:
        checks.append(_ceklis(
            "Kesesuaian asesmen dengan tujuan", config.VALIDASI_BELUM,
            "Asesmen belum disusun.",
            "Buat asesmen awal, proses (formatif), dan akhir yang selaras dengan TP.",
        ))

    # 9. Alokasi waktu
    total = ai_generator.total_menit(pemb)
    stage_minutes = []
    for key in ("memahami", "mengaplikasi", "merefleksi"):
        angka = re.findall(r"\d+", _txt(_tahap(data, key).get("alokasi")))
        stage_minutes.append(int(angka[0]) if angka else 0)
    jumlah_stage = sum(stage_minutes)
    if not any(stage_minutes):
        checks.append(_ceklis(
            "Kesesuaian alokasi waktu", config.VALIDASI_BELUM,
            f"Total alokasi pembelajaran {total} menit, tetapi alokasi tiap tahap belum diisi.",
            "Bagi alokasi waktu ke tahap memahami, mengaplikasi, dan merefleksi.",
        ))
    elif abs(jumlah_stage - total) <= max(5, total * 0.1):
        checks.append(_ceklis(
            "Kesesuaian alokasi waktu", config.VALIDASI_SESUAI,
            f"Total alokasi tahap ({jumlah_stage} menit) sesuai dengan alokasi pembelajaran ({total} menit).",
            "Sisakan waktu transisi dan pengelolaan kelas; alokasi di atas kertas sering lebih cepat di kelas.",
        ))
    else:
        checks.append(_ceklis(
            "Kesesuaian alokasi waktu", config.VALIDASI_PERBAIKAN,
            f"Jumlah alokasi tahap {jumlah_stage} menit tidak sesuai total {total} menit.",
            "Sesuaikan pembagian waktu. Bila total lebih dari 120 menit, pertimbangkan lebih dari satu pertemuan.",
        ))

    # 10. Diferensiasi
    tingkat = [row for row in (dif.get("tingkat") or []) if isinstance(row, dict) and _txt(row.get("tingkat"))]
    scaffolding = [row for row in tingkat if _txt(row.get("scaffolding"))]
    if len(tingkat) >= 3 and len(scaffolding) >= 3:
        checks.append(_ceklis(
            "Kelengkapan diferensiasi", config.VALIDASI_SESUAI,
            "Tiga tingkat dukungan tersedia dengan scaffolding.",
            "Pastikan diferensiasi tidak menambah beban administratif berlebihan; fokus pada dukungan yang benar-benar dipakai.",
        ))
    elif tingkat:
        checks.append(_ceklis(
            "Kelengkapan diferensiasi", config.VALIDASI_PERBAIKAN,
            f"Baru {len(tingkat)} tingkat dukungan yang tersedia.",
            "Lengkapi minimal tiga tingkat: perlu bimbingan, berkembang, dan mahir.",
        ))
    else:
        checks.append(_ceklis(
            "Kelengkapan diferensiasi", config.VALIDASI_BELUM,
            "Diferensiasi belum disusun.",
            "Susun satu pembelajaran inti dengan tiga tingkat dukungan yang realistis.",
        ))

    # 11. Sarana dan prasarana
    sarana = _txt(pemb.get("sarana")).lower()
    digital = desain.get("digital") or []
    digital_text = " ".join(_txt(row.get("alat")) + " " + _txt(row.get("pemanfaatan")) for row in digital if isinstance(row, dict)).lower()
    if not sarana:
        checks.append(_ceklis(
            "Kelayakan sarana dan prasarana", config.VALIDASI_BELUM,
            "Sarana dan prasarana belum diisi.",
            "Tuliskan fasilitas nyata yang tersedia agar kegiatan tidak menuntut alat yang tidak ada.",
        ))
    elif ("internet" in digital_text or "wifi" in digital_text) and any(
        frasa in sarana for frasa in ("tidak ada internet", "tanpa internet", "terbatas", "tidak tersedia")
    ):
        checks.append(_ceklis(
            "Kelayakan sarana dan prasarana", config.VALIDASI_PERBAIKAN,
            "Pemanfaatan digital menyebut internet, sementara sarana menandakan keterbatasan koneksi.",
            "Ganti kegiatan daring dengan media luring, atau tandai sebagai kegiatan opsional.",
        ))
    elif ("laboratorium" in digital_text or "lab" in digital_text) and "lab" not in sarana:
        checks.append(_ceklis(
            "Kelayakan sarana dan prasarana", config.VALIDASI_PERBAIKAN,
            "Kegiatan menyebut laboratorium, tetapi tidak tercantum pada sarana.",
            "Pastikan laboratorium tersedia dan dapat dijadwalkan; bila tidak, gunakan ruang kelas.",
        ))
    else:
        checks.append(_ceklis(
            "Kelayakan sarana dan prasarana", config.VALIDASI_SESUAI,
            "Sarana diisi dan pemanfaatan digital tidak melebihi fasilitas yang tercantum.",
            "Lakukan pengecekan langsung sebelum pembelajaran, termasuk ketersediaan perangkat.",
        ))

    # 12. Kelengkapan identitas (tambahan)
    wajib = {
        "mata pelajaran": _txt(pemb.get("mata_pelajaran")),
        "kelas": _txt(pemb.get("kelas")),
        "fase": _txt(pemb.get("fase")),
        "materi pokok": _txt(pemb.get("materi_pokok")),
        "alokasi waktu": _txt(pemb.get("alokasi_waktu")),
    }
    kosong = [nama for nama, nilai in wajib.items() if not nilai]
    if kosong:
        checks.append(_ceklis(
            "Kelengkapan identitas pembelajaran", config.VALIDASI_PERBAIKAN,
            f"Belum lengkap: {', '.join(kosong)}.",
            "Lengkapi identitas pada Data Pembelajaran agar dokumen siap diekspor.",
        ))
    else:
        checks.append(_ceklis(
            "Kelengkapan identitas pembelajaran", config.VALIDASI_SESUAI,
            "Identitas utama pembelajaran tersedia.",
            "Periksa kembali nama sekolah, guru, dan tahun pelajaran pada profil.",
        ))

    return checks


def ringkasan(checks: list[dict]) -> dict:
    semua = len(checks) or 1
    sesuai = sum(1 for c in checks if c["status"] == config.VALIDASI_SESUAI)
    perbaikan = sum(1 for c in checks if c["status"] == config.VALIDASI_PERBAIKAN)
    belum = sum(1 for c in checks if c["status"] == config.VALIDASI_BELUM)
    skor = round(sesuai / semua * 100)
    return {"sesuai": sesuai, "perbaikan": perbaikan, "belum": belum, "total": len(checks), "skor": skor}


# ---------------------------------------------------------------------------
# Halaman
# ---------------------------------------------------------------------------
def _status_box(status: str) -> tuple[str, str]:
    if status == config.VALIDASI_SESUAI:
        return "tag-ok", "Sesuai"
    if status == config.VALIDASI_PERBAIKAN:
        return "tag-warn", "Perlu perbaikan"
    return "tag-danger", "Belum tersedia"


def render() -> None:
    komponen.page_header(
        "Validasi RPM",
        "Pemeriksaan konsistensi berbasis aturan. Ini bukan pengesahan resmi dan bukan jaminan pemenuhan ketentuan.",
        "✅",
    )
    komponen.show_flash()

    baris = db.list_rpm()
    if not baris:
        komponen.empty_state("Belum ada RPM", "Buat dokumen RPM terlebih dahulu untuk divalidasi.")
        if st.button("Buka Generator RPM", type="primary"):
            komponen.navigate("Generator RPM")
        return

    ids = [r["id"] for r in baris]
    default = st.session_state.get("validasi_rpm_id")
    index = ids.index(default) if default in ids else 0
    rpm_id = st.selectbox(
        "Pilih dokumen RPM",
        ids,
        index=index,
        format_func=lambda x: next(
            (f"{r.get('judul') or 'RPM'} · {r.get('mata_pelajaran','')}" for r in baris if r["id"] == x),
            f"RPM #{x}",
        ),
        key="validasi_rpm_pilih",
    )
    st.session_state["validasi_rpm_id"] = rpm_id
    rpm = db.get_rpm(rpm_id)
    if not rpm:
        return
    pemb = db.get_pembelajaran(rpm.get("pembelajaran_id")) or {}
    data = ensure_structure(json.loads(rpm.get("data_json") or "{}"))

    st.markdown(
        komponen.tag(rpm.get("judul") or "RPM", "info")
        + komponen.tag(f"{pemb.get('mata_pelajaran','-')} · Kelas {pemb.get('kelas','-')}", "neutral")
        + komponen.badge_status(rpm.get("status", "draf")),
        unsafe_allow_html=True,
    )

    tombol = st.columns([1, 1, 2])
    with tombol[0]:
        jalankan = st.button("🔍 Jalankan Validasi", type="primary", width="stretch")
    with tombol[1]:
        buka = st.button("⚙️ Buka Generator", width="stretch")
    with tombol[2]:
        st.caption("Validasi memeriksa struktur dan konsistensi teks. Keputusan akhir tetap pada guru.")

    if buka:
        st.session_state["rpm_id"] = rpm_id
        komponen.navigate("Generator RPM")

    if jalankan or "validasi_hasil" not in st.session_state or st.session_state.get("validasi_untuk") != rpm_id:
        checks = validate_rpm(pemb, data)
        st.session_state["validasi_hasil"] = checks
        st.session_state["validasi_untuk"] = rpm_id

    checks = st.session_state.get("validasi_hasil") or []
    stat = ringkasan(checks)

    st.write("")
    metrik = st.columns(4)
    metrik[0].metric("Skor kesesuaian", f"{stat['skor']}%")
    metrik[1].metric("Sudah sesuai", stat["sesuai"])
    metrik[2].metric("Perlu perbaikan", stat["perbaikan"])
    metrik[3].metric("Belum tersedia", stat["belum"])
    st.progress(stat["skor"] / 100 if stat["total"] else 0)

    if stat["belum"] or stat["perbaikan"]:
        komponen.info(
            "Beberapa aspek belum sesuai. Perbaikan dapat dilakukan langsung di Generator RPM pada tahap terkait.",
            "warning",
        )
    else:
        komponen.info(
            "Semua butir pemeriksaan otomatis terpenuhi. Ini bukan pengesahan resmi; lakukan reviu profesional.",
            "success",
        )

    # Tampilkan per kategori
    kategori_tabs = st.tabs([
        f"Semua ({len(checks)})",
        f"Perlu perbaikan ({stat['perbaikan']})",
        f"Belum tersedia ({stat['belum']})",
        f"Sudah sesuai ({stat['sesuai']})",
    ])
    urutan = [checks, [c for c in checks if c["status"] == config.VALIDASI_PERBAIKAN],
              [c for c in checks if c["status"] == config.VALIDASI_BELUM],
              [c for c in checks if c["status"] == config.VALIDASI_SESUAI]]
    for tab, daftar in zip(kategori_tabs, urutan):
        with tab:
            if not daftar:
                st.caption("Tidak ada butir pada kategori ini.")
                continue
            for item in daftar:
                kelas, label = _status_box(item["status"])
                st.markdown(
                    f"""
                    <div class="rpm-card" style="margin-bottom:0.55rem">
                        <div style="display:flex;justify-content:space-between;gap:0.6rem;align-items:flex-start">
                            <div class="rpm-card-title">{item['aspek']}</div>
                            <span class="tag {kelas}">{label}</span>
                        </div>
                        <div style="font-size:0.83rem;color:#45524b;margin-top:0.3rem">{item['catatan']}</div>
                        <div style="font-size:0.8rem;color:#7a4c0d;margin-top:0.35rem"><b>Rekomendasi:</b> {item['rekomendasi']}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

    st.write("")
    with st.expander("Tinjauan AI tambahan (opsional)", expanded=False):
        ai_siap, ai_pesan = komponen.ai_ready()
        st.caption(
            "Tinjauan AI hanya pendapat tambahan berbasis teks. AI tidak berwenang mengesahkan dokumen. "
            f"{'' if ai_siap else 'AI tidak tersedia: ' + ai_pesan}"
        )
        if st.button("Minta tinjauan AI", disabled=not ai_siap, key=f"validasi_ai_{rpm_id}"):
            client = komponen.get_ai_client()
            with st.spinner("AI meninjau dokumen..."):
                hasil, error = ai_generator.validasi_ai(client, pemb, data, rpm_id)
            if hasil:
                st.session_state[f"validasi_ai_hasil_{rpm_id}"] = hasil
            else:
                st.error(error or "Tinjauan AI tidak berhasil.")
        hasil_ai = st.session_state.get(f"validasi_ai_hasil_{rpm_id}")
        if hasil_ai:
            st.markdown(f"**Ringkasan AI:** {hasil_ai.get('ringkasan', '')}")
            for item in hasil_ai.get("temuan") or []:
                if not isinstance(item, dict):
                    continue
                with st.expander(f"{item.get('aspek','Temuan')} · {item.get('status','')}"):
                    st.write(item.get("catatan", ""))
                    st.caption(f"Rekomendasi: {item.get('rekomendasi','')}")
            st.caption(hasil_ai.get("disclaimer", "Tinjauan AI bukan pengesahan resmi."))

    st.write("")
    with st.expander("Ekspor hasil validasi"):
        from exports import txt_export

        teks = ["HASIL VALIDASI RPM (BUKAN PENGESAHAN RESMI)", "=" * 50, ""]
        teks.append(f"Dokumen: {rpm.get('judul','')}")
        teks.append(f"Skor kesesuaian: {stat['skor']}%")
        teks.append("")
        for item in checks:
            teks.append(f"[{item['status']}] {item['aspek']}")
            teks.append(f"  Catatan: {item['catatan']}")
            teks.append(f"  Rekomendasi: {item['rekomendasi']}")
            teks.append("")
        teks.append("Catatan: hasil ini dihasilkan dari aturan pemeriksaan aplikasi dan/atau AI lokal.")
        teks.append("Bukan pengesahan resmi dan tidak menjamin pemenuhan seluruh ketentuan pemerintah.")
        komponen.download_bytes(
            "⬇️ Unduh hasil validasi (TXT)",
            "\n".join(teks).encode("utf-8"),
            f"Validasi_{pemb.get('mata_pelajaran','')}_{pemb.get('kelas','')}.txt",
            "text/plain",
            f"validasi_txt_{rpm_id}",
        )

    komponen.info(
        "Validasi otomatis tidak menggantikan pertimbangan profesional guru, kepala sekolah, atau pengawas. "
        "Selalu periksa CP/ATP dengan dokumen resmi dan sesuaikan kegiatan dengan kondisi kelas.",
        "info",
    )
