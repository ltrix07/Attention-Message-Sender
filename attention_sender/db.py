import aiosqlite
from aiogram.types import Message
from typing import Optional, Union, List

from attention_sender.config import settings


class DataBase:
    """
    Async wrapper around SQLite for storing and managing sent Telegram messages.

    Used to:
      - save info about sent messages,
      - check if a message with given (shop, type, order_id) already exists,
      - delete or fetch messages by filters.
    """

    def __init__(self, db_ph: str = None) -> None:
        # Default path from centralized config
        self.db_ph = db_ph or settings.paths.sqlite_db.as_posix()
        self.conn: Optional[aiosqlite.Connection] = None

    async def initialize(self) -> None:
        """Initialize connection and create DB schema if needed."""
        await self._ensure_dir()
        self.conn = await aiosqlite.connect(self.db_ph)
        await self._create_db()

    async def _ensure_dir(self) -> None:
        """Ensure that directory for DB file exists."""
        db_path = settings.paths.sqlite_db
        db_path.parent.mkdir(parents=True, exist_ok=True)

    async def _create_db(self) -> None:
        """Create table if not exists."""
        async with self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sent_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message_id INTEGER NOT NULL,
                chat_id INTEGER NOT NULL,
                shop_name TEXT NOT NULL,
                message_type TEXT NOT NULL,
                order_id TEXT NOT NULL,
                text TEXT,
                date TEXT
            )
            """
        ):
            await self.conn.commit()

    async def __aenter__(self) -> "DataBase":
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        if self.conn:
            await self.conn.close()

    async def sent_mes_save(
        self,
        message: Message,
        shop_name: str,
        order: str,
        mes_type: str,
    ) -> None:
        """Save info about a sent message in DB."""
        if not self.conn:
            raise RuntimeError("Database connection is not initialized")

        try:
            async with self.conn.execute(
                """
                INSERT INTO sent_messages (message_id, chat_id, shop_name, message_type, order_id, text, date)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    message.message_id,
                    message.chat.id,
                    shop_name,
                    mes_type,
                    order,
                    message.text,
                    str(message.date),
                ),
            ):
                await self.conn.commit()
        except aiosqlite.Error as e:
            print(f"DB error occurred: {e}")
            await self.conn.rollback()

    async def delete_message(self, **filters) -> None:
        """
        Delete rows from DB by arbitrary filters, e.g.:

          await db.delete_message(shop_name="shop1", message_type="bad_price")
        """
        if not self.conn:
            raise RuntimeError("Database connection is not initialized")

        if not filters:
            return

        keys = list(filters.keys())
        values = list(filters.values())
        where_clause = " AND ".join(f"{k} = ?" for k in keys)

        query = f"DELETE FROM sent_messages WHERE {where_clause}"
        async with self.conn.execute(query, values):
            await self.conn.commit()

    async def get_message(self, **filters) -> Optional[aiosqlite.Row]:
        """Fetch single message row by filters, or None if not found."""
        if not self.conn:
            raise RuntimeError("Database connection is not initialized")

        if not filters:
            return None

        keys = list(filters.keys())
        values = list(filters.values())
        where_clause = " AND ".join(f"{k} = ?" for k in keys)

        query = f"SELECT * FROM sent_messages WHERE {where_clause} LIMIT 1"
        self.conn.row_factory = aiosqlite.Row
        async with self.conn.execute(query, values) as cursor:
            row = await cursor.fetchone()
        return row

    async def check_values_in_columns(
        self,
        shop_name: str,
        message_type: str,
        order_id: str,
    ) -> bool:
        """
        Check if message with given (shop_name, message_type, order_id) already exists.
        Returns True if exists, False otherwise.
        """
        row = await self.get_message(
            shop_name=shop_name, message_type=message_type, order_id=order_id
        )
        return row is not None

    async def get_messages_by_filters(self, **filters) -> List[aiosqlite.Row]:
        """Fetch all rows that match given filters."""
        if not self.conn:
            raise RuntimeError("Database connection is not initialized")

        if not filters:
            return []

        keys = list(filters.keys())
        values = list(filters.values())
        where_clause = " AND ".join(f"{k} = ?" for k in keys)

        query = f"SELECT * FROM sent_messages WHERE {where_clause}"
        self.conn.row_factory = aiosqlite.Row
        async with self.conn.execute(query, values) as cursor:
            rows = await cursor.fetchall()
        return rows
