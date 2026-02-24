import os
import sys
import logging
import asyncio
import datetime
import signal
import atexit
from aiohttp import web
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.types import ParseMode
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import google.generativeai as genai

from config import ADMIN_IDS, POST_TIMES
from database import Database

# Принудительная очистка старых процессов
def cleanup():
    print("🧹 Очистка старых процессов...")
    try:
        os.kill(os.getpid(), signal.SIGTERM)
    except:
        pass

atexit.register(cleanup)
signal.signal(signal.SIGTERM, lambda sig, frame: sys.exit(0))

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Инициализация бота и базы данных
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    logger.error("❌ BOT_TOKEN не найден в переменных окружения!")
    exit(1)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)
dp.middleware.setup(LoggingMiddleware())
db = Database()

# Настройка Gemini
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    logger.info("✅ Gemini AI настроен")
else:
    logger.warning("⚠️ GEMINI_API_KEY не задан, AI-генерация работать не будет")

CHANNEL_ID = os.getenv("CHANNEL_ID", "@cvetnik_nsk")
logger.info(f"📢 Канал для публикации: {CHANNEL_ID}")

# --- ВЕБ-СЕРВЕР ДЛЯ ПИНГА ---
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

# Проверка прав администратора
def is_admin(user_id):
    return user_id in ADMIN_IDS

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
        "Используйте /stats чтобы увидеть статистику."
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

# ---------- ГЕНЕРАЦИЯ ТЕКСТА С FALLBACK ----------
async def generate_post_text():
    """Генерация текста поста с fallback на несколько моделей Gemini"""
    
    models_to_try = [
        'gemini-2.5-flash',
        'gemini-2.5-pro',
        'gemini-3.0-flash-preview',
        'gemini-3.1-pro-preview'
    ]
    
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

Пост должен быть на русском, длиной 300-500 символов (без учёта блока в конце)."""
    
    if not GEMINI_API_KEY:
        logger.warning("⚠️ Нет ключа Gemini, использую запасной текст")
        return get_default_post_text(datetime=True)
    
    last_error = None
    used_models = []
    
    for model_name in models_to_try:
        try:
            logger.info(f"🚀 Пробую модель: {model_name}")
            used_models.append(model_name)
            
            current_model = genai.GenerativeModel(model_name)
            await asyncio.sleep(1)
            
            response = current_model.generate_content(prompt)
            
            if response and response.text:
                logger.info(f"✅ Успех с моделью: {model_name}")
                return response.text
            else:
                logger.warning(f"⚠️ Пустой ответ от {model_name}")
                continue
                
        except Exception as e:
            error_str = str(e)
            logger.warning(f"❌ Ошибка с моделью {model_name}: {error_str[:200]}")
            last_error = e
            
            if "429" in error_str or "quota" in error_str.lower():
                logger.info("⏳ Обнаружена ошибка квоты, жду 5 секунд...")
                await asyncio.sleep(5)
                continue
    
    logger.error(f"❌ Все модели не сработали. Последняя ошибка: {last_error}")
    return get_default_post_text(datetime=True)

def get_default_post_text(datetime=False):
    """Запасной текст, если AI не сработает"""
    if datetime:
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
    else:
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

# ---------- ОБНОВЛЕННАЯ ФУНКЦИЯ ПУБЛИКАЦИИ С ОБНУЛЕНИЕМ ----------
async def post_random_photo():
    """Публикация случайного фото из базы с автоматическим обнулением"""
    logger.info("⏰ Запуск публикации по расписанию")
    
    photo = db.get_random_unposted_photo()
    
    # Если фото нет, обнуляем все и берем любое
    if not photo:
        logger.warning("⚠️ Все фото опубликованы, обнуляю статистику...")
        
        # Подсчитываем, сколько всего было фото
        stats = db.get_stats()
        total_photos = stats['total']
        
        # Обнуляем все фото (устанавливаем posted = 0 для всех)
        db.reset_all_photos()
        
        # Отправляем уведомление админам
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
        
        # Берем любое фото (теперь все снова доступны)
        photo = db.get_random_unposted_photo()
        
        if not photo:
            logger.error("❌ Критическая ошибка: нет фото даже после обнуления!")
            return
    
    logger.info(f"🖼️ Выбрано фото для публикации: {photo['file_id']}")
    
    # Генерируем текст поста
    post_text = await generate_post_text()
    
    # Публикуем в канал
    try:
        with open(photo['file_path'], 'rb') as photo_file:
            await bot.send_photo(
                chat_id=CHANNEL_ID,
                photo=photo_file,
                caption=post_text,
                parse_mode=ParseMode.HTML
            )
        
        # Отмечаем фото как опубликованное
        db.mark_as_posted(photo['id'])
        stats = db.get_stats()
        logger.info(f"✅ Пост опубликован. Осталось фото: {stats['pending']}")
    except Exception as e:
        logger.error(f"❌ Ошибка при публикации: {e}")

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
