import asyncio
from typing import Optional

from pymongo import AsyncMongoClient
from config import Config
from app.utils.logger import logger


class MongoManager:
    def __init__(self):
        self.client: Optional[AsyncMongoClient] = None
        self.db = None
        self._connect_lock = asyncio.Lock()

    async def connect(self):
        if self.client is not None and self.db is not None:
            return self.db

        async with self._connect_lock:
            if self.client is not None and self.db is not None:
                return self.db

            client = AsyncMongoClient(
                Config.MONGO_URI,
                maxPoolSize=100,
                minPoolSize=5,
                serverSelectionTimeoutMS=5000,
                connectTimeoutMS=5000,
                retryWrites=True,
                appname="MMW-ProBot",
            )
            try:
                await client.admin.command("ping")
                db = client[Config.DATABASE_NAME]
                self.client = client
                self.db = db
                await self._init_indexes()
                logger.info(f"MongoDB connected successfully: {Config.DATABASE_NAME}")
                return db
            except Exception:
                await client.close()
                raise

    async def _init_indexes(self):
        await self.db.users.create_index("user_id", unique=True, name="user_id_1")
        await self.db.chats.create_index("chat_id", unique=True, name="chat_id_1")
        await self.db.files.create_index("file_id", unique=True, name="file_id_1")
        await self.db.files.create_index([("file_name", 1), ("created_at", -1)], name="file_name_created_at")
        await self.db.auto_delete.create_index("delete_at", name="delete_at_1")
        await self.db.auto_delete.create_index(
            [("chat_id", 1), ("message_id", 1)],
            unique=True,
            name="chat_message_unique",
        )

    async def close(self):
        if self.client:
            await self.client.close()
            self.client = None
            self.db = None
            logger.info("MongoDB connection closed.")


mongo = MongoManager()
