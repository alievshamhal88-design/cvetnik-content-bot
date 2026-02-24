import os

# ID администраторов
ADMIN_IDS = [
    7651760894,  # @cvetnik1_sib
    7750251679,  # @Alan_Aliev
]

# Время публикации по Новосибирску (UTC+7)
POST_TIMES = [
    "09:00",  # Утро
    "18:00",  # Вечер
]

# Настройки Yandex Cloud
YANDEX_FOLDER_ID = os.getenv("YANDEX_FOLDER_ID")
YANDEX_API_KEY = os.getenv("YANDEX_API_KEY")
