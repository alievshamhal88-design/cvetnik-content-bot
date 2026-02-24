import os
import sys
import logging
import asyncio
import datetime
import signal
import atexit
import random
from io import BytesIO
from PIL import Image
from aiohttp import web
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.types import ParseMode, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import google.generativeai as genai

from config import ADMIN_IDS, POST_TIMES, GEMINI_MODELS
from database import Database

# ============================================
# НАСТРОЙКИ
# ============================================
BOT_TOKEN = os.getenv("BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not BOT_TOKEN:
    logger.error("❌ BOT_TOKEN не найден в переменных окружения!")
    exit(1)

if not GEMINI_API_KEY:
    logger.warning("⚠️ GEMINI_API_KEY не задан, AI-генерация работать не будет")
else:
    genai.configure(api_key=GEMINI_API_KEY)

# ============================================
# ЛОГИРОВАНИЕ
# ============================================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================
# ИНИЦИАЛИЗАЦИЯ
# ============================================
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)
dp.middleware.setup(LoggingMiddleware())
db = Database()

CHANNEL_ID = os.getenv("CHANNEL_ID", "@cvetnik_nsk")
logger.info(f"📢 Канал для публикации: {CHANNEL_ID}")

# ============================================
# ФУНКЦИИ ДЛЯ GEMINI
# ============================================
async def generate_post_with_ai(photo_file_id):
    """
    Gemini смотрит на фото и генерирует название + описание для поста
    """
    
    # Запасной текст
    def get_fallback_text():
        now = datetime.datetime.now().strftime("%d.%m.%Y %H:%M")
        return (
            f"🌸 Пост от {now}\n\n"
            f"(Сгенерировано вручную, AI временно недоступен)\n\n"
            f"Цветник 🌸 | Новосибирск\n"
            f"Свежие цветы и букеты с доставкой 💐\n"
            f"Заказ онлайн 👉 Открыть каталог (https://cvetniknsk.ru/)\n\n"
            f"Мы на ⭐️📍 2ГИС 3 филиала (https://2gis.ru/novosibirsk/branches/70000001091590889)\n"
            f"⚡️ Быстрый заказ 👉 @cvetniknsk_bot\n\n"
            f"📍 2-я Марата, 22 — @cvetnik_sib\n"
            f"📍 Некрасова, 41 — @cvetnik1_sib\n"
            f"📍 Связистов, 113А — @cvetniksvezistrov"
        )
    
    if not GEMINI_API_KEY or not photo_file_id:
        return get_fallback_text()
    
    try:
        # Скачиваем фото
        file_info = await bot.get_file(photo_file_id)
        file_bytes = await bot.download_file(file_info.file_path)
        
        # Открываем изображение
        image = Image.open(BytesIO(file_bytes.read()))
        
        # Промпт для Gemini
        prompt = (
            "Посмотри на это фото букета цветов. Напиши для него:\n\n"
            "1. КРАСИВОЕ НАЗВАНИЕ (2-4 слова, поэтичное, на русском)\n"
            "2. КОРОТКОЕ ОПИСАНИЕ (2-3 предложения о букете: какие цветы, "
            "какое настроение, для какого повода подойдёт)\n\n"
            "Формат ответа (строго соблюдай):\n"
            "Название: ...\n"
            "Описание: ..."
        )
        
        # Пробуем разные модели
        result = None
        for model_name in GEMINI_MODELS:
            try:
                model = genai.GenerativeModel(model_name)
                response = model.generate_content([prompt, image])
                if response and response.text:
                    result = response.text
                    logger.info(f"✅ Gemini {model_name} сгенерировал текст")
                    break
            except Exception as e:
                logger.warning(f"⚠️ Модель {model_name} не сработала: {e}")
                continue
        
        if result:
            # Парсим ответ
            lines = result.split('\n')
            name = "Волшебный букет"
            description = "Нежный букет для особенного случая."
            
            for line in lines:
                if line.startswith('Название:'):
                    name = line.replace('Название:', '').strip()
                elif line.startswith('Описание:'):
                    description = line.replace('Описание:', '').strip()
            
            # Формируем полный текст поста
            post_text = (
                f"🌸 **{name}** 🌸\n\n"
                f"{description}\n\n"
                f"Цветник 🌸 | Новосибирск\n"
                f"Свежие цветы и букеты с доставкой 💐\n"
                f"Заказ онлайн 👉 Открыть каталог (https://cvetniknsk.ru/)\n\n"
                f"Мы на ⭐️📍 2ГИС 3 филиала (https://2gis.ru/novosibirsk/branches/70000001091590889)\n"
                f"⚡️ Быстрый заказ 👉 @cvetniknsk_bot\n\n"
                f"📍 2-я Марата, 22 — @cvetnik_sib\n"
                f"📍 Некрасова, 41 — @cvetnik1_sib\n"
                f"📍 Связистов, 113А — @cvetniksvezistrov"
            )
            
            return post_text
        
    except Exception as e:
        logger.error(f"❌ Ошибка Gemini: {e}")
    
    return get_fallback_text()

# ============================================
# ПИНГ-СЕРВЕР
# ============================================
async def handle_ping(request):
    return web.Response(text='OK')

async def run_web_server():
    app = web.Application()
    app.router.add_get('/', handle_ping)
    app.router.add_get('/ping', handle_ping)
    app.router.add_get('/health', handle_ping)
    
    port = int(os.environ.get('PORT', 10000))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    logger.info(f"✅ Пинг-сервер запущен на порту {port}")

# ============================================
# ПРОВЕРКА ПРАВ АДМИНИСТРАТОРА
# ============================================
def is_admin(user_id):
    return user_id in ADMIN_IDS

# ============================================
# ОБРАБОТЧИКИ КОМАНД
# ============================================
@dp.message_handler(commands=['start'])
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    logger.info(f"🖥️ Команда /start от пользователя {user_id}")
    
    if not is_admin(user_id):
        logger.warning(f"⛔️ Доступ запрещён для {user_id}")
        await message.reply("⛔️ У вас нет доступа к этому боту.")
        return
    
    await message.reply(
        "🌸 Привет! Я бот для автоматического постинга в канал.\n\n"
        "📸 Просто отправляйте мне фото, и я буду их публиковать по расписанию.\n"
        "Каждый пост будет содержать описание от ИИ и ваши контакты.\n\n"
        "Используйте /stats чтобы увидеть статистику.\n"
        "Используйте /reset чтобы сбросить статусы всех фото."
    )

@dp.message_handler(commands=['stats'])
async def cmd_stats(message: types.Message):
    user_id = message.from_user.id
    logger.info(f"📊 Команда /stats от пользователя {user_id}")
    
    if not is_admin(user_id):
        logger.warning(f"⛔️ Доступ запрещён для {user_id}")
        return
    
    stats = db.get_stats()
    await message.reply(
        f"📊 **Статистика**\n\n"
        f"📸 Всего фото: {stats['total']}\n"
        f"✅ Опубликовано: {stats['posted']}\n"
        f"⏳ В очереди: {stats['pending']}",
        parse_mode=ParseMode.MARKDOWN
    )

@dp.message_handler(commands=['reset'])
async def cmd_reset(message: types.Message):
    user_id = message.from_user.id
    logger.info(f"🔄 Команда /reset от пользователя {user_id}")
    
    if not is_admin(user_id):
        logger.warning(f"⛔️ Доступ запрещён для {user_id}")
        await message.reply("⛔️ Нет доступа")
        return
    
    db.reset_all_photos()
    stats = db.get_stats()
    
    await message.reply(
        f"🔄 **Все фото сброшены!**\n\n"
        f"📸 Всего фото: {stats['total']}\n"
        f"✅ Опубликовано: 0\n"
        f"⏳ В очереди: {stats['pending']}",
        parse_mode='Markdown'
    )

# ============================================
# ОБРАБОТКА ФОТО
# ============================================
@dp.message_handler(content_types=['photo'])
async def handle_photo(message: types.Message):
    user_id = message.from_user.id
    logger.info(f"📸 Получено фото от пользователя {user_id}")
    
    if not is_admin(user_id):
        logger.warning(f"⛔️ Пользователь {user_id} не админ, фото не сохранено")
        await message.reply("⛔️ У вас нет доступа к этому боту.")
        return
    
    try:
        photo = message.photo[-1]
        file_id = photo.file_id
        logger.info(f"🆔 File_id: {file_id}")
        
        file_info = await bot.get_file(file_id)
        file_path = f"data/photos/{file_id}.jpg"
        await bot.download_file(file_info.file_path, file_path)
        logger.info(f"💾 Фото сохранено: {file_path}")
        
        success = db.add_photo(file_id, file_path)
        
        if success:
            await message.reply("✅ Фото добавлено в очередь на публикацию!")
        else:
            await message.reply("❌ Ошибка при сохранении фото в базу данных")
            
    except Exception as e:
        logger.error(f"❌ Ошибка при обработке фото: {e}")
        await message.reply(f"❌ Произошла ошибка: {e}")

# ============================================
# ПУБЛИКАЦИЯ ПОСТА
# ============================================
async def post_random_photo():
    """Публикация случайного фото с AI-генерацией текста"""
    logger.info("⏰ Запуск публикации по расписанию")
    
    photo = db.get_random_unposted_photo()
    
    # Если фото нет, обнуляем все и берем любое
    if not photo:
        logger.warning("⚠️ Все фото опубликованы, обнуляю статистику...")
        stats = db.get_stats()
        total_photos = stats['total']
        
        db.reset_all_photos()
        
        for admin_id in ADMIN_IDS:
            try:
                await bot.send_message(
                    admin_id,
                    f"🔄 **Круг публикаций завершен!**\n\n"
                    f"📸 Всего опубликовано: {total_photos} фото\n"
                    f"✨ Начинаю публиковать заново с начала.\n\n"
                    f"Хотите добавить новые фото? Просто отправьте их мне!",
                    parse_mode='Markdown'
                )
            except Exception as e:
                logger.error(f"❌ Не удалось отправить уведомление админу {admin_id}: {e}")
        
        photo = db.get_random_unposted_photo()
        
        if not photo:
            logger.error("❌ Критическая ошибка: нет фото даже после обнуления!")
            return
    
    logger.info(f"🖼️ Выбрано фото для публикации: {photo['file_id']}")
    
    # Генерируем текст поста через AI
    post_text = await generate_post_with_ai(photo['file_id'])
    
    # Публикуем в канал
    try:
        with open(photo['file_path'], 'rb') as photo_file:
            await bot.send_photo(
                chat_id=CHANNEL_ID,
                photo=photo_file,
                caption=post_text,
                parse_mode=ParseMode.HTML
            )
        
        db.mark_as_posted(photo['id'])
        stats = db.get_stats()
        logger.info(f"✅ Пост опубликован. Осталось фото: {stats['pending']}")
        
    except Exception as e:
        logger.error(f"❌ Ошибка при публикации: {e}")

# ============================================
# ПЛАНИРОВЩИК
# ============================================
async def setup_scheduler():
    scheduler = AsyncIOScheduler()
    
    for time_str in POST_TIMES:
        try:
            hour, minute = map(int, time_str.split(':'))
            utc_hour = hour - 7
            if utc_hour < 0:
                utc_hour += 24
                
            scheduler.add_job(
                post_random_photo,
                trigger=CronTrigger(hour=utc_hour, minute=minute)
            )
            logger.info(f"📅 Запланирован пост на {hour:02d}:{minute:02d} MSK (UTC {utc_hour:02d}:{minute:02d})")
        except Exception as e:
            logger.error(f"❌ Ошибка в настройке времени {time_str}: {e}")
    
    scheduler.start()
    logger.info("✅ Планировщик запущен")

# ============================================
# ЗАПУСК И ОСТАНОВКА
# ============================================
async def on_startup(dp):
    logger.info("🚀 Бот запускается...")
    asyncio.create_task(run_web_server())
    await setup_scheduler()
    logger.info("🚀 Бот-постер запущен")

async def on_shutdown(dp):
    db.close()
    logger.info("👋 Бот-постер остановлен")

if __name__ == '__main__':
    from aiogram import executor
    executor.start_polling(dp, on_startup=on_startup, on_shutdown=on_shutdown)
