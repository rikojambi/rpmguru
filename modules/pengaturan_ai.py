"""Halaman Pengaturan AI Lokal (Ollama)."""

from __future__ import annotations

import streamlit as st

import config
from ai.ollama_client import OllamaClient, OllamaError
from database import db
from modules import komponen


def render() -> None:
    komponen.page_header(
        "Pengaturan AI Lokal",
        "Aplikasi hanya mengirim permintaan ke server Ollama di komputer Anda. Tidak ada layanan berbayar.",
        "🤖",
    )

    settings = db.get_settings()
    status = komponen.status_ollama()
    url = settings.get("ollama_url", "http://localhost:11434")
    model = settings.get("ollama_model", "qwen2.5:7b")

    kiri, kanan = st.columns([1.4, 1])

    with kiri:
        if status["ok"] and status["model_installed"]:
            komponen.info(f"Ollama aktif di <b>{url}</b>. Model <b>{model}</b> terpasang dan siap dipakai.", "success")
        elif status["ok"]:
            komponen.info(
                f"Ollama aktif, tetapi model <b>{model}</b> belum terpasang. "
                f"Model tersedia: {', '.join(status['models']) or 'belum ada'}.",
                "warning",
            )
        else:
            komponen.info(f"Belum terhubung: {status['message']}", "warning")

        with st.form("form_pengaturan_ai"):
            st.markdown("#### Server Ollama")
            base_url = st.text_input(
                "Alamat server Ollama",
                value=url,
                help="Bawaan: http://localhost:11434. Gunakan alamat lokal, bukan layanan internet.",
            )

            st.markdown("#### Model dan Parameter")
            opsi = list(dict.fromkeys([model] + status.get("models", []) + ["qwen2.5:7b"]))
            indeks = opsi.index(model) if model in opsi else 0
            pilihan = st.selectbox("Model AI", options=opsi, index=indeks)
            manual = st.text_input(
                "Atau ketik nama model lain",
                value="",
                placeholder="contoh: llama3.1:8b",
                help="Kosongkan bila memakai pilihan di atas.",
            )
            temperature = st.slider(
                "Temperature (kreativitas)", min_value=0.0, max_value=1.0,
                value=float(settings.get("temperature", 0.4)), step=0.05,
                help="Nilai rendah lebih konsisten; nilai tinggi lebih bervariasi. Untuk RPM, 0.2-0.5 disarankan.",
            )
            num_predict = st.slider(
                "Panjang respons maksimum (token)", min_value=500, max_value=8000,
                value=int(settings.get("num_predict", 2000)), step=100,
                help="Naikkan bila respons terpotong. Nilai besar membutuhkan waktu lebih lama.",
            )
            timeout = st.slider(
                "Batas waktu permintaan (detik)", min_value=30, max_value=600,
                value=int(settings.get("timeout", 180)), step=30,
            )

            simpan = st.form_submit_button("💾 Simpan Pengaturan", type="primary", width="stretch")

        if simpan:
            model_final = manual.strip() or pilihan
            db.set_settings(
                {
                    "ollama_url": base_url.strip() or "http://localhost:11434",
                    "ollama_model": model_final,
                    "temperature": str(temperature),
                    "num_predict": str(num_predict),
                    "timeout": str(timeout),
                }
            )
            db.log_activity("Simpan pengaturan AI", f"{model_final} @ {base_url}")
            komponen.reset_ollama_cache()
            st.success("Pengaturan AI disimpan.")
            st.rerun()

        st.write("")
        tombol = st.columns([1, 1, 1.2])
        with tombol[0]:
            if st.button("🔌 Periksa Koneksi", width="stretch"):
                komponen.reset_ollama_cache()
                st.rerun()
        with tombol[1]:
            uji = st.button("🧪 Uji AI", type="secondary", width="stretch")
        with tombol[2]:
            if st.button("↩ Bawaan", width="stretch"):
                db.set_settings(
                    {
                        "ollama_url": config.DEFAULT_SETTINGS["ollama_url"],
                        "ollama_model": config.DEFAULT_SETTINGS["ollama_model"],
                        "temperature": config.DEFAULT_SETTINGS["temperature"],
                        "num_predict": config.DEFAULT_SETTINGS["num_predict"],
                        "timeout": config.DEFAULT_SETTINGS["timeout"],
                    }
                )
                komponen.reset_ollama_cache()
                st.rerun()

        if uji:
            with st.spinner("Menguji model AI..."):
                client = komponen.get_ai_client()
                ok, pesan = client.test()
            if ok:
                st.success(pesan)
            else:
                st.error(pesan)
                st.caption("Aplikasi tetap dapat digunakan dengan draf offline pada setiap tahap generator.")

    with kanan:
        st.markdown("### Ringkasan Status")
        status2 = komponen.status_ollama()
        st.markdown(
            f"""
            <div class="status-panel">
                <div class="status-row"><span>Server</span><b>{url}</b></div>
                <div class="status-row"><span>Koneksi</span><b>{'Aktif' if status2['ok'] else 'Tidak aktif'}</b></div>
                <div class="status-row"><span>Model aktif</span><b>{model}</b></div>
                <div class="status-row"><span>Model terpasang</span><b>{'Ya' if status2['model_installed'] else 'Tidak'}</b></div>
                <div class="status-row"><span>Temperature</span><b>{settings.get('temperature')}</b></div>
                <div class="status-row"><span>Maks. token</span><b>{settings.get('num_predict')}</b></div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.write("")
        st.markdown("### Model Terpasang")
        if status2["models"]:
            for item in status2["models"]:
                tanda = "●" if item.split(":")[0] == model.split(":")[0] else "○"
                st.markdown(
                    f'<div class="model-row"><span>{tanda}</span> <code>{item}</code></div>',
                    unsafe_allow_html=True,
                )
        else:
            st.caption("Belum ada model yang terdeteksi.")

        st.write("")
        with st.expander("Panduan singkat Ollama", expanded=False):
            st.markdown(
                """
                1. Pasang Ollama dari situs resmi Ollama di komputer Anda (sekali saja).
                2. Buka PowerShell, lalu jalankan:
                   ```
                   ollama pull qwen2.5:7b
                   ```
                3. Pastikan Ollama berjalan. Perintah `ollama serve` dapat dipakai bila layanan belum aktif.
                4. Klik **Periksa Koneksi**, pilih model, lalu **Uji AI**.
                5. Bila komputer memiliki RAM terbatas, gunakan model yang lebih kecil, misalnya `qwen2.5:3b`.

                Aplikasi tidak mengirim data ke internet. Model diunduh sekali melalui Ollama, setelah itu
                inferensi berjalan lokal.
                """
            )

        st.write("")
        st.markdown("### Privasi")
        st.caption(
            "Data guru, siswa, dan dokumen hanya disimpan di komputer ini. Permintaan AI hanya menuju "
            "alamat server Ollama yang Anda isi. Jangan mengisi alamat layanan AI berbayar atau cloud."
        )

    st.write("")
    st.markdown("### Riwayat Generasi AI")
    riwayat = db.list_ai_history(15)
    if not riwayat:
        st.caption("Belum ada riwayat. Riwayat tercatat otomatis saat generator AI dipakai.")
    else:
        for item in riwayat:
            status_teks = "berhasil" if item.get("status") == "sukses" else item.get("status", "")
            with st.expander(
                f"{item.get('created_at','')} · {item.get('tahap','')} · {item.get('model','')} · {status_teks}"
            ):
                st.markdown(f"**Status:** {status_teks}")
                if item.get("response"):
                    st.text_area(
                        "Ringkasan respons",
                        value=item.get("response", "")[:3000],
                        height=160,
                        disabled=True,
                        key=f"hist_{item['id']}",
                    )
                else:
                    st.caption("Tidak ada respons tersimpan.")

    st.write("")
    komponen.info(
        "Hasil AI adalah draf. Periksa kebenaran konsep, kesesuaian dengan CP/ATP resmi, dan konteks kelas "
        "sebelum dokumen digunakan.",
        "info",
    )
