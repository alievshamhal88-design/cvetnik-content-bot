import boto3
import os
import logging
from botocore.client import Config
from botocore.exceptions import ClientError
from typing import Optional

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
        
        # Создаем S3-клиент (совместимый с Яндекс.Облаком)
        self.s3 = boto3.client(
            's3',
            endpoint_url=self.endpoint_url,
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            config=Config(signature_version='s3v4'),
            region_name='ru-central1'
        )
        logger.info(f"✅ Storage клиент инициализирован для бакета {self.bucket_name}")

    def upload_file(self, file_bytes: bytes, file_name: str, content_type: str = 'image/jpeg') -> Optional[str]:
        """
        Загружает файл в Яндекс.Облако и возвращает публичную ссылку
        """
        try:
            # Загружаем файл
            self.s3.put_object(
                Bucket=self.bucket_name,
                Key=file_name,
                Body=file_bytes,
                ContentType=content_type,
                ACL='public-read'
            )
            
            # Формируем ссылку
            url = f"https://{self.bucket_name}.storage.yandexcloud.net/{file_name}"
            logger.info(f"✅ Файл загружен: {url}")
            return url
            
        except ClientError as e:
            logger.error(f"❌ Ошибка загрузки в облако: {e}")
            return None

    def get_file_url(self, file_name: str) -> str:
        """Возвращает публичную ссылку на файл"""
        return f"https://{self.bucket_name}.storage.yandexcloud.net/{file_name}"
