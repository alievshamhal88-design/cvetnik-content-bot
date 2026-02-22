import sqlite3
import os
from datetime import datetime

class Database:
    def __init__(self, db_path='data/database.sqlite'):
        # Создаем папку data, если её нет
        os.makedirs('data/photos', exist_ok=True)
        
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
    
    def add_photo(self, file_id, file_path):
        self.cursor.execute(
            'INSERT OR IGNORE INTO photos (file_id, file_path) VALUES (?, ?)',
            (file_id, file_path)
        )
        self.conn.commit()
    
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
    
    def close(self):
        self.conn.close()
