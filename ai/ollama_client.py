"""Klien tipis untuk Ollama lokal.

Tidak ada data yang dikirim ke layanan eksternal: seluruh permintaan hanya
menuju alamat server Ollama yang diisi guru (bawaan localhost).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import requests


class OllamaError(RuntimeError):
    """Kesalahan komunikasi dengan Ollama."""


@dataclass
class OllamaClient:
    base_url: str = "http://localhost:11434"
    model: str = "qwen2.5:7b"
    temperature: float = 0.4
    num_predict: int = 2000
    timeout: int = 180

    def __post_init__(self) -> None:
        self.base_url = (self.base_url or "http://localhost:11434").rstrip("/")
        try:
            self.temperature = float(self.temperature)
        except (TypeError, ValueError):
            self.temperature = 0.4
        try:
            self.num_predict = int(self.num_predict)
        except (TypeError, ValueError):
            self.num_predict = 2000
        try:
            self.timeout = max(10, int(self.timeout))
        except (TypeError, ValueError):
            self.timeout = 180

    # ------------------------------------------------------------------
    # Koneksi
    # ------------------------------------------------------------------
    def is_available(self, timeout: int = 4) -> tuple[bool, str]:
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=timeout)
            response.raise_for_status()
            return True, "Terhubung"
        except requests.exceptions.ConnectionError:
            return False, "Server Ollama tidak aktif atau alamat salah."
        except requests.exceptions.Timeout:
            return False, "Koneksi ke Ollama melewati batas waktu."
        except requests.exceptions.HTTPError as exc:
            return False, f"Ollama merespons dengan kesalahan HTTP: {exc}"
        except requests.exceptions.RequestException as exc:
            return False, f"Gagal menghubungi Ollama: {exc}"

    def list_models(self, timeout: int = 8) -> list[str]:
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=timeout)
            response.raise_for_status()
            payload = response.json()
        except requests.exceptions.RequestException as exc:
            raise OllamaError(f"Tidak dapat mengambil daftar model: {exc}") from exc
        models = []
        for item in payload.get("models", []):
            name = item.get("name") or item.get("model")
            if name:
                models.append(name)
        return sorted(models)

    def model_installed(self, model: str | None = None) -> bool:
        target = (model or self.model).strip()
        try:
            daftar = self.list_models()
        except OllamaError:
            return False
        return any(m == target or m.split(":")[0] == target.split(":")[0] for m in daftar)

    # ------------------------------------------------------------------
    # Inferensi
    # ------------------------------------------------------------------
    def chat(self, messages: Iterable[dict], json_mode: bool = False,
             num_predict: int | None = None) -> str:
        payload: dict = {
            "model": self.model,
            "messages": list(messages),
            "stream": False,
            "options": {
                "temperature": self.temperature,
                "num_predict": int(num_predict or self.num_predict),
            },
        }
        if json_mode:
            payload["format"] = "json"

        try:
            response = requests.post(
                f"{self.base_url}/api/chat", json=payload, timeout=self.timeout
            )
        except requests.exceptions.ConnectionError as exc:
            raise OllamaError("Server Ollama tidak aktif. Periksa apakah Ollama sudah dijalankan.") from exc
        except requests.exceptions.Timeout as exc:
            raise OllamaError(
                "Ollama melewati batas waktu. Coba model yang lebih kecil atau kurangi panjang respons."
            ) from exc
        except requests.exceptions.RequestException as exc:
            raise OllamaError(f"Gagal menghubungi Ollama: {exc}") from exc

        if response.status_code == 404:
            raise OllamaError(
                f"Model '{self.model}' tidak ditemukan di Ollama. Jalankan: ollama pull {self.model}"
            )
        if response.status_code >= 400:
            detail = response.text[:300]
            raise OllamaError(f"Ollama menolak permintaan (HTTP {response.status_code}): {detail}")

        try:
            data = response.json()
        except ValueError as exc:
            raise OllamaError("Respons Ollama bukan JSON yang valid.") from exc

        message = data.get("message") or {}
        content = message.get("content")
        if not content:
            # Sebagian versi Ollama memakai field response
            content = data.get("response")
        if not content:
            raise OllamaError("Ollama mengembalikan respons kosong.")
        return content.strip()

    def test(self) -> tuple[bool, str]:
        ok, message = self.is_available()
        if not ok:
            return False, message
        try:
            models = self.list_models()
        except OllamaError as exc:
            return False, str(exc)
        if not models:
            return False, "Ollama aktif, tetapi belum ada model yang terpasang."
        if not self.model_installed(self.model):
            return (
                False,
                f"Ollama aktif, tetapi model '{self.model}' belum terpasang. "
                f"Model tersedia: {', '.join(models)}. Jalankan: ollama pull {self.model}",
            )
        try:
            jawaban = self.chat(
                [
                    {"role": "system", "content": "Jawab sangat singkat dalam bahasa Indonesia."},
                    {"role": "user", "content": "Balas dengan kata: SIAP"},
                ],
                num_predict=20,
            )
        except OllamaError as exc:
            return False, str(exc)
        return True, f"Uji berhasil. Model '{self.model}' merespons: {jawaban[:80]}"
