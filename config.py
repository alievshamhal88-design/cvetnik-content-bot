import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Telegram - НОВЫЙ ТОКЕН для @content_cvetnik_bot
    BOT_TOKEN = "8736488668:AAEsz_Ws3iYMOR8odf7-k-jTE_ctuClgJVE"
    
    # Yandex GPT
    YANDEX_FOLDER = "b1gag20fr95ujgos7fv9"
    YANDEX_API_KEY = "AQVnwBeEGS67ZahXn1qrJnKnagKMhZXt8Zqv1a5"
    
    # Yandex Storage
    YC_ACCESS_KEY = "YCAJE1B_EbVzadJJhjffGVMgo"
    YC_SECRET_KEY = "YCNGUXScykRhi4_znH2B0PzmnvgWj7sfS73SLTYX"
    YC_BUCKET_NAME = "cvetnik-photos"
    
    # Admin - два админа (ваш ID и второй админ)
    ADMIN_IDS = [7750251679, 123456789]  # 7750251679 - это вы, 123456789 - замените на ID второго админа
    
    # Канал для проверки подписки
    CHANNEL_ID = "@cvetnik_nsk"
