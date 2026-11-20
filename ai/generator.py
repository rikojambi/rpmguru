"""Mesin generator RPM: orkestrasi AI lokal dan draf offline.

Setiap tahap mengembalikan ``GenResult`` berisi data terstruktur. Bila Ollama
tidak aktif atau gagal, aplikasi tetap menghasilkan draf awal berbasis aturan
(mode offline) yang bisa diedit guru. Draf offline tidak pernah mengklaim
sebagai CP resmi atau dokumen yang telah disahkan.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any

import config
from ai import prompts
from ai.ollama_client import OllamaClient, OllamaError
from database import db


@dataclass
class GenResult:
    data: dict
    mode: str = "offline"  # "ai" | "offline"
    message: str = ""
    model: str = ""
    error: str = ""
    raw: str = field(default="", repr=False)


# ---------------------------------------------------------------------------
# Utilitas teks dan waktu
# ---------------------------------------------------------------------------
def _text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    if isinstance(value, (list, tuple)):
        return "\n".join(str(v).strip() for v in value if str(v).strip())
    return str(value).strip() or default


def _lines(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    text = _text(value)
    if not text:
        return []
    parts = re.split(r"\n|;|(?<=\.)\s+(?=[A-Z0-9])", text)
    cleaned = []
    for part in parts:
        item = re.sub(r"^\s*(?:[-*•]|\d+[.)])\s*", "", part).strip()
        if item:
            cleaned.append(item)
    return cleaned


def _short(value: Any, limit: int = 500) -> str:
    text = _text(value)
    return text if len(text) <= limit else text[: limit - 3].rstrip() + "..."


def _materi(p: dict) -> str:
    return _text(p.get("materi_pokok"), "materi pokok")


def _mapel(p: dict) -> str:
    return _text(p.get("mata_pelajaran"), "mata pelajaran")


def _kelas(p: dict) -> str:
    kelas = _text(p.get("kelas"))
    jenjang = _text(p.get("jenjang"))
    return f"kelas {kelas} {jenjang}".strip() if kelas else (jenjang or "peserta didik")


def _tp_list(p: dict) -> list[str]:
    items = _lines(p.get("tp"))
    if items:
        return items
    materi = _materi(p)
    return [
        f"Peserta didik dapat menjelaskan konsep utama {materi} dengan bahasa sendiri.",
        f"Peserta didik dapat menerapkan konsep {materi} untuk menyelesaikan masalah kontekstual.",
        f"Peserta didik dapat menyajikan hasil kerja dan merefleksikan proses belajarnya.",
    ]


def total_menit(p: dict) -> int:
    teks = _text(p.get("alokasi_waktu"))
    match = re.search(r"(\d+)\s*(?:x|×)\s*(\d+)", teks, re.IGNORECASE)
    if match:
        return int(match.group(1)) * int(match.group(2))
    match = re.search(r"(\d+)\s*JP", teks, re.IGNORECASE)
    if match:
        return int(match.group(1)) * 45
    numbers = [int(n) for n in re.findall(r"\d+", teks)]
    if numbers:
        return max(numbers)
    return 90


def _split_waktu(p: dict) -> tuple[str, str, str]:
    total = max(30, total_menit(p))
    memahami = max(10, round(total * 0.30 / 5) * 5)
    mengaplikasi = max(15, round(total * 0.45 / 5) * 5)
    merefleksi = max(5, total - memahami - mengaplikasi)
    return f"{memahami} menit", f"{mengaplikasi} menit", f"{merefleksi} menit"


def _dimensi_default(p: dict) -> list[str]:
    materi = _materi(p).lower()
    hasil = ["Penalaran kritis", "Kolaborasi"]
    if any(k in materi for k in ("presentasi", "komunikasi", "bahasa", "cerita", "wawancara")):
        hasil.append("Komunikasi")
    if any(k in materi for k in ("karya", "desain", "produk", "proyek", "seni")):
        hasil.append("Kreativitas")
    if any(k in materi for k in ("praktik", "laboratorium", "bengkel", "kesehatan", "olahraga")):
        hasil.append("Kemandirian")
    return list(dict.fromkeys(hasil))[:3]


def rekomendasi_model(p: dict) -> str:
    teks = f"{_materi(p)} {_text(p.get('tp'))} {_text(p.get('elemen'))}".lower()
    if any(k in teks for k in ("proyek", "produk", "karya", "membuat", "merancang")):
        return "Project Based Learning"
    if any(k in teks for k in ("masalah", "kasus", "solusi", "pemecahan")):
        return "Problem Based Learning"
    if any(k in teks for k in ("percobaan", "eksperimen", "penyelidikan", "gejala", "fenomena")):
        return "Discovery Learning"
    if any(k in teks for k in ("praktik", "prosedur", "langkah", "mengoperasikan")):
        return "Direct Instruction"
    return "Cooperative Learning"


# ---------------------------------------------------------------------------
# Parsing dan penggabungan JSON
# ---------------------------------------------------------------------------
def extract_json(text: str) -> dict | None:
    if not text:
        return None
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        data = json.loads(cleaned)
        return data if isinstance(data, dict) else None
    except json.JSONDecodeError:
        pass

    decoder = json.JSONDecoder()
    for index, char in enumerate(cleaned):
        if char != "{":
            continue
        try:
            data, _ = decoder.raw_decode(cleaned[index:])
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            continue
    # Upaya terakhir: potong pada kurung kurawal terakhir
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end > start:
        try:
            data = json.loads(cleaned[start:end + 1])
            return data if isinstance(data, dict) else None
        except json.JSONDecodeError:
            return None
    return None


def _merge(base: Any, incoming: Any) -> Any:
    if isinstance(base, dict):
        if not isinstance(incoming, dict):
            return base
        result = dict(base)
        for key, value in incoming.items():
            result[key] = _merge(base.get(key), value) if key in base else value
        return result
    if isinstance(base, list):
        if not isinstance(incoming, list) or not incoming:
            return base
        return incoming
    if isinstance(incoming, str):
        return incoming.strip() or base
    if incoming is None:
        return base
    return incoming


def _string(value: Any, default: str = "") -> str:
    if isinstance(value, list):
        return "; ".join(_string(v) for v in value if _string(v))
    if isinstance(value, dict):
        return "; ".join(f"{k}: {_string(v)}" for k, v in value.items())
    return _text(value, default)


def _list_of_dicts(value: Any, keys: list[str], base: list[dict] | None = None) -> list[dict]:
    items = value if isinstance(value, list) else ([value] if isinstance(value, dict) else [])
    result = []
    for index, item in enumerate(items):
        if isinstance(item, str):
            item = {keys[0]: item}
        if not isinstance(item, dict):
            continue
        fallback = base[index] if base and index < len(base) else {}
        row = {}
        for key in keys:
            row[key] = _string(item.get(key), fallback.get(key, ""))
        if any(row.values()):
            result.append(row)
    return result or (base or [])


def _list_of_strings(value: Any, base: list[str] | None = None) -> list[str]:
    items = _lines(value)
    return items or (base or [])


# ---------------------------------------------------------------------------
# Draf offline: Identifikasi
# ---------------------------------------------------------------------------
DIMENSI_ALASAN = {
    "Keimanan dan ketakwaan terhadap Tuhan YME": "Materi dan aktivitas memberi ruang untuk mensyukuri ciptaan serta menerapkan sikap jujur dan bertanggung jawab.",
    "Kewargaan": "Aktivitas mendorong kepedulian terhadap lingkungan dan kontribusi bagi masyarakat sekitar.",
    "Penalaran kritis": "Peserta didik perlu menilai informasi, membandingkan sumber, dan mengambil keputusan berbasis bukti.",
    "Kreativitas": "Peserta didik diberi kesempatan menghasilkan gagasan atau karya dengan cara sendiri.",
    "Kolaborasi": "Tugas kelompok menuntut pembagian peran, kesepakatan, dan saling membantu.",
    "Kemandirian": "Peserta didik mengelola waktu, menetapkan langkah kerja, dan mengevaluasi hasil sendiri.",
    "Kesehatan": "Konteks tugas berkaitan dengan pola hidup sehat, keselamatan, atau kesejahteraan.",
    "Komunikasi": "Hasil belajar disampaikan secara lisan, tertulis, atau visual kepada audiens.",
}


def offline_identifikasi(p: dict, dimensi_pilihan: list[str] | None = None) -> dict:
    materi = _materi(p)
    pengetahuan = _text(p.get("pengetahuan_awal"), "Belum ada data rinci; perlu dipetakan melalui asesmen awal.")
    karakter = _text(p.get("karakteristik"), "Peserta didik beragam dalam kecepatan belajar dan gaya belajar.")
    kebutuhan = _text(p.get("kebutuhan_belajar"), "Sebagian peserta didik memerlukan contoh konkret dan pendampingan bertahap.")
    sarana = _text(p.get("sarana"), "Sarana pembelajaran yang tersedia di sekolah.")

    dimensi = dimensi_pilihan or _dimensi_default(p)
    dimensi_rows = []
    for nama in dimensi[:5]:
        dimensi_rows.append(
            {
                "nama": nama,
                "alasan": DIMENSI_ALASAN.get(nama, "Relevan dengan tuntutan aktivitas dan tujuan pembelajaran."),
                "wujud_aktivitas": (
                    f"Peserta didik {('menganalisis informasi tentang ' + materi) if nama == 'Penalaran kritis' else ''}"
                    f"{('bekerja dalam kelompok untuk menyelesaikan tugas tentang ' + materi) if nama == 'Kolaborasi' else ''}"
                    f"{('menyajikan hasil kerja secara jelas kepada kelompok lain') if nama == 'Komunikasi' else ''}"
                    f"{('mengembangkan alternatif solusi atau produk') if nama == 'Kreativitas' else ''}"
                    f"{('menetapkan target dan memeriksa kemajuan belajarnya') if nama == 'Kemandirian' else ''}"
                    f"{('menunjukkan sikap peduli dan bertanggung jawab terhadap lingkungan sekitar') if nama == 'Kewargaan' else ''}"
                    f"{('mensyukuri karunia Tuhan dan menerapkan kejujuran dalam bekerja') if nama.startswith('Keimanan') else ''}"
                    f"{('menerapkan kebiasaan sehat dan aman selama aktivitas') if nama == 'Kesehatan' else ''}"
                ).strip() or f"Ditunjukkan melalui partisipasi aktif dalam kegiatan tentang {materi}.",
            }
        )

    jenis = "konseptual dan prosedural"
    materi_lower = materi.lower()
    if any(k in materi_lower for k in ("istilah", "fakta", "sejarah", "tokoh")):
        jenis = "faktual dan konseptual"
    elif any(k in materi_lower for k in ("prosedur", "langkah", "praktik", "mengoperasikan", "menghitung")):
        jenis = "prosedural"
    elif any(k in materi_lower for k in ("refleksi", "strategi belajar", "metakognisi")):
        jenis = "metakognitif"

    konsep = [materi]
    elemen = _text(p.get("elemen"))
    if elemen and elemen.lower() != materi.lower():
        konsep.append(elemen)
    atp = _lines(p.get("atp"))
    if atp:
        konsep.extend([_short(item, 80) for item in atp[:2]])
    konsep = list(dict.fromkeys(konsep))[:4]

    return {
        "kesiapan": {
            "pengetahuan_awal": pengetahuan,
            "tingkat_pemahaman": (
                f"Pemahaman awal {_kelas(p)} terhadap {materi} belum seragam. "
                "Guru perlu memetakan pemahaman melalui pertanyaan diagnostik sebelum kegiatan inti."
            ),
            "keterampilan_awal": (
                f"Keterampilan yang relevan dengan {materi} perlu dipetakan, misalnya kemampuan mengamati, "
                "mencatat data, berdiskusi, dan menyajikan hasil. Peserta didik dengan keterampilan awal rendah "
                "mendapat contoh dan pendampingan langkah demi langkah."
            ),
            "kesulitan_belajar": (
                f"Kesulitan yang mungkin muncul: memahami istilah kunci pada {materi}, menghubungkan konsep dengan "
                "pengalaman nyata, serta menjaga fokus saat kerja kelompok. Kesulitan ini perlu dipantau melalui "
                "observasi dan umpan balik singkat."
            ),
            "kebutuhan_dukungan": kebutuhan,
        },
        "materi": {
            "jenis_pengetahuan": jenis,
            "konsep_utama": konsep,
            "keterkaitan": (
                f"Materi {materi} terhubung dengan materi sebelumnya pada elemen {elemen or _mapel(p)} "
                "dan menjadi dasar untuk materi berikutnya. Guru dapat menunjukkan keterkaitan melalui peta konsep "
                "atau pertanyaan penghubung."
            ),
            "penerapan": (
                f"Penerapan {materi} dapat ditemukan pada {_text(p.get('konteks_lingkungan'), 'kehidupan sehari-hari di sekitar sekolah')}. "
                "Guru perlu memilih contoh yang dekat dengan pengalaman peserta didik."
            ),
            "potensi_kontekstual": (
                f"Konteks lingkungan sekolah dan pengalaman peserta didik dapat dijadikan sumber masalah nyata. "
                f"Sarana yang tersedia ({_short(sarana, 160)}) dapat dimanfaatkan tanpa menuntut peralatan tambahan."
            ),
        },
        "dimensi": dimensi_rows,
        "catatan": (
            "Draf identifikasi ini disusun dari data yang diisi guru. Bagian yang belum memiliki data rinci "
            "ditandai sebagai kebutuhan pemetaan melalui asesmen awal, bukan sebagai kesimpulan final."
        ),
    }


# ---------------------------------------------------------------------------
# Draf offline: Desain
# ---------------------------------------------------------------------------
def _model_name(p: dict, pilihan: str | None) -> str:
    if pilihan and pilihan in config.MODEL_PEMBELAJARAN:
        return pilihan
    if pilihan and pilihan.strip():
        return pilihan.strip()
    return rekomendasi_model(p)


def offline_desain(p: dict, identifikasi: dict, model_pilihan: str | None = None) -> dict:
    materi = _materi(p)
    tp_items = _tp_list(p)
    dimensi = [d.get("nama", "") for d in identifikasi.get("dimensi", []) if d.get("nama")]
    dimensi_teks = ", ".join(dimensi[:3]) or "Penalaran kritis, Kolaborasi"

    tujuan = []
    for tp in tp_items[:6]:
        kalimat = tp.strip().rstrip(".")
        tujuan.append(
            {
                "tp": kalimat + ".",
                "indikator": (
                    f"Peserta didik menunjukkan ketercapaian melalui penjelasan, unjuk kerja, atau produk yang "
                    f"memuat {materi} secara tepat dan dapat diperiksa guru."
                ),
                "asesmen": "Observasi proses, LKPD/kuis formatif, dan unjuk kerja atau produk akhir.",
            }
        )

    model = _model_name(p, model_pilihan)
    sintaks = config.SINTAKS_MODEL.get(model, config.SINTAKS_MODEL["Model lainnya"])
    alasan_model = {
        "Problem Based Learning": f"Materi {materi} dapat dikaitkan dengan masalah nyata sehingga peserta didik belajar menerapkan konsep, bukan hanya menghafal.",
        "Project Based Learning": f"Materi {materi} memungkinkan peserta didik menghasilkan produk atau karya sebagai bukti pemahaman.",
        "Discovery Learning": f"Konsep pada {materi} dapat ditemukan peserta didik melalui pengamatan dan penyelidikan terbimbing.",
        "Inquiry Learning": f"Peserta didik dapat mengembangkan pertanyaan dan mencari jawaban tentang {materi} secara terbimbing.",
        "Cooperative Learning": f"Kerja kelompok membantu peserta didik saling menjelaskan {materi} dan membangun pemahaman bersama.",
        "Contextual Teaching and Learning": f"Materi {materi} dapat dihubungkan langsung dengan pengalaman dan lingkungan peserta didik.",
        "Direct Instruction": f"Keterampilan prosedural pada {materi} memerlukan demonstrasi dan latihan terbimbing sebelum mandiri.",
        "Pembelajaran kolaboratif": f"Tugas kolaboratif memberi ruang bagi peserta didik untuk berbagi peran dalam memahami {materi}.",
        "Model lainnya": f"Model dipilih guru dengan mempertimbangkan karakteristik {materi} dan kondisi kelas.",
    }.get(model, f"Model dipilih agar sesuai dengan karakteristik {materi}.")

    kemitraan = [
        {"pihak": "Antarsiswa", "peran": "Saling menjelaskan konsep, berbagi peran dalam kelompok, dan memberi umpan balik."},
        {"pihak": "Guru dengan siswa", "peran": "Guru memberi pertanyaan pemandu, umpan balik, dan dukungan bertahap."},
        {"pihak": "Orang tua", "peran": "Mendukung belajar di rumah dengan menanyakan hasil kerja dan menyediakan waktu belajar."},
    ]
    if _text(p.get("jenjang")) in ("SMK", "MAK"):
        kemitraan.append(
            {"pihak": "Dunia usaha dan dunia industri", "peran": "Memberi contoh penerapan di tempat kerja atau meninjau hasil kerja peserta didik."}
        )
    konteks = _text(p.get("konteks_lingkungan"))
    if konteks:
        kemitraan.append({"pihak": "Masyarakat", "peran": f"Menjadi sumber informasi atau konteks nyata: {_short(konteks, 120)}."})

    lingkungan = ["Ruang kelas"]
    sarana = _text(p.get("sarana")).lower()
    if any(k in sarana for k in ("lab", "laboratorium")):
        lingkungan.append("Laboratorium")
    if "bengkel" in sarana:
        lingkungan.append("Bengkel praktik")
    if konteks:
        lingkungan.append("Lingkungan sekolah")
    if any(k in sarana for k in ("komputer", "laptop", "proyektor", "hp", "internet", "wifi")):
        lingkungan.append("Lingkungan digital")

    digital = []
    if any(k in sarana for k in ("komputer", "laptop")):
        digital.append({"alat": "Komputer/laptop", "pemanfaatan": "Mengolah data, mengetik laporan, atau membuat presentasi secara luring."})
    if any(k in sarana for k in ("hp", "smartphone", "ponsel")):
        digital.append({"alat": "Smartphone", "pemanfaatan": "Merekam hasil pengamatan atau memindai bahan bacaan; digunakan sesuai kesepakatan kelas."})
    if any(k in sarana for k in ("internet", "wifi", "jaringan")) and not any(k in sarana for k in ("tidak ada internet", "terbatas", "tanpa internet")):
        digital.append({"alat": "Internet", "pemanfaatan": "Mencari satu sumber pembanding dengan arahan guru; tidak menjadi syarat utama tugas."})
    digital.append({"alat": "Media pembelajaran luring", "pemanfaatan": "Bahan cetak, kartu tugas, gambar, atau benda nyata yang tersedia di sekolah."})
    if any(k in sarana for k in ("proyektor", "lcd", "tv")):
        digital.append({"alat": "Proyektor/TV", "pemanfaatan": "Menampilkan contoh, pertanyaan pemantik, atau hasil kerja kelompok."})

    prinsip = [
        {
            "prinsip": "Berkesadaran",
            "wujud": "Guru menyampaikan tujuan dan kriteria keberhasilan di awal; peserta didik menandai bagian yang sudah dipahami dan yang masih sulit pada lembar refleksi.",
        },
        {
            "prinsip": "Bermakna",
            "wujud": f"Tugas dihubungkan dengan konteks {konteks or 'kehidupan sehari-hari peserta didik'}, sehingga peserta didik melihat kegunaan {materi}.",
        },
        {
            "prinsip": "Menggembirakan",
            "wujud": "Peserta didik diberi pilihan cara menyajikan hasil, bekerja dalam kelompok kecil, dan memperoleh apresiasi atas proses, bukan hanya nilai akhir.",
        },
    ]

    return {
        "tujuan": tujuan,
        "model": {"nama": model, "alasan": alasan_model, "sintaks": list(sintaks)},
        "kemitraan": kemitraan,
        "lingkungan": list(dict.fromkeys(lingkungan)),
        "digital": digital,
        "prinsip": prinsip,
        "catatan": (
            f"Dimensi profil lulusan yang ditekankan: {dimensi_teks}. "
            "Tujuan pembelajaran mengacu pada TP yang diisi guru; guru tetap perlu memeriksa keselarasan dengan CP dan ATP."
        ),
    }


# ---------------------------------------------------------------------------
# Draf offline: Pengalaman belajar
# ---------------------------------------------------------------------------
def offline_pengalaman(p: dict, desain: dict) -> dict:
    materi = _materi(p)
    model = _text(desain.get("model", {}).get("nama"), "Cooperative Learning")
    tp = _text(desain.get("tujuan", [{}])[0].get("tp") if desain.get("tujuan") else "", f"memahami {materi}")
    sumber = _text(p.get("sumber_belajar"), "buku teks, bahan ajar, dan sumber yang tersedia di sekolah")
    sarana = _text(p.get("sarana"), "media yang tersedia")
    konteks = _text(p.get("konteks_lingkungan"), "lingkungan sekitar sekolah")
    dimensi = _text(desain.get("catatan")).split(":")[-1].strip(" .") if "Dimensi" in _text(desain.get("catatan")) else "Penalaran kritis, Kolaborasi"
    w_memahami, w_aplikasi, w_refleksi = _split_waktu(p)

    sintaks = config.SINTAKS_MODEL.get(model, config.SINTAKS_MODEL["Model lainnya"])
    langkah_awal = sintaks[0] if sintaks else "Orientasi"
    langkah_tengah = sintaks[1] if len(sintaks) > 1 else "Kegiatan inti"

    memahami = {
        "aktivitas_guru": (
            f"Guru membuka dengan pertanyaan pemantik tentang {materi}, menyampaikan tujuan dan kriteria keberhasilan, "
            f"kemudian memandu kegiatan '{langkah_awal.lower()}'. Guru memberi contoh, mendengarkan jawaban awal, "
            "dan mencatat miskonsepsi yang perlu ditindaklanjuti."
        ),
        "aktivitas_siswa": (
            f"Peserta didik mengamati contoh/fenomena tentang {materi}, membaca sumber ({_short(sumber, 120)}), "
            f"lalu berdiskusi dalam kelompok kecil untuk mengidentifikasi ciri, istilah kunci, dan pertanyaan yang belum terjawab. "
            f"Setiap kelompok menuliskan hasil dugaan pada peta konsep sederhana."
        ),
        "alokasi": w_memahami,
        "media": f"{_short(sarana, 120)}; {_short(sumber, 120)}; papan tulis atau kertas kerja.",
        "dimensi": dimensi,
        "prinsip": (
            "Berkesadaran: tujuan dan kriteria dibahas sebelum tugas. Bermakna: contoh diambil dari konteks nyata. "
            "Menggembirakan: peserta didik boleh menyampaikan dugaan tanpa takut salah."
        ),
        "bukti": "Catatan hasil diskusi, peta konsep awal, dan jawaban lisan/tertulis pada pertanyaan pemantik.",
    }

    mengaplikasi = {
        "aktivitas_guru": (
            f"Guru memberi tugas kontekstual tentang {materi}, menjelaskan langkah kerja dan batas waktu, "
            f"lalu berkeliling memberi umpan balik. Guru menggunakan pertanyaan lanjutan untuk mendorong peserta didik "
            "menjelaskan alasan jawabannya dan membantu kelompok yang tertinggal."
        ),
        "aktivitas_siswa": (
            f"Peserta didik mengerjakan tugas '{langkah_tengah.lower()}' secara berkelompok: menganalisis kasus atau data "
            f"tentang {materi}, mencoba langkah penyelesaian, dan menyiapkan hasil kerja. Hasil dihubungkan dengan "
            f"{_short(konteks, 100)}. Kelompok yang selesai lebih cepat diberi tantangan tambahan, bukan tugas baru."
        ),
        "alokasi": w_aplikasi,
        "media": f"LKPD, data/kasus kontekstual, {_short(sarana, 100)}, dan alat tulis.",
        "dimensi": dimensi,
        "prinsip": (
            "Bermakna: tugas menyerupai situasi nyata dan hasilnya dapat digunakan. Menggembirakan: ada pilihan cara kerja "
            "dan apresiasi proses. Berkesadaran: kelompok memeriksa kecocokan hasil dengan kriteria."
        ),
        "bukti": "LKPD terisi, catatan proses kerja kelompok, dan produk/hasil kerja yang dapat diperiksa.",
    }

    merefleksi = {
        "aktivitas_guru": (
            "Guru memandu presentasi singkat antar kelompok, memberi umpan balik berdasarkan kriteria, "
            "lalu mengajak peserta didik menilai proses kerja. Guru menutup dengan mengaitkan hasil belajar "
            "dengan tujuan dan menyampaikan langkah tindak lanjut."
        ),
        "aktivitas_siswa": (
            f"Peserta didik menyampaikan hal yang dipelajari tentang {materi}, membandingkan hasil dengan kelompok lain, "
            "menuliskan kesulitan dan rencana perbaikan pada lembar refleksi. Setiap peserta didik menuliskan satu "
            "penerapan yang akan dilakukan di luar kelas."
        ),
        "alokasi": w_refleksi,
        "media": "Lembar refleksi, hasil kerja kelompok, dan rubrik penilaian singkat.",
        "dimensi": dimensi,
        "prinsip": (
            "Berkesadaran: peserta didik menilai kemajuan terhadap tujuan. Bermakna: refleksi dikaitkan dengan penerapan "
            "nyata. Menggembirakan: apresiasi diberikan kepada proses, usaha, dan perbaikan."
        ),
        "bukti": "Lembar refleksi terisi dan catatan tindak lanjut perbaikan.",
    }

    return {
        "memahami": memahami,
        "mengaplikasi": mengaplikasi,
        "merefleksi": merefleksi,
        "catatan": (
            f"Alokasi mengikuti total {total_menit(p)} menit. Sesuaikan pembagian bila jam pelajaran sekolah berbeda. "
            f"Tujuan yang menjadi fokus tahap ini: {_short(tp, 160)}"
        ),
    }


# ---------------------------------------------------------------------------
# Draf offline: Asesmen
# ---------------------------------------------------------------------------
def _rubrik(kriteria: list[str], levels: list[str] | None = None) -> list[dict]:
    levels = levels or ["Perlu bimbingan", "Berkembang", "Mahir", "Sangat mahir"]
    return [
        {
            "kriteria": kriteria[0],
            "deskripsi": " | ".join(f"{level}: {desc}" for level, desc in zip(levels, [
                "Belum menunjukkan ketercapaian; perlu contoh dan pendampingan penuh.",
                "Menunjukkan sebagian ketercapaian; masih perlu koreksi pada bagian tertentu.",
                "Menunjukkan ketercapaian sesuai kriteria secara mandiri.",
                "Menunjukkan ketercapaian dengan penjelasan tambahan atau penerapan pada situasi baru.",
            ])),
        },
        {
            "kriteria": kriteria[1] if len(kriteria) > 1 else "Proses kerja",
            "deskripsi": " | ".join(f"{level}: {desc}" for level, desc in zip(levels, [
                "Belum terlibat atau langkah kerja belum terarah.",
                "Terlibat pada sebagian langkah dengan bantuan guru.",
                "Mengikuti langkah kerja dan bekerja sama dengan konsisten.",
                "Mengelola langkah kerja dan membantu kelompok menyelesaikan tugas.",
            ])),
        },
        {
            "kriteria": kriteria[2] if len(kriteria) > 2 else "Penyajian hasil",
            "deskripsi": " | ".join(f"{level}: {desc}" for level, desc in zip(levels, [
                "Hasil belum lengkap dan sulit dipahami.",
                "Hasil sebagian lengkap; penyajian perlu perbaikan.",
                "Hasil lengkap dan disajikan dengan jelas.",
                "Hasil lengkap, jelas, dan memberi tanggapan terhadap pertanyaan.",
            ])),
        },
    ]


def offline_asesmen(p: dict, desain: dict) -> dict:
    materi = _materi(p)
    konteks = _text(p.get("konteks_lingkungan"), "lingkungan sekitar sekolah")
    tp_rows = desain.get("tujuan", [])
    tp_teks = _text(tp_rows[0].get("tp") if tp_rows else "", f"memahami {materi}")
    total = total_menit(p)

    awal = {
        "tujuan": f"Memetakan kesiapan belajar dan pengetahuan awal peserta didik tentang {materi} sebelum pembelajaran dimulai.",
        "instrumen": "Kuis diagnostik singkat (lisan/tertulis), angket nonkognitif, dan pertanyaan pemantik.",
        "soal": [
            f"Apa yang sudah kamu ketahui tentang {materi}? Sebutkan satu contoh yang pernah kamu lihat.",
            f"Menurutmu, mengapa mempelajari {materi} penting dalam kehidupan sehari-hari?",
            f"Bagian mana dari {materi} yang menurutmu paling sulit? Apa yang biasanya membantumu belajar?",
            "Bagaimana perasaanmu hari ini? Pilih gambar/emotikon dan jelaskan alasannya secara singkat.",
        ],
        "kunci": [
            "Rambu: jawaban memuat pengetahuan awal yang relevan; tidak dinilai benar/salah, digunakan untuk pemetaan.",
            "Rambu: jawaban menunjukkan kesadaran kegunaan; catat contoh yang disebut.",
            "Rambu: catat kesulitan yang disebut untuk menentukan scaffolding.",
            "Rambu: catat kondisi emosi dan kebutuhan dukungan; jaga kerahasiaan jawaban.",
        ],
        "pedoman": "Tidak diberi nilai angka. Jawaban dikelompokkan menjadi: sudah paham, perlu penguatan, dan perlu pendampingan intensif.",
        "rubrik": _rubrik(["Pengetahuan awal", "Kesiapan belajar", "Keterlibatan awal"]),
        "kktp": f"Peserta didik dinyatakan siap memulai apabila dapat menyebutkan satu pengetahuan awal tentang {materi} dan mengikuti instruksi awal dengan bantuan yang sesuai.",
    }

    proses = {
        "tujuan": f"Memantau perkembangan pemahaman dan keterampilan peserta didik selama mempelajari {materi}, serta memberi umpan balik yang memperbaiki proses belajar.",
        "instrumen": "Observasi kelas, LKPD, kuis formatif singkat, dan umpan balik lisan/tertulis.",
        "soal": [
            f"Jelaskan dengan bahasamu sendiri apa yang dimaksud dengan {materi}.",
            f"Berikan satu contoh penerapan {materi} di {konteks} dan jelaskan alasanmu.",
            f"Periksa kembali hasil kerjamu: bagian mana yang sudah tepat dan bagian mana yang perlu diperbaiki?",
            "Tuliskan satu pertanyaan yang masih kamu miliki tentang materi ini.",
        ],
        "kunci": [
            "Rambu: jawaban memuat ciri/definisi utama sesuai sumber belajar yang dipakai.",
            "Rambu: contoh relevan dengan konteks dan alasan dapat diterima.",
            "Rambu: peserta didik menunjukkan kesadaran terhadap kriteria keberhasilan.",
            "Rambu: pertanyaan digunakan guru untuk tindak lanjut, bukan dinilai.",
        ],
        "pedoman": "Observasi dinilai dengan rubrik 3 kriteria. Kuis formatif diberi umpan balik, bukan hanya angka. Peserta didik yang belum mencapai KKTP mendapat latihan tambahan dan kesempatan memperbaiki.",
        "rubrik": _rubrik(["Pemahaman konsep", "Penerapan konteks", "Umpan balik dan perbaikan"]),
        "kktp": f"Peserta didik mencapai KKTP apabila dapat menjelaskan {materi} dengan bahasa sendiri dan memberi satu contoh penerapan yang relevan.",
    }

    akhir = {
        "tujuan": f"Mengukur ketercapaian tujuan pembelajaran tentang {materi} secara menyeluruh melalui tes dan unjuk kerja.",
        "instrumen": "Tes tertulis (uraian), unjuk kerja/produk, dan presentasi singkat.",
        "soal": [
            f"Jelaskan konsep utama {materi} dan berikan dua contoh yang berbeda.",
            f"Analisis kasus berikut yang berkaitan dengan {konteks}. Tentukan langkah penyelesaian yang tepat dan jelaskan alasanmu.",
            f"Bandingkan dua cara/ pendekatan yang dapat digunakan untuk menyelesaikan masalah tentang {materi}. Mana yang lebih tepat untuk konteksmu?",
            f"Buatlah produk/presentasi singkat yang menunjukkan penerapan {materi}. Sertakan sumber yang kamu gunakan.",
            "Tuliskan satu rencana penerapan yang akan kamu lakukan setelah pembelajaran ini.",
        ],
        "kunci": [
            "Rambu: jawaban memuat konsep utama dan dua contoh yang relevan; sesuaikan dengan sumber belajar.",
            "Rambu: langkah penyelesaian logis, alasan didukung data/konsep, dan mempertimbangkan konteks.",
            "Rambu: perbandingan memuat kelebihan/kekurangan dan keputusan yang beralasan.",
            "Rambu: produk sesuai kriteria: ketepatan konsep, kejelasan, dan relevansi konteks.",
            "Rambu: rencana konkret dan dapat dilakukan.",
        ],
        "pedoman": "Skor tes tertulis 50%, unjuk kerja/produk 40%, presentasi 10%. Nilai akhir = jumlah skor komponen. Peserta didik yang belum mencapai KKTP diberi kesempatan perbaikan pada komponen yang belum tuntas.",
        "rubrik": _rubrik(["Ketepatan konsep", "Penerapan dan penalaran", "Penyajian produk"]),
        "kktp": f"Peserta didik mencapai KKTP apabila memperoleh minimal 70% dari total skor dan menunjukkan penerapan {materi} yang relevan pada tugas akhir.",
    }

    return {
        "awal": awal,
        "proses": proses,
        "akhir": akhir,
        "catatan": (
            f"Asesmen disusun untuk alokasi {total} menit. Kunci jawaban berupa rambu agar guru menyesuaikan dengan "
            "sumber belajar yang benar-benar dipakai; hindari menilai berdasarkan hafalan di luar sumber."
        ),
    }


# ---------------------------------------------------------------------------
# Draf offline: Diferensiasi, LKPD, Refleksi
# ---------------------------------------------------------------------------
def offline_diferensiasi(p: dict, desain: dict, pengalaman: dict) -> dict:
    materi = _materi(p)
    tp_rows = desain.get("tujuan", [])
    tp_teks = _short(tp_rows[0].get("tp") if tp_rows else f"memahami {materi}", 160)
    return {
        "ringkasan": (
            "Satu pembelajaran inti dengan tiga tingkat dukungan. Semua peserta didik mengikuti tujuan dan aktivitas "
            "utama yang sama; perbedaan terletak pada kompleksitas tugas, bantuan, sumber, dan pilihan produk."
        ),
        "tingkat": [
            {
                "tingkat": "Perlu bimbingan",
                "kesiapan": "Belum memiliki pengetahuan awal yang cukup dan memerlukan langkah kerja yang lebih terstruktur.",
                "kompleksitas": f"Fokus pada satu aspek utama {materi}; tugas dipecah menjadi langkah kecil.",
                "scaffolding": "Contoh yang sudah dikerjakan sebagian, kata kunci, kartu langkah, dan pendampingan guru/ tutor sebaya.",
                "sumber": "Bahan bacaan ringkas dengan gambar, contoh konkret, dan glosarium.",
                "pengelompokan": "Kelompok kecil heterogen dengan satu teman pendamping; guru bekerja dengan kelompok ini lebih lama.",
                "produk": "Mengisi LKPD terbimbing atau menyajikan hasil dengan bantuan format yang disediakan.",
            },
            {
                "tingkat": "Berkembang",
                "kesiapan": "Memiliki pengetahuan awal dan dapat mengikuti langkah kerja dengan sedikit bantuan.",
                "kompleksitas": f"Menerapkan konsep {materi} pada satu kasus dan menjelaskan alasan langkah kerja.",
                "scaffolding": "Pertanyaan pemandu pada LKPD dan umpan balik berkala dari guru.",
                "sumber": "Buku teks/bahan ajar utama dan satu contoh tambahan.",
                "pengelompokan": "Kelompok berpasangan atau tiga orang dengan peran yang disepakati.",
                "produk": "LKPD lengkap dengan penjelasan, atau presentasi singkat hasil kerja.",
            },
            {
                "tingkat": "Mahir",
                "kesiapan": "Menguasai pengetahuan awal dan mampu bekerja mandiri serta membantu teman.",
                "kompleksitas": f"Menganalisis kasus baru, membandingkan alternatif solusi, atau memperluas penerapan {materi}.",
                "scaffolding": "Tantangan tambahan berupa pertanyaan terbuka; guru memberi umpan balik pada penalaran, bukan langkah.",
                "sumber": "Sumber tambahan yang tersedia di sekolah, data nyata, atau rujukan mandiri tanpa mewajibkan internet.",
                "pengelompokan": "Kelompok fleksibel; dapat menjadi tutor sebaya atau bekerja mandiri pada bagian tantangan.",
                "produk": "Produk orisinal, analisis kasus, atau presentasi dengan rekomendasi.",
            },
        ],
        "catatan": (
            f"Diferensiasi mengacu pada tujuan: {tp_teks}. Guru tidak perlu membuat tiga rencana terpisah; "
            "gunakan tugas inti yang sama dengan variasi dukungan dan produk. Pantau siapa yang berpindah tingkat "
            "setelah asesmen formatif."
        ),
    }


def offline_lkpd(p: dict, desain: dict, pengalaman: dict) -> dict:
    materi = _materi(p)
    konteks = _text(p.get("konteks_lingkungan"), "lingkungan sekitar sekolah")
    tp_rows = desain.get("tujuan", [])
    tp_teks = "\n".join(f"{i+1}. {row.get('tp','')}" for i, row in enumerate(tp_rows[:4]))
    return {
        "judul": f"LKPD - {materi}",
        "identitas": (
            f"Nama: ____________________  Kelas: {_text(p.get('kelas'), '____')}  "
            f"Kelompok: ____________  Tanggal: ____________"
        ),
        "tujuan": tp_teks or f"Peserta didik dapat memahami dan menerapkan {materi}.",
        "petunjuk": (
            "1. Baca seluruh petunjuk sebelum bekerja.\n"
            "2. Diskusikan dengan kelompok dan tuliskan jawaban dengan bahasa sendiri.\n"
            "3. Tulis sumber yang kamu gunakan.\n"
            "4. Tanyakan kepada guru bila ada bagian yang belum jelas.\n"
            "5. Periksa kembali hasil kerja sebelum dikumpulkan."
        ),
        "masalah": (
            f"Di {konteks}, ditemukan situasi yang berkaitan dengan {materi}. "
            f"Sebagai anggota masyarakat, kamu diminta memahami situasi tersebut dan mengusulkan langkah yang tepat. "
            "Gunakan informasi pada bahan bacaan dan hasil pengamatanmu."
        ),
        "memahami": (
            f"1. Amati contoh/gambar/data yang disediakan guru.\n"
            f"2. Tuliskan tiga hal penting yang kamu temukan tentang {materi}.\n"
            f"3. Jelaskan hubungan antara temuanmu dengan pengetahuan yang sudah kamu miliki.\n"
            "4. Tuliskan satu pertanyaan yang masih ingin kamu jawab."
        ),
        "mengaplikasi": (
            f"1. Identifikasi masalah utama pada situasi di atas.\n"
            f"2. Gunakan konsep {materi} untuk menyusun langkah penyelesaian.\n"
            "3. Tuliskan data/alasan yang mendukung langkahmu.\n"
            "4. Siapkan hasil kerja dalam bentuk yang dapat dipresentasikan (tulisan, diagram, atau produk sederhana)."
        ),
        "merefleksi": (
            "1. Apa hal terpenting yang kamu pelajari hari ini?\n"
            "2. Bagian mana yang masih sulit? Apa yang akan kamu lakukan untuk memperbaikinya?\n"
            "3. Bagaimana hasil kerjamu dibandingkan dengan kriteria keberhasilan?"
        ),
        "pertanyaan": [
            f"Mengapa {materi} penting dalam situasi tersebut?",
            "Apa yang akan terjadi jika langkah penyelesaian tidak dilakukan dengan tepat?",
            "Adakah cara lain yang lebih efektif? Jelaskan alasannya.",
            "Sumber apa yang kamu gunakan, dan mengapa sumber itu dapat dipercaya?",
        ],
        "kesimpulan": (
            f"Tuliskan kesimpulanmu tentang {materi} dalam 3-5 kalimat. "
            "Sertakan satu contoh penerapan yang dapat dilakukan di lingkunganmu."
        ),
        "penilaian": (
            "Penilaian menggunakan rubrik: ketepatan konsep, kelengkapan langkah kerja, kualitas alasan/bukti, "
            "dan kejelasan penyajian. Nilai akhir merupakan rata-rata kriteria dengan skala 1-4."
        ),
    }


def offline_refleksi(p: dict, desain: dict) -> dict:
    materi = _materi(p)
    return {
        "siswa": [
            f"Apa hal baru yang saya pelajari tentang {materi}?",
            "Bagian mana yang sudah saya pahami dengan baik? Bagaimana saya tahu?",
            f"Bagaimana saya dapat menerapkan {materi} di rumah atau lingkungan saya?",
            "Apa kesulitan yang saya hadapi, dan bantuan apa yang saya butuhkan?",
            "Apa satu hal yang akan saya perbaiki pada belajar berikutnya?",
        ],
        "guru": [
            "Apakah tujuan pembelajaran tercapai? Bukti apa yang menunjukkan hal itu?",
            "Apakah aktivitas berjalan efektif? Bagian mana yang perlu diubah?",
            "Apakah seluruh peserta didik terlibat? Siapa yang perlu perhatian khusus?",
            f"Bagaimana hasil asesmen formatif tentang {materi}? Pola kesulitan apa yang muncul?",
            "Apa perbaikan konkret untuk pembelajaran berikutnya?",
        ],
        "catatan": (
            "Refleksi diisi pada akhir pembelajaran. Guru dapat memilih 2-3 pertanyaan yang paling relevan "
            "agar waktu refleksi tidak berlebihan."
        ),
    }


# ---------------------------------------------------------------------------
# Orkestrasi AI + fallback
# ---------------------------------------------------------------------------
def _context_pembelajaran(p: dict) -> dict:
    keys = [
        "judul", "jenjang", "fase", "kelas", "semester", "mata_pelajaran", "konsentrasi",
        "elemen", "cp", "atp", "materi_pokok", "tp", "alokasi_waktu", "jumlah_peserta",
        "karakteristik", "pengetahuan_awal", "kebutuhan_belajar", "konteks_lingkungan",
        "sarana", "sumber_belajar",
    ]
    context = {}
    for key in keys:
        value = p.get(key)
        if isinstance(value, str):
            value = _short(value, 4000) if key in ("cp", "atp") else _short(value, 2500)
        context[key] = value
    return context


def _run_ai(client: OllamaClient | None, messages: list[dict], tahap: str,
            rpm_id: int | None) -> tuple[dict | None, str, str]:
    """Menjalankan AI dan mengembalikan (data, error, raw)."""
    if not client:
        return None, "AI tidak diaktifkan.", ""
    try:
        raw = client.chat(messages, json_mode=True)
    except OllamaError as exc:
        db.log_ai(rpm_id, tahap, client.model, messages[-1].get("content", ""), "", f"gagal: {exc}")
        return None, str(exc), ""
    parsed = extract_json(raw)
    if not parsed:
        db.log_ai(rpm_id, tahap, client.model, messages[-1].get("content", ""), raw, "json_tidak_valid")
        return None, "Respons AI tidak dapat dibaca sebagai JSON. Draf offline digunakan.", raw
    db.log_ai(rpm_id, tahap, client.model, messages[-1].get("content", ""), raw, "sukses")
    return parsed, "", raw


def _result(offline: dict, ai_data: dict | None, error: str, client: OllamaClient | None,
            success_note: str) -> GenResult:
    if ai_data is None:
        return GenResult(
            data=offline,
            mode="offline",
            message=("Draf offline dipakai. " + error).strip(),
            model=client.model if client else "",
            error=error,
        )
    merged = _merge(offline, ai_data)
    return GenResult(
        data=merged,
        mode="ai",
        message=success_note,
        model=client.model if client else "",
    )


def generate_identifikasi(client: OllamaClient | None, p: dict, dimensi_pilihan: list[str] | None = None,
                          use_ai: bool = True, rpm_id: int | None = None) -> GenResult:
    offline = offline_identifikasi(p, dimensi_pilihan)
    if not use_ai or not client:
        return GenResult(data=offline, mode="offline", message="Draf identifikasi disusun tanpa AI. Silakan periksa dan edit.")
    context = _context_pembelajaran(p)
    context["dimensi_pilihan_guru"] = dimensi_pilihan or []
    ai, error, _ = _run_ai(client, prompts.prompt_identifikasi(context), "identifikasi", rpm_id)
    if ai:
        ai["dimensi"] = _list_of_dicts(ai.get("dimensi"), ["nama", "alasan", "wujud_aktivitas"], offline["dimensi"])
        if isinstance(ai.get("materi"), dict):
            ai["materi"]["konsep_utama"] = _list_of_strings(
                ai["materi"].get("konsep_utama"), offline["materi"]["konsep_utama"]
            )
        else:
            ai["materi"] = offline["materi"]
    return _result(offline, ai, error, client, "Identifikasi berhasil dibuat dengan AI. Periksa kembali sebelum disetujui.")


def generate_desain(client: OllamaClient | None, p: dict, identifikasi: dict, model_pilihan: str | None = None,
                    use_ai: bool = True, rpm_id: int | None = None) -> GenResult:
    offline = offline_desain(p, identifikasi, model_pilihan)
    if not use_ai or not client:
        return GenResult(data=offline, mode="offline", message="Draf desain disusun tanpa AI. Silakan periksa dan edit.")
    context = _context_pembelajaran(p)
    context["identifikasi"] = identifikasi
    context["model_pilihan_guru"] = model_pilihan or ""
    ai, error, _ = _run_ai(client, prompts.prompt_desain(context), "desain", rpm_id)
    if ai:
        ai["tujuan"] = _list_of_dicts(ai.get("tujuan"), ["tp", "indikator", "asesmen"], offline["tujuan"])
        ai["kemitraan"] = _list_of_dicts(ai.get("kemitraan"), ["pihak", "peran"], offline["kemitraan"])
        ai["digital"] = _list_of_dicts(ai.get("digital"), ["alat", "pemanfaatan"], offline["digital"])
        ai["prinsip"] = _list_of_dicts(ai.get("prinsip"), ["prinsip", "wujud"], offline["prinsip"])
        ai["lingkungan"] = _list_of_strings(ai.get("lingkungan"), offline["lingkungan"])
        if isinstance(ai.get("model"), dict):
            ai["model"]["sintaks"] = _list_of_strings(
                ai["model"].get("sintaks"), offline["model"]["sintaks"]
            )
        else:
            ai["model"] = offline["model"]
    return _result(offline, ai, error, client, "Desain pembelajaran berhasil dibuat dengan AI. Periksa keselarasan tujuan dan asesmen.")


def generate_pengalaman(client: OllamaClient | None, p: dict, desain: dict,
                        use_ai: bool = True, rpm_id: int | None = None) -> GenResult:
    offline = offline_pengalaman(p, desain)
    if not use_ai or not client:
        return GenResult(data=offline, mode="offline", message="Draf pengalaman belajar disusun tanpa AI. Silakan periksa dan edit.")
    context = _context_pembelajaran(p)
    context["desain"] = desain
    ai, error, _ = _run_ai(client, prompts.prompt_pengalaman(context), "pengalaman", rpm_id)
    if ai:
        for tahap in ("memahami", "mengaplikasi", "merefleksi"):
            if not isinstance(ai.get(tahap), dict):
                ai[tahap] = offline[tahap]
    return _result(offline, ai, error, client, "Pengalaman belajar berhasil dibuat dengan AI. Pastikan prinsip dan bukti benar-benar tampak.")


def generate_asesmen(client: OllamaClient | None, p: dict, desain: dict,
                     use_ai: bool = True, rpm_id: int | None = None) -> GenResult:
    offline = offline_asesmen(p, desain)
    if not use_ai or not client:
        return GenResult(data=offline, mode="offline", message="Draf asesmen disusun tanpa AI. Silakan periksa dan edit.")
    context = _context_pembelajaran(p)
    context["desain"] = desain
    ai, error, _ = _run_ai(client, prompts.prompt_asesmen(context), "asesmen", rpm_id)
    if ai:
        for jenis in ("awal", "proses", "akhir"):
            if isinstance(ai.get(jenis), dict):
                ai[jenis]["soal"] = _list_of_strings(ai[jenis].get("soal"), offline[jenis]["soal"])
                ai[jenis]["kunci"] = _list_of_strings(ai[jenis].get("kunci"), offline[jenis]["kunci"])
                ai[jenis]["rubrik"] = _list_of_dicts(
                    ai[jenis].get("rubrik"), ["kriteria", "deskripsi"], offline[jenis]["rubrik"]
                )
            else:
                ai[jenis] = offline[jenis]
    return _result(offline, ai, error, client, "Asesmen berhasil dibuat dengan AI. Verifikasi kunci jawaban dengan sumber belajar.")


def generate_diferensiasi(client: OllamaClient | None, p: dict, desain: dict, pengalaman: dict,
                          use_ai: bool = True, rpm_id: int | None = None) -> GenResult:
    offline = offline_diferensiasi(p, desain, pengalaman)
    if not use_ai or not client:
        return GenResult(data=offline, mode="offline", message="Draf diferensiasi disusun tanpa AI. Silakan periksa dan edit.")
    context = _context_pembelajaran(p)
    context["desain"] = desain
    context["pengalaman"] = pengalaman
    ai, error, _ = _run_ai(client, prompts.prompt_diferensiasi(context), "diferensiasi", rpm_id)
    if ai:
        ai["tingkat"] = _list_of_dicts(
            ai.get("tingkat"),
            ["tingkat", "kesiapan", "kompleksitas", "scaffolding", "sumber", "pengelompokan", "produk"],
            offline["tingkat"],
        )
    return _result(offline, ai, error, client, "Diferensiasi berhasil dibuat dengan AI. Sesuaikan dengan kondisi kelas.")


def generate_lkpd(client: OllamaClient | None, p: dict, desain: dict, pengalaman: dict,
                  use_ai: bool = True, rpm_id: int | None = None) -> GenResult:
    offline = offline_lkpd(p, desain, pengalaman)
    if not use_ai or not client:
        return GenResult(data=offline, mode="offline", message="Draf LKPD disusun tanpa AI. Silakan periksa dan edit.")
    context = _context_pembelajaran(p)
    context["desain"] = desain
    context["pengalaman"] = pengalaman
    ai, error, _ = _run_ai(client, prompts.prompt_lkpd(context), "lkpd", rpm_id)
    if ai:
        ai["pertanyaan"] = _list_of_strings(ai.get("pertanyaan"), offline["pertanyaan"])
    return _result(offline, ai, error, client, "LKPD berhasil dibuat dengan AI. Periksa keterbacaan dan kesesuaian dengan siswa.")


def generate_refleksi(client: OllamaClient | None, p: dict, desain: dict,
                      use_ai: bool = True, rpm_id: int | None = None) -> GenResult:
    offline = offline_refleksi(p, desain)
    if not use_ai or not client:
        return GenResult(data=offline, mode="offline", message="Draf refleksi disusun tanpa AI. Silakan periksa dan edit.")
    context = _context_pembelajaran(p)
    context["desain"] = desain
    ai, error, _ = _run_ai(client, prompts.prompt_refleksi(context), "refleksi", rpm_id)
    if ai:
        ai["siswa"] = _list_of_strings(ai.get("siswa"), offline["siswa"])
        ai["guru"] = _list_of_strings(ai.get("guru"), offline["guru"])
    return _result(offline, ai, error, client, "Refleksi berhasil dibuat dengan AI. Silakan sesuaikan dengan kebutuhan.")


def run_prompt_ai(client: OllamaClient, messages: list[dict], tahap: str, rpm_id: int | None):
    return _run_ai(client, messages, tahap, rpm_id)


def rekomendasi_model_ai(client: OllamaClient | None, p: dict, rpm_id: int | None = None) -> tuple[list[dict], str]:
    """Rekomendasi model; fallback ke aturan lokal."""
    lokal = [{"nama": rekomendasi_model(p), "alasan": "Dipilih berdasarkan kata kunci materi dan tujuan.", "kesesuaian": "tinggi"}]
    if not client:
        return lokal, ""
    try:
        data, error, _ = _run_ai(client, prompts.prompt_rekomendasi_model(_context_pembelajaran(p)), "rekomendasi_model", rpm_id)
    except Exception as exc:  # pragma: no cover - pengaman tambahan
        return lokal, str(exc)
    if not data:
        return lokal, error
    rows = _list_of_dicts(data.get("rekomendasi"), ["nama", "alasan", "kesesuaian"])
    return rows or lokal, ""


# ---------------------------------------------------------------------------
# Pemeriksaan AI opsional untuk validasi
# ---------------------------------------------------------------------------
def validasi_ai(client: OllamaClient | None, p: dict, data: dict,
                rpm_id: int | None = None) -> tuple[dict | None, str]:
    if not client:
        return None, "Ollama tidak aktif."
    context = {"pembelajaran": _context_pembelajaran(p), "rpm": data}
    parsed, error, _ = _run_ai(client, prompts.prompt_validasi(context), "validasi", rpm_id)
    return parsed, error
