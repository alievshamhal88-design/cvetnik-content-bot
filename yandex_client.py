import requests
import logging
import os
import random

logger = logging.getLogger(__name__)

class YandexGPTClient:
    def __init__(self):
        self.folder_id = os.getenv("YANDEX_FOLDER_ID")
        self.api_key = os.getenv("YANDEX_API_KEY")
        self.api_url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
        
        if not self.folder_id or not self.api_key:
            raise ValueError("❌ Отсутствуют YANDEX_FOLDER_ID или YANDEX_API_KEY")
        
        logger.info("✅ YandexGPT клиент инициализирован для постера")

    def generate_post_text(self) -> str:
        """
        Генерирует текст для поста в канал
        Возвращает строку с названием и описанием букета
        """
        prompts = [
            "Придумай красивый пост для цветочного магазина. "
            "Напиши название букета (2-4 слова) и короткое описание (1-2 предложения). "
            "Формат: Название: ...\nОписание: ...",
            
            "Придумай романтический пост о букете цветов. "
            "Название должно быть поэтичным, описание — тёплым. "
            "Формат: Название: ...\nОписание: ...",
            
            "Придумай весенний пост о букете. Нежные, вдохновляющие слова. "
            "Формат: Название: ...\nОписание: ..."
        ]
        
        prompt = random.choice(prompts)
        
        headers = {
            "Authorization": f"Api-Key {self.api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "modelUri": f"gpt://{self.folder_id}/yandexgpt-lite",
            "completionOptions": {
                "stream": False,
                "temperature": 0.8,
                "maxTokens": "200"
            },
            "messages": [
                {
                    "role": "user",
                    "text": prompt
                }
            ]
        }
        
        try:
            response = requests.post(self.api_url, headers=headers, json=data, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                text = result['result']['alternatives'][0]['message']['text']
                
                # Парсим название и описание
                lines = text.split('\n')
                name = "Волшебный букет"
                description = "Нежный букет для особенного случая."
                
                for line in lines:
                    if 'Название:' in line:
                        name = line.replace('Название:', '').strip()
                    elif 'Описание:' in line:
                        description = line.replace('Описание:', '').strip()
                
                # Формируем полный текст поста
                return f"🌸 **{name}** 🌸\n\n{description}"
            else:
                logger.error(f"❌ Ошибка YandexGPT: {response.status_code}")
                return self._get_fallback_text()
                
        except Exception as e:
            logger.error(f"❌ Исключение: {e}")
            return self._get_fallback_text()
    
    def _get_fallback_text(self) -> str:
        """Запасной текст на случай ошибки"""
        fallback = [
            "🌸 **Нежность утра** 🌸\n\nНежный букет для особенного случая.",
            "🌸 **Цветочная симфония** 🌸\n\nЯркий букет, который подарит радость.",
            "🌸 **Весеннее настроение** 🌸\n\nСвежий букет из лучших цветов."
        ]
        return random.choice(fallback)
