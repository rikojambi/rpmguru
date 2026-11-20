"""Lapisan akses database SQLite untuk Generator RPM."""

from __future__ import annotations

import json
import shutil
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

import config


# ---------------------------------------------------------------------------
# Koneksi dan inisialisasi
# ---------------------------------------------------------------------------
def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(str(config.DB_PATH), timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def get_db():
    conn = _connect()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    """Membuat tabel, indeks, dan data awal bila belum ada."""
    schema_path = Path(__file__).resolve().parent / "schema.sql"
    with get_db() as conn:
        conn.executescript(schema_path.read_text(encoding="utf-8"))
        for key, value in config.DEFAULT_SETTINGS.items():
            conn.execute(
                "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
                (key, value),
            )
        jumlah_model = conn.execute("SELECT COUNT(*) AS n FROM bank_model").fetchone()["n"]
        if jumlah_model == 0:
            now = timestamp()
            rows = []
            for nama in config.MODEL_PEMBELAJARAN:
                rows.append(
                    (
                        nama,
                        config.MODEL_DESKRIPSI.get(nama, ""),
                        " | ".join(config.SINTAKS_MODEL.get(nama, [])),
                        now,
                    )
                )
            conn.executemany(
                "INSERT OR IGNORE INTO bank_model (nama, deskripsi, sintaks, created_at) "
                "VALUES (?, ?, ?, ?)",
                rows,
            )


# ---------------------------------------------------------------------------
# Utilitas umum
# ---------------------------------------------------------------------------
def timestamp() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def query(sql: str, params: Iterable[Any] = ()) -> list[dict]:
    with get_db() as conn:
        rows = conn.execute(sql, tuple(params)).fetchall()
    return [dict(row) for row in rows]


def query_one(sql: str, params: Iterable[Any] = ()) -> dict | None:
    with get_db() as conn:
        row = conn.execute(sql, tuple(params)).fetchone()
    return dict(row) if row else None


def scalar(sql: str, params: Iterable[Any] = (), default: Any = 0) -> Any:
    with get_db() as conn:
        row = conn.execute(sql, tuple(params)).fetchone()
    if row is None or row[0] is None:
        return default
    return row[0]


def execute(sql: str, params: Iterable[Any] = ()) -> int:
    with get_db() as conn:
        cur = conn.execute(sql, tuple(params))
        return int(cur.lastrowid or 0)


def executemany(sql: str, rows: Iterable[Iterable[Any]]) -> None:
    with get_db() as conn:
        conn.executemany(sql, [tuple(r) for r in rows])


def log_activity(aksi: str, detail: str = "") -> None:
    detail = (detail or "")[:500]
    execute(
        "INSERT INTO activities (aksi, detail, created_at) VALUES (?, ?, ?)",
        (aksi, detail, timestamp()),
    )


# ---------------------------------------------------------------------------
# Pengaturan
# ---------------------------------------------------------------------------
def get_settings() -> dict:
    data = dict(config.DEFAULT_SETTINGS)
    for row in query("SELECT key, value FROM settings"):
        data[row["key"]] = row["value"]
    return data


def set_setting(key: str, value: Any) -> None:
    execute(
        "INSERT INTO settings (key, value) VALUES (?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (key, str(value)),
    )


def set_settings(values: dict) -> None:
    for key, value in values.items():
        set_setting(key, value)


def get_setting(key: str, default: str = "") -> str:
    row = query_one("SELECT value FROM settings WHERE key = ?", (key,))
    return row["value"] if row else default


# ---------------------------------------------------------------------------
# Profil sekolah dan guru
# ---------------------------------------------------------------------------
PROFILE_FIELDS = [
    "label", "nama_sekolah", "npsn", "alamat", "kabupaten", "provinsi",
    "nama_kepala_sekolah", "nama_guru", "nip", "tahun_pelajaran", "semester",
    "jenjang", "status_sekolah", "kurikulum",
]


def list_profiles() -> list[dict]:
    return query("SELECT * FROM profiles ORDER BY is_active DESC, updated_at DESC, id DESC")


def get_profile(profile_id: int | None) -> dict | None:
    if not profile_id:
        return None
    return query_one("SELECT * FROM profiles WHERE id = ?", (profile_id,))


def get_active_profile() -> dict | None:
    row = query_one("SELECT * FROM profiles WHERE is_active = 1 ORDER BY updated_at DESC LIMIT 1")
    if row:
        return row
    row = query_one("SELECT * FROM profiles ORDER BY updated_at DESC LIMIT 1")
    return row


def save_profile(data: dict, profile_id: int | None = None) -> int:
    now = timestamp()
    values = [str(data.get(field, "") or "") for field in PROFILE_FIELDS]
    with get_db() as conn:
        if profile_id:
            assignments = ", ".join(f"{field} = ?" for field in PROFILE_FIELDS)
            conn.execute(
                f"UPDATE profiles SET {assignments}, updated_at = ? WHERE id = ?",
                (*values, now, int(profile_id)),
            )
            return int(profile_id)
        columns = ", ".join(PROFILE_FIELDS)
        placeholders = ", ".join("?" for _ in PROFILE_FIELDS)
        cur = conn.execute(
            f"INSERT INTO profiles ({columns}, created_at, updated_at) VALUES ({placeholders}, ?, ?)",
            (*values, now, now),
        )
        return int(cur.lastrowid)


def delete_profile(profile_id: int) -> None:
    execute("DELETE FROM profiles WHERE id = ?", (profile_id,))


def set_active_profile(profile_id: int) -> None:
    with get_db() as conn:
        conn.execute("UPDATE profiles SET is_active = 0")
        conn.execute(
            "UPDATE profiles SET is_active = 1, updated_at = ? WHERE id = ?",
            (timestamp(), int(profile_id)),
        )


# ---------------------------------------------------------------------------
# Data pembelajaran
# ---------------------------------------------------------------------------
PEMBELAJARAN_FIELDS = [
    "profile_id", "judul", "jenjang", "fase", "kelas", "semester", "mata_pelajaran",
    "konsentrasi", "elemen", "cp", "atp", "materi_pokok", "tp", "alokasi_waktu",
    "jumlah_peserta", "karakteristik", "pengetahuan_awal", "kebutuhan_belajar",
    "konteks_lingkungan", "sarana", "sumber_belajar",
]


def list_pembelajaran(include_archived: bool = False) -> list[dict]:
    sql = (
        "SELECT p.*, pr.nama_sekolah, pr.nama_guru "
        "FROM pembelajaran p LEFT JOIN profiles pr ON pr.id = p.profile_id"
    )
    return query(sql + " ORDER BY p.updated_at DESC, p.id DESC")


def get_pembelajaran(pembelajaran_id: int | None) -> dict | None:
    if not pembelajaran_id:
        return None
    return query_one("SELECT * FROM pembelajaran WHERE id = ?", (int(pembelajaran_id),))


def save_pembelajaran(data: dict, pembelajaran_id: int | None = None) -> int:
    now = timestamp()
    values: list[Any] = []
    for field in PEMBELAJARAN_FIELDS:
        value = data.get(field, "")
        if field == "profile_id":
            value = int(value) if str(value or "").strip().isdigit() else None
        elif field == "jumlah_peserta":
            try:
                value = int(value or 0)
            except (TypeError, ValueError):
                value = 0
        else:
            value = str(value or "")
        values.append(value)

    with get_db() as conn:
        if pembelajaran_id:
            assignments = ", ".join(f"{field} = ?" for field in PEMBELAJARAN_FIELDS)
            conn.execute(
                f"UPDATE pembelajaran SET {assignments}, updated_at = ? WHERE id = ?",
                (*values, now, int(pembelajaran_id)),
            )
            return int(pembelajaran_id)
        columns = ", ".join(PEMBELAJARAN_FIELDS)
        placeholders = ", ".join("?" for _ in PEMBELAJARAN_FIELDS)
        cur = conn.execute(
            f"INSERT INTO pembelajaran ({columns}, created_at, updated_at) "
            f"VALUES ({placeholders}, ?, ?)",
            (*values, now, now),
        )
        return int(cur.lastrowid)


def delete_pembelajaran(pembelajaran_id: int) -> None:
    execute("DELETE FROM pembelajaran WHERE id = ?", (int(pembelajaran_id),))


def duplicate_pembelajaran(pembelajaran_id: int) -> int:
    row = get_pembelajaran(pembelajaran_id)
    if not row:
        return 0
    row = dict(row)
    for key in ("id", "created_at", "updated_at"):
        row.pop(key, None)
    row["judul"] = f"{row.get('judul') or 'Pembelajaran'} (salinan)"
    return save_pembelajaran(row)


def count_pembelajaran() -> int:
    return int(scalar("SELECT COUNT(*) FROM pembelajaran"))


def count_mata_pelajaran() -> int:
    return int(scalar("SELECT COUNT(DISTINCT mata_pelajaran) FROM pembelajaran WHERE TRIM(mata_pelajaran) <> ''"))


# ---------------------------------------------------------------------------
# Bank CP dan ATP
# ---------------------------------------------------------------------------
BANK_CP_FIELDS = [
    "jenjang", "fase", "mata_pelajaran", "elemen", "cp", "atp", "sumber", "is_official",
]


def list_bank_cp(search: str = "") -> list[dict]:
    if search.strip():
        like = f"%{search.strip()}%"
        return query(
            "SELECT * FROM bank_cp WHERE mata_pelajaran LIKE ? OR elemen LIKE ? "
            "OR cp LIKE ? OR atp LIKE ? ORDER BY updated_at DESC, id DESC",
            (like, like, like, like),
        )
    return query("SELECT * FROM bank_cp ORDER BY updated_at DESC, id DESC")


def save_bank_cp(data: dict, row_id: int | None = None) -> int:
    now = timestamp()
    values = []
    for field in BANK_CP_FIELDS:
        if field == "is_official":
            values.append(1 if data.get(field) else 0)
        else:
            values.append(str(data.get(field, "") or ""))
    with get_db() as conn:
        if row_id:
            assignments = ", ".join(f"{field} = ?" for field in BANK_CP_FIELDS)
            conn.execute(
                f"UPDATE bank_cp SET {assignments}, updated_at = ? WHERE id = ?",
                (*values, now, int(row_id)),
            )
            return int(row_id)
        columns = ", ".join(BANK_CP_FIELDS)
        placeholders = ", ".join("?" for _ in BANK_CP_FIELDS)
        cur = conn.execute(
            f"INSERT INTO bank_cp ({columns}, created_at, updated_at) VALUES ({placeholders}, ?, ?)",
            (*values, now, now),
        )
        return int(cur.lastrowid)


def delete_bank_cp(row_id: int) -> None:
    execute("DELETE FROM bank_cp WHERE id = ?", (int(row_id),))


def get_bank_cp(row_id: int) -> dict | None:
    return query_one("SELECT * FROM bank_cp WHERE id = ?", (int(row_id),))


# ---------------------------------------------------------------------------
# Dokumen RPM
# ---------------------------------------------------------------------------
RPM_FIELDS = [
    "pembelajaran_id", "profile_id", "judul", "status", "data_json", "catatan", "archived",
]


def list_rpm(search: str = "", include_archived: bool = False) -> list[dict]:
    sql = (
        "SELECT r.*, p.mata_pelajaran, p.kelas, p.fase, p.jenjang, "
        "pr.nama_sekolah, pr.nama_guru, "
        "(SELECT COUNT(*) FROM rpm_versions v WHERE v.rpm_id = r.id) AS jumlah_versi "
        "FROM rpm_documents r "
        "LEFT JOIN pembelajaran p ON p.id = r.pembelajaran_id "
        "LEFT JOIN profiles pr ON pr.id = r.profile_id WHERE 1=1"
    )
    params: list[Any] = []
    if not include_archived:
        sql += " AND r.archived = 0"
    if search.strip():
        like = f"%{search.strip()}%"
        sql += " AND (r.judul LIKE ? OR p.mata_pelajaran LIKE ? OR pr.nama_sekolah LIKE ?)"
        params.extend([like, like, like])
    sql += " ORDER BY r.updated_at DESC, r.id DESC"
    return query(sql, params)


def get_rpm(rpm_id: int | None) -> dict | None:
    if not rpm_id:
        return None
    row = query_one(
        "SELECT r.*, p.mata_pelajaran, p.kelas, p.fase, p.jenjang, p.elemen, p.cp, p.atp, "
        "p.materi_pokok, p.tp, p.alokasi_waktu, p.jumlah_peserta, p.karakteristik, "
        "p.pengetahuan_awal, p.kebutuhan_belajar, p.konteks_lingkungan, p.sarana, "
        "p.sumber_belajar, p.konsentrasi, p.semester AS semester_pembelajaran, "
        "pr.nama_sekolah, pr.nama_guru, pr.nama_kepala_sekolah, pr.nip, pr.npsn, "
        "pr.alamat, pr.kabupaten, pr.provinsi, pr.tahun_pelajaran, pr.jenjang AS jenjang_profil "
        "FROM rpm_documents r "
        "LEFT JOIN pembelajaran p ON p.id = r.pembelajaran_id "
        "LEFT JOIN profiles pr ON pr.id = r.profile_id WHERE r.id = ?",
        (int(rpm_id),),
    )
    return row


def create_rpm(pembelajaran_id: int, profile_id: int | None, judul: str, data: dict | None = None) -> int:
    now = timestamp()
    data_json = json.dumps(data or {}, ensure_ascii=False)
    rpm_id = execute(
        "INSERT INTO rpm_documents "
        "(pembelajaran_id, profile_id, judul, status, data_json, catatan, archived, created_at, updated_at) "
        "VALUES (?, ?, ?, 'draf', ?, '', 0, ?, ?)",
        (int(pembelajaran_id), profile_id, judul, data_json, now, now),
    )
    if rpm_id:
        save_version(rpm_id, data or {}, "Versi awal")
        log_activity("Buat RPM", judul)
    return rpm_id


def save_rpm(rpm_id: int, data: dict, catatan: str | None = None, judul: str | None = None,
             status: str | None = None) -> None:
    now = timestamp()
    current = get_rpm(rpm_id)
    if not current:
        return
    execute(
        "UPDATE rpm_documents SET data_json = ?, catatan = ?, judul = ?, status = ?, updated_at = ? "
        "WHERE id = ?",
        (
            json.dumps(data, ensure_ascii=False),
            catatan if catatan is not None else current.get("catatan", ""),
            judul if judul is not None else current.get("judul", ""),
            status if status is not None else current.get("status", "draf"),
            now,
            int(rpm_id),
        ),
    )


def update_rpm_status(rpm_id: int, status: str) -> None:
    execute(
        "UPDATE rpm_documents SET status = ?, updated_at = ? WHERE id = ?",
        (status, timestamp(), int(rpm_id)),
    )


def archive_rpm(rpm_id: int, archived: bool = True) -> None:
    execute(
        "UPDATE rpm_documents SET archived = ?, updated_at = ? WHERE id = ?",
        (1 if archived else 0, timestamp(), int(rpm_id)),
    )


def delete_rpm(rpm_id: int) -> None:
    execute("DELETE FROM rpm_documents WHERE id = ?", (int(rpm_id),))


def duplicate_rpm(rpm_id: int) -> int:
    row = get_rpm(rpm_id)
    if not row:
        return 0
    new_id = create_rpm(
        row.get("pembelajaran_id"),
        row.get("profile_id"),
        f"{row.get('judul') or 'RPM'} (salinan)",
        json.loads(row.get("data_json") or "{}"),
    )
    return new_id


def count_rpm(include_archived: bool = True) -> int:
    if include_archived:
        return int(scalar("SELECT COUNT(*) FROM rpm_documents"))
    return int(scalar("SELECT COUNT(*) FROM rpm_documents WHERE archived = 0"))


def count_documents() -> int:
    rpm = int(scalar("SELECT COUNT(*) FROM rpm_documents"))
    lkpd = int(scalar("SELECT COUNT(*) FROM lkpd_documents"))
    return rpm + lkpd


# ---------------------------------------------------------------------------
# Versi dokumen
# ---------------------------------------------------------------------------
def save_version(rpm_id: int, data: dict, catatan: str = "") -> int:
    nomor = int(scalar("SELECT COALESCE(MAX(version_no), 0) FROM rpm_versions WHERE rpm_id = ?", (int(rpm_id),))) + 1
    return execute(
        "INSERT INTO rpm_versions (rpm_id, version_no, data_json, catatan, created_at) "
        "VALUES (?, ?, ?, ?, ?)",
        (int(rpm_id), nomor, json.dumps(data, ensure_ascii=False), catatan[:300], timestamp()),
    )


def list_versions(rpm_id: int) -> list[dict]:
    return query(
        "SELECT * FROM rpm_versions WHERE rpm_id = ? ORDER BY version_no DESC",
        (int(rpm_id),),
    )


def get_version(version_id: int) -> dict | None:
    return query_one("SELECT * FROM rpm_versions WHERE id = ?", (int(version_id),))


# ---------------------------------------------------------------------------
# LKPD
# ---------------------------------------------------------------------------
def list_lkpd(rpm_id: int | None = None) -> list[dict]:
    if rpm_id:
        return query(
            "SELECT l.*, r.judul AS judul_rpm FROM lkpd_documents l "
            "LEFT JOIN rpm_documents r ON r.id = l.rpm_id WHERE l.rpm_id = ? "
            "ORDER BY l.updated_at DESC",
            (int(rpm_id),),
        )
    return query(
        "SELECT l.*, r.judul AS judul_rpm FROM lkpd_documents l "
        "LEFT JOIN rpm_documents r ON r.id = l.rpm_id ORDER BY l.updated_at DESC"
    )


def save_lkpd(rpm_id: int, data: dict, judul: str) -> int:
    now = timestamp()
    existing = query_one("SELECT id FROM lkpd_documents WHERE rpm_id = ?", (int(rpm_id),))
    if existing:
        execute(
            "UPDATE lkpd_documents SET judul = ?, data_json = ?, updated_at = ? WHERE id = ?",
            (judul, json.dumps(data, ensure_ascii=False), now, existing["id"]),
        )
        return int(existing["id"])
    return execute(
        "INSERT INTO lkpd_documents (rpm_id, judul, data_json, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?)",
        (int(rpm_id), judul, json.dumps(data, ensure_ascii=False), now, now),
    )


def get_lkpd(lkpd_id: int) -> dict | None:
    return query_one("SELECT * FROM lkpd_documents WHERE id = ?", (int(lkpd_id),))


def delete_lkpd(lkpd_id: int) -> None:
    execute("DELETE FROM lkpd_documents WHERE id = ?", (int(lkpd_id),))


# ---------------------------------------------------------------------------
# Riwayat AI
# ---------------------------------------------------------------------------
def log_ai(rpm_id: int | None, tahap: str, model: str, prompt: str, response: str,
           status: str = "sukses") -> None:
    execute(
        "INSERT INTO ai_history (rpm_id, tahap, model, prompt, response, status, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (rpm_id, tahap, model, prompt[:8000], response[:20000], status, timestamp()),
    )


def list_ai_history(limit: int = 50) -> list[dict]:
    return query(
        "SELECT * FROM ai_history ORDER BY id DESC LIMIT ?", (int(limit),)
    )


# ---------------------------------------------------------------------------
# Bank asesmen dan materi
# ---------------------------------------------------------------------------
def add_bank_asesmen(data: dict) -> int:
    return execute(
        "INSERT INTO bank_asesmen (mata_pelajaran, jenis, tujuan, instrumen, soal, kunci, rubrik, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (
            data.get("mata_pelajaran", ""), data.get("jenis", "proses"),
            data.get("tujuan", ""), data.get("instrumen", ""),
            data.get("soal", ""), data.get("kunci", ""),
            data.get("rubrik", ""), timestamp(),
        ),
    )


def list_bank_asesmen() -> list[dict]:
    return query("SELECT * FROM bank_asesmen ORDER BY id DESC")


def add_bank_materi(mata_pelajaran: str, jenjang: str, materi: str, catatan: str = "") -> int:
    return execute(
        "INSERT INTO bank_materi (mata_pelajaran, jenjang, materi, catatan, created_at) "
        "VALUES (?, ?, ?, ?, ?)",
        (mata_pelajaran, jenjang, materi, catatan, timestamp()),
    )


def list_bank_materi() -> list[dict]:
    return query("SELECT * FROM bank_materi ORDER BY id DESC")


# ---------------------------------------------------------------------------
# Aktivitas dan dashboard
# ---------------------------------------------------------------------------
def list_activities(limit: int = 8) -> list[dict]:
    return query("SELECT * FROM activities ORDER BY id DESC LIMIT ?", (int(limit),))


# ---------------------------------------------------------------------------
# Backup dan restore
# ---------------------------------------------------------------------------
def backup_database(note: str = "") -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    target = config.BACKUP_DIR / f"generator_rpm_{stamp}.db"
    source = _connect()
    try:
        target_conn = sqlite3.connect(str(target))
        try:
            source.backup(target_conn)
        finally:
            target_conn.close()
    finally:
        source.close()
    size = target.stat().st_size
    execute(
        "INSERT INTO backups (filename, size, note, created_at) VALUES (?, ?, ?, ?)",
        (target.name, size, note, timestamp()),
    )
    log_activity("Backup database", target.name)
    return target


def list_backup_files() -> list[dict]:
    files = []
    for path in sorted(config.BACKUP_DIR.glob("*.db"), key=lambda p: p.stat().st_mtime, reverse=True):
        files.append(
            {
                "filename": path.name,
                "path": str(path),
                "size": path.stat().st_size,
                "modified": datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
            }
        )
    return files


def validate_sqlite_file(path: Path) -> tuple[bool, str]:
    try:
        conn = sqlite3.connect(str(path))
        try:
            result = conn.execute("PRAGMA integrity_check").fetchone()
            if not result or result[0] != "ok":
                return False, "Berkas bukan database SQLite yang sehat."
            tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            wajib = {"profiles", "pembelajaran", "rpm_documents", "settings"}
            if not wajib.issubset(tables):
                return False, "Struktur database tidak dikenali sebagai database Generator RPM."
        finally:
            conn.close()
    except Exception as exc:  # pragma: no cover - bergantung berkas pengguna
        return False, f"Gagal membaca berkas database: {exc}"
    return True, "Berkas database valid."


def restore_database(source_path: Path) -> tuple[bool, str]:
    ok, message = validate_sqlite_file(source_path)
    if not ok:
        return False, message
    # Simpan cadangan otomatis sebelum menimpa
    backup_database("Cadangan otomatis sebelum restore")
    try:
        # Tutup koneksi WAL yang mungkin tersisa
        with get_db() as conn:
            conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        shutil.copy2(source_path, config.DB_PATH)
        for suffix in ("-wal", "-shm"):
            leftover = Path(str(config.DB_PATH) + suffix)
            if leftover.exists():
                leftover.unlink()
        init_db()
        log_activity("Restore database", Path(source_path).name)
        return True, "Database berhasil dipulihkan. Muat ulang halaman bila perlu."
    except Exception as exc:  # pragma: no cover - bergantung sistem berkas
        return False, f"Restore gagal: {exc}"
