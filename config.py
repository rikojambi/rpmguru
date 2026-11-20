"""Konfigurasi global aplikasi Generator RPM.

Semua path, konstanta kurikulum, dan pengaturan bawaan diletakkan di sini
agar modul lain tidak perlu menduplikasi nilai.
"""

from pathlib import Path

APP_NAME = "Generator RPM"
APP_LONG_NAME = "Generator RPM - Asisten Perencanaan Pembelajaran Mendalam"
APP_VERSION = "1.0.0"

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
BACKUP_DIR = DATA_DIR / "backups"
EXPORT_DIR = DATA_DIR / "exports"
UPLOAD_DIR = DATA_DIR / "uploads"
ASSETS_DIR = BASE_DIR / "assets"
TEMPLATE_DIR = BASE_DIR / "templates"
DB_PATH = DATA_DIR / "generator_rpm.db"

for _folder in (DATA_DIR, BACKUP_DIR, EXPORT_DIR, UPLOAD_DIR, ASSETS_DIR, TEMPLATE_DIR):
    _folder.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Pilihan kurikulum
# ---------------------------------------------------------------------------
JENJANG = ["SD", "MI", "SMP", "MTs", "SMA", "MA", "SMK", "MAK"]
FASE = ["A", "B", "C", "D", "E", "F"]
FASE_KELAS = {
    "A": "Kelas 1-2 SD/MI",
    "B": "Kelas 3-4 SD/MI",
    "C": "Kelas 5-6 SD/MI",
    "D": "Kelas 7-9 SMP/MTs",
    "E": "Kelas 10 SMA/MA/SMK/MAK",
    "F": "Kelas 11-12 SMA/MA/SMK/MAK",
}
KELAS = [str(i) for i in range(1, 13)]
SEMESTER = ["Ganjil", "Genap"]
STATUS_SEKOLAH = ["Negeri", "Swasta"]
KURIKULUM = [
    "Kurikulum Merdeka",
    "Kurikulum Merdeka (Pembelajaran Mendalam)",
    "Kurikulum 2013",
    "Kurikulum Satuan Pendidikan",
]

# ---------------------------------------------------------------------------
# Delapan dimensi profil lulusan
# ---------------------------------------------------------------------------
DIMENSI_PROFIL = [
    "Keimanan dan ketakwaan terhadap Tuhan YME",
    "Kewargaan",
    "Penalaran kritis",
    "Kreativitas",
    "Kolaborasi",
    "Kemandirian",
    "Kesehatan",
    "Komunikasi",
]

DIMENSI_DESKRIPSI = {
    "Keimanan dan ketakwaan terhadap Tuhan YME": (
        "Menghayati nilai keimanan dan ketakwaan serta menerapkannya secara sadar "
        "dalam sikap dan perilaku sehari-hari."
    ),
    "Kewargaan": (
        "Bersikap peduli, bertanggung jawab, dan berkontribusi bagi lingkungan "
        "serta masyarakat."
    ),
    "Penalaran kritis": (
        "Mengolah informasi, mengevaluasi argumen, dan mengambil keputusan "
        "berdasarkan bukti."
    ),
    "Kreativitas": (
        "Menghasilkan gagasan dan karya orisinal serta mencari alternatif solusi."
    ),
    "Kolaborasi": (
        "Bekerja sama, berbagi peran, dan membangun kesepakatan dalam kelompok."
    ),
    "Kemandirian": (
        "Mengelola diri, menetapkan tujuan, dan bertanggung jawab atas proses belajar."
    ),
    "Kesehatan": (
        "Menjaga kesehatan fisik, mental, dan sosial serta menerapkan pola hidup sehat."
    ),
    "Komunikasi": (
        "Menyampaikan gagasan secara jelas dan mendengarkan serta menghargai "
        "pandangan orang lain."
    ),
}

# ---------------------------------------------------------------------------
# Praktik pedagogis dan sintaks model
# ---------------------------------------------------------------------------
MODEL_PEMBELAJARAN = [
    "Problem Based Learning",
    "Project Based Learning",
    "Discovery Learning",
    "Inquiry Learning",
    "Cooperative Learning",
    "Contextual Teaching and Learning",
    "Direct Instruction",
    "Pembelajaran kolaboratif",
    "Model lainnya",
]

SINTAKS_MODEL = {
    "Problem Based Learning": [
        "Orientasi peserta didik pada masalah",
        "Mengorganisasi peserta didik untuk belajar",
        "Membimbing penyelidikan individu dan kelompok",
        "Mengembangkan dan menyajikan hasil karya",
        "Menganalisis dan mengevaluasi proses pemecahan masalah",
    ],
    "Project Based Learning": [
        "Menentukan pertanyaan mendasar",
        "Mendesain perencanaan proyek",
        "Menyusun jadwal",
        "Memonitor kemajuan proyek",
        "Menguji hasil",
        "Mengevaluasi pengalaman",
    ],
    "Discovery Learning": [
        "Stimulasi",
        "Identifikasi masalah",
        "Pengumpulan data",
        "Pengolahan data",
        "Pembuktian",
        "Menarik kesimpulan",
    ],
    "Inquiry Learning": [
        "Merumuskan pertanyaan",
        "Menyusun hipotesis",
        "Mengumpulkan data",
        "Menganalisis data",
        "Menyimpulkan",
        "Mengomunikasikan hasil",
    ],
    "Cooperative Learning": [
        "Menyampaikan tujuan dan memotivasi",
        "Menyajikan informasi",
        "Mengorganisasi kelompok belajar",
        "Membimbing kelompok bekerja dan belajar",
        "Evaluasi hasil belajar",
        "Memberikan penghargaan",
    ],
    "Contextual Teaching and Learning": [
        "Mengaitkan materi dengan konteks nyata",
        "Menemukan makna melalui pengalaman",
        "Melakukan kegiatan bermakna",
        "Bekerja sama",
        "Refleksi",
        "Penilaian autentik",
    ],
    "Direct Instruction": [
        "Menyampaikan tujuan dan mempersiapkan peserta didik",
        "Mendemonstrasikan pengetahuan atau keterampilan",
        "Membimbing pelatihan",
        "Mengecek pemahaman dan memberikan umpan balik",
        "Memberikan kesempatan latihan mandiri",
    ],
    "Pembelajaran kolaboratif": [
        "Membangun kesepakatan belajar",
        "Membentuk kelompok fleksibel",
        "Bekerja bersama dengan peran jelas",
        "Saling memberi umpan balik",
        "Refleksi bersama",
    ],
    "Model lainnya": [
        "Pendahuluan",
        "Kegiatan inti",
        "Penutup",
    ],
}

MODEL_DESKRIPSI = {
    "Problem Based Learning": "Belajar melalui pemecahan masalah kontekstual secara berkelompok.",
    "Project Based Learning": "Belajar melalui proyek bermakna yang menghasilkan produk.",
    "Discovery Learning": "Menemukan konsep melalui pengamatan dan penyelidikan terbimbing.",
    "Inquiry Learning": "Mengembangkan pertanyaan dan menjawabnya melalui penyelidikan.",
    "Cooperative Learning": "Belajar bersama dalam kelompok kecil dengan saling ketergantungan positif.",
    "Contextual Teaching and Learning": "Menghubungkan materi dengan pengalaman dan lingkungan nyata.",
    "Direct Instruction": "Pembelajaran terstruktur dengan demonstrasi dan latihan terbimbing.",
    "Pembelajaran kolaboratif": "Kerja sama antar peserta didik dengan peran dan tanggung jawab bersama.",
    "Model lainnya": "Model pembelajaran lain yang dipilih guru sesuai konteks.",
}

KEMITRAAN = [
    "Antarsiswa",
    "Guru dengan siswa",
    "Orang tua",
    "Dunia usaha dan dunia industri",
    "Masyarakat",
    "Praktisi atau narasumber",
]

LINGKUNGAN = [
    "Ruang kelas",
    "Laboratorium",
    "Bengkel praktik",
    "Lingkungan sekolah",
    "Lingkungan masyarakat",
    "Lingkungan digital",
]

DIGITAL = [
    "Komputer",
    "Smartphone",
    "Internet",
    "Aplikasi pembelajaran",
    "Simulasi",
    "AI",
    "Media digital lainnya",
]

PRINSIP_PEMBELAJARAN = ["Berkesadaran", "Bermakna", "Menggembirakan"]

PRINSIP_DESKRIPSI = {
    "Berkesadaran": (
        "Peserta didik tahu tujuan belajar, memantau kemajuan, dan merefleksikan "
        "proses berpikirnya."
    ),
    "Bermakna": (
        "Materi dihubungkan dengan pengalaman, lingkungan, dan kebutuhan nyata "
        "peserta didik."
    ),
    "Menggembirakan": (
        "Belajar berlangsung aman, menantang secara wajar, dan melibatkan pilihan "
        "serta interaksi yang menyenangkan."
    ),
}

ASESMEN_JENIS = {
    "awal": "Asesmen Awal",
    "proses": "Asesmen Proses (Formatif)",
    "akhir": "Asesmen Akhir (Sumatif)",
}

# Kata kerja operasional yang dapat diamati/diukur
KATA_KERJA_OPERASIONAL = [
    "menjelaskan", "mengidentifikasi", "menganalisis", "menerapkan", "menyusun",
    "membandingkan", "mengklasifikasikan", "mengukur", "menghitung", "mendemonstrasikan",
    "merancang", "membuat", "menyajikan", "mengomunikasikan", "mengevaluasi",
    "menyimpulkan", "memecahkan", "melakukan", "menggunakan", "menentukan",
    "membedakan", "mengaitkan", "mempresentasikan", "menulis", "menggambar",
    "menyusun", "mengembangkan", "menguji", "mengamati", "mendeskripsikan",
    "mengorganisasi", "merefleksikan", "menilai", "memilih", "merencanakan",
    "mempraktikkan", "mengimplementasikan", "mendiagnosis", "mengoreksi",
]

KATA_TIDAK_TERUKUR = ["memahami", "mengetahui", "mengerti", "menghayati", "menikmati", "merasakan"]

# ---------------------------------------------------------------------------
# Pengaturan bawaan AI lokal (Ollama)
# ---------------------------------------------------------------------------
DEFAULT_SETTINGS = {
    "ollama_url": "http://localhost:11434",
    "ollama_model": "qwen2.5:7b",
    "temperature": "0.4",
    "num_predict": "2000",
    "timeout": "180",
    "tahun_pelajaran": "2025/2026",
    "semester": "Ganjil",
    "auto_save_versi": "1",
}

# Status dokumen
STATUS_DOKUMEN = ["draf", "ditinjau", "disetujui", "final"]

# Label kategori validasi
VALIDASI_SESUAI = "Sudah sesuai"
VALIDASI_PERBAIKAN = "Perlu perbaikan"
VALIDASI_BELUM = "Belum tersedia"
