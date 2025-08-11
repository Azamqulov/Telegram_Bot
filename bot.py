#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
IT Center Telegram Bot – Firestore version with Channel Subscription
Python 3.13 + python-telegram-bot 21.x
"""

import os
import re
import logging
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Telegram imports (v21)
from telegram import (
    Update, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove,
    InlineKeyboardButton, InlineKeyboardMarkup,
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, ConversationHandler, filters,
)

# Firebase Admin
import firebase_admin
from firebase_admin import credentials, firestore

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID", "0"))
REQUIRED_CHANNEL = os.getenv("REQUIRED_CHANNEL", "@ITCenter_01")  # Kanal username yoki ID

# Firebase setup
try:
    cred_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "service-account.json")
    logger.info(f"Firebase credential file: {cred_path}")

    if not os.path.exists(cred_path):
        raise FileNotFoundError(f"Firebase credential file not found: {cred_path}")

    cred = credentials.Certificate(cred_path)

    if not firebase_admin._apps:
        firebase_admin.initialize_app(cred)
        logger.info("Firebase app initialized successfully")

    db = firestore.client()
    logger.info("Firestore client created successfully")

    # Test connection
    test_collection = db.collection('test').limit(1)
    list(test_collection.stream())
    logger.info("Firestore connection successful!")

except Exception as e:
    logger.error(f"Firebase setup error: {e}")
    raise

# Emojis and design elements
EMOJI = {
    'welcome': '🎉',
    'register': '📝',
    'courses': '📚',
    'contact': '☎️',
    'success': '✅',
    'error': '❌',
    'info': 'ℹ️',
    'phone': '📱',
    'age': '🎂',
    'name': '👤',
    'course': '🎓',
    'time': '⏰',
    'money': '💰',
    'location': '📍',
    'new': '🆕',
    'cancel': '❌',
    'admin': '👑',
    'add': '➕',
    'edit': '✏️',
    'delete': '🗑️',
    'broadcast': '📢',
    'stats': '📊',
    'back': '⬅️',
    'save': '💾',
    'announce': '📣',
    'subscribe': '🔔',
    'warning': '⚠️',
    'check': '✔️',
}

# Conversation states
FULLNAME, AGE, PHONE, COURSE = range(4)
ADD_COURSE_NAME, ADD_COURSE_DURATION, ADD_COURSE_PRICE, ADD_COURSE_DESC = range(101, 105)
EDIT_COURSE_SELECT, EDIT_COURSE_FIELD, EDIT_COURSE_VALUE = range(105, 108)
BROADCAST_MESSAGE = 108
DELETE_COURSE_SELECT = 109

# Helper functions
def is_admin(user_id):
    """Check if user is admin"""
    return user_id == ADMIN_CHAT_ID

async def check_subscription(context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Check if user is subscribed to required channel"""
    try:
        chat_member = await context.bot.get_chat_member(REQUIRED_CHANNEL, user_id)
        return chat_member.status in ['member', 'administrator', 'creator']
    except Exception as e:
        logger.error(f"Error checking subscription: {e}")
        return False

def create_subscription_keyboard():
    """Create subscription keyboard"""
    keyboard = [
        [InlineKeyboardButton(f'{EMOJI["subscribe"]} Kanalga obuna bo\'lish', url=f'https://t.me/{REQUIRED_CHANNEL.replace("@", "")}')],
        [InlineKeyboardButton(f'{EMOJI["check"]} Obunani tekshirish', callback_data='check_subscription')]
    ]
    return InlineKeyboardMarkup(keyboard)

async def subscription_required_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send subscription required message"""
    subscription_text = f"""
{EMOJI['warning']} <b>Diqqat!</b>

{EMOJI['info']} Botdan to'liq foydalanish uchun bizning kanalimizga obuna bo'ling!

{EMOJI['subscribe']} <b>Kanal:</b> {REQUIRED_CHANNEL}

{EMOJI['check']} Obuna bo'lgandan so'ng "Obunani tekshirish" tugmasini bosing.
"""
    
    await update.message.reply_text(
        subscription_text,
        parse_mode='HTML',
        reply_markup=create_subscription_keyboard()
    )

async def check_subscription_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle subscription check callback"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    
    if await check_subscription(context, user_id):
        success_text = f"""
{EMOJI['success']} <b>Rahmat!</b>

{EMOJI['check']} Siz muvaffaqiyatli obuna bo'ldingiz!
Endi botdan to'liq foydalanishingiz mumkin.

{EMOJI['info']} Asosiy menyuga o'tish uchun /start buyrug'ini bosing.
"""
        await query.edit_message_text(success_text, parse_mode='HTML')
        
        # Save subscription status
        try:
            user_ref = db.collection('users').document(str(user_id))
            user_ref.update({'subscribed': True, 'subscription_date': firestore.SERVER_TIMESTAMP})
        except Exception as e:
            logger.error(f"Error updating subscription status: {e}")
            
    else:
        error_text = f"""
{EMOJI['error']} <b>Obuna topilmadi!</b>

{EMOJI['warning']} Iltimos, avval kanalga obuna bo'ling:
{REQUIRED_CHANNEL}

{EMOJI['info']} Keyin qaytadan "Obunani tekshirish" tugmasini bosing.
"""
        await query.edit_message_text(
            error_text, 
            parse_mode='HTML',
            reply_markup=create_subscription_keyboard()
        )

def is_valid_age(age_text):
    """Validate age input"""
    try:
        age = int(age_text.strip())
        return 5 <= age <= 100
    except ValueError:
        return False

def format_phone(phone):
    """Format phone number"""
    digits = re.sub(r'[^\d]', '', phone)
    if digits.startswith('998'):
        return f"+{digits}"
    elif len(digits) == 9:
        return f"+998{digits}"
    return phone

def is_valid_name(name):
    """Validate name input"""
    return re.match(r'^[a-zA-ZА-Яа-яЁёЎўҚқҒғҲҳ\s\-\']+$', name) and len(name.split()) >= 2

def is_valid_phone(phone):
    """Validate phone number"""
    return re.match(r'^[\+]?[0-9\s\-\(\)]{9,15}$', phone)

def create_main_keyboard():
    """Create main keyboard"""
    keyboard = [
        [f'{EMOJI["register"]} Ro\'yxatdan o\'tish', f'{EMOJI["courses"]} Kurslar ro\'yxati'],
        [f'{EMOJI["contact"]} Bog\'lanish', f'{EMOJI["info"]} Ma\'lumot']
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)

def create_admin_keyboard():
    """Create admin keyboard"""
    keyboard = [
        [f'{EMOJI["add"]} Kurs qo\'shish', f'{EMOJI["edit"]} Kurs tahrirlash'],
        [f'{EMOJI["delete"]} Kurs o\'chirish', f'{EMOJI["broadcast"]} E\'lon yuborish'],
        [f'{EMOJI["stats"]} Statistika', f'{EMOJI["back"]} Asosiy menu']
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)

async def save_user_interaction(user_id, username, first_name):
    """Save user interaction data"""
    try:
        user_data = {
            'user_id': user_id,
            'username': username or '',
            'first_name': first_name or '',
            'last_interaction': firestore.SERVER_TIMESTAMP
        }

        user_ref = db.collection('users').document(str(user_id))
        user_ref.set(user_data, merge=True)

    except Exception as e:
        logger.error(f"Error saving user interaction: {e}")

# Subscription check decorator
async def require_subscription(func):
    """Decorator to check subscription before allowing access"""
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id
        
        # Admin bypass
        if is_admin(user_id):
            return await func(update, context, *args, **kwargs)
        
        # Check subscription
        if not await check_subscription(context, user_id):
            await subscription_required_message(update, context)
            return
        
        return await func(update, context, *args, **kwargs)
    
    return wrapper

# Start handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_name = user.first_name or "Foydalanuvchi"

    await save_user_interaction(user.id, user.username, user.first_name)

    if is_admin(user.id):
        welcome_text = f"""
{EMOJI['admin']} <b>Admin panelga xush kelibsiz, {user_name}!</b>

{EMOJI['info']} Admin sifatida siz:
• Kurslarni boshqara olasiz
• E'lonlar yuborish mumkin
• Statistika ko'ra olasiz
• Oddiy foydalanuvchi funksiyalarini ham ishlatish mumkin
• Obuna bo'lish talabidan ozod

Kerakli bo'limni tanlang:
"""
        await update.message.reply_text(
            welcome_text,
            reply_markup=create_admin_keyboard(),
            parse_mode='HTML'
        )
    else:
        # Check subscription for regular users
        if not await check_subscription(context, user.id):
            await subscription_required_message(update, context)
            return
        
        welcome_text = f"""
{EMOJI['welcome']} <b>IT Center botiga xush kelibsiz, {user_name}!</b>

{EMOJI['info']} Bu bot orqali siz:
• Kurslarimizga ro'yxatdan o'ta olasiz
• Barcha kurslar haqida ma'lumot olasiz
• Biz bilan bog'lana olasiz

Kerakli bo'limni tanlang:
"""
        await update.message.reply_text(
            welcome_text,
            reply_markup=create_main_keyboard(),
            parse_mode='HTML'
        )

# Registration handlers (with subscription check)
async def reg_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # Admin bypass
    if not is_admin(user_id):
        if not await check_subscription(context, user_id):
            await subscription_required_message(update, context)
            return
    
    welcome_reg = f"""
{EMOJI['register']} <b>Ro'yxatdan o'tish</b>

{EMOJI['name']} Iltimos, <b>ism va familiyangizni</b> to'liq kiriting:

<i>Masalan: Ahmadjon Valiyev</i>
"""
    await update.message.reply_text(
        welcome_reg,
        reply_markup=ReplyKeyboardRemove(),
        parse_mode='HTML'
    )
    return FULLNAME

async def reg_fullname(update: Update, context: ContextTypes.DEFAULT_TYPE):
    fullname = update.message.text.strip()

    if len(fullname) < 2:
        await update.message.reply_text(
            f"{EMOJI['error']} Ism juda qisqa! Iltimos, to'liq ism va familiyangizni kiriting."
        )
        return FULLNAME

    if not is_valid_name(fullname):
        await update.message.reply_text(
            f"{EMOJI['error']} Iltimos, faqat harflardan iborat ism kiriting."
        )
        return FULLNAME

    context.user_data['fullName'] = fullname

    age_text = f"""
{EMOJI['age']} <b>Yoshingizni kiriting:</b>

{EMOJI['info']} <i>Faqat raqam kiriting (5-100 oralig'ida)</i>
"""
    await update.message.reply_text(age_text, parse_mode='HTML')
    return AGE

async def reg_age(update: Update, context: ContextTypes.DEFAULT_TYPE):
    age_input = update.message.text.strip()

    if not is_valid_age(age_input):
        error_text = f"""
{EMOJI['error']} <b>Noto'g'ri yosh!</b>

{EMOJI['info']} Iltimos:
• Faqat raqam kiriting
• 5 dan 100 gacha bo'lgan yoshni kiriting

<i>Masalan: 25</i>
"""
        await update.message.reply_text(error_text, parse_mode='HTML')
        return AGE

    context.user_data['age'] = age_input

    phone_kb = [[KeyboardButton(f'{EMOJI["phone"]} Telefonni yuborish', request_contact=True)]]
    phone_text = f"""
{EMOJI['phone']} <b>Telefon raqamingizni yuboring:</b>

{EMOJI['info']} Ikki usuldan birini tanlang:
• Pastdagi tugmani bosing
• Yoki qo'lda kiriting (+998901234567)
"""

    await update.message.reply_text(
        phone_text,
        reply_markup=ReplyKeyboardMarkup(phone_kb, one_time_keyboard=True, resize_keyboard=True),
        parse_mode='HTML'
    )
    return PHONE

async def reg_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.contact:
        phone = update.message.contact.phone_number
    else:
        phone = update.message.text.strip()
        if not is_valid_phone(phone):
            await update.message.reply_text(
                f"{EMOJI['error']} Noto'g'ri telefon raqami! Iltimos, to'g'ri formatda kiriting.\n"
                f"Masalan: +998901234567"
            )
            return PHONE

    context.user_data['phone'] = format_phone(phone)

    try:
        logger.info("Getting courses from Firestore...")
        courses_ref = db.collection('courses')
        courses_docs = courses_ref.stream()
        courses = []

        for doc in courses_docs:
            course_data = doc.to_dict()
            course_data['id'] = doc.id
            courses.append(course_data)
            logger.info(f"Found course: {course_data.get('name', 'Unknown')}")

        if not courses:
            logger.warning("No courses found")
            await update.message.reply_text(
                f'{EMOJI["error"]} Hozircha kurslar mavjud emas. Keyinroq urinib ko\'ring.\n'
                f'Admin bilan bog\'laning: @ITCenter_01',
                reply_markup=create_main_keyboard()
            )
            return ConversationHandler.END

        buttons = []
        for course in courses:
            course_name = course.get('name', 'Noma\'lum kurs')
            course_text = f"{EMOJI['course']} {course_name}"
            buttons.append([InlineKeyboardButton(course_text, callback_data=course['id'])])

        buttons.append([InlineKeyboardButton(f"{EMOJI['cancel']} Bekor qilish", callback_data='cancel')])

        course_selection_text = f"""
{EMOJI['course']} <b>Kursni tanlang:</b>

{EMOJI['info']} <i>Quyidagi kurslardan birini tanlang:</i>
"""

        await update.message.reply_text(
            course_selection_text,
            reply_markup=InlineKeyboardMarkup(buttons),
            parse_mode='HTML'
        )
        return COURSE

    except Exception as e:
        logger.error(f"Error getting courses: {e}")
        await update.message.reply_text(
            f'{EMOJI["error"]} Kurslarni yuklashda xatolik yuz berdi.\n'
            f'Xatolik: {str(e)}\n'
            f'Admin bilan bog\'laning: @ITCenter_01',
            reply_markup=create_main_keyboard()
        )
        return ConversationHandler.END

async def reg_course(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == 'cancel':
        await query.edit_message_text(f'{EMOJI["cancel"]} Ro\'yxatdan o\'tish bekor qilindi.')
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f'{EMOJI["info"]} Asosiy menyuga qaytdingiz.',
            reply_markup=create_main_keyboard()
        )
        return ConversationHandler.END

    try:
        course_id = query.data
        logger.info(f"Selected course ID: {course_id}")

        course_doc = db.collection('courses').document(course_id).get()

        if not course_doc.exists:
            logger.error(f"Course not found: {course_id}")
            await query.edit_message_text(f'{EMOJI["error"]} Kurs topilmadi!')
            return ConversationHandler.END

        course_data = course_doc.to_dict()
        course_name = course_data.get('name', 'Noma\'lum kurs')
        logger.info(f"Course data: {course_name}")

        registration_data = {
            'tg_id': update.effective_user.id,
            'username': update.effective_user.username or '',
            'fullName': context.user_data['fullName'],
            'age': context.user_data['age'],
            'phone': context.user_data['phone'],
            'course': course_name,
            'course_id': course_id,
            'created_at': firestore.SERVER_TIMESTAMP,
        }

        logger.info(f"Registration data: {registration_data}")
        doc_ref = db.collection('registrations').add(registration_data)
        logger.info(f"Registration saved successfully: {doc_ref}")

        success_text = f"""
{EMOJI['success']} <b>Tabriklaymiz!</b>

{EMOJI['info']} Arizangiz muvaffaqiyatli qabul qilindi!

<b>Ma'lumotlaringiz:</b>
{EMOJI['name']} Ism: {registration_data['fullName']}
{EMOJI['age']} Yosh: {registration_data['age']}
{EMOJI['phone']} Telefon: {registration_data['phone']}
{EMOJI['course']} Kurs: {course_name}

{EMOJI['time']} Tez orada operatorlarimiz siz bilan bog'lanishadi!
"""

        await query.edit_message_text(success_text, parse_mode='HTML')

        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f'{EMOJI["info"]} Asosiy menyuga qaytdingiz.',
            reply_markup=create_main_keyboard()
        )

        if ADMIN_CHAT_ID != 0:
            admin_text = f"""
{EMOJI['new']} <b>YANGI ARIZA!</b>

{EMOJI['name']} <b>Ism:</b> {registration_data['fullName']}
{EMOJI['age']} <b>Yosh:</b> {registration_data['age']}
{EMOJI['phone']} <b>Telefon:</b> {registration_data['phone']}
{EMOJI['course']} <b>Kurs:</b> {course_name}

{EMOJI['info']} <b>Telegram:</b> @{registration_data['username'] or 'username yo\'q'}
🆔 <b>ID:</b> {registration_data['tg_id']}
"""

            try:
                await context.bot.send_message(
                    chat_id=ADMIN_CHAT_ID,
                    text=admin_text,
                    parse_mode='HTML'
                )
                logger.info("Admin notification sent")
            except Exception as e:
                logger.error(f"Error sending admin notification: {e}")

        return ConversationHandler.END

    except Exception as e:
        logger.error(f"Registration error: {e}")
        await query.edit_message_text(
            f'{EMOJI["error"]} Xatolik yuz berdi.\n'
            f'Xatolik: {str(e)}\n'
            f'Admin bilan bog\'laning: @ITCenter_01'
        )
        return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f'{EMOJI["cancel"]} Ro\'yxatdan o\'tish bekor qilindi.',
        reply_markup=create_main_keyboard()
    )
    return ConversationHandler.END

# Admin functions
async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin statistics"""
    if not is_admin(update.effective_user.id):
        return

    try:
        users_count = len(list(db.collection('users').stream()))
        registrations_count = len(list(db.collection('registrations').stream()))
        courses_count = len(list(db.collection('courses').stream()))

        # Count subscribed users
        subscribed_count = 0
        for doc in db.collection('users').stream():
            user_data = doc.to_dict()
            if user_data.get('subscribed', False):
                subscribed_count += 1

        week_ago = datetime.now() - timedelta(days=7)
        recent_registrations = 0

        for doc in db.collection('registrations').stream():
            reg_data = doc.to_dict()
            if 'created_at' in reg_data and reg_data['created_at']:
                if reg_data['created_at'].replace(tzinfo=None) > week_ago:
                    recent_registrations += 1

        stats_text = f"""
{EMOJI['stats']} <b>Bot statistikasi:</b>

{EMOJI['name']} <b>Jami foydalanuvchilar:</b> {users_count}
{EMOJI['subscribe']} <b>Obuna bo'lganlar:</b> {subscribed_count}
{EMOJI['register']} <b>Jami ro'yxatdan o'tganlar:</b> {registrations_count}
{EMOJI['courses']} <b>Jami kurslar:</b> {courses_count}
{EMOJI['new']} <b>Oxirgi 7 kunlik ro'yxatdan o'tishlar:</b> {recent_registrations}

{EMOJI['time']} <b>Oxirgi yangilanish:</b> {datetime.now().strftime('%d.%m.%Y %H:%M')}
"""

        await update.message.reply_text(
            stats_text,
            parse_mode='HTML',
            reply_markup=create_admin_keyboard()
        )

    except Exception as e:
        logger.error(f"Error getting statistics: {e}")
        await update.message.reply_text(
            f'{EMOJI["error"]} Statistika olishda xatolik yuz berdi.',
            reply_markup=create_admin_keyboard()
        )

# Course management functions (existing functions remain the same)
async def add_course_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start adding course"""
    if not is_admin(update.effective_user.id):
        return

    text = f"""
{EMOJI['add']} <b>Yangi kurs qo'shish</b>

{EMOJI['course']} <b>Kurs nomini kiriting:</b>

{EMOJI['info']} <i>Masalan: Python dasturlash</i>
"""

    await update.message.reply_text(
        text,
        parse_mode='HTML',
        reply_markup=ReplyKeyboardRemove()
    )
    return ADD_COURSE_NAME

async def add_course_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get course name"""
    course_name = update.message.text.strip()

    if len(course_name) < 3:
        await update.message.reply_text(
            f"{EMOJI['error']} Kurs nomi juda qisqa! Kamida 3 ta harf bo'lishi kerak."
        )
        return ADD_COURSE_NAME

    context.user_data['new_course_name'] = course_name

    text = f"""
{EMOJI['time']} <b>Kurs davomiyligini kiriting (oyda):</b>

{EMOJI['info']} <i>Faqat raqam kiriting. Masalan: 6</i>
"""

    await update.message.reply_text(text, parse_mode='HTML')
    return ADD_COURSE_DURATION

async def add_course_duration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get course duration"""
    try:
        duration = int(update.message.text.strip())
        if duration < 1 or duration > 24:
            await update.message.reply_text(
                f"{EMOJI['error']} Davomiylik 1 dan 24 oygacha bo'lishi kerak!"
            )
            return ADD_COURSE_DURATION
    except ValueError:
        await update.message.reply_text(
            f"{EMOJI['error']} Iltimos, faqat raqam kiriting!"
        )
        return ADD_COURSE_DURATION

    context.user_data['new_course_duration'] = duration

    text = f"""
{EMOJI['money']} <b>Kurs narxini kiriting (so'mda):</b>

{EMOJI['info']} <i>Faqat raqam kiriting. Masalan: 500000</i>
"""

    await update.message.reply_text(text, parse_mode='HTML')
    return ADD_COURSE_PRICE

async def add_course_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get course price"""
    try:
        price = int(update.message.text.strip())
        if price < 0:
            await update.message.reply_text(
                f"{EMOJI['error']} Narx manfiy bo'lishi mumkin emas!"
            )
            return ADD_COURSE_PRICE
    except ValueError:
        await update.message.reply_text(
            f"{EMOJI['error']} Iltimos, faqat raqam kiriting!"
        )
        return ADD_COURSE_PRICE

    context.user_data['new_course_price'] = price

    text = f"""
{EMOJI['info']} <b>Kurs tavsifini kiriting:</b>

{EMOJI['info']} <i>Kurs haqida qisqacha ma'lumot yozing yoki "yo'q" deb yozing</i>
"""

    await update.message.reply_text(text, parse_mode='HTML')
    return ADD_COURSE_DESC

async def add_course_desc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get course description and save"""
    description = update.message.text.strip()

    if description.lower() == "yo'q":
        description = ""

    try:
        course_data = {
            'name': context.user_data['new_course_name'],
            'duration_weeks': context.user_data['new_course_duration'],
            'price': context.user_data['new_course_price'],
            'description': description,
            'created_at': firestore.SERVER_TIMESTAMP,
            'created_by': update.effective_user.id
        }

        doc_ref = db.collection('courses').add(course_data)
        logger.info(f"New course added: {doc_ref}")

        success_text = f"""
{EMOJI['success']} <b>Kurs muvaffaqiyatli qo'shildi!</b>

{EMOJI['course']} <b>Kurs:</b> {course_data['name']}
{EMOJI['time']} <b>Davomiyligi:</b> {course_data['duration_weeks']} oy
{EMOJI['money']} <b>Narxi:</b> {course_data['price']:,} so'm
{EMOJI['info']} <b>Tavsif:</b> {description or "Tavsif yo'q"}
"""

        await update.message.reply_text(
            success_text,
            parse_mode='HTML',
            reply_markup=create_admin_keyboard()
        )

        context.user_data.clear()
        return ConversationHandler.END

    except Exception as e:
        logger.error(f"Error adding course: {e}")
        await update.message.reply_text(
            f'{EMOJI["error"]} Kurs qo\'shishda xatolik yuz berdi: {str(e)}',
            reply_markup=create_admin_keyboard()
        )
        return ConversationHandler.END

# Edit course functions
async def edit_course_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start editing course"""
    if not is_admin(update.effective_user.id):
        return

    try:
        courses_ref = db.collection('courses')
        courses_docs = courses_ref.stream()
        courses = []

        for doc in courses_docs:
            course_data = doc.to_dict()
            course_data['id'] = doc.id
            courses.append(course_data)

        if not courses:
            await update.message.reply_text(
                f'{EMOJI["error"]} Hech qanday kurs mavjud emas.',
                reply_markup=create_admin_keyboard()
            )
            return ConversationHandler.END

        buttons = []
        for course in courses:
            course_name = course.get('name', 'Noma\'lum kurs')
            buttons.append([InlineKeyboardButton(course_name, callback_data=f"edit_{course['id']}")])

        buttons.append([InlineKeyboardButton(f"{EMOJI['cancel']} Bekor qilish", callback_data='cancel_edit')])

        text = f"""
{EMOJI['edit']} <b>Qaysi kursni tahrirlash kerak?</b>

{EMOJI['info']} <i>Tahrirlash kerak bo'lgan kursni tanlang:</i>
"""

        await update.message.reply_text(
            text,
            reply_markup=InlineKeyboardMarkup(buttons),
            parse_mode='HTML'
        )
        return EDIT_COURSE_SELECT

    except Exception as e:
        logger.error(f"Error getting courses: {e}")
        await update.message.reply_text(
            f'{EMOJI["error"]} Kurslarni yuklashda xatolik yuz berdi.',
            reply_markup=create_admin_keyboard()
        )
        return ConversationHandler.END

async def edit_course_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Select course field to edit"""
    query = update.callback_query
    await query.answer()

    if query.data == 'cancel_edit':
        await query.edit_message_text(
            f'{EMOJI["cancel"]} Kurs tahrirlash bekor qilindi.'
        )
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f'{EMOJI["info"]} Admin paneliga qaytdingiz.',
            reply_markup=create_admin_keyboard()
        )
        return ConversationHandler.END

    course_id = query.data.replace('edit_', '')
    context.user_data['edit_course_id'] = course_id

    try:
        course_doc = db.collection('courses').document(course_id).get()
        if not course_doc.exists:
            await query.edit_message_text(f'{EMOJI["error"]} Kurs topilmadi!')
            return ConversationHandler.END

        course_data = course_doc.to_dict()
        context.user_data['edit_course_data'] = course_data

        buttons = [
            [InlineKeyboardButton(f"{EMOJI['course']} Kurs nomi", callback_data='edit_name')],
            [InlineKeyboardButton(f"{EMOJI['time']} Davomiylik", callback_data='edit_duration')],
            [InlineKeyboardButton(f"{EMOJI['money']} Narx", callback_data='edit_price')],
            [InlineKeyboardButton(f"{EMOJI['info']} Tavsif", callback_data='edit_description')],
            [InlineKeyboardButton(f"{EMOJI['cancel']} Bekor qilish", callback_data='cancel_edit')]
        ]

        text = f"""
{EMOJI['edit']} <b>"{course_data.get('name', 'Noma\'lum')}" kursini tahrirlash</b>

<b>Hozirgi ma'lumotlar:</b>
{EMOJI['course']} <b>Nomi:</b> {course_data.get('name', 'N/A')}
{EMOJI['time']} <b>Davomiyligi:</b> {course_data.get('duration_weeks', 'N/A')} oy
{EMOJI['money']} <b>Narxi:</b> {course_data.get('price', 'N/A'):,} so'm
{EMOJI['info']} <b>Tavsif:</b> {course_data.get('description', 'Tavsif yo\'q')}

<b>Qaysi maydonni tahrirlash kerak?</b>
"""

        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(buttons),
            parse_mode='HTML'
        )
        return EDIT_COURSE_FIELD

    except Exception as e:
        logger.error(f"Error getting course data: {e}")
        await query.edit_message_text(f'{EMOJI["error"]} Xatolik yuz berdi!')
        return ConversationHandler.END

async def edit_course_field(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Select field to edit"""
    query = update.callback_query
    await query.answer()

    if query.data == 'cancel_edit':
        await query.edit_message_text(
            f'{EMOJI["cancel"]} Kurs tahrirlash bekor qilindi.'
        )
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f'{EMOJI["info"]} Admin paneliga qaytdingiz.',
            reply_markup=create_admin_keyboard()
        )
        return ConversationHandler.END

    field_map = {
        'edit_name': ('name', 'Kurs nomini'),
        'edit_duration': ('duration_weeks', 'Davomiylikni (oyda)'),
        'edit_price': ('price', 'Narxni (so\'mda)'),
        'edit_description': ('description', 'Tavsifni')
    }

    field, field_name = field_map.get(query.data, ('', ''))
    context.user_data['edit_field'] = field

    text = f"""
{EMOJI['edit']} <b>Yangi {field_name.lower()} kiriting:</b>

{EMOJI['info']} <i>Hozirgi qiymat: {context.user_data['edit_course_data'].get(field, 'N/A')}</i>
"""

    await query.edit_message_text(text, parse_mode='HTML')
    return EDIT_COURSE_VALUE

async def edit_course_value(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Save new value"""
    new_value = update.message.text.strip()
    field = context.user_data.get('edit_field')
    course_id = context.user_data.get('edit_course_id')

    # Validate input
    if field == 'duration_weeks':
        try:
            new_value = int(new_value)
            if new_value < 1 or new_value > 24:
                await update.message.reply_text(
                    f"{EMOJI['error']} Davomiylik 1 dan 24 oygacha bo'lishi kerak!"
                )
                return EDIT_COURSE_VALUE
        except ValueError:
            await update.message.reply_text(
                f"{EMOJI['error']} Iltimos, faqat raqam kiriting!"
            )
            return EDIT_COURSE_VALUE

    elif field == 'price':
        try:
            new_value = int(new_value)
            if new_value < 0:
                await update.message.reply_text(
                    f"{EMOJI['error']} Narx manfiy bo'lishi mumkin emas!"
                )
                return EDIT_COURSE_VALUE
        except ValueError:
            await update.message.reply_text(
                f"{EMOJI['error']} Iltimos, faqat raqam kiriting!"
            )
            return EDIT_COURSE_VALUE

    elif field == 'name' and len(new_value) < 3:
        await update.message.reply_text(
            f"{EMOJI['error']} Kurs nomi juda qisqa! Kamida 3 ta harf bo'lishi kerak."
        )
        return EDIT_COURSE_VALUE

    try:
        course_ref = db.collection('courses').document(course_id)
        course_ref.update({
            field: new_value,
            'updated_at': firestore.SERVER_TIMESTAMP,
            'updated_by': update.effective_user.id
        })

        success_text = f"""
{EMOJI['success']} <b>Kurs muvaffaqiyatli yangilandi!</b>

{EMOJI['edit']} <b>Yangilangan maydon:</b> {field}
{EMOJI['new']} <b>Yangi qiymat:</b> {new_value}
"""

        await update.message.reply_text(
            success_text,
            parse_mode='HTML',
            reply_markup=create_admin_keyboard()
        )

        context.user_data.clear()
        return ConversationHandler.END

    except Exception as e:
        logger.error(f"Error updating course: {e}")
        await update.message.reply_text(
            f'{EMOJI["error"]} Kurs yangilashda xatolik yuz berdi: {str(e)}',
            reply_markup=create_admin_keyboard()
        )
        return ConversationHandler.END

# Delete course functions
async def delete_course_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start deleting course"""
    if not is_admin(update.effective_user.id):
        return

    try:
        courses_ref = db.collection('courses')
        courses_docs = courses_ref.stream()
        courses = []

        for doc in courses_docs:
            course_data = doc.to_dict()
            course_data['id'] = doc.id
            courses.append(course_data)

        if not courses:
            await update.message.reply_text(
                f'{EMOJI["error"]} Hech qanday kurs mavjud emas.',
                reply_markup=create_admin_keyboard()
            )
            return ConversationHandler.END

        buttons = []
        for course in courses:
            course_name = course.get('name', 'Noma\'lum kurs')
            buttons.append([InlineKeyboardButton(f"{EMOJI['delete']} {course_name}", callback_data=f"delete_{course['id']}")])

        buttons.append([InlineKeyboardButton(f"{EMOJI['cancel']} Bekor qilish", callback_data='cancel_delete')])

        text = f"""
{EMOJI['delete']} <b>Qaysi kursni o'chirish kerak?</b>

{EMOJI['error']} <b>Diqqat!</b> <i>O'chirilgan kursni tiklash mumkin emas!</i>
"""

        await update.message.reply_text(
            text,
            reply_markup=InlineKeyboardMarkup(buttons),
            parse_mode='HTML'
        )
        return DELETE_COURSE_SELECT

    except Exception as e:
        logger.error(f"Error getting courses: {e}")
        await update.message.reply_text(
            f'{EMOJI["error"]} Kurslarni yuklashda xatolik yuz berdi.',
            reply_markup=create_admin_keyboard()
        )
        return ConversationHandler.END

async def delete_course_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Delete selected course"""
    query = update.callback_query
    await query.answer()

    if query.data == 'cancel_delete':
        await query.edit_message_text(
            f'{EMOJI["cancel"]} Kurs o\'chirish bekor qilindi.'
        )
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f'{EMOJI["info"]} Admin paneliga qaytdingiz.',
            reply_markup=create_admin_keyboard()
        )
        return ConversationHandler.END

    course_id = query.data.replace('delete_', '')

    try:
        course_doc = db.collection('courses').document(course_id).get()
        if not course_doc.exists:
            await query.edit_message_text(f'{EMOJI["error"]} Kurs topilmadi!')
            return ConversationHandler.END

        course_data = course_doc.to_dict()
        course_name = course_data.get('name', 'Noma\'lum kurs')

        db.collection('courses').document(course_id).delete()

        success_text = f"""
{EMOJI['success']} <b>Kurs muvaffaqiyatli o'chirildi!</b>

{EMOJI['delete']} <b>O'chirilgan kurs:</b> {course_name}
"""

        await query.edit_message_text(success_text, parse_mode='HTML')

        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f'{EMOJI["info"]} Admin paneliga qaytdingiz.',
            reply_markup=create_admin_keyboard()
        )

        return ConversationHandler.END

    except Exception as e:
        logger.error(f"Error deleting course: {e}")
        await query.edit_message_text(
            f'{EMOJI["error"]} Kurs o\'chirishda xatolik yuz berdi: {str(e)}'
        )
        return ConversationHandler.END

# Broadcast functions
async def broadcast_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start broadcasting"""
    if not is_admin(update.effective_user.id):
        return

    text = f"""
{EMOJI['broadcast']} <b>Barcha foydalanuvchilarga e'lon yuborish</b>

{EMOJI['announce']} <b>E'lon matnini yozing:</b>

{EMOJI['info']} <i>Matn, rasm, video va boshqa formatlarni yuborish mumkin.
HTML formatini ishlatish mumkin: <b>qalin</b>, <i>qiya</i></i>
"""

    await update.message.reply_text(
        text,
        parse_mode='HTML',
        reply_markup=ReplyKeyboardRemove()
    )
    return BROADCAST_MESSAGE

async def broadcast_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send broadcast to all users"""
    try:
        users_ref = db.collection('users')
        users_docs = users_ref.stream()
        users = []

        for doc in users_docs:
            user_data = doc.to_dict()
            users.append(user_data['user_id'])

        if not users:
            await update.message.reply_text(
                f'{EMOJI["error"]} Hech qanday foydalanuvchi topilmadi.',
                reply_markup=create_admin_keyboard()
            )
            return ConversationHandler.END

        message = update.message
        sent_count = 0
        failed_count = 0

        status_msg = await update.message.reply_text(
            f'{EMOJI["broadcast"]} E\'lon yuborilmoqda...\n'
            f'Jami foydalanuvchilar: {len(users)}\n'
            f'Yuborildi: 0\n'
            f'Xatolik: 0'
        )

        for user_id in users:
            try:
                if user_id == update.effective_user.id:
                    continue

                if message.text:
                    await context.bot.send_message(
                        chat_id=user_id,
                        text=f'{EMOJI["announce"]} <b>E\'LON</b>\n\n{message.text}',
                        parse_mode='HTML'
                    )
                elif message.photo:
                    await context.bot.send_photo(
                        chat_id=user_id,
                        photo=message.photo[-1].file_id,
                        caption=f'{EMOJI["announce"]} <b>E\'LON</b>\n\n{message.caption or ""}',
                        parse_mode='HTML'
                    )
                elif message.video:
                    await context.bot.send_video(
                        chat_id=user_id,
                        video=message.video.file_id,
                        caption=f'{EMOJI["announce"]} <b>E\'LON</b>\n\n{message.caption or ""}',
                        parse_mode='HTML'
                    )
                elif message.document:
                    await context.bot.send_document(
                        chat_id=user_id,
                        document=message.document.file_id,
                        caption=f'{EMOJI["announce"]} <b>E\'LON</b>\n\n{message.caption or ""}',
                        parse_mode='HTML'
                    )

                sent_count += 1

                if sent_count % 10 == 0:
                    await status_msg.edit_text(
                        f'{EMOJI["broadcast"]} E\'lon yuborilmoqda...\n'
                        f'Jami foydalanuvchilar: {len(users)}\n'
                        f'Yuborildi: {sent_count}\n'
                        f'Xatolik: {failed_count}'
                    )

            except Exception as e:
                failed_count += 1
                logger.error(f"Error sending to user {user_id}: {e}")

        # Calculate success percentage safely
        total_attempts = sent_count + failed_count
        success_percentage = (sent_count / total_attempts * 100) if total_attempts > 0 else 0

        final_text = f"""
{EMOJI['success']} <b>E'lon yuborish yakunlandi!</b>

{EMOJI['stats']} <b>Hisobot:</b>
• Jami foydalanuvchilar: {len(users)}
• Muvaffaqiyatli yuborildi: {sent_count}
• Xatolik: {failed_count}
• Muvaffaqiyat foizi: {success_percentage:.1f}%
"""

        await status_msg.edit_text(final_text, parse_mode='HTML')

        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f'{EMOJI["info"]} Admin paneliga qaytdingiz.',
            reply_markup=create_admin_keyboard()
        )

        return ConversationHandler.END

    except Exception as e:
        logger.error(f"Broadcast error: {e}")
        await update.message.reply_text(
            f'{EMOJI["error"]} E\'lon yuborishda xatolik yuz berdi: {str(e)}',
            reply_markup=create_admin_keyboard()
        )
        return ConversationHandler.END

# Static menu handlers (with subscription check)
async def list_courses(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # Admin bypass
    if not is_admin(user_id):
        if not await check_subscription(context, user_id):
            await subscription_required_message(update, context)
            return

    try:
        logger.info("Getting courses list...")
        courses_ref = db.collection('courses')
        courses_docs = courses_ref.stream()
        courses = []

        for doc in courses_docs:
            course_data = doc.to_dict()
            courses.append(course_data)
            logger.info(f"Course: {course_data.get('name', 'Unknown')}")

        if not courses:
            logger.warning("No courses found")
            await update.message.reply_text(
                f'{EMOJI["error"]} Hozircha kurslar mavjud emas.\n'
                f'Admin bilan bog\'laning: @ITCenter_01',
                reply_markup=create_main_keyboard()
            )
            return

        msg = f'{EMOJI["courses"]} <b>Bizning kurslarimiz:</b>\n\n'

        for i, course in enumerate(courses, 1):
            msg += f'<b>{i}. {course.get("name", "Noma\'lum")}</b>\n'
            msg += f'{EMOJI["time"]} Davomiyligi: {course.get("duration_weeks", "N/A")} oy\n'
            msg += f'{EMOJI["money"]} Narxi: {course.get("price", "N/A"):,} so\'m\n'

            if course.get('description'):
                msg += f'{EMOJI["info"]} {course["description"]}\n'
            msg += '\n'

        msg += f'{EMOJI["register"]} <i>Ro\'yxatdan o\'tish uchun tegishli tugmani bosing!</i>'

        await update.message.reply_text(msg, parse_mode='HTML', reply_markup=create_main_keyboard())

    except Exception as e:
        logger.error(f"Error getting courses: {e}")
        await update.message.reply_text(
            f'{EMOJI["error"]} Kurslarni yuklashda xatolik yuz berdi.\n'
            f'Xatolik: {str(e)}\n'
            f'Admin bilan bog\'laning: @ITCenter_01',
            reply_markup=create_main_keyboard()
        )

async def contact_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # Admin bypass
    if not is_admin(user_id):
        if not await check_subscription(context, user_id):
            await subscription_required_message(update, context)
            return

    contact_text = f"""
{EMOJI['contact']} <b>Bog'lanish ma'lumotlari:</b>

{EMOJI['phone']} <b>Telefon:</b> +998 99 448-46-24
{EMOJI['location']} <b>Manzil:</b> Muzrabot tuman, Xalqabot IT Center
{EMOJI['time']} <b>Ish vaqti:</b> 9:00 - 18:00

{EMOJI['info']} <b>Admin:</b> @ITCenter_01

{EMOJI['courses']} <i>Barcha savollaringiz bo'yicha murojaat qilishingiz mumkin!</i>
"""
    await update.message.reply_text(contact_text, parse_mode='HTML', reply_markup=create_main_keyboard())

async def about_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # Admin bypass
    if not is_admin(user_id):
        if not await check_subscription(context, user_id):
            await subscription_required_message(update, context)
            return

    about_text = f"""
{EMOJI['info']} <b>IT Center haqida:</b>

{EMOJI['course']} Biz zamonaviy IT ta'lim markazi bo'lib, professional dasturchilar tayyorlaymiz.

<b>Bizning afzalliklarimiz:</b>
• Tajribali o'qituvchilar
• Amaliy loyihalar
• Ish bilan ta'minlash
• Sertifikat berish
• Kichik guruhlar

{EMOJI['success']} <b>1000+</b> muvaffaqiyatli bitiruvchi
{EMOJI['time']} <b>5 yil</b> tajriba
{EMOJI['course']} <b>10+</b> turli kurslar

{EMOJI['register']} Bugunoq ro'yxatdan o'ting va IT sohasida o'z karerangizni boshlang!
"""
    await update.message.reply_text(about_text, parse_mode='HTML', reply_markup=create_main_keyboard())

async def back_to_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Return to main menu"""
    user = update.effective_user
    user_name = user.first_name or "Foydalanuvchi"

    welcome_text = f"""
{EMOJI['welcome']} <b>Asosiy menuga qaytdingiz, {user_name}!</b>

{EMOJI['info']} Kerakli bo'limni tanlang:
"""

    if is_admin(user.id):
        await update.message.reply_text(
            welcome_text,
            reply_markup=create_admin_keyboard(),
            parse_mode='HTML'
        )
    else:
        await update.message.reply_text(
            welcome_text,
            reply_markup=create_main_keyboard(),
            parse_mode='HTML'
        )

async def admin_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f'{EMOJI["cancel"]} Amal bekor qilindi.',
        reply_markup=create_admin_keyboard()
    )
    return ConversationHandler.END

def main():
    """Main function"""
    if not BOT_TOKEN or ADMIN_CHAT_ID == 0:
        logger.error('BOT_TOKEN or ADMIN_CHAT_ID not found in .env!')
        raise RuntimeError('BOT_TOKEN or ADMIN_CHAT_ID not found in .env!')

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Registration conversation handler
    reg_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex(f'{EMOJI["register"]} Ro\'yxatdan o\'tish'), reg_entry)],
        states={
            FULLNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, reg_fullname)],
            AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, reg_age)],
            PHONE: [
                MessageHandler(filters.CONTACT, reg_phone),
                MessageHandler(filters.TEXT & ~filters.COMMAND, reg_phone),
            ],
            COURSE: [CallbackQueryHandler(reg_course)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
        allow_reentry=True,
    )

    # Admin conversation handlers
    add_course_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex(f'{EMOJI["add"]} Kurs qo\'shish'), add_course_start)],
        states={
            ADD_COURSE_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_course_name)],
            ADD_COURSE_DURATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_course_duration)],
            ADD_COURSE_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_course_price)],
            ADD_COURSE_DESC: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_course_desc)],
        },
        fallbacks=[CommandHandler('cancel', admin_cancel)],
        allow_reentry=True,
    )

    edit_course_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex(f'{EMOJI["edit"]} Kurs tahrirlash'), edit_course_start)],
        states={
            EDIT_COURSE_SELECT: [CallbackQueryHandler(edit_course_select)],
            EDIT_COURSE_FIELD: [CallbackQueryHandler(edit_course_field)],
            EDIT_COURSE_VALUE: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_course_value)],
        },
        fallbacks=[CommandHandler('cancel', admin_cancel)],
        allow_reentry=True,
    )

    delete_course_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex(f'{EMOJI["delete"]} Kurs o\'chirish'), delete_course_start)],
        states={
            DELETE_COURSE_SELECT: [CallbackQueryHandler(delete_course_select)],
        },
        fallbacks=[CommandHandler('cancel', admin_cancel)],
        allow_reentry=True,
    )

    broadcast_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex(f'{EMOJI["broadcast"]} E\'lon yuborish'), broadcast_start)],
        states={
            BROADCAST_MESSAGE: [MessageHandler(filters.ALL & ~filters.COMMAND, broadcast_message)],
        },
        fallbacks=[CommandHandler('cancel', admin_cancel)],
        allow_reentry=True,
    )

    # Add handlers
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CallbackQueryHandler(check_subscription_callback, pattern='check_subscription'))
    app.add_handler(reg_conv)
    app.add_handler(add_course_conv)
    app.add_handler(edit_course_conv)
    app.add_handler(delete_course_conv)
    app.add_handler(broadcast_conv)

    # Admin buttons
    app.add_handler(MessageHandler(filters.Regex(f'{EMOJI["stats"]} Statistika'), admin_stats))
    app.add_handler(MessageHandler(filters.Regex(f'{EMOJI["back"]} Asosiy menu'), back_to_main))

    # Regular user buttons
    app.add_handler(MessageHandler(filters.Regex(f'{EMOJI["courses"]} Kurslar ro\'yxati'), list_courses))
    app.add_handler(MessageHandler(filters.Regex(f'{EMOJI["contact"]} Bog\'lanish'), contact_info))
    app.add_handler(MessageHandler(filters.Regex(f'{EMOJI["info"]} Ma\'lumot'), about_info))
    app.add_handler(MessageHandler(filters.COMMAND, start))  # fallback

    logger.info(f"{EMOJI['success']} Bot started successfully!")
    app.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
