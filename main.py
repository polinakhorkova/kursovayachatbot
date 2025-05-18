import asyncio
import os
from openpyxl import load_workbook
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters
from datetime import datetime
import psycopg2

# Состояния разговора
class ConversationState:
    WAITING_FOR_FIO = 1
    WAITING_FOR_BIRTHDATE = 2
    WAITING_FOR_SYMPTOMS = 3
    WAITING_FOR_TERM = 4
    WAITING_FOR_CODE = 5

# Загрузка медицинских терминов
def load_medical_terms():
    terms = {}
    try:
        file_path = os.path.join(os.path.dirname(__file__), "medical_terms.xlsx")
        wb = load_workbook(filename=file_path)
        sheet = wb.active
        for row in sheet.iter_rows(min_row=2, values_only=True):
            if row[0] and row[1]:
                terms[row[0].lower()] = row[1]
        return terms
    except Exception as e:
        print(f"Ошибка загрузки medical_terms.xlsx: {e}")
        return {}

# Загрузка кодов МКБ
def load_icd_codes():
    codes = {}
    try:
        file_path = os.path.join(os.path.dirname(__file__), "codes.xlsx")
        wb = load_workbook(filename=file_path)
        sheet = wb.active
        for row in sheet.iter_rows(min_row=2, values_only=True):
            if row[0] and row[1]:
                codes[row[0].upper()] = row[1]
        return codes
    except Exception as e:
        print(f"Ошибка загрузки codes.xlsx: {e}")
        return {}

MEDICAL_TERMS = load_medical_terms()
ICD_CODES = load_icd_codes()

def test_db_connection():
    try:
        conn = psycopg2.connect(
            dbname="postgres",
            user="myuser",
            password="polina",
            host="192.168.0.6",
            port="5432"
        )
        if conn.status == psycopg2.extensions.STATUS_READY:
            print("Успешно подключились к базе данных PostgreSQL!")
        conn.close()
    except Exception as e:
        print(f"Ошибка подключения к БД: {e}")

# 🔌 Функция для сохранения ФИО пациента в базу данных
def insert_patient_to_db(fio):
    try:
        parts = fio.split()
        if len(parts) != 3:
            print("ФИО должно содержать 3 части")
            return False

        last_name, first_name, middle_name = parts

        conn = psycopg2.connect(
            dbname="postgres",
            user="myuser",
            password="polina",
            host="192.168.0.6",
            port="5432"
        )
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO пациенты (фамилия, имя, отчество) VALUES (%s, %s, %s);",
            (last_name, first_name, middle_name)
        )
        conn.commit()
        cursor.close()
        conn.close()
        print("Пациент добавлен в БД.")
        return True

    except Exception as e:
        print(f"Ошибка при вставке пациента: {e}")
        return False

# /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.effective_user.first_name or "друг"
    await update.message.reply_text(f"Здравствуйте, {name}! Напишите Ф.И.О. пациента.")
    context.user_data['state'] = ConversationState.WAITING_FOR_FIO

# 🔁 Обработка сообщений
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if 'state' not in context.user_data:
        await update.message.reply_text("Пожалуйста, начните с команды /start")
        return

    current_state = context.user_data['state']
    text = update.message.text.strip()

    if current_state == ConversationState.WAITING_FOR_FIO:
        if len(text.split()) != 3:
            await update.message.reply_text("Пожалуйста, укажите Ф.И.О. полностью (три слова).")
            return
        context.user_data['fio'] = text
        success = insert_patient_to_db(text)
        if success:
            await update.message.reply_text("Спасибо! Укажите дату рождения пациента (ДД.ММ.ГГГГ).")
            context.user_data['state'] = ConversationState.WAITING_FOR_BIRTHDATE
        else:
            await update.message.reply_text("Произошла ошибка при сохранении ФИО. Попробуйте позже.")

    elif current_state == ConversationState.WAITING_FOR_BIRTHDATE:
        try:
            birth_date = datetime.strptime(text, "%d.%m.%Y").date()
            context.user_data['birth_date'] = birth_date
            await update.message.reply_text("Спасибо! Опишите симптомы пациента.")
            context.user_data['state'] = ConversationState.WAITING_FOR_SYMPTOMS
        except ValueError:
            await update.message.reply_text("Неверный формат даты. Используйте ДД.ММ.ГГГГ")

    elif current_state == ConversationState.WAITING_FOR_SYMPTOMS:
        context.user_data['symptoms'] = text
        await update.message.reply_text(
            f"Спасибо! Данные сохранены:\n"
            f"ФИО: {context.user_data['fio']}\n"
            f"Дата рождения: {context.user_data['birth_date'].strftime('%d.%m.%Y')}\n"
            f"Симптомы: {context.user_data['symptoms']}"
        )
        context.user_data.clear()

    elif current_state == ConversationState.WAITING_FOR_TERM:
        term = text.lower()
        if term in MEDICAL_TERMS:
            await update.message.reply_text(f"📖 {term.capitalize()}:\n{MEDICAL_TERMS[term]}")
        else:
            await update.message.reply_text("Термин не найден. Введите другой или /terms для справки.")
        context.user_data['state'] = None

    elif current_state == ConversationState.WAITING_FOR_CODE:
        code = text.upper()
        if code in ICD_CODES:
            await update.message.reply_text(f"📘 Код {code}:\n{ICD_CODES[code]}")
        else:
            await update.message.reply_text("Код не найден. Убедитесь в правильности формата (например, J45).")
        context.user_data['state'] = None

# /terms
async def terms_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Введите термин, чтобы получить определение.")
        context.user_data['state'] = ConversationState.WAITING_FOR_TERM
    else:
        term = " ".join(context.args).lower()
        if term in MEDICAL_TERMS:
            await update.message.reply_text(f"📖 {term.capitalize()}:\n{MEDICAL_TERMS[term]}")
        else:
            await update.message.reply_text("Термин не найден.")

# /codes
async def codes_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Введите код МКБ-10 (например, J45), чтобы получить расшифровку.")
        context.user_data['state'] = ConversationState.WAITING_FOR_CODE
    else:
        code = context.args[0].upper()
        if code in ICD_CODES:
            await update.message.reply_text(f"📘 Код {code}:\n{ICD_CODES[code]}")
        else:
            await update.message.reply_text("Код не найден. Убедитесь в корректности ввода.")

# /help
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Доступные команды:\n"
        "/start — начать ввод данных пациента\n"
        "/terms — справочник медицинских терминов\n"
        "/codes — расшифровка кодов МКБ-10\n"
        "/help — список команд"
    )

# 🚀 Запуск бота
async def main():
    
    TOKEN = '7903839198:AAHD7_C1qic4ic9Xc8ei53XVSOAoOmZ_Bi8'  # Обязательно замени на актуальный токен
    app = ApplicationBuilder().token(TOKEN).build()
    

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("terms", terms_command))
    app.add_handler(CommandHandler("codes", codes_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Бот запущен. Нажмите Ctrl+C для остановки.")
  

    try:
        await app.initialize()
        await app.start()
        await app.updater.start_polling()
        while True:
            await asyncio.sleep(1)
    except (KeyboardInterrupt, asyncio.CancelledError):
        print("\nБот остановлен.")
    finally:
        await app.updater.stop()
        await app.stop()
        await app.shutdown()

if __name__ == '__main__':
    test_db_connection()
    asyncio.run(main())
