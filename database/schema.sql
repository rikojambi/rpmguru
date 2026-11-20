-- Skema database Generator RPM
-- Semua tabel dibuat dengan IF NOT EXISTS agar aman dijalankan berulang.

PRAGMA journal_mode = WAL;

CREATE TABLE IF NOT EXISTS profiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    label TEXT,
    nama_sekolah TEXT NOT NULL DEFAULT '',
    npsn TEXT DEFAULT '',
    alamat TEXT DEFAULT '',
    kabupaten TEXT DEFAULT '',
    provinsi TEXT DEFAULT '',
    nama_kepala_sekolah TEXT DEFAULT '',
    nama_guru TEXT DEFAULT '',
    nip TEXT DEFAULT '',
    tahun_pelajaran TEXT DEFAULT '',
    semester TEXT DEFAULT 'Ganjil',
    jenjang TEXT DEFAULT '',
    status_sekolah TEXT DEFAULT 'Negeri',
    kurikulum TEXT DEFAULT 'Kurikulum Merdeka',
    is_active INTEGER DEFAULT 0,
    created_at TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS pembelajaran (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_id INTEGER,
    judul TEXT DEFAULT '',
    jenjang TEXT DEFAULT '',
    fase TEXT DEFAULT '',
    kelas TEXT DEFAULT '',
    semester TEXT DEFAULT 'Ganjil',
    mata_pelajaran TEXT DEFAULT '',
    konsentrasi TEXT DEFAULT '',
    elemen TEXT DEFAULT '',
    cp TEXT DEFAULT '',
    atp TEXT DEFAULT '',
    materi_pokok TEXT DEFAULT '',
    tp TEXT DEFAULT '',
    alokasi_waktu TEXT DEFAULT '',
    jumlah_peserta INTEGER DEFAULT 0,
    karakteristik TEXT DEFAULT '',
    pengetahuan_awal TEXT DEFAULT '',
    kebutuhan_belajar TEXT DEFAULT '',
    konteks_lingkungan TEXT DEFAULT '',
    sarana TEXT DEFAULT '',
    sumber_belajar TEXT DEFAULT '',
    created_at TEXT,
    updated_at TEXT,
    FOREIGN KEY (profile_id) REFERENCES profiles(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS bank_cp (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    jenjang TEXT DEFAULT '',
    fase TEXT DEFAULT '',
    mata_pelajaran TEXT DEFAULT '',
    elemen TEXT DEFAULT '',
    cp TEXT DEFAULT '',
    atp TEXT DEFAULT '',
    sumber TEXT DEFAULT 'Input guru',
    is_official INTEGER DEFAULT 0,
    created_at TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS bank_materi (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    mata_pelajaran TEXT DEFAULT '',
    jenjang TEXT DEFAULT '',
    materi TEXT DEFAULT '',
    catatan TEXT DEFAULT '',
    created_at TEXT
);

CREATE TABLE IF NOT EXISTS bank_asesmen (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    mata_pelajaran TEXT DEFAULT '',
    jenis TEXT DEFAULT 'proses',
    tujuan TEXT DEFAULT '',
    instrumen TEXT DEFAULT '',
    soal TEXT DEFAULT '',
    kunci TEXT DEFAULT '',
    rubrik TEXT DEFAULT '',
    created_at TEXT
);

CREATE TABLE IF NOT EXISTS bank_model (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nama TEXT UNIQUE,
    deskripsi TEXT DEFAULT '',
    sintaks TEXT DEFAULT '',
    created_at TEXT
);

CREATE TABLE IF NOT EXISTS rpm_documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pembelajaran_id INTEGER,
    profile_id INTEGER,
    judul TEXT DEFAULT '',
    status TEXT DEFAULT 'draf',
    data_json TEXT DEFAULT '{}',
    catatan TEXT DEFAULT '',
    archived INTEGER DEFAULT 0,
    created_at TEXT,
    updated_at TEXT,
    FOREIGN KEY (pembelajaran_id) REFERENCES pembelajaran(id) ON DELETE SET NULL,
    FOREIGN KEY (profile_id) REFERENCES profiles(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS rpm_versions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    rpm_id INTEGER NOT NULL,
    version_no INTEGER NOT NULL,
    data_json TEXT DEFAULT '{}',
    catatan TEXT DEFAULT '',
    created_at TEXT,
    FOREIGN KEY (rpm_id) REFERENCES rpm_documents(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS lkpd_documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    rpm_id INTEGER,
    judul TEXT DEFAULT '',
    data_json TEXT DEFAULT '{}',
    created_at TEXT,
    updated_at TEXT,
    FOREIGN KEY (rpm_id) REFERENCES rpm_documents(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS ai_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    rpm_id INTEGER,
    tahap TEXT DEFAULT '',
    model TEXT DEFAULT '',
    prompt TEXT DEFAULT '',
    response TEXT DEFAULT '',
    status TEXT DEFAULT 'sukses',
    created_at TEXT
);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT
);

CREATE TABLE IF NOT EXISTS activities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    aksi TEXT DEFAULT '',
    detail TEXT DEFAULT '',
    created_at TEXT
);

CREATE TABLE IF NOT EXISTS backups (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename TEXT DEFAULT '',
    size INTEGER DEFAULT 0,
    note TEXT DEFAULT '',
    created_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_pembelajaran_mapel ON pembelajaran(mata_pelajaran);
CREATE INDEX IF NOT EXISTS idx_bank_cp_mapel ON bank_cp(mata_pelajaran);
CREATE INDEX IF NOT EXISTS idx_rpm_pembelajaran ON rpm_documents(pembelajaran_id);
CREATE INDEX IF NOT EXISTS idx_rpm_archived ON rpm_documents(archived);
CREATE INDEX IF NOT EXISTS idx_versions_rpm ON rpm_versions(rpm_id);
CREATE INDEX IF NOT EXISTS idx_lkpd_rpm ON lkpd_documents(rpm_id);
CREATE INDEX IF NOT EXISTS idx_activities_time ON activities(created_at);
