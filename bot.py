# IT Center Telegram Bot – Firestore (sync) version (p‑telegram‑bot 21.x)
# --------------------------------------------------
# Python 3.13 + python-telegram-bot 21.1   ✅ supported
# 1) pip install --upgrade python-telegram-bot==21.1 firebase-admin python-dotenv
# 2) .env:
#      BOT_TOKEN=<telegram bot token>
#      ADMIN_CHAT_ID=<admin numeric ID>
# 3) service-account.json shu papkada bo'lsin (yoki to'liq yo'l).
# --------------------------------------------------

import os
import re
from dotenv import load_dotenv

# --- Telegram imports (v21) ---
from telegram import (
    Update, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove,
    InlineKeyboardButton, InlineKeyboardMarkup,
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, ConversationHandler, filters,
)

# --- Firebase Admin ---
import firebase_admin
from firebase_admin import credentials, firestore

# ------------------- ENV -------------------
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID", "0"))

cred_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "service-account.json")
cred = credentials.Certificate(cred_path)
firebase_admin.initialize_app(cred)

db = firestore.client()

# ------------- Emojis va Design elementlari -------------
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
    'cancel': '❌'
}

# ------------- Conversation constants -------------
FULLNAME, AGE, PHONE, COURSE = range(4)

# ------------- Yordamchi funksiyalar -------------
def is_valid_age(age_text):
    """Yosh to'g'ri kiritilganligini tekshiradi (faqat raqam va 5-100 oralig'ida)"""
    try:
        age = int(age_text.strip())
        return 5 <= age <= 100
    except ValueError:
        return False

def format_phone(phone):
    """Telefon raqamini formatlaydi"""
    # Faqat raqamlarni qoldirish
    digits = re.sub(r'[^\d]', '', phone)
    if digits.startswith('998'):
        return f"+{digits}"
    elif len(digits) == 9:
        return f"+998{digits}"
    return phone

def create_main_keyboard():
    """Asosiy klaviaturani yaratadi"""
    keyboard = [
        [f'{EMOJI["register"]} Ro\'yxatdan o\'tish', f'{EMOJI["courses"]} Kurslar ro\'yxati'],
        [f'{EMOJI["contact"]} Bog\'lanish', f'{EMOJI["info"]} Ma\'lumot']
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)

# ------------- /start handler -------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_name = update.effective_user.first_name or "Foydalanuvchi"
    
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

# ------------- Registration flow -------------
async def reg_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    
    # Ism tekshiruvi
    if len(fullname) < 2:
        await update.message.reply_text(
            f"{EMOJI['error']} Ism juda qisqa! Iltimos, to'liq ism va familiyangizni kiriting."
        )
        return FULLNAME
    
    if not re.match(r'^[a-zA-ZА-Яа-яЁёЎўҚқҒғҲҳ\s\-\']+$', fullname):
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
        # Telefon raqami tekshiruvi
        if not re.match(r'^[\+]?[0-9\s\-\(\)]{9,15}$', phone):
            await update.message.reply_text(
                f"{EMOJI['error']} Noto'g'ri telefon raqami! Iltimos, to'g'ri formatda kiriting.\n"
                f"Masalan: +998901234567"
            )
            return PHONE
    
    context.user_data['phone'] = format_phone(phone)

    # Kurslarni olish
    try:
        courses = [doc.to_dict() | {'id': doc.id} for doc in db.collection('courses').stream()]
        if not courses:
            await update.message.reply_text(
                f'{EMOJI["error"]} Hozircha kurslar mavjud emas. Keyinroq urinib ko\'ring.',
                reply_markup=create_main_keyboard()
            )
            return ConversationHandler.END

        # Kurslar tugmalari
        buttons = []
        for course in courses:
            course_text = f"{EMOJI['course']} {course['name']}"
            buttons.append([InlineKeyboardButton(course_text, callback_data=course['id'])])
        
        # Bekor qilish tugmasi
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
        await update.message.reply_text(
            f'{EMOJI["error"]} Xatolik yuz berdi. Iltimos, qayta urinib ko\'ring.',
            reply_markup=create_main_keyboard()
        )
        return ConversationHandler.END

async def reg_course(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == 'cancel':
        await query.edit_message_text(
            f'{EMOJI["cancel"]} Ro\'yxatdan o\'tish bekor qilindi.',
        )
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f'{EMOJI["info"]} Asosiy menyuga qaytdingiz.',
            reply_markup=create_main_keyboard()
        )
        return ConversationHandler.END
    
    try:
        course_id = query.data
        course_doc = db.collection('courses').document(course_id).get()
        
        if not course_doc.exists:
            await query.edit_message_text(f'{EMOJI["error"]} Kurs topilmadi!')
            return ConversationHandler.END
            
        course_data = course_doc.to_dict()
        course_name = course_data.get('name', 'Noma\'lum kurs')

        # Ma'lumotlarni saqlash
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

        db.collection('registrations').add(registration_data)

        # Foydalanuvchiga xabar
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
        
        # Klaviaturani qaytarish
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f'{EMOJI["info"]} Asosiy menyuga qaytdingiz.',
            reply_markup=create_main_keyboard()
        )

        # Adminga xabar
        admin_text = f"""
{EMOJI['new']} <b>YANGI ARIZA!</b>

{EMOJI['name']} <b>Ism:</b> {registration_data['fullName']}
{EMOJI['age']} <b>Yosh:</b> {registration_data['age']}
{EMOJI['phone']} <b>Telefon:</b> {registration_data['phone']}
{EMOJI['course']} <b>Kurs:</b> {course_name}

{EMOJI['info']} <b>Telegram:</b> @{registration_data['username'] or 'username yo\'q'}
🆔 <b>ID:</b> {registration_data['tg_id']}
"""

        await context.bot.send_message(
            chat_id=ADMIN_CHAT_ID,
            text=admin_text,
            parse_mode='HTML'
        )
        
        return ConversationHandler.END
        
    except Exception as e:
        await query.edit_message_text(f'{EMOJI["error"]} Xatolik yuz berdi. Qayta urinib ko\'ring.')
        return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f'{EMOJI["cancel"]} Ro\'yxatdan o\'tish bekor qilindi.',
        reply_markup=create_main_keyboard()
    )
    return ConversationHandler.END

# ------------- Static menu handlers -------------
async def list_courses(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        courses = [doc.to_dict() for doc in db.collection('courses').stream()]
        if not courses:
            await update.message.reply_text(
                f'{EMOJI["error"]} Hozircha kurslar mavjud emas.',
                reply_markup=create_main_keyboard()
            )
            return

        msg = f'{EMOJI["courses"]} <b>Bizning kurslarimiz:</b>\n\n'
        
        for i, course in enumerate(courses, 1):
            msg += f'<b>{i}. {course.get("name", "Noma\'lum")}</b>\n'
            msg += f'{EMOJI["time"]} Davomiyligi: {course.get("duration_weeks", "N/A")} hafta\n'
            msg += f'{EMOJI["money"]} Narxi: {course.get("price", "N/A")} so\'m\n'
            
            if course.get('description'):
                msg += f'{EMOJI["info"]} {course["description"]}\n'
            msg += '\n'

        msg += f'{EMOJI["register"]} <i>Ro\'yxatdan o\'tish uchun tegishli tugmani bosing!</i>'
        
        await update.message.reply_text(msg, parse_mode='HTML', reply_markup=create_main_keyboard())
        
    except Exception as e:
        await update.message.reply_text(
            f'{EMOJI["error"]} Kurslarni yuklashda xatolik yuz berdi.',
            reply_markup=create_main_keyboard()
        )

async def contact_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    contact_text = f"""
{EMOJI['contact']} <b>Bog'lanish ma'lumotlari:</b>

{EMOJI['phone']} <b>Telefon:</b> +998 99 448-46-24
{EMOJI['location']} <b>Manzil:</b> Muzrabot tuman , Xalqabot IT Center
{EMOJI['time']} <b>Ish vaqti:</b> 9:00 - 18:00 

{EMOJI['info']} <b>Admin:</b> @ITCenter_01

{EMOJI['courses']} <i>Barcha savollaringiz bo'yicha murojaat qilishingiz mumkin!</i>
"""
    await update.message.reply_text(contact_text, parse_mode='HTML', reply_markup=create_main_keyboard())

async def about_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
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

# ------------- Main launcher -------------
def main():
    if not BOT_TOKEN or ADMIN_CHAT_ID == 0:
        raise RuntimeError('BOT_TOKEN yoki ADMIN_CHAT_ID .env da yo\'q!')

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Ro'yxatdan o'tish conversation handler
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

    # Handlerlarni qo'shish
    app.add_handler(CommandHandler('start', start))
    app.add_handler(reg_conv)
    app.add_handler(MessageHandler(filters.Regex(f'{EMOJI["courses"]} Kurslar ro\'yxati'), list_courses))
    app.add_handler(MessageHandler(filters.Regex(f'{EMOJI["contact"]} Bog\'lanish'), contact_info))
    app.add_handler(MessageHandler(filters.Regex(f'{EMOJI["info"]} Ma\'lumot'), about_info))
    app.add_handler(MessageHandler(filters.COMMAND, start))  # fallback

    print(f"{EMOJI['success']} Bot ishga tushdi!")
    app.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()