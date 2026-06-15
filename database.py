"""
===========================================================
  MODULE: database.py
  Deskripsi: Modul ini menangani semua operasi database
             SQLite untuk Chatbot Pengingat Tugas Kuliah.
  Database : tugas_bot.db
  Tabel    : tugas (id, matkul, deskripsi, deadline, status)
===========================================================
"""

import sqlite3
import os

# =========================================================
# KONFIGURASI DATABASE
# =========================================================
# Nama file database SQLite. File ini akan dibuat otomatis
# di direktori yang sama dengan script ini.
DB_NAME = "tugas_bot.db"

def get_db_path():
    """
    Mengembalikan path absolut ke file database.
    Ini memastikan database selalu dibuat di folder yang sama
    dengan file script ini, bukan di folder kerja terminal.
    """
    base_dir = os.environ.get("DATA_DIR", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_dir, DB_NAME)


def get_connection():
    """
    Membuat dan mengembalikan koneksi ke database SQLite.
    Menggunakan context manager (with statement) di pemanggil
    untuk memastikan koneksi ditutup dengan benar.
    """
    return sqlite3.connect(get_db_path())


# =========================================================
# INISIALISASI DATABASE
# =========================================================
def init_db():
    """
    Membuat tabel 'tugas' jika belum ada di database.
    Fungsi ini WAJIB dipanggil sekali saat program pertama
    kali dijalankan.

    Struktur Tabel:
    ┌────────────┬──────────┬──────────────────────────────┐
    │ Kolom      │ Tipe     │ Keterangan                   │
    ├────────────┼──────────┼──────────────────────────────┤
    │ id         │ INTEGER  │ Primary Key, Auto Increment  │
    │ matkul     │ TEXT     │ Nama mata kuliah              │
    │ deskripsi  │ TEXT     │ Detail/deskripsi tugas       │
    │ deadline   │ TEXT     │ Tenggat waktu pengumpulan    │
    │ status     │ TEXT     │ Default: 'Belum Selesai'     │
    └────────────┴──────────┴──────────────────────────────┘
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tugas (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                matkul      TEXT    NOT NULL,
                deskripsi   TEXT    NOT NULL,
                deadline    TEXT    NOT NULL,
                status      TEXT    NOT NULL DEFAULT 'Belum Selesai'
            )
        """)
        conn.commit()
    print("[DB] ✅ Database dan tabel 'tugas' siap digunakan.")


# =========================================================
# OPERASI CRUD (Create, Read, Update, Delete)
# =========================================================

def tambah_tugas(matkul: str, deskripsi: str, deadline: str) -> int:
    """
    Menambahkan tugas baru ke database.

    Parameters:
        matkul    (str): Nama mata kuliah
        deskripsi (str): Detail tugas
        deadline  (str): Tenggat waktu

    Returns:
        int: ID dari tugas yang baru ditambahkan

    Catatan:
        Menggunakan parameterized query (tanda ?) untuk
        mencegah SQL Injection — ini best practice keamanan.
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO tugas (matkul, deskripsi, deadline) VALUES (?, ?, ?)",
            (matkul.strip(), deskripsi.strip(), deadline.strip())
        )
        conn.commit()
        return cursor.lastrowid  # Mengembalikan ID record baru


def get_tugas_belum_selesai() -> list:
    """
    Mengambil semua tugas yang statusnya masih 'Belum Selesai'.

    Returns:
        list: Daftar tuple berisi (id, matkul, deskripsi, deadline)
              Contoh: [(1, 'Kalkulus', 'Latihan Bab 5', '20 Juni 2026'), ...]
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, matkul, deskripsi, deadline FROM tugas WHERE status = ?",
            ("Belum Selesai",)
        )
        return cursor.fetchall()


def selesaikan_tugas(tugas_id: int) -> bool:
    """
    Menghapus tugas dari database berdasarkan ID karena sudah selesai.

    Parameters:
        tugas_id (int): ID tugas yang ingin diselesaikan/dihapus

    Returns:
        bool: True jika berhasil (ID ditemukan), False jika tidak
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM tugas WHERE id = ?",
            (tugas_id,)
        )
        conn.commit()
        return cursor.rowcount > 0  # True jika ada baris yang terhapus


def get_semua_tugas() -> list:
    """
    Mengambil SEMUA tugas dari database (termasuk yang sudah selesai).
    Berguna untuk keperluan debugging atau laporan lengkap.

    Returns:
        list: Daftar tuple berisi (id, matkul, deskripsi, deadline, status)
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, matkul, deskripsi, deadline, status FROM tugas")
        return cursor.fetchall()
