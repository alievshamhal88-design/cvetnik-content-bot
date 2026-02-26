#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sqlite3
import logging
import boto3
from botocore.client import Config
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Подключаемся к базе
db_path = "content_bot.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Создаем таблицу если её нет
cursor.execute('''
    CREATE TABLE IF NOT EXISTS bouquets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        file_id TEXT UNIQUE,
        photo_url TEXT,
        file_name TEXT,
        name TEXT DEFAULT "Букет",
        description TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
''')

# Настройки Яндекс.Облака
access_key = os.getenv("YC_ACCESS_KEY")
secret_key = os.getenv("YC_SECRET_KEY")
bucket_name = os.getenv("YC_BUCKET_NAME", "cvetnik-photos")

# Подключаемся к S3
s3 = boto3.client(
    's3',
    endpoint_url='https://storage.yandexcloud.net',
    aws_access_key_id=access_key,
    aws_secret_access_key=secret_key,
    config=Config(signature_version='s3v4'),
    region_name='ru-central1'
)

# Получаем список всех фото из папки bouquets/
logger.info("📸 Сканируем облако...")
response = s3.list_objects_v2(Bucket=bucket_name, Prefix='bouquets/')

if 'Contents' not in response:
    logger.info("📭 В облаке нет фото")
    exit()

# Добавляем каждое фото в базу
count = 0
for obj in response['Contents']:
    file_name = obj['Key']
    photo_url = f"https://{bucket_name}.storage.yandexcloud.net/{file_name}"
    
    # Генерируем file_id из имени файла
    file_id = file_name.replace('bouquets/', '').replace('.jpg', '')
    
    try:
        cursor.execute('''
            INSERT OR IGNORE INTO bouquets (file_id, photo_url, file_name, name)
            VALUES (?, ?, ?, ?)
        ''', (file_id, photo_url, file_name, "Букет"))
        
        if cursor.rowcount > 0:
            count += 1
            logger.info(f"✅ Добавлено: {file_name}")
            
    except Exception as e:
        logger.error(f"❌ Ошибка: {e}")

conn.commit()
logger.info(f"🎉 Готово! Добавлено {count} фото в базу")
conn.close()
