import os
import json
import logging
from typing import Dict, Any, List, Optional, Union

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    KeyboardButton,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)

# =========================
# الإعدادات
# =========================

BOT_TOKEN = "8674770134:AAHawnWgnNofC-3CAYYFCyXS2PJ7QKRezkA"

# آيدي حساب المالك الحقيقي
OWNER_ID = 8410176147

OWNER_NAME = "OK_C7"
OWNER_USERNAME = "@OK_C7"
OWNER_LINK = "https://t.me/OK_C7"

# يوزرات مسموح لها تستخدم البوت
ALLOWED_USERNAMES = {"x7vqz4"}

DATA_FILE = "bot_data.json"

MENU_BUTTON_TEXTS = {
    "صنع منشور 📌",
    "تعديل منشور 📝",
    "منشوراتي 📁",
    "معاينة منشور 👁",
    "إرسال منشور 📤",
    "إدارة القروبات 📡",
    "مساعدة ❓",
    "حول البوت ℹ",
    "ارسل للمالك 📩",
    "إلغاء / رجوع ↩",
    "عرض المنشورات 📂",
}

ASK_CONTENT, ASK_BUTTON_TEXT, ASK_LINK = range(3)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)


# =========================
# التخزين
# =========================

def default_data() -> Dict[str, Any]:
    return {
        "allowed_users": [OWNER_ID],
        "posts": [],
        "next_post_id": 1,
        "target_chats": []
    }


def load_data() -> Dict[str, Any]:
    if not os.path.exists(DATA_FILE):
        data = default_data()
        save_data(data)
        return data

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        data = default_data()

    data.setdefault("allowed_users", [])
    data.setdefault("posts", [])
    data.setdefault("next_post_id", 1)
    data.setdefault("target_chats", [])

    # ترقية المنشورات القديمة وإعطاؤها أرقام
    changed = False
    max_id = 0

    for index, post in enumerate(data["posts"], start=1):
        if "id" not in post:
            post["id"] = index
            changed = True

        try:
            max_id = max(max_id, int(post["id"]))
        except Exception:
            pass

        # توافق مع نسخ قديمة كانت تستخدم bottom_text بدل button_text
        if "button_text" not in post and "bottom_text" in post:
            post["button_text"] = post.get("bottom_text", "")
            changed = True

    if data["next_post_id"] <= max_id:
        data["next_post_id"] = max_id + 1
        changed = True

    if OWNER_ID not in data["allowed_users"]:
        data["allowed_users"].append(OWNER_ID)
        changed = True

    if changed:
        save_data(data)

    return data


def save_data(data: Dict[str, Any]) -> None:
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def find_post(post_id: int) -> Optional[Dict[str, Any]]:
    data = load_data()

    for post in data["posts"]:
        try:
            if int(post.get("id")) == int(post_id):
                return post
        except Exception:
            pass

    return None


def add_target_chat(chat_id: int, title: str, chat_type: str) -> None:
    data = load_data()

    for chat in data["target_chats"]:
        if int(chat["id"]) == int(chat_id):
            chat["title"] = title
            chat["type"] = chat_type
            save_data(data)
            return

    data["target_chats"].append({
        "id": chat_id,
        "title": title,
        "type": chat_type,
    })
    save_data(data)


def remove_target_chat(chat_id: int) -> bool:
    data = load_data()
    old_len = len(data["target_chats"])

    data["target_chats"] = [
        chat for chat in data["target_chats"]
        if int(chat["id"]) != int(chat_id)
    ]

    changed = len(data["target_chats"]) != old_len
    if changed:
        save_data(data)

    return changed


def is_owner(user_id: int) -> bool:
    return user_id == OWNER_ID


def is_allowed(user_or_id: Union[int, Any]) -> bool:
    data = load_data()

    if isinstance(user_or_id, int):
        return user_or_id in data["allowed_users"]

    user = user_or_id
    username = (user.username or "").lower().lstrip("@")

    return user.id in data["allowed_users"] or username in ALLOWED_USERNAMES


# =========================
# الكيبورد والقوائم
# =========================

def owner_reply_menu() -> ReplyKeyboardMarkup:
    keyboard = [
        [KeyboardButton("صنع منشور 📌"), KeyboardButton("تعديل منشور 📝")],
        [KeyboardButton("منشوراتي 📁"), KeyboardButton("معاينة منشور 👁")],
        [KeyboardButton("إرسال منشور 📤"), KeyboardButton("إدارة القروبات 📡")],
        [KeyboardButton("مساعدة ❓"), KeyboardButton("حول البوت ℹ")],
        [KeyboardButton("ارسل للمالك 📩")],
        [KeyboardButton("إلغاء / رجوع ↩")],
    ]

    return ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,
        one_time_keyboard=False,
        input_field_placeholder="اختر من القائمة"
    )


def user_reply_menu() -> ReplyKeyboardMarkup:
    keyboard = [
        [KeyboardButton("عرض المنشورات 📂")],
        [KeyboardButton("ارسل للمالك 📩")],
        [KeyboardButton("حول البوت ℹ")],
    ]

    return ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,
        one_time_keyboard=False,
        input_field_placeholder="اختر من القائمة"
    )


def get_reply_menu(user_id: int) -> ReplyKeyboardMarkup:
    if is_owner(user_id):
        return owner_reply_menu()
    return user_reply_menu()


def owner_inline_button() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("فتح صفحة المالك 📩", url=OWNER_LINK)]
    ])


def post_keyboard(link: str = "", button_text: str = "") -> Optional[InlineKeyboardMarkup]:
    if not link:
        return None

    if not button_text:
        button_text = "فتح الرابط"

    return InlineKeyboardMarkup([
        [InlineKeyboardButton(button_text, url=link)]
    ])


def post_manage_keyboard(post_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("إرسال المنشور 📤", callback_data=f"send_post:{post_id}"),
            InlineKeyboardButton("حذف المنشور 🗑", callback_data=f"delete_post:{post_id}")
        ],
        [
            InlineKeyboardButton("معاينة المنشور 👁", callback_data=f"preview_post:{post_id}")
        ]
    ])


# =========================
# الحماية
# =========================

async def deny_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    chat = update.effective_chat

    # داخل القروبات: أي شخص غير مسموح له يتم تجاهله بالكامل
    # حتى لا يصير القروب لوحة إعلانات للرفض، وكأننا ناقصين فوضى.
    if chat and chat.type in ("group", "supergroup"):
        if update.callback_query:
            await update.callback_query.answer("غير مسموح لك.", show_alert=True)
        return

    text = (
        "المالك يرحب بك 🌹\n\n"
        "نعتذر، غير مسموح لك باستخدام البوت.\n"
        "إذا عندك شيء يفيد تواصل مع المالك.\n\n"
        f"المالك: {OWNER_USERNAME}"
    )

    if update.message:
        await update.message.reply_text(text, reply_markup=owner_inline_button())
    elif update.callback_query:
        await update.callback_query.answer("غير مسموح لك.", show_alert=True)
        await update.callback_query.message.reply_text(text, reply_markup=owner_inline_button())

    try:
        username = f"@{user.username}" if user.username else "بدون يوزر"
        await context.bot.send_message(
            chat_id=OWNER_ID,
            text=(
                "شخص حاول يدخل البوت في الخاص:\n\n"
                f"الاسم: {user.full_name}\n"
                f"اليوزر: {username}\n"
                f"الآيدي: `{user.id}`\n\n"
                "للسماح له اكتب:\n"
                f"/allow {user.id}"
            ),
            parse_mode="Markdown",
        )
    except Exception:
        pass


def owner_only(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id

        if not is_owner(user_id):
            await deny_user(update, context)
            return ConversationHandler.END

        return await func(update, context)

    return wrapper


def allowed_only(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user

        if not is_allowed(user):
            await deny_user(update, context)
            return ConversationHandler.END

        return await func(update, context)

    return wrapper



# =========================
# إرسال أي نوع محتوى
# =========================

async def send_post_content(chat_id: int, context: ContextTypes.DEFAULT_TYPE, post: Dict[str, Any]) -> bool:
    content_type = post.get("content_type", "photo")
    file_id = post.get("file_id") or post.get("photo_file_id")
    text = (post.get("top_text") or "").strip()
    button_text = (post.get("button_text") or "").strip()
    link = (post.get("link") or "").strip()
    keyboard = post_keyboard(link, button_text)

    try:
        if content_type == "text":
            await context.bot.send_message(
                chat_id=chat_id,
                text=text or f"منشور رقم {post.get('id', '')}",
                reply_markup=keyboard,
            )
            return True

        if content_type == "photo":
            await context.bot.send_photo(
                chat_id=chat_id,
                photo=file_id,
                caption=text or None,
                reply_markup=keyboard,
            )
            return True

        if content_type == "video":
            await context.bot.send_video(
                chat_id=chat_id,
                video=file_id,
                caption=text or None,
                reply_markup=keyboard,
            )
            return True

        if content_type == "audio":
            await context.bot.send_audio(
                chat_id=chat_id,
                audio=file_id,
                caption=text or None,
                reply_markup=keyboard,
            )
            return True

        if content_type == "voice":
            await context.bot.send_voice(
                chat_id=chat_id,
                voice=file_id,
                caption=text or None,
                reply_markup=keyboard,
            )
            return True

        if content_type == "document":
            await context.bot.send_document(
                chat_id=chat_id,
                document=file_id,
                caption=text or None,
                reply_markup=keyboard,
            )
            return True

        # fallback للبشر الذين يرسلون أشياء تيليجرام نفسه يحتار فيها
        await context.bot.send_message(
            chat_id=chat_id,
            text=text or f"منشور رقم {post.get('id', '')}",
            reply_markup=keyboard,
        )
        return True

    except Exception as e:
        print(f"Failed sending content to {chat_id}: {e}", flush=True)
        return False


# =========================
# إرسال المنشور
# =========================

async def send_single_post(chat_id: int, context: ContextTypes.DEFAULT_TYPE, post: Dict[str, Any]) -> bool:
    return await send_post_content(chat_id, context, post)


async def send_post_to_targets(context: ContextTypes.DEFAULT_TYPE, post_id: int) -> Dict[str, int]:
    data = load_data()
    post = find_post(post_id)

    if not post:
        return {"sent": 0, "failed": 0, "total": 0}

    targets = data["target_chats"]
    sent = 0
    failed = 0

    for chat in targets:
        ok = await send_single_post(chat["id"], context, post)
        if ok:
            sent += 1
        else:
            failed += 1

    return {
        "sent": sent,
        "failed": failed,
        "total": len(targets),
    }


# =========================
# البداية والقائمة
# =========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat

    print(f"Received start from {user.id} - {user.full_name} in chat {chat.id}", flush=True)

    if not is_allowed(user):
        await deny_user(update, context)
        return

    # إذا الأمر داخل قروب، نسجل القروب تلقائياً للتحكم
    if chat.type in ("group", "supergroup"):
        add_target_chat(chat.id, chat.title or str(chat.id), chat.type)

    await update.message.reply_text(
        "اهلا وسهلا بك.\n\n"
        "هذا البوت يسمح لك بصنع منشورات تحتوي على أزرار بطريقة احترافية.\n"
        "اضافة الى نمط HTML و MarkDown.\n\n"
        "اوامر مهمة:\n"
        "/p رقم المنشور = معاينة المنشور\n"
        "/s رقم المنشور = ارسال المنشور لكل القنوات والقروبات المحفوظة\n\n"
        "اضغط صنع منشور 📌 واتبع التعليمات.",
        reply_markup=get_reply_menu(user.id),
    )


@allowed_only
async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "اختر من القائمة:",
        reply_markup=get_reply_menu(update.effective_user.id),
    )


async def my_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat
    username = f"@{user.username}" if user.username else "بدون يوزر"

    await update.message.reply_text(
        f"آيديك الحقيقي:\n{user.id}\n\n"
        f"اسمك:\n{user.full_name}\n\n"
        f"يوزرك:\n{username}\n\n"
        f"آيدي هذه المحادثة/القروب:\n{chat.id}\n"
        f"نوعها:\n{chat.type}",
        reply_markup=get_reply_menu(user.id) if is_allowed(user) else None,
    )


# =========================
# السماح والمنع
# =========================

@owner_only
async def allow_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("اكتب آيدي الشخص.\nمثال:\n/allow 123456789")
        return

    try:
        user_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("الآيدي لازم يكون رقم.")
        return

    data = load_data()

    if user_id not in data["allowed_users"]:
        data["allowed_users"].append(user_id)
        save_data(data)

    await update.message.reply_text(f"تم السماح للمستخدم:\n{user_id}")

    try:
        await context.bot.send_message(chat_id=user_id, text="تم السماح لك باستخدام البوت.\nاكتب /start")
    except Exception:
        pass


@owner_only
async def disallow_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("اكتب آيدي الشخص.\nمثال:\n/disallow 123456789")
        return

    try:
        user_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("الآيدي لازم يكون رقم.")
        return

    if user_id == OWNER_ID:
        await update.message.reply_text("ما تقدر تمنع نفسك، حتى الفوضى لها حدود.")
        return

    data = load_data()

    if user_id in data["allowed_users"]:
        data["allowed_users"].remove(user_id)
        save_data(data)

    await update.message.reply_text(f"تم منع المستخدم:\n{user_id}")


@owner_only
async def allowed_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    allowed = data["allowed_users"]

    text = "المسموح لهم بالآيدي:\n\n"
    text += "\n".join(str(uid) for uid in allowed)
    text += "\n\nالمسموح لهم باليوزر:\n"
    text += "\n".join("@" + username for username in sorted(ALLOWED_USERNAMES))

    await update.message.reply_text(text)


# =========================
# إدارة القروبات والقنوات
# =========================

@owner_only
async def add_here(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat

    if chat.type not in ("group", "supergroup", "channel"):
        await update.message.reply_text("هذا الأمر يستخدم داخل قروب أو قناة.")
        return

    add_target_chat(chat.id, chat.title or str(chat.id), chat.type)

    await update.message.reply_text(
        f"تمت إضافة هذا المكان لقائمة الإرسال:\n{chat.title or chat.id}"
    )


@owner_only
async def remove_here(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    removed = remove_target_chat(chat.id)

    if removed:
        await update.message.reply_text("تم حذف هذا المكان من قائمة الإرسال.")
    else:
        await update.message.reply_text("هذا المكان غير موجود في قائمة الإرسال.")


@owner_only
async def add_chat_by_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "اكتب آيدي القروب/القناة أو يوزر القناة.\n"
            "مثال:\n/addchat -1001234567890\n/addchat @channelusername"
        )
        return

    raw = context.args[0].strip()

    try:
        chat = await context.bot.get_chat(raw)
        add_target_chat(chat.id, chat.title or raw, chat.type)

        await update.message.reply_text(
            f"تمت إضافة:\n{chat.title or raw}\nID: {chat.id}"
        )
    except Exception as e:
        await update.message.reply_text(
            "ما قدرت أضيفها.\n"
            "تأكد أن البوت مضاف ومشرف في القناة/القروب.\n"
            f"الخطأ:\n{e}"
        )


@owner_only
async def remove_chat_by_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "اكتب آيدي القروب/القناة.\n"
            "مثال:\n/removechat -1001234567890"
        )
        return

    raw = context.args[0].strip()

    try:
        chat_id = int(raw)
    except ValueError:
        await update.message.reply_text("الحذف يحتاج آيدي رقمي. استخدم /chats لمعرفة الآيديات.")
        return

    removed = remove_target_chat(chat_id)

    if removed:
        await update.message.reply_text("تم حذف المكان من قائمة الإرسال.")
    else:
        await update.message.reply_text("هذا الآيدي غير موجود في قائمة الإرسال.")


@owner_only
async def list_chats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    chats = data["target_chats"]

    if not chats:
        await update.message.reply_text(
            "ما فيه قروبات أو قنوات محفوظة.\n\n"
            "داخل أي قروب اكتب /addhere\n"
            "أو أضف قناة كذا:\n/addchat @channelusername"
        )
        return

    text = "القنوات والقروبات المحفوظة:\n\n"

    for i, chat in enumerate(chats, start=1):
        text += (
            f"{i}. {chat.get('title', 'بدون اسم')}\n"
            f"ID: {chat.get('id')}\n"
            f"Type: {chat.get('type')}\n\n"
        )

    await update.message.reply_text(text)


async def manage_chats_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    if not is_owner(user.id):
        await deny_user(update, context)
        return

    await update.message.reply_text(
        "إدارة القروبات والقنوات 📡\n\n"
        "داخل القروب اكتب:\n"
        "/addhere لإضافة القروب لقائمة الإرسال\n"
        "/removehere لحذف القروب من قائمة الإرسال\n\n"
        "لإضافة قناة:\n"
        "/addchat @channelusername\n"
        "أو:\n"
        "/addchat -1001234567890\n\n"
        "عرض القائمة:\n"
        "/chats\n\n"
        "مهم: في القنوات لازم البوت يكون مشرف ويملك صلاحية النشر."
    )


# =========================
# المنشورات
# =========================

async def send_posts(chat_id: int, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    posts: List[Dict[str, Any]] = data["posts"]

    if not posts:
        await context.bot.send_message(chat_id=chat_id, text="ما فيه منشورات حالياً.")
        return

    for post in posts:
        await send_single_post(chat_id, context, post)


async def preview_post_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    if not is_allowed(user):
        await deny_user(update, context)
        return

    if not context.args:
        await update.message.reply_text("اكتب رقم المنشور.\nمثال:\n/p 1")
        return

    try:
        post_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("رقم المنشور لازم يكون رقم.")
        return

    post = find_post(post_id)

    if not post:
        await update.message.reply_text("ما لقيت منشور بهذا الرقم.")
        return

    await update.message.reply_text(f"معاينة المنشور رقم {post_id}:")
    await send_single_post(update.effective_chat.id, context, post)


async def send_post_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    if not is_owner(user.id):
        await deny_user(update, context)
        return

    if not context.args:
        await update.message.reply_text("اكتب رقم المنشور.\nمثال:\n/s 1")
        return

    try:
        post_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("رقم المنشور لازم يكون رقم.")
        return

    post = find_post(post_id)

    if not post:
        await update.message.reply_text("ما لقيت منشور بهذا الرقم.")
        return

    data = load_data()
    total = len(data["target_chats"])

    if total == 0:
        await update.message.reply_text(
            "ما فيه قنوات أو قروبات محفوظة للإرسال.\n\n"
            "داخل القروب اكتب /addhere\n"
            "أو أضف قناة:\n/addchat @channelusername"
        )
        return

    status_msg = await update.message.reply_text(
        f"تم جاري إرسال المنشور رقم {post_id} إلى {total} قناة/قروب..."
    )

    result = await send_post_to_targets(context, post_id)

    await status_msg.edit_text(
        f"تم إرسال المنشور رقم {post_id}\n\n"
        f"{result['total']}/{result['total']}\n"
        f"تم الإرسال: {result['sent']}\n"
        f"فشل: {result['failed']}"
    )


async def preview_last_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    if not is_allowed(user):
        await deny_user(update, context)
        return

    data = load_data()
    posts = data["posts"]

    if not posts:
        await update.message.reply_text("ما فيه منشور للمعاينة.", reply_markup=get_reply_menu(user.id))
        return

    post = posts[-1]
    await update.message.reply_text(f"معاينة آخر منشور، رقمه: {post.get('id')}")
    await send_single_post(update.effective_chat.id, context, post)


async def show_my_posts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    if not is_allowed(user):
        await deny_user(update, context)
        return

    data = load_data()
    posts = data["posts"]

    if not posts:
        await update.message.reply_text("ما فيه منشورات محفوظة.", reply_markup=get_reply_menu(user.id))
        return

    text = "منشوراتي:\n\n"

    for post in posts:
        post_id = post.get("id")
        title = post.get("top_text") or post.get("button_text") or "بدون عنوان"
        title = title.replace("\n", " ")

        if len(title) > 45:
            title = title[:45] + "..."

        text += (
            f"رقم المنشور: {post_id}\n"
            f"{title}\n"
            f"معاينة: /p {post_id}\n"
            f"إرسال: /s {post_id}\n\n"
        )

    await update.message.reply_text(text, reply_markup=get_reply_menu(user.id))


# =========================
# إضافة منشور
# =========================

@owner_only
async def add_post_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        await update.callback_query.answer()
        target = update.callback_query.message
    else:
        target = update.message

    await target.reply_text(
        "قم بارسال محتوى المنشور\n"
        "ممكن ان يكون اي شيء\n"
        "(نص, 🖼 صورة, 🎥 فديو, 🎙 مقطع صوت. . . .)",
        reply_markup=get_reply_menu(update.effective_user.id),
    )

    context.user_data["new_post"] = {}
    return ASK_CONTENT


@owner_only
async def receive_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message

    post_data = {}

    # نص عادي
    if message.text and not message.text.startswith("/"):
        post_data = {
            "content_type": "text",
            "top_text": message.text.strip(),
        }

    # صورة
    elif message.photo:
        post_data = {
            "content_type": "photo",
            "file_id": message.photo[-1].file_id,
            "photo_file_id": message.photo[-1].file_id,
            "top_text": message.caption or "",
        }

    # فيديو
    elif message.video:
        post_data = {
            "content_type": "video",
            "file_id": message.video.file_id,
            "top_text": message.caption or "",
        }

    # مقطع صوتي كملف audio
    elif message.audio:
        post_data = {
            "content_type": "audio",
            "file_id": message.audio.file_id,
            "top_text": message.caption or "",
        }

    # بصمة/Voice
    elif message.voice:
        post_data = {
            "content_type": "voice",
            "file_id": message.voice.file_id,
            "top_text": message.caption or "",
        }

    # ملف، ومنه الصور المرسلة كملف
    elif message.document:
        mime = message.document.mime_type or ""
        content_type = "photo" if mime.startswith("image/") else "document"

        post_data = {
            "content_type": content_type,
            "file_id": message.document.file_id,
            "top_text": message.caption or "",
        }

        if content_type == "photo":
            post_data["photo_file_id"] = message.document.file_id

    # رد على رسالة فيها محتوى
    elif message.reply_to_message:
        replied = message.reply_to_message

        if replied.photo:
            post_data = {
                "content_type": "photo",
                "file_id": replied.photo[-1].file_id,
                "photo_file_id": replied.photo[-1].file_id,
                "top_text": message.text or replied.caption or "",
            }
        elif replied.video:
            post_data = {
                "content_type": "video",
                "file_id": replied.video.file_id,
                "top_text": message.text or replied.caption or "",
            }
        elif replied.audio:
            post_data = {
                "content_type": "audio",
                "file_id": replied.audio.file_id,
                "top_text": message.text or replied.caption or "",
            }
        elif replied.voice:
            post_data = {
                "content_type": "voice",
                "file_id": replied.voice.file_id,
                "top_text": message.text or "",
            }
        elif replied.document:
            mime = replied.document.mime_type or ""
            content_type = "photo" if mime.startswith("image/") else "document"
            post_data = {
                "content_type": content_type,
                "file_id": replied.document.file_id,
                "top_text": message.text or replied.caption or "",
            }
            if content_type == "photo":
                post_data["photo_file_id"] = replied.document.file_id
        elif replied.text:
            post_data = {
                "content_type": "text",
                "top_text": message.text or replied.text,
            }

    if not post_data:
        await message.reply_text(
            "ما قدرت أتعرف على المحتوى.\\n"
            "ارسل نص أو صورة أو فيديو أو مقطع صوت أو ملف."
        )
        return ASK_CONTENT

    context.user_data["new_post"] = post_data

    await message.reply_text("ارسل النص الذي يظهر في الزر:")
    return ASK_BUTTON_TEXT


@owner_only
async def receive_button_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    button_text = update.message.text.strip()

    if button_text == "إلغاء / رجوع ↩":
        return await cancel(update, context)

    if button_text in MENU_BUTTON_TEXTS:
        await update.message.reply_text(
            "أنت الآن داخل خطوة صنع منشور.\n"
            "ارسل نص الزر، أو اضغط إلغاء / رجوع ↩ للخروج.",
            reply_markup=get_reply_menu(update.effective_user.id),
        )
        return ASK_BUTTON_TEXT

    context.user_data["new_post"]["button_text"] = button_text

    await update.message.reply_text("ارسل الرابط:")
    return ASK_LINK


@owner_only
async def receive_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    link = update.message.text.strip()

    if link == "إلغاء / رجوع ↩":
        return await cancel(update, context)

    if link in MENU_BUTTON_TEXTS:
        context.user_data.pop("new_post", None)

        if link == "تعديل منشور 📝":
            context.user_data["waiting_edit_number"] = True
            await update.message.reply_text(
                "قم بارسال رقم المنشور الذي تريد تعديله.",
                reply_markup=get_reply_menu(update.effective_user.id),
            )
            return ConversationHandler.END

        if link == "معاينة منشور 👁":
            await update.message.reply_text(
                "اكتب رقم المنشور للمعاينة هكذا:\n/p 1",
                reply_markup=get_reply_menu(update.effective_user.id),
            )
            return ConversationHandler.END

        if link == "إرسال منشور 📤":
            await update.message.reply_text(
                "اكتب رقم المنشور للإرسال هكذا:\n/s 1",
                reply_markup=get_reply_menu(update.effective_user.id),
            )
            return ConversationHandler.END

        await update.message.reply_text(
            "تم إلغاء صنع المنشور ورجعت للقائمة الرئيسية.",
            reply_markup=get_reply_menu(update.effective_user.id),
        )
        return ConversationHandler.END

    if not (link.startswith("http://") or link.startswith("https://")):
        await update.message.reply_text(
            "الرابط لازم يبدأ بـ http:// أو https://\n"
            "ارسله مرة ثانية.\n\n"
            "للخروج اضغط إلغاء / رجوع ↩",
            reply_markup=get_reply_menu(update.effective_user.id),
        )
        return ASK_LINK

    data = load_data()

    post_id = data["next_post_id"]
    data["next_post_id"] += 1

    context.user_data["new_post"]["id"] = post_id
    context.user_data["new_post"]["link"] = link

    data["posts"].append(context.user_data["new_post"])
    save_data(data)

    context.user_data.pop("new_post", None)

    await update.message.reply_text(
        f"تم حفظ المنشور ✅\n\n"
        f"رقم المنشور: {post_id}\n\n"
        f"للمعاينة:\n/p {post_id}\n\n"
        f"للإرسال للقنوات والقروبات:\n/s {post_id}",
        reply_markup=get_reply_menu(update.effective_user.id),
    )

    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.pop("new_post", None)
    context.user_data.pop("waiting_edit_number", None)

    user_id = update.effective_user.id

    if update.message:
        await update.message.reply_text(
            "تم الإلغاء ورجعت للقائمة الرئيسية.",
            reply_markup=get_reply_menu(user_id) if is_allowed(update.effective_user) else None,
        )
    elif update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.message.reply_text(
            "تم الإلغاء ورجعت للقائمة الرئيسية.",
            reply_markup=get_reply_menu(user_id) if is_allowed(update.effective_user) else None,
        )

    return ConversationHandler.END


# =========================
# حذف المنشورات
# =========================

@owner_only
async def delete_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    posts = data["posts"]

    if not posts:
        await update.message.reply_text("ما فيه منشورات للحذف.", reply_markup=get_reply_menu(update.effective_user.id))
        return

    buttons = []

    for post in posts:
        post_id = post.get("id")
        title = post.get("top_text") or post.get("button_text") or f"منشور {post_id}"
        title = title.replace("\n", " ")

        if len(title) > 30:
            title = title[:30] + "..."

        buttons.append([
            InlineKeyboardButton(f"حذف {post_id} - {title}", callback_data=f"delete_post:{post_id}")
        ])

    await update.message.reply_text(
        "اختر المنشور الذي تريد حذفه:",
        reply_markup=InlineKeyboardMarkup(buttons),
    )


@owner_only
async def delete_post_by_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("اكتب رقم المنشور.\nمثال:\n/d 1")
        return

    try:
        post_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("رقم المنشور لازم يكون رقم.")
        return

    data = load_data()
    old_len = len(data["posts"])
    data["posts"] = [post for post in data["posts"] if int(post.get("id")) != post_id]

    if len(data["posts"]) == old_len:
        await update.message.reply_text("ما لقيت منشور بهذا الرقم.")
        return

    save_data(data)
    await update.message.reply_text(f"تم حذف المنشور رقم {post_id}.")


@owner_only
async def delete_post_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    post_id = int(query.data.split(":")[1])

    data = load_data()
    old_len = len(data["posts"])
    data["posts"] = [post for post in data["posts"] if int(post.get("id")) != post_id]

    if len(data["posts"]) == old_len:
        await query.message.reply_text("هذا المنشور غير موجود.")
        return

    save_data(data)
    await query.message.reply_text(f"تم حذف المنشور رقم {post_id}.")


# =========================
# معلومات ومساعدة ومالك
# =========================

async def contact_owner(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"للتواصل مع المالك {OWNER_USERNAME}:",
        reply_markup=owner_inline_button(),
    )


async def help_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    if not is_allowed(user):
        await deny_user(update, context)
        return

    text = (
        "طريقة الاستخدام:\n\nملاحظة: داخل القروبات، البوت يستجيب فقط للمالك والمسموح لهم.\n\n"
        "صنع منشور:\n"
        "1. اضغط صنع منشور 📌\n"
        "2. ارسل محتوى المنشور: نص، صورة، فيديو، مقطع صوت، أو ملف\n"
        "3. ارسل النص الذي يظهر في الزر\n"
        "4. ارسل الرابط\n\n"
        "معاينة منشور:\n"
        "/p رقم المنشور\n"
        "مثال: /p 1\n\n"
        "إرسال منشور لكل القنوات والقروبات المحفوظة:\n"
        "/s رقم المنشور\n"
        "مثال: /s 1\n\n"
        "إدارة القنوات والقروبات:\n"
        "/addhere إضافة القروب الحالي\n"
        "/removehere حذف القروب الحالي\n"
        "/addchat @channelusername إضافة قناة\n"
        "/chats عرض القائمة\n\n"
        "أوامر المالك:\n"
        "/allow ID للسماح لشخص\n"
        "/disallow ID لمنع شخص\n"
        "/allowed لعرض المسموح لهم\n"
        "/d رقم حذف منشور\n"
        "/myid معرفة الآيدي"
    )

    await update.message.reply_text(text, reply_markup=get_reply_menu(user.id))


async def about_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    if not is_allowed(user):
        await deny_user(update, context)
        return

    await update.message.reply_text(
        "حول البوت ℹ\n\n"
        "بوت لصنع منشورات بصورة وكابشن وزر رابط باسم تختاره.\n"
        "يدعم ترقيم المنشورات وإرسالها للقنوات والقروبات.\n"
        f"المالك: {OWNER_USERNAME}",
        reply_markup=get_reply_menu(user.id),
    )


# =========================
# معالجة أزرار القائمة النصية
# =========================

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = (update.message.text or "").strip()

    print(f"Text from {user.id}: {text}", flush=True)

    start_words = {
        "start",
        "ستارت",
        "/ستارت",
        "ابدأ",
        "ابدا",
        "بدء",
        "menu",
        "القائمة",
        "قائمة",
    }

    if text.lower() in start_words:
        await start(update, context)
        return

    if not is_allowed(user):
        await deny_user(update, context)
        return

    if context.user_data.get("waiting_edit_number"):
        if text == "إلغاء / رجوع ↩":
            context.user_data.pop("waiting_edit_number", None)
            await update.message.reply_text(
                "تم الإلغاء ورجعت للقائمة الرئيسية.",
                reply_markup=get_reply_menu(user.id),
            )
            return

        try:
            post_id = int(text)
        except ValueError:
            await update.message.reply_text(
                "ارسل رقم المنشور فقط. مثال: 1\n"
                "أو اضغط إلغاء / رجوع ↩",
                reply_markup=get_reply_menu(user.id),
            )
            return

        post = find_post(post_id)
        if not post:
            await update.message.reply_text(
                "ما لقيت منشور بهذا الرقم.\n"
                "ارسل رقم صحيح أو اضغط إلغاء / رجوع ↩",
                reply_markup=get_reply_menu(user.id),
            )
            return

        context.user_data.pop("waiting_edit_number", None)
        await update.message.reply_text(
            f"المنشور رقم {post_id} موجود.\n\n"
            "التعديل الكامل حالياً يكون بحذف المنشور وإنشاء منشور جديد.\n"
            f"لحذفه اكتب:\n/d {post_id}\n\n"
            "أو اضغط صنع منشور 📌 لإنشاء نسخة جديدة.",
            reply_markup=get_reply_menu(user.id),
        )
        return

    if text == "صنع منشور 📌":
        await add_post_start(update, context)
        return ASK_CONTENT

    if text == "تعديل منشور 📝":
        await update.message.reply_text(
            "قم بارسال رقم المنشور الذي تريد تعديله.",
            reply_markup=get_reply_menu(user.id),
        )
        context.user_data["waiting_edit_number"] = True
        return

    if text == "منشوراتي 📁":
        await show_my_posts(update, context)
        return

    if text == "معاينة منشور 👁":
        await update.message.reply_text(
            "اكتب رقم المنشور للمعاينة هكذا:\n/p 1",
            reply_markup=get_reply_menu(user.id),
        )
        return

    if text == "إرسال منشور 📤":
        await update.message.reply_text(
            "اكتب رقم المنشور للإرسال هكذا:\n/s 1",
            reply_markup=get_reply_menu(user.id),
        )
        return

    if text == "إدارة القروبات 📡":
        await manage_chats_message(update, context)
        return

    if text == "عرض المنشورات 📂":
        await send_posts(update.effective_chat.id, context)
        return

    if text == "مساعدة ❓":
        await help_message(update, context)
        return

    if text == "حول البوت ℹ":
        await about_bot(update, context)
        return

    if text == "ارسل للمالك 📩":
        await contact_owner(update, context)
        return

    if text == "إلغاء / رجوع ↩":
        await cancel(update, context)
        return

    await update.message.reply_text(
        "اختر من الأزرار تحت أو اكتب /help.",
        reply_markup=get_reply_menu(user.id),
    )


# =========================
# أزرار الإنلاين
# =========================

async def inline_buttons_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = update.effective_user

    if not is_allowed(user):
        await deny_user(update, context)
        return

    await query.answer()

    if query.data.startswith("preview_post:"):
        post_id = int(query.data.split(":")[1])
        post = find_post(post_id)

        if not post:
            await query.message.reply_text("ما لقيت منشور بهذا الرقم.")
            return

        await query.message.reply_text(f"معاينة المنشور رقم {post_id}:")
        await send_single_post(query.message.chat_id, context, post)

    elif query.data.startswith("send_post:"):
        if not is_owner(user.id):
            await query.message.reply_text("هذا الزر للمالك فقط.")
            return

        post_id = int(query.data.split(":")[1])
        result = await send_post_to_targets(context, post_id)

        await query.message.reply_text(
            f"تم إرسال المنشور رقم {post_id}\n\n"
            f"{result['total']}/{result['total']}\n"
            f"تم الإرسال: {result['sent']}\n"
            f"فشل: {result['failed']}"
        )


# =========================
# التشغيل
# =========================

def main():
    load_data()

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    add_post_conv = ConversationHandler(
        entry_points=[
            CommandHandler("addpost", add_post_start),
            MessageHandler(filters.Regex("^صنع منشور 📌$"), add_post_start),
        ],
        states={
            ASK_CONTENT: [
                MessageHandler(filters.PHOTO, receive_photo),
                MessageHandler(filters.ALL, receive_photo),
            ],
            ASK_BUTTON_TEXT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_button_text),
            ],
            ASK_LINK: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_link),
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cancel),
            MessageHandler(filters.Regex("^إلغاء / رجوع ↩$"), cancel),
        ],
        allow_reentry=True,
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_message))
    app.add_handler(CommandHandler("menu", menu))
    app.add_handler(CommandHandler("myid", my_id))

    app.add_handler(CommandHandler("allow", allow_user))
    app.add_handler(CommandHandler("disallow", disallow_user))
    app.add_handler(CommandHandler("allowed", allowed_list))

    app.add_handler(CommandHandler("p", preview_post_command))
    app.add_handler(CommandHandler("s", send_post_command))
    app.add_handler(CommandHandler("d", delete_post_by_number))

    app.add_handler(CommandHandler("addhere", add_here))
    app.add_handler(CommandHandler("removehere", remove_here))
    app.add_handler(CommandHandler("addchat", add_chat_by_id))
    app.add_handler(CommandHandler("removechat", remove_chat_by_id))
    app.add_handler(CommandHandler("chats", list_chats))

    app.add_handler(add_post_conv)

    app.add_handler(CallbackQueryHandler(delete_post_callback, pattern=r"^delete_post:\d+$"))
    app.add_handler(CallbackQueryHandler(inline_buttons_handler))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

    print("Bot is running...", flush=True)
    print(f"Owner ID: {OWNER_ID}", flush=True)
    print(f"Owner username: {OWNER_USERNAME}", flush=True)
    print("Commands: /p 1 preview, /s 1 send, /addhere add current group", flush=True)

    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
