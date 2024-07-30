import aiosqlite
import os
from aiogram.types import Message


class DataBase:
    def __init__(self, db_ph: str = './cech/messages.db'):
        self.db_ph = db_ph
        self.conn = None

    async def initialize(self):
        await self._check_dir()
        self.conn = await aiosqlite.connect(self.db_ph)
        await self._create_db()

    async def __aenter__(self):
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.close_connection()

    @staticmethod
    async def _check_dir() -> None:
        if not os.path.isdir('./cech'):
            os.mkdir('./cech')

    async def _create_db(self) -> None:
        async with self.conn.execute('''
            CREATE TABLE IF NOT EXISTS sent_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message_id INTEGER,
                chat_id INTEGER,
                shop_name TEXT,
                message_type TEXT,
                order_id TEXT NULL,
                text TEXT
            )
        '''):
            await self.conn.commit()

    async def close_connection(self) -> None:
        await self.conn.close()

    async def sent_mes_save(self, message: Message, shop_name: str, order: str, mes_type: str) -> None:
        try:
            async with self.conn.execute(
                '''
                INSERT INTO sent_messages (message_id, chat_id, shop_name, message_type, order_id, text)
                VALUES (?, ?, ?, ?, ?, ?)
                ''',
                (message.message_id, message.chat.id, shop_name, mes_type, order, message.text)
            ):
                await self.conn.commit()
        except aiosqlite.Error as e:
            print(f"Error occurred: {e}")
            await self.conn.rollback()

    async def delete_message(self, **kwargs) -> None:
        keys = [key for key in kwargs.keys()]
        values = [value for value in kwargs.values()]
        try:
            async with self.conn.execute(
                f'''
                DELETE FROM sent_messages
                WHERE {" = ? AND ".join(keys)} = ?
                ''',
                values
            ):
                await self.conn.commit()
        except aiosqlite.Error as e:
            print(f"Error occurred: {e}")
            await self.conn.rollback()

    async def check_values_in_columns(self, **kwargs) -> bool:
        keys = [key for key in kwargs.keys()]
        values = [value for value in kwargs.values()]
        try:
            async with self.conn.execute(
                f'''
                SELECT 1 FROM sent_messages
                WHERE {" = ? AND ".join(keys)} = ?
                LIMIT 1
                ''',
                values
            ) as cursor:
                row = await cursor.fetchone()
                return row is not None
        except aiosqlite.Error as e:
            print(f"Error occurred: {e}")
            return False

    async def get_item(self, desired_col: str, **kwargs) -> str | int | None | bool:
        keys = [key for key in kwargs.keys()]
        values = [value for value in kwargs.values()]
        try:
            async with self.conn.execute(
                f'''
                SELECT {desired_col} FROM sent_messages
                WHERE {" = ? AND ".join(keys)} = ?
                LIMIT 1
                ''',
                values
            ) as cursor:
                res = await cursor.fetchone()
                if res:
                    return res[0]
                else:
                    return None
        except aiosqlite.Error as e:
            print(f"Error occurred: {e}")
            return False

    async def fetch_all_data(self) -> list:
        try:
            async with self.conn.execute('SELECT * FROM sent_messages') as cursor:
                rows = await cursor.fetchall()
                return rows
        except aiosqlite.Error as e:
            print(f"Error occurred: {e}")
            return []
