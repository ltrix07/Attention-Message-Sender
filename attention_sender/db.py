import sqlite3
import os


class DataBase:
    def __init__(self, db_ph):
        self.db_ph = db_ph
        self.conn = sqlite3.connect(self.db_ph)
        self.cursor = self.conn.cursor()
        self._create_db()

    def __del__(self):
        self.close_connection()

    def _create_db(self):
        if not os.path.isdir('./cech'):
            os.mkdir('./cech')

        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS sent_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message_id INTEGER,
            chat_id INTEGER,
            shop_name TEXT,
            message_type TEXT,
            order_id TEXT NULL,
            text TEXT
        )
        ''')
        self.conn.commit()

    def close_connection(self):
        self.conn.close()

    def sent_mes_save(self, message, shop_name, order, mes_type):
        try:
            self.cursor.execute(
                '''
                INSERT INTO sent_messages (message_id, chat_id, shop_name, message_type, order_id, text)
                VALUES (?, ?, ?, ?, ?, ?)
                ''',
                (message.message_id, message.chat.id, shop_name, mes_type, order, message.text)
            )
            self.conn.commit()
        except sqlite3.Error as e:
            print(f"Error occurred: {e}")
            self.conn.rollback()

    def delete_message(self, **kwargs):
        keys = [key for key in kwargs.keys()]
        values = [value for value in kwargs.values()]
        try:
            self.cursor.execute(
                f'''
                DELETE FROM sent_messages
                WHERE {" = ? AND ".join(keys)} = ?
                ''',
                values
            )
            self.conn.commit()
        except sqlite3.Error as e:
            print(f"Error occurred: {e}")
            self.conn.rollback()

    def check_values_in_columns(self, **kwargs):
        keys = [key for key in kwargs.keys()]
        values = [value for value in kwargs.values()]
        try:
            self.cursor.execute(
                f'''
                SELECT 1 FROM sent_messages
                WHERE {" = ? AND ".join(keys)} = ?
                LIMIT 1
                ''',
                values
            )
            row = self.cursor.fetchone()
            return row is not None
        except sqlite3.Error as e:
            print(f"Error occurred: {e}")
            return False

    def get_item(self, desired_col, **kwargs):
        keys = [key for key in kwargs.keys()]
        values = [value for value in kwargs.values()]
        try:
            self.cursor.execute(
                f'''
                SELECT {desired_col} FROM sent_messages
                WHERE {" = ? AND ".join(keys)} = ?
                LIMIT 1
                ''',
                values
            )
            res = self.cursor.fetchone()
            if res:
                return res[0]
            else:
                return None
        except sqlite3.Error as e:
            print(f"Error occurred: {e}")
            return False

    def fetch_all_data(self):
        try:
            self.cursor.execute('SELECT * FROM sent_messages')
            rows = self.cursor.fetchall()
            return rows
        except sqlite3.Error as e:
            print(f"Error occurred: {e}")
            return []
