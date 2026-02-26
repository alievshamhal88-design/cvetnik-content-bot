import boto3
import os
import logging
from botocore.client import Config as BotoConfig
from botocore.exceptions import ClientError
from typing import Optional
import uuid
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

class YandexStorageClient:
    def __init__(self):
        """Инициализация клиента для Яндекс.Object Storage"""
        self.access_key = os.getenv("YC_ACCESS_KEY")
        self.secret_key = os.getenv("YC_SECRET_KEY")
        self.bucket_name = os.getenv("YC_BUCKET_NAME")
        self.endpoint_url = "https://storage.yandexcloud.net"
        
        if not self.access_key or not self.secret_key or not self.bucket_name:
            raise ValueError("❌ Отсутствуют ключи доступа к Яндекс.Облаку")
        
        logger.info(f"🔑 Access Key (первые 10 символов): {self.access_key[:10]}...")
        logger.info(f"🔐 Secret Key (первые 5 символов): {self.secret_key[:5]}...")
        logger.info(f"📦 Bucket: {self.bucket_name}")
        
        # ВАЖНО: правильная конфигурация для Яндекс.Облака
        self.s3 = boto3.client(
            's3',
            endpoint_url=self.endpoint_url,
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            config=BotoConfig(
                signature_version='s3v4',
                region_name='ru-central1',
                s3={'addressing_style': 'virtual'}  # важно для Яндекс.Облака
            ),
            region_name='ru-central1'
        )
        logger.info("✅ Storage клиент инициализирован")
        
        # Проверяем доступ к бакету
        try:
            self.s3.head_bucket(Bucket=self.bucket_name)
            logger.info(f"✅ Доступ к бакету {self.bucket_name} подтвержден")
        except ClientError as e:
            logger.error(f"❌ Ошибка доступа к бакету: {e}")

    def upload_file(self, file_bytes: bytes, file_name: str = None, content_type: str = 'image/jpeg') -> Optional[str]:
        """Загружает файл в Яндекс.Облако и возвращает публичную ссылку"""
        try:
            if file_name is None:
                file_name = f"bouquets/{uuid.uuid4()}.jpg"
            
            logger.info(f"📤 Загружаю файл: {file_name}")
            logger.info(f"📦 Размер файла: {len(file_bytes)} байт")
            
            # ВАЖНО: указываем ACL='public-read' для публичного доступа
            self.s3.put_object(
                Bucket=self.bucket_name,
                Key=file_name,
                Body=file_bytes,
                ContentType=content_type,
                ACL='public-read'  # это делает файл публичным
            )
            
            # Формируем публичную ссылку
            url = f"https://{self.bucket_name}.storage.yandexcloud.net/{file_name}"
            logger.info(f"✅ Файл успешно загружен: {url}")
            return url
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_msg = e.response['Error']['Message']
            logger.error(f"❌ Ошибка загрузки {error_code}: {error_msg}")
            
            if error_code == 'AccessDenied':
                logger.error("🔑 AccessDenied - проверьте настройки бакета:")
                logger.error("   1. В бакете cvetnik-photos → вкладка 'Доступ'")
                logger.error("   2. Установите 'Чтение объектов' → 'Для всех' (публичный доступ)")
                logger.error("   3. ИЛИ добавьте сервисный аккаунт с правами READ и WRITE")
            return None

    def delete_file(self, file_name: str) -> bool:
        """Удаляет файл из облака"""
        try:
            self.s3.delete_object(
                Bucket=self.bucket_name,
                Key=file_name
            )
            logger.info(f"✅ Файл удалён: {file_name}")
            return True
        except ClientError as e:
            logger.error(f"❌ Ошибка удаления: {e}")
            return False

    def get_file_url(self, file_name: str) -> str:
        """Возвращает публичную ссылку на файл"""
        return f"https://{self.bucket_name}.storage.yandexcloud.net/{file_name}"
