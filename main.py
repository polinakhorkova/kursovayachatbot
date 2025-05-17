import asyncio
import os
from openpyxl import load_workbook
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters
from datetime import datetime

# Состояния разговора
class ConversationState:
    WAITING_FOR_FIO = 1
    WAITING_FOR_BIRTHDATE = 2
    WAITING_FOR_SYMPTOMS = 3
    WAITING_FOR_TERM = 4  # Новое состояние для поиска термина

# Функция загрузки терминов из Excel
def load_medical_terms():
    terms = {}
    try:
        file_path = os.path.join(os.path.dirname(__file__), "medical_terms.xlsx")
        wb = load_workbook(filename=file_path)
        sheet = wb.active
        for row in sheet.iter_rows(min_row=2, values_only=True):  # Пропускаем заголовок
            if row[0] and row[1]:  # Если есть и термин, и описание
                terms[row[0].lower()] = row[1]
        return terms
    except Exception as e:
        print(f"Ошибка загрузки Excel: {e}")
        return {
            "гипертония": "Повышенное артериальное давление. Основные симптомы: головная боль, головокружение.",
            "диабет": "Хроническое заболевание, связанное с нарушением обмена глюкозы.",
            "аритмия": "Нарушение сердечного ритма."
        }

# Загружаем термины при старте
MEDICAL_TERMS = load_medical_terms()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    name = user.first_name or "друг"
    greeting = f"Здравствуйте, {name}! Напишите полное Ф.И.О. пациента для начала работы."
    await update.message.reply_text(greeting)
    
    context.user_data['state'] = ConversationState.WAITING_FOR_FIO

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if 'state' not in context.user_data:
        await update.message.reply_text("Пожалуйста, начните с команды /start")
        return
    
    current_state = context.user_data['state']
    
    if current_state == ConversationState.WAITING_FOR_FIO:
        context.user_data['fio'] = update.message.text
        await update.message.reply_text("Спасибо! Теперь укажите дату рождения пациента в формате ДД.ММ.ГГГГ")
        context.user_data['state'] = ConversationState.WAITING_FOR_BIRTHDATE
    
    elif current_state == ConversationState.WAITING_FOR_BIRTHDATE:
        try:
            birth_date = datetime.strptime(update.message.text, "%d.%m.%Y").date()
            context.user_data['birth_date'] = birth_date
            await update.message.reply_text("Спасибо! Теперь опишите симптомы пациента.")
            context.user_data['state'] = ConversationState.WAITING_FOR_SYMPTOMS
        except ValueError:
            await update.message.reply_text("Неверный формат даты. Пожалуйста, укажите дату в формате ДД.ММ.ГГГГ")
    
    elif current_state == ConversationState.WAITING_FOR_SYMPTOMS:
        context.user_data['symptoms'] = update.message.text
        await update.message.reply_text(
            f"Спасибо! Ваши данные:\n"
            f"ФИО: {context.user_data['fio']}\n"
            f"Дата рождения: {context.user_data['birth_date'].strftime('%d.%m.%Y')}\n"
            f"Симптомы: {context.user_data['symptoms']}\n\n"
            f"Ваша информация сохранена. Ожидайте, результаты будут отправлены позже."
        )
        del context.user_data['state']
    
    elif current_state == ConversationState.WAITING_FOR_TERM:
        term = update.message.text.lower()
        if term in MEDICAL_TERMS:
            await update.message.reply_text(f"📖 {term.capitalize()}:\n{MEDICAL_TERMS[term]}")
        else:
            await update.message.reply_text("Термин не найден. Попробуйте другой или введите /terms для списка.")
        context.user_data['state'] = None

async def terms_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        terms_list = "\n".join(f"• {term}" for term in MEDICAL_TERMS.keys())
        await update.message.reply_text(
           # f"📚 Доступные медицинские термины:\n{terms_list}\n\n" 
            f"Введите название термина, чтобы получить его определение."
        )
        context.user_data['state'] = ConversationState.WAITING_FOR_TERM
    else:
        term = " ".join(context.args).lower()
        if term in MEDICAL_TERMS:
            await update.message.reply_text(f"📖 {term.capitalize()}:\n{MEDICAL_TERMS[term]}")
        else:
            await update.message.reply_text("Термин не найден. Попробуйте один из этих:\n" + ", ".join(MEDICAL_TERMS.keys()))

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Доступные команды:\n"
        "/start - приветствие и регистрация\n"
        "/terms - справочник медицинских терминов\n"
        "/help - список команд"
    )

async def main():
    TOKEN = '7903839198:AAHD7_C1qic4ic9Xc8ei53XVSOAoOmZ_Bi8'
    
    app = ApplicationBuilder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("terms", terms_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("Бот запущен. Нажмите Ctrl+C для остановки.")
    
    try:
        await app.initialize()
        await app.start()
        await app.updater.start_polling()
        while True:
            await asyncio.sleep(1)
    except (KeyboardInterrupt, asyncio.CancelledError):
        print("\nБот останавливается...")
    except Exception as e:
        print(f"Ошибка: {e}")
    finally:
        if app.updater:
            await app.updater.stop()
        if app:
            await app.stop()
            await app.shutdown()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nБот завершил работу.")
