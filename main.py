import asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters
from datetime import datetime

# Состояния разговора
class ConversationState:
    WAITING_FOR_FIO = 1
    WAITING_FOR_BIRTHDATE = 2
    WAITING_FOR_SYMPTOMS = 3

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    name = user.first_name or "друг"
    greeting = f"Здравствуйте, {name}! Напишите полное ФИО пациента для начала работы."
    await update.message.reply_text(greeting)
    
    # Устанавливаем состояние ожидания ФИО
    context.user_data['state'] = ConversationState.WAITING_FOR_FIO

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if 'state' not in context.user_data:
        await update.message.reply_text("Пожалуйста, начните с команды /start")
        return
    
    if context.user_data['state'] == ConversationState.WAITING_FOR_FIO:
        # Сохраняем ФИО
        context.user_data['fio'] = update.message.text
        await update.message.reply_text("Спасибо! Теперь укажите дату рождения пациента в формате ДД.ММ.ГГГГ")
        
        # Переходим к ожиданию даты рождения
        context.user_data['state'] = ConversationState.WAITING_FOR_BIRTHDATE
    
    elif context.user_data['state'] == ConversationState.WAITING_FOR_BIRTHDATE:
        try:
            # Пытаемся распарсить дату
            birth_date = datetime.strptime(update.message.text, "%d.%m.%Y").date()
            context.user_data['birth_date'] = birth_date
            
            # Запрашиваем симптомы
            await update.message.reply_text(
                "Спасибо! Теперь опишите, пожалуйста, симптомы пациента (ПРИДУМАТЬ ТЕКСТ тут добавим пояснение!!!!!!):"
            )
            
            # Переходим к ожиданию симптомов
            context.user_data['state'] = ConversationState.WAITING_FOR_SYMPTOMS
            
        except ValueError:
            await update.message.reply_text("Неверный формат даты. Пожалуйста, укажите дату в формате ДД.ММ.ГГГГ")
    
    elif context.user_data['state'] == ConversationState.WAITING_FOR_SYMPTOMS:
        # Сохраняем симптомы
        context.user_data['symptoms'] = update.message.text
        
        # Выводим все собранные данные
        await update.message.reply_text(
            f"Спасибо! Ваши данные:\n"
            f"ФИО: {context.user_data['fio']}\n"
            f"Дата рождения: {context.user_data['birth_date'].strftime('%d.%m.%Y')}\n"
            f"Симптомы: {context.user_data['symptoms']}\n\n"
            f"Ваша информация сохранена. ПРИДУМАТЬ ТЕКСТ."
        )
        
        # Здесь можно добавить сохранение в базу данных
        # await save_to_database(context.user_data)
        
        # Сбрасываем состояние
        del context.user_data['state']

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Доступные команды:\n"
        "/start - приветствие и регистрация\n"
        "/help - список команд"
    )

async def main():
    TOKEN = '7903839198:AAHD7_C1qic4ic9Xc8ei53XVSOAoOmZ_Bi8'
    
    app = ApplicationBuilder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
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