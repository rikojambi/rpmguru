"""Kumpulan prompt untuk Generator RPM.

Semua prompt menekankan agar model tidak mengarang CP, ATP, atau dasar hukum,
serta mengembalikan JSON yang sesuai struktur aplikasi.
"""

from __future__ import annotations

import json

SYSTEM_PROMPT = """Anda adalah asisten perencanaan pembelajaran untuk guru Indonesia.
Anda membantu menyusun Rencana Pembelajaran Mendalam (RPM) yang realistis, kontekstual,
dan dapat dilaksanakan di kelas.

ATURAN WAJIB:
1. Gunakan bahasa Indonesia yang formal, jelas, dan ringkas.
2. JANGAN mengarang Capaian Pembelajaran (CP), Alur Tujuan Pembelajaran (ATP), nomor
   peraturan, atau kutipan resmi. CP dan ATP hanya boleh diambil dari data yang diberikan guru.
3. JANGAN menyatakan dokumen sudah disahkan, diverifikasi, atau dijamin memenuhi seluruh
   ketentuan pemerintah.
4. Sesuaikan kegiatan dengan sarana, jumlah peserta didik, dan konteks yang diberikan.
   Jangan mewajibkan internet atau perangkat yang tidak tersedia.
5. Gunakan kata kerja operasional yang dapat diamati dan dinilai pada tujuan pembelajaran.
6. Pastikan asesmen selaras dengan tujuan pembelajaran dan utamakan umpan balik formatif.
7. Jangan memaksakan kedelapan dimensi profil lulusan; pilih yang benar-benar relevan.
8. Prinsip berkesadaran, bermakna, dan menggembirakan harus tampak dalam kegiatan konkret,
   bukan sekadar label.
9. Diferensiasi harus realistis: satu pembelajaran inti dengan dukungan berbeda, bukan tiga
   pembelajaran yang sepenuhnya berbeda.
10. Kembalikan HANYA objek JSON valid tanpa penjelasan tambahan, tanpa markdown, tanpa komentar.
11. Jangan menyalin instruksi ini ke dalam jawaban.
"""


def _context(context: dict) -> str:
    return json.dumps(context, ensure_ascii=False, indent=2)


def prompt_identifikasi(context: dict) -> list[dict]:
    schema = {
        "kesiapan": {
            "pengetahuan_awal": "uraian singkat berbasis data guru",
            "tingkat_pemahaman": "uraian",
            "keterampilan_awal": "uraian",
            "kesulitan_belajar": "uraian",
            "kebutuhan_dukungan": "uraian",
        },
        "materi": {
            "jenis_pengetahuan": "faktual/konseptual/prosedural/metakognitif",
            "konsep_utama": ["konsep 1", "konsep 2", "konsep 3"],
            "keterkaitan": "keterkaitan dengan materi lain",
            "penerapan": "penerapan dalam kehidupan nyata",
            "potensi_kontekstual": "peluang pembelajaran kontekstual",
        },
        "dimensi": [
            {
                "nama": "salah satu dari delapan dimensi profil lulusan",
                "alasan": "alasan pemilihan yang spesifik",
                "wujud_aktivitas": "aktivitas siswa yang menunjukkan dimensi tersebut",
            }
        ],
        "catatan": "catatan singkat untuk guru",
    }
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                "Susun IDENTIFIKASI pembelajaran berdasarkan data berikut. "
                "Pilih hanya dimensi profil lulusan yang benar-benar relevan "
                f"(boleh 2-4 dimensi).\n\nDATA:\n{_context(context)}\n\n"
                f"Kembalikan JSON dengan struktur persis seperti ini:\n{json.dumps(schema, ensure_ascii=False, indent=2)}"
            ),
        },
    ]


def prompt_desain(context: dict) -> list[dict]:
    schema = {
        "tujuan": [
            {
                "tp": "tujuan pembelajaran operasional",
                "indikator": "indikator ketercapaian yang dapat diamati",
                "asesmen": "bentuk asesmen yang selaras",
            }
        ],
        "model": {
            "nama": "nama model pembelajaran",
            "alasan": "alasan pemilihan sesuai materi dan tujuan",
            "sintaks": ["langkah 1", "langkah 2", "langkah 3"],
        },
        "kemitraan": [{"pihak": "pihak", "peran": "peran konkret"}],
        "lingkungan": ["lingkungan belajar"],
        "digital": [{"alat": "alat/media", "pemanfaatan": "cara pakai, sesuaikan fasilitas"}],
        "prinsip": [{"prinsip": "Berkesadaran/Bermakna/Menggembirakan", "wujud": "wujud konkret"}],
        "catatan": "catatan singkat",
    }
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                "Susun DESAIN pembelajaran (tujuan, model pedagogis, kemitraan, lingkungan, "
                "pemanfaatan digital, dan prinsip pembelajaran). Tujuan harus mengacu pada CP, "
                "ATP, dan TP dari guru, memakai kata kerja operasional, serta selaras dengan asesmen. "
                "Pilih model yang paling cocok dan sebutkan alasannya. Sesuaikan digital dengan sarana.\n\n"
                f"KONTEKS:\n{_context(context)}\n\n"
                f"Kembalikan JSON dengan struktur persis seperti ini:\n{json.dumps(schema, ensure_ascii=False, indent=2)}"
            ),
        },
    ]


def prompt_pengalaman(context: dict) -> list[dict]:
    tahap_schema = {
        "aktivitas_guru": "langkah guru yang konkret",
        "aktivitas_siswa": "langkah siswa yang konkret",
        "alokasi": "mis. 25 menit",
        "media": "media dan sumber belajar",
        "dimensi": "dimensi profil lulusan yang dikembangkan",
        "prinsip": "prinsip yang tampak dan bagaimana",
        "bukti": "bukti ketercapaian yang dapat diamati",
    }
    schema = {
        "memahami": tahap_schema,
        "mengaplikasi": tahap_schema,
        "merefleksi": tahap_schema,
        "catatan": "catatan singkat",
    }
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                "Susun PENGALAMAN BELAJAR dengan tiga tahap: memahami, mengaplikasi, dan merefleksi. "
                "Aktivitas harus selaras dengan tujuan dan model pembelajaran, memuat aktivitas guru dan "
                "siswa, alokasi waktu, media, dimensi profil lulusan, prinsip pembelajaran yang benar-benar "
                "tampak, serta bukti ketercapaian. Total alokasi harus sama dengan alokasi waktu yang "
                "diberikan guru. Jangan memaksakan proyek besar bila waktu terbatas.\n\n"
                f"KONTEKS:\n{_context(context)}\n\n"
                f"Kembalikan JSON dengan struktur persis seperti ini:\n{json.dumps(schema, ensure_ascii=False, indent=2)}"
            ),
        },
    ]


def prompt_asesmen(context: dict) -> list[dict]:
    jenis_schema = {
        "tujuan": "tujuan asesmen",
        "instrumen": "bentuk instrumen",
        "soal": ["butir soal atau tugas"],
        "kunci": ["kunci/rambu jawaban; tulis 'Sesuaikan dengan sumber belajar' bila tidak pasti"],
        "pedoman": "pedoman penskoran",
        "rubrik": [{"kriteria": "kriteria", "deskripsi": "deskripsi capaian"}],
        "kktp": "kriteria ketercapaian tujuan pembelajaran",
    }
    schema = {"awal": jenis_schema, "proses": jenis_schema, "akhir": jenis_schema, "catatan": "catatan"}
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                "Susun ASESMEN AWAL (diagnostik kognitif dan nonkognitif serta pertanyaan pemantik), "
                "ASESMEN PROSES (formatif), dan ASESMEN AKHIR (sumatif). Setiap asesmen memuat tujuan, "
                "instrumen, soal/tugas, kunci atau rambu jawaban, pedoman penskoran, rubrik, dan KKTP. "
                "Selaraskan dengan tujuan pembelajaran. Jangan mengarang fakta pada kunci jawaban; "
                "gunakan rambu jawaban bila jawaban bergantung pada sumber yang dipakai guru.\n\n"
                f"KONTEKS:\n{_context(context)}\n\n"
                f"Kembalikan JSON dengan struktur persis seperti ini:\n{json.dumps(schema, ensure_ascii=False, indent=2)}"
            ),
        },
    ]


def prompt_diferensiasi(context: dict) -> list[dict]:
    schema = {
        "ringkasan": "prinsip diferensiasi yang dipakai",
        "tingkat": [
            {
                "tingkat": "Perlu bimbingan",
                "kesiapan": "ciri kesiapan siswa pada tingkat ini",
                "kompleksitas": "penyesuaian kompleksitas tugas",
                "scaffolding": "dukungan konkret",
                "sumber": "variasi sumber belajar",
                "pengelompokan": "pengelompokan fleksibel",
                "produk": "pilihan produk/hasil",
            },
            {"tingkat": "Berkembang", "kesiapan": "", "kompleksitas": "", "scaffolding": "", "sumber": "", "pengelompokan": "", "produk": ""},
            {"tingkat": "Mahir", "kesiapan": "", "kompleksitas": "", "scaffolding": "", "sumber": "", "pengelompokan": "", "produk": ""},
        ],
        "catatan": "catatan pelaksanaan",
    }
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                "Susun DIFERENSIASI untuk tiga tingkat: Perlu bimbingan, Berkembang, dan Mahir. "
                "Bedakan kesiapan, kompleksitas tugas, scaffolding, sumber belajar, pengelompokan fleksibel, "
                "dan pilihan produk. Diferensiasi harus realistis untuk satu pembelajaran inti, bukan tiga "
                "pembelajaran terpisah.\n\n"
                f"KONTEKS:\n{_context(context)}\n\n"
                f"Kembalikan JSON dengan struktur persis seperti ini:\n{json.dumps(schema, ensure_ascii=False, indent=2)}"
            ),
        },
    ]


def prompt_lkpd(context: dict) -> list[dict]:
    schema = {
        "judul": "judul LKPD",
        "identitas": "identitas peserta didik dan pembelajaran",
        "tujuan": "tujuan pembelajaran yang relevan",
        "petunjuk": "petunjuk pengerjaan",
        "masalah": "permasalahan kontekstual",
        "memahami": "aktivitas memahami",
        "mengaplikasi": "aktivitas mengaplikasi",
        "merefleksi": "aktivitas merefleksi",
        "pertanyaan": ["pertanyaan analisis 1", "pertanyaan analisis 2"],
        "kesimpulan": "panduan menyusun kesimpulan",
        "penilaian": "ketentuan penilaian dan rubrik ringkas",
    }
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                "Susun LKPD yang dapat langsung dipakai siswa, berdasarkan RPM berikut. "
                "Gunakan bahasa yang sesuai jenjang, permasalahan kontekstual dari lingkungan sekolah, "
                "dan aktivitas memahami-mengaplikasi-merefleksi. Sertakan pertanyaan analisis dan "
                "ketentuan penilaian.\n\n"
                f"KONTEKS:\n{_context(context)}\n\n"
                f"Kembalikan JSON dengan struktur persis seperti ini:\n{json.dumps(schema, ensure_ascii=False, indent=2)}"
            ),
        },
    ]


def prompt_refleksi(context: dict) -> list[dict]:
    schema = {
        "siswa": ["pertanyaan refleksi peserta didik"],
        "guru": ["pertanyaan refleksi guru"],
        "catatan": "catatan penggunaan",
    }
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                "Susun REFLEKSI peserta didik dan guru yang spesifik untuk pembelajaran ini. "
                "Refleksi siswa mencakup apa yang dipelajari, apa yang dipahami, penerapan, kesulitan, "
                "dan rencana perbaikan. Refleksi guru mencakup ketercapaian tujuan, efektivitas aktivitas, "
                "keterlibatan siswa, hasil asesmen, dan perbaikan berikutnya.\n\n"
                f"KONTEKS:\n{_context(context)}\n\n"
                f"Kembalikan JSON dengan struktur persis seperti ini:\n{json.dumps(schema, ensure_ascii=False, indent=2)}"
            ),
        },
    ]


def prompt_validasi(context: dict) -> list[dict]:
    schema = {
        "ringkasan": "penilaian ringkas kualitas RPM",
        "temuan": [
            {
                "aspek": "aspek yang diperiksa",
                "status": "Sudah sesuai / Perlu perbaikan / Belum tersedia",
                "catatan": "alasan berbasis bukti dari dokumen",
                "rekomendasi": "perbaikan spesifik",
            }
        ],
        "disclaimer": "peringatan bahwa ini bukan pengesahan resmi",
    }
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                "Lakukan tinjauan kualitas RPM berikut. Periksa keselarasan CP-ATP-TP, keterukuran tujuan, "
                "kesesuaian model, aktivitas, kehadiran memahami-mengaplikasi-merefleksi, prinsip "
                "berkesadaran-bermakna-menggembirakan, dimensi profil lulusan, asesmen, alokasi waktu, "
                "diferensiasi, dan kelayakan sarana. Berikan temuan spesifik dan rekomendasi. "
                "Jangan menyatakan dokumen disahkan secara resmi.\n\n"
                f"KONTEKS:\n{_context(context)}\n\n"
                f"Kembalikan JSON dengan struktur persis seperti ini:\n{json.dumps(schema, ensure_ascii=False, indent=2)}"
            ),
        },
    ]


def prompt_rekomendasi_model(context: dict) -> list[dict]:
    schema = {
        "rekomendasi": [
            {"nama": "nama model", "alasan": "alasan", "kesesuaian": "tinggi/sedang"}
        ]
    }
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                "Beri 2-3 rekomendasi model pembelajaran berdasarkan karakteristik materi, tujuan, "
                "alokasi waktu, dan sarana. Jangan memilih model yang menuntut waktu atau alat yang tidak tersedia.\n\n"
                f"KONTEKS:\n{_context(context)}\n\n"
                f"Kembalikan JSON:\n{json.dumps(schema, ensure_ascii=False, indent=2)}"
            ),
        },
    ]
