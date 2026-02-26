import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Telegram - берется из переменных окружения
    BOT_TOKEN = os.getenv('BOT_TOKEN')
    
    # Yandex GPT - берется из переменных окружения
    YANDEX_FOLDER = os.getenv('YANDEX_FOLDER')
    YANDEX_API_KEY = os.getenv('YANDEX_API_KEY')
    
    # Yandex Storage - берется из переменных окружения
    YC_ACCESS_KEY = os.getenv('YC_ACCESS_KEY')
    YC_SECRET_KEY = os.getenv('YC_SECRET_KEY')
    YC_BUCKET_NAME = os.getenv('YC_BUCKET_NAME')
    
    # Admin - преобразуем строку с ID через запятую в список чисел
    ADMIN_IDS = [int(id) for id in os.getenv('ADMIN_IDS', '').split(',') if id]
    
    # Канал для проверки подписки
    CHANNEL_ID = os.getenv('CHANNEL_ID')
