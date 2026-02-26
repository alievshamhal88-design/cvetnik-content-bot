import requests
import logging
import os
import uuid
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

class YandexStorage:
    def __init__(self):
        self.access_key = os.getenv("YC_ACCESS_KEY")
        self.secret_key = os.getenv("YC_SECRET_KEY")
        self.bucket_name = os.getenv("YC_BUCKET_NAME")
        
    def upload_file(self, file_bytes, file_name=None):
        try:
            if file_name is None:
                file_name = f"bouquets/{uuid.uuid4()}.jpg"
            
            # Простой HTTP запрос к Яндекс.Облаку
            url = f"https://storage.yandexcloud.net/{self.bucket_name}/{file_name}"
            
            headers = {
                "Content-Type": "image/jpeg",
                "x-amz-acl": "public-read"
            }
            
            response = requests.put(
                url,
                data=file_bytes,
                headers=headers,
                auth=(self.access_key, self.secret_key)
            )
            
            if response.status_code == 200:
                photo_url = f"https://{self.bucket_name}.storage.yandexcloud.net/{file_name}"
                logger.info(f"✅ Файл загружен: {photo_url}")
                return photo_url
            else:
                logger.error(f"❌ Ошибка {response.status_code}: {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Ошибка: {e}")
            return None
