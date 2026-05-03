import telebot
import subprocess
import os
import zipfile
import tempfile
import shutil
import requests
import re
import logging
import json
import hashlib
import socket
import psutil
import time
from telebot import types
from datetime import datetime, timedelta
import signal
import sqlite3
import threading
from flask import Flask

# تكوين نظام التسجيل
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("bot_security.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("SecureBot")


# سيرفر ويب بسيط للاستضافة والفحص
# Simple web server for hosting health checks
app = Flask(__name__)

@app.route("/")
def home():
    return "OK"

@app.route("/health")
def health():
    return "OK"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

# شغّل السيرفر في Thread منفصل عشان البوت يشتغل بنفس الوقت
threading.Thread(target=run_web, daemon=True).start()


print('''
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣼⡇⠀⠀⠀⠀⠀⠀⠀⠀⣠⣾⣿⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣼⣿⣧⠀⠀⠀⠀⠀⠀⣠⣾⠟⣿⡟⠀⠀⠀⠀⠀⠀⣠⣄⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⡀⠀⠀⠀⣸⣿⠹⣿⡄⠀⠀⠀⢀⣼⡟⠁⠀⢾⡇⠀⠀⠀⣀⣴⣿⡿⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢸⣇⠀⠀⢀⣿⡇⠀⢻⣿⡀⠀⢀⣿⡟⠀⠀⠀⣿⡇⠀⢀⣼⡿⢿⣿⠇⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢸⣿⣆⠀⣸⣿⠀⠀⠀⠻⣷⣤⣾⠏⠀⠀⠀⠀⣿⣧⣶⡿⠋⠀⣼⡏⠀⠀⠀⠀⠀⠀⣠⡄⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠸⣿⣿⣶⣿⡏⠀⠀⠀⠀⠙⠿⠋⠀⠀⠀⠀⠀⠸⠟⠁⠀⠀⢀⣿⠃⠀⢀⣀⣤⣾⣿⡿⠁⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣿⡆⠙⠿⠃⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠸⣿⣶⡶⠟⠋⠉⣼⡟⠁⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢾⣶⣶⣶⣶⣶⣶⣤⣾⣿⡄⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⠀⠀⠀⢠⣾⠏⢀⣀⣠⡀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠉⠛⢷⣦⡀⠀⠀⠉⠉⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⣴⣿⣿⣿⣿⠟⠋⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠙⢻⣦⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⣬⣿⣿⣯⣀⣀⡀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠰⣶⣶⣶⣶⣿⡿⠆⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⠉⠉⠉⣩⣿⡿⠏⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⠙⠻⢿⣷⣤⣤⣤⣤⣶⣶⠾⠿⠿⢿⣿⣿⣿⣿⣿⣷⣶⣶⣶⣤⣤⣤⣀⡀⠀⠀⠀⣠⣤⣶⠿⠛⠉⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⢹⡟⠉⢡⣴⣶⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣟⣋⠉⠈⠉⠛⠻⠿⣿⣷⣶⣿⣿⣦⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢸⡇⠀⢀⣠⣤⣭⣭⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣦⣄⣀⡀⠀⠀⠈⣿⡏⠙⠛⠗⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢸⡇⢰⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣷⢠⣿⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀ ⠀⢠⣿⣷⡘⢿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡍⠙⠻⢿⣿⣿⣿⣿⣿⣿⣿⣾⣿⣆⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀ ⣴⣶⣄⠀  ⠀⠀⠀⠀⢀⡿⠀⣿⡿⣷⣿⣿⣿⡿⠿⠟⠛⠛⠿⠿⣷⣤⣤⣤⣤⣭⣾⣿⠿⠟⠻⣿⡟⣿⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⣴⣶⣤⡀⠀⣿⠉⣿⡆⠀⠀⠀⠀⠀⠈⣿⠀⢸⡇⠀⠈⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠉⠉⠛⠛⠉⠁⠀⠀⠀⠀⠋⢠⣿  ⢀⣴⣿⣷⠀⠀⠀
⠀⣿⡇⠹⣿⣤⣿⡄⢸⣷⠀⠀⠀⠀⠀⠀⠹⢧⣼⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⣀⣰⡿⠃ ⠀⢸⡟⠀⣿⡆⣠⣾⢿⣿⡆
⠀⠘⣿⣄⠈⢿⣿⡇⠘⣿⡄⠀⠀⠀⠀⠀⠀⠈⣿⡆⠀⠀⠀⠀⠐⢾⣿⡟⠛⠛⠛⠳⣶⠀⠀⠀⠀⠀⠀⢀⣾⡟⠋⠀⠀⠀⠀⣼⡇⠀⣿⣷⡟⠁⣼⡟⠀
⠀⠀⠈⢿⣦⡀⠙⠃⠀⣹⣿⣷⣦⡀⠀⠀⠀⠀⠹⣿⣄⠀⠀⠀⠀⠸⣏⠀⠀⠀⠀⣼⠏⠀⠀⠀⠀⢀⣴⡿⠋⠀⠀⠀⠀⠀⢀⣿⡇⠀⣿⠏⢀⣾⠟⠀⠀
⠀⠀⠀⠘⣿⡇⠀⢠⣾⠋⠁⠀⠙⣿⡆⠀⠀⠀⠀⠘⢻⣷⣤⠀⠀⠀⢻⣦⠀⢠⣾⠋⠀⠀⠀⠀⣴⣿⠋⠀⠀⠀⠀⠀⠀⣴⣾⣿⣷⣦⠀⠀⢻⣿⠀⠀⠀
⠀⠀⠀⠀⣿⡇⠀⠘⢿⣶⣶⡖⢀⣿⠇⠀⠀⠀⠀⠀⠀⠙⠻⢷⣦⣄⣀⡙⠛⠛⠁⠀⣀⣠⣶⡿⠛⠁⠀⠀⠀⠀⠀⠀⢸⣿⠉⠉⢉⣿⡇⠀⠘⣿⡆⠀⠀
⠀⠀⠀⠀⢻⣷⡀⠀⠀⠀⢿⣧⡾⠏⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⠙⠛⠛⠿⠿⠿⠟⠛⠋⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⢸⣷⡀⠘⣿⡟⠀⠀⣰⣿⠁⠀⠀
⠀⠀⠀⠀⠀⠙⠻⠿⠿⠿⠟⠋⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠙⢿⣶⣼⣤⣤⣾⠟⠁⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀ ⠀⠀⠀⠀⠉⠉⠉⠀⠀⠀⠀⠀⠀⠀
{3}


''')

# إعدادات البوت
TOKEN = '8606560584:AAH6al7L6bdoAj8f0a5RjWx50moaDdIFtZ0'  # توكنك
ADMIN_ID = 8410176147  # آيدي المالك
YOUR_USERNAME = '@OK_C7'  # يوزر المالك
EXTRA_OWNER_ID = None  # لا يوجد مالك إضافي
EXTRA_OWNER_USERNAME = None

OWNER_IDS = {ADMIN_ID}

def is_owner(user_id):
    return user_id in OWNER_IDS

# المالك
bot = telebot.TeleBot(TOKEN)

# ==== START MENU BUTTONS ====
from telebot import types

def main_menu(user_id):
    markup = types.InlineKeyboardMarkup(row_width=1)
    # زر اللغة
    markup.add(types.InlineKeyboardButton("🌐 اللغة / Language", callback_data="menu_language"))
    # زر بوتاتي
    markup.add(types.InlineKeyboardButton("🤖 بوتاتي", callback_data="menu_my_bots"))
    # زر الاشتراكات
    markup.add(types.InlineKeyboardButton("💳 الاشتراكات", callback_data="menu_subscriptions"))
    return markup

@bot.callback_query_handler(func=lambda call: call.data in ["menu_language","menu_my_bots","menu_subscriptions"])
def menu_handler(call):
    user_id = call.from_user.id
    if call.data == "menu_language":
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🇸🇦 العربية", callback_data="lang_ar"))
        markup.add(types.InlineKeyboardButton("🇺🇸 English", callback_data="lang_en"))
        bot.edit_message_text("اختر اللغة / Choose language:", call.message.chat.id, call.message.message_id, reply_markup=markup)
    elif call.data == "menu_my_bots":
        msg_text = list_user_bots(user_id)
        bot.edit_message_text(msg_text, call.message.chat.id, call.message.message_id, reply_markup=main_menu(user_id))
    elif call.data == "menu_subscriptions":
        msg_text = get_subscription_info(user_id)
        bot.edit_message_text(msg_text, call.message.chat.id, call.message.message_id, reply_markup=main_menu(user_id))

@bot.callback_query_handler(func=lambda call: call.data in ["lang_ar","lang_en"])
def set_language(call):
    user_id = call.from_user.id
    user_languages[user_id] = "ar" if call.data=="lang_ar" else "en"
    text = "✅ تم تغيير اللغة إلى العربية." if call.data=="lang_ar" else "✅ Language changed to English."
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=main_menu(user_id))
# ==== END MENU BUTTONS ====

# إعدادات اللغة
# Language settings
user_languages = {}

def tr(user_id, ar, en):
    return en if user_languages.get(user_id, "ar") == "en" else ar

def lang_suffix(user_id, ar, en):
    return f"{ar}\n\n{en}"

def language_keyboard():
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("🇸🇦 العربية", callback_data="lang_ar"),
        types.InlineKeyboardButton("🇺🇸 English", callback_data="lang_en")
    )
    return markup


# ملف الرسائل الخارجي
# External messages file
MESSAGES_FILE = "messages.json"

DEFAULT_MESSAGES = {
    "ar": {
        "choose_language": "اختر اللغة:",
        "language_changed_ar": "✅ تم تغيير اللغة إلى العربية.",
        "language_changed_en": "✅ Language changed to English.",
        "subscription_title": "💳 خطط الاشتراك",
        "file_rejected_security": "⛔ تم رفض الملف مؤقتاً لأسباب أمنية وتم إرساله للمالك للمراجعة.",
        "upload_prompt": "📄 من فضلك، أرسل الملف الذي تريد رفعه.",
        "bot_locked": "⚠️ البوت مقفل حالياً. الرجاء التواصل مع المطور @OK_C7.",
        "not_owner": "⚠️ أنت لست المطور.",
        "main_note": "〽️ أنا بوت استضافة ملفات بايثون 🎗 يمكنك استخدام الأزرار أدناه للتحكم ♻️\n\n🌐 لتغيير اللغة: /language"
    },
    "en": {
        "choose_language": "Choose language:",
        "language_changed_ar": "✅ تم تغيير اللغة إلى العربية.",
        "language_changed_en": "✅ Language changed to English.",
        "subscription_title": "💳 Subscription Plans",
        "file_rejected_security": "⛔ File temporarily rejected for security review and sent to the owner.",
        "upload_prompt": "📄 Please send the file you want to upload.",
        "bot_locked": "⚠️ The bot is currently locked. Please contact @OK_C7.",
        "not_owner": "⚠️ You are not the developer.",
        "main_note": "〽️ Python hosting bot 🎗 Use the buttons below to control it ♻️\n\n🌐 To change language: /language"
    }
}

def ensure_messages_file():
    if not os.path.exists(MESSAGES_FILE):
        with open(MESSAGES_FILE, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_MESSAGES, f, ensure_ascii=False, indent=2)

def load_messages():
    ensure_messages_file()
    try:
        with open(MESSAGES_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        for lang in DEFAULT_MESSAGES:
            data.setdefault(lang, {})
            for key, value in DEFAULT_MESSAGES[lang].items():
                data[lang].setdefault(key, value)
        return data
    except Exception as e:
        logger.error(f"فشل تحميل ملف الرسائل messages.json: {e}")
        return DEFAULT_MESSAGES

MESSAGES = load_messages()

def msg(user_id, key, **kwargs):
    lang = user_languages.get(user_id, "ar")
    value = MESSAGES.get(lang, MESSAGES["ar"]).get(key, DEFAULT_MESSAGES.get(lang, DEFAULT_MESSAGES["ar"]).get(key, key))
    try:
        return value.format(**kwargs)
    except Exception:
        return value

def edit_or_send(call, text_value, reply_markup=None, parse_mode=None):
    try:
        bot.edit_message_text(
            text_value,
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=reply_markup,
            parse_mode=parse_mode
        )
    except Exception:
        bot.send_message(call.message.chat.id, text_value, reply_markup=reply_markup, parse_mode=parse_mode)

def send_or_edit_menu(target, text_value, reply_markup=None):
    # يقبل callback أو message. callback يعدل نفس الرسالة، message يرسل رسالة جديدة.
    if hasattr(target, "message"):
        edit_or_send(target, text_value, reply_markup=reply_markup)
    else:
        bot.send_message(target.chat.id, text_value, reply_markup=reply_markup)



# المجلدات والمتغيرات العامة
uploaded_files_dir = 'uploaded_bots'
bot_scripts = {}
stored_tokens = {}
user_subscriptions = {}  
user_files = {}  
active_users = set()  
active_usernames = {}
active_user_names = {}
banned_users = set()  # قائمة المستخدمين المحظورين
suspicious_activities = {}  # سجل الأنشطة المشبوهة

# حالة البوت
bot_locked = False  # حالة البوت (مقفل أو مفتوح)
free_mode = False  # وضع البوت بدون اشتراك

# حدود الاشتراكات
# الخطة المجانية محدودة، وخطط الاشتراك أقوى منها.
# المالكين يعملون بدون أي حدود مراقبة من البوت.
FREE_RAM_MB = 128
FREE_CPU_PERCENT = 10
CPU_CHECK_INTERVAL = 5
CPU_MAX_VIOLATIONS = 3

SUBSCRIPTION_PLANS = {
    'free': {
        'name': 'Free Subscription',
        'ram_mb': 128,
        'cpu_percent': 10,
        'description': 'Basic free hosting for small bots.'
    },
    'medium': {
        'name': 'Medium Subscription',
        'ram_mb': 512,
        'cpu_percent': 30,
        'description': 'Better than free, suitable for normal bots.'
    },
    'strong': {
        'name': 'Strong Subscription',
        'ram_mb': 1024,
        'cpu_percent': 60,
        'description': 'High resources for active bots.'
    },
    'very_strong': {
        'name': 'Very Strong Subscription',
        'ram_mb': 2048,
        'cpu_percent': 100,
        'description': 'Maximum paid plan for heavy bots.'
    },
    'owner': {
        'name': 'Owner Unlimited',
        'ram_mb': None,
        'cpu_percent': None,
        'description': 'Unlimited access for the owner.'
    }
}
DEFAULT_PAID_PLAN = 'medium'

# قائمة الكلمات والأنماط المشبوهة للكشف عن محاولات الاختراق
SUSPICIOUS_PATTERNS = [
    r"__import__", 
    r"exec\s*\(", 
    r"eval\s*\(", 
    r"os\.(system|popen|exec|spawn)", 
    r"subprocess\.(Popen|call|check_output|run)",
    r"base64\.(b64decode|b64encode)",
    r"importlib",
    r"getattr\s*\(\s*__builtins__",
    r"open\s*\(\s*['\"]\/",
    r"requests\.get\s*\(\s*['\"]https?:\/\/",
    r"socket\.(connect|bind|listen|accept)",
    r"shutil\.(copy|move|rmtree)",
    r"threading\.Thread",
    r"multiprocessing",
    r"pty\.spawn",
    r"pickle\.(loads|dumps)",
    r"yaml\.load",
    r"marshal\.(loads|dumps)",
]

# قائمة الملفات الحساسة التي يجب حمايتها
SENSITIVE_FILES = [
    "/etc/passwd",
    "/etc/shadow",
    "/etc/hosts",
    "/proc/self",
    "/proc/cpuinfo",
    "/proc/meminfo",
    "/var/log",
    "/root",
    "/home",
    "/.ssh",
    "/.bash_history",
    "/.env",
    "config.json",
    "credentials",
    "password",
    "token",
    "secret",
    "api_key"
]

# إنشاء المجلدات اللازمة
if not os.path.exists(uploaded_files_dir):
    os.makedirs(uploaded_files_dir)

# إنشاء مجلد للملفات المشبوهة
suspicious_files_dir = 'suspicious_files'
if not os.path.exists(suspicious_files_dir):
    os.makedirs(suspicious_files_dir)

# قائمة المالكين الذين تصلهم الملفات والتنبيهات
def get_owner_ids():
    owner_ids = []
    for owner_id in (ADMIN_ID, EXTRA_OWNER_ID):
        if owner_id and owner_id not in owner_ids:
            owner_ids.append(owner_id)
    return owner_ids

def send_message_to_owners(text):
    for owner_id in get_owner_ids():
        try:
            bot.send_message(owner_id, text)
        except Exception as e:
            logger.error(f"فشل إرسال رسالة للمالك {owner_id}: {e}")

def send_document_to_owners(file_path, caption=None):
    for owner_id in get_owner_ids():
        try:
            with open(file_path, 'rb') as file_obj:
                bot.send_document(owner_id, file_obj, caption=caption)
        except Exception as e:
            logger.error(f"فشل إرسال الملف {file_path} للمالك {owner_id}: {e}")

# تهيئة قاعدة البيانات
def init_db():
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    
    # جدول الاشتراكات
    c.execute('''CREATE TABLE IF NOT EXISTS subscriptions
                 (user_id INTEGER PRIMARY KEY, expiry TEXT, plan TEXT DEFAULT 'medium')''')
    c.execute('PRAGMA table_info(subscriptions)')
    subscription_columns = [column[1] for column in c.fetchall()]
    if 'plan' not in subscription_columns:
        c.execute("ALTER TABLE subscriptions ADD COLUMN plan TEXT DEFAULT 'medium'")
    
    # جدول ملفات المستخدمين
    c.execute('''CREATE TABLE IF NOT EXISTS user_files
                 (user_id INTEGER, file_name TEXT)''')
    
    # جدول المستخدمين النشطين
    c.execute('''CREATE TABLE IF NOT EXISTS active_users
                 (user_id INTEGER PRIMARY KEY)''')

    # جدول بيانات المستخدمين لتسهيل إضافة الاشتراك باليوزر
    c.execute('''CREATE TABLE IF NOT EXISTS user_profiles
                 (user_id INTEGER PRIMARY KEY, username TEXT, first_name TEXT, updated_at TEXT)''')
    
    # جدول المستخدمين المحظورين
    c.execute('''CREATE TABLE IF NOT EXISTS banned_users
                 (user_id INTEGER PRIMARY KEY, reason TEXT, ban_date TEXT)''')
    
    # جدول الأنشطة المشبوهة
    c.execute('''CREATE TABLE IF NOT EXISTS suspicious_activities
                 (user_id INTEGER, activity TEXT, file_name TEXT, timestamp TEXT)''')
    
    conn.commit()
    conn.close()

# تحميل البيانات من قاعدة البيانات
def load_data():
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    
    # تحميل الاشتراكات
    c.execute('SELECT user_id, expiry, COALESCE(plan, ?) FROM subscriptions', (DEFAULT_PAID_PLAN,))
    subscriptions = c.fetchall()
    for user_id, expiry, plan in subscriptions:
        if plan not in SUBSCRIPTION_PLANS or plan in ('free', 'owner'):
            plan = DEFAULT_PAID_PLAN
        user_subscriptions[user_id] = {'expiry': datetime.fromisoformat(expiry), 'plan': plan}
    
    # تحميل ملفات المستخدمين
    c.execute('SELECT * FROM user_files')
    user_files_data = c.fetchall()
    for user_id, file_name in user_files_data:
        if user_id not in user_files:
            user_files[user_id] = []
        user_files[user_id].append(file_name)
    
    # تحميل المستخدمين النشطين
    c.execute('SELECT * FROM active_users')
    active_users_data = c.fetchall()
    for user_id, in active_users_data:
        active_users.add(user_id)

    # تحميل اليوزرات المحفوظة
    c.execute('SELECT user_id, username, first_name FROM user_profiles')
    user_profiles_data = c.fetchall()
    for user_id, username, first_name in user_profiles_data:
        if username:
            active_usernames[username.lower().lstrip('@')] = user_id
        active_user_names[user_id] = first_name or ''
    
    # تحميل المستخدمين المحظورين
    c.execute('SELECT user_id FROM banned_users')
    banned_users_data = c.fetchall()
    for user_id, in banned_users_data:
        banned_users.add(user_id)
    
    conn.close()

# حفظ الاشتراك في قاعدة البيانات
def save_subscription(user_id, expiry, plan=DEFAULT_PAID_PLAN):
    if plan not in SUBSCRIPTION_PLANS or plan in ('free', 'owner'):
        plan = DEFAULT_PAID_PLAN
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    c.execute('INSERT OR REPLACE INTO subscriptions (user_id, expiry, plan) VALUES (?, ?, ?)', 
              (user_id, expiry.isoformat(), plan))
    conn.commit()
    conn.close()

# إزالة الاشتراك من قاعدة البيانات
def remove_subscription_db(user_id):
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    c.execute('DELETE FROM subscriptions WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()

# حفظ ملف المستخدم في قاعدة البيانات
def save_user_file(user_id, file_name):
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    c.execute('INSERT INTO user_files (user_id, file_name) VALUES (?, ?)', 
              (user_id, file_name))
    conn.commit()
    conn.close()

# إزالة ملف المستخدم من قاعدة البيانات

def save_user_profile(user_id, username=None, first_name=None):
    if username:
        active_usernames[username.lower().lstrip('@')] = user_id
    active_user_names[user_id] = first_name or ''
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    c.execute('INSERT OR REPLACE INTO user_profiles (user_id, username, first_name, updated_at) VALUES (?, ?, ?, ?)',
              (user_id, username, first_name, datetime.now().isoformat()))
    conn.commit()
    conn.close()

def resolve_user_identifier(identifier):
    value = str(identifier).strip()
    if value.isdigit():
        return int(value)
    username = value.lstrip('@').lower()
    return active_usernames.get(username)

def get_user_label(user_id):
    name = active_user_names.get(user_id, '')
    return f"{name} ({user_id})" if name else str(user_id)

def remove_user_file_db(user_id, file_name):
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    c.execute('DELETE FROM user_files WHERE user_id = ? AND file_name = ?', 
              (user_id, file_name))
    conn.commit()
    conn.close()

# إضافة مستخدم نشط إلى قاعدة البيانات
def add_active_user(user_id):
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    c.execute('INSERT OR IGNORE INTO active_users (user_id) VALUES (?)', (user_id,))
    conn.commit()
    conn.close()

# إزالة مستخدم نشط من قاعدة البيانات
def remove_active_user(user_id):
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    c.execute('DELETE FROM active_users WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()

# حظر مستخدم وإضافته إلى قاعدة البيانات
def ban_user(user_id, reason):
    # الحظر اليدوي فقط بقرار المالك، بدون حظر تلقائي من الفحص الأمني
    if not user_id:
        return
    if is_owner(user_id):
        logger.warning(f"تم منع محاولة حظر المالك {user_id}. السبب: {reason}")
        return
    banned_users.add(user_id)
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    c.execute('INSERT OR REPLACE INTO banned_users (user_id, reason, ban_date) VALUES (?, ?, ?)',
              (user_id, reason, datetime.now().isoformat()))
    conn.commit()
    conn.close()
    logger.warning(f"تم حظر المستخدم {user_id} يدوياً بسبب: {reason}")

# تسجيل نشاط مشبوه في قاعدة البيانات
def log_suspicious_activity(user_id, activity, file_name=None):
    # تسجيل فقط، بدون حظر تلقائي. المالك هو من يقرر.
    if is_owner(user_id):
        logger.info(f"تجاهل نشاط مشبوه للمالك {user_id}: {activity}")
        return False

    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    c.execute('INSERT INTO suspicious_activities (user_id, activity, file_name, timestamp) VALUES (?, ?, ?, ?)',
              (user_id, activity, file_name, datetime.now().isoformat()))
    conn.commit()
    conn.close()

    if user_id not in suspicious_activities:
        suspicious_activities[user_id] = []
    suspicious_activities[user_id].append({
        'activity': activity,
        'file_name': file_name,
        'timestamp': datetime.now().isoformat()
    })

    send_message_to_owners(
        "⚠️ تنبيه أمني / Security Alert\n\n"
        f"User ID: {user_id}\n"
        f"Activity: {activity}\n"
        f"File: {file_name or 'N/A'}\n"
        "Action: No automatic ban. Owner decides manually."
    )
    return False

# إشعار المشرفين بمحاولة اختراق
def notify_admins_of_intrusion(user_id, activity, file_name=None):
    try:
        # الحصول على معلومات المستخدم
        user_info = bot.get_chat(user_id)
        user_name = user_info.first_name
        user_username = user_info.username if user_info.username else "غير متوفر"
        
        # إنشاء رسالة التنبيه
        alert_message = f"⚠️ تنبيه أمني: محاولة اختراق مكتشفة! ⚠️\n\n"
        alert_message += f"👤 المستخدم: {user_name}\n"
        alert_message += f"🆔 معرف المستخدم: {user_id}\n"
        alert_message += f"📌 اليوزر: @{user_username}\n"
        alert_message += f"⚠️ النشاط المشبوه: {activity}\n"
        
        if file_name:
            alert_message += f"📄 الملف المستخدم: {file_name}\n"
        
        alert_message += f"⏰ وقت الاكتشاف: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        alert_message += f"ℹ️ لم يتم حظر المستخدم تلقائياً. القرار للمالك فقط."
        
        # إرسال التنبيه إلى كل المالكين
        send_message_to_owners(alert_message)
        
        # إذا كان هناك ملف، أرسله أيضاً
        if file_name and os.path.exists(os.path.join(suspicious_files_dir, file_name)):
            send_document_to_owners(os.path.join(suspicious_files_dir, file_name), caption=f"الملف المشبوه: {file_name}")
        
        logger.info(f"تم إرسال تنبيه إلى المشرف عن محاولة اختراق من المستخدم {user_id}")
    except Exception as e:
        logger.error(f"فشل في إرسال تنبيه إلى المشرف: {e}")

# فحص الملف للكشف عن الأكواد الضارة
def scan_file_for_malicious_code(file_path, user_id):
    if is_owner(user_id):
        return False, None
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
            content = file.read()
            
            # فحص الأنماط المشبوهة
            for pattern in SUSPICIOUS_PATTERNS:
                matches = re.finditer(pattern, content, re.IGNORECASE)
                for match in matches:
                    suspicious_code = content[max(0, match.start() - 20):min(len(content), match.end() + 20)]
                    activity = f"تم اكتشاف كود مشبوه: {match.group(0)} في السياق: {suspicious_code}"
                    
                    # نسخ الملف المشبوه إلى مجلد الملفات المشبوهة
                    file_name = os.path.basename(file_path)
                    suspicious_file_path = os.path.join(suspicious_files_dir, f"{user_id}_{file_name}")
                    shutil.copy2(file_path, suspicious_file_path)
                    
                    # تسجيل النشاط المشبوه
                    banned = log_suspicious_activity(user_id, activity, file_name)
                    
                    # لا يوجد حظر تلقائي، لكن يتم رفض الملف حتى يراجعه المالك
                    return True, activity
                    
                    logger.warning(f"تم اكتشاف كود مشبوه في الملف {file_path} للمستخدم {user_id}: {match.group(0)}")
            
            # فحص محاولات الوصول إلى الملفات الحساسة
            for sensitive_file in SENSITIVE_FILES:
                if sensitive_file.lower() in content.lower():
                    activity = f"محاولة الوصول إلى ملف حساس: {sensitive_file}"
                    
                    # نسخ الملف المشبوه إلى مجلد الملفات المشبوهة
                    file_name = os.path.basename(file_path)
                    suspicious_file_path = os.path.join(suspicious_files_dir, f"{user_id}_{file_name}")
                    shutil.copy2(file_path, suspicious_file_path)
                    
                    # تسجيل النشاط المشبوه
                    banned = log_suspicious_activity(user_id, activity, file_name)
                    
                    # لا يوجد حظر تلقائي، لكن يتم رفض الملف حتى يراجعه المالك
                    return True, activity
                    
                    logger.warning(f"تم اكتشاف محاولة وصول إلى ملف حساس في الملف {file_path} للمستخدم {user_id}: {sensitive_file}")
        
        return False, None
    except Exception as e:
        logger.error(f"فشل في فحص الملف {file_path}: {e}")
        return False, None

# فحص الملفات في الأرشيف للكشف عن الأكواد الضارة
def scan_zip_for_malicious_code(zip_path, user_id):
    if is_owner(user_id):
        return False, None
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)
            
            for root, dirs, files in os.walk(temp_dir):
                for file in files:
                    if file.endswith('.py'):
                        file_path = os.path.join(root, file)
                        is_malicious, activity = scan_file_for_malicious_code(file_path, user_id)
                        if is_malicious:
                            return True, activity
        
        return False, None
    except Exception as e:
        logger.error(f"فشل في فحص الأرشيف {zip_path}: {e}")
        return False, None

# تهيئة قاعدة البيانات وتحميل البيانات
init_db()
load_data()
# منع بقاء المالك محظوراً إذا انحظر قبل هذا التحديث
def ensure_owners_not_banned():
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    for owner_id in OWNER_IDS:
        banned_users.discard(owner_id)
        c.execute('DELETE FROM banned_users WHERE user_id = ?', (owner_id,))
    conn.commit()
    conn.close()

ensure_owners_not_banned()


# التحقق من نوع خطة المستخدم
def has_active_subscription(user_id):
    return user_id in user_subscriptions and user_subscriptions[user_id]['expiry'] > datetime.now()

def get_user_plan(user_id):
    if is_owner(user_id):
        return 'owner'
    if has_active_subscription(user_id):
        plan = user_subscriptions[user_id].get('plan', DEFAULT_PAID_PLAN)
        if plan in SUBSCRIPTION_PLANS and plan not in ('free', 'owner'):
            return plan
        return DEFAULT_PAID_PLAN
    return 'free'

def get_plan_limits(plan_type):
    return SUBSCRIPTION_PLANS.get(plan_type, SUBSCRIPTION_PLANS['free'])

def get_plan_text(plan_type):
    plan = get_plan_limits(plan_type)
    if plan_type == 'owner':
        return '👑 Owner Unlimited: No RAM or CPU limits'
    return f"💳 {plan['name']}: RAM {plan['ram_mb']}MB | CPU {plan['cpu_percent']}%"

def build_subscription_info():
    return (
        "💳 Subscription Plans\n\n"
        "Free Subscription\n"
        f"RAM: {SUBSCRIPTION_PLANS['free']['ram_mb']}MB\n"
        f"CPU: {SUBSCRIPTION_PLANS['free']['cpu_percent']}%\n"
        f"Description: {SUBSCRIPTION_PLANS['free']['description']}\n\n"
        "Medium Subscription\n"
        f"RAM: {SUBSCRIPTION_PLANS['medium']['ram_mb']}MB\n"
        f"CPU: {SUBSCRIPTION_PLANS['medium']['cpu_percent']}%\n"
        f"Description: {SUBSCRIPTION_PLANS['medium']['description']}\n\n"
        "Strong Subscription\n"
        f"RAM: {SUBSCRIPTION_PLANS['strong']['ram_mb']}MB\n"
        f"CPU: {SUBSCRIPTION_PLANS['strong']['cpu_percent']}%\n"
        f"Description: {SUBSCRIPTION_PLANS['strong']['description']}\n\n"
        "Very Strong Subscription\n"
        f"RAM: {SUBSCRIPTION_PLANS['very_strong']['ram_mb']}MB\n"
        f"CPU: {SUBSCRIPTION_PLANS['very_strong']['cpu_percent']}%\n"
        f"Description: {SUBSCRIPTION_PLANS['very_strong']['description']}\n\n"
        "Paid subscriptions are stronger than the free plan.\n"
        "To buy a subscription, contact the owner."
    )

# مراقبة موارد البوتات حسب الخطة
def monitor_limited_process(process, chat_id, file_name, plan_type):
    plan = get_plan_limits(plan_type)
    ram_mb = plan.get('ram_mb')
    cpu_limit = plan.get('cpu_percent')
    if ram_mb is None and cpu_limit is None:
        return

    try:
        ps_process = psutil.Process(process.pid)
        ps_process.cpu_percent(interval=None)
        violations = 0
        ram_limit_bytes = ram_mb * 1024 * 1024 if ram_mb is not None else None

        while process.poll() is None:
            time.sleep(CPU_CHECK_INTERVAL)
            try:
                cpu_percent = ps_process.cpu_percent(interval=None)
                memory_bytes = ps_process.memory_info().rss

                children = ps_process.children(recursive=True)
                for child in children:
                    try:
                        cpu_percent += child.cpu_percent(interval=None)
                        memory_bytes += child.memory_info().rss
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue

                if ram_limit_bytes is not None and memory_bytes > ram_limit_bytes:
                    kill_process_tree(process)
                    bot.send_message(chat_id, f"⚠️ تم إيقاف {file_name} لأنه تجاوز حد الرام للخطة ({ram_mb}MB).")
                    return

                if cpu_limit is not None and cpu_percent > cpu_limit:
                    violations += 1
                else:
                    violations = 0

                if violations >= CPU_MAX_VIOLATIONS:
                    kill_process_tree(process)
                    bot.send_message(chat_id, f"⚠️ تم إيقاف {file_name} لأنه تجاوز حد المعالج للخطة ({cpu_limit}% CPU).")
                    return
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                return
    except Exception as e:
        logger.error(f"فشل في مراقبة موارد البوت {file_name}: {e}")

# توافق مع الاسم القديم
def monitor_free_process(process, chat_id, file_name):
    monitor_limited_process(process, chat_id, file_name, 'free')


def main_menu_text(user_id, user_name=None, user_username=None, user_bio=None):
    if user_name is None:
        user_name = active_user_names.get(user_id, "")
    username_text = f"@{user_username}" if user_username else "غير متوفر"
    text_value = f"〽️┇اهلا بك: {user_name}\n"
    text_value += f"🆔┇ايديك: {user_id}\n"
    text_value += f"♻️┇يوزرك: {username_text}\n"
    if user_bio is not None:
        text_value += f"📰┇بايو: {user_bio}\n\n"
    text_value += msg(user_id, "main_note")
    return text_value

def back_keyboard(user_id):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("⬅️ رجوع / Back", callback_data="back_main"))
    return markup

# إنشاء القائمة الرئيسية
def create_main_menu(user_id):
    markup = types.InlineKeyboardMarkup()
    upload_button = types.InlineKeyboardButton('📤 رفع ملف', callback_data='upload')
    speed_button = types.InlineKeyboardButton('⚡ سرعة البوت', callback_data='speed')
    contact_button = types.InlineKeyboardButton('📞 تواصل مع المالك', url=f'https://t.me/{YOUR_USERNAME[1:]}')
    plans_button = types.InlineKeyboardButton('💳 الاشتراكات', callback_data='subscription')
    language_button = types.InlineKeyboardButton('🌐 Language / اللغة', callback_data='language_menu')
    if is_owner(user_id):
        subscription_button = types.InlineKeyboardButton('⚙️ إدارة الاشتراكات', callback_data='subscription')
        stats_button = types.InlineKeyboardButton('📊 إحصائيات', callback_data='stats')
        lock_button = types.InlineKeyboardButton('🔒 قفل البوت', callback_data='lock_bot')
        unlock_button = types.InlineKeyboardButton('🔓 فتح البوت', callback_data='unlock_bot')
        free_mode_button = types.InlineKeyboardButton('🔓 فتح البوت بدون اشتراك', callback_data='free_mode')
        broadcast_button = types.InlineKeyboardButton('📢 إذاعة', callback_data='broadcast')
        security_button = types.InlineKeyboardButton('🔐 تقرير الأمان', callback_data='security_report')
        markup.add(upload_button)
        markup.add(speed_button, subscription_button, stats_button)
        markup.add(lock_button, unlock_button, free_mode_button)
        markup.add(broadcast_button, security_button)
    else:
        markup.add(upload_button)
        markup.add(speed_button, plans_button)
    markup.add(language_button)
    markup.add(contact_button)
    return markup

# معالج أمر البدء
@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    
    # التحقق مما إذا كان المستخدم محظوراً
    if user_id in banned_users:
        bot.send_message(message.chat.id, "⛔ أنت محظور من استخدام هذا البوت. يرجى التواصل مع المطور إذا كنت تعتقد أن هذا خطأ.")
        return
    
    if bot_locked:
        bot.send_message(message.chat.id, "⚠️ البوت مقفل حالياً. الرجاء المحاولة لاحقًا.")
        return

    user_name = message.from_user.first_name
    user_username = message.from_user.username
    save_user_profile(user_id, user_username, user_name)

    # محاولة الحصول على معلومات المستخدم
    try:
        user_profile = bot.get_chat(user_id)
        user_bio = user_profile.bio if user_profile.bio else "لا يوجد بايو"
    except Exception as e:
        logger.error(f"فشل في جلب البايو: {e}")
        user_bio = "لا يوجد بايو"

    # محاولة الحصول على صورة المستخدم
    try:
        user_profile_photos = bot.get_user_profile_photos(user_id, limit=1)
        if user_profile_photos.photos:
            photo_file_id = user_profile_photos.photos[0][-1].file_id  
        else:
            photo_file_id = None
    except Exception as e:
        logger.error(f"فشل في جلب صورة المستخدم: {e}")
        photo_file_id = None

    # إضافة المستخدم إلى قائمة المستخدمين النشطين
    if user_id not in active_users:
        active_users.add(user_id)  
        add_active_user(user_id)  

        # إرسال إشعار للمشرف بانضمام مستخدم جديد
        try:
            welcome_message_to_admin = f"🎉 انضم مستخدم جديد إلى البوت!\n\n"
            welcome_message_to_admin += f"👤 الاسم: {user_name}\n"
            welcome_message_to_admin += f"📌 اليوزر: @{user_username}\n"
            welcome_message_to_admin += f"🆔 الـ ID: {user_id}\n"
            welcome_message_to_admin += f"📝 البايو: {user_bio}\n"

            for owner_id in get_owner_ids():
                if photo_file_id:
                    bot.send_photo(owner_id, photo_file_id, caption=welcome_message_to_admin)
                else:
                    bot.send_message(owner_id, welcome_message_to_admin)
        except Exception as e:
            logger.error(f"فشل في إرسال تفاصيل المستخدم إلى الأدمن: {e}")

    # إرسال رسالة الترحيب للمستخدم
    welcome_message = f"〽️┇اهلا بك: {user_name}\n"
    welcome_message += f"🆔┇ايديك: {user_id}\n"
    welcome_message += f"♻️┇يوزرك: @{user_username}\n"
    welcome_message += f"📰┇بايو: {user_bio}\n\n"
    welcome_message += msg(user_id, "main_note")

    if photo_file_id:
        bot.send_photo(message.chat.id, photo_file_id, caption=welcome_message, reply_markup=create_main_menu(user_id))
    else:
        bot.send_message(message.chat.id, welcome_message, reply_markup=create_main_menu(user_id))


@bot.callback_query_handler(func=lambda call: call.data == 'language_menu')
def language_menu_callback(call):
    edit_or_send(call, "اختر اللغة / Choose language:", reply_markup=language_keyboard())


# معالج زر الإذاعة
@bot.callback_query_handler(func=lambda call: call.data == 'broadcast')
def broadcast_callback(call):
    if is_owner(call.from_user.id):
        bot.send_message(call.message.chat.id, "أرسل الرسالة التي تريد إذاعتها:")
        bot.register_next_step_handler(call.message, process_broadcast_message)
    else:
        bot.send_message(call.message.chat.id, "⚠️ أنت لست المطور.")

# معالج زر تقرير الأمان
@bot.callback_query_handler(func=lambda call: call.data == 'security_report')
def security_report_callback(call):
    if is_owner(call.from_user.id):
        conn = sqlite3.connect('bot_data.db')
        c = conn.cursor()
        
        # الحصول على عدد المستخدمين المحظورين
        c.execute('SELECT COUNT(*) FROM banned_users')
        banned_count = c.fetchone()[0]
        
        # الحصول على آخر 5 أنشطة مشبوهة
        c.execute('SELECT user_id, activity, file_name, timestamp FROM suspicious_activities ORDER BY timestamp DESC LIMIT 5')
        recent_activities = c.fetchall()
        
        conn.close()
        
        report = f"📊 تقرير الأمان 🔐\n\n"
        report += f"👥 عدد المستخدمين المحظورين: {banned_count}\n\n"
        
        if recent_activities:
            report += "⚠️ آخر الأنشطة المشبوهة:\n"
            for user_id, activity, file_name, timestamp in recent_activities:
                dt = datetime.fromisoformat(timestamp)
                formatted_time = dt.strftime('%Y-%m-%d %H:%M:%S')
                report += f"- المستخدم: {user_id}\n"
                report += f"  النشاط: {activity}\n"
                if file_name:
                    report += f"  الملف: {file_name}\n"
                report += f"  الوقت: {formatted_time}\n\n"
        else:
            report += "✅ لا توجد أنشطة مشبوهة مسجلة."
        
        edit_or_send(call, report, reply_markup=back_keyboard(call.from_user.id))
    else:
        bot.send_message(call.message.chat.id, "⚠️ أنت لست المطور.")

# معالج رسائل الإذاعة
def process_broadcast_message(message):
    if is_owner(message.from_user.id):
        broadcast_message = message.text
        success_count = 0
        fail_count = 0

        for user_id in active_users:
            try:
                bot.send_message(user_id, broadcast_message)
                success_count += 1
            except Exception as e:
                logger.error(f"فشل في إرسال الرسالة إلى المستخدم {user_id}: {e}")
                fail_count += 1

        bot.send_message(message.chat.id, f"✅ تم إرسال الرسالة إلى {success_count} مستخدم.\n❌ فشل إرسال الرسالة إلى {fail_count} مستخدم.")
    else:
        bot.send_message(message.chat.id, "⚠️ أنت لست المطور.")

# معالج زر سرعة البوت
@bot.callback_query_handler(func=lambda call: call.data == 'speed')
def bot_speed_info(call):
    try:
        start_time = time.time()
        response = requests.get(f'https://api.telegram.org/bot{TOKEN}/getMe')
        latency = time.time() - start_time
        if response.ok:
            bot.send_message(call.message.chat.id, f"⚡ سرعة البوت: {latency:.2f} ثانية.")
        else:
            bot.send_message(call.message.chat.id, "⚠️ فشل في الحصول على سرعة البوت.")
    except Exception as e:
        logger.error(f"حدث خطأ أثناء فحص سرعة البوت: {e}")
        bot.send_message(call.message.chat.id, f"❌ حدث خطأ أثناء فحص سرعة البوت: {e}")

# معالج زر رفع ملف
@bot.callback_query_handler(func=lambda call: call.data == 'upload')
def ask_to_upload_file(call):
    user_id = call.from_user.id
    
    # التحقق مما إذا كان المستخدم محظوراً
    if user_id in banned_users:
        bot.send_message(call.message.chat.id, "⛔ أنت محظور من استخدام هذا البوت. يرجى التواصل مع المطور إذا كنت تعتقد أن هذا خطأ.")
        return
    
    if bot_locked:
        edit_or_send(call, msg(call.from_user.id, "bot_locked"), reply_markup=back_keyboard(call.from_user.id))
        return
    if free_mode or get_user_plan(user_id):
        edit_or_send(call, msg(call.from_user.id, "upload_prompt"), reply_markup=back_keyboard(call.from_user.id))
    else:
        bot.send_message(call.message.chat.id, "⚠️ يجب عليك الاشتراك لاستخدام هذه الميزة. الرجاء التواصل مع المطور @OK_C7 .")


def show_admin_subscription_plans(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton('Medium Subscription', callback_data='adm_plan_medium'))
    markup.add(types.InlineKeyboardButton('Strong Subscription', callback_data='adm_plan_strong'))
    markup.add(types.InlineKeyboardButton('Very Strong Subscription', callback_data='adm_plan_very_strong'))
    markup.add(types.InlineKeyboardButton('Remove Subscription', callback_data='remove_subscription'))
    bot.send_message(
        message.chat.id,
        "Admin Subscription Panel\n\nChoose a plan, then send the user ID or @username and the number of days.\nExample: @user 30\n\nPlans:\nMedium Subscription\nStrong Subscription\nVery Strong Subscription",
        reply_markup=markup
    )

@bot.message_handler(func=lambda message: message.text and message.text.strip().lower() in ('adm', '/adm'))
def adm_panel(message):
    if is_owner(message.from_user.id):
        show_admin_subscription_plans(message)
    else:
        bot.send_message(message.chat.id, "⚠️ أنت لست المطور.")

@bot.callback_query_handler(func=lambda call: call.data.startswith('adm_plan_'))
def adm_plan_selected(call):
    if not is_owner(call.from_user.id):
        bot.send_message(call.message.chat.id, "⚠️ أنت لست المطور.")
        return
    plan = call.data.replace('adm_plan_', '', 1)
    if plan not in ('medium', 'strong', 'very_strong'):
        bot.send_message(call.message.chat.id, "❌ Invalid plan.")
        return
    bot.send_message(call.message.chat.id, f"Selected: {SUBSCRIPTION_PLANS[plan]['name']}\nSend: @username days\nExample: @user 30")
    bot.register_next_step_handler(call.message, lambda msg: process_plan_assignment(msg, plan))

def process_plan_assignment(message, plan):
    if not is_owner(message.from_user.id):
        bot.send_message(message.chat.id, "⚠️ أنت لست المطور.")
        return
    try:
        parts = message.text.split()
        if len(parts) < 2:
            bot.send_message(message.chat.id, "❌ Send it like this: @username 30 or 123456789 30")
            return
        user_id = resolve_user_identifier(parts[0])
        days = int(parts[1])
        if not user_id:
            bot.send_message(message.chat.id, "❌ I could not find this @username. The user must start the bot first, or use the numeric user ID.")
            return
        expiry_date = datetime.now() + timedelta(days=days)
        user_subscriptions[user_id] = {'expiry': expiry_date, 'plan': plan}
        save_subscription(user_id, expiry_date, plan)
        bot.send_message(message.chat.id, f"✅ Added {SUBSCRIPTION_PLANS[plan]['name']} for {days} days to {get_user_label(user_id)}.")
        try:
            bot.send_message(user_id, f"🎉 Your {SUBSCRIPTION_PLANS[plan]['name']} is active for {days} days.\n{get_plan_text(plan)}")
        except Exception:
            pass
    except Exception as e:
        logger.error(f"حدث خطأ أثناء إضافة اشتراك من لوحة adm: {e}")
        bot.send_message(message.chat.id, f"❌ حدث خطأ: {e}")

def process_remove_subscription_identifier(message):
    if not is_owner(message.from_user.id):
        bot.send_message(message.chat.id, "⚠️ أنت لست المطور.")
        return
    try:
        user_id = resolve_user_identifier(message.text.split()[0])
        if not user_id:
            bot.send_message(message.chat.id, "❌ I could not find this user. Use ID or a @username that started the bot.")
            return
        if user_id in user_subscriptions:
            del user_subscriptions[user_id]
            remove_subscription_db(user_id)
            bot.send_message(message.chat.id, f"✅ Removed paid subscription from {get_user_label(user_id)}.")
            try:
                bot.send_message(user_id, "⚠️ Your paid subscription was removed. You are now on the Free Subscription.")
            except Exception:
                pass
        else:
            bot.send_message(message.chat.id, f"⚠️ {get_user_label(user_id)} does not have a paid subscription.")
    except Exception as e:
        logger.error(f"حدث خطأ أثناء إزالة اشتراك من لوحة adm: {e}")
        bot.send_message(message.chat.id, f"❌ حدث خطأ: {e}")

# معالج زر الاشتراكات
@bot.callback_query_handler(func=lambda call: call.data == 'subscription')
def subscription_menu(call):
    markup = types.InlineKeyboardMarkup()
    buy_button = types.InlineKeyboardButton('Buy Subscription', url=f'https://t.me/{YOUR_USERNAME[1:]}')
    markup.add(buy_button)

    if is_owner(call.from_user.id):
        add_subscription_button = types.InlineKeyboardButton('➕ Add Subscription', callback_data='add_subscription')
        remove_subscription_button = types.InlineKeyboardButton('➖ Remove Subscription', callback_data='remove_subscription')
        markup.add(add_subscription_button, remove_subscription_button)

    markup.add(types.InlineKeyboardButton("⬅️ رجوع / Back", callback_data="back_main"))
    edit_or_send(call, build_subscription_info(), reply_markup=markup)

# معالج زر الإحصائيات
@bot.callback_query_handler(func=lambda call: call.data == 'stats')
def stats_menu(call):
    if is_owner(call.from_user.id):
        total_files = sum(len(files) for files in user_files.values())
        total_users = len(user_files)
        active_users_count = len(active_users)
        banned_users_count = len(banned_users)
        edit_or_send(call, f"📊 الإحصائيات:\n\n📂 عدد الملفات المرفوعة: {total_files}\n👤 عدد المستخدمين: {total_users}\n👥 المستخدمين النشطين: {active_users_count}\n🚫 المستخدمين المحظورين: {banned_users_count}", reply_markup=back_keyboard(call.from_user.id))
    else:
        bot.send_message(call.message.chat.id, "⚠️ أنت لست المطور.")

# معالج زر إضافة اشتراك
@bot.callback_query_handler(func=lambda call: call.data == 'add_subscription')
def add_subscription_callback(call):
    if is_owner(call.from_user.id):
        show_admin_subscription_plans(call.message)
    else:
        bot.send_message(call.message.chat.id, "⚠️ أنت لست المطور.")

# معالج زر إزالة اشتراك
@bot.callback_query_handler(func=lambda call: call.data == 'remove_subscription')
def remove_subscription_callback(call):
    if is_owner(call.from_user.id):
        bot.send_message(call.message.chat.id, "Send the user ID or @username to remove the paid subscription:")
        bot.register_next_step_handler(call.message, process_remove_subscription_identifier)
    else:
        bot.send_message(call.message.chat.id, "⚠️ أنت لست المطور.")

# معالج أمر إضافة اشتراك
@bot.message_handler(commands=['add_subscription'])
def add_subscription(message):
    if is_owner(message.from_user.id):
        try:
            parts = message.text.split()
            user_id = resolve_user_identifier(parts[1])
            if not user_id:
                bot.send_message(message.chat.id, "❌ I could not find this @username. The user must start the bot first, or use the numeric user ID.")
                return
            days = int(parts[2])
            plan = parts[3].lower() if len(parts) > 3 else DEFAULT_PAID_PLAN
            if plan not in ('medium', 'strong', 'very_strong'):
                bot.send_message(message.chat.id, "❌ Invalid plan. Use: medium, strong, very_strong")
                return
            expiry_date = datetime.now() + timedelta(days=days)
            user_subscriptions[user_id] = {'expiry': expiry_date, 'plan': plan}
            save_subscription(user_id, expiry_date, plan)
            bot.send_message(message.chat.id, f"✅ Added {SUBSCRIPTION_PLANS[plan]['name']} for {days} days to user {user_id}.")
            bot.send_message(user_id, f"🎉 Your {SUBSCRIPTION_PLANS[plan]['name']} is active for {days} days.\n{get_plan_text(plan)}")
        except Exception as e:
            logger.error(f"حدث خطأ أثناء إضافة اشتراك: {e}")
            bot.send_message(message.chat.id, f"❌ حدث خطأ: {e}")
    else:
        bot.send_message(message.chat.id, "⚠️ أنت لست المطور.")

# معالج أمر إزالة اشتراك
@bot.message_handler(commands=['remove_subscription'])
def remove_subscription(message):
    if is_owner(message.from_user.id):
        try:
            user_id = resolve_user_identifier(message.text.split()[1])
            if not user_id:
                bot.send_message(message.chat.id, "❌ I could not find this user. Use ID or a @username that started the bot.")
                return
            if user_id in user_subscriptions:
                del user_subscriptions[user_id]
                remove_subscription_db(user_id)
                bot.send_message(message.chat.id, f"✅ تم إزالة الاشتراك للمستخدم {user_id}.")
                bot.send_message(user_id, "⚠️ Your paid subscription was removed. You are now on the Free Subscription.")
            else:
                bot.send_message(message.chat.id, f"⚠️ المستخدم {user_id} ليس لديه اشتراك.")
        except Exception as e:
            logger.error(f"حدث خطأ أثناء إزالة اشتراك: {e}")
            bot.send_message(message.chat.id, f"❌ حدث خطأ: {e}")
    else:
        bot.send_message(message.chat.id, "⚠️ أنت لست المطور.")

# معالج أمر عرض ملفات المستخدم
@bot.message_handler(commands=['user_files'])
def show_user_files(message):
    if is_owner(message.from_user.id):
        try:
            user_id = int(message.text.split()[1])
            if user_id in user_files:
                files_list = "\n".join(user_files[user_id])
                bot.send_message(message.chat.id, f"📂 الملفات التي رفعها المستخدم {user_id}:\n{files_list}")
            else:
                bot.send_message(message.chat.id, f"⚠️ المستخدم {user_id} لم يرفع أي ملفات.")
        except Exception as e:
            logger.error(f"حدث خطأ أثناء عرض ملفات المستخدم: {e}")
            bot.send_message(message.chat.id, f"❌ حدث خطأ: {e}")
    else:
        bot.send_message(message.chat.id, "⚠️ أنت لست المطور.")

# معالج أمر قفل البوت
@bot.message_handler(commands=['lock'])
def lock_bot(message):
    if is_owner(message.from_user.id):
        global bot_locked
        bot_locked = True
        bot.send_message(message.chat.id, "🔒 تم قفل البوت.")
    else:
        bot.send_message(message.chat.id, "⚠️ أنت لست المطور.")

# معالج أمر فتح البوت
@bot.message_handler(commands=['unlock'])
def unlock_bot(message):
    if is_owner(message.from_user.id):
        global bot_locked
        bot_locked = False
        bot.send_message(message.chat.id, "🔓 تم فتح البوت.")
    else:
        bot.send_message(message.chat.id, "⚠️ أنت لست المطور.")

# معالج زر قفل البوت
@bot.callback_query_handler(func=lambda call: call.data == 'lock_bot')
def lock_bot_callback(call):
    if is_owner(call.from_user.id):
        global bot_locked
        bot_locked = True
        bot.send_message(call.message.chat.id, "🔒 تم قفل البوت.")
    else:
        bot.send_message(call.message.chat.id, "⚠️ أنت لست المطور.")

# معالج زر فتح البوت
@bot.callback_query_handler(func=lambda call: call.data == 'unlock_bot')
def unlock_bot_callback(call):
    if is_owner(call.from_user.id):
        global bot_locked
        bot_locked = False
        bot.send_message(call.message.chat.id, "🔓 تم فتح البوت.")
    else:
        bot.send_message(call.message.chat.id, "⚠️ أنت لست المطور.")

# معالج زر فتح البوت بدون اشتراك
@bot.callback_query_handler(func=lambda call: call.data == 'free_mode')
def toggle_free_mode(call):
    if is_owner(call.from_user.id):
        global free_mode
        free_mode = not free_mode
        status = "مفتوح" if free_mode else "مغلق"
        bot.send_message(call.message.chat.id, f"🔓 تم تغيير وضع البوت بدون اشتراك إلى: {status}.")
    else:
        bot.send_message(call.message.chat.id, "⚠️ أنت لست المطور.")

# معالج أمر حظر مستخدم
@bot.message_handler(commands=['ban'])
def ban_user_command(message):
    if is_owner(message.from_user.id):
        try:
            parts = message.text.split(maxsplit=2)
            if len(parts) < 3:
                bot.send_message(message.chat.id, "⚠️ الصيغة الصحيحة: /ban <user_id> <reason>")
                return
            
            user_id = int(parts[1])
            reason = parts[2]
            
            ban_user(user_id, reason)
            bot.send_message(message.chat.id, f"✅ تم حظر المستخدم يدوياً {user_id} بسبب: {reason}")
            try:
                bot.send_message(user_id, f"⛔ تم حظرك من استخدام البوت بسبب: {reason}")
            except:
                pass
        except Exception as e:
            logger.error(f"حدث خطأ أثناء حظر المستخدم: {e}")
            bot.send_message(message.chat.id, f"❌ حدث خطأ: {e}")
    else:
        bot.send_message(message.chat.id, "⚠️ أنت لست المطور.")

# معالج أمر إلغاء حظر مستخدم
@bot.message_handler(commands=['unban'])
def unban_user_command(message):
    if is_owner(message.from_user.id):
        try:
            user_id = int(message.text.split()[1])
            
            if user_id in banned_users:
                banned_users.remove(user_id)
                
                conn = sqlite3.connect('bot_data.db')
                c = conn.cursor()
                c.execute('DELETE FROM banned_users WHERE user_id = ?', (user_id,))
                conn.commit()
                conn.close()
                
                bot.send_message(message.chat.id, f"✅ تم إلغاء حظر المستخدم {user_id}")
                try:
                    bot.send_message(user_id, f"🎉 تم إلغاء الحظر عنك. يمكنك الآن استخدام البوت مرة أخرى.")
                except:
                    pass
            else:
                bot.send_message(message.chat.id, f"⚠️ المستخدم {user_id} غير محظور.")
        except Exception as e:
            logger.error(f"حدث خطأ أثناء إلغاء حظر المستخدم: {e}")
            bot.send_message(message.chat.id, f"❌ حدث خطأ: {e}")
    else:
        bot.send_message(message.chat.id, "⚠️ أنت لست المطور.")

# معالج استلام الملفات
@bot.message_handler(content_types=['document'])
def handle_file(message):
    user_id = message.from_user.id
    save_user_profile(user_id, message.from_user.username, message.from_user.first_name)
    
    # التحقق مما إذا كان المستخدم محظوراً
    if user_id in banned_users:
        bot.reply_to(message, "⛔ أنت محظور من استخدام هذا البوت. يرجى التواصل مع المطور إذا كنت تعتقد أن هذا خطأ.")
        return
    
    if bot_locked:
        bot.reply_to(message, "⚠️ البوت مقفل حالياً. الرجاء التواصل مع المطور @OK_C7.")
        return
    
    if free_mode or get_user_plan(user_id):
        plan_type = get_user_plan(user_id)
        try:
            file_id = message.document.file_id
            file_info = bot.get_file(file_id)
            downloaded_file = bot.download_file(file_info.file_path)
            file_name = message.document.file_name

            # التحقق من نوع الملف
            if not file_name.endswith('.py') and not file_name.endswith('.zip'):
                bot.reply_to(message, "⚠️ هذا البوت خاص برفع ملفات بايثون (.py) أو أرشيفات zip فقط.")
                return

            # حساب بصمة الملف للتحقق من الأمان
            file_hash = hashlib.sha256(downloaded_file).hexdigest()
            logger.info(f"تم استلام ملف: {file_name} من المستخدم {user_id} بالبصمة {file_hash}")

            # معالجة ملفات الأرشيف
            if file_name.endswith('.zip'):
                # حفظ الملف مؤقتاً للفحص
                temp_zip_path = os.path.join(tempfile.gettempdir(), file_name)
                with open(temp_zip_path, 'wb') as temp_file:
                    temp_file.write(downloaded_file)
                
                # فحص الأرشيف للكشف عن الأكواد الضارة
                is_malicious, activity = scan_zip_for_malicious_code(temp_zip_path, user_id)
                
                if is_malicious:
                    bot.reply_to(message, "⛔ تم رفض الملف مؤقتاً لأسباب أمنية وتم إرساله للمالك للمراجعة.\n⛔ File temporarily rejected for security review and sent to the owner.")
                    return
                
                with tempfile.TemporaryDirectory() as temp_dir:
                    zip_folder_path = os.path.join(temp_dir, file_name.split('.')[0])

                    zip_path = os.path.join(temp_dir, file_name)
                    with open(zip_path, 'wb') as new_file:
                        new_file.write(downloaded_file)
                    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                        zip_ref.extractall(zip_folder_path)

                    final_folder_path = os.path.join(uploaded_files_dir, file_name.split('.')[0])
                    if not os.path.exists(final_folder_path):
                        os.makedirs(final_folder_path)

                    for root, dirs, files in os.walk(zip_folder_path):
                        for file in files:
                            src_file = os.path.join(root, file)
                            dest_file = os.path.join(final_folder_path, file)
                            shutil.move(src_file, dest_file)

                    # البحث عن ملفات بايثون في الأرشيف
                    py_files = [f for f in os.listdir(final_folder_path) if f.endswith('.py')]
                    if py_files:
                        main_script = py_files[0]  
                        run_script(os.path.join(final_folder_path, main_script), message.chat.id, final_folder_path, main_script, message, plan_type)
                    else:
                        bot.send_message(message.chat.id, f"❌ لم يتم العثور على أي ملفات بايثون (.py) في الأرشيف.")
                        return

            else:
                # حفظ الملف مؤقتاً للفحص
                temp_script_path = os.path.join(tempfile.gettempdir(), file_name)
                with open(temp_script_path, 'wb') as temp_file:
                    temp_file.write(downloaded_file)
                
                # فحص الملف للكشف عن الأكواد الضارة
                is_malicious, activity = scan_file_for_malicious_code(temp_script_path, user_id)
                
                if is_malicious:
                    bot.reply_to(message, "⛔ تم رفض الملف مؤقتاً لأسباب أمنية وتم إرساله للمالك للمراجعة.\n⛔ File temporarily rejected for security review and sent to the owner.")
                    return
                
                script_path = os.path.join(uploaded_files_dir, file_name)
                with open(script_path, 'wb') as new_file:
                    new_file.write(downloaded_file)

                run_script(script_path, message.chat.id, uploaded_files_dir, file_name, message, plan_type)

            if user_id not in user_files:
                user_files[user_id] = []
            user_files[user_id].append(file_name)
            save_user_file(user_id, file_name)

        except Exception as e:
            logger.error(f"فشل في معالجة الملف: {e}")
            bot.reply_to(message, f"❌ حدث خطأ: {e}")
    else:
        bot.reply_to(message, "⚠️ يجب عليك الاشتراك لاستخدام هذه الميزة. الرجاء التواصل مع المطور @OK_C7.")

# تشغيل البوت
def run_script(script_path, chat_id, folder_path, file_name, original_message, plan_type='free'):
    try:
        requirements_path = os.path.join(os.path.dirname(script_path), 'requirements.txt')
        if os.path.exists(requirements_path):
            bot.send_message(chat_id, "🔄 جارٍ تثبيت المتطلبات...")
            subprocess.check_call(['pip', 'install', '-r', requirements_path])

        bot.send_message(chat_id, f"🚀 جارٍ تشغيل البوت {file_name}...\n{get_plan_text(plan_type)}")
        
        # إنشاء بيئة آمنة لتشغيل البوت
        env = os.environ.copy()
        env["PYTHONPATH"] = os.path.dirname(script_path)
        
        process = subprocess.Popen(['python3', script_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
        bot_scripts[chat_id] = {'process': process, 'folder_path': folder_path, 'plan_type': plan_type}

        if plan_type != 'owner':
            monitor_thread = threading.Thread(
                target=monitor_limited_process,
                args=(process, chat_id, file_name, plan_type),
                daemon=True
            )
            monitor_thread.start()

        token = extract_token_from_script(script_path)
        if token:
            try:
                bot_info = requests.get(f'https://api.telegram.org/bot{token}/getMe').json()
                if bot_info.get('ok'):
                    bot_username = bot_info['result']['username']

                    user_info = f"@{original_message.from_user.username}" if original_message.from_user.username else str(original_message.from_user.id)
                    caption = f"📤 قام المستخدم {user_info} برفع ملف بوت جديد. معرف البوت: @{bot_username}"
                    send_document_to_owners(script_path, caption=caption)

                    markup = types.InlineKeyboardMarkup()
                    stop_button = types.InlineKeyboardButton(f"🔴 إيقاف {file_name}", callback_data=f'stop_{chat_id}_{file_name}')
                    delete_button = types.InlineKeyboardButton(f"🗑️ حذف {file_name}", callback_data=f'delete_{chat_id}_{file_name}')
                    markup.add(stop_button, delete_button)
                    bot.send_message(chat_id, f"استخدم الأزرار أدناه للتحكم في البوت 👇", reply_markup=markup)
                else:
                    bot.send_message(chat_id, f"✅ تم تشغيل البوت بنجاح! ولكن لم أتمكن من التحقق من معرف البوت.")
            except Exception as e:
                logger.error(f"فشل في التحقق من معرف البوت: {e}")
                bot.send_message(chat_id, f"✅ تم تشغيل البوت بنجاح! ولكن لم أتمكن من التحقق من معرف البوت.")
        else:
            bot.send_message(chat_id, f"✅ تم تشغيل البوت بنجاح! ولكن لم أتمكن من جلب معرف البوت.")
            user_info = f"@{original_message.from_user.username}" if original_message.from_user.username else str(original_message.from_user.id)
            send_document_to_owners(script_path, caption=f"📤 قام المستخدم {user_info} برفع ملف بوت جديد، ولكن لم أتمكن من جلب معرف البوت.")

    except Exception as e:
        logger.error(f"فشل في تشغيل البوت: {e}")
        bot.send_message(chat_id, f"❌ حدث خطأ أثناء تشغيل البوت: {e}")

# استخراج التوكن من الملف
def extract_token_from_script(script_path):
    try:
        with open(script_path, 'r', encoding='utf-8', errors='ignore') as script_file:
            file_content = script_file.read()

            token_match = re.search(r"['\"]([0-9]{9,10}:[A-Za-z0-9_-]+)['\"]", file_content)
            if token_match:
                return token_match.group(1)
            else:
                logger.warning(f"لم يتم العثور على توكن في {script_path}")
    except Exception as e:
        logger.error(f"فشل في استخراج التوكن من {script_path}: {e}")
    return None


@bot.callback_query_handler(func=lambda call: call.data in ("lang_ar", "lang_en"))
def set_language(call):
    user_languages[call.from_user.id] = "ar" if call.data == "lang_ar" else "en"
    if user_languages[call.from_user.id] == "ar":
        edit_or_send(call, msg(call.from_user.id, "language_changed_ar"), reply_markup=create_main_menu(call.from_user.id))
    else:
        edit_or_send(call, msg(call.from_user.id, "language_changed_en"), reply_markup=create_main_menu(call.from_user.id))

@bot.message_handler(commands=['language', 'lang'])
def language_command(message):
    bot.send_message(
        message.chat.id,
        "اختر اللغة / Choose language:",
        reply_markup=language_keyboard()
    )



@bot.callback_query_handler(func=lambda call: call.data == "back_main")
def back_to_main(call):
    try:
        user = call.from_user
        save_user_profile(user.id, user.username, user.first_name)
        edit_or_send(call, main_menu_text(user.id, user.first_name, user.username), reply_markup=create_main_menu(user.id))
    except Exception as e:
        logger.error(f"فشل الرجوع للقائمة الرئيسية: {e}")
        bot.send_message(call.message.chat.id, "⚠️ حدث خطأ أثناء الرجوع للقائمة.")


# معالج الاستجابة للأزرار
@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    chat_id = call.message.chat.id
    
    # التحقق من نوع الزر
    if 'stop_' in call.data:
        file_name = call.data.split('_')[-1]
        stop_running_bot(chat_id)
    elif 'delete_' in call.data:
        file_name = call.data.split('_')[-1]
        delete_uploaded_file(chat_id)

# إيقاف البوت
def stop_running_bot(chat_id):
    if chat_id in bot_scripts and bot_scripts[chat_id].get('process'):
        kill_process_tree(bot_scripts[chat_id]['process'])
        bot.send_message(chat_id, "🔴 تم إيقاف تشغيل البوت.")
    else:
        bot.send_message(chat_id, "⚠️ لا يوجد بوت يعمل حالياً.")

# حذف الملفات المرفوعة
def delete_uploaded_file(chat_id):
    if chat_id in bot_scripts and bot_scripts[chat_id].get('folder_path') and os.path.exists(bot_scripts[chat_id]['folder_path']):
        shutil.rmtree(bot_scripts[chat_id]['folder_path'])
        bot.send_message(chat_id, f"🗑️ تم حذف الملفات المتعلقة بالبوت.")
    else:
        bot.send_message(chat_id, "⚠️ الملفات غير موجودة.")

# قتل العمليات
def kill_process_tree(process):
    try:
        parent = psutil.Process(process.pid)
        children = parent.children(recursive=True)
        for child in children:
            child.kill()
        parent.kill()
    except Exception as e:
        logger.error(f"فشل في قتل العملية: {e}")

# معالج أمر حذف ملف المستخدم
@bot.message_handler(commands=['delete_user_file'])
def delete_user_file(message):
    if is_owner(message.from_user.id):
        try:
            user_id = int(message.text.split()[1])
            file_name = message.text.split()[2]
            
            if user_id in user_files and file_name in user_files[user_id]:
                file_path = os.path.join(uploaded_files_dir, file_name)
                if os.path.exists(file_path):
                    os.remove(file_path)
                    user_files[user_id].remove(file_name)
                    remove_user_file_db(user_id, file_name)
                    bot.send_message(message.chat.id, f"✅ تم حذف الملف {file_name} للمستخدم {user_id}.")
                else:
                    bot.send_message(message.chat.id, f"⚠️ الملف {file_name} غير موجود.")
            else:
                bot.send_message(message.chat.id, f"⚠️ المستخدم {user_id} لم يرفع الملف {file_name}.")
        except Exception as e:
            logger.error(f"فشل في حذف ملف المستخدم: {e}")
            bot.send_message(message.chat.id, f"❌ حدث خطأ: {e}")
    else:
        bot.send_message(message.chat.id, "⚠️ أنت لست المطور.")

# معالج أمر إيقاف بوت المستخدم
@bot.message_handler(commands=['stop_user_bot'])
def stop_user_bot(message):
    if is_owner(message.from_user.id):
        try:
            user_id = int(message.text.split()[1])
            file_name = message.text.split()[2]
            
            if user_id in user_files and file_name in user_files[user_id]:
                for chat_id, script_info in bot_scripts.items():
                    if script_info.get('folder_path', '').endswith(file_name.split('.')[0]):
                        kill_process_tree(script_info['process'])
                        bot.send_message(chat_id, f"🔴 تم إيقاف تشغيل البوت {file_name}.")
                        bot.send_message(message.chat.id, f"✅ تم إيقاف تشغيل البوت {file_name} للمستخدم {user_id}.")
                        break
                else:
                    bot.send_message(message.chat.id, f"⚠️ البوت {file_name} غير قيد التشغيل.")
            else:
                bot.send_message(message.chat.id, f"⚠️ المستخدم {user_id} لم يرفع الملف {file_name}.")
        except Exception as e:
            logger.error(f"فشل في إيقاف بوت المستخدم: {e}")
            bot.send_message(message.chat.id, f"❌ حدث خطأ: {e}")
    else:
        bot.send_message(message.chat.id, "⚠️ أنت لست المطور.")

# تشغيل البوت
logger.info('بدء تشغيل البوت بنجاح')
print('تم تشغيل البوت بنجاح')
bot.infinity_polling()
