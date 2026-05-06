# OK_C7 PURE PYTHON BOT
# لا يحتاج أي مكتبات خارجية
# شغله باسم main.py في الاستضافة

import json
import os
import time
import shutil
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
import urllib.parse
import urllib.request
from typing import Any, Dict, Optional

BOT_TOKEN = "8787985203:AAHZRJN9jWrFK5WURY5VU9XBuDxiSg-gT-E"
BOT_USERNAME = "RESPECTRAZEBOT"
RAZERESPECT_URL = "https://t.me/RAZERESPECTBOT"
BOT_VERSION = "OK_C7_ONE_INSTANCE_DEDUP_V18"

OWNER_ID = 6507166349
ASSISTANT_OWNER_ID = 8410176147
THIRD_ALLOWED_ID = 5723931989

OWNER_USERNAME = "x7vqz4"
ASSISTANT_OWNER_USERNAME = "OK_C7"
THIRD_ALLOWED_USERNAME = "rzzqr"

ADMIN_IDS = {OWNER_ID, ASSISTANT_OWNER_ID}
ADMIN_USERNAMES = {OWNER_USERNAME.lower(), ASSISTANT_OWNER_USERNAME.lower()}

ALLOWED_USER_IDS = {OWNER_ID, ASSISTANT_OWNER_ID, THIRD_ALLOWED_ID}
ALLOWED_USERNAMES = {OWNER_USERNAME.lower(), ASSISTANT_OWNER_USERNAME.lower(), THIRD_ALLOWED_USERNAME.lower()}

APP_DIR = os.path.dirname(os.path.abspath(__file__))
STORAGE_FILE_NAME = "OK_C7_STORAGE.json"

# التخزين الثابت:
# 1) إذا حطيت OK_C7_STORAGE_FILE في Render يستخدمه.
# 2) إذا عندك Persistent Disk على Render غالبا يكون /var/data، يستخدمه تلقائيا.
# 3) إذا ما فيه دسك، يستخدم نفس مجلد main.py. هذا يحافظ داخل نفس التشغيل فقط، لكن Render المجاني قد يمسحه بعد التحديث.
def choose_data_file():
    env_path = os.environ.get("OK_C7_STORAGE_FILE")
    if env_path:
        return env_path
    render_disk = "/var/data"
    if os.path.isdir(render_disk) and os.access(render_disk, os.W_OK):
        return os.path.join(render_disk, STORAGE_FILE_NAME)
    return os.path.join(APP_DIR, STORAGE_FILE_NAME)

DATA_FILE = choose_data_file()
BACKUP_FILE = DATA_FILE + ".bak"
TMP_FILE = DATA_FILE + ".tmp"
OLD_APP_DATA_FILE = os.path.join(APP_DIR, STORAGE_FILE_NAME)

DELETE_OPERATION_ACTIVE = False

# user_id -> state dict
USER_STATE: Dict[str, Dict[str, Any]] = {}


# =========================
# Telegram API
# =========================

def api(method: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/{method}"
    payload = json.dumps(data or {}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as response:
        raw = response.read().decode("utf-8")
        result = json.loads(raw)
        if not result.get("ok"):
            raise RuntimeError(result)
        return result


def send_message(chat_id, text, reply_markup=None):
    data = {"chat_id": chat_id, "text": text}
    if reply_markup is not None:
        data["reply_markup"] = reply_markup
    return api("sendMessage", data).get("result")


def edit_message_text(chat_id, message_id, text, reply_markup=None):
    data = {"chat_id": chat_id, "message_id": message_id, "text": text}
    if reply_markup is not None:
        data["reply_markup"] = reply_markup
    return api("editMessageText", data).get("result")


def answer_callback_query(callback_query_id, text=None, show_alert=False):
    data = {"callback_query_id": callback_query_id, "show_alert": show_alert}
    if text:
        data["text"] = text
    try:
        return api("answerCallbackQuery", data).get("result")
    except Exception:
        return None


def delete_message(chat_id, message_id):
    return api("deleteMessage", {"chat_id": chat_id, "message_id": message_id}).get("result")


def get_chat(target):
    return api("getChat", {"chat_id": target}).get("result")


def get_updates(offset=None):
    data = {"timeout": 35, "allowed_updates": ["message", "callback_query"]}
    if offset is not None:
        data["offset"] = offset
    return api("getUpdates", data).get("result", [])


def remove_webhook():
    try:
        api("deleteWebhook", {"drop_pending_updates": True})
    except Exception as e:
        print("deleteWebhook failed:", e, flush=True)


# =========================
# Storage
# =========================

def ensure_storage_location():
    """ينقل التخزين القديم للمسار الثابت إذا لزم، بدون حذف المنشورات."""
    data_dir = os.path.dirname(DATA_FILE)
    if data_dir:
        os.makedirs(data_dir, exist_ok=True)

    # لو انتقلنا من مجلد التطبيق إلى Persistent Disk، انسخ التخزين القديم مرة واحدة.
    if DATA_FILE != OLD_APP_DATA_FILE and (not os.path.exists(DATA_FILE)) and os.path.exists(OLD_APP_DATA_FILE):
        try:
            shutil.copy2(OLD_APP_DATA_FILE, DATA_FILE)
            print(f"Migrated storage from {OLD_APP_DATA_FILE} to {DATA_FILE}", flush=True)
        except Exception as e:
            print("storage migration failed:", e, flush=True)


def safe_load_json_file(path):
    try:
        if not os.path.exists(path):
            return None
        with open(path, "r", encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, dict) else None
    except Exception as e:
        print(f"safe_load_json_file failed {path}: {e}", flush=True)
        return None


def recover_storage_data():
    """يحاول يرجع البيانات من الملف الأساسي ثم الباك أب. لا يصفّر المنشورات بسبب ملف خربان."""
    for path in (DATA_FILE, BACKUP_FILE, OLD_APP_DATA_FILE):
        d = safe_load_json_file(path)
        if isinstance(d, dict):
            return normalize_data(d)
    return None

def normalize_username(username: str) -> str:
    return str(username or "").strip().lower().lstrip("@")


def default_data():
    return {
        "allowed_users": list(ALLOWED_USER_IDS),
        "allowed_usernames": list(ALLOWED_USERNAMES),
        "banned_users": [],
        "banned_usernames": [],
        "posts": [],
        "next_post_id": 1,
        "target_chats": [],
        "processed_update_ids": [],
    }


def normalize_data(data):
    if not isinstance(data, dict):
        data = default_data()

    data.setdefault("allowed_users", list(ALLOWED_USER_IDS))
    data.setdefault("allowed_usernames", list(ALLOWED_USERNAMES))
    data.setdefault("banned_users", [])
    data.setdefault("banned_usernames", [])
    data.setdefault("posts", [])
    data.setdefault("next_post_id", 1)
    data.setdefault("target_chats", [])
    data.setdefault("processed_update_ids", [])

    for uid in ALLOWED_USER_IDS:
        if uid not in data["allowed_users"]:
            data["allowed_users"].append(uid)

    data["allowed_usernames"] = sorted({
        normalize_username(x)
        for x in data.get("allowed_usernames", [])
        if normalize_username(x)
    } | {normalize_username(x) for x in ALLOWED_USERNAMES})

    data["banned_usernames"] = sorted({
        normalize_username(x)
        for x in data.get("banned_usernames", [])
        if normalize_username(x)
    })

    clean_posts = []
    max_id = 0
    for i, post in enumerate(data.get("posts", []), start=1):
        if not isinstance(post, dict):
            continue
        try:
            post["id"] = int(post.get("id", i))
        except Exception:
            post["id"] = i
        max_id = max(max_id, post["id"])
        post.setdefault("sent_messages", {})
        clean_posts.append(post)

    data["posts"] = clean_posts
    try:
        data["next_post_id"] = int(data.get("next_post_id", 1) or 1)
    except Exception:
        data["next_post_id"] = 1
    if data["next_post_id"] < 1:
        data["next_post_id"] = 1
    return data


def load_data():
    ensure_storage_location()
    data = recover_storage_data()
    if data is not None:
        return data

    # ما فيه أي ملف تخزين أو باك أب. هنا فقط يبدأ جديد.
    data = default_data()
    save_data(data)
    return data


def read_existing_data_raw():
    return safe_load_json_file(DATA_FILE)


def posts_ids(data):
    ids = []
    if not isinstance(data, dict):
        return ids
    for post in data.get("posts", []):
        if not isinstance(post, dict):
            continue
        try:
            ids.append(int(post.get("id")))
        except Exception:
            pass
    return ids


def next_post_id_value(data):
    # يرجع أصغر رقم فاضي. إذا حذفت 2، المنشور الجديد القادم يصير 2.
    used = set(posts_ids(data))
    n = 1
    while n in used:
        n += 1
    return n


def allocate_post_id(data):
    post_id = next_post_id_value(data)
    used = set(posts_ids(data)) | {post_id}
    n = 1
    while n in used:
        n += 1
    data["next_post_id"] = n
    return post_id


def save_data(data):
    global DELETE_OPERATION_ACTIVE
    data = normalize_data(data)
    old_data = read_existing_data_raw()

    if old_data is not None and not DELETE_OPERATION_ACTIVE:
        old_ids = posts_ids(old_data)
        new_ids = posts_ids(data)

        # يمنع أي تحديث أو تغيير توكن من حذف منشورات قديمة بالغلط.
        if len(old_ids) > 0 and len(new_ids) < len(old_ids):
            print(f"Blocked unsafe save old_posts={len(old_ids)} new_posts={len(new_ids)}", flush=True)
            return False

        # يمنع تغيير أرقام المنشورات القديمة أو اختفاء رقم قديم إلا عند /d فقط.
        missing_ids = [x for x in old_ids if x not in new_ids]
        if missing_ids:
            print(f"Blocked unsafe save missing_post_ids={missing_ids}", flush=True)
            return False

    data["next_post_id"] = next_post_id_value(data)

    # حفظ آمن: نسخة احتياطية ثم ملف مؤقت ثم استبدال ذري.
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, "r", encoding="utf-8") as src, open(BACKUP_FILE, "w", encoding="utf-8") as dst:
                dst.write(src.read())
    except Exception as e:
        print("backup failed:", e, flush=True)

    with open(TMP_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(TMP_FILE, DATA_FILE)
    return True


def find_post(post_id):
    data = load_data()
    for post in data.get("posts", []):
        if int(post.get("id", 0)) == int(post_id):
            return post
    return None


# =========================
# Permissions
# =========================

def user_id(user):
    return user.get("id") if user else None


def username_of(user):
    return normalize_username(user.get("username", "")) if user else ""


def is_owner_or_assistant(user):
    return user_id(user) in ADMIN_IDS or username_of(user) in ADMIN_USERNAMES


def is_assistant_only(user):
    return user_id(user) == ASSISTANT_OWNER_ID or username_of(user) == normalize_username(ASSISTANT_OWNER_USERNAME)


def is_allowed(user):
    data = load_data()
    uid = user_id(user)
    uname = username_of(user)

    if uid in data.get("banned_users", []):
        return False
    if uname and uname in data.get("banned_usernames", []):
        return False

    return (
        uid in data.get("allowed_users", [])
        or uname in ALLOWED_USERNAMES
        or uname in data.get("allowed_usernames", [])
    )


# =========================
# Keyboards
# =========================

def reply_keyboard(user):
    if is_owner_or_assistant(user):
        keyboard = [
            ["صنع منشور 📌", "تعديل منشور 📝"],
            ["منشوراتي 📁", "معاينة منشور 👁"],
            ["إرسال منشور 📤", "إدارة القنوات 📡"],
            ["إلغاء / رجوع ↩"],
        ]
    else:
        keyboard = [
            ["منشوراتي 📁", "معاينة منشور 👁"],
            ["إلغاء / رجوع ↩"],
        ]
    return {"keyboard": keyboard, "resize_keyboard": True}


def remove_keyboard():
    return {"remove_keyboard": True}


def group_menu():
    return {
        "inline_keyboard": [
            [
                {"text": "إضافة قنوات", "callback_data": "group_add_channels_help"},
                {"text": "إزالة قناة", "callback_data": "group_remove_channels_help"},
            ],
            [
                {"text": "إرسال منشور 📤", "callback_data": "group_send_post_help"},
                {"text": "معاينة منشور 👁", "callback_data": "group_preview_post_help"},
            ],
            [
                {"text": "اصنع منشور 📌", "url": RAZERESPECT_URL},
                {"text": "تعديل منشور 📝", "url": RAZERESPECT_URL},
            ],
        ]
    }


def denied_text(user):
    visitor = "زائر"
    if user:
        visitor = f"@{user.get('username')}" if user.get("username") else user.get("first_name", "زائر")
    return (
        f"اهلا بك يا {visitor}\n\n"
        "هذا البوت المسموح لهم فقط باستخدامه\n"
        "{ @x7vqz4 } { @OK_C7 }\n\n"
        "للتواصل مع المالك : @x7vqz4\n\n"
        "للتواصل مع مساعد المالك : @OK_C7\n"
        "الرجاء عدم التواصل الا للضرورة فقط\n\n"
        "إذا تحتاج شيء أو عندك شيء يفيدنا كلمنا"
    )


def denied_keyboard():
    return {
        "inline_keyboard": [
            [{"text": "شرح عن البوت 📘", "callback_data": "denied_info"}],
            [{"text": "التواصل مع المالك", "url": "https://t.me/x7vqz4"}],
            [{"text": "مساعد المالك", "url": "https://t.me/OK_C7"}],
        ]
    }


def admin_menu():
    return {
        "inline_keyboard": [
            [
                {"text": "📊 إحصائيات", "callback_data": "admin_stats"},
                {"text": "💾 التخزين", "callback_data": "admin_storage"},
            ],
            [
                {"text": "📢 القنوات", "callback_data": "admin_channels"},
                {"text": "🛠 إصلاح البيانات", "callback_data": "admin_fix"},
            ],
            [
                {"text": "🚫 حظر شخص", "callback_data": "admin_ban"},
                {"text": "✅ إزالة حظر", "callback_data": "admin_unban"},
            ],
        ]
    }


def admin_back():
    return {"inline_keyboard": [[{"text": "العودة لقائمة الأدمن ↩", "callback_data": "admin_home"}]]}


def sent_actions_keyboard(post_id):
    return {
        "inline_keyboard": [[
            {"text": "🗑 حذف منشور", "callback_data": f"sent_delete:{post_id}"},
            {"text": "🗑 حذف وارسال", "callback_data": f"sent_delete_resend:{post_id}"},
        ]]
    }


# =========================
# Post sending
# =========================

def post_keyboard(post):
    if not post.get("link") or not post.get("button_text"):
        return None
    return {"inline_keyboard": [[{"text": post["button_text"], "url": post["link"]}]]}


def build_post(message):
    if message.get("text") and not message.get("reply_to_message"):
        return {"content_type": "text", "text": message["text"], "top_text": message["text"]}

    source = message.get("reply_to_message") or message
    caption = message.get("caption") or source.get("caption") or message.get("text") or ""

    if source.get("photo"):
        return {"content_type": "photo", "file_id": source["photo"][-1]["file_id"], "top_text": caption}
    if source.get("video"):
        return {"content_type": "video", "file_id": source["video"]["file_id"], "top_text": caption}
    if source.get("audio"):
        return {"content_type": "audio", "file_id": source["audio"]["file_id"], "top_text": caption}
    if source.get("voice"):
        return {"content_type": "voice", "file_id": source["voice"]["file_id"], "top_text": caption}
    if source.get("document"):
        return {"content_type": "document", "file_id": source["document"]["file_id"], "top_text": caption}
    return None


def extract_url_button(message):
    # يقرأ زر الرابط إذا وصّلته تيليجرام داخل الرسالة.
    markup = message.get("reply_markup") or {}
    keyboard = markup.get("inline_keyboard") or []
    for row in keyboard:
        for button in row:
            text = button.get("text")
            url = button.get("url")
            if text and url:
                return str(text), str(url)
    return None, None


def message_has_url_button(message):
    button_text, link = extract_url_button(message)
    return bool(button_text and link)


def is_complete_auto_post_message(message):
    # الحفظ التلقائي فقط للرسالة الكاملة: محتوى + زر رابط.
    # الرسائل العادية مثل نجمة أو حرف أو صورة بدون زر ما تنحفظ.
    return bool(build_post(message) and message_has_url_button(message))


def save_new_post_from_message(message):
    post = build_post(message)
    if not post:
        return None, "ما قدرت أتعرف على المحتوى. ارسل نص أو صورة أو فيديو أو ملف."

    button_text, link = extract_url_button(message)
    if not button_text or not link:
        return None, "هذه ليست رسالة كاملة. ارسل المحتوى ثم نص الزر ثم الرابط بالطريقة العادية."

    post["button_text"] = button_text
    post["link"] = link
    post["sent_messages"] = {}

    d = load_data()
    post_id = allocate_post_id(d)
    post["id"] = post_id
    d["posts"].append(post)
    d["next_post_id"] = next_post_id_value(d)
    if not save_data(d):
        return None, "ما قدرت أحفظ المنشور لأن نظام الحماية منع حفظ غير آمن."
    return post_id, None


def send_post_to_chat(chat_id, post):
    markup = post_keyboard(post)
    caption = post.get("top_text", "")

    if post.get("content_type") == "text":
        return send_message(chat_id, post.get("text") or post.get("top_text") or "", markup)

    method_map = {
        "photo": ("sendPhoto", "photo"),
        "video": ("sendVideo", "video"),
        "audio": ("sendAudio", "audio"),
        "voice": ("sendVoice", "voice"),
        "document": ("sendDocument", "document"),
    }

    content_type = post.get("content_type")
    if content_type in method_map:
        method, field = method_map[content_type]
        payload = {"chat_id": chat_id, field: post.get("file_id"), "caption": caption}
        if markup:
            payload["reply_markup"] = markup
        return api(method, payload).get("result")

    return send_message(chat_id, "منشور غير معروف", markup)


def send_post_to_saved_channels(data, post):
    ok = 0
    failed = 0
    for chat in data.get("target_chats", []):
        try:
            sent = send_post_to_chat(chat.get("id"), post)
            post.setdefault("sent_messages", {})
            post["sent_messages"][str(chat.get("id"))] = sent["message_id"]
            ok += 1
        except Exception as e:
            print("send failed:", e, flush=True)
            failed += 1
    save_data(data)
    return ok, failed


def delete_sent_messages(data, post):
    deleted = 0
    for chat_id, message_id in list((post.get("sent_messages") or {}).items()):
        try:
            delete_message(int(chat_id), int(message_id))
            deleted += 1
        except Exception:
            pass
    post["sent_messages"] = {}
    save_data(data)
    return deleted


# =========================
# Admin text
# =========================

def admin_home_text():
    return (
        "قائمة أدمن مساعد المالك 👑\n\n"
        "هذه القائمة خاصة بـ @OK_C7 فقط.\n"
        "اختر من الأزرار تحت، وسيتم تحديث نفس الرسالة.\n\n"
        "للخروج اكتب /oadm"
    )


def admin_stats():
    data = load_data()
    ids = [int(p.get("id", 0)) for p in data.get("posts", [])]
    max_id = max(ids) if ids else 0
    return (
        f"إصدار البوت: {BOT_VERSION}\n\n"
        f"عدد المنشورات: {len(data.get('posts', []))}\n"
        f"أكبر رقم منشور: {max_id}\n"
        f"الرقم القادم: {next_post_id_value(data)}\n"
        f"عدد القنوات: {len(data.get('target_chats', []))}\n\n"
        "الحذف فقط عبر /d رقم_المنشور"
    )


def channels_text():
    data = load_data()
    if not data.get("target_chats"):
        return "القنوات المحفوظة:\n\nلا توجد قنوات.\n\nلإضافة قناة:\n/add @channelusername"
    text = "القنوات المحفوظة:\n\n"
    for i, chat in enumerate(data["target_chats"], start=1):
        text += f"{i}. {chat.get('title', 'بدون اسم')}\nID: {chat.get('id')}\n\n"
    return text


# =========================
# Allow/ban
# =========================

def parse_target(raw):
    raw = str(raw or "").strip()
    if raw.lstrip("-").isdigit():
        return "id", int(raw)
    return "username", normalize_username(raw)


def allow_target(raw):
    kind, value = parse_target(raw)
    data = load_data()
    if kind == "id":
        if value not in data["allowed_users"]:
            data["allowed_users"].append(value)
        if value in data["banned_users"]:
            data["banned_users"].remove(value)
        save_data(data)
        return f"تم السماح للمستخدم بالآيدي:\n{value}"
    if value not in data["allowed_usernames"]:
        data["allowed_usernames"].append(value)
    if value in data["banned_usernames"]:
        data["banned_usernames"].remove(value)
    save_data(data)
    return f"تم السماح للمستخدم باليوزر:\n@{value}"



def unallow_target(raw):
    kind, value = parse_target(raw)
    data = load_data()

    if kind == "id":
        if value in ADMIN_IDS:
            return "ما تقدر تشيل المالك أو مساعد المالك."
        if value in data.get("allowed_users", []):
            data["allowed_users"].remove(value)
            save_data(data)
            return f"تم حذف السماح للآيدي:\n{value}"
        return "هذا الآيدي غير موجود في المسموح لهم."

    if value in ADMIN_USERNAMES:
        return "ما تقدر تشيل المالك أو مساعد المالك."
    if value in data.get("allowed_usernames", []):
        data["allowed_usernames"].remove(value)
        save_data(data)
        return f"تم حذف السماح لليوزر:\n@{value}"
    return "هذا اليوزر غير موجود في المسموح لهم."


def ban_target(raw):
    kind, value = parse_target(raw)
    data = load_data()
    if kind == "id":
        if value in ADMIN_IDS:
            return "ما تقدر تحظر المالك أو مساعد المالك."
        if value not in data["banned_users"]:
            data["banned_users"].append(value)
        if value in data["allowed_users"]:
            data["allowed_users"].remove(value)
        save_data(data)
        return f"تم حظر المستخدم بالآيدي:\n{value}"
    if value in ADMIN_USERNAMES:
        return "ما تقدر تحظر المالك أو مساعد المالك."
    if value not in data["banned_usernames"]:
        data["banned_usernames"].append(value)
    save_data(data)
    return f"تم حظر المستخدم باليوزر:\n@{value}"


def unban_target(raw):
    kind, value = parse_target(raw)
    data = load_data()
    if kind == "id":
        if value in data["banned_users"]:
            data["banned_users"].remove(value)
            save_data(data)
            return f"تمت إزالة الحظر بالآيدي:\n{value}"
        return "هذا الآيدي غير محظور."
    if value in data["banned_usernames"]:
        data["banned_usernames"].remove(value)
        save_data(data)
        return f"تمت إزالة الحظر باليوزر:\n@{value}"
    return "هذا اليوزر غير محظور."


# =========================
# Commands
# =========================

def handle_command(message):
    chat = message["chat"]
    chat_id = chat["id"]
    chat_type = chat.get("type", "private")
    user = message.get("from", {})
    text = message.get("text", "")
    parts = text.split()
    cmd = parts[0].split("@")[0]
    args = parts[1:]

    if cmd == "/start":
        if not is_allowed(user):
            if chat_type in ("group", "supergroup"):
                return
            send_message(chat_id, denied_text(user), denied_keyboard())
            return

        if args and args[0] == "makepost":
            if not is_owner_or_assistant(user):
                send_message(chat_id, "هذا الإجراء للمالك أو مساعد المالك فقط.")
                return
            USER_STATE[str(user["id"])] = {"state": "create_content"}
            send_message(chat_id, "قم بارسال محتوى المنشور\nممكن ان يكون اي شيء\n(نص, 🖼 صورة, 🎥 فديو, 🎙 مقطع صوت. . . .)", reply_keyboard(user))
            return

        if args and args[0] == "editpost":
            if not is_owner_or_assistant(user):
                send_message(chat_id, "هذا الإجراء للمالك أو مساعد المالك فقط.")
                return
            USER_STATE[str(user["id"])] = {"state": "edit_number"}
            send_message(chat_id, "قم بارسال رقم المنشور الذي تريد تعديله.", reply_keyboard(user))
            return

        if chat_type in ("group", "supergroup"):
            send_message(chat_id, "كيف يمكنني مساعدتك؟", group_menu())
            return

        send_message(chat_id, "تم تنظيف الكيبورد القديم.", remove_keyboard())
        send_message(chat_id, f"اختر من القائمة:\n{BOT_VERSION}", reply_keyboard(user))
        return

    if cmd == "/clean":
        USER_STATE.pop(str(user.get("id")), None)
        send_message(chat_id, "تم تنظيف الكيبورد القديم. اكتب /start.", remove_keyboard())
        return

    if cmd == "/version":
        data = load_data()
        send_message(chat_id, f"إصدار البوت: {BOT_VERSION}\nملف التخزين:\n{DATA_FILE}\n\nعدد المنشورات: {len(data.get('posts', []))}\nالرقم القادم: {next_post_id_value(data)}")
        return

    if cmd == "/backup":
        if not is_owner_or_assistant(user):
            send_message(chat_id, "هذا الإجراء للمالك أو مساعد المالك فقط.")
            return
        data = load_data()
        save_data(data)
        send_message(chat_id, f"تم تجهيز نسخة احتياطية ✅\nالمنشورات: {len(data.get('posts', []))}\nملف التخزين:\n{DATA_FILE}\n\nملاحظة: خذ نسخة من OK_C7_STORAGE.json قبل أي تحديث لو ما عندك Persistent Disk.")
        return

    if cmd == "/myid":
        send_message(chat_id, f"آيديك: {user.get('id')}\nآيدي الشات: {chat_id}\nيوزرك: @{user.get('username', 'بدون')}")
        return

    if cmd == "/adm":
        if chat_type != "private":
            return
        if not is_owner_or_assistant(user):
            return
        send_message(chat_id, admin_home_text(), admin_menu())
        return

    if cmd == "/oadm":
        if not is_assistant_only(user):
            send_message(chat_id, "قائمة الأدمن خاصة بمساعد المالك فقط.")
            return
        USER_STATE.pop(str(user.get("id")), None)
        send_message(chat_id, "تم الخروج من قائمة الأدمن.", remove_keyboard())
        send_message(chat_id, "اختر من القائمة:", reply_keyboard(user))
        return

    if cmd in ("/allow", "/unallow", "/allowed", "/ban", "/unban"):
        if not is_owner_or_assistant(user):
            send_message(chat_id, "هذا الإجراء للمالك أو مساعد المالك فقط.")
            return
        if cmd == "/allowed":
            d = load_data()
            text = "المسموح لهم:\n\nبالآيدي:\n"
            text += "\n".join(str(x) for x in d.get("allowed_users", [])) or "لا يوجد"
            text += "\n\nباليوزر:\n"
            text += "\n".join("@" + x for x in d.get("allowed_usernames", [])) or "لا يوجد"
            send_message(chat_id, text)
            return
        if not args:
            send_message(chat_id, "اكتب آيدي أو يوزر بعد الأمر.")
            return
        if cmd == "/allow":
            send_message(chat_id, allow_target(args[0]))
        elif cmd == "/unallow":
            send_message(chat_id, unallow_target(args[0]))
        elif cmd == "/ban":
            send_message(chat_id, ban_target(args[0]))
        elif cmd == "/unban":
            send_message(chat_id, unban_target(args[0]))
        return

    if cmd == "/add":
        if not is_owner_or_assistant(user):
            send_message(chat_id, "هذا الإجراء للمالك أو مساعد المالك فقط.")
            return
        if not args:
            send_message(chat_id, "اكتب القناة.\n/add @channelusername")
            return
        try:
            c = get_chat(args[0])
            if c.get("type") in ("group", "supergroup"):
                send_message(chat_id, "إضافة القروبات معطلة. الإضافة للقنوات فقط.")
                return
            d = load_data()
            if not any(str(x.get("id")) == str(c["id"]) for x in d["target_chats"]):
                d["target_chats"].append({"id": c["id"], "title": c.get("title") or c.get("username") or str(c["id"]), "type": c.get("type")})
                save_data(d)
            send_message(chat_id, f"تمت إضافة القناة:\n{c.get('title') or c.get('username') or c['id']}")
        except Exception as e:
            send_message(chat_id, f"ما قدرت أضيف القناة.\nتأكد أن البوت مشرف فيها.\n{e}")
        return

    if cmd == "/del":
        if not is_owner_or_assistant(user):
            send_message(chat_id, "هذا الإجراء للمالك أو مساعد المالك فقط.")
            return
        if not args:
            send_message(chat_id, "اكتب آيدي القناة أو يوزرها.")
            return
        target = args[0]
        d = load_data()
        before = len(d["target_chats"])
        d["target_chats"] = [c for c in d["target_chats"] if str(c.get("id")) != target and normalize_username(c.get("title")) != normalize_username(target)]
        if len(d["target_chats"]) == before:
            send_message(chat_id, "ما لقيت قناة بهذا المعرف.")
            return
        save_data(d)
        send_message(chat_id, "تم حذف القناة من القائمة.")
        return

    if cmd == "/chats":
        if not is_owner_or_assistant(user):
            send_message(chat_id, "هذا الإجراء للمالك أو مساعد المالك فقط.")
            return
        send_message(chat_id, channels_text())
        return

    if cmd == "/p":
        if not is_allowed(user):
            if chat_type in ("group", "supergroup"):
                return
            send_message(chat_id, denied_text(user), denied_keyboard())
            return
        if not args or not args[0].isdigit():
            send_message(chat_id, "اكتب رقم المنشور.\n/p 1")
            return
        post = find_post(int(args[0]))
        if not post:
            send_message(chat_id, "ما لقيت منشور بهذا الرقم.")
            return
        send_post_to_chat(chat_id, post)
        return

    if cmd == "/s":
        if chat_type not in ("group", "supergroup"):
            send_message(chat_id, "الإرسال للقنوات يكون من قروب التحكم فقط.")
            return
        if not is_owner_or_assistant(user):
            send_message(chat_id, "هذا الإجراء للمالك أو مساعد المالك فقط.")
            return
        if not args or not args[0].isdigit():
            send_message(chat_id, "اكتب رقم المنشور.\n/s 1")
            return
        post_id = int(args[0])
        d = load_data()
        post = next((p for p in d["posts"] if int(p.get("id", 0)) == post_id), None)
        if not post:
            send_message(chat_id, "ما لقيت منشور بهذا الرقم.")
            return
        if not d["target_chats"]:
            send_message(chat_id, "ما فيه قنوات محفوظة.\nأضف قناة بـ /add @channelusername")
            return

        if post.get("sent_messages"):
            send_message(
                chat_id,
                "هذا المنشور مرسل مسبقًا في القنوات.\n"
                "لتجنب التكرار اختر حذف وارسال، أو احذف النسخة المنشورة فقط.",
                sent_actions_keyboard(post_id)
            )
            return

        ok, failed = send_post_to_saved_channels(d, post)
        send_message(chat_id, f"تم الإرسال.\nنجح: {ok}\nفشل: {failed}", sent_actions_keyboard(post_id))
        return

    if cmd == "/d":
        global DELETE_OPERATION_ACTIVE
        if not is_owner_or_assistant(user):
            send_message(chat_id, "هذا الإجراء للمالك أو مساعد المالك فقط.")
            return
        if not args or not args[0].isdigit():
            send_message(chat_id, "اكتب رقم المنشور.\n/d 1")
            return
        post_id = int(args[0])
        d = load_data()
        before = len(d["posts"])
        d["posts"] = [p for p in d["posts"] if int(p.get("id", 0)) != post_id]
        if len(d["posts"]) == before:
            send_message(chat_id, "ما لقيت منشور بهذا الرقم.")
            return
        d["next_post_id"] = next_post_id_value(d)
        DELETE_OPERATION_ACTIVE = True
        try:
            save_data(d)
        finally:
            DELETE_OPERATION_ACTIVE = False
        send_message(chat_id, f"تم حذف المنشور رقم {post_id}.\nالأرقام القديمة لا تتغير، والرقم القادم: {d['next_post_id']}")
        return


# =========================
# Callbacks
# =========================

def handle_callback(query):
    qid = query["id"]
    msg = query["message"]
    chat = msg["chat"]
    chat_id = chat["id"]
    message_id = msg["message_id"]
    user = query.get("from", {})
    data = query.get("data", "")
    answer_callback_query(qid)

    if data == "denied_info":
        edit_message_text(chat_id, message_id, "شرح عن البوت 📘\n\nهذا البوت مخصص لصنع منشورات تحتوي على محتوى وزر رابط، ثم إرسالها للقنوات المحفوظة.\n\nصانع البوت: @OK_C7", {"inline_keyboard": [[{"text": "العودة للوراء ↩", "callback_data": "denied_back"}]]})
        return
    if data == "denied_back":
        edit_message_text(chat_id, message_id, denied_text(user), denied_keyboard())
        return

    if data.startswith("admin_"):
        if not is_assistant_only(user):
            answer_callback_query(qid, "قائمة الأدمن خاصة بمساعد المالك فقط.", True)
            return
        if data == "admin_home":
            edit_message_text(chat_id, message_id, admin_home_text(), admin_menu())
        elif data == "admin_stats":
            edit_message_text(chat_id, message_id, admin_stats(), admin_back())
        elif data == "admin_storage":
            edit_message_text(chat_id, message_id, f"ملف التخزين:\n{DATA_FILE}", admin_back())
        elif data == "admin_channels":
            edit_message_text(chat_id, message_id, channels_text(), admin_back())
        elif data == "admin_fix":
            d = load_data()
            d["next_post_id"] = next_post_id_value(d)
            save_data(d)
            edit_message_text(chat_id, message_id, f"تم تثبيت الترقيم بدون حذف أو تغيير أرقام المنشورات.\nالرقم القادم: {d['next_post_id']}", admin_back())
        elif data == "admin_ban":
            USER_STATE[str(user["id"])] = {"state": "ban_username"}
            edit_message_text(chat_id, message_id, "حظر شخص من البوت 🚫\n\nارسل يوزر الشخص الآن فقط.\nمثال:\n@username", admin_back())
        elif data == "admin_unban":
            USER_STATE[str(user["id"])] = {"state": "unban_username"}
            edit_message_text(chat_id, message_id, "إزالة حظر شخص ✅\n\nارسل يوزر الشخص الآن فقط.\nمثال:\n@username", admin_back())
        return

    if data.startswith("sent_delete:") or data.startswith("sent_delete_resend:"):
        if not is_owner_or_assistant(user):
            answer_callback_query(qid, "هذا الإجراء للمالك أو مساعد المالك فقط.", True)
            return
        try:
            post_id = int(data.split(":")[1])
        except Exception:
            send_message(chat_id, "رقم المنشور غير صحيح.")
            return
        d = load_data()
        post = next((p for p in d["posts"] if int(p.get("id", 0)) == post_id), None)
        if not post:
            send_message(chat_id, "ما لقيت منشور بهذا الرقم.")
            return
        deleted = delete_sent_messages(d, post)
        if data.startswith("sent_delete_resend:"):
            ok, failed = send_post_to_saved_channels(d, post)
            edit_message_text(chat_id, message_id, f"تم حذف القديم وإعادة الإرسال.\nالمحذوف: {deleted}\nنجح: {ok}\nفشل: {failed}", sent_actions_keyboard(post_id))
        else:
            edit_message_text(chat_id, message_id, f"تم حذف الرسائل المنشورة من القنوات.\nالمحذوف: {deleted}\n\nالمنشور المحفوظ لم يتم حذفه. الحذف النهائي فقط بـ /d {post_id}")
        return

    if not is_allowed(user):
        return

    if data == "group_add_channels_help":
        send_message(chat_id, "لإضافة قناة:\n/add @channelusername\n\nلازم البوت يكون مشرف في القناة.")
    elif data == "group_remove_channels_help":
        send_message(chat_id, "لحذف قناة:\n/del CHAT_ID\n\nلعرض القنوات:\n/chats")
    elif data == "group_send_post_help":
        send_message(chat_id, "لإرسال منشور:\n/s رقم_المنشور\n\nمثال:\n/s 1")
    elif data == "group_preview_post_help":
        send_message(chat_id, "لمعاينة منشور:\n/p رقم_المنشور\n\nمثال:\n/p 1")


# =========================
# Normal messages
# =========================

def handle_message(message):
    if "text" in message and message["text"].startswith("/"):
        handle_command(message)
        return

    chat = message["chat"]
    chat_id = chat["id"]
    chat_type = chat.get("type", "private")
    user = message.get("from", {})
    text = (message.get("text") or "").strip()
    uid = str(user.get("id"))

    if not is_allowed(user):
        return

    if text in ("إلغاء / رجوع ↩", "الرجوع للقائمة الرئيسية ↩", "القائمة الرئيسية ↩"):
        USER_STATE.pop(uid, None)
        send_message(chat_id, "تم الرجوع للقائمة الرئيسية.", remove_keyboard())
        send_message(chat_id, "اختر من القائمة:", reply_keyboard(user))
        return

    state = USER_STATE.get(uid, {}).get("state")

    if state == "ban_username":
        result = ban_target(text)
        USER_STATE.pop(uid, None)
        send_message(chat_id, result, reply_keyboard(user))
        return

    if state == "unban_username":
        result = unban_target(text)
        USER_STATE.pop(uid, None)
        send_message(chat_id, result, reply_keyboard(user))
        return

    if state is None and is_owner_or_assistant(user) and is_complete_auto_post_message(message):
        post_id, error = save_new_post_from_message(message)
        if error:
            send_message(chat_id, error, reply_keyboard(user))
            return
        send_message(chat_id, f"تم حفظ المنشور الكامل تلقائيًا ✅\nرقم المنشور: {post_id}", reply_keyboard(user))
        return

    if state == "create_content":
        if not is_owner_or_assistant(user):
            send_message(chat_id, "هذا الإجراء للمالك أو مساعد المالك فقط.")
            return
        if is_complete_auto_post_message(message):
            post_id, error = save_new_post_from_message(message)
            USER_STATE.pop(uid, None)
            if error:
                send_message(chat_id, error, reply_keyboard(user))
                return
            send_message(chat_id, f"تم حفظ المنشور الكامل تلقائيًا ✅\nرقم المنشور: {post_id}", reply_keyboard(user))
            return
        post = build_post(message)
        if not post:
            send_message(chat_id, "ما قدرت أتعرف على المحتوى. ارسل نص أو صورة أو فيديو أو ملف.")
            return
        USER_STATE[uid] = {"state": "create_button", "post": post}
        send_message(chat_id, "ارسل نص الزر:")
        return

    if state == "create_button":
        st = USER_STATE[uid]
        st["post"]["button_text"] = text
        st["state"] = "create_link"
        send_message(chat_id, "ارسل الرابط:")
        return

    if state == "create_link":
        if not text.startswith(("http://", "https://")):
            send_message(chat_id, "الرابط لازم يبدأ بـ http أو https")
            return
        d = load_data()
        post_id = allocate_post_id(d)
        post = USER_STATE[uid]["post"]
        post["id"] = post_id
        post["link"] = text
        post["sent_messages"] = {}
        d["posts"].append(post)
        d["next_post_id"] = next_post_id_value(d)
        save_data(d)
        USER_STATE.pop(uid, None)
        send_message(chat_id, f"تم حفظ المنشور تلقائيًا ✅\nرقم المنشور: {post_id}", reply_keyboard(user))
        return

    if state == "edit_number":
        if not text.isdigit():
            send_message(chat_id, "ارسل رقم منشور صحيح.")
            return
        post_id = int(text)
        if not find_post(post_id):
            send_message(chat_id, "ما لقيت منشور بهذا الرقم.")
            return
        USER_STATE[uid] = {"state": "edit_content", "edit_post_id": post_id}
        send_message(chat_id, "ارسل محتوى المنشور الجديد:")
        return

    if state == "edit_content":
        post = build_post(message)
        if not post:
            send_message(chat_id, "ارسل محتوى صحيح.")
            return
        USER_STATE[uid]["post"] = post
        USER_STATE[uid]["state"] = "edit_button"
        send_message(chat_id, "ارسل نص الزر:")
        return

    if state == "edit_button":
        USER_STATE[uid]["post"]["button_text"] = text
        USER_STATE[uid]["state"] = "edit_link"
        send_message(chat_id, "ارسل الرابط:")
        return

    if state == "edit_link":
        if not text.startswith(("http://", "https://")):
            send_message(chat_id, "الرابط لازم يبدأ بـ http أو https")
            return
        d = load_data()
        post_id = USER_STATE[uid]["edit_post_id"]
        for i, p in enumerate(d["posts"]):
            if int(p.get("id", 0)) == int(post_id):
                new_post = USER_STATE[uid]["post"]
                new_post["id"] = post_id
                new_post["link"] = text
                new_post["sent_messages"] = p.get("sent_messages", {})
                d["posts"][i] = new_post
                save_data(d)
                USER_STATE.pop(uid, None)
                send_message(chat_id, f"تم تعديل المنشور رقم {post_id} ✅", reply_keyboard(user))
                return
        USER_STATE.pop(uid, None)
        send_message(chat_id, "ما لقيت المنشور.")
        return

    # keyboard commands
    if text == "صنع منشور 📌":
        if not is_owner_or_assistant(user):
            send_message(chat_id, "هذا الإجراء للمالك أو مساعد المالك فقط.")
            return
        USER_STATE[uid] = {"state": "create_content"}
        send_message(chat_id, "قم بارسال محتوى المنشور\nممكن ان يكون اي شيء\n(نص, 🖼 صورة, 🎥 فديو, 🎙 مقطع صوت. . . .)")
        return

    if text == "تعديل منشور 📝":
        if not is_owner_or_assistant(user):
            send_message(chat_id, "هذا الإجراء للمالك أو مساعد المالك فقط.")
            return
        USER_STATE[uid] = {"state": "edit_number"}
        send_message(chat_id, "قم بارسال رقم المنشور الذي تريد تعديله.")
        return

    if text == "منشوراتي 📁":
        d = load_data()
        if not d["posts"]:
            send_message(chat_id, "ما فيه منشورات محفوظة.")
            return
        out = "المنشورات المحفوظة:\n\n"
        for p in d["posts"]:
            out += f"رقم المنشور: {p.get('id')}\nمعاينة: /p {p.get('id')}\nإرسال: /s {p.get('id')}\nحذف: /d {p.get('id')}\n\n"
        send_message(chat_id, out)
        return

    if text == "معاينة منشور 👁":
        send_message(chat_id, "لمعاينة منشور اكتب:\n/p رقم_المنشور")
        return

    if text == "إرسال منشور 📤":
        if not is_owner_or_assistant(user):
            send_message(chat_id, "هذا الإجراء للمالك أو مساعد المالك فقط.")
            return
        send_message(chat_id, "لإرسال منشور اكتب من قروب التحكم:\n/s رقم_المنشور")
        return

    if text == "إدارة القنوات 📡":
        if not is_owner_or_assistant(user):
            send_message(chat_id, "هذا الإجراء للمالك أو مساعد المالك فقط.")
            return
        send_message(chat_id, "إدارة القنوات:\n/add @channelusername\n/del CHAT_ID\n/chats")
        return

    # ساكت على الرسائل العشوائية
    return


# =========================
# Update deduplication
# =========================

def mark_update_seen(update_id):
    """يمنع تنفيذ نفس تحديث تيليجرام مرتين إذا صار تداخل Deploy أو تشغيل نسختين."""
    try:
        d = load_data()
        seen = d.get("processed_update_ids", [])
        try:
            update_id = int(update_id)
        except Exception:
            return True
        if update_id in seen:
            print(f"Skipped duplicate update {update_id}", flush=True)
            return False
        seen.append(update_id)
        d["processed_update_ids"] = seen[-300:]
        save_data(d)
        return True
    except Exception as e:
        print("mark_update_seen failed:", e, flush=True)
        return True

# =========================
# Render health server
# =========================

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        body = f"OK {BOT_VERSION}\nStorage: {DATA_FILE}\n".encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        return


def start_health_server():
    port = int(os.environ.get("PORT", "10000"))
    def run():
        try:
            server = HTTPServer(("0.0.0.0", port), HealthHandler)
            print(f"Health server running on port {port}", flush=True)
            server.serve_forever()
        except Exception as e:
            print("Health server error:", e, flush=True)
    threading.Thread(target=run, daemon=True).start()

# =========================
# Main loop
# =========================

def main():
    ensure_storage_location()
    start_health_server()
    print(f"Starting {BOT_VERSION}", flush=True)
    print(f"Storage: {DATA_FILE}", flush=True)
    remove_webhook()
    offset = None
    while True:
        try:
            updates = get_updates(offset)
            for update in updates:
                offset = update["update_id"] + 1
                if not mark_update_seen(update.get("update_id")):
                    continue
                if "message" in update:
                    handle_message(update["message"])
                elif "callback_query" in update:
                    handle_callback(update["callback_query"])
        except KeyboardInterrupt:
            print("Stopped.", flush=True)
            break
        except Exception as e:
            print("Loop error:", repr(e), flush=True)
            time.sleep(3)


if __name__ == "__main__":
    main()
