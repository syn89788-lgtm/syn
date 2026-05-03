
import os
import threading
from flask import Flask
import telebot
import logging
import sqlite3

# ==== START CUSTOM FEATURES ====
# إعداد الرسائل حسب اللغة
user_languages = {}
user_subscriptions = {}  # user_id: {'plan':'free','bots':1}
user_bots_db = {}        # user_id: list of bots {'name','ram','cpu'}
SUBSCRIPTION_PRICES = {'free':0,'medium':2,'strong':3,'very_strong':4}
SUBSCRIPTION_BOTS = {'free':1,'medium':2,'strong':3,'very_strong':4}

def is_owner(user_id):
    return user_id in [8410176147]

def get_subscription_info(user_id):
    lang = user_languages.get(user_id,'ar')
    info = f"اشتراكك الحالي وعدد البوتات المسموح بها: {user_subscriptions.get(user_id, {}).get('bots',0)}\n"
    info += "عدد البوتات حسب خطة الاشتراك:\n"
    for plan, bots in SUBSCRIPTION_BOTS.items():
        plan_name = plan if lang=='ar' else plan.replace('_',' ').capitalize()
        info += f"- {plan_name}: {bots} بوت(s)\n"
    return info

def list_user_bots(user_id):
    bots = user_bots_db.get(user_id, [])
    msg_text = f"عدد البوتات لديك: {len(bots)}\n"
    for b in bots:
        msg_text += f"- {b['name']} | RAM: {b['ram']} MB | CPU: {b['cpu']} cores\n"
    return msg_text

def purchase_subscription(user_id, plan, stars_sent):
    price = SUBSCRIPTION_PRICES.get(plan,0)
    if stars_sent >= price:
        user_subscriptions[user_id] = {'plan':plan,'bots':SUBSCRIPTION_BOTS[plan]}
        return True, f"تم شراء الاشتراك {plan} بنجاح!"
    else:
        return False, f"عدد النجوم غير كافي. مطلوب: {price}, مرسل: {stars_sent}"

def admin_set_price(plan, new_price, user_id):
    if is_owner(user_id):
        SUBSCRIPTION_PRICES[plan] = new_price
        return True
    return False
# ==== END CUSTOM FEATURES ====

# ==== Flask Web Server ====
app = Flask(__name__)

@app.route("/")
def home():
    return "OK"

@app.route("/health")
def health():
    return "OK"

def run_web():
    port = int(os.environ.get("PORT",10000))
    app.run(host="0.0.0.0", port=port)

threading.Thread(target=run_web, daemon=True).start()

# ==== Telegram Bot ====
TOKEN = "YOUR_BOT_TOKEN_HERE"
bot = telebot.TeleBot(TOKEN)

# مجلد حفظ الملفات
UPLOAD_DIR = "uploaded_bots"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# مثال رسالة start
@bot.message_handler(commands=['start'])
def start_handler(message):
    bot.send_message(message.chat.id, "مرحبًا! استخدم الأزرار لاختيار اللغة والاشتراك والبوتات.")

# مثال رفع أي رابط/ملف
@bot.message_handler(content_types=['document','text','audio','video','photo','sticker'])
def upload_handler(message):
    if not os.path.exists(UPLOAD_DIR):
        os.makedirs(UPLOAD_DIR, exist_ok=True)
    file_info = getattr(message,'document',None)
    if file_info:
        file_path = os.path.join(UPLOAD_DIR, file_info.file_name)
        bot.reply_to(message,f"تم حفظ الملف: {file_info.file_name}")
    else:
        bot.reply_to(message,"تم قبول الرابط/الملف")

# مثال قائمة بوتاتي
@bot.message_handler(commands=['mybots'])
def my_bots(message):
    msg_text = list_user_bots(message.from_user.id)
    bot.send_message(message.chat.id, msg_text)

# مثال اشتراك
@bot.message_handler(commands=['subscribe'])
def subscribe(message):
    # فقط توضيح
    bot.send_message(message.chat.id, get_subscription_info(message.from_user.id))

# شغّل البوت
bot.polling(none_stop=True)
