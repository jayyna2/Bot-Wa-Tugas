"""
===========================================================
  FILE: bot.py
  Deskripsi: File utama Chatbot Pengingat Tugas Kuliah.
             Berisi logika parsing perintah chat dan
             simulasi interaksi via terminal.

  Perintah yang didukung:
    !tambah   → Bot akan tanya satu-satu (Matkul, Deskripsi, Deadline)
    !list     → Lihat tugas yang belum selesai
    !kelar [ID] → Tandai tugas selesai
    !help     → Panduan penggunaan
    !semua    → Lihat semua tugas (termasuk selesai)
    !batal    → Batalkan proses tambah tugas
    !keluar   → Keluar (khusus terminal)
===========================================================
"""

# =========================================================
import sys
import os

if sys.platform == "win32":
    # Aktifkan mode UTF-8 di Windows console
    os.system("")  # Enable ANSI/VT100 escape sequences
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

def load_env():
    """Membaca file .env jika ada dan memasukkannya ke os.environ secara manual."""
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    parts = line.split("=", 1)
                    if len(parts) == 2:
                        key, val = parts[0].strip(), parts[1].strip()
                        if val.startswith('"') and val.endswith('"'):
                            val = val[1:-1]
                        elif val.startswith("'") and val.endswith("'"):
                            val = val[1:-1]
                        os.environ[key] = val

load_env()

from database import init_db, tambah_tugas, get_tugas_belum_selesai, selesaikan_tugas, get_semua_tugas


# =========================================================
# STATE MANAGEMENT — PERCAKAPAN INTERAKTIF
# =========================================================
# Untuk fitur !tambah yang interaktif (tanya satu-satu),
# kita perlu menyimpan "state" setiap user. Dictionary ini
# menyimpan posisi user dalam alur percakapan.
#
# Struktur:
#   sesi_tambah[user_id] = {
#       "step": "matkul" | "deskripsi" | "deadline",
#       "matkul": "...",       # diisi setelah step matkul
#       "deskripsi": "...",    # diisi setelah step deskripsi
#   }
#
# Alur percakapan !tambah:
#   User: !tambah
#   Bot:  Masukkan nama mata kuliah?
#   User: Kalkulus
#   Bot:  Masukkan deskripsi tugas?
#   User: Latihan Bab 5
#   Bot:  Masukkan deadline?
#   User: 20 Juni 2026
#   Bot:  ✅ Tugas berhasil ditambahkan!

sesi_tambah = {}


# =========================================================
# FORMATTER TABEL MONOSPACE WHATSAPP
# =========================================================
# WhatsApp mendukung format monospace (font fixed-width)
# dengan mengapit teks menggunakan tiga backtick (```).
# Kita manfaatkan ini agar tabel terlihat lurus dan rapi
# di layar HP pengguna.

def format_tabel_tugas(data_tugas: list) -> str:
    """
    Memformat daftar tugas menjadi tabel teks monospace
    yang kompatibel dengan WhatsApp.

    Parameters:
        data_tugas (list): List of tuples (id, matkul, deskripsi, deadline)

    Returns:
        str: Tabel yang sudah diformat dalam monospace WhatsApp

    Algoritma Dynamic Padding:
        1. Tentukan lebar minimum setiap kolom dari header
        2. Bandingkan dengan lebar data terpanjang di tiap kolom
        3. Ambil nilai maksimum → ini jadi lebar kolom final
        4. Gunakan str.ljust() untuk padding spasi otomatis
    """

    # Jika tidak ada tugas, kembalikan pesan info
    if not data_tugas:
        return "📭 *Tidak ada tugas yang pending.* Semua beres! 🎉"

    # --- LANGKAH 1: Definisikan header kolom ---
    headers = ["ID", "Mata Kuliah", "Tugas", "DL"]

    # --- LANGKAH 2: Hitung lebar dinamis tiap kolom ---
    # Mulai dari lebar header sebagai nilai minimum
    col_widths = [len(h) for h in headers]

    for row in data_tugas:
        # row = (id, matkul, deskripsi, deadline)
        col_widths[0] = max(col_widths[0], len(str(row[0])))      # ID
        col_widths[1] = max(col_widths[1], len(str(row[1])))      # Matkul
        col_widths[2] = max(col_widths[2], len(str(row[2])))      # Tugas
        col_widths[3] = max(col_widths[3], len(str(row[3])))      # Deadline

    # Tambahkan padding ekstra 2 spasi agar tabel lebih lebar dan mudah dibaca
    col_widths = [w + 2 for w in col_widths]

    # --- LANGKAH 3: Bangun baris-baris tabel ---
    # Fungsi helper untuk membuat satu baris tabel
    def buat_baris(values):
        """Membuat satu baris tabel dengan padding dinamis."""
        cells = []
        for i, val in enumerate(values):
            # ljust() menambahkan spasi di kanan agar lebar = col_widths[i]
            cells.append(str(val).ljust(col_widths[i]))
        return " | ".join(cells)

    # Bangun header
    header_line = buat_baris(headers)

    # Bangun garis pemisah (separator) menggunakan karakter '-'
    separator = "-+-".join("-" * w for w in col_widths)

    # Bangun baris data
    data_lines = [buat_baris(row) for row in data_tugas]

    # --- LANGKAH 4: Gabungkan semua dan bungkus dengan ``` ---
    tabel = "\n".join([header_line, separator, *data_lines])

    # Bungkus dengan backtick tiga (format monospace WhatsApp)
    return f"📋 *Daftar Tugas Pending:*\n\n```\n{tabel}\n```"


# =========================================================
# HANDLER PERINTAH CHAT
# =========================================================

def handle_tambah_mulai(user_id: str) -> str:
    """
    Menangani perintah: !tambah (LANGKAH 1)

    Memulai sesi interaktif untuk menambah tugas.
    Bot akan menanyakan data satu per satu:
      Step 1: Nama Mata Kuliah
      Step 2: Deskripsi Tugas
      Step 3: Deadline

    User bisa membatalkan kapan saja dengan !batal.
    """
    # Buat sesi baru untuk user ini, mulai dari step "matkul"
    sesi_tambah[user_id] = {"step": "matkul"}

    return (
        "📝 *Tambah Tugas Baru*\n\n"
        "Silakan jawab pertanyaan berikut satu per satu.\n"
        "Ketik `!batal` kapan saja untuk membatalkan.\n\n"
        "📚 *Langkah 1/3* — Masukkan *nama mata kuliah*:"
    )


def handle_tambah_step(user_id: str, pesan: str) -> str:
    """
    Melanjutkan sesi interaktif !tambah berdasarkan step saat ini.

    Alur:
        step "matkul"    → simpan matkul, tanya deskripsi
        step "deskripsi" → simpan deskripsi, tanya deadline
        step "deadline"  → simpan deadline, masukkan ke database, selesai

    Parameters:
        user_id (str): ID unik pengguna (nomor WA atau "terminal")
        pesan   (str): Jawaban user untuk step saat ini

    Returns:
        str: Balasan bot (pertanyaan selanjutnya / konfirmasi)
    """
    sesi = sesi_tambah[user_id]
    step = sesi["step"]

    # Validasi: jawaban tidak boleh kosong
    if not pesan.strip():
        return "⚠️ *Tidak boleh kosong!* Silakan masukkan data yang diminta."

    # --------------------------------------------------
    # STEP 1: Menerima nama mata kuliah, lanjut ke deskripsi
    # --------------------------------------------------
    if step == "matkul":
        sesi["matkul"] = pesan.strip().title()  # "basis data" → "Basis Data"
        sesi["step"] = "deskripsi"
        return (
            f"✅ Mata Kuliah: *{pesan.strip().title()}*\n\n"
            "📝 *Langkah 2/3* — Masukkan *deskripsi/detail tugas*:"
        )

    # --------------------------------------------------
    # STEP 2: Menerima deskripsi tugas, lanjut ke deadline
    # --------------------------------------------------
    elif step == "deskripsi":
        sesi["deskripsi"] = pesan.strip().capitalize()  # "latihan bab 5" → "Latihan bab 5"
        sesi["step"] = "deadline"
        return (
            f"✅ Deskripsi: *{pesan.strip().capitalize()}*\n\n"
            "⏰ *Langkah 3/3* — Masukkan *deadline* (contoh: 20 Juni 2026):"
        )

    # --------------------------------------------------
    # STEP 3: Menerima deadline, simpan ke database
    # --------------------------------------------------
    elif step == "deadline":
        deadline = pesan.strip().capitalize()  # "20 juni 2026" → "20 juni 2026" (angka tetap)
        matkul = sesi["matkul"]
        deskripsi = sesi["deskripsi"]

        # Simpan ke database
        new_id = tambah_tugas(matkul, deskripsi, deadline)

        # Hapus sesi karena sudah selesai
        del sesi_tambah[user_id]

        return (
            f"✅ *Tugas berhasil ditambahkan!*\n\n"
            f"📌 ID       : {new_id}\n"
            f"📚 Matkul   : {matkul}\n"
            f"📝 Tugas    : {deskripsi}\n"
            f"⏰ Deadline : {deadline}\n"
            f"📊 Status   : Belum Selesai"
        )


def handle_batal(user_id: str) -> str:
    """
    Menangani perintah: !batal

    Membatalkan sesi !tambah yang sedang berlangsung.
    Jika tidak ada sesi aktif, beri tahu user.
    """
    if user_id in sesi_tambah:
        del sesi_tambah[user_id]
        return "❌ *Proses tambah tugas dibatalkan.*"
    else:
        return "ℹ️ Tidak ada proses yang sedang berjalan."


def handle_list() -> str:
    """
    Menangani perintah: !list

    Mengambil semua tugas yang belum selesai dari database,
    lalu memformatnya menjadi tabel monospace WhatsApp.
    """
    data = get_tugas_belum_selesai()
    return format_tabel_tugas(data)


def handle_kelar(pesan: str) -> str:
    """
    Menangani perintah: !kelar [ID]

    Proses:
        1. Ekstrak ID dari pesan
        2. Validasi bahwa ID adalah angka
        3. Update status di database
        4. Kembalikan hasil (berhasil / ID tidak ditemukan)

    Contoh:
        "!kelar 3" → Menandai tugas ID=3 sebagai Selesai
    """

    # Ambil bagian setelah "!kelar "
    konten = pesan[len("!kelar"):].strip()

    # Validasi: cek apakah ada ID
    if not konten:
        return (
            "⚠️ *ID tugas tidak boleh kosong!*\n\n"
            "Gunakan format: `!kelar [ID]`\n"
            "Contoh: `!kelar 3`"
        )

    # Validasi: cek apakah ID adalah angka
    if not konten.isdigit():
        return (
            f"⚠️ *'{konten}' bukan ID yang valid!*\n\n"
            "ID harus berupa angka.\n"
            "Cek ID tugas dengan perintah `!list`"
        )

    tugas_id = int(konten)

    # Coba hapus di database karena sudah selesai
    berhasil = selesaikan_tugas(tugas_id)

    if berhasil:
        return f"🎉 *Tugas ID {tugas_id} sudah ditandai SELESAI dan dihapus otomatis!* Good job! 💪"
    else:
        return (
            f"❌ *Tugas dengan ID {tugas_id} tidak ditemukan*.\n\n"
            "Cek daftar tugas pending dengan `!list`"
        )


def handle_semua() -> str:
    """
    Menangani perintah: !semua

    Menampilkan SEMUA tugas (termasuk yang sudah selesai).
    Berguna untuk melihat riwayat lengkap.
    """
    data = get_semua_tugas()

    if not data:
        return "📭 *Database masih kosong.* Belum ada tugas yang ditambahkan."

    headers = ["ID", "Mata Kuliah", "Tugas", "DL", "Status"]
    col_widths = [len(h) for h in headers]

    for row in data:
        for i in range(5):
            col_widths[i] = max(col_widths[i], len(str(row[i])))

    def buat_baris(values):
        cells = [str(val).ljust(col_widths[i]) for i, val in enumerate(values)]
        return " | ".join(cells)

    header_line = buat_baris(headers)
    separator = "-+-".join("-" * w for w in col_widths)
    data_lines = [buat_baris(row) for row in data]
    tabel = "\n".join([header_line, separator, *data_lines])

    return f"📋 *Semua Tugas (Riwayat Lengkap):*\n\n```\n{tabel}\n```"


def handle_help() -> str:
    """
    Menangani perintah: !help

    Menampilkan panduan lengkap penggunaan bot.
    """
    return (
        "🤖 *Panduan Bot Pengingat Tugas Kuliah*\n\n"
        "Berikut daftar perintah yang tersedia:\n\n"
        "1️⃣ *Tambah Tugas Baru*\n"
        "   `!tambah`\n"
        "   Bot akan menanyakan data satu per satu.\n\n"
        "2️⃣ *Lihat Tugas Pending*\n"
        "   `!list`\n"
        "   Menampilkan semua tugas yang belum selesai.\n\n"
        "3️⃣ *Tandai Tugas Selesai*\n"
        "   `!kelar [ID]`\n"
        "   Contoh: `!kelar 3` (tugas akan dihapus otomatis)\n\n"
        "4️⃣ *Lihat Semua Tugas*\n"
        "   `!semua`\n"
        "   Menampilkan semua tugas termasuk yang sudah selesai.\n\n"
        "5️⃣ *Batalkan Proses*\n"
        "   `!batal`\n"
        "   Membatalkan proses tambah tugas yang sedang berjalan.\n\n"
        "6️⃣ *Metode Pembayaran*\n"
        "   `!bayar` atau `!dana`\n"
        "   Menampilkan QR Code DANA untuk pembayaran.\n\n"
        "7️⃣ *Bantuan*\n"
        "   `!help`\n"
        "   Menampilkan pesan bantuan ini."
    )


def crc16_ccitt(data: str) -> str:
    """Menghitung CRC-16/CCITT-FALSE untuk standar QRIS (EMVCo)."""
    crc = 0xFFFF
    for byte in data.encode('ascii'):
        crc ^= (byte << 8)
        for _ in range(8):
            if crc & 0x8000:
                crc = (crc << 1) ^ 0x1021
            else:
                crc = crc << 1
            crc &= 0xFFFF
    return f"{crc:04X}"


def make_qris_dynamic(static_qris: str, amount: int) -> str:
    """Mengubah string QRIS statis menjadi dinamis dengan nominal tertentu."""
    import re
    qris = static_qris.strip()
    
    # Hapus CRC lama di akhir jika ada (6304 + 4 karakter hex CRC)
    if not qris.endswith("6304"):
        idx_63 = qris.rfind("6304")
        if idx_63 != -1:
            qris = qris[:idx_63 + 4]
            
    # Format tag 54 (Amount): "54" + 2 digit panjang nominal + nominal
    amount_str = str(amount)
    tag_54 = f"54{len(amount_str):02d}{amount_str}"
    
    # Cari tag 58 (Country Code "5802ID") untuk menyisipkan tag 54 sebelumnya
    idx_58 = qris.find("5802ID")
    if idx_58 != -1:
        before_58 = qris[:idx_58]
        # Cari jika tag 54 sudah ada sebelumnya untuk di-replace
        match = re.search(r"54(\d{2})(\d+)", before_58)
        if match:
            length = int(match.group(1))
            val = match.group(2)
            if len(val) >= length:
                val = val[:length]
                old_tag = f"54{length:02d}{val}"
                qris = qris.replace(old_tag, tag_54)
        else:
            # Jika belum ada, sisipkan sebelum tag 58
            qris = qris[:idx_58] + tag_54 + qris[idx_58:]
            
    # Hitung CRC16 baru
    crc = crc16_ccitt(qris)
    return qris + crc


def create_midtrans_payment(amount: int) -> tuple[str, str]:
    """
    Membuat transaksi di Midtrans Snap dan mengembalikan (redirect_url, order_id).
    """
    import requests
    import base64
    import time
    import random
    
    server_key = os.environ.get("MIDTRANS_SERVER_KEY", "").strip()
    is_prod = os.environ.get("MIDTRANS_IS_PRODUCTION", "false").strip().lower() == "true"
    
    if not server_key:
        raise ValueError("MIDTRANS_SERVER_KEY tidak dikonfigurasi.")
        
    url = (
        "https://app.midtrans.com/snap/v1/transactions"
        if is_prod
        else "https://app.sandbox.midtrans.com/snap/v1/transactions"
    )
    
    # Encode Server Key ke Base64 (ditambah ':' sesuai spec Midtrans)
    auth_str = f"{server_key}:"
    auth_base64 = base64.b64encode(auth_str.encode("utf-8")).decode("utf-8")
    
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": f"Basic {auth_base64}"
    }
    
    order_id = f"TUGAS-BOT-{int(time.time())}-{random.randint(1000, 9999)}"
    
    payload = {
        "transaction_details": {
            "order_id": order_id,
            "gross_amount": amount
        },
        "credit_card": {
            "secure": True
        }
    }
    
    response = requests.post(url, json=payload, headers=headers, timeout=10)
    if response.status_code == 201:
        data = response.json()
        return data["redirect_url"], order_id
    else:
        raise Exception(f"Midtrans API Error: {response.status_code} - {response.text}")


def handle_bayar(pesan: str) -> str:
    """
    Menangani perintah: !bayar [nominal] atau !dana [nominal]

    Mengembalikan QR Code beserta detail informasi untuk menyelesaikan pembayaran.
    """
    import re
    import os
    
    # Ambil bagian nominal dari pesan (misal "!bayar 10000" -> 10000)
    parts = pesan.strip().split()
    nominal = None
    if len(parts) > 1:
        # Hapus semua karakter non-angka seperti Rp, titik, koma
        num_str = re.sub(r"\D", "", parts[1])
        if num_str.isdigit():
            nominal = int(num_str)
            
    # Format nominal ke mata uang Rupiah untuk tampilan caption
    nominal_text = f"Rp {nominal:,.0f}".replace(",", ".") if nominal else "Sukarela"
    
    # --- PILIHAN 1: Midtrans Payment Gateway ---
    midtrans_key = os.environ.get("MIDTRANS_SERVER_KEY")
    if midtrans_key and nominal:
        try:
            redirect_url, order_id = create_midtrans_payment(nominal)
            qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=300x300&data={redirect_url}"
            caption = (
                f"💸 *INVOICE PEMBAYARAN ELEKTRONIK* 💸\n\n"
                f"Sistem telah membuat invoice pembayaran baru:\n"
                f"📝 *Order ID:* `{order_id}`\n"
                f"💰 *Nominal:* *{nominal_text}*\n\n"
                f"Silakan scan QR Code di atas atau selesaikan pembayaran lewat link berikut:\n"
                f"🔗 {redirect_url}\n\n"
                f"Mendukung pembayaran via QRIS, GoPay, ShopeePay, Bank Virtual Account (BCA, Mandiri, BNI, BRI), Credit Card, dll. 🙏"
            )
            return f"[IMAGE]{qr_url}|{caption}"
        except Exception as e:
            return f"❌ *Gagal membuat Invoice Midtrans:*\n`{e}`\n\nSilakan periksa kembali apakah Server Key kamu sudah benar dan sesuai (Sandbox / Production)."

    # --- PILIHAN 2: Link Pembayaran Kustom (Saweria / Sociabuzz / Trakteer) ---
    custom_link = os.environ.get("PAYMENT_LINK")
    if custom_link:
        # Jika ada nominal, coba tambahkan info nominal ke link jika didukung (opsional)
        qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=300x300&data={custom_link}"
        caption = (
            f"💸 *LINK PEMBAYARAN KUSTOM* 💸\n\n"
            f"Silakan scan QR Code di atas atau kunjungi link berikut untuk melakukan pembayaran:\n"
            f"🔗 {custom_link}\n\n"
            f"💰 *Nominal:* *{nominal_text}*\n\n"
            f"Terima kasih atas dukungannya! 🙏"
        )
        return f"[IMAGE]{qr_url}|{caption}"

    # --- PILIHAN 3: Dynamic QRIS (jika STATIC_QRIS di-set) ---
    static_qris = os.environ.get("STATIC_QRIS")
    if static_qris and nominal:
        try:
            dynamic_qris_str = make_qris_dynamic(static_qris, nominal)
            qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=300x300&data={dynamic_qris_str}"
            caption = (
                f"💸 *METODE PEMBAYARAN QRIS* 💸\n\n"
                f"Silakan scan QRIS di atas untuk membayar otomatis:\n"
                f"💰 *Nominal:* *{nominal_text}*\n\n"
                f"Bisa di-scan menggunakan DANA, OVO, GoPay, ShopeePay, LinkAja, atau Mobile Banking apa saja! 🙏"
            )
            return f"[IMAGE]{qr_url}|{caption}"
        except Exception as err_qris:
            print(f"⚠️ Gagal generate QRIS dinamis: {err_qris}", flush=True)

    # --- PILIHAN 4: Fallback Default (DANA Personal) ---
    qr_data = "https://link.dana.id/qr/085841532954"
    qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=300x300&data={qr_data}"
    
    caption = (
        f"💸 *METODE PEMBAYARAN DANA* 💸\n\n"
        f"Silakan scan QR Code DANA di atas atau klik link berikut untuk membayar:\n"
        f"🔗 https://link.dana.id/qr/085841532954\n\n"
        f"📞 *No. HP DANA:* `085841532954`\n"
        f"💰 *Nominal:* *{nominal_text}*\n\n"
        f"Setelah melakukan transfer, silakan konfirmasi ke admin. Terima kasih! 🙏"
    )
    return f"[IMAGE]{qr_url}|{caption}"


# =========================================================
# ROUTER PERINTAH (COMMAND DISPATCHER)
# =========================================================
# Fungsi ini adalah "otak" utama bot. Ia menerima pesan
# mentah + user_id, lalu menentukan apakah user sedang
# dalam sesi interaktif atau mengirim perintah baru.

def proses_pesan(pesan: str, user_id: str = "terminal") -> str:
    """
    Menerima pesan chat mentah dan mengembalikan balasan bot.

    ALUR UTAMA:
        1. Cek apakah pesan adalah perintah !batal
        2. Cek apakah user sedang dalam sesi interaktif !tambah
           → Jika ya, teruskan jawaban ke handler step
        3. Jika tidak dalam sesi, cocokkan prefix perintah
        4. Panggil handler yang sesuai

    Parameters:
        pesan   (str): String pesan mentah dari chat
        user_id (str): ID unik pengguna. Di WhatsApp ini adalah
                       nomor telepon (JID). Di terminal, default "terminal".

    Returns:
        str: String balasan dari bot
    """

    pesan = pesan.strip()

    # Jika pesan kosong, abaikan
    if not pesan:
        return ""

    # Normalisasi: hapus spasi berlebih setelah tanda '!'
    # Agar "! help", "!  tambah", "! kelar 3" tetap dikenali
    if pesan.startswith("!"):
        # Hapus '!', strip spasi, lalu tambahkan '!' kembali
        pesan = "!" + pesan[1:].lstrip()

    pesan_lower = pesan.lower()

    # --- Prioritas 1: Perintah !batal (bisa dipanggil kapan saja) ---
    if pesan_lower == "!batal":
        return handle_batal(user_id)

    # --- Prioritas 2: Cek apakah user sedang dalam sesi !tambah ---
    # Jika user sedang mengisi data step-by-step, semua pesan
    # (kecuali !batal) dianggap sebagai jawaban untuk step tsb.
    if user_id in sesi_tambah:
        # Cek jika user mengetik perintah lain di tengah sesi
        if pesan_lower.startswith("!"):
            return (
                "⚠️ *Kamu sedang dalam proses tambah tugas.*\n\n"
                "Silakan selesaikan dulu atau ketik `!batal` untuk membatalkan."
            )
        return handle_tambah_step(user_id, pesan)

    # --- Prioritas 3: Routing perintah normal ---
    if pesan_lower == "!tambah" or pesan_lower.startswith("!tambah "):
        return handle_tambah_mulai(user_id)

    elif pesan_lower == "!list":
        return handle_list()

    elif pesan_lower.startswith("!kelar"):
        return handle_kelar(pesan)

    elif pesan_lower == "!semua":
        return handle_semua()

    elif pesan_lower == "!help":
        return handle_help()

    elif pesan_lower.startswith("!bayar") or pesan_lower.startswith("!dana") or pesan_lower.startswith("!qr"):
        return handle_bayar(pesan)

    else:
        # Perintah tidak dikenali
        return (
            "🤔 *Perintah tidak dikenali.*\n\n"
            "Ketik `!help` untuk melihat daftar perintah yang tersedia."
        )


# =========================================================
# SIMULASI TERMINAL (MODE TESTING)
# =========================================================
# Blok ini hanya berjalan jika file dieksekusi langsung
# (bukan di-import sebagai modul). Berguna untuk testing
# logika bot sebelum diintegrasikan ke WhatsApp.

if __name__ == "__main__":
    print("=" * 55)
    print("  🤖 CHATBOT PENGINGAT TUGAS KULIAH — MODE TERMINAL")
    print("=" * 55)
    print()

    # Inisialisasi database (buat tabel jika belum ada)
    init_db()

    print()
    print("Ketik perintah bot seperti di WhatsApp.")
    print("Ketik !help untuk melihat panduan.")
    print("Ketik !keluar untuk keluar dari program.")
    print("-" * 55)
    print()

    # Loop utama simulasi terminal
    # user_id = "terminal" karena di terminal hanya ada 1 user
    while True:
        try:
            # Menerima input dari user (simulasi chat masuk)
            pesan = input("📱 Kamu > ")
        except (EOFError, KeyboardInterrupt):
            # Handle Ctrl+C atau Ctrl+D dengan graceful
            print("\n\n👋 Sampai jumpa! Semangat ngerjain tugasnya! 💪")
            break

        # Cek perintah keluar (khusus mode terminal)
        if pesan.strip().lower() == "!keluar":
            print("\n👋 Sampai jumpa! Semangat ngerjain tugasnya! 💪")
            break

        # Proses pesan dan tampilkan balasan
        # user_id "terminal" digunakan untuk state management
        balasan = proses_pesan(pesan, user_id="terminal")

        if balasan:  # Hanya tampilkan jika ada balasan
            print(f"\n🤖 Bot > {balasan}\n")
