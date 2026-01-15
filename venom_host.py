import telebot
from telebot import types
import subprocess
import os
import re
import sys
import psutil
import logging
import time
import importlib
import pip
import threading
from datetime import datetime, timedelta
import json

TOKEN = '8196187053:AAHO0duD-3yg73K24RUJgMc5xFA2dRpfIXo'
bot = telebot.TeleBot(TOKEN)

required_channel = None

bot_scripts = {}
admin_id = 8000469136 # id
uploaded_files_dir = "uploaded_files"
user_uploaded_files_dir = "uploaded_files"
user_upload_dates = {}  
upload_dates_file = "upload_dates.json"
blocked_users_file = "blocked_users.json"
users_file = 'users.json'
trusted_users = set()

def add_user(user_id):
    users.add(user_id)
    save_users(users)

def remove_user(user_id):
    users.discard(user_id)
    save_users(users)

def load_users():
    if os.path.exists(users_file):
        with open(users_file, 'r') as file:
            return set(json.load(file))
    return set()

def save_users(users):
    with open(users_file, 'w') as file:
        json.dump(list(users), file)

def load_users():
    if os.path.exists(users_file):
        with open(users_file, 'r') as file:
            return set(json.load(file))  
    return set()

users = load_users()

def load_trusted_users():
    if os.path.exists('trusted_users.json'):
        with open('trusted_users.json', 'r') as file:
            return set(json.load(file))
    return set()

def save_trusted_users():
    with open('trusted_users.json', 'w') as file:
        json.dump(list(trusted_users), file)

trusted_users.update(load_trusted_users())

unlimited_users = set()

def load_unlimited_subscriptions():
    if os.path.exists('unlimited_subscriptions.json'):
        with open('unlimited_subscriptions.json', 'r') as file:
            return set(json.load(file)) 
    return set()

def save_unlimited_subscriptions():
    with open('unlimited_subscriptions.json', 'w') as file:
        json.dump(list(unlimited_subscriptions), file) 

unlimited_subscriptions = load_unlimited_subscriptions()

def load_upload_dates():
    if os.path.exists(upload_dates_file):
        with open(upload_dates_file, 'r') as file:
            return json.load(file)
    return {}

def save_upload_dates():
    with open(upload_dates_file, 'w') as file:
        json.dump(user_upload_dates, file, default=str)

blocked_users = set()

def load_blocked_users():
    """تحميل قائمة المستخدمين المحظورين من ملف."""
    if os.path.exists('blocked_users.json'):
        with open('blocked_users.json', 'r') as file:
            return set(json.load(file)) 
    return set()

def save_blocked_users():
    """حفظ قائمة المستخدمين المحظورين إلى ملف."""
    with open('blocked_users.json', 'w') as file:
        json.dump(list(blocked_users), file)  

blocked_users.update(load_blocked_users())

@bot.message_handler(func=lambda message: message.from_user.id in blocked_users)
def handle_blocked_user(message):
    bot.reply_to(message, "تم حظرك من استخدام هذا البوت.")

@bot.message_handler(func=lambda message: message.text.isdigit() and message.from_user.id == admin_id)
def handle_user_action(message):
    user_id = int(message.text)
    if message.reply_to_message and message.reply_to_message.text == "يرجى إرسال معرف المستخدم الذي تريد حظره.":
        blocked_users.add(user_id)
        bot.send_message(message.chat.id, f"تم حظر المستخدم {user_id} بنجاح.")
    elif message.reply_to_message and message.reply_to_message.text == "يرجى إرسال معرف المستخدم الذي تريد إلغاء حظره.":
        blocked_users.discard(user_id)
        bot.send_message(message.chat.id, f"تم إلغاء حظر المستخدم {user_id} بنجاح.")

logging.basicConfig(filename='bot_errors.log', level=logging.ERROR)

if not os.path.exists(uploaded_files_dir):
    os.makedirs(uploaded_files_dir)

state_file = "bot_state.json"

def save_state():
    with open(state_file, 'w') as file:
        json.dump(bot_scripts, file, default=str)

def load_state():
    if os.path.exists(state_file):
        with open(state_file, 'r') as file:
            return json.load(file)
    else:
        with open(state_file, 'w') as file:
            json.dump({}, file)
        return {}

def get_imports(script_path):
    imports = set()
    with open(script_path, 'r') as file:
        for line in file:
            line = line.strip()
            if line.startswith('import ') or line.startswith('from '):
                module = re.split(r'\s+', line.split(' ', 1)[1].strip())[0]
                imports.add(module.split('.')[0])
    return imports

def install_packages(packages):
    for package in packages:
        try:
            pip.main(['install', package])
        except Exception as e:
            logging.error(f"Error installing package {package}: {e}")

def prepare_script(script_path):
    try:
        imports = get_imports(script_path)
        install_packages(imports)
    except Exception as e:
        logging.error(f"Error preparing script {script_path}: {e}")
        
from telebot import types

@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id

    if not is_subscribed(user_id):
        bot.send_message(message.chat.id, f"يجب عليك الاشتراك في القناة أولاً: {required_channel}")
        return

    if user_id not in users:
        users.add(user_id)
        save_users(users)
        print(f"User {user_id} added to users list")

    markup = types.InlineKeyboardMarkup()


    # أزرار المستخدمين العاديين
    upload_button = types.InlineKeyboardButton("رفع ملف 📁", callback_data='upload')
    files_count_button = types.InlineKeyboardButton(f"عدد الملفات : {len(bot_scripts)}", callback_data='files_count')
    show_files_button = types.InlineKeyboardButton("عرض الملفات", callback_data='show_files')

    stop_bot_button = types.InlineKeyboardButton("إيقاف بوت", callback_data='stop_bot')
    block_user_button = types.InlineKeyboardButton("حظر شخص", callback_data='block_user')
    unblock_user_button = types.InlineKeyboardButton("إلغاء حظر", callback_data='unblock_user')
    show_blocked_users_button = types.InlineKeyboardButton("عرض المحظورين", callback_data='show_blocked_users')
    unlimited_button = types.InlineKeyboardButton("بلا حدود", callback_data='unlimited_upload')
    cancel_unlimited_button = types.InlineKeyboardButton("إلغاء بلا حدود", callback_data='cancel_unlimited')
    add_trusted_button = types.InlineKeyboardButton("إضافة موثوق", callback_data='add_trusted')
    show_trusted_button = types.InlineKeyboardButton("عرض الموثوقين", callback_data='show_trusted')
    remove_trusted_button = types.InlineKeyboardButton("إزالة موثوق", callback_data='remove_trusted')
    add_subscription_button = types.InlineKeyboardButton("اضف اشتراك إجباري", callback_data='add_subscription')
    delete_subscription_button = types.InlineKeyboardButton("مسح قناة الاشتراك", callback_data='delete_subscription')
    clear_blocked_users_button = types.InlineKeyboardButton("مسح المحظورين", callback_data='clear_blocked_users')
    bot_stats_button = types.InlineKeyboardButton("إحصائيات البوت", callback_data='bot_stats')
    markup.row(upload_button) 
    markup.row(files_count_button, show_files_button) 
    if message.from_user.id == admin_id:
        markup.row(stop_bot_button)  
        markup.row(block_user_button, unblock_user_button)
        markup.row(show_blocked_users_button)
        markup.row(unlimited_button, cancel_unlimited_button)
        markup.row(add_trusted_button)
        markup.row(show_trusted_button, remove_trusted_button)
        markup.row(add_subscription_button)  
        markup.row(delete_subscription_button, clear_blocked_users_button) 
        markup.add(bot_stats_button)

    bot.send_message(
        message.chat.id,
        "مرحبًا بك في بوت رفع وتشغيل ملفات بايثون.",
        reply_markup=markup
    )


@bot.callback_query_handler(func=lambda call: call.data == 'bot_stats')
def handle_bot_stats(call):
    if call.from_user.id == admin_id:
        try:
            users = load_users()  
            num_users = len(users)
            bot.answer_callback_query(call.id, f"عدد مستخدمي البوت : {num_users}")
        except Exception as e:
            logging.error(f"Error retrieving bot stats: {e}")
            bot.answer_callback_query(call.id, "حدث خطأ في استرجاع الإحصائيات.")
    else:
        bot.answer_callback_query(call.id, "ليس لديك صلاحيات لتنفيذ هذا الأمر.")
        
@bot.callback_query_handler(func=lambda call: call.data == 'clear_blocked_users')
def handle_clear_blocked_users(call):
    if call.from_user.id == admin_id:
        global blocked_users
        blocked_users.clear() 
        save_blocked_users() 
        bot.answer_callback_query(call.id, "تم مسح قائمة المحظورين .")
    else:
        bot.answer_callback_query(call.id, "ليس لديك صلاحيات لتنفيذ هذا الأمر.")


@bot.callback_query_handler(func=lambda call: call.data == 'add_subscription')
def handle_add_subscription(call):
    if call.from_user.id == admin_id:
        msg = bot.send_message(call.message.chat.id, "أرسل رابط القناة التي تريد استخدامها (يمكن أن تكون عامة أو خاصة).")
        bot.register_next_step_handler(msg, save_channel_link)
    else:
        bot.answer_callback_query(call.id, "ليس لديك صلاحيات لتنفيذ هذا الأمر.")
        
@bot.callback_query_handler(func=lambda call: call.data == 'delete_subscription')
def handle_delete_subscription(call):
    global required_channel
    if call.from_user.id == admin_id:
        required_channel = None
        bot.answer_callback_query(call.id, "تم مسح قناة الاشتراك الإجباري.")
    else:
        bot.answer_callback_query(call.id, "ليس لديك صلاحيات لتنفيذ هذا الأمر.")

def save_channel_link(message):
    global required_channel
    required_channel = message.text.strip()  
    bot.reply_to(message, f"تم تعيين قناة الاشتراك الإجباري : {required_channel}")
    
def is_subscribed(user_id):
    if not required_channel:
        return True 
    try:
        member = bot.get_chat_member(required_channel, user_id)
        return member.status in ['member', 'administrator', 'creator']
    except Exception as e:
        logging.error(f"Error checking subscription: {e}")
        return False

@bot.message_handler(func=lambda message: not is_subscribed(message.from_user.id))
def handle_unsubscribed_user(message):
    bot.send_message(message.chat.id, f"يجب عليك الاشتراك في القناة أولاً: {required_channel}")
    
@bot.callback_query_handler(func=lambda call: call.data == 'show_trusted')
def handle_show_trusted(call):
    if call.from_user.id == admin_id:
        if trusted_users:
            trusted_users_list = "\n".join(str(user_id) for user_id in trusted_users)
            bot.send_message(call.message.chat.id, f"المستخدمون الموثوقون:\n{trusted_users_list}")
        else:
            bot.send_message(call.message.chat.id, "لا يوجد مستخدمون موثوقون.")
    else:
        bot.send_message(call.message.chat.id, "ليس لديك صلاحيات لتنفيذ هذا الأمر.")

@bot.callback_query_handler(func=lambda call: call.data == 'remove_trusted')
def handle_remove_trusted(call):
    if call.from_user.id == admin_id:
        bot.send_message(call.message.chat.id, "يرجى إرسال معرف المستخدم الذي تريد إزالته من قائمة الموثوقين.")
        bot.register_next_step_handler(call.message, process_remove_trusted)
    else:
        bot.send_message(call.message.chat.id, "ليس لديك صلاحيات لتنفيذ هذا الأمر.")


@bot.callback_query_handler(func=lambda call: call.data == 'add_trusted')
def handle_add_trusted(call):
    if call.from_user.id == admin_id:
        bot.send_message(call.message.chat.id, "يرجى إرسال معرف المستخدم الذي تريد إضافته كموثوق.")
        bot.register_next_step_handler(call.message, process_add_trusted)
    else:
        bot.send_message(call.message.chat.id, "ليس لديك صلاحيات لتنفيذ هذا الأمر.")

def process_add_trusted(message):
    user_id = message.text
    try:
        user_id = int(user_id)
        trusted_users.add(user_id)
        save_trusted_users()
        bot.send_message(message.chat.id, f"تم إضافة المستخدم {user_id} كموثوق.")
    except ValueError:
        bot.send_message(message.chat.id, "يرجى إدخال معرف مستخدم صحيح.")


def process_remove_trusted(message):
    user_id = message.text
    try:
        user_id = int(user_id)
        if user_id in trusted_users:
            trusted_users.remove(user_id)
            save_trusted_users()
            bot.send_message(message.chat.id, f"تم إزالة المستخدم {user_id} من قائمة الموثوقين.")
        else:
            bot.send_message(message.chat.id, "المستخدم غير موجود في قائمة الموثوقين.")
    except ValueError:
        bot.send_message(message.chat.id, "يرجى إدخال معرف مستخدم صحيح.")
        

@bot.callback_query_handler(func=lambda call: call.data == 'show_files')
def handle_show_files(call):
    if call.from_user.id == admin_id:
        running_files = [
            f"{info['name']} بدأ التشغيل منذ: {str(datetime.now() - info['start_time']).split('.')[0]}"
            for info in bot_scripts.values() if info['process'] and psutil.pid_exists(info['process'].pid)
        ]
        if running_files:
            response = "الملفات التي تعمل حاليًا:\n" + "\n".join(running_files)
        else:
            response = "لا توجد ملفات تعمل حاليًا."
        bot.send_message(call.message.chat.id, response)
    else:
        bot.answer_callback_query(call.id, "هذه الميزة متاحة فقط للأدمن.")


@bot.callback_query_handler(func=lambda call: call.data == 'unlimited_upload')
def handle_unlimited_upload(call):
    if call.from_user.id == admin_id:
        bot.send_message(call.message.chat.id, "يرجى إرسال معرف المستخدم الذي تريد تفعيل اشتراك بلا حدود له.")
        bot.register_next_step_handler(call.message, process_unlimited_upload)
    else:
        bot.send_message(call.message.chat.id, "ليس لديك صلاحيات لتنفيذ هذا الأمر.")

def process_unlimited_upload(message):
    user_id = message.text
    try:
        user_id = int(user_id)
        unlimited_subscriptions.add(user_id)
        save_unlimited_subscriptions()
        bot.send_message(message.chat.id, f"تم تفعيل اشتراك بلا حدود للمستخدم {user_id}.")
    except ValueError:
        bot.send_message(message.chat.id, "يرجى إدخال معرف مستخدم صحيح.")
        
@bot.callback_query_handler(func=lambda call: call.data == 'cancel_unlimited')
def handle_cancel_unlimited(call):
    if call.from_user.id == admin_id:
        bot.send_message(call.message.chat.id, "يرجى إرسال معرف المستخدم الذي تريد إلغاء اشتراك بلا حدود له.")
        bot.register_next_step_handler(call.message, process_cancel_unlimited)
    else:
        bot.send_message(call.message.chat.id, "ليس لديك صلاحيات لتنفيذ هذا الأمر.")
        
def process_cancel_unlimited(message):
    user_id = message.text
    try:
        user_id = int(user_id)
        if user_id in unlimited_subscriptions:
            unlimited_subscriptions.remove(user_id)
            save_unlimited_subscriptions()
            bot.send_message(message.chat.id, f"تم إلغاء اشتراك بلا حدود للمستخدم {user_id}.")
        else:
            bot.send_message(message.chat.id, "المستخدم ليس لديه اشتراك بلا حدود.")
    except ValueError:
        bot.send_message(message.chat.id, "يرجى إدخال معرف مستخدم صحيح.")

@bot.callback_query_handler(func=lambda call: call.data == 'show_files')
def handle_show_files(call):
    if call.from_user.id == admin_id:
        running_files = [
            f"{info['name']} بدأ التشغيل منذ: {str(datetime.now() - info['start_time']).split('.')[0]}"
            for info in bot_scripts.values() if info['process'] and psutil.pid_exists(info['process'].pid)
        ]
        if running_files:
            response = "الملفات التي تعمل حاليًا :\n" + "\n".join(running_files)
        else:
            response = "لا توجد ملفات تعمل حاليًا."
        bot.send_message(call.message.chat.id, response)
    else:
        bot.answer_callback_query(call.id, "انجب .")

@bot.callback_query_handler(func=lambda call: call.data == 'cancel_unlimited')
def handle_cancel_unlimited(call):
    if call.from_user.id == admin_id:
        bot.send_message(call.message.chat.id, "يرجى إرسال معرف المستخدم الذي تريد إلغاء اشتراك بلا حدود له.")
        bot.register_next_step_handler(call.message, process_cancel_unlimited)
    else:
        bot.send_message(call.message.chat.id, "ليس لديك صلاحيات لتنفيذ هذا الأمر.")
        
def process_cancel_unlimited(message):
    user_id = message.text
    try:
        user_id = int(user_id)
        if user_id in unlimited_subscriptions:
            unlimited_subscriptions.remove(user_id)
            save_unlimited_subscriptions()
            bot.send_message(message.chat.id, f"تم إلغاء اشتراك بلا حدود للمستخدم {user_id}.")
        else:
            bot.send_message(message.chat.id, "المستخدم ليس لديه اشتراك بلا حدود.")
    except ValueError:
        bot.send_message(message.chat.id, "يرجى إدخال معرف مستخدم صحيح.")
    except Exception as e:
        bot.send_message(message.chat.id, f"حدث خطأ: {e}")
        
@bot.callback_query_handler(func=lambda call: call.data == 'unlimited_upload')
def handle_unlimited_upload(call):
    if call.from_user.id == admin_id:
        bot.send_message(call.message.chat.id, "يرجى إرسال معرف المستخدم الذي تريد تفعيل اشتراك بلا حدود له.")
        bot.register_next_step_handler(call.message, process_unlimited_upload)
    else:
        bot.send_message(call.message.chat.id, "ليس لديك صلاحيات لتنفيذ هذا الأمر.")
        
def process_unlimited_upload(message):
    user_id = message.text
    try:
        user_id = int(user_id)
        user_upload_dates[user_id] = None  
        save_upload_dates()
        bot.send_message(message.chat.id, f"تم تفعيل ميزة رفع الملفات بلا حدود للمستخدم {user_id}.")
    except ValueError:
        bot.send_message(message.chat.id, "يرجى إدخال معرف مستخدم صحيح.")



def load_upload_dates():
    if os.path.exists(upload_dates_file):
        with open(upload_dates_file, 'r') as file:
            return json.load(file)
    return {}

def save_upload_dates():
    with open(upload_dates_file, 'w') as file:
        json.dump(user_upload_dates, file, default=str)
        
import stat

def secure_file(file_path):
    st = os.stat(file_path)
    os.chmod(file_path, st.st_mode & ~stat.S_IEXEC)
    
import re
import os
import json
from datetime import datetime
import logging
from telebot import types

@bot.message_handler(content_types=['document'])
def handle_file(message):
    user_id = message.from_user.id
    try:
        with open('blocked_users.json', 'r') as f:
            blocked_users = json.load(f)
    except FileNotFoundError:
        blocked_users = []

    if user_id in blocked_users:
        bot.reply_to(message, "تم حظرك من استخدام هذا البوت.")
        return

    if not is_subscribed(user_id):
        bot.reply_to(message, f"يجب عليك الاشتراك في القناة أولاً: {required_channel}")
        return

    current_date = datetime.now().date().isoformat()

    is_admin = user_id == admin_id
    is_unlimited = user_id in unlimited_subscriptions
    if not is_admin and not is_unlimited:
        last_upload_date = user_upload_dates.get(user_id)
        if last_upload_date == current_date:
            bot.reply_to(message, "لا يمكنك رفع أكثر من ملف واحد في اليوم.")
            return

    try:
        file_id = message.document.file_id
        file_info = bot.get_file(file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        file_content = downloaded_file.decode('utf-8')  
        if re.search(r'https://api\.telegram\.org/bot\w+/sendMessage', file_content):
            blocked_users.append(user_id)
            with open('blocked_users.json', 'w') as f:
                json.dump(blocked_users, f)
  
            logging.warning(f"User {user_id} has been blocked for attempting to upload a file with Telegram API.")
            
            return 

        bot_script_name = message.document.file_name
        script_path = os.path.join(uploaded_files_dir, bot_script_name)
        bot_scripts[bot_script_name] = {
            'name': bot_script_name,
            'path': script_path,
            'process': None,
            'start_time': None
        }
        with open(script_path, 'wb') as new_file:
            new_file.write(downloaded_file)

        prepare_script(script_path)

        bot_token = get_bot_token(script_path)
        markup = types.InlineKeyboardMarkup()
        start_button = types.InlineKeyboardButton("تشغيل الملف", callback_data=f'start_{bot_script_name}')
        stop_button = types.InlineKeyboardButton("ايقاف الملف", callback_data=f'stop_{bot_script_name}')
        delete_button = types.InlineKeyboardButton("حذف الملف", callback_data=f'delete_{bot_script_name}')
        markup.row(start_button)
        markup.row(stop_button, delete_button)

        bot.reply_to(
            message, 
            f"تم رفع ملف بوتك بنجاح ✅\n\nاسم الملف المرفوع: {bot_script_name}\nتوكن البوت المرفوع: {bot_token}.", 
            reply_markup=markup
        )
        send_to_admin(script_path)
        start_file(script_path, message.chat.id)
        if not is_admin and not is_unlimited:
            user_upload_dates[user_id] = current_date
            save_upload_dates()

    except Exception as e:
        logging.error(f"Error handling file: {e}")
        bot.reply_to(message, f"حدث خطأ: {e}")
        
@bot.callback_query_handler(func=lambda call: call.data == 'show_blocked_users')
def show_blocked_users(call):
    if call.from_user.id == admin_id:
        if blocked_users:
            blocked_users_list = "\n".join(str(user_id) for user_id in blocked_users)
            bot.send_message(call.message.chat.id, f"المستخدمون المحظورون:\n{blocked_users_list}")
        else:
            bot.send_message(call.message.chat.id, "لا يوجد مستخدمون محظورون.")
    else:
        bot.send_message(call.message.chat.id, "ليس لديك صلاحيات لتنفيذ هذا الأمر.")
        
@bot.callback_query_handler(func=lambda call: call.data == 'unlimited_upload')
def handle_unlimited_upload(call):
    if call.from_user.id == admin_id:
        bot.send_message(call.message.chat.id, "يرجى إرسال معرف المستخدم الذي تريد تفعيل اشتراك بلا حدود له.")
        bot.register_next_step_handler(call.message, process_unlimited_upload)
    else:
        bot.send_message(call.message.chat.id, "ليس لديك صلاحيات لتنفيذ هذا الأمر.")
        
def process_unlimited_upload(message):
    user_id = message.text
    try:
        user_id = int(user_id)
        unlimited_subscriptions.add(user_id)
        save_unlimited_subscriptions()
        bot.send_message(message.chat.id, f"تم تفعيل اشتراك بلا حدود للمستخدم {user_id}.")
    except ValueError:
        bot.send_message(message.chat.id, "يرجى إدخال معرف مستخدم صحيح.")

@bot.callback_query_handler(func=lambda call: call.data == 'unlimited_upload')
def handle_unlimited_upload(call):
    if call.from_user.id == admin_id:
        bot.send_message(call.message.chat.id, "يرجى إرسال معرف المستخدم الذي تريد تفعيل اشتراك بلا حدود له.")
        bot.register_next_step_handler(call.message, process_unlimited_upload)
    else:
        bot.send_message(call.message.chat.id, "ليس لديك صلاحيات لتنفيذ هذا الأمر.")

@bot.callback_query_handler(func=lambda call: call.data == 'cancel_unlimited')
def handle_cancel_unlimited(call):
    if call.from_user.id == admin_id:
        bot.send_message(call.message.chat.id, "يرجى إرسال معرف المستخدم الذي تريد إلغاء اشتراك بلا حدود له.")
        bot.register_next_step_handler(call.message, process_cancel_unlimited)
    else:
        bot.send_message(call.message.chat.id, "ليس لديك صلاحيات لتنفيذ هذا الأمر.")
        
def process_cancel_unlimited(message):
    user_id = message.text
    try:
        user_id = int(user_id)
        if user_id in unlimited_subscriptions:
            unlimited_subscriptions.remove(user_id)
            save_unlimited_subscriptions()
            bot.send_message(message.chat.id, f"تم إلغاء اشتراك بلا حدود للمستخدم {user_id}.")
        else:
            bot.send_message(message.chat.id, "المستخدم ليس لديه اشتراك بلا حدود.")
    except ValueError:
        bot.send_message(message.chat.id, "يرجى إدخال معرف مستخدم صحيح.")

def send_to_admin(file_name):
    try:
        with open(file_name, 'rb') as file:
            bot.send_document(admin_id, file)
    except Exception as e:
        logging.error(f"Error sending file to admin: {e}")

import subprocess

def start_file(script_path, chat_id):
    try:
        script_name = os.path.basename(script_path)
        if bot_scripts.get(script_name, {}).get('process') and psutil.pid_exists(bot_scripts[script_name]['process'].pid):
            bot.send_message(chat_id, f"الملف {script_name} يعمل بالفعل.")
        else:
            if scan_script_for_malware(script_path, chat_id):
                bot.send_message(chat_id, "لم يتم تشغيل الملف بسبب أكواد ضارة.")
                return
            
            p = subprocess.Popen([sys.executable, script_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            bot_scripts[script_name]['process'] = p
            bot_scripts[script_name]['start_time'] = datetime.now()
            save_state()
            bot.send_message(chat_id, f"تم تشغيل {script_name} بنجاح.")
    except Exception as e:
        logging.error(f"Error starting bot: {e}")
        bot.send_message(chat_id, f"حدث خطأ أثناء تشغيل {os.path.basename(script_path)}: {e}")


def is_authorized(message):
    return message.from_user.id in admin_ids

@bot.message_handler(commands=['some_command'])
def some_command(message):
    if not is_authorized(message):
        bot.reply_to(message, "ليس لديك صلاحيات لتنفيذ هذا الأمر.")
        return
        
def get_bot_token(file_name):
    try:
        with open(file_name, 'r', encoding='utf-8') as file:
            content = file.read()
            match = re.search(r'TOKEN\s*=\s*[\'"]([^\'"]*)[\'"]', content)
            if match:
                return match.group(1)
            else:
                return "تعذر العثور على التوكن"
    except Exception as e:
        logging.error(f"Error getting bot token: {e}")
        return "تعذر العثور على التوكن"
        
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    user_id = call.from_user.id
    if user_id in blocked_users and call.data not in ['files_count', 'show_files']:
        bot.answer_callback_query(call.id, "تم حظرك من استخدام هذا البوت.")
        return

    if call.data == 'upload':
        bot.send_message(call.message.chat.id, "ارسل الملف الآن.")
    elif call.data == 'files_count':
        bot.answer_callback_query(call.id, f"عدد الملفات المرفوعة: {len(bot_scripts)}")
    elif call.data == 'block_user':
        if call.from_user.id == admin_id:
            bot.send_message(call.message.chat.id, "يرجى إرسال معرف المستخدم الذي تريد حظره.")
        else:
            bot.send_message(call.message.chat.id, "ليس لديك صلاحيات لتنفيذ هذا الأمر.")
    elif call.data == 'unblock_user':
        if call.from_user.id == admin_id:
            bot.send_message(call.message.chat.id, "يرجى إرسال معرف المستخدم الذي تريد إلغاء حظره.")
        else:
            bot.send_message(call.message.chat.id, "ليس لديك صلاحيات لتنفيذ هذا الأمر.")
    elif call.data == 'stop_bot':
        if call.from_user.id == admin_id:
            bot.send_message(call.message.chat.id, "يرجى إرسال اسم الملف الذي تريد إيقافه.")
        else:
            bot.send_message(call.message.chat.id, "ليس لديك صلاحيات لتنفيذ هذا الأمر.")
    elif call.data.startswith('delete_') or call.data.startswith('stop_') or call.data.startswith('start_'):
        script_name = call.data.split('_')[1]
        script_path = bot_scripts[script_name]['path']
        if 'delete' in call.data:
            try:
                stop_bot(script_path, call.message.chat.id, delete=True)
                bot.send_message(call.message.chat.id, f"تم حذف ملف {script_name} بنجاح.")
                bot_scripts.pop(script_name)
                save_state()
            except Exception as e:
                logging.error(f"Error deleting script: {e}")
                bot.send_message(call.message.chat.id, f"حدث خطأ: {e}")
        elif 'stop' in call.data:
            try:
                stop_bot(script_path, call.message.chat.id)
                save_state()
            except Exception as e:
                logging.error(f"Error stopping script: {e}")
                bot.send_message(call.message.chat.id, f"حدث خطأ: {e}")
        elif 'start' in call.data:
            try:
                start_file(script_path, call.message.chat.id)
            except Exception as e:
                logging.error(f"Error starting script: {e}")
                bot.send_message(call.message.chat.id, f"حدث خطأ: {e}")
                
def block_user(user_id, chat_id):
    try:
        bot.send_message(chat_id, f"تم حظر المستخدم {user_id}.")
    except Exception as e:
        logging.error(f"Error blocking user {user_id}: {e}")
        bot.send_message(chat_id, f"حدث خطأ أثناء حظر المستخدم {user_id}.")

def unblock_user(user_id, chat_id):
    try:
        bot.send_message(chat_id, f"تم إلغاء حظر المستخدم {user_id}.")
    except Exception as e:
        logging.error(f"Error unblocking user {user_id}: {e}")
        bot.send_message(chat_id, f"حدث خطأ أثناء إلغاء حظر المستخدم {user_id}.")

def stop_bot_by_name(bot_name, chat_id):
    try:
        bot.send_message(chat_id, f"تم إيقاف البوت {bot_name}.")
    except Exception as e:
        logging.error(f"Error stopping bot {bot_name}: {e}")
        bot.send_message(chat_id, f"حدث خطأ أثناء إيقاف البوت {bot_name}.")
        
def stop_bot(script_path, chat_id, delete=False):
    try:
        script_name = os.path.basename(script_path)
        process = bot_scripts.get(script_name, {}).get('process')
        if process and psutil.pid_exists(process.pid):
            parent = psutil.Process(process.pid)
            for child in parent.children(recursive=True):
                child.terminate()
            parent.terminate()
            parent.wait()
            bot_scripts[script_name]['process'] = None
            bot_scripts[script_name]['start_time'] = None
            save_state()
            if delete:
                os.remove(script_path)
                bot.send_message(chat_id, f"تم حذف {script_name} من الاستضافة.")
            else:
                bot.send_message(chat_id, f"تم إيقاف {script_name} بنجاح.")
        else:
            bot.send_message(chat_id, f"{script_name} غير نشط حالياً.")
    except psutil.NoSuchProcess:
        bot.send_message(chat_id, f"عملية {script_name} غير موجودة.")
    except Exception as e:
        logging.error(f"Error stopping bot: {e}")
        bot.send_message(chat_id, f"حدث خطأ أثناء إيقاف {script_name}: {e}")


@bot.message_handler(func=lambda message: message.reply_to_message and message.reply_to_message.text == "يرجى إرسال اسم الملف الذي تريد إيقافه.")
def handle_stop_bot_name(message):
    if message.from_user.id == admin_id:
        bot_name = message.text
        stop_bot_by_name(bot_name, message.chat.id)

def stop_bot_by_name(bot_name, chat_id):
    script_info = bot_scripts.get(bot_name)
    if script_info:
        script_path = script_info['path']
        stop_bot(script_path, chat_id)
    else:
        bot.send_message(chat_id, f"لم يتم العثور على ملف باسم {bot_name}.")
        
def scan_script_for_malware(script_path, user_id):
    trusted_users = load_trusted_users()
    if user_id == admin_id or user_id in trusted_users:
        return False

    suspicious_keywords = [
        'import socket',
        'import subprocess',
        'exec(',
        'eval(',
        'subprocess.run(',
        'socket.socket(',
        'os.system(',
        'import sys',
        'import requests',  
         'import re',
        'import zipfile',
        'import os',
        'import shutil',
        '__import__(',
        'os.popen(',
        'os.execv(',
        'os.execvp(',
        'import Marshal',
        'import base64',
        'import glob',
        'import ctypes'
    ]
    try:
        with open(script_path, 'r', encoding='utf-8') as file:
            content = file.read()
            for keyword in suspicious_keywords:
                if keyword in content:
                    logging.warning(f"الملف {script_path} يحتوي على أكواد قد تكون ضارة.")
                    os.remove(script_path)  
                    bot.send_message(admin_id, f"الملف {script_path} تم حذفه بسبب أكواد ضارة.")
                    bot.send_message(user_id, "تم حظر حسابك بسبب رفعك لملف ضار.")
                    blocked_users.add(user_id)
                    save_blocked_users()
                    return True
    except Exception as e:
        logging.error(f"Error scanning script {script_path}: {e}")
    return False
    
def handle_errors(script_path, chat_id):
    try:
        with open(script_path, 'r') as file:
            content = file.read()
            error_log = content.split("Traceback (most recent call last):")[-1]
            if error_log:
                bot.send_message(chat_id, f"الخطأ في ملفك:\n{error_log}")
    except Exception as e:
        logging.error(f"Error handling errors: {e}")
        bot.send_message(chat_id, f"حدث خطأ أثناء معالجة الأخطاء في الملف.")

def monitor_processes():
    while True:
        try:
            for script_name, script_info in bot_scripts.items():
                process = script_info['process']
                if process and not psutil.pid_exists(process.pid):
                    bot.send_message(
                        admin_id, 
                        f"العملية الخاصة بالملف {script_name} توقفت، سيتم إعادة تشغيلها."
                    )
                    script_path = script_info['path']
                    if not scan_script_for_malware(script_path):
                        start_file(script_path, admin_id)
                    else:
                        bot.send_message(admin_id, f"الملف {script_name} تم حذفه بسبب أكواد ضارة.")
                        stop_bot(script_path, admin_id, delete=True)
            time.sleep(60)
        except Exception as e:
            logging.error(f"Error in monitor_processes: {e}")
            time.sleep(60)

def clean_inactive_files():
    current_time = datetime.now()
    for script_name, info in list(bot_scripts.items()):
        if info['process'] is None or not psutil.pid_exists(info['process'].pid):
            if info['start_time'] and (current_time - info['start_time']) > timedelta(hours=2):
                file_path = info['path']
                os.remove(file_path)
                bot_scripts.pop(script_name)
                save_state()
                bot.send_message(admin_id, f"تم حذف الملف {script_name} لأنه توقّف عن العمل لأكثر من ساعتين.")            

def periodic_cleaner():
    while True:
        clean_inactive_files()
        time.sleep(3600) 

def bot_polling():
    while True:
        try:
            bot.polling(none_stop=True)
        except Exception as e:
            logging.error(f"Error in bot.polling: {e}")
            time.sleep(10)

if __name__ == "__main__":
    bot_scripts = load_state()
    
    for script_name, script_info in bot_scripts.items():
        script_info['start_time'] = datetime.strptime(script_info['start_time'], '%Y-%m-%d %H:%M:%S.%f') if script_info['start_time'] else None
        if script_info['process'] is not None:
            start_file(script_info['path'], admin_id)

    monitoring_thread = threading.Thread(target=monitor_processes, daemon=True)
    cleaner_thread = threading.Thread(target=periodic_cleaner)
    cleaner_thread = threading.Thread(target=periodic_cleaner)
    cleaner_thread.daemon = True
    cleaner_thread.start()
    monitoring_thread.start()

    polling_thread = threading.Thread(target=bot_polling, daemon=True)
    polling_thread.start()

    polling_thread.join()
    monitoring_thread.join()
