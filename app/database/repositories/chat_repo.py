import time
from typing import Dict, Any, List, Optional
from app.database.mongodb import mongo
from app.database.models import new_chat_dict
from app.utils.cache import cache

class ChatRepository:
    """
    Production-ready MongoDB repository for chats and channels with in-memory caching.
    Full CRUD implementation: create_chat, get_chat, update_chat, delete_chat.
    """
    @property
    def col(self):
        return mongo.db.chats

    @property
    def auto_del_col(self):
        return mongo.db.auto_delete

    # --- CREATE ---
    async def create_chat(self, chat_id: int, title: str, chat_type: str) -> Dict[str, Any]:
        """CREATE: Inserts a new chat document."""
        chat_data = new_chat_dict(chat_id, title, chat_type)
        await self.col.update_one({"chat_id": chat_id}, {"$setOnInsert": chat_data}, upsert=True)
        await cache.set(f"chat_{chat_id}", chat_data, ttl=600)
        await cache.delete("stats_total_chats")
        return chat_data

    async def get_or_create_chat(self, chat_id: int, title: str, chat_type: str) -> Dict[str, Any]:
        """Fetches chat from cache/DB or creates a new entry if not existing."""
        cache_key = f"chat_{chat_id}"
        cached = await cache.get(cache_key)
        if cached:
            return cached
        chat = await self.col.find_one({"chat_id": chat_id})
        if not chat:
            chat = new_chat_dict(chat_id, title, chat_type)
            await self.col.insert_one(chat)
            await cache.delete("stats_total_chats")
        await cache.set(cache_key, chat, ttl=600)
        return chat

    # --- READ ---
    async def get_chat(self, chat_id: int) -> Optional[Dict[str, Any]]:
        """READ: Retrieves chat document by chat_id."""
        cache_key = f"chat_{chat_id}"
        cached = await cache.get(cache_key)
        if cached:
            return cached
        chat = await self.col.find_one({"chat_id": chat_id})
        if chat:
            await cache.set(cache_key, chat, ttl=600)
        return chat

    async def get_all_chats(self) -> List[Dict[str, Any]]:
        """READ: Retrieves all registered chats (chat_id projection)."""
        cursor = self.col.find({}, {"chat_id": 1, "_id": 0})
        return await cursor.to_list(length=100000)

    async def get_total_chats(self) -> int:
        """READ: Retrieves total chats count with caching."""
        cached = await cache.get("stats_total_chats")
        if cached is not None:
            return cached
        count = await self.col.count_documents({})
        await cache.set("stats_total_chats", count, ttl=300)
        return count

    # --- UPDATE ---
    async def update_chat(self, chat_id: int, data: Dict[str, Any]) -> bool:
        """UPDATE: Updates fields on a chat document."""
        data["updated_at"] = float(time.time())
        res = await self.col.update_one({"chat_id": chat_id}, {"$set": data}, upsert=True)
        await cache.delete(f"chat_{chat_id}")
        return res.acknowledged

    # --- DELETE ---
    async def delete_chat(self, chat_id: int) -> bool:
        """DELETE: Deletes a chat document from database."""
        res = await self.col.delete_one({"chat_id": chat_id})
        await cache.delete(f"chat_{chat_id}")
        await cache.delete("stats_total_chats")
        return res.deleted_count > 0

    # --- AUTO-DELETE TASKS (CRUD) ---
    async def create_auto_delete_task(self, chat_id: int, message_id: int, delete_at: float):
        """CREATE: Schedules an auto-delete task."""
        await self.auto_del_col.insert_one({
            "chat_id": chat_id,
            "message_id": message_id,
            "delete_at": float(delete_at)
        })

    async def add_auto_delete_task(self, chat_id: int, message_id: int, delete_at: float):
        """Alias for create_auto_delete_task."""
        await self.create_auto_delete_task(chat_id, message_id, delete_at)

    async def get_expired_auto_delete(self, current_time: float) -> List[Dict[str, Any]]:
        """READ: Retrieves tasks where delete_at <= current_time."""
        cursor = self.auto_del_col.find({"delete_at": {"$lte": float(current_time)}})
        return await cursor.to_list(length=100)

    async def delete_auto_delete_task(self, chat_id: int, message_id: int) -> bool:
        """DELETE: Removes an auto-delete task."""
        res = await self.auto_del_col.delete_one({"chat_id": chat_id, "message_id": message_id})
        return res.deleted_count > 0

    async def remove_auto_delete_task(self, chat_id: int, message_id: int) -> bool:
        """Alias for delete_auto_delete_task."""
        return await self.delete_auto_delete_task(chat_id, message_id)

chat_repo = ChatRepository()
