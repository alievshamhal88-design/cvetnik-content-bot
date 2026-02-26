import requests
import logging
import os
import uuid
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

class YandexGPT:
    """Класс для YandexGPT - оставляем как есть"""
    
    def __init__(self):
        self.folder_id = os.getenv("YANDEX_FOLDER") or os.getenv("YANDEX_FOLDER_ID")
        self.api_key = os.getenv("YANDEX_API_KEY")
        self.url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
        
    def generate_description(self, prompt: str) -> str:
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
            return result['result']['alternatives'][0]['message']['text']
            
        except Exception as e:
            logger.error(f"Ошибка GPT: {e}")
            return ""


class YandexStorage:
    """Класс для Яндекс Облака - УПРОЩЕННЫЙ ДО ЖИЗНИ"""
    
    def __init__(self):
        self.access_key = os.getenv("YC_ACCESS_KEY", "").strip()
        self.secret_key = os.getenv("YC_SECRET_KEY", "").strip()
        self.bucket_name = os.getenv("YC_BUCKET_NAME", "").strip()
        
        logger.info("=" * 50)
        logger.info("STORAGE INIT")
        logger.info(f"Access Key: {self.access_key[:10]}...")
        logger.info(f"Bucket: {self.bucket_name}")
        logger.info("=" * 50)

    def upload_file(self, file_bytes, file_name=None):
        """Загружает файл - МАКСИМАЛЬНО ПРОСТО"""
        try:
            # Генерируем имя файла
            if file_name is None:
                file_name = f"bouquets/{uuid.uuid4().hex}.jpg"
            
            # Убираем лишнее
            if file_name.startswith('/'):
                file_name = file_name[1:]
            
            # Формируем URL
            url = f"https://{self.bucket_name}.storage.yandexcloud.net/{file_name}"
            
            logger.info(f"📤 URL: {url}")
            logger.info(f"📦 Size: {len(file_bytes)} bytes")
            
            # ПРОСТОЙ PUT запрос - без заморочек
            response = requests.put(
                url,
                data=file_bytes,
                headers={
                    "Content-Type": "image/jpeg",
                    "x-amz-acl": "public-read"
                },
                auth=(self.access_key, self.secret_key)
            )
            
            logger.info(f"📊 Status: {response.status_code}")
            
            if response.status_code in [200, 201, 204]:
                logger.info(f"✅ SUCCESS! File uploaded")
                return url
            else:
                logger.error(f"❌ Failed: {response.status_code}")
                logger.error(f"Response: {response.text[:200]}")
                return None
                
        except Exception as e:
            logger.error(f"❌ ERROR: {e}")
            return None
