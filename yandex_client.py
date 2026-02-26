import requests
import logging
import boto3
from botocore.client import Config as BotoConfig
from botocore.exceptions import ClientError
from typing import Optional
import uuid
from config import Config

logger = logging.getLogger(__name__)

class YandexGPT:
    def __init__(self):
        self.folder_id = Config.YANDEX_FOLDER
        self.api_key = Config.YANDEX_API_KEY
        self.url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
        
    def generate_description(self, prompt: str) -> Optional[str]:
        try:
            headers = {
                "Authorization": f"Api-Key {self.api_key}",
                "Content-Type": "application/json"
            }
            
            data = {
                "modelUri": f"gpt://{self.folder_id}/yandexgpt-lite",
                "completionOptions": {
                    "stream": False,
                    "temperature": 0.6,
                    "maxTokens": 200
                },
                "messages": [
                    {
                        "role": "system",
                        "text": "Ты - профессиональный флорист и копирайтер. Составляй красивые описания для букетов цветов."
                    },
                    {
                        "role": "user",
                        "text": prompt
                    }
                ]
            }
            
            response = requests.post(self.url, headers=headers, json=data)
            response.raise_for_status()
            
            result = response.json()
            description = result['result']['alternatives'][0]['message']['text']
            return description
            
        except Exception as e:
            logger.error(f"Ошибка генерации описания: {e}")
            return None


class YandexStorage:
    def __init__(self):
        self.access_key = Config.YC_ACCESS_KEY
        self.secret_key = Config.YC_SECRET_KEY
        self.bucket_name = Config.YC_BUCKET_NAME
        self.endpoint_url = "https://storage.yandexcloud.net"
        
        logger.info(f"🔑 Access Key (первые 10 символов): {self.access_key[:10]}...")
        logger.info(f"🔐 Secret Key (первые 5 символов): {self.secret_key[:5]}...")
        logger.info(f"📦 Bucket: {self.bucket_name}")
        
        try:
            self.s3 = boto3.client(
                's3',
                endpoint_url=self.endpoint_url,
                aws_access_key_id=self.access_key,
                aws_secret_access_key=self.secret_key,
                config=BotoConfig(
                    signature_version='s3v4',
                    region_name='ru-central1',
                    s3={'addressing_style': 'virtual'}
                ),
                region_name='ru-central1'
            )
            logger.info("✅ Storage клиент создан")
            
            # Проверяем доступ к бакету
            self.s3.head_bucket(Bucket=self.bucket_name)
            logger.info(f"✅ Доступ к бакету {self.bucket_name} подтвержден")
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            logger.error(f"❌ Ошибка доступа к бакету: {error_code}")
            if error_code == '403':
                logger.error("🚫 Нет доступа к бакету. Проверьте права сервисного аккаунта.")
            elif error_code == '404':
                logger.error("❓ Бакет не найден. Проверьте имя бакета.")
            self.s3 = None

    def upload_file(self, file_bytes: bytes, file_name: str = None, content_type: str = 'image/jpeg') -> Optional[str]:
        if self.s3 is None:
            logger.error("❌ Storage клиент не инициализирован")
            return None
            
        try:
            if file_name is None:
                file_name = f"bouquets/{uuid.uuid4()}.jpg"
            
            logger.info(f"📤 Попытка загрузки файла: {file_name}")
            logger.info(f"📦 Размер файла: {len(file_bytes)} байт")
            
            # Добавляем ContentDisposition для корректной загрузки
            self.s3.put_object(
                Bucket=self.bucket_name,
                Key=file_name,
                Body=file_bytes,
                ContentType=content_type,
                ACL='public-read'
            )
            
            url = f"https://{self.bucket_name}.storage.yandexcloud.net/{file_name}"
            logger.info(f"✅ Файл успешно загружен: {url}")
            return url
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_msg = e.response['Error']['Message']
            logger.error(f"❌ Ошибка {error_code}: {error_msg}")
            
            if error_code == 'SignatureDoesNotMatch':
                logger.error("🔑 Проблема с подписью запроса")
                logger.error("📋 Проверьте:")
                logger.error("   1. Правильно ли указаны Access Key и Secret Key")
                logger.error("   2. Совпадает ли регион (ru-central1)")
                logger.error("   3. Нет ли опечаток в ключах")
            elif error_code == 'AccessDenied':
                logger.error("🔑 Проблема с правами доступа")
            return None

    def get_file_url(self, file_name: str) -> str:
        return f"https://{self.bucket_name}.storage.yandexcloud.net/{file_name}"
