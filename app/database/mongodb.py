from motor.motor_asyncio import AsyncIOMotorClient
from config import Config
from app.utils.logger import logger

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
                self.db = self.client[Config.DATABASE_NAME]
                await self._init_indexes()
                logger.info(f"MongoDB Connected successfully: {Config.DATABASE_NAME}")
            except Exception as e:
                logger.error(f"MongoDB Connection Failed: {e}")
                raise

    async def _init_indexes(self):
        try:
            await self.db.users.create_index("user_id", unique=True)
            await self.db.chats.create_index("chat_id", unique=True)
            await self.db.files.create_index("file_id", unique=True)
            await self.db.auto_delete.create_index("delete_at")
        except Exception as e:
            logger.warning(f"Error creating indexes: {e}")

    async def close(self):
        if self.client:
            self.client.close()
            logger.info("MongoDB Connection closed.")

mongo = MongoManager()
