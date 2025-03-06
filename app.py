import logging
import random
import sqlite3
import os
import requests
import pandas as pd
import base64
import json
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters

# Конфигурация
BOT_TOKEN = "7679266869:AAEG6RoG1aUClN2Cd9MEZMSxWS5YxNS3f_M"  # Замените на ваш токен
DATABASE_NAME = 'plants.db'
GROUP_LINK = "https://t.me/+d22-vaRbGzgyZTli"

# Список растений
PLANTS_LIST = [
    "Кактус", "Фикус", "Алоэ", "Орхидея", "Гибискус", "Роза", "Тюльпан", "Лаванда",
    "Пион", "Герань", "Хризантема", "Гортензия", "Ирис", "Лилия", "Магнолия",
    "Настурция", "Петуния", "Флокс", "Ромашка", "Азалия", "Бегония", "Вербена",
    "Гвоздика", "Гиацинт", "Клематис", "Крокус", "Лобелия", "Мальва", "Маргаритка",
    "Нарцисс", "Примула", "Сирень", "Анемона", "Астра", "Брунфельсия", "Василек",
    "Глициния", "Дельфиниум", "Дицентра", "Камелия", "Калистегия", "Канна",
    "Колокольчик", "Кротон", "Лантана", "Лавр", "Лилейник", "Люпин", "Мак",
    "Медуница", "Морозник", "Наперстянка", "Незабудка", "Одуванчик", "Папоротник",
    "Пеларгония", "Подсолнечник", "Рододендрон", "Сальвия", "Фиалка", "Хоста",
    "Цинния", "Шалфей", "Энотера", "Эустома"
]

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)


# Класс базы данных растений
class PlantDatabase:
    def __init__(self):
        self.db_name = DATABASE_NAME
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                        user_id INTEGER PRIMARY KEY,
                        username TEXT)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS plants (
                        plant_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        plant_name TEXT,
                        notifications_enabled BOOLEAN DEFAULT 0)''')
        conn.commit()
        conn.close()

    def get_or_create_user_plants(self, user_id, username):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute("INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)", (user_id, username))
        cursor.execute("SELECT plant_id FROM plants WHERE user_id = ?", (user_id,))
        plants = cursor.fetchall()
        if not plants:
            random_plants = random.sample(PLANTS_LIST, 5)
            for plant_name in random_plants:
                cursor.execute("INSERT INTO plants (user_id, plant_name) VALUES (?, ?)", (user_id, plant_name))
            cursor.execute("INSERT INTO plants (user_id, plant_name, notifications_enabled) VALUES (?, ?, ?)",
                           (user_id, "Тестовое растение", 1))
            cursor.execute("SELECT plant_id FROM plants WHERE user_id = ? AND plant_name = ?",
                           (user_id, "Тестовое растение"))
            test_plant_id = cursor.fetchone()[0]
        else:
            cursor.execute(
                "SELECT plant_id FROM plants WHERE user_id = ? AND plant_name = ? AND notifications_enabled = 1",
                (user_id, "Тестовое растение"))
            result = cursor.fetchone()
            test_plant_id = result[0] if result else None
        conn.commit()
        conn.close()
        return test_plant_id

    def get_plants(self, user_id):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute('''SELECT plant_id, plant_name, notifications_enabled
                        FROM plants WHERE user_id = ?''', (user_id,))
        plants = cursor.fetchall()
        conn.close()
        return plants

    def add_random_plant(self, user_id):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        random_plant = random.choice(PLANTS_LIST)
        cursor.execute("INSERT INTO plants (user_id, plant_name) VALUES (?, ?)", (user_id, random_plant))
        conn.commit()
        conn.close()

    def add_plant(self, user_id, plant_name):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO plants (user_id, plant_name) VALUES (?, ?)", (user_id, plant_name))
        conn.commit()
        conn.close()

    def toggle_notifications(self, plant_id, status):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute('''UPDATE plants SET notifications_enabled = ?
                        WHERE plant_id = ?''', (status, plant_id))
        conn.commit()
        conn.close()


# Инициализация базы данных
db = PlantDatabase()


# Функция для получения стандартного меню
def get_main_menu():
    return [
        [InlineKeyboardButton("🌿 Мои растения", callback_data='my_plants')],
        [InlineKeyboardButton("➕ Добавить случайное растение", callback_data='add_plant')],
        [InlineKeyboardButton("🌱 Обмен цветами", url=GROUP_LINK)]
    ]


# Функция для удаления предыдущего сообщения
async def delete_previous_message(context: ContextTypes.DEFAULT_TYPE, chat_id: int):
    if 'last_message_id' in context.user_data:
        try:
            await context.bot.delete_message(chat_id=chat_id, message_id=context.user_data['last_message_id'])
        except Exception as e:
            logging.warning(f"Не удалось удалить сообщение: {e}")


# Функция для удаления предыдущей фотографии
async def delete_previous_photo(context: ContextTypes.DEFAULT_TYPE, chat_id: int):
    if 'last_photo_id' in context.user_data:
        try:
            await context.bot.delete_message(chat_id=chat_id, message_id=context.user_data['last_photo_id'])
        except Exception as e:
            logging.warning(f"Не удалось удалить фото: {e}")


# Асинхронная функция для отправки уведомления (один раз)
async def send_reminder(context: ContextTypes.DEFAULT_TYPE):
    user_id = context.job.data['user_id']
    plant_id = context.job.data['plant_id']
    conn = sqlite3.connect(DATABASE_NAME)
    plant = conn.execute(
        "SELECT plant_name FROM plants WHERE plant_id = ?",
        (plant_id,)
    ).fetchone()
    conn.close()
    if plant:
        keyboard = [[InlineKeyboardButton("Полил", callback_data=f'watered_{plant_id}')]]
        message = await context.bot.send_message(
            chat_id=user_id,
            text=f"Уведомление: {plant[0]} надо полить! 💧",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        if 'reminder_messages' not in context.user_data:
            context.user_data['reminder_messages'] = {}
        context.user_data['reminder_messages'][f"{user_id}_{plant_id}"] = message.message_id
        logging.info(f"Отправлено уведомление для {plant[0]}, message_id: {message.message_id}")


# Обработчики команд и callback'ов
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    chat_id = update.message.chat_id
    test_plant_id = db.get_or_create_user_plants(user.id, user.username)
    keyboard = get_main_menu()

    await delete_previous_message(context, chat_id)

    message = await context.bot.send_message(
        chat_id=chat_id,
        text=f"Добро пожаловать, {user.first_name}! Отправьте фото для идентификации и добавления растения или используйте кнопки ниже:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    context.user_data['last_message_id'] = message.message_id

    # Запускаем уведомление для тестового растения один раз через 6 секунд
    if test_plant_id:
        job_id = f"plant_{test_plant_id}_user_{user.id}"
        if not context.job_queue.get_jobs_by_name(job_id):
            context.job_queue.run_once(
                send_reminder,
                6,
                data={'user_id': user.id, 'plant_id': test_plant_id},
                name=job_id
            )


async def show_plants(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user_id = query.from_user.id
    chat_id = query.message.chat_id
    plants = db.get_plants(user_id)

    if not plants:
        await query.answer("У вас пока нет растений")
        return

    keyboard = [
        [InlineKeyboardButton(f"{'🔔' if plant[2] else '🌱'} {plant[1]}",
                              callback_data=f'plant_{plant[0]}')]
        for plant in plants
    ]
    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data='back_to_start')])

    await delete_previous_message(context, chat_id)

    message = await context.bot.send_message(
        chat_id=chat_id,
        text="Ваши растения:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    context.user_data['last_message_id'] = message.message_id


async def plant_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    chat_id = query.message.chat_id
    plant_id = query.data.split('_')[1]

    keyboard = [
        [InlineKeyboardButton("✅ Включить уведомления", callback_data=f'enable_{plant_id}')],
        [InlineKeyboardButton("❌ Отключить уведомления", callback_data=f'disable_{plant_id}')],
        [InlineKeyboardButton("⬅️ Назад", callback_data='my_plants')]
    ]

    await delete_previous_message(context, chat_id)

    message = await context.bot.send_message(
        chat_id=chat_id,
        text="Управление уведомлениями:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    context.user_data['last_message_id'] = message.message_id


async def handle_notification(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    chat_id = query.message.chat_id
    action, plant_id = query.data.split('_')
    user_id = query.from_user.id
    job_id = f"plant_{plant_id}_user_{user_id}"

    db.toggle_notifications(plant_id, 1 if action == 'enable' else 0)

    if action == 'enable':
        context.job_queue.run_once(
            send_reminder,
            6,  # Уведомление один раз через 6 секунд
            data={'user_id': user_id, 'plant_id': plant_id},
            name=job_id
        )
        await query.answer("Уведомления включены! 💦")
    else:
        job = context.job_queue.get_jobs_by_name(job_id)
        if job:
            for j in job:
                j.schedule_removal()
            await query.answer("Уведомления отключены! 🔕")
        else:
            await query.answer("Уведомления уже отключены! 🔕")

    keyboard = [
        [InlineKeyboardButton("✅ Включить уведомления", callback_data=f'enable_{plant_id}')],
        [InlineKeyboardButton("❌ Отключить уведомления", callback_data=f'disable_{plant_id}')],
        [InlineKeyboardButton("⬅️ Назад", callback_data='my_plants')]
    ]

    await delete_previous_message(context, chat_id)

    message = await context.bot.send_message(
        chat_id=chat_id,
        text="Управление уведомлениями:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    context.user_data['last_message_id'] = message.message_id


async def add_plant(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user_id = query.from_user.id
    chat_id = query.message.chat_id
    db.add_random_plant(user_id)
    plants = db.get_plants(user_id)

    keyboard = [
        [InlineKeyboardButton(f"{'🔔' if plant[2] else '🌱'} {plant[1]}",
                              callback_data=f'plant_{plant[0]}')]
        for plant in plants
    ]
    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data='back_to_start')])

    await delete_previous_message(context, chat_id)

    message = await context.bot.send_message(
        chat_id=chat_id,
        text="Ваши растения:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    context.user_data['last_message_id'] = message.message_id


async def back_to_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user = query.from_user
    chat_id = query.message.chat_id
    keyboard = get_main_menu()

    await delete_previous_message(context, chat_id)

    message = await context.bot.send_message(
        chat_id=chat_id,
        text=f"Добро пожаловать, {user.first_name}! Отправьте фото для идентификации и добавления растения или используйте кнопки ниже:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    context.user_data['last_message_id'] = message.message_id


async def handle_watered(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    chat_id = query.message.chat_id
    plant_id = query.data.split('_')[1]
    user_id = query.from_user.id

    # Удаляем сообщение с уведомлением
    reminder_key = f"{user_id}_{plant_id}"
    if 'reminder_messages' in context.user_data and reminder_key in context.user_data['reminder_messages']:
        try:
            message_id = context.user_data['reminder_messages'][reminder_key]
            await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
            del context.user_data['reminder_messages'][reminder_key]
            logging.info(f"Удалено сообщение с ID {message_id} для {plant_id}")
        except Exception as e:
            logging.error(f"Ошибка при удалении сообщения: {e}")

    await query.answer("Растение полито! 🌱")


# Обработчик фото
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        user_id = update.effective_user.id
        chat_id = update.message.chat_id
        photo_message = update.message

        await delete_previous_photo(context, chat_id)

        context.user_data['last_photo_id'] = photo_message.message_id

        photo_file = await photo_message.photo[-1].get_file()
        downloaded_file = await photo_file.download_as_bytearray()

        identifier = PlantIdentifier()
        extractor = PlantInfoExtractor()
        identifier.load_database()

        plant_response = identifier.identify_plant(downloaded_file)

        keyboard = get_main_menu()

        await delete_previous_message(context, chat_id)

        if plant_response and "suggestions" in plant_response and plant_response["suggestions"]:
            probability = plant_response["suggestions"][0].get("probability", 0)
            if probability < 0.1:
                message = await context.bot.send_message(
                    chat_id=chat_id,
                    text="Это не цветок 🌿❌",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            else:
                plant_info = extractor.get_plant_info(plant_response, identifier.df)
                if plant_info:
                    plant_name = plant_info['название']
                    db.add_plant(user_id, plant_name)
                    response = (
                        f"🌸 Растение добавлено в ваш список!\n"
                        f"Название: {plant_info['название']}\n"
                        f"🔬 Научное название: {plant_info['научное_название']}\n"
                        f"💧 Полив: {plant_info['полив']}\n"
                        f"📝 Заметки: {plant_info['заметки']}\n"
                        f"☠️ Токсичность: {plant_info['токсичность']}\n"
                        f"🌱 Пересадка: {plant_info['пересадка']}\n"
                        f"☀️ Требования к освещению: {plant_info['требования_к_освещению']}\n"
                        f"❤️ Здоровье: {plant_info['здоровье']}"
                    )
                    message = await context.bot.send_message(
                        chat_id=chat_id,
                        text=response,
                        reply_markup=InlineKeyboardMarkup(keyboard)
                    )
                else:
                    message = await context.bot.send_message(
                        chat_id=chat_id,
                        text="Информация о растении не найдена 🌱❓",
                        reply_markup=InlineKeyboardMarkup(keyboard)
                    )
        else:
            message = await context.bot.send_message(
                chat_id=chat_id,
                text="Это не цветок 🌿❌",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

        context.user_data['last_message_id'] = message.message_id

    except Exception as e:
        keyboard = get_main_menu()
        await delete_previous_message(context, chat_id)
        await delete_previous_photo(context, chat_id)
        message = await context.bot.send_message(
            chat_id=chat_id,
            text=f"Ошибка: {str(e)} ⚠️",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        context.user_data['last_message_id'] = message.message_id


# Класс для идентификации растений
class PlantIdentifier:
    def __init__(self, api_key="dJnePWJr2JzgMp8MYYqnl9nHDnZAdbNVwoySY89M6mfdqC6D0z"):
        self.api_key = api_key
        self.url = "https://api.plant.id/v2/identify"
        self.df = None

    def load_database(self, csv_path="plants_watering.csv"):
        self.df = pd.read_csv(csv_path, names=[
            "scientific_name", "common_name", "family", "watering_frequency",
            "notes", "toxicity", "repotting", "light_requirements", "health"
        ], header=None)

    @staticmethod
    def image_to_base64(image_data):
        return base64.b64encode(image_data).decode('utf-8')

    def identify_plant(self, image_data):
        image_base64 = self.image_to_base64(image_data)
        data = {
            "images": [image_base64],
            "modifiers": ["crops_fast"],
            "plant_language": "ru",
            "upload_images": True
        }
        headers = {
            "Content-Type": "application/json",
            "Api-Key": self.api_key
        }
        response = requests.post(self.url, json=data, headers=headers)
        return response.json()


# Класс для извлечения информации о растении
class PlantInfoExtractor:
    def get_plant_info(self, plant_data, df):
        if "suggestions" not in plant_data or not plant_data["suggestions"]:
            return None
        plant = plant_data["suggestions"][0]
        scientific_name = plant.get("plant_details", {}).get("scientific_name", "")
        plant_name = plant.get("plant_name", "")
        common_name = plant_name if isinstance(plant_name, str) else plant_name.get("common", "")

        row = df[
            (df["scientific_name"] == scientific_name) |
            (df["common_name"] == common_name)
            ]
        if not row.empty:
            return {
                "название": row.iloc[0]["common_name"] or common_name,
                "научное_название": scientific_name,
                "полив": row.iloc[0]["watering_frequency"],
                "заметки": row.iloc[0]["notes"],
                "токсичность": row.iloc[0]["toxicity"],
                "пересадка": row.iloc[0]["repotting"],
                "требования_к_освещению": row.iloc[0]["light_requirements"],
                "здоровье": row.iloc[0]["health"]
            }
        return None


# Основная функция
def main():
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(show_plants, pattern='^my_plants$'))
    application.add_handler(CallbackQueryHandler(plant_menu, pattern='^plant_'))
    application.add_handler(CallbackQueryHandler(handle_notification, pattern='^(enable|disable)_'))
    application.add_handler(CallbackQueryHandler(add_plant, pattern='^add_plant$'))
    application.add_handler(CallbackQueryHandler(back_to_start, pattern='^back_to_start$'))
    application.add_handler(CallbackQueryHandler(handle_watered, pattern='^watered_'))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    application.run_polling()


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        logging.error("Error occurred", exc_info=e)