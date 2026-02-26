import requests
import logging
import boto3
from botocore.client import Config
from botocore.exceptions import ClientError
from typing import Optional
import uuid
import os
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

class YandexGPT:
    def __init__(self):
        self.folder_id = os.getenv("YANDEX_FOLDER_ID") or os.getenv("YANDEX_FOLDER")
        self.api_key = os.getenv("YANDEX_API_KEY")
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
        # Явно берем переменные из окружения
        self.access_key = os.getenv("YC_ACCESS_KEY", "").strip()
        self.secret_key = os.getenv("YC_SECRET_KEY", "").strip()
        self.bucket_name = os.getenv("YC_BUCKET_NAME", "cvetnik-photos").strip()
        
        # Яндекс.Облако endpoint
        self.endpoint_url = "https://storage.yandexcloud.net"
        
        logger.info("=" * 50)
        logger.info("ИНИЦИАЛИЗАЦИЯ STORAGE КЛИЕНТА")
        logger.info(f"🔑 Access Key (первые 10 символов): {self.access_key[:10] if self.access_key else 'НЕТ'}")
        logger.info(f"🔐 Secret Key (первые 5 символов): {self.secret_key[:5] if self.secret_key else 'НЕТ'}")
        logger.info(f"📦 Bucket: {self.bucket_name}")
        logger.info(f"🌍 Endpoint: {self.endpoint_url}")
        logger.info("=" * 50)
        
        if not self.access_key or not self.secret_key:
            logger.error("❌ НЕТ КЛЮЧЕЙ ДОСТУПА!")
            self.s3 = None
            return
            
        try:
            # ВАЖНО: правильная конфигурация для Яндекс.Облака
            self.s3 = boto3.client(
                's3',
                endpoint_url=self.endpoint_url,
                aws_access_key_id=self.access_key,
                aws_secret_access_key=self.secret_key,
                config=Config(
                    signature_version='s3v4',
                    region_name='ru-central1',
                    s3={'addressing_style': 'path'}  # path addressing для Яндекс.Облака
                ),
                region_name='ru-central1',
                verify=True  # проверка SSL
            )
            logger.info("✅ S3 клиент создан")
            
            # Пробуем получить список бакетов (проверка доступа)
            response = self.s3.list_buckets()
            logger.info(f"✅ Доступ подтвержден. Всего бакетов: {len(response.get('Buckets', []))}")
            
            # Проверяем конкретный бакет
            try:
                self.s3.head_bucket(Bucket=self.bucket_name)
                logger.info(f"✅ Бакет {self.bucket_name} найден и доступен")
                
                # Пробуем получить список объектов
                objects = self.s3.list_objects_v2(Bucket=self.bucket_name, MaxKeys=5)
                obj_count = objects.get('KeyCount', 0)
                logger.info(f"✅ В бакете {obj_count} объектов")
                
            except ClientError as e:
                error_code = e.response['Error']['Code']
                if error_code == '404':
                    logger.error(f"❌ Бакет {self.bucket_name} НЕ НАЙДЕН!")
                elif error_code == '403':
                    logger.error(f"❌ НЕТ ДОСТУПА к бакету {self.bucket_name}!")
                else:
                    logger.error(f"❌ Ошибка доступа к бакету: {error_code}")
                
        except Exception as e:
            logger.error(f"❌ КРИТИЧЕСКАЯ ОШИБКА: {e}")
            self.s3 = None

    def upload_file(self, file_bytes: bytes, file_name: str = None, content_type: str = 'image/jpeg') -> Optional[str]:
        if self.s3 is None:
            logger.error("❌ S3 клиент не инициализирован")
            return None
            
        try:
            if file_name is None:
                file_name = f"bouquets/{uuid.uuid4()}.jpg"
            
            # Убедимся, что file_name не начинается с /
            if file_name.startswith('/'):
                file_name = file_name[1:]
            
            logger.info(f"📤 Загружаю файл: {file_name}")
            logger.info(f"📦 Размер: {len(file_bytes)} байт")
            
            # Пробуем загрузить
            self.s3.put_object(
                Bucket=self.bucket_name,
                Key=file_name,
                Body=file_bytes,
                ContentType=content_type,
                ACL='public-read'
            )
            
            # Формируем URL
            url = f"https://{self.bucket_name}.storage.yandexcloud.net/{file_name}"
            logger.info(f"✅ ФАЙЛ УСПЕШНО ЗАГРУЖЕН!")
            logger.info(f"🔗 URL: {url}")
            
            # Проверяем, что файл действительно загрузился
            try:
                self.s3.head_object(Bucket=self.bucket_name, Key=file_name)
                logger.info(f"✅ Файл подтвержден в бакете")
            except:
                logger.warning(f"⚠️ Не удалось подтвердить файл")
            
            return url
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_msg = e.response['Error']['Message']
            logger.error(f"❌ ОШИБКА ЗАГРУЗКИ {error_code}: {error_msg}")
            
            if error_code == 'AccessDenied':
                logger.error("🔑 AccessDenied - ВОЗМОЖНЫЕ ПРИЧИНЫ:")
                logger.error("   1. Ключи доступа НЕ соответствуют сервисному аккаунту")
                logger.error("   2. У сервисного аккаунта нет прав на запись в ЭТОТ бакет")
                logger.error("   3. Бакет находится в другом каталоге/облаке")
                logger.error("   4. Ключи были скопированы с пробелами или лишними символами")
            return None
        except Exception as e:
            logger.error(f"❌ НЕИЗВЕСТНАЯ ОШИБКА: {e}")
            return None
