import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, CallbackContext
from apscheduler.schedulers.background import BackgroundScheduler
import sqlite3
import os

# Конфигурация
DATABASE_PATH = 'path/to/your/database.db'  # Укажите реальный путь к вашей базе
BOT_TOKEN = '7749975937:AAFHUNchCOG6PSq6Vfhs5FOVGaqGz2CYl_U'  # Замените на токен от @BotFather

# Инициализация планировщика
scheduler = BackgroundScheduler(timezone="UTC")
scheduler.start()

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

class PlantDatabase:
    def __init__(self):
        self.conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        self._verify_db_structure()

    def _verify_db_structure(self):
        """Проверка и инициализация структуры БД при необходимости"""
        cursor = self.conn.cursor()
        # Создаем таблицы, если они не существуют
        cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                        user_id INTEGER PRIMARY KEY,
                        username TEXT)''')
        
        cursor.execute('''CREATE TABLE IF NOT EXISTS plants (
                        plant_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        plant_name TEXT,
                        notifications_enabled BOOLEAN DEFAULT 0,
                        FOREIGN KEY(user_id) REFERENCES users(user_id))''')
        self.conn.commit()

    def get_user_plants(self, user_id):
        cursor = self.conn.cursor()
        cursor.execute('''SELECT plant_id, plant_name, notifications_enabled 
                        FROM plants WHERE user_id = ?''', (user_id,))
        return cursor.fetchall()

    def toggle_notifications(self, plant_id, status):
        cursor = self.conn.cursor()
        cursor.execute('''UPDATE plants SET notifications_enabled = ? 
                        WHERE plant_id = ?''', (status, plant_id))
        self.conn.commit()

db = PlantDatabase()

def start(update: Update, context: CallbackContext) -> None:
    user = update.effective_user
    keyboard = [
        [InlineKeyboardButton("🌿 Мои растения", callback_data='my_plants')],
        [InlineKeyboardButton("➕ Добавить растение", callback_data='add_plant')]
    ]
    update.message.reply_text(
        f"Добро пожаловать, {user.first_name}!",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

def show_plants_menu(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    user_id = query.from_user.id
    plants = db.get_user_plants(user_id)
    
    if not plants:
        query.answer("У вас пока нет растений")
        return
    
    keyboard = [
        [InlineKeyboardButton(f"🌱 {plant[1]}", callback_data=f'plant_{plant[0]}')]
        for plant in plants
    ]
    query.edit_message_text(
        "Ваши растения:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

def plant_actions(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    plant_id = query.data.split('_')[1]
    
    keyboard = [
        [InlineKeyboardButton("💧 Включить уведомления", callback_data=f'enable_{plant_id}')],
        [InlineKeyboardButton("🔕 Отключить уведомления", callback_data=f'disable_{plant_id}')]
    ]
    query.edit_message_text(
        "Выберите действие:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

def handle_notifications(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    action, plant_id = query.data.split('_')
    user_id = query.from_user.id
    
    db.toggle_notifications(plant_id, 1 if action == 'enable' else 0)
    
    if action == 'enable':
        schedule_reminder(user_id, plant_id)
        query.answer("Уведомления включены! 🌧️")
    else:
        cancel_reminder(plant_id, user_id)
        query.answer("Уведомления отключены! 🌞")

def schedule_reminder(user_id, plant_id):
    scheduler.add_job(
        send_reminder,
        'interval',
        hours=12,
        args=[user_id, plant_id],
        id=f"{user_id}_{plant_id}",
        replace_existing=True
    )

def cancel_reminder(plant_id, user_id):
    scheduler.remove_job(f"{user_id}_{plant_id}")

def send_reminder(user_id, plant_id):
    cursor = db.conn.cursor()
    cursor.execute('''SELECT plant_name FROM plants WHERE plant_id = ?''', (plant_id,))
    plant_name = cursor.fetchone()[0]
    
    context.bot.send_message(
        chat_id=user_id,
        text=f"🕒 Пора поливать {plant_name}! 💦"
    )

def main() -> None:
    updater = Updater(BOT_TOKEN)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CallbackQueryHandler(show_plants_menu, pattern='^my_plants$'))
    dp.add_handler(CallbackQueryHandler(plant_actions, pattern='^plant_'))
    dp.add_handler(CallbackQueryHandler(handle_notifications, pattern='^(enable|disable)_'))

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()