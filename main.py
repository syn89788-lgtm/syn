# -*- coding: utf-8 -*-
"""
OK_C7 Telegram Bot - Render-ready version
- Flask health endpoint for Render/UptimeRobot
- Stores data in OK_C7_STORAGE.json beside this file
- Does NOT save posts unless the user first chooses "صنع منشور"
- Control group stays silent except send/delete commands
"""

import os
import json
import time
import threading
import traceback
from copy import deepcopy

from flask import Flask
import telebot
from telebot import types
from telebot.apihelper import ApiTelegramException


# =========================
# Render / UptimeRobot web
# =========================

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

threading.Thread(target=run_web, daemon=True).start()


# =========================
# Bot settings
# =========================

# الأفضل في Render تضيف Environment Variable باسم BOT_TOKEN.
# لو ما أضفته، حط التوكن بين علامتي التنصيص تحت.
BOT_TOKEN = os.environ.get("BOT_TOKEN", "").strip() or "PUT_YOUR_BOT_TOKEN_HERE"

if ":" not in BOT_TOKEN:
    raise ValueError("Token must contain a colon. Put your Telegram bot token in BOT_TOKEN or inside BOT_TOKEN variable.")

bot = telebot.TeleBot(BOT_TOKEN, parse_mode=None)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STORAGE_FILE = os.path.join(BASE_DIR, "OK_C7_STORAGE.json")


OWNER_ID = 6507166349          # @x7vqz4
ASSISTANT_OWNER_ID = 8410176147 # @OK_C7
THIRD_ALLOWED_ID = 5723931989   # @rzzqr

TRUE_ADMINS = {OWNER_ID, ASSISTANT_OWNER_ID}
DEFAULT_ALLOWED = {OWNER_ID, ASSISTANT_OWNER_ID, THIRD_ALLOWED_ID}

# اتركه صفر. أول قروب تستخدم فيه /s سيصير قروب التحكم تلقائياً.
CONTROL_GROUP_ID = int(os.environ.get("CONTROL_GROUP_ID", "0") or "0")

RAZER_BOT_URL = "https://t.me/RAZERESPECTBOT"

WAITING_FOR_POST = "waiting_for_post"
user_states = {}


# =========================
# Storage
# =========================

DEFAULT_DATA = {
    "posts": [],
    "next_post_id": 1,
    "channels": [],
    "allowed_users": list(DEFAULT_ALLOWED),
    "control_group_id": CONTROL_GROUP_ID,
    "sent_messages": {}
}

DATA = deepcopy(DEFAULT_DATA)


def load_data():
    global DATA, CONTROL_GROUP_ID
    if not os.path.exists(STORAGE_FILE):
        DATA = deepcopy(DEFAULT_DATA)
        save_data(explicit_delete=True)
        return

    try:
        with open(STORAGE_FILE, "r", encoding="utf-8") as f:
            loaded = json.load(f)
    except Exception:
        loaded = {}

    DATA = deepcopy(DEFAULT_DATA)
    if isinstance(loaded, dict):
        DATA.update(loaded)

    # repair
    DATA.setdefault("posts", [])
    DATA.setdefault("next_post_id", 1)
    DATA.setdefault("channels", [])
    DATA.setdefault("allowed_users", list(DEFAULT_ALLOWED))
    DATA.setdefault("control_group_id", CONTROL_GROUP_ID)
    DATA.setdefault("sent_messages", {})

    for uid in DEFAULT_ALLOWED:
        if uid not in DATA["allowed_users"]:
            DATA["allowed_users"].append(uid)

    try:
        CONTROL_GROUP_ID = int(DATA.get("control_group_id") or CONTROL_GROUP_ID or 0)
    except Exception:
        CONTROL_GROUP_ID = 0

    # keep next_post_id sane
    max_id = 0
    for p in DATA["posts"]:
        try:
            max_id = max(max_id, int(p.get("id", 0)))
        except Exception:
            pass
    DATA["next_post_id"] = max(int(DATA.get("next_post_id", 1)), max_id + 1)


def save_data(explicit_delete=False):
    """
    Basic protection: do not accidentally save fewer posts unless explicit_delete=True.
    """
    old_posts_count = 0
    if os.path.exists(STORAGE_FILE):
        try:
            with open(STORAGE_FILE, "r", encoding="utf-8") as f:
                old = json.load(f)
            old_posts_count = len(old.get("posts", []))
        except Exception:
            old_posts_count = 0

    new_posts_count = len(DATA.get("posts", []))
    if old_posts_count and new_posts_count < old_posts_count and not explicit_delete:
        print("[PROTECT] Refused saving fewer posts without explicit_delete=True")
        return False

    tmp = STORAGE_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(DATA, f, ensure_ascii=False, indent=2)
    os.replace(tmp, STORAGE_FILE)
    return True


load_data()


# =========================
# Helpers
# =========================

def is_private(message):
    return message.chat.type == "private"

def is_group(message):
    return message.chat.type in ("group", "supergroup")

def user_id_of(message):
    return message.from_user.id if message.from_user else 0

def is_allowed(user_id):
    return user_id in set(DATA.get("allowed_users", []))

def is_true_admin(user_id):
    return user_id in TRUE_ADMINS

def safe_send(chat_id, text, **kwargs):
    try:
        return bot.send_message(chat_id, text, **kwargs)
    except Exception as e:
        print("[send_message error]", repr(e))
        return None

def main_keyboard(user_id):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("صنع منشور 📌", "تعديل منشور 📝")
    kb.row("منشوراتي")
    if user_id == ASSISTANT_OWNER_ID:
        kb.row("/adm")
    return kb

def razer_inline_keyboard():
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("فتح بوت الصنع/التعديل", url=RAZER_BOT_URL))
    return kb

def post_by_id(post_id):
    for p in DATA["posts"]:
        if int(p.get("id", -1)) == int(post_id):
            return p
    return None

def normalize_channel(chat_ref):
    chat_ref = str(chat_ref).strip()
    if not chat_ref:
        return None
    return chat_ref

def add_channel(chat_ref):
    chat_ref = normalize_channel(chat_ref)
    if not chat_ref:
        return False
    if chat_ref not in DATA["channels"]:
        DATA["channels"].append(chat_ref)
        save_data()
    return True

def remove_channel(chat_ref):
    chat_ref = normalize_channel(chat_ref)
    if not chat_ref:
        return False
    if chat_ref in DATA["channels"]:
        DATA["channels"].remove(chat_ref)
        save_data()
        return True
    return False


# =========================
# Markup serialization
# =========================

def serialize_reply_markup(reply_markup):
    if not reply_markup:
        return None
    try:
        raw = reply_markup.to_dict()
    except Exception:
        raw = getattr(reply_markup, "json", None)
    if not raw:
        return None

    inline_keyboard = raw.get("inline_keyboard") if isinstance(raw, dict) else None
    if not inline_keyboard:
        return None

    clean_rows = []
    for row in inline_keyboard:
        clean_row = []
        for btn in row:
            text = btn.get("text")
            url = btn.get("url")
            callback_data = btn.get("callback_data")
            if text and url:
                clean_row.append({"text": text, "url": url})
            elif text and callback_data:
                clean_row.append({"text": text, "callback_data": callback_data})
        if clean_row:
            clean_rows.append(clean_row)
    return clean_rows or None

def build_inline_markup(rows):
    if not rows:
        return None
    kb = types.InlineKeyboardMarkup()
    for row in rows:
        buttons = []
        for btn in row:
            text = btn.get("text", "")
            if btn.get("url"):
                buttons.append(types.InlineKeyboardButton(text, url=btn["url"]))
            elif btn.get("callback_data"):
                buttons.append(types.InlineKeyboardButton(text, callback_data=btn["callback_data"]))
        if buttons:
            kb.row(*buttons)
    return kb


# =========================
# Post save/send/delete
# =========================

SUPPORTED_CONTENT_TYPES = {
    "text", "photo", "video", "animation", "document", "audio", "voice", "video_note", "sticker"
}

def save_post_from_message(message):
    """
    Saves the next message after 'صنع منشور'.
    Accepts text, media, forwarded/copied posts, and inline URL buttons if present.
    """
    content_type = message.content_type
    if content_type not in SUPPORTED_CONTENT_TYPES:
        return None, "هذا النوع غير مدعوم."

    post_id = int(DATA.get("next_post_id", 1))
    post = {
        "id": post_id,
        "type": content_type,
        "caption": getattr(message, "caption", None),
        "text": getattr(message, "text", None),
        "reply_markup": serialize_reply_markup(getattr(message, "reply_markup", None)),
        "created_at": int(time.time()),
        "from_user_id": user_id_of(message),
        "sent_messages": []
    }

    if content_type == "photo":
        post["file_id"] = message.photo[-1].file_id
    elif content_type == "video":
        post["file_id"] = message.video.file_id
    elif content_type == "animation":
        post["file_id"] = message.animation.file_id
    elif content_type == "document":
        post["file_id"] = message.document.file_id
    elif content_type == "audio":
        post["file_id"] = message.audio.file_id
    elif content_type == "voice":
        post["file_id"] = message.voice.file_id
    elif content_type == "video_note":
        post["file_id"] = message.video_note.file_id
    elif content_type == "sticker":
        post["file_id"] = message.sticker.file_id

    DATA["posts"].append(post)
    DATA["next_post_id"] = post_id + 1
    save_data()
    return post, None


def send_post_to_chat(post, chat_id):
    markup = build_inline_markup(post.get("reply_markup"))
    t = post.get("type")
    caption = post.get("caption")

    if t == "text":
        return bot.send_message(chat_id, post.get("text") or "", reply_markup=markup)
    if t == "photo":
        return bot.send_photo(chat_id, post["file_id"], caption=caption, reply_markup=markup)
    if t == "video":
        return bot.send_video(chat_id, post["file_id"], caption=caption, reply_markup=markup)
    if t == "animation":
        return bot.send_animation(chat_id, post["file_id"], caption=caption, reply_markup=markup)
    if t == "document":
        return bot.send_document(chat_id, post["file_id"], caption=caption, reply_markup=markup)
    if t == "audio":
        return bot.send_audio(chat_id, post["file_id"], caption=caption, reply_markup=markup)
    if t == "voice":
        return bot.send_voice(chat_id, post["file_id"], caption=caption, reply_markup=markup)
    if t == "video_note":
        return bot.send_video_note(chat_id, post["file_id"], reply_markup=markup)
    if t == "sticker":
        return bot.send_sticker(chat_id, post["file_id"], reply_markup=markup)
    raise ValueError("Unsupported post type")


def delete_sent_messages(post):
    deleted = 0
    for item in list(post.get("sent_messages", [])):
        try:
            bot.delete_message(item["chat_id"], item["message_id"])
            deleted += 1
        except Exception as e:
            print("[delete sent message error]", repr(e))
    post["sent_messages"] = []
    save_data(explicit_delete=True)
    return deleted


def send_post_to_channels(post):
    sent = []
    for ch in DATA.get("channels", []):
        try:
            msg = send_post_to_chat(post, ch)
            if msg:
                sent.append({"chat_id": msg.chat.id, "message_id": msg.message_id})
        except Exception as e:
            print(f"[send to {ch} error]", repr(e))
    post["sent_messages"] = sent
    save_data()
    return sent


# =========================
# Commands
# =========================

@bot.message_handler(commands=["start"])
def cmd_start(message):
    uid = user_id_of(message)
    if not is_allowed(uid):
        if is_private(message):
            safe_send(message.chat.id, "غير مسموح لك باستخدام البوت.")
        return

    if is_group(message):
        return

    safe_send(
        message.chat.id,
        "أهلًا. اختر من القائمة.",
        reply_markup=main_keyboard(uid)
    )


@bot.message_handler(commands=["allow"])
def cmd_allow(message):
    uid = user_id_of(message)
    if not is_true_admin(uid):
        return

    parts = (message.text or "").split(maxsplit=1)
    if len(parts) < 2:
        safe_send(message.chat.id, "استخدم: /allow ID")
        return

    target = parts[1].strip().replace("@", "")
    try:
        target_id = int(target)
    except ValueError:
        safe_send(message.chat.id, "استخدم ID رقمي.")
        return

    if target_id not in DATA["allowed_users"]:
        DATA["allowed_users"].append(target_id)
        save_data()
    safe_send(message.chat.id, f"تم السماح: {target_id}")


@bot.message_handler(commands=["unallow"])
def cmd_unallow(message):
    uid = user_id_of(message)
    if not is_true_admin(uid):
        return

    parts = (message.text or "").split(maxsplit=1)
    if len(parts) < 2:
        safe_send(message.chat.id, "استخدم: /unallow ID")
        return

    try:
        target_id = int(parts[1].strip().replace("@", ""))
    except ValueError:
        safe_send(message.chat.id, "استخدم ID رقمي.")
        return

    if target_id in DEFAULT_ALLOWED:
        safe_send(message.chat.id, "لا يمكن إزالة السماح الأساسي.")
        return

    if target_id in DATA["allowed_users"]:
        DATA["allowed_users"].remove(target_id)
        save_data()
    safe_send(message.chat.id, f"تم إلغاء السماح: {target_id}")


@bot.message_handler(commands=["allowed"])
def cmd_allowed(message):
    uid = user_id_of(message)
    if not is_true_admin(uid):
        return
    text = "المسموح لهم:\n" + "\n".join(str(x) for x in DATA.get("allowed_users", []))
    safe_send(message.chat.id, text)


@bot.message_handler(commands=["add"])
def cmd_add_channel(message):
    uid = user_id_of(message)
    if not is_true_admin(uid):
        return

    parts = (message.text or "").split(maxsplit=1)
    if len(parts) < 2:
        safe_send(message.chat.id, "استخدم: /add @channel أو /add -100...")
        return

    if add_channel(parts[1]):
        safe_send(message.chat.id, "تمت إضافة القناة.")
    else:
        safe_send(message.chat.id, "لم تتم الإضافة.")


@bot.message_handler(commands=["del"])
def cmd_del_channel(message):
    uid = user_id_of(message)
    if not is_true_admin(uid):
        return

    parts = (message.text or "").split(maxsplit=1)
    if len(parts) < 2:
        safe_send(message.chat.id, "استخدم: /del @channel أو /del -100...")
        return

    if remove_channel(parts[1]):
        safe_send(message.chat.id, "تم حذف القناة.")
    else:
        safe_send(message.chat.id, "القناة غير موجودة.")


@bot.message_handler(commands=["chats"])
def cmd_chats(message):
    uid = user_id_of(message)
    if not is_true_admin(uid):
        return

    channels = DATA.get("channels", [])
    if not channels:
        safe_send(message.chat.id, "لا توجد قنوات.")
    else:
        safe_send(message.chat.id, "القنوات:\n" + "\n".join(channels))


@bot.message_handler(commands=["d"])
def cmd_delete_saved_post(message):
    uid = user_id_of(message)
    if not is_true_admin(uid):
        return

    parts = (message.text or "").split()
    if len(parts) < 2:
        safe_send(message.chat.id, "استخدم: /d رقم_المنشور")
        return

    try:
        post_id = int(parts[1])
    except ValueError:
        safe_send(message.chat.id, "رقم المنشور غير صحيح.")
        return

    post = post_by_id(post_id)
    if not post:
        safe_send(message.chat.id, "المنشور غير موجود.")
        return

    delete_sent_messages(post)
    DATA["posts"] = [p for p in DATA["posts"] if int(p.get("id", -1)) != post_id]
    save_data(explicit_delete=True)
    safe_send(message.chat.id, f"تم حذف المنشور {post_id} نهائيًا.")


@bot.message_handler(commands=["s"])
def cmd_send_post(message):
    """
    Works only in control group.
    If CONTROL_GROUP_ID is 0, first group using /s becomes control group.
    """
    global CONTROL_GROUP_ID

    uid = user_id_of(message)
    if not is_allowed(uid):
        return

    if is_private(message):
        return

    if CONTROL_GROUP_ID == 0:
        CONTROL_GROUP_ID = message.chat.id
        DATA["control_group_id"] = CONTROL_GROUP_ID
        save_data()

    if message.chat.id != CONTROL_GROUP_ID:
        return

    parts = (message.text or "").split()
    if len(parts) < 2:
        return

    try:
        post_id = int(parts[1])
    except ValueError:
        return

    post = post_by_id(post_id)
    if not post:
        safe_send(message.chat.id, "المنشور غير موجود.")
        return

    kb = types.InlineKeyboardMarkup()
    if post.get("sent_messages"):
        kb.add(types.InlineKeyboardButton("🗑 حذف منشور", callback_data=f"del_sent:{post_id}"))
        kb.add(types.InlineKeyboardButton("🗑 حذف وارسال", callback_data=f"del_resend:{post_id}"))
        safe_send(message.chat.id, "المنشور مرسل سابقًا.", reply_markup=kb)
        return

    sent = send_post_to_channels(post)
    kb.add(types.InlineKeyboardButton("🗑 حذف منشور", callback_data=f"del_sent:{post_id}"))
    kb.add(types.InlineKeyboardButton("🗑 حذف وارسال", callback_data=f"del_resend:{post_id}"))
    safe_send(message.chat.id, f"تم الإرسال إلى {len(sent)} قناة.", reply_markup=kb)


@bot.message_handler(commands=["adm"])
def cmd_admin_menu(message):
    uid = user_id_of(message)
    if uid != ASSISTANT_OWNER_ID:
        return
    if is_group(message):
        return

    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("📌 صنع منشور", callback_data="make_post"))
    kb.add(types.InlineKeyboardButton("📝 تعديل منشور", url=RAZER_BOT_URL))
    kb.add(types.InlineKeyboardButton("خروج", callback_data="close_admin"))
    safe_send(message.chat.id, "قائمة الأدمن:", reply_markup=kb)


@bot.message_handler(commands=["oadm"])
def cmd_close_admin(message):
    uid = user_id_of(message)
    if uid != ASSISTANT_OWNER_ID:
        return
    if is_private(message):
        safe_send(message.chat.id, "تم الخروج من قائمة الأدمن.")


# =========================
# Callback buttons
# =========================

@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    uid = call.from_user.id
    chat_id = call.message.chat.id if call.message else uid

    if not is_allowed(uid):
        try:
            bot.answer_callback_query(call.id)
        except Exception:
            pass
        return

    data = call.data or ""

    try:
        bot.answer_callback_query(call.id)
    except Exception:
        pass

    if data == "make_post":
        user_states[uid] = WAITING_FOR_POST
        safe_send(chat_id, "أرسل المنشور الآن.")
        return

    if data == "close_admin":
        try:
            bot.edit_message_text("تم الإغلاق.", chat_id, call.message.message_id)
        except Exception:
            pass
        return

    if data.startswith("del_sent:"):
        post_id = int(data.split(":", 1)[1])
        post = post_by_id(post_id)
        if not post:
            safe_send(chat_id, "المنشور غير موجود.")
            return
        count = delete_sent_messages(post)
        safe_send(chat_id, f"تم حذف {count} رسالة من القنوات.")
        return

    if data.startswith("del_resend:"):
        post_id = int(data.split(":", 1)[1])
        post = post_by_id(post_id)
        if not post:
            safe_send(chat_id, "المنشور غير موجود.")
            return
        delete_sent_messages(post)
        sent = send_post_to_channels(post)
        safe_send(chat_id, f"تم الحذف والإرسال إلى {len(sent)} قناة.")
        return


# =========================
# Text/menu handling
# =========================

@bot.message_handler(content_types=["text"])
def handle_text(message):
    uid = user_id_of(message)

    if not is_allowed(uid):
        if is_private(message) and (message.text or "").strip() == "/start":
            safe_send(message.chat.id, "غير مسموح لك باستخدام البوت.")
        return

    # Control group stays silent except command handlers above.
    if is_group(message) and CONTROL_GROUP_ID and message.chat.id == CONTROL_GROUP_ID:
        return

    text = (message.text or "").strip()

    if is_private(message) and text in ("صنع منشور", "صنع منشور 📌", "اصنع منشور"):
        user_states[uid] = WAITING_FOR_POST
        safe_send(message.chat.id, "أرسل المنشور الآن.")
        return

    if is_private(message) and text in ("تعديل منشور", "تعديل منشور 📝"):
        safe_send(message.chat.id, "افتح بوت التعديل:", reply_markup=razer_inline_keyboard())
        return

    if is_private(message) and text == "منشوراتي":
        posts = DATA.get("posts", [])
        if not posts:
            safe_send(message.chat.id, "لا توجد منشورات محفوظة.")
            return
        lines = ["منشوراتك:"]
        for p in posts[-50:]:
            preview = p.get("text") or p.get("caption") or p.get("type")
            preview = str(preview).replace("\n", " ")[:40]
            lines.append(f"{p.get('id')} - {preview}")
        safe_send(message.chat.id, "\n".join(lines))
        return

    # If user is waiting for a post and sends text, save it.
    if user_states.get(uid) == WAITING_FOR_POST:
        post, err = save_post_from_message(message)
        user_states.pop(uid, None)
        if err:
            safe_send(message.chat.id, err)
        else:
            safe_send(message.chat.id, f"تم حفظ المنشور رقم {post['id']}.")
        return

    # Any random message outside creation mode: silence.
    return


@bot.message_handler(content_types=["photo", "video", "animation", "document", "audio", "voice", "video_note", "sticker"])
def handle_media(message):
    uid = user_id_of(message)

    if not is_allowed(uid):
        return

    # Control group stays silent.
    if is_group(message) and CONTROL_GROUP_ID and message.chat.id == CONTROL_GROUP_ID:
        return

    if user_states.get(uid) != WAITING_FOR_POST:
        return

    post, err = save_post_from_message(message)
    user_states.pop(uid, None)
    if err:
        safe_send(message.chat.id, err)
    else:
        safe_send(message.chat.id, f"تم حفظ المنشور رقم {post['id']}.")


# =========================
# Polling loop
# =========================

def run_bot_forever():
    print("[OK_C7] Bot started.")
    while True:
        try:
            bot.infinity_polling(timeout=60, long_polling_timeout=60, skip_pending=True)
        except ApiTelegramException as e:
            print("[Telegram API error]", repr(e))
            if "409" in str(e):
                print("[409 Conflict] نفس التوكن شغال في مكان ثاني. أوقف النسخة الثانية.")
            time.sleep(10)
        except Exception as e:
            print("[Loop error]", repr(e))
            traceback.print_exc()
            time.sleep(10)

if __name__ == "__main__":
    run_bot_forever()
