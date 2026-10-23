from motor.motor_asyncio import AsyncIOMotorClient
from config import Config
from logger import logger

class MongoManager:
    def __init__(self):
        self.client: AsyncIOMotorClient = None
        self.db = None

    async def connect(self):
        if not self.client:
            try:
                self.client = AsyncIOMotorClient(
                    Config.MONGO_URI,
                    maxPoolSize=50,
                    minPoolSize=10,
                    serverSelectionTimeoutMS=5000
                )
                await self.client.admin.command("ping")
                self.db = self.client[Config.DATABASE_NAME]
                await self._init_indexes()
                logger.info("MongoDB connected and verified (%s).", Config.DATABASE_NAME)
            except Exception as exc:
                if self.client is not None:
                    self.client.close()
                self.client = None
                self.db = None
                logger.error("MongoDB connection failed (%s).", type(exc).__name__)
                raise

    async def _init_indexes(self):
        if self.db is None:
            return
        indexes = (
            (self.db.users, "user_id", {"unique": True}),
            (self.db.users, [("created_at", -1)], {}),
            (self.db.users, "is_banned", {}),
            (self.db.chats, "chat_id", {"unique": True}),
            (self.db.chats, [("created_at", -1)], {}),
            (self.db.files, "file_id", {"unique": True}),
            (self.db.files, [("created_at", -1)], {}),
            (self.db.files, "file_name", {}),
            (self.db.auto_delete, "delete_at", {}),
        )
        for collection, keys, options in indexes:
            try:
                await collection.create_index(keys, **options)
            except Exception as exc:
                logger.warning(
                    "MongoDB index setup incomplete for %s (%s).",
                    collection.name,
                    type(exc).__name__,
                )

    @property
    def is_connected(self) -> bool:
        return self.client is not None and self.db is not None

    async def close(self):
        if self.client:
            self.client.close()
            self.client = None
            self.db = None
            logger.info("MongoDB Connection closed.")

mongo = MongoManager()
