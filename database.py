import sqlite3
import os
import logging

logger = logging.getLogger(__name__)

class Database:
    def __init__(self, db_path='data/database.sqlite'):
        # Создаем папку data, если её нет
        os.makedirs('data/photos', exist_ok=True)
        print(f"✅ Папка data/photos создана или уже существует")
        
        self.conn = sqlite3.connect(db_path)
        self.cursor = self.conn.cursor()
        self._create_tables()
    
    def _create_tables(self):
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS photos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_id TEXT UNIQUE,
                file_path TEXT,
                posted INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                posted_at TIMESTAMP
            )
        ''')
        self.conn.commit()
        print("✅ Таблица photos создана или уже существует")
    
    def add_photo(self, file_id, file_path):
        try:
            self.cursor.execute(
                'INSERT OR IGNORE INTO photos (file_id, file_path) VALUES (?, ?)',
                (file_id, file_path)
            )
            self.conn.commit()
            print(f"✅ Фото {file_id} добавлено в базу")
            return True
        except Exception as e:
            print(f"❌ Ошибка добавления фото: {e}")
            return False
    
    def get_random_unposted_photo(self):
        self.cursor.execute(
            'SELECT id, file_id, file_path FROM photos WHERE posted = 0 ORDER BY RANDOM() LIMIT 1'
        )
        row = self.cursor.fetchone()
        if row:
            return {'id': row[0], 'file_id': row[1], 'file_path': row[2]}
        return None
    
    def mark_as_posted(self, photo_id):
        self.cursor.execute(
            'UPDATE photos SET posted = 1, posted_at = CURRENT_TIMESTAMP WHERE id = ?',
            (photo_id,)
        )
        self.conn.commit()
        print(f"✅ Фото {photo_id} отмечено как опубликованное")
    
    def get_stats(self):
        self.cursor.execute('SELECT COUNT(*) FROM photos')
        total = self.cursor.fetchone()[0]
        
        self.cursor.execute('SELECT COUNT(*) FROM photos WHERE posted = 1')
        posted = self.cursor.fetchone()[0]
        
        pending = total - posted
        
        return {'total': total, 'posted': posted, 'pending': pending}
    
    def get_pending_count(self):
        self.cursor.execute('SELECT COUNT(*) FROM photos WHERE posted = 0')
        return self.cursor.fetchone()[0]
    
    def reset_all_photos(self):
        """Сбрасывает статус всех фото (posted = 0) для нового круга публикаций"""
        self.cursor.execute('UPDATE photos SET posted = 0')
        self.conn.commit()
        logger.info("🔄 Все фото сброшены для нового круга публикаций")
    
    def close(self):
        self.conn.close()
