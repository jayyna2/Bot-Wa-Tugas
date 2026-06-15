# 🤖 WhatsApp Chatbot Pengingat Tugas Kuliah

Chatbot berbasis Python + SQLite untuk mengelola dan mengingatkan tugas-tugas kuliah via WhatsApp.

---

## 📂 Struktur Project

```
Project Bot Tugas/
├── bot.py              # Logika chatbot (parsing, state management, formatter)
├── database.py         # Modul database SQLite (operasi CRUD)
├── wa_bot.py           # Integrasi WhatsApp via Neonize
├── tugas_bot.db        # File database (dibuat otomatis saat run)
├── wa_session.sqlite3  # Session WhatsApp (dibuat otomatis saat scan QR)
└── README.md           # Dokumentasi ini
```

## 🚀 Cara Menjalankan

### Mode Terminal (Testing)
```bash
python bot.py
```
Simulasi chat interaktif di terminal — cocok untuk testing sebelum colok ke WhatsApp.

### Mode WhatsApp (Live)
```bash
pip install neonize
python wa_bot.py
```
1. Scan QR Code yang muncul di terminal
2. Bot langsung aktif dan bisa menerima perintah via WhatsApp!

## 📋 Daftar Perintah

| Perintah | Fungsi |
|---|---|
| `!tambah` | Tambah tugas baru (bot tanya satu per satu) |
| `!list` | Lihat tugas yang belum selesai |
| `!kelar [ID]` | Tandai tugas selesai (contoh: `!kelar 3`) |
| `!semua` | Lihat semua tugas (termasuk selesai) |
| `!batal` | Batalkan proses tambah tugas |
| `!help` | Tampilkan panduan |
| `!keluar` | Keluar program (khusus mode terminal) |

## 💬 Contoh Percakapan

```
Kamu  > !tambah
Bot   > 📚 Langkah 1/3 — Masukkan nama mata kuliah:
Kamu  > Kalkulus
Bot   > ✅ Mata Kuliah: Kalkulus
        📝 Langkah 2/3 — Masukkan deskripsi/detail tugas:
Kamu  > Latihan Bab 5
Bot   > ✅ Deskripsi: Latihan Bab 5
        ⏰ Langkah 3/3 — Masukkan deadline:
Kamu  > 20 Juni 2026
Bot   > ✅ Tugas berhasil ditambahkan! (ID: 1)
```

## 📝 Catatan
- Database `tugas_bot.db` dibuat otomatis saat program pertama kali jalan
- Mode terminal **tidak butuh** install library tambahan (hanya library bawaan Python)
- Mode WhatsApp butuh `pip install neonize`
- Kode dilengkapi komentar penjelasan lengkap untuk presentasi
- ⚠️ Gunakan nomor WA **khusus bot**, jangan nomor utama
