import logging
import re
from datetime import datetime
from telegram import Update, ParseMode
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# ========== KONFIGURASI ==========
TOKEN = '7625345294:AAGBA_ArI3k_EHkgXQnooF_1OGkIqnSjvfc'
SPREADSHEET_NAME = 'KUBE 2025 PENDAMPING'
ADMIN_IDS = [1154363370, 787961924]  # Ganti dengan ID admin

# ========== LOGGING ==========
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

print("🚀 Menjalankan Bot Telegram...")

# ========== AUTENTIKASI GOOGLE SHEETS ==========
try:
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
    client = gspread.authorize(creds)
    sheet = client.open(SPREADSHEET_NAME).sheet1
    print("✅ Berhasil menyambungkan dengan Google Sheets.")
except Exception as e:
    print(f"❌ Gagal menyambungkan dengan Google Sheets: {e}")
    exit()

print("✅ Bot aktif dan sedang mendengarkan pesan...")

# ========== CONSTANT ==========
FIELD_NAMES = [
    "WAKTU INPUT", "KABUPATEN", "NAMA PENDAMPING", "TUGAS SEBAGAI", "NIP/ID PEGAWAI", "JABATAN",
    "NIK", "ALAMAT", "NAMA KUBE DAMPINGAN", "NO. TELP (WA)", "NO.REK", "NAMA BANK", "BANK CABANG", "NO NPWP"
]

FORMAT_PESAN = """
Silakan kirim data dengan format seperti ini (WAJIB KAPITAL, jika KUBE lebih dari satu, pisahkan dengan koma):

KABUPATEN: 
NAMA PENDAMPING: 
TUGAS SEBAGAI: 
NIP/ID PEGAWAI: 
JABATAN: 
NIK: 
ALAMAT: 
NAMA KUBE DAMPINGAN: 
NO. TELP (WA): 
NO.REK: 
NAMA BANK: 
BANK CABANG: 
NO NPWP:
"""

# ========== FUNGSI UTAMA ==========
def parse_message(text):
    data = {field.upper(): "-" for field in FIELD_NAMES[1:]}  # default isi "-"
    lines = text.strip().split('\n')

    for line in lines:
        if ":" not in line:
            continue
        key_part, value_part = line.split(":", 1)
        key = key_part.strip().upper()
        value = value_part.strip()
        if key == "NAMA KUBE DAMPINGAN":
            value = '\n'.join([v.strip() for v in value.split(',') if v.strip()])
        if key in data:
            data[key] = value if value else "-"
    return data if len(data) >= 13 else None

def is_admin(user_id):
    return user_id in ADMIN_IDS

def get_user_nik_map():
    """Buat peta user_id -> NIK"""
    values = sheet.get_all_values()
    header = values[0]
    nik_index = header.index("NIK")
    telp_index = header.index("NO. TELP (WA)")

    user_map = {}
    for row in values[1:]:
        if len(row) > telp_index:
            telp = row[telp_index]
            nik = row[nik_index]
            user_map[telp] = nik
    return user_map

# ========== HANDLERS ==========
def start(update: Update, context: CallbackContext):
    update.message.reply_text("Selamat datang! Kirim data sesuai format. Gunakan perintah /format untuk melihat template.")

def format_cmd(update: Update, context: CallbackContext):
    update.message.reply_text(FORMAT_PESAN)

def id_cmd(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    update.message.reply_text(f"🆔 ID Telegram Anda: `{user_id}`", parse_mode=ParseMode.MARKDOWN)

def handle_message(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    text = update.message.text
    username = update.effective_user.full_name

    try:
        data = parse_message(text)
        if not data:
            update.message.reply_text("⚠ Format data tidak lengkap atau salah. Gunakan perintah /format untuk melihat contoh yang benar.")
            return

        nik = data["NIK"]
        telp = data["NO. TELP (WA)"]
        waktu_input = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Bangun data baris lengkap dengan pengisian "-" jika kosong
        row_data = [waktu_input]
        for field in FIELD_NAMES[1:]:
            value = data.get(field, "-").strip()
            if not value:
                value = "-"
            row_data.append(value)

        all_data = sheet.get_all_values()
        header = all_data[0]
        nik_idx = header.index("NIK")
        telp_idx = header.index("NO. TELP (WA)")

        user_map = get_user_nik_map()
        user_nik = user_map.get(telp)

        for i, row in enumerate(all_data[1:], start=2):
            if row[nik_idx] == nik:
                if is_admin(user_id):
                    sheet.update(f"A{i}:{chr(64 + len(FIELD_NAMES))}{i}", [row_data])
                    update.message.reply_text("🔄 Data berhasil diperbarui oleh admin.")
                    return
                elif user_nik == nik:
                    sheet.update(f"A{i}:{chr(64 + len(FIELD_NAMES))}{i}", [row_data])
                    update.message.reply_text("🔄Yeay, Data berhasil diperbarui.")
                    return
                else:
                    update.message.reply_text("🚫Mohon maaf, Anda hanya boleh mengisi atau memperbarui data dengan NIK yang sama. Coba lagi yaaa!")
                    return

        # Jika data belum ada
        if user_nik and user_nik != nik and not is_admin(user_id):
            update.message.reply_text("🚫Mohon maaf, Anda hanya boleh mengisi atau memperbarui data dengan NIK yang sama. Coba lagi yaaa!")
            return

        sheet.append_row(row_data)
        update.message.reply_text("✅ Data baru berhasil disimpan. Terima kasih!")

    except Exception as e:
        update.message.reply_text(f"❌ Terjadi kesalahan saat memproses data: {e}")


# ========== MAIN ==========
def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("format", format_cmd))
    dp.add_handler(CommandHandler("id", id_cmd))
    dp.add_handler(MessageHandler(Filters.text & Filters.group, handle_message))

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
