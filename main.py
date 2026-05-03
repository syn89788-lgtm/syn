import os
import json
import time
import traceback
import shutil
import tempfile
import threading
from flask import Flask
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STORAGE_FILE = os.path.join(BASE_DIR, "OK_C7_STORAGE.json")
DATA_FILE = Path(STORAGE_FILE)

BACKUP_DIR = Path(BASE_DIR) / "OK_C7_BACKUPS"
BACKUP_DIR.mkdir(exist_ok=True)

HOME_MIRROR_DIR = Path.home() / ".ok_c7_safe_storage"
HOME_MIRROR_DIR.mkdir(exist_ok=True)
HOME_MIRROR_FILE = HOME_MIRROR_DIR / "OK_C7_STORAGE.json"

# main.py
# OK_C7 Telegram Bot - stable storage version
# Requires: python-telegram-bot==21.6


from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

# =========================
# CONFIG
# =========================

BOT_TOKEN = "7561000853:AAEkTorXtiQxgB9aHSegWcbVWD_yHnbhO_s"
BOT_VERSION = "OK_C7_PATH_FIX_V17"

OWNER_ID = 6507166349
ASSISTANT_OWNER_ID = 8410176147
THIRD_ALLOWED_ID = 5723931989

OWNER_USERNAME = "x7vqz4"
ASSISTANT_OWNER_USERNAME = "OK_C7"
THIRD_ALLOWED_USERNAME = "rzzqr"

RAZERESPECT_URL = "https://t.me/RAZERESPECTBOT"

ADMIN_IDS = {OWNER_ID, ASSISTANT_OWNER_ID}
ADMIN_USERNAMES = {OWNER_USERNAME.lower(), ASSISTANT_OWNER_USERNAME.lower()}

ALLOWED_USER_IDS = {OWNER_ID, ASSISTANT_OWNER_ID, THIRD_ALLOWED_ID}
ALLOWED_USERNAMES = {
    OWNER_USERNAME.lower(),
    ASSISTANT_OWNER_USERNAME.lower(),
    THIRD_ALLOWED_USERNAME.lower(),
}



DELETE_OPERATION_ACTIVE = False


# =========================
# DATA STORAGE
# =========================

def normalize_username(username: str) -> str:
    return str(username or "").strip().lower().lstrip("@")


def default_data() -> Dict[str, Any]:
    return {
        "allowed_users": sorted(ALLOWED_USER_IDS),
        "allowed_usernames": sorted(ALLOWED_USERNAMES),
        "banned_users": [],
        "banned_usernames": [],
        "posts": [],
        "next_post_id": 1,
        "target_chats": [],
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "updated_at": datetime.now().isoformat(timespec="seconds"),
    }


def normalize_data(data: Any) -> Dict[str, Any]:
    if not isinstance(data, dict):
        data = default_data()

    data.setdefault("allowed_users", sorted(ALLOWED_USER_IDS))
    data.setdefault("allowed_usernames", sorted(ALLOWED_USERNAMES))
    data.setdefault("banned_users", [])
    data.setdefault("banned_usernames", [])
    data.setdefault("posts", [])
    data.setdefault("next_post_id", 1)
    data.setdefault("target_chats", [])
    data.setdefault("created_at", datetime.now().isoformat(timespec="seconds"))
    data["updated_at"] = datetime.now().isoformat(timespec="seconds")

    for uid in ALLOWED_USER_IDS:
        if uid not in data["allowed_users"]:
            data["allowed_users"].append(uid)

    names = {normalize_username(x) for x in data.get("allowed_usernames", []) if normalize_username(x)}
    names |= ALLOWED_USERNAMES
    data["allowed_usernames"] = sorted(names)

    data["banned_usernames"] = sorted({
        normalize_username(x)
        for x in data.get("banned_usernames", [])
        if normalize_username(x)
    })

    clean_posts = []
    max_id = 0
    for index, post in enumerate(data.get("posts", []), start=1):
        if not isinstance(post, dict):
            continue
        try:
            post["id"] = int(post.get("id", index))
        except Exception:
            post["id"] = index

        post.setdefault("sent_messages", {})
        if not isinstance(post["sent_messages"], dict):
            post["sent_messages"] = {}

        post.setdefault("content_type", post.get("type", "text"))
        if "caption" in post and "top_text" not in post:
            post["top_text"] = post.get("caption", "")

        max_id = max(max_id, int(post["id"]))
        clean_posts.append(post)

    data["posts"] = clean_posts

    try:
        current_next = int(data.get("next_post_id", 1) or 1)
    except Exception:
        current_next = 1
    data["next_post_id"] = max(current_next, max_id + 1 if max_id else 1)

    clean_chats = []
    seen = set()
    for chat in data.get("target_chats", []):
        if not isinstance(chat, dict):
            continue
        chat_id = chat.get("id")
        if chat_id is None or str(chat_id) in seen:
            continue
        seen.add(str(chat_id))
        clean_chats.append({
            "id": chat_id,
            "title": chat.get("title") or chat.get("username") or str(chat_id),
            "type": chat.get("type") or "channel",
        })
    data["target_chats"] = clean_chats

    return data


def read_storage_file(path: Path) -> Optional[Dict[str, Any]]:
    try:
        if not path.exists():
            return None
        with path.open("r", encoding="utf-8") as f:
            return normalize_data(json.load(f))
    except Exception as exc:
        print(f"[storage] failed to read {path}: {exc}", flush=True)
        return None


def storage_candidates():
    candidates = [
        DATA_FILE,
        Path(BASE_DIR) / "OK_C7_STORAGE.json",
        Path.cwd() / "OK_C7_STORAGE.json",
        HOME_MIRROR_FILE,
        Path.home() / ".ok_c7_clean_py_bot" / "OK_C7_STORAGE.json",
        Path.home() / ".ok_c7_list_bot" / "OK_C7_STORAGE.json",
        Path.home() / ".ok_c7_js_list_bot" / "OK_C7_STORAGE.json",
        BACKUP_DIR / "OK_C7_STORAGE.latest.json",
    ]
    candidates += sorted(BACKUP_DIR.glob("OK_C7_STORAGE_*.json"), reverse=True)

    unique = []
    seen = set()
    for path in candidates:
        path = Path(path)
        key = str(path.resolve()) if path.exists() else str(path)
        if key not in seen:
            unique.append(path)
            seen.add(key)
    return unique


def find_best_storage() -> Tuple[Optional[Dict[str, Any]], Optional[Path], int]:
    best_data = None
    best_path = None
    best_count = -1

    for path in storage_candidates():
        data = read_storage_file(path)
        if data is None:
            continue
        count = len(data.get("posts", []))
        if count > best_count:
            best_data = data
            best_path = path
            best_count = count

    if best_data is not None:
        print(f"[storage] best candidate: {best_path} posts={best_count}", flush=True)
    return best_data, best_path, best_count


def write_json_atomic(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=path.name, suffix=".tmp", dir=str(path.parent))
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        tmp_path.replace(path)
    finally:
        try:
            if tmp_path.exists():
                tmp_path.unlink()
        except Exception:
            pass


def post_count_from_file(path: Path) -> int:
    data = read_storage_file(path)
    if data is None:
        return 0
    return len(data.get("posts", []))


def backup_storage_before_write() -> None:
    if not DATA_FILE.exists():
        return
    try:
        current = read_storage_file(DATA_FILE)
        if current is None:
            return
        count = len(current.get("posts", []))
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = BACKUP_DIR / f"OK_C7_STORAGE_{stamp}_{count}posts.json"
        shutil.copy2(DATA_FILE, backup_path)
        shutil.copy2(DATA_FILE, BACKUP_DIR / "OK_C7_STORAGE.latest.json")
    except Exception as exc:
        print(f"[storage] backup failed: {exc}", flush=True)


def mirror_storage(data: Dict[str, Any]) -> None:
    for path in [HOME_MIRROR_FILE, BACKUP_DIR / "OK_C7_STORAGE.latest.json"]:
        try:
            write_json_atomic(path, data)
        except Exception as exc:
            print(f"[storage] mirror failed {path}: {exc}", flush=True)


def save_data(data: Dict[str, Any], allow_post_count_decrease: bool = False) -> bool:
    global DELETE_OPERATION_ACTIVE
    data = normalize_data(data)

    old_count = post_count_from_file(DATA_FILE)
    new_count = len(data.get("posts", []))

    if old_count > 0 and new_count < old_count and not (DELETE_OPERATION_ACTIVE or allow_post_count_decrease):
        print(f"[storage] blocked unsafe save old={old_count} new={new_count}", flush=True)
        return False

    backup_storage_before_write()
    write_json_atomic(DATA_FILE, data)
    mirror_storage(data)
    return True


def load_data() -> Dict[str, Any]:
    primary = read_storage_file(DATA_FILE)
    best_data, best_path, best_count = find_best_storage()

    if primary is None:
        if best_data is not None:
            write_json_atomic(DATA_FILE, best_data)
            mirror_storage(best_data)
            print(f"[storage] recovered into {DATA_FILE} from {best_path}", flush=True)
            return best_data
        data = default_data()
        save_data(data)
        return data

    primary_count = len(primary.get("posts", []))
    if best_data is not None and best_count > primary_count:
        write_json_atomic(DATA_FILE, best_data)
        mirror_storage(best_data)
        print(f"[storage] restored richer storage: {best_count}>{primary_count} from {best_path}", flush=True)
        return best_data

    return primary


def next_available_post_id(data: Dict[str, Any]) -> int:
    used = set()
    for post in data.get("posts", []):
        try:
            used.add(int(post.get("id")))
        except Exception:
            pass
    pid = 1
    while pid in used:
        pid += 1
    return pid


def find_post(data: Dict[str, Any], post_id: int) -> Optional[Dict[str, Any]]:
    for post in data.get("posts", []):
        try:
            if int(post.get("id")) == int(post_id):
                return post
        except Exception:
            pass
    return None


# =========================
# PERMISSIONS
# =========================

def user_id(user) -> Optional[int]:
    if not user:
        return None
    try:
        return int(user.id)
    except Exception:
        return None


def username_of(user) -> str:
    if not user:
        return ""
    return normalize_username(getattr(user, "username", ""))


def is_admin(user) -> bool:
    return user_id(user) in ADMIN_IDS or username_of(user) in ADMIN_USERNAMES


def is_assistant_owner(user) -> bool:
    return user_id(user) == ASSISTANT_OWNER_ID or username_of(user) == normalize_username(ASSISTANT_OWNER_USERNAME)


def is_allowed(user) -> bool:
    if not user:
        return False

    data = load_data()
    uid = user_id(user)
    uname = username_of(user)

    banned_ids = set()
    for item in data.get("banned_users", []):
        try:
            banned_ids.add(int(item))
        except Exception:
            pass

    if uid in banned_ids:
        return False
    if uname and uname in data.get("banned_usernames", []):
        return False

    return (
        uid in data.get("allowed_users", [])
        or uname in data.get("allowed_usernames", [])
        or uname in ALLOWED_USERNAMES
    )


# =========================
# KEYBOARDS
# =========================

def reply_keyboard(user):
    if is_admin(user):
        keyboard = [
            [KeyboardButton("صنع منشور 📌"), KeyboardButton("تعديل منشور 📝")],
            [KeyboardButton("منشوراتي 📁"), KeyboardButton("معاينة منشور 👁")],
            [KeyboardButton("إرسال منشور 📤"), KeyboardButton("إدارة القنوات 📡")],
            [KeyboardButton("إلغاء / رجوع ↩")],
        ]
    else:
        keyboard = [
            [KeyboardButton("منشوراتي 📁"), KeyboardButton("معاينة منشور 👁")],
            [KeyboardButton("إلغاء / رجوع ↩")],
        ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)


def denied_text(user) -> str:
    visitor = f"@{user.username}" if getattr(user, "username", None) else (getattr(user, "first_name", "زائر") or "زائر")
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
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("شرح عن البوت 📘", callback_data="denied_info")],
        [InlineKeyboardButton("التواصل مع المالك", url="https://t.me/x7vqz4")],
        [InlineKeyboardButton("مساعد المالك", url="https://t.me/OK_C7")],
    ])


def group_menu():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("إضافة قنوات", callback_data="group_add_channels_help"),
            InlineKeyboardButton("إزالة قناة", callback_data="group_remove_channels_help"),
        ],
        [
            InlineKeyboardButton("إرسال منشور 📤", callback_data="group_send_post_help"),
            InlineKeyboardButton("معاينة منشور 👁", callback_data="group_preview_post_help"),
        ],
        [
            InlineKeyboardButton("صنع منشور 📌", url=RAZERESPECT_URL),
            InlineKeyboardButton("تعديل منشور 📝", url=RAZERESPECT_URL),
        ],
    ])


def admin_menu():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📊 إحصائيات", callback_data="admin_stats"),
            InlineKeyboardButton("💾 التخزين", callback_data="admin_storage"),
        ],
        [
            InlineKeyboardButton("📢 القنوات", callback_data="admin_channels"),
            InlineKeyboardButton("🛠 إصلاح البيانات", callback_data="admin_fix"),
        ],
        [
            InlineKeyboardButton("🚫 حظر شخص", callback_data="admin_ban"),
            InlineKeyboardButton("✅ إزالة حظر", callback_data="admin_unban"),
        ],
    ])


def admin_back():
    return InlineKeyboardMarkup([[InlineKeyboardButton("العودة لقائمة الأدمن ↩", callback_data="admin_home")]])


def sent_buttons(post_id: int):
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("🗑 حذف منشور", callback_data=f"sent_delete:{post_id}"),
        InlineKeyboardButton("🗑 حذف وارسال", callback_data=f"sent_delete_resend:{post_id}"),
    ]])


def post_keyboard(post: Dict[str, Any]):
    if not post.get("button_text") or not post.get("link"):
        return None
    return InlineKeyboardMarkup([[InlineKeyboardButton(post["button_text"], url=post["link"])]])


# =========================
# POST HELPERS
# =========================

def build_post(message) -> Optional[Dict[str, Any]]:
    if message.text and not message.reply_to_message:
        return {
            "content_type": "text",
            "text": message.text,
            "top_text": message.text,
        }

    source = message.reply_to_message or message
    caption = message.caption or getattr(source, "caption", None) or ""

    if source.photo:
        return {"content_type": "photo", "file_id": source.photo[-1].file_id, "top_text": caption}
    if source.video:
        return {"content_type": "video", "file_id": source.video.file_id, "top_text": caption}
    if source.document:
        return {"content_type": "document", "file_id": source.document.file_id, "top_text": caption}
    if source.audio:
        return {"content_type": "audio", "file_id": source.audio.file_id, "top_text": caption}
    if source.voice:
        return {"content_type": "voice", "file_id": source.voice.file_id, "top_text": caption}

    return None


async def send_post_to_chat(bot, chat_id, post: Dict[str, Any]):
    keyboard = post_keyboard(post)
    caption = post.get("top_text") or post.get("caption") or ""

    ctype = post.get("content_type") or post.get("type")

    if ctype == "text":
        return await bot.send_message(chat_id=chat_id, text=post.get("text") or caption or "", reply_markup=keyboard)
    if ctype == "photo":
        return await bot.send_photo(chat_id=chat_id, photo=post["file_id"], caption=caption, reply_markup=keyboard)
    if ctype == "video":
        return await bot.send_video(chat_id=chat_id, video=post["file_id"], caption=caption, reply_markup=keyboard)
    if ctype == "document":
        return await bot.send_document(chat_id=chat_id, document=post["file_id"], caption=caption, reply_markup=keyboard)
    if ctype == "audio":
        return await bot.send_audio(chat_id=chat_id, audio=post["file_id"], caption=caption, reply_markup=keyboard)
    if ctype == "voice":
        return await bot.send_voice(chat_id=chat_id, voice=post["file_id"], caption=caption, reply_markup=keyboard)

    return await bot.send_message(chat_id=chat_id, text="منشور غير معروف", reply_markup=keyboard)


async def send_to_channels(context: ContextTypes.DEFAULT_TYPE, data: Dict[str, Any], post: Dict[str, Any]) -> Tuple[int, int]:
    ok = 0
    failed = 0
    for chat in data.get("target_chats", []):
        try:
            sent = await send_post_to_chat(context.bot, chat["id"], post)
            post.setdefault("sent_messages", {})
            post["sent_messages"][str(chat["id"])] = sent.message_id
            ok += 1
        except Exception as exc:
            print(f"[send] failed to {chat}: {exc}", flush=True)
            failed += 1
    save_data(data)
    return ok, failed


async def delete_sent_messages(context: ContextTypes.DEFAULT_TYPE, data: Dict[str, Any], post: Dict[str, Any]) -> int:
    deleted = 0
    for chat_id, message_id in list((post.get("sent_messages") or {}).items()):
        try:
            await context.bot.delete_message(chat_id=int(chat_id), message_id=int(message_id))
            deleted += 1
        except Exception:
            pass
    post["sent_messages"] = {}
    save_data(data)
    return deleted


# =========================
# ALLOW / BAN
# =========================

def parse_target(raw: str):
    raw = str(raw or "").strip()
    if raw.lstrip("-").isdigit():
        return "id", int(raw)
    return "username", normalize_username(raw)


def allow_target(raw: str) -> str:
    kind, value = parse_target(raw)
    data = load_data()
    if kind == "id":
        if value not in data["allowed_users"]:
            data["allowed_users"].append(value)
        if value in data.get("banned_users", []):
            data["banned_users"].remove(value)
        save_data(data)
        return f"تم السماح للمستخدم بالآيدي:\n{value}"

    if value not in data["allowed_usernames"]:
        data["allowed_usernames"].append(value)
    if value in data.get("banned_usernames", []):
        data["banned_usernames"].remove(value)
    save_data(data)
    return f"تم السماح للمستخدم باليوزر:\n@{value}"


def unallow_target(raw: str) -> str:
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


def ban_target(raw: str) -> str:
    kind, value = parse_target(raw)
    data = load_data()
    if kind == "id":
        if value in ADMIN_IDS:
            return "ما تقدر تحظر المالك أو مساعد المالك."
        if value not in data["banned_users"]:
            data["banned_users"].append(value)
        if value in data.get("allowed_users", []):
            data["allowed_users"].remove(value)
        save_data(data)
        return f"تم حظر المستخدم بالآيدي:\n{value}"

    if value in ADMIN_USERNAMES:
        return "ما تقدر تحظر المالك أو مساعد المالك."
    if value not in data["banned_usernames"]:
        data["banned_usernames"].append(value)
    save_data(data)
    return f"تم حظر المستخدم باليوزر:\n@{value}"


def unban_target(raw: str) -> str:
    kind, value = parse_target(raw)
    data = load_data()
    if kind == "id":
        if value in data.get("banned_users", []):
            data["banned_users"].remove(value)
            save_data(data)
            return f"تمت إزالة الحظر بالآيدي:\n{value}"
        return "هذا الآيدي غير محظور."

    if value in data.get("banned_usernames", []):
        data["banned_usernames"].remove(value)
        save_data(data)
        return f"تمت إزالة الحظر باليوزر:\n@{value}"
    return "هذا اليوزر غير محظور."


# =========================
# DISPLAY TEXT
# =========================

def posts_text() -> str:
    data = load_data()
    if not data.get("posts"):
        return "ما فيه منشورات محفوظة."
    out = "المنشورات المحفوظة:\n\n"
    for post in data["posts"]:
        pid = post["id"]
        out += f"رقم المنشور: {pid}\nمعاينة: /p {pid}\nإرسال: /s {pid}\nحذف نهائي: /d {pid}\n\n"
    return out.strip()


def channels_text() -> str:
    data = load_data()
    if not data.get("target_chats"):
        return "ما فيه قنوات محفوظة.\nلإضافة قناة:\n/add @channelusername"
    out = "القنوات المحفوظة:\n\n"
    for i, ch in enumerate(data["target_chats"], 1):
        out += f"{i}. {ch.get('title')}\nID: {ch.get('id')}\n\n"
    return out.strip()


def allowed_text() -> str:
    data = load_data()
    out = "المسموح لهم:\n\nبالآيدي:\n"
    out += "\n".join(str(x) for x in data.get("allowed_users", [])) or "لا يوجد"
    out += "\n\nباليوزر:\n"
    out += "\n".join("@" + normalize_username(x) for x in data.get("allowed_usernames", [])) or "لا يوجد"
    return out


def admin_stats() -> str:
    data = load_data()
    ids = [int(p.get("id", 0)) for p in data.get("posts", [])]
    return (
        f"إصدار البوت: {BOT_VERSION}\n\n"
        f"عدد المنشورات: {len(data.get('posts', []))}\n"
        f"أكبر رقم منشور: {max(ids) if ids else 0}\n"
        f"الرقم القادم: {next_available_post_id(data)}\n"
        f"عدد القنوات: {len(data.get('target_chats', []))}\n"
        f"ملف التخزين:\n{DATA_FILE}\n"
        f"مجلد النسخ:\n{BACKUP_DIR}"
    )


# =========================
# COMMANDS
# =========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat

    if not is_allowed(user):
        if chat.type in ("group", "supergroup"):
            return
        await update.message.reply_text(denied_text(user), reply_markup=denied_keyboard())
        return

    if chat.type in ("group", "supergroup"):
        await update.message.reply_text("كيف يمكنني مساعدتك؟", reply_markup=group_menu())
        return

    await update.message.reply_text("تم تنظيف الكيبورد القديم.", reply_markup=ReplyKeyboardRemove())
    await update.message.reply_text(f"اختر من القائمة:\n{BOT_VERSION}", reply_markup=reply_keyboard(user))


async def version(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    await update.message.reply_text(
        f"إصدار البوت: {BOT_VERSION}\n"
        f"عدد المنشورات: {len(data.get('posts', []))}\n"
        f"ملف التخزين:\n{DATA_FILE}\n"
        f"مجلد النسخ:\n{BACKUP_DIR}"
    )


async def clean(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("تم تنظيف الكيبورد القديم. اكتب /start.", reply_markup=ReplyKeyboardRemove())


async def adm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_assistant_owner(update.effective_user):
        await update.message.reply_text("قائمة الأدمن خاصة بمساعد المالك فقط.")
        return
    await update.message.reply_text("قائمة أدمن مساعد المالك 👑\n\nللخروج اكتب /oadm", reply_markup=admin_menu())


async def oadm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_assistant_owner(update.effective_user):
        await update.message.reply_text("قائمة الأدمن خاصة بمساعد المالك فقط.")
        return
    context.user_data.clear()
    await update.message.reply_text("تم الخروج من قائمة الأدمن.", reply_markup=ReplyKeyboardRemove())
    await update.message.reply_text("اختر من القائمة:", reply_markup=reply_keyboard(update.effective_user))


async def allow_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user):
        await update.message.reply_text("هذا الإجراء للمالك أو مساعد المالك فقط.")
        return
    if not context.args:
        await update.message.reply_text("اكتب آيدي أو يوزر.\n/allow @username")
        return
    await update.message.reply_text(allow_target(context.args[0]))


async def unallow_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user):
        await update.message.reply_text("هذا الإجراء للمالك أو مساعد المالك فقط.")
        return
    if not context.args:
        await update.message.reply_text("اكتب آيدي أو يوزر.\n/unallow @username")
        return
    await update.message.reply_text(unallow_target(context.args[0]))


async def allowed_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user):
        await update.message.reply_text("هذا الإجراء للمالك أو مساعد المالك فقط.")
        return
    await update.message.reply_text(allowed_text())


async def ban_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user):
        await update.message.reply_text("هذا الإجراء للمالك أو مساعد المالك فقط.")
        return
    if not context.args:
        await update.message.reply_text("اكتب آيدي أو يوزر.\n/ban @username")
        return
    await update.message.reply_text(ban_target(context.args[0]))


async def unban_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user):
        await update.message.reply_text("هذا الإجراء للمالك أو مساعد المالك فقط.")
        return
    if not context.args:
        await update.message.reply_text("اكتب آيدي أو يوزر.\n/unban @username")
        return
    await update.message.reply_text(unban_target(context.args[0]))


async def add_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user):
        await update.message.reply_text("هذا الإجراء للمالك أو مساعد المالك فقط.")
        return
    if not context.args:
        await update.message.reply_text("اكتب القناة.\n/add @channelusername")
        return
    try:
        chat = await context.bot.get_chat(context.args[0])
        if chat.type in ("group", "supergroup"):
            await update.message.reply_text("إضافة القروبات معطلة. الإضافة للقنوات فقط.")
            return
        data = load_data()
        if not any(str(c["id"]) == str(chat.id) for c in data["target_chats"]):
            data["target_chats"].append({"id": chat.id, "title": chat.title or chat.username or str(chat.id), "type": chat.type})
            save_data(data)
        await update.message.reply_text(f"تمت إضافة القناة:\n{chat.title or chat.username or chat.id}")
    except Exception as exc:
        await update.message.reply_text(f"ما قدرت أضيف القناة.\nتأكد أن البوت مشرف فيها.\n{exc}")


async def del_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user):
        await update.message.reply_text("هذا الإجراء للمالك أو مساعد المالك فقط.")
        return
    if not context.args:
        await update.message.reply_text("اكتب آيدي القناة.\n/del CHAT_ID")
        return
    target = context.args[0]
    data = load_data()
    old = len(data["target_chats"])
    data["target_chats"] = [
        c for c in data["target_chats"]
        if str(c.get("id")) != target and normalize_username(c.get("title")) != normalize_username(target)
    ]
    if len(data["target_chats"]) == old:
        await update.message.reply_text("ما لقيت قناة بهذا المعرف.")
        return
    save_data(data)
    await update.message.reply_text("تم حذف القناة.")


async def chats_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user):
        await update.message.reply_text("هذا الإجراء للمالك أو مساعد المالك فقط.")
        return
    await update.message.reply_text(channels_text())


async def preview_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update.effective_user):
        if update.effective_chat.type in ("group", "supergroup"):
            return
        await update.message.reply_text(denied_text(update.effective_user), reply_markup=denied_keyboard())
        return
    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text("اكتب رقم المنشور.\n/p 1")
        return
    data = load_data()
    post = find_post(data, int(context.args[0]))
    if not post:
        await update.message.reply_text("ما لقيت منشور بهذا الرقم.")
        return
    await update.message.reply_text(f"معاينة المنشور رقم {context.args[0]}:")
    await send_post_to_chat(context.bot, update.effective_chat.id, post)


async def send_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type not in ("group", "supergroup"):
        await update.message.reply_text("الإرسال للقنوات يكون من قروب التحكم فقط.")
        return
    if not is_admin(update.effective_user):
        await update.message.reply_text("هذا الإجراء للمالك أو مساعد المالك فقط.")
        return
    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text("اكتب رقم المنشور.\n/s 1")
        return
    data = load_data()
    post = find_post(data, int(context.args[0]))
    if not post:
        await update.message.reply_text("ما لقيت منشور بهذا الرقم.")
        return
    if not data["target_chats"]:
        await update.message.reply_text("ما فيه قنوات محفوظة.")
        return
    if post.get("sent_messages"):
        await update.message.reply_text(
            "هذا المنشور مرسل مسبقًا في القنوات.\nاختر حذف وارسال لتجنب التكرار.",
            reply_markup=sent_buttons(post["id"]),
        )
        return
    ok, failed = await send_to_channels(context, data, post)
    await update.message.reply_text(f"تم الإرسال.\nنجح: {ok}\nفشل: {failed}", reply_markup=sent_buttons(post["id"]))


async def delete_post_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global DELETE_OPERATION_ACTIVE
    if not is_admin(update.effective_user):
        await update.message.reply_text("هذا الإجراء للمالك أو مساعد المالك فقط.")
        return
    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text("اكتب رقم المنشور.\n/d 1")
        return
    data = load_data()
    pid = int(context.args[0])
    old = len(data["posts"])
    data["posts"] = [p for p in data["posts"] if int(p.get("id", 0)) != pid]
    if len(data["posts"]) == old:
        await update.message.reply_text("ما لقيت منشور بهذا الرقم.")
        return
    data["next_post_id"] = next_available_post_id(data)
    DELETE_OPERATION_ACTIVE = True
    try:
        save_data(data, allow_post_count_decrease=True)
    finally:
        DELETE_OPERATION_ACTIVE = False
    await update.message.reply_text(f"تم حذف المنشور رقم {pid}.")


async def recover_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user):
        await update.message.reply_text("هذا الإجراء للمالك أو مساعد المالك فقط.")
        return
    data, path, count = find_best_storage()
    if data is None:
        await update.message.reply_text("ما لقيت أي ملف تخزين.")
        return
    current_count = post_count_from_file(DATA_FILE)
    if count > current_count:
        write_json_atomic(DATA_FILE, data)
        mirror_storage(data)
        await update.message.reply_text(f"تم الاسترجاع ✅\nالمصدر:\n{path}\nعدد المنشورات: {count}")
    else:
        await update.message.reply_text(f"أفضل نسخة موجودة ليست أكبر من الحالية.\nالحالي: {current_count}\nالأفضل: {count}\n{path}")


# =========================
# CALLBACKS / MESSAGES
# =========================

async def callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = update.effective_user
    msg = query.message
    data = query.data
    await query.answer()

    if data == "denied_info":
        await msg.edit_text(
            "شرح عن البوت 📘\n\nهذا البوت لصنع منشورات وإرسالها للقنوات.\n\nصانع البوت: @OK_C7",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("العودة للوراء ↩", callback_data="denied_back")]]),
        )
        return
    if data == "denied_back":
        await msg.edit_text(denied_text(user), reply_markup=denied_keyboard())
        return

    if data.startswith("admin_"):
        if not is_assistant_owner(user):
            await query.answer("قائمة الأدمن خاصة بمساعد المالك فقط.", show_alert=True)
            return
        if data == "admin_home":
            await msg.edit_text("قائمة أدمن مساعد المالك 👑\n\nللخروج اكتب /oadm", reply_markup=admin_menu())
        elif data == "admin_stats":
            await msg.edit_text(admin_stats(), reply_markup=admin_back())
        elif data == "admin_storage":
            await msg.edit_text(f"ملف التخزين:\n{DATA_FILE}\n\nمجلد النسخ:\n{BACKUP_DIR}", reply_markup=admin_back())
        elif data == "admin_channels":
            await msg.edit_text(channels_text(), reply_markup=admin_back())
        elif data == "admin_fix":
            d = load_data()
            d["next_post_id"] = next_available_post_id(d)
            save_data(d)
            await msg.edit_text(f"تم إصلاح الترقيم.\nالرقم القادم: {d['next_post_id']}", reply_markup=admin_back())
        elif data == "admin_ban":
            context.user_data["state"] = "ban"
            await msg.edit_text("ارسل يوزر الشخص لحظره.", reply_markup=admin_back())
        elif data == "admin_unban":
            context.user_data["state"] = "unban"
            await msg.edit_text("ارسل يوزر الشخص لإزالة الحظر.", reply_markup=admin_back())
        return

    if data.startswith("sent_delete:") or data.startswith("sent_delete_resend:"):
        if not is_admin(user):
            await query.answer("هذا الإجراء للمالك أو مساعد المالك فقط.", show_alert=True)
            return
        pid = int(data.split(":")[1])
        d = load_data()
        post = find_post(d, pid)
        if not post:
            await msg.reply_text("ما لقيت المنشور.")
            return
        deleted = await delete_sent_messages(context, d, post)
        if data.startswith("sent_delete_resend:"):
            ok, failed = await send_to_channels(context, d, post)
            await msg.edit_text(
                f"تم حذف القديم وإعادة الإرسال.\nالمحذوف: {deleted}\nنجح: {ok}\nفشل: {failed}",
                reply_markup=sent_buttons(pid),
            )
        else:
            await msg.edit_text(f"تم حذف الرسائل المنشورة من القنوات.\nالمحذوف: {deleted}\n\nالمنشور المحفوظ لم يتم حذفه.")
        return

    if not is_allowed(user):
        return

    if data == "group_add_channels_help":
        await msg.reply_text("لإضافة قناة:\n/add @channelusername")
    elif data == "group_remove_channels_help":
        await msg.reply_text("لحذف قناة:\n/del CHAT_ID")
    elif data == "group_send_post_help":
        await msg.reply_text("لإرسال منشور:\n/s رقم_المنشور")
    elif data == "group_preview_post_help":
        await msg.reply_text("لمعاينة منشور:\n/p رقم_المنشور")


async def messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    user = update.effective_user
    chat = update.effective_chat
    text = (msg.text or "").strip() if msg.text else ""

    if not is_allowed(user):
        return

    if text in ("إلغاء / رجوع ↩", "الرجوع للقائمة الرئيسية ↩", "القائمة الرئيسية ↩"):
        context.user_data.clear()
        await msg.reply_text("تم الرجوع للقائمة الرئيسية.", reply_markup=ReplyKeyboardRemove())
        await msg.reply_text("اختر من القائمة:", reply_markup=reply_keyboard(user))
        return

    state = context.user_data.get("state")

    if state == "ban":
        await msg.reply_text(ban_target(text), reply_markup=reply_keyboard(user))
        context.user_data.clear()
        return
    if state == "unban":
        await msg.reply_text(unban_target(text), reply_markup=reply_keyboard(user))
        context.user_data.clear()
        return

    if state == "create_content":
        post = build_post(msg)
        if not post:
            await msg.reply_text("ارسل محتوى صحيح.")
            return
        context.user_data["draft_post"] = post
        context.user_data["state"] = "create_button"
        await msg.reply_text("ارسل نص الزر:")
        return

    if state == "create_button":
        context.user_data["draft_post"]["button_text"] = text
        context.user_data["state"] = "create_link"
        await msg.reply_text("ارسل الرابط:")
        return

    if state == "create_link":
        if not text.startswith(("http://", "https://")):
            await msg.reply_text("الرابط لازم يبدأ بـ http أو https")
            return
        data = load_data()
        pid = next_available_post_id(data)
        post = context.user_data["draft_post"]
        post["id"] = pid
        post["link"] = text
        post["sent_messages"] = {}
        data["posts"].append(post)
        data["next_post_id"] = next_available_post_id(data)
        save_data(data)
        context.user_data.clear()
        await msg.reply_text(f"تم حفظ المنشور تلقائيًا ✅\nرقم المنشور: {pid}", reply_markup=reply_keyboard(user))
        return

    if state == "edit_number":
        if not text.isdigit():
            await msg.reply_text("ارسل رقم صحيح.")
            return
        data = load_data()
        post = find_post(data, int(text))
        if not post:
            await msg.reply_text("ما لقيت منشور بهذا الرقم.")
            return
        context.user_data["edit_id"] = int(text)
        context.user_data["state"] = "edit_content"
        await msg.reply_text("ارسل محتوى المنشور الجديد:")
        return

    if state == "edit_content":
        post = build_post(msg)
        if not post:
            await msg.reply_text("ارسل محتوى صحيح.")
            return
        context.user_data["draft_post"] = post
        context.user_data["state"] = "edit_button"
        await msg.reply_text("ارسل نص الزر:")
        return

    if state == "edit_button":
        context.user_data["draft_post"]["button_text"] = text
        context.user_data["state"] = "edit_link"
        await msg.reply_text("ارسل الرابط:")
        return

    if state == "edit_link":
        if not text.startswith(("http://", "https://")):
            await msg.reply_text("الرابط لازم يبدأ بـ http أو https")
            return
        data = load_data()
        pid = context.user_data["edit_id"]
        for index, old_post in enumerate(data["posts"]):
            if int(old_post["id"]) == pid:
                new_post = context.user_data["draft_post"]
                new_post["id"] = pid
                new_post["link"] = text
                new_post["sent_messages"] = old_post.get("sent_messages", {})
                data["posts"][index] = new_post
                save_data(data)
                context.user_data.clear()
                await msg.reply_text(f"تم تعديل المنشور رقم {pid} ✅", reply_markup=reply_keyboard(user))
                return
        context.user_data.clear()
        await msg.reply_text("ما لقيت المنشور.")
        return

    if text == "صنع منشور 📌":
        if not is_admin(user):
            await msg.reply_text("هذا الإجراء للمالك أو مساعد المالك فقط.")
            return
        context.user_data["state"] = "create_content"
        await msg.reply_text("قم بارسال محتوى المنشور\nممكن ان يكون اي شيء\n(نص, 🖼 صورة, 🎥 فديو, 🎙 مقطع صوت. . . .)")
        return

    if text == "تعديل منشور 📝":
        if not is_admin(user):
            await msg.reply_text("هذا الإجراء للمالك أو مساعد المالك فقط.")
            return
        context.user_data["state"] = "edit_number"
        await msg.reply_text("قم بارسال رقم المنشور الذي تريد تعديله.")
        return

    if text == "منشوراتي 📁":
        await msg.reply_text(posts_text())
        return
    if text == "معاينة منشور 👁":
        await msg.reply_text("لمعاينة منشور اكتب:\n/p رقم_المنشور")
        return
    if text == "إرسال منشور 📤":
        await msg.reply_text("لإرسال منشور من قروب التحكم:\n/s رقم_المنشور")
        return
    if text == "إدارة القنوات 📡":
        await msg.reply_text("إدارة القنوات:\n/add @channelusername\n/del CHAT_ID\n/chats")
        return

    # Silent for random messages.
    return


# =========================
# KEEP-ALIVE WEB SERVER
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


def main():
    threading.Thread(target=run_web, daemon=True).start()
    load_data()
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("version", version))
    app.add_handler(CommandHandler("clean", clean))
    app.add_handler(CommandHandler("adm", adm))
    app.add_handler(CommandHandler("oadm", oadm))

    app.add_handler(CommandHandler("allow", allow_cmd))
    app.add_handler(CommandHandler("unallow", unallow_cmd))
    app.add_handler(CommandHandler("allowed", allowed_cmd))
    app.add_handler(CommandHandler("ban", ban_cmd))
    app.add_handler(CommandHandler("unban", unban_cmd))

    app.add_handler(CommandHandler("add", add_channel))
    app.add_handler(CommandHandler("del", del_channel))
    app.add_handler(CommandHandler("chats", chats_cmd))

    app.add_handler(CommandHandler("p", preview_cmd))
    app.add_handler(CommandHandler("s", send_cmd))
    app.add_handler(CommandHandler("d", delete_post_cmd))
    app.add_handler(CommandHandler("recover", recover_cmd))

    app.add_handler(CallbackQueryHandler(callbacks))
    app.add_handler(MessageHandler(
        filters.TEXT | filters.PHOTO | filters.VIDEO | filters.Document.ALL | filters.AUDIO | filters.VOICE,
        messages,
    ))

    print(f"Starting {BOT_VERSION}")
    print(f"Storage: {DATA_FILE}")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        print("========== BOT CRASH TRACEBACK ==========", flush=True)
        traceback.print_exc()
        print("========== END TRACEBACK ==========", flush=True)
        raise
