@echo off
setlocal
cd /d "%~dp0"
title Generator RPM - Pembelajaran Mendalam
color 0A

echo ============================================================
echo   GENERATOR RPM - ASISTEN PERENCANAAN PEMBELAJARAN MENDALAM
echo ============================================================
echo.

REM --- Cari Python ---
set "PYTHON_CMD="
where py >nul 2>nul && set "PYTHON_CMD=py -3"
if not defined PYTHON_CMD (
    where python >nul 2>nul && set "PYTHON_CMD=python"
)
if not defined PYTHON_CMD (
    echo [GAGAL] Python tidak ditemukan.
    echo Silakan pasang Python 3.12 atau lebih baru dari https://www.python.org/downloads/
    echo Pastikan opsi "Add Python to PATH" dicentang saat instalasi.
    pause
    exit /b 1
)

echo [OK] Python ditemukan: %PYTHON_CMD%

REM --- Siapkan virtual environment ---
if not exist ".venv\Scripts\python.exe" (
    echo [1/3] Membuat virtual environment (.venv)...
    %PYTHON_CMD% -m venv .venv
    if errorlevel 1 (
        echo [GAGAL] Virtual environment tidak dapat dibuat.
        pause
        exit /b 1
    )
    if exist ".venv\.deps_ok" del ".venv\.deps_ok" >nul 2>nul
) else (
    echo [1/3] Virtual environment sudah ada.
)

call ".venv\Scripts\activate.bat"
if errorlevel 1 (
    echo [GAGAL] Gagal mengaktifkan virtual environment.
    pause
    exit /b 1
)
echo [OK] Virtual environment diaktifkan.

REM --- Pasang dependensi sekali saja ---
if not exist ".venv\.deps_ok" (
    echo [2/3] Memasang dependensi. Proses ini membutuhkan internet satu kali...
    python -m pip install --upgrade pip
    python -m pip install -r requirements.txt
    if errorlevel 1 (
        echo.
        echo [GAGAL] Instalasi dependensi tidak berhasil.
        echo Periksa koneksi internet atau jalankan file ini sebagai administrator.
        pause
        exit /b 1
    )
    echo ok> ".venv\.deps_ok"
    echo [OK] Dependensi terpasang.
) else (
    echo [2/3] Dependensi sudah terpasang.
)

REM --- Jalankan aplikasi ---
echo [3/3] Menjalankan aplikasi di http://localhost:8501
echo.
echo Jendela ini harus tetap terbuka selama aplikasi digunakan.
echo Tekan Ctrl+C untuk menghentikan aplikasi.
echo.

start "" "http://localhost:8501"

python -m streamlit run app.py --server.port 8501 --server.address localhost --server.headless true

echo.
echo Aplikasi telah dihentikan.
pause
endlocal
pause
