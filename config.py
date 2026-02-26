import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Telegram
    BOT_TOKEN = "8378996136:AAFHQ-NPDbRVljd0Ap02IU9EdohY6Bma-O4"  # ← Новый токен
    
    # Yandex GPT
    YANDEX_FOLDER = "b1gag20fr95ujgos7fv9"
    YANDEX_API_KEY = "AQVnwBeEGS67ZahXn1qrJnKnagKMhZXt8Zqv1a5"
    
    # Yandex Storage
    YC_ACCESS_KEY = "YCAJE1B_EbVzadJJhjffGVMgo"
    YC_SECRET_KEY = "YCNGUXScykRhi4_znH2B0PzmnvgWj7sfS73SLTYX"
    YC_BUCKET_NAME = "cvetnik-photos"
    
    # Admin
    ADMIN_ID = 8378996136
    CHANNEL_ID = "@cvetnik_nsk"
