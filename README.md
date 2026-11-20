# GENERATOR RPM — Asisten Perencanaan Pembelajaran Mendalam

Aplikasi web lokal (Windows 11) untuk membantu guru menyusun **Rencana Pembelajaran Mendalam (RPM)**
secara bertahap, kontekstual, dan dapat diedit. Aplikasi berjalan sepenuhnya di komputer pengguna,
menggunakan SQLite sebagai basis data dan **Ollama lokal** sebagai mesin AI opsional.

> Aplikasi ini adalah alat bantu perencanaan. Dokumen yang dihasilkan **tidak otomatis disahkan** dan
> **tidak menjamin** pemenuhan seluruh ketentuan pemerintah. Guru tetap melakukan reviu dan penyesuaian.
> Aplikasi tidak mengarang CP, ATP, atau dasar hukum resmi.

---

## 1. Fitur Utama

| Modul | Isi |
|---|---|
| Dashboard | Jumlah RPM, mata pelajaran, dokumen, bank CP, aktivitas terakhir, status Ollama |
| Profil Sekolah | Identitas sekolah & guru, mendukung beberapa profil, profil aktif |
| Data Pembelajaran | Jenjang, fase, kelas, mapel, konsentrasi SMK, elemen, CP, ATP, materi, TP, alokasi, konteks, sarana, sumber |
| Bank CP dan ATP | Simpan CP/ATP milik guru, impor Word/Excel/CSV/TXT, pencarian, penanda sumber resmi |
| Generator RPM | Wizard 7 tahap: identifikasi → desain → pengalaman → asesmen → diferensiasi → LKPD → refleksi |
| Generator LKPD | Membuat/menyunting LKPD dari RPM, ekspor DOCX/PDF/TXT |
| Generator Asesmen | Asesmen awal, proses, akhir beserta rubrik; ekspor XLSX |
| Validasi RPM | 12 butir pemeriksaan + kategori dan rekomendasi spesifik; tinjauan AI opsional |
| Arsip Dokumen | Cari, buka, duplikasi, arsipkan, hapus, riwayat versi, ekspor |
| Pengaturan AI | Alamat Ollama, daftar model, temperature, panjang respons, uji AI, riwayat generasi |
| Backup Database | Buat backup, unduh, hapus, restore dengan validasi berkas |

Sesuai kebutuhan RPM, aplikasi memuat:

- **8 dimensi profil lulusan** (keimanan, kewargaan, penalaran kritis, kreativitas, kolaborasi,
  kemandirian, kesehatan, komunikasi) — dipilih yang relevan, tidak dipaksakan.
- **3 pengalaman belajar**: memahami, mengaplikasi, merefleksi — lengkap dengan aktivitas guru/siswa,
  alokasi waktu, media, dimensi, prinsip, dan bukti ketercapaian.
- **3 jenis asesmen**: awal, proses (formatif), akhir — dengan instrumen, soal, kunci/rambu,
  pedoman penskoran, rubrik, dan KKTP.
- **3 tingkat diferensiasi**: perlu bimbingan, berkembang, mahir — satu pembelajaran inti.
- **Struktur dokumen 19 bagian** yang fleksibel (bukan format resmi tunggal).
- **Ekspor** DOCX (A4, margin diatur, kop opsional, tabel, nomor halaman, tanda tangan),
  PDF, XLSX (instrumen & rubrik), TXT.

---

## 2. Kebutuhan Sistem

- Windows 11 (Windows 10 juga dapat digunakan).
- Python **3.12 atau lebih baru**.
- Tanpa internet untuk penggunaan sehari-hari.
- Internet hanya diperlukan **sekali** saat memasang dependensi dan mengunduh model Ollama.
- Ollama **opsional**. Tanpa Ollama, aplikasi tetap berfungsi dengan **draf offline berbasis aturan**.

Dependensi Python (lihat `requirements.txt`):

```
streamlit, pandas, python-docx, reportlab, openpyxl, requests, numpy
```

---

## 3. Instalasi

### Cara cepat (disarankan)

1. Salin seluruh folder `generator_rpm` ke komputer.
2. Klik dua kali **`run.bat`**.
3. Saat pertama dijalankan, `run.bat` membuat virtual environment `.venv`, memasang dependensi,
   lalu membuka **http://localhost:8501** di peramban.

### Cara manual (PowerShell)

```powershell
cd "E:\VIBE CODING\open1\generator_rpm"
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m streamlit run app.py --server.port 8501 --server.address localhost
```

Bila PowerShell menolak aktivasi skrip, jalankan sekali:

```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```

---

## 4. Menyiapkan AI Lokal (Opsional)

1. Pasang Ollama dari situs resmi Ollama.
2. Unduh model bawaan:

   ```powershell
   ollama pull qwen2.5:7b
   ```

3. Pastikan Ollama berjalan (biasanya otomatis setelah instalasi).
4. Buka aplikasi → **Pengaturan AI** → **Periksa Koneksi** → pilih model → **Uji AI**.

Catatan:

- Jika RAM terbatas, gunakan model lebih kecil, misalnya `qwen2.5:3b`.
- Aplikasi hanya mengirim permintaan ke alamat Ollama yang diisi (bawaan `http://localhost:11434`).
- **Jangan** mengisi alamat layanan AI cloud/berbayar. Data guru dan siswa tidak boleh keluar dari komputer.
- Bila Ollama tidak aktif, setiap tahap generator tetap menghasilkan **draf offline** yang bisa diedit.

---

## 5. Alur Penggunaan yang Disarankan

1. **Profil Sekolah** — isi identitas sekolah, guru, kepala sekolah, tahun pelajaran, semester.
2. **Data Pembelajaran** — isi mata pelajaran, CP dan ATP **dari dokumen guru**, materi, TP, konteks,
   sarana, dan sumber belajar. CP/ATP dapat diimpor dari Word/Excel atau diambil dari Bank CP.
3. **Generator RPM** — buat dokumen baru, lalu kerjakan 7 tahap. Setiap tahap dapat:
   - digenerate dengan AI lokal,
   - dibuat sebagai draf offline,
   - diedit manual,
   - disimpan sebagai versi,
   - dibandingkan dengan versi sebelumnya.
4. **Validasi RPM** — jalankan pemeriksaan 12 butir; perbaiki sesuai rekomendasi.
5. **Ekspor** — unduh DOCX, PDF, XLSX, atau TXT dari halaman Generator RPM atau Arsip Dokumen.
6. **Backup Database** — buat backup berkala dan simpan salinannya di lokasi lain.

---

## 6. Struktur Proyek

```
generator_rpm/
├── app.py                     # aplikasi utama, sidebar, dispatch halaman
├── config.py                  # path, konstanta kurikulum, dimensi, sintaks model
├── requirements.txt
├── README.md
├── run.bat                    # launcher Windows (venv + dependensi + streamlit)
├── .streamlit/
│   └── config.toml            # tema dan konfigurasi server lokal
├── assets/
│   └── style.css              # gaya antarmuka
├── database/
│   ├── db.py                  # seluruh operasi SQLite
│   └── schema.sql             # skema tabel dan indeks
├── modules/
│   ├── dashboard.py
│   ├── profil.py
│   ├── pembelajaran.py        # data pembelajaran + impor CP/ATP
│   ├── bank_cp.py
│   ├── identifikasi.py
│   ├── desain.py
│   ├── pengalaman_belajar.py
│   ├── asesmen.py
│   ├── diferensiasi.py
│   ├── lkpd.py
│   ├── refleksi.py
│   ├── generator.py           # wizard RPM, versi, finalisasi, ekspor
│   ├── validasi.py            # 12 aturan pemeriksaan + halaman validasi
│   ├── arsip.py
│   ├── pengaturan_ai.py
│   ├── backup.py
│   ├── editor.py              # skema bagian RPM + editor generik
│   └── komponen.py            # komponen UI, impor berkas, unduhan
├── ai/
│   ├── ollama_client.py       # klien HTTP Ollama
│   ├── prompts.py             # prompt JSON + aturan anti-fabrikasi
│   └── generator.py           # orkestrasi AI + draf offline
├── exports/
│   ├── konten.py              # model blok dokumen bersama
│   ├── docx_export.py
│   ├── pdf_export.py
│   ├── excel_export.py
│   └── txt_export.py
├── templates/                 # disiapkan untuk template tambahan
├── data/
│   ├── generator_rpm.db       # basis data utama
│   ├── backups/               # berkas backup .db
│   ├── exports/               # ruang ekspor
│   └── uploads/               # berkas impor/restore
└── tests/
    ├── test_tahap1.py         # uji inti database & generator offline
    ├── test_ui_tahap1.py      # uji UI tahap 1
    ├── test_integration.py    # uji integrasi seluruh bagian + ekspor
    ├── test_ui_all.py         # uji pemuatan 11 halaman
    └── test_flows.py          # uji alur interaktif lengkap
```

---

## 7. Pengujian

Jalankan dari folder proyek:

```powershell
python tests\test_tahap1.py
python tests\test_ui_tahap1.py
python tests\test_integration.py
python tests\test_ui_all.py
python tests\test_flows.py
```

Hasil yang diharapkan:

- `test_tahap1.py` — database, profil, pengaturan, bank CP, 7 generator offline, parser JSON,
  RPM/versi, dan backup lulus.
- `test_ui_tahap1.py` — Dashboard, Profil, Pengaturan AI termuat tanpa kesalahan.
- `test_integration.py` — seluruh bagian offline, 12/12 validasi, DOCX (23 tabel), PDF, XLSX (7 sheet),
  TXT, ekspor LKPD, RPM/versi/duplikasi/arsip/LKPD, backup.
- `test_ui_all.py` — 11 halaman termuat tanpa exception.
- `test_flows.py` — alur nyata: simpan profil, simpan data pembelajaran, simpan bank CP, buat RPM,
  generate offline 7 tahap, simpan versi, validasi, arsip, ekspor, backup.

Tes memakai database terpisah (`data/test_*.db`) dan membersihkannya setelah selesai.

---

## 8. Catatan Validasi

- Validasi bersifat **berbasis aturan** (12 butir) dan memeriksa struktur serta konsistensi teks.
- Kategori hasil: **Sudah sesuai**, **Perlu perbaikan**, **Belum tersedia**.
- Tinjauan AI bersifat opsional dan hanya pendapat tambahan.
- Skor 100% **bukan** pengesahan resmi dan bukan jaminan pemenuhan seluruh ketentuan pemerintah.

---

## 9. Backup dan Keamanan Data

- Seluruh data tersimpan di `data/generator_rpm.db` (SQLite).
- Backup disimpan di `data/backups/` dengan cap waktu.
- Restore memvalidasi berkas dan otomatis membuat backup sebelum menimpa.
- Tidak ada server pusat dan tidak ada pengiriman data ke layanan eksternal.
- Salin folder `data/` secara berkala ke penyimpanan lain.

---

## 10. Pemecahan Masalah

| Gejala | Penanganan |
|---|---|
| `run.bat` gagal membuat venv | Pastikan Python terpasang dan opsi "Add Python to PATH" dicentang |
| Halaman kosong / error modul | Pastikan seluruh berkas proyek tersalin; jalankan `python -m compileall -q .` |
| Ollama tidak aktif | Jalankan Ollama, cek alamat di Pengaturan AI; aplikasi tetap bisa memakai draf offline |
| Model tidak ditemukan | `ollama pull qwen2.5:7b`, lalu pilih model di Pengaturan AI |
| Respons AI terpotong | Naikkan "Panjang respons maksimum" di Pengaturan AI |
| Port 8501 dipakai | `python -m streamlit run app.py --server.port 8502` |
| Ingin mengulang dari data bersih | Backup dulu, lalu hapus isi tabel melalui menu Backup/Restore |

---

## 11. Lisensi dan Tanggung Jawab

Aplikasi ini disediakan sebagai alat bantu pendidikan. Pengguna bertanggung jawab memverifikasi
CP, ATP, regulasi, dan seluruh isi dokumen dengan sumber resmi sebelum digunakan.
