"""
===========================================================
  FILE: wa_bot.py
  Deskripsi: File integrasi WhatsApp menggunakan library
             Neonize (wrapper WhatsApp Web berbasis Go).

  Cara Pakai:
    1. Install neonize: pip install neonize
    2. Jalankan: python wa_bot.py
    3. Scan QR Code yang muncul di terminal dengan WA kamu
    4. Bot langsung aktif dan bisa menerima perintah!

  Catatan:
    - Scan QR hanya perlu dilakukan SEKALI. Session akan
      disimpan di file 'wa_session.sqlite3'.
    - Jika session expired, hapus file tersebut dan scan ulang.
    - Gunakan nomor WA khusus untuk bot, JANGAN nomor utama.
===========================================================
"""

import sys
import os

# =========================================================
# FIX ENCODING WINDOWS
# =========================================================
if sys.platform == "win32":
    os.system("")
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# =========================================================
# IMPORT LIBRARY
# =========================================================
try:
    from neonize.client import NewClient
    from neonize.events import ConnectedEv, MessageEv, PairStatusEv
    from neonize.utils import log
    import logging
except ImportError as err:
    print("=" * 55)
    print(f"  ❌ ERROR: Library 'neonize' gagal di-import!")
    print(f"  Detail Error: {err}")
    print("=" * 55)
    print()
    print("  Jalankan perintah berikut untuk install:")
    print("  pip install neonize")
    print()
    print("  Atau jika pakai virtual environment:")
    print("  python -m venv venv")
    print("  venv\\Scripts\\activate")
    print("  pip install neonize")
    print()
    sys.exit(1)

from database import init_db
from bot import proses_pesan


# =========================================================
# KONFIGURASI
# =========================================================

# File session SQLite untuk menyimpan login WhatsApp.
# Scan QR hanya perlu dilakukan sekali, session disimpan di sini.
data_dir = os.environ.get("DATA_DIR", os.path.dirname(os.path.abspath(__file__)))
os.makedirs(data_dir, exist_ok=True)
SESSION_DB = os.path.join(data_dir, "wa_session.sqlite3")

# Set log level ke ERROR agar terminal bersih dari warning
# history sync yang tidak penting. Ubah ke logging.DEBUG
# jika ingin melihat detail koneksi untuk debugging.
log.setLevel(logging.ERROR)


# =========================================================
# INISIALISASI CLIENT WHATSAPP
# =========================================================

# NewClient menerima path ke file database session.
# Jika file belum ada, akan dibuat otomatis saat pertama connect.
client = NewClient(SESSION_DB)

# Catat waktu bot dimulai. Pesan yang timestamp-nya SEBELUM
# waktu ini akan di-skip (pesan lama dari history sync).
import time
BOT_START_TIME = int(time.time())


# =========================================================
# EVENT HANDLERS
# =========================================================

@client.event(ConnectedEv)
def on_connected(_: NewClient, __: ConnectedEv):
    """
    Event: Berhasil terkoneksi ke WhatsApp.
    Dipanggil setiap kali client berhasil login/reconnect.
    """
    try:
        print()
        print("=" * 55)
        print("  ⚡ BOT BERHASIL TERKONEKSI KE WHATSAPP!")
        print("=" * 55)
        print()
        print("  Bot sudah aktif dan siap menerima perintah.")
        print("  Kirim !help ke nomor bot untuk panduan.")
        print()
        print("  Tekan Ctrl+C untuk menghentikan bot.")
        print("-" * 55)
    except Exception as e:
        print(f"❌ Error in on_connected: {e}", flush=True)


@client.event(PairStatusEv)
def on_pair_status(_: NewClient, pair: PairStatusEv):
    """
    Event: Status pairing (scan QR Code).
    Memberikan feedback saat proses scan QR selesai.
    """
    try:
        if pair and hasattr(pair, "ID"):
            print(f"  📱 Pairing status: {pair.ID}", flush=True)
        else:
            print(f"  📱 Pairing status update received", flush=True)
    except Exception as e:
        print(f"❌ Error in on_pair_status: {e}", flush=True)


@client.event(MessageEv)
def on_message(client: NewClient, message: MessageEv):
    """
    Event: Pesan masuk diterima.
    """
    try:
        # --- VALIDASI OBJEK PESAN ---
        if not message:
            return

        # Pengecekan apakah Metadata/Info tersedia
        if not hasattr(message, "Info") or not message.Info:
            return

        # Pengecekan apakah Source/Pengirim tersedia
        if not hasattr(message.Info, "MessageSource") or not message.Info.MessageSource:
            return

        # Pengecekan apakah isi pesan (Message) tersedia
        if not hasattr(message, "Message") or not message.Message:
            return

        # --- SKIP PESAN LAMA (HISTORY SYNC) ---
        # Saat bot connect, WhatsApp mengirim ulang pesan-pesan lama.
        # Kita hanya mau proses pesan yang masuk SETELAH bot start.
        msg_timestamp = message.Info.Timestamp
        if msg_timestamp < BOT_START_TIME:
            return  # Abaikan pesan lama

        # --- EKSTRAK TEKS PESAN ---
        msg_text = ""

        # Tipe 1: Pesan teks biasa (conversation)
        if hasattr(message.Message, "conversation") and message.Message.conversation:
            msg_text = message.Message.conversation

        # Tipe 2: Pesan reply/kutipan (extendedTextMessage)
        elif hasattr(message.Message, "extendedTextMessage") and message.Message.extendedTextMessage and hasattr(message.Message.extendedTextMessage, "text") and message.Message.extendedTextMessage.text:
            msg_text = message.Message.extendedTextMessage.text

        # Abaikan pesan kosong atau pesan non-teks (gambar, stiker, dll.)
        if not msg_text:
            return

        # --- AMBIL INFORMASI PENGIRIM ---
        chat_jid = message.Info.MessageSource.Chat
        sender_jid = message.Info.MessageSource.Sender
        if not sender_jid or not chat_jid:
            return

        user_id = str(sender_jid)

        # --- PERINTAH KHUSUS KELUAR/MATIKAN BOT ---
        if msg_text.strip().lower() == "!keluar":
            try:
                client.reply_message("👋 Bot dihentikan. Mematikan proses...", message)
            except Exception as e:
                print(f"❌ GAGAL kirim reply_message untuk keluar: {e}", flush=True)
                try:
                    client.send_message(chat_jid, "👋 Bot dihentikan. Mematikan proses...")
                except Exception:
                    pass
            print(f"🛑 Menerima perintah !keluar dari {user_id}. Mematikan bot...", flush=True)
            import os
            os._exit(0)

        # Cek apakah pesan dari diri sendiri
        # Izinkan jika: (1) perintah !, ATAU (2) user sedang di sesi !tambah
        # Block sisanya agar balasan bot tidak trigger loop
        if message.Info.MessageSource.IsFromMe:
            from bot import sesi_tambah
            is_command = msg_text.strip().startswith("!")
            in_session = user_id in sesi_tambah
            if not is_command and not in_session:
                return

        # Deteksi apakah pesan dari grup
        is_group = message.Info.MessageSource.IsGroup

        # --- LOG PESAN MASUK ---
        sender_name = message.Info.Pushname or "Unknown"
        label = "[GRUP]" if is_group else "[PERSONAL]"
        print(f"📨 {label} {sender_name} > {msg_text}", flush=True)

        # --- PROSES PESAN DAN KIRIM BALASAN ---
        balasan = proses_pesan(msg_text, user_id=user_id)

        if balasan:
            try:
                # Gunakan reply_message agar balasan muncul sebagai
                # quoted reply (lebih jelas siapa yang dituju di grup)
                result = client.reply_message(balasan, message)
                print(f"🤖 Bot > {balasan[:80]}...", flush=True)
                print(f"   📤 Send result: {result}", flush=True)
            except Exception as send_err:
                print(f"❌ GAGAL kirim reply_message: {send_err}", flush=True)
                # Fallback: coba send_message biasa
                try:
                    result2 = client.send_message(chat_jid, balasan)
                    print(f"🤖 Bot (fallback) > {balasan[:80]}...", flush=True)
                    print(f"   📤 Fallback result: {result2}", flush=True)
                except Exception as send_err2:
                    print(f"❌ GAGAL send_message juga: {send_err2}", flush=True)
                    import traceback
                    traceback.print_exc()

    except Exception as e:
        # Tangkap SEMUA error dan print ke terminal agar bisa di-debug
        import traceback
        print(f"❌ ERROR saat proses pesan: {e}", flush=True)
        traceback.print_exc()
        sys.stdout.flush()


# =========================================================
# MAIN — JALANKAN BOT
# =========================================================

if __name__ == "__main__":
    print("=" * 55)
    print("  🤖 CHATBOT PENGINGAT TUGAS KULIAH — MODE WHATSAPP")
    print("=" * 55)
    print()

    # Inisialisasi database tugas
    init_db()

    print()

    # Cek apakah session sudah ada
    if os.path.exists(SESSION_DB):
        print("  📱 Session ditemukan! Menghubungkan...")
        print("     (Jika gagal, hapus file wa_session.sqlite3")
        print("      dan jalankan ulang untuk scan QR baru)")
    else:
        print("  📱 Scan QR Code di bawah dengan WhatsApp kamu:")
        print("     Buka WhatsApp > Titik Tiga > Perangkat Tertaut")
        print("     > Tautkan Perangkat > Scan QR Code")

    print()
    print("-" * 55)

    import time
    retry_delay = 5  # detik

    # Mulai koneksi WhatsApp dengan loop auto-reconnect
    while True:
        try:
            print("  🔌 Menghubungkan ke WhatsApp...")
            client.connect()
            # Jika connect() selesai tanpa error (misal disconnect biasa), kita coba hubungkan ulang
            print("  ⚠️ Koneksi terputus. Mencoba menghubungkan kembali dalam 5 detik...")
            time.sleep(retry_delay)
        except KeyboardInterrupt:
            print("\n\n👋 Bot dihentikan oleh pengguna (Ctrl+C). Sampai jumpa!")
            break
        except Exception as e:
            print(f"\n❌ Terjadi kesalahan koneksi: {e}")
            print(f"  Mencoba menyambung ulang dalam {retry_delay} detik...")
            print("Tips:")
            print("  1. Pastikan koneksi internet aktif")
            print("  2. Jika error persisten, hapus file wa_session.sqlite3 dan scan ulang")
            print("  3. Pastikan neonize versi terbaru: pip install --upgrade neonize")
            
            try:
                time.sleep(retry_delay)
            except KeyboardInterrupt:
                print("\n\n👋 Bot dihentikan oleh pengguna (Ctrl+C). Sampai jumpa!")
                break
