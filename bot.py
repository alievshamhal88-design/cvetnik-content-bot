#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import asyncio
import uuid
import threading
import requests
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

from config import Config
from database import Database
from yandex_client import YandexGPT, YandexStorage
from web_server import start_health_server

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Функция принудительного сброса подключений
def force_reset_bot():
    """Отключает все старые вебхуки и сбрасывает pending updates"""
    try:
        token = Config.BOT_TOKEN
        url = f"https://api.telegram.org/bot{token}/deleteWebhook?drop_pending_updates=true"
        response = requests.get(url)
        if response.status_code == 200:
            logger.info("✅ Все старые подключения сброшены")
        else:
            logger.warning(f"⚠️ Ошибка сброса: {response.text}")
    except Exception as e:
        logger.error(f"❌ Ошибка при сбросе: {e}")

# Инициализация компонентов
db = Database()
storage = YandexStorage()
gpt = YandexGPT()

# Временное хранилище для состояний
user_data = {}

# Проверка на администратора
def is_admin(user_id):
    return user_id in Config.ADMIN_IDS

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    user = update.effective_user
    welcome_text = (
        f"👋 Привет, {user.first_name}!\n\n"
        "Я бот для генерации контента для цветочного магазина.\n\n"
        "📝 Доступные команды:\n"
        "/start - приветствие\n"
        "/help - помощь\n"
        "/list - список всех букетов\n"
        "/generate - сгенерировать описание для последнего букета\n"
        "/myid - показать ваш Telegram ID\n"
        "/admin - проверить права администратора\n\n"
        "Просто отправь мне фото букета, и я сохраню его в облако!"
    )
    await update.message.reply_text(welcome_text)

# Команда /help
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /help"""
    help_text = (
        "📋 *Справка по командам:*\n\n"
        "/start - приветствие\n"
        "/help - это сообщение\n"
        "/list - список всех букетов\n"
        "/generate - сгенерировать описание для последнего букета\n"
        "/myid - показать ваш Telegram ID\n"
        "/admin - проверить права администратора\n\n"
        "📸 *Работа с фото:*\n"
        "Отправьте фото букета - оно сохранится в Яндекс.Облако\n"
        "После сохранения можно сгенерировать описание через YandexGPT"
    )
    await update.message.reply_text(help_text, parse_mode='Markdown')

# Команда для проверки своего ID
async def show_my_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает ваш Telegram ID"""
    user_id = update.effective_user.id
    is_admin_status = "✅ Администратор" if is_admin(user_id) else "❌ Не администратор"
    await update.message.reply_text(
        f"Ваш Telegram ID: `{user_id}`\n"
        f"Статус: {is_admin_status}",
        parse_mode='Markdown'
    )

# Обработчик фото
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик получения фото"""
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("❌ У вас нет прав для загрузки фото")
        return
    
    try:
        photo = update.message.photo[-1]
        file_id = photo.file_id
        file_unique_id = photo.file_unique_id
        
        status_msg = await update.message.reply_text("⏳ Сохраняю фото в облако...")
        
        file = await context.bot.get_file(file_id)
        file_bytes = await file.download_as_bytearray()
        
        file_name = f"bouquets/{file_unique_id}.jpg"
        photo_url = storage.upload_file(bytes(file_bytes), file_name)
        
        if photo_url:
            bouquet_id = db.add_bouquet(file_id, photo_url, file_name)
            
            if bouquet_id:
                user_data[user_id] = {'last_bouquet_id': bouquet_id}
                
                keyboard = [
                    [InlineKeyboardButton("✨ Сгенерировать описание", callback_data=f"generate_{bouquet_id}")],
                    [InlineKeyboardButton("📋 Список всех букетов", callback_data="list")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await status_msg.edit_text(
                    f"✅ Фото успешно сохранено!\n\n"
                    f"📸 ID букета: {bouquet_id}\n"
                    f"🔗 Ссылка: {photo_url}",
                    reply_markup=reply_markup
                )
            else:
                await status_msg.edit_text("❌ Ошибка при сохранении в базу данных")
        else:
            await status_msg.edit_text("❌ Ошибка при загрузке в облако")
            
    except Exception as e:
        logger.error(f"Ошибка обработки фото: {e}")
        await update.message.reply_text(f"❌ Ошибка: {e}")

# Команда /list
async def list_bouquets(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает список всех букетов"""
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("❌ У вас нет прав")
        return
    
    bouquets = db.get_all_bouquets()
    
    if not bouquets:
        await update.message.reply_text("📭 В базе пока нет букетов")
        return
    
    await update.message.reply_text(f"📊 Всего букетов: {len(bouquets)}")
    
    for bouquet in bouquets[:5]:
        keyboard = [
            [InlineKeyboardButton("✨ Сгенерировать описание", callback_data=f"generate_{bouquet['id']}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        caption = f"🌸 *Букет #{bouquet['id']}*\n"
        if bouquet['description']:
            caption += f"\n📝 {bouquet['description'][:100]}..."
        else:
            caption += "\n❌ Описание отсутствует"
        
        await update.message.reply_photo(
            photo=bouquet['photo_url'],
            caption=caption,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

# Команда /generate
async def generate_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Генерирует описание для последнего букета"""
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("❌ У вас нет прав")
        return
    
    if user_id not in user_data or 'last_bouquet_id' not in user_data[user_id]:
        await update.message.reply_text("❌ Сначала отправьте фото букета")
        return
    
    bouquet_id = user_data[user_id]['last_bouquet_id']
    await generate_description(update, context, bouquet_id)

# Функция генерации описания
async def generate_description(update: Update, context: ContextTypes.DEFAULT_TYPE, bouquet_id):
    """Генерирует описание для указанного букета"""
    user_id = update.effective_user.id
    
    bouquet = db.get_bouquet(bouquet_id)
    if not bouquet:
        await update.message.reply_text("❌ Букет не найден")
        return
    
    status_msg = await update.message.reply_text("⏳ Генерирую описание через YandexGPT...")
    
    prompt = f"Составь красивое описание для букета цветов. Название букета: {bouquet['name']}. Опиши цветы, их значение, кому подойдет такой букет."
    description = gpt.generate_description(prompt)
    
    if description:
        db.update_description(bouquet_id, description)
        db.add_generation(bouquet_id, prompt, description)
        
        keyboard = [
            [InlineKeyboardButton("📋 Список букетов", callback_data="list")],
            [InlineKeyboardButton("🔄 Сгенерировать снова", callback_data=f"generate_{bouquet_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await status_msg.edit_text(
            f"✅ *Описание сгенерировано!*\n\n"
            f"📝 {description}\n\n"
            f"🌸 Букет #{bouquet_id}",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    else:
        await status_msg.edit_text("❌ Ошибка генерации описания")

# Обработчик callback-запросов
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик нажатий на кнопки"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    if not is_admin(user_id):
        await query.edit_message_text("❌ У вас нет прав")
        return
    
    data = query.data
    
    if data == "list":
        bouquets = db.get_all_bouquets()
        
        if not bouquets:
            await query.edit_message_text("📭 В базе пока нет букетов")
            return
        
        await query.edit_message_text(f"📊 Всего букетов: {len(bouquets)}")
        
        for bouquet in bouquets[:3]:
            keyboard = [
                [InlineKeyboardButton("✨ Сгенерировать описание", callback_data=f"generate_{bouquet['id']}")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            caption = f"🌸 *Букет #{bouquet['id']}*\n"
            if bouquet['description']:
                caption += f"\n📝 {bouquet['description'][:100]}..."
            else:
                caption += "\n❌ Описание отсутствует"
            
            await query.message.reply_photo(
                photo=bouquet['photo_url'],
                caption=caption,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        
    elif data.startswith("generate_"):
        bouquet_id = int(data.split("_")[1])
        await generate_description(update, context, bouquet_id)

# Команда /admin
async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Проверка прав администратора"""
    user_id = update.effective_user.id
    
    if is_admin(user_id):
        await update.message.reply_text("✅ Вы администратор")
    else:
        await update.message.reply_text("❌ Вы не администратор")

# Обработка ошибок
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик ошибок"""
    logger.error(f"Ошибка: {context.error}")

def main():
    """Главная функция"""
    # Принудительный сброс перед запуском
    force_reset_bot()
    
    # Запускаем сервер для проверки здоровья
    start_health_server()
    logger.info("✅ Сервер здоровья запущен")
    
    # Создаем приложение
    application = Application.builder().token(Config.BOT_TOKEN).build()
    
    # Добавляем обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("list", list_bouquets))
    application.add_handler(CommandHandler("generate", generate_command))
    application.add_handler(CommandHandler("admin", admin))
    application.add_handler(CommandHandler("myid", show_my_id))
    
    # Обработчик фото
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    
    # Обработчик callback-кнопок
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # Обработчик ошибок
    application.add_error_handler(error_handler)
    
    # Запускаем бота
    logger.info("🚀 Бот контента запущен...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
