    def add_bouquet_url(self, file_id: str, photo_url: str, file_name: str) -> bool:
        """Добавляет букет в каталог с URL из облака"""
        try:
            self.cursor.execute(
                'INSERT OR IGNORE INTO bouquets (photo_file_id, photo_url, file_name, name) VALUES (?, ?, ?, ?)',
                (file_id, photo_url, file_name, "Букет")
            )
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Ошибка добавления букета: {e}")
            return False

    def get_random_bouquet(self):
        """Возвращает случайный букет с URL из облака"""
        self.cursor.execute('SELECT id, name, description, photo_url FROM bouquets ORDER BY RANDOM() LIMIT 1')
        row = self.cursor.fetchone()
        if row:
            return {
                'id': row[0],
                'name': row[1],
                'description': row[2],
                'photo_url': row[3]  # теперь это URL, а не file_id
            }
        return None
