import time
from typing import Dict, Any, List

from pymongo import ReturnDocument
from app.database.mongodb import mongo
from app.database.models import new_chat_dict
from app.utils.cache import cache


class ChatRepository:
    @property
    def col(self):
        if mongo.db is None:
            raise RuntimeError("MongoDB is not connected")
        return mongo.db.chats

    @property
    def auto_del_col(self):
        if mongo.db is None:
            raise RuntimeError("MongoDB is not connected")
        return mongo.db.auto_delete

    async def get_or_create_chat(self, chat_id: int, title: str, chat_type: str) -> Dict[str, Any]:
        cache_key = f"chat_{chat_id}"
        cached = await cache.get(cache_key)
        if cached:
            return cached

        defaults = new_chat_dict(chat_id, title, chat_type)
        # Avoid MongoDB conflicting update paths between $set and $setOnInsert.
        for key in ("title", "chat_type", "updated_at"):
            defaults.pop(key, None)
        chat = await self.col.find_one_and_update(
            {"chat_id": chat_id},
            {
                "$set": {
                    "title": title or "Chat",
                    "chat_type": chat_type,
                    "updated_at": time.time(),
                },
                "$setOnInsert": defaults,
            },
            upsert=True,
            return_document=ReturnDocument.AFTER,
        )
        chat.pop("_id", None)
        await cache.set(cache_key, chat, ttl=600)
        await cache.delete("stats_total_chats")
        return chat

    async def update_chat(self, chat_id: int, data: Dict[str, Any]):
        updates = dict(data)
        updates["updated_at"] = time.time()
        defaults = new_chat_dict(chat_id, str(chat_id), "unknown")
        for key in list(updates):
            defaults.pop(key, None)
        defaults.pop("updated_at", None)
        await self.col.update_one(
            {"chat_id": chat_id},
            {"$set": updates, "$setOnInsert": defaults},
            upsert=True,
        )
        await cache.delete(f"chat_{chat_id}")

    async def get_total_chats(self) -> int:
        cached = await cache.get("stats_total_chats")
        if cached is not None:
            return int(cached)
        count = await self.col.count_documents({})
        await cache.set("stats_total_chats", count, ttl=300)
        return count

    async def get_all_chats(self) -> List[Dict[str, Any]]:
        cursor = self.col.find({}, {"chat_id": 1, "_id": 0})
        return await cursor.to_list(length=1_000_000)

    async def add_auto_delete_task(self, chat_id: int, message_id: int, delete_at: float):
        await self.auto_del_col.update_one(
            {"chat_id": chat_id, "message_id": message_id},
            {"$set": {"delete_at": delete_at}},
            upsert=True,
        )

    async def get_expired_auto_delete(self, current_time: float, limit: int = 100) -> List[Dict[str, Any]]:
        cursor = self.auto_del_col.find(
            {"delete_at": {"$lte": current_time}},
            {"_id": 0},
        ).sort("delete_at", 1).limit(limit)
        return await cursor.to_list(length=limit)

    async def remove_auto_delete_task(self, chat_id: int, message_id: int):
        await self.auto_del_col.delete_one({"chat_id": chat_id, "message_id": message_id})

    async def remove_auto_delete_tasks(self, pairs):
        if not pairs:
            return
        from pymongo import DeleteOne
        operations = []
        for item in pairs:
            if isinstance(item, dict):
                chat_id = item.get("chat_id")
                message_id = item.get("message_id")
            else:
                chat_id, message_id = item
            if chat_id is not None and message_id is not None:
                operations.append(DeleteOne({"chat_id": chat_id, "message_id": message_id}))
        if operations:
            await self.auto_del_col.bulk_write(operations, ordered=False)


chat_repo = ChatRepository()
