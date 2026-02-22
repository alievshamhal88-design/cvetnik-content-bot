import os
import logging
import asyncio
import random
from datetime import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.types import ParseMode
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import google.generativeai as genai

from config import ADMIN_IDS, POST_TIMES
from database import Database

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Инициализация бота и базы данных
bot = Bot(token=os.getenv("BOT_TOKEN"))
dp = Dispatcher(bot)
dp.middleware.setup(LoggingMiddleware())
db = Database()

# Настройка Gemini
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-pro')

CHANNEL_ID = os.getenv("CHANNEL_ID")

# Проверка прав администратора
def is_admin(user_id):
    return user_id in ADMIN_IDS

@dp.message_handler(commands=['start'])
async def cmd_start(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.reply("⛔️ У вас нет доступа к этому боту.")
        return
    
    await message.reply(
        "🌸 Привет! Я бот для автоматического постинга в канал.\n\n"
        "📸 Просто отправляйте мне фото, и я буду их публиковать по расписанию.\n"
        "Каждый пост будет содержать описание от ИИ и ваши контакты.\n\n"
        "Используйте /stats чтобы увидеть статистику."
    )

@dp.message_handler(commands=['stats'])
async def cmd_stats(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    
    stats = db.get_stats()
    await message.reply(
        f"📊 **Статистика**\n\n"
        f"📸 Всего фото: {stats['total']}\n"
        f"✅ Опубликовано: {stats['posted']}\n"
        f"⏳ В очереди: {stats['pending']}"
    )

@dp.message_handler(content_types=['photo'])
async def handle_photo(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    
    photo = message.photo[-1]
    file_id = photo.file_id
    
    # Сохраняем фото
    file_info = await bot.get_file(file_id)
    file_path = f"data/photos/{file_id}.jpg"
    await bot.download_file(file_info.file_path, file_path)
    
    # Сохраняем в базу
    db.add_photo(file_id, file_path)
    
    await message.reply("✅ Фото добавлено в очередь на публикацию!")

async def generate_post_text():
    """Генерация текста поста через Gemini"""
    prompt = """Напиши красивый пост для Telegram канала цветочного магазина о букете на фото.
Используй тёплый, вдохновляющий, немного поэтичный стиль.
Опиши, какие могут быть чувства у получателя, для какого повода подойдёт.
В конце обязательно добавь этот блок (скопируй точно):

Цветник 🌸 | Новосибирск
Свежие цветы и букеты с доставкой 💐
Заказ онлайн 👉 Открыть каталог (https://cvetniknsk.ru/)

Мы на ⭐️📍 2ГИС 3 филиала (https://2gis.ru/novosibirsk/branches/70000001091590889)
⚡️ Быстрый заказ 👉 @cvetniknsk_bot

📍 2-я Марата, 22 — @cvetnik_sib
📍 Некрасова, 41 — @cvetnik1_sib
📍 Связистов, 113А — @cvetniksvezistrov

Пост должен быть на русском, длиной 300-500 символов (без учёта блока в конце).
"""
    
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        logger.error(f"Ошибка генерации текста: {e}")
        # Запасной вариант, если AI не сработает
        return (
            "🌸 Прекрасный букет для особенного момента!\n\n"
            "Пусть цветы скажут всё, что вы чувствуете 💐\n\n"
            "Цветник 🌸 | Новосибирск\n"
            "Свежие цветы и букеты с доставкой 💐\n"
            "Заказ онлайн 👉 Открыть каталог (https://cvetniknsk.ru/)\n\n"
            "Мы на ⭐️📍 2ГИС 3 филиала (https://2gis.ru/novosibirsk/branches/70000001091590889)\n"
            "⚡️ Быстрый заказ 👉 @cvetniknsk_bot\n\n"
            "📍 2-я Марата, 22 — @cvetnik_sib\n"
            "📍 Некрасова, 41 — @cvetnik1_sib\n"
            "📍 Связистов, 113А — @cvetniksvezistrov"
        )

async def post_random_photo():
    """Публикация случайного фото из базы"""
    photo = db.get_random_unposted_photo()
    if not photo:
        # Уведомляем админов, что фото кончились
        for admin_id in ADMIN_IDS:
            await bot.send_message(
                admin_id,
                "⚠️ Внимание! Все фото уже опубликованы.\n"
                "Пожалуйста, добавьте новые фото в бота."
            )
        return
    
    # Генерируем текст поста
    post_text = await generate_post_text()
    
    # Публикуем в канал
    with open(photo['file_path'], 'rb') as photo_file:
        await bot.send_photo(
            chat_id=CHANNEL_ID,
            photo=photo_file,
            caption=post_text,
            parse_mode=ParseMode.HTML
        )
    
    # Отмечаем фото как опубликованное
    db.mark_as_posted(photo['id'])
    
    logger.info(f"Пост опубликован. Осталось фото: {db.get_pending_count()}")

async def setup_scheduler():
    """Настройка планировщика"""
    scheduler = AsyncIOScheduler()
    
    # Разбираем время из POST_TIMES
    for time_str in POST_TIMES:
        hour, minute = map(int, time_str.split(':'))
        # Переводим в UTC (Новосибирск UTC+7)
        utc_hour = hour - 7
        if utc_hour < 0:
            utc_hour += 24
            
        scheduler.add_job(
            post_random_photo,
            trigger=CronTrigger(hour=utc_hour, minute=minute)
        )
        logger.info(f"Запланирован пост на {hour:02d}:{minute:02d} MSK (UTC {utc_hour:02d}:{minute:02d})")
    
    scheduler.start()
    logger.info("Планировщик запущен")

async def on_startup(dp):
    """Действия при запуске бота"""
    await setup_scheduler()
    logger.info("Бот запущен")

async def on_shutdown(dp):
    """Действия при остановке бота"""
    db.close()
    logger.info("Бот остановлен")

if __name__ == '__main__':
    from aiogram import executor
    executor.start_polling(dp, on_startup=on_startup, on_shutdown=on_shutdown)
