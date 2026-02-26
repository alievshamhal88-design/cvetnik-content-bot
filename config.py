import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Telegram
    BOT_TOKEN = os.getenv('BOT_TOKEN')
    
    # Yandex GPT
    YANDEX_FOLDER = os.getenv('YANDEX_FOLDER')
    YANDEX_API_KEY = os.getenv('YANDEX_API_KEY')
    
    # Yandex Storage
    YC_ACCESS_KEY = os.getenv('YC_ACCESS_KEY')
    YC_SECRET_KEY = os.getenv('YC_SECRET_KEY')
    YC_BUCKET_NAME = os.getenv('YC_BUCKET_NAME')
    
    # Admin
    ADMIN_IDS = [int(id) for id in os.getenv('ADMIN_IDS', '').split(',') if id]
    
    # Канал
    CHANNEL_ID = os.getenv('CHANNEL_ID')
