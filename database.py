import sqlite3
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class Database:
    def __init__(self, db_name="content_bot.db"):
        self.db_name = db_name
        self.conn = None
        self.cursor = None
        self.connect()
        self.create_tables()
        
    def connect(self):
        try:
            self.conn = sqlite3.connect(self.db_name, check_same_thread=False)
            self.cursor = self.conn.cursor()
            logger.info("✅ Подключение к БД установлено")
        except Exception as e:
            logger.error(f"❌ Ошибка подключения к БД: {e}")
    
    def create_tables(self):
        try:
            self.cursor.execute('''
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
            
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS generations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    bouquet_id INTEGER,
                    prompt TEXT,
                    description TEXT,
                    model TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (bouquet_id) REFERENCES bouquets (id)
                )
            ''')
            
            self.conn.commit()
            logger.info("✅ Таблицы созданы")
        except Exception as e:
            logger.error(f"❌ Ошибка создания таблиц: {e}")
    
    def add_bouquet(self, file_id, photo_url, file_name):
        try:
            self.cursor.execute(
                'INSERT OR IGNORE INTO bouquets (file_id, photo_url, file_name) VALUES (?, ?, ?)',
                (file_id, photo_url, file_name)
            )
            self.conn.commit()
            return self.cursor.lastrowid
        except Exception as e:
            logger.error(f"Ошибка добавления букета: {e}")
            return None
    
    def get_bouquet(self, bouquet_id):
        try:
            self.cursor.execute('SELECT * FROM bouquets WHERE id = ?', (bouquet_id,))
            row = self.cursor.fetchone()
            if row:
                return {
                    'id': row[0],
                    'file_id': row[1],
                    'photo_url': row[2],
                    'file_name': row[3],
                    'name': row[4],
                    'description': row[5],
                    'created_at': row[6]
                }
            return None
        except Exception as e:
            logger.error(f"Ошибка получения букета: {e}")
            return None
    
    def get_all_bouquets(self):
        try:
            self.cursor.execute('SELECT id, photo_url, name, description FROM bouquets ORDER BY created_at DESC')
            rows = self.cursor.fetchall()
            bouquets = []
            for row in rows:
                bouquets.append({
                    'id': row[0],
                    'photo_url': row[1],
                    'name': row[2],
                    'description': row[3]
                })
            return bouquets
        except Exception as e:
            logger.error(f"Ошибка получения букетов: {e}")
            return []
    
    def update_description(self, bouquet_id, description):
        try:
            self.cursor.execute(
                'UPDATE bouquets SET description = ? WHERE id = ?',
                (description, bouquet_id)
            )
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Ошибка обновления описания: {e}")
            return False
    
    def add_generation(self, bouquet_id, prompt, description, model="yandexgpt"):
        try:
            self.cursor.execute(
                'INSERT INTO generations (bouquet_id, prompt, description, model) VALUES (?, ?, ?, ?)',
                (bouquet_id, prompt, description, model)
            )
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Ошибка сохранения генерации: {e}")
            return False
    
    def close(self):
        if self.conn:
            self.conn.close()
            logger.info("✅ Соединение с БД закрыто")
