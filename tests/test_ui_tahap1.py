"""Uji antarmuka Tahap 1 dengan Streamlit AppTest."""

from __future__ import annotations

import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

from streamlit.testing.v1 import AppTest  # noqa: E402


def main() -> None:
    at = AppTest.from_file(str(BASE / "app.py"), default_timeout=60)
    at.run()
    assert not at.exception, at.exception
    print("OK  Dashboard dimuat")
    judul = [h.value for h in at.markdown if "page-head" in h.value and len(h.value) < 2000]
    print("    Judul:", judul[:1])

    at.radio(key="nav_page").set_value("Profil Sekolah").run()
    assert not at.exception, at.exception
    assert any("Profil Sekolah" in h.value for h in at.markdown)
    print("OK  Halaman Profil Sekolah dimuat")

    at.radio(key="nav_page").set_value("Pengaturan AI").run()
    assert not at.exception, at.exception
    assert any("Pengaturan AI" in h.value for h in at.markdown)
    print("OK  Halaman Pengaturan AI dimuat")

    at.radio(key="nav_page").set_value("Dashboard").run()
    assert not at.exception, at.exception
    print("OK  Navigasi kembali ke Dashboard")
    print("\nSEMUA UJI ANTARMUKA TAHAP 1 LULUS")


if __name__ == "__main__":
    main()
