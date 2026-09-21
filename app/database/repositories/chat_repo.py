import time
from typing import Optional, Dict, Any, List
from app.database.mongodb import mongo
from app.database.models import new_chat_dict
from app.utils.cache import cache

class ChatRepository:
    @property
    def col(self):
        return mongo.db.chats

    @property
    def auto_del_col(self):
        return mongo.db.auto_delete

    async def get_or_create_chat(self, chat_id: int, title: str, chat_type: str) -> Dict[str, Any]:
        cache_key = f"chat_{chat_id}"
        cached = await cache.get(cache_key)
        if cached:
            return cached
        chat = await self.col.find_one({"chat_id": chat_id})
        if not chat:
            chat = new_chat_dict(chat_id, title, chat_type)
            await self.col.insert_one(chat)
        await cache.set(cache_key, chat, ttl=600)
        return chat

    async def update_chat(self, chat_id: int, data: Dict[str, Any]):
        data["updated_at"] = time.time()
        await self.col.update_one({"chat_id": chat_id}, {"$set": data}, upsert=True)
        await cache.delete(f"chat_{chat_id}")

    async def get_total_chats(self) -> int:
        cached = await cache.get("stats_total_chats")
        if cached is not None:
            return cached
        count = await self.col.count_documents({})
        await cache.set("stats_total_chats", count, ttl=300)
        return count

    async def get_all_chats(self) -> List[Dict[str, Any]]:
        cursor = self.col.find({}, {"chat_id": 1, "_id": 0})
        return await cursor.to_list(length=100000)

    async def add_auto_delete_task(self, chat_id: int, message_id: int, delete_at: float):
        await self.auto_del_col.insert_one({
            "chat_id": chat_id,
            "message_id": message_id,
            "delete_at": delete_at
        })

    async def get_expired_auto_delete(self, current_time: float) -> List[Dict[str, Any]]:
        cursor = self.auto_del_col.find({"delete_at": {"$lte": current_time}})
        return await cursor.to_list(length=100)

    async def remove_auto_delete_task(self, chat_id: int, message_id: int):
        await self.auto_del_col.delete_one({"chat_id": chat_id, "message_id": message_id})

chat_repo = ChatRepository()
