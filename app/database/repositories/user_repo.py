import time
from typing import Optional, Dict, Any, List
from app.database.mongodb import mongo
from app.database.models import new_user_dict
from app.utils.cache import cache

class UserRepository:
    @property
    def col(self):
        return mongo.db.users

    async def get_or_create(self, user_id: int, first_name: str, username: Optional[str] = None) -> Dict[str, Any]:
        cache_key = f"user_{user_id}"
        cached = await cache.get(cache_key)
        if cached:
            return cached

        user = await self.col.find_one({"user_id": user_id})
        if not user:
            user_data = new_user_dict(user_id, first_name, username)
            try:
                await self.col.insert_one(user_data)
                user = user_data
            except Exception:
                # Handle race condition/DuplicateKeyError gracefully
                user = await self.col.find_one({"user_id": user_id})
                if not user:
                    user = user_data

        user_clean = dict(user)
        user_clean.pop("_id", None)
        await cache.set(cache_key, user_clean, ttl=600)
        return user_clean

    async def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        cache_key = f"user_{user_id}"
        cached = await cache.get(cache_key)
        if cached:
            return cached
        user = await self.col.find_one({"user_id": user_id})
        if user:
            user_clean = dict(user)
            user_clean.pop("_id", None)
            await cache.set(cache_key, user_clean, ttl=600)
            return user_clean
        return user

    async def update_user(self, user_id: int, data: Dict[str, Any]):
        data["updated_at"] = time.time()
        await self.col.update_one({"user_id": user_id}, {"$set": data}, upsert=True)
        await cache.delete(f"user_{user_id}")

    async def get_total_users(self) -> int:
        cached = await cache.get("stats_total_users")
        if cached is not None:
            return cached
        count = await self.col.count_documents({})
        await cache.set("stats_total_users", count, ttl=300)
        return count

    async def get_banned_users_count(self) -> int:
        cached = await cache.get("stats_banned_users")
        if cached is not None:
            return cached
        count = await self.col.count_documents({"is_banned": True})
        await cache.set("stats_banned_users", count, ttl=300)
        return count

    async def get_all_users(self) -> List[Dict[str, Any]]:
        cursor = self.col.find({}, {"user_id": 1, "_id": 0})
        return await cursor.to_list(length=100000)

    async def ban_user(self, user_id: int):
        await self.col.update_one({"user_id": user_id}, {"$set": {"is_banned": True, "updated_at": time.time()}})
        await cache.set(f"banned_{user_id}", True, ttl=86400)
        await cache.delete(f"user_{user_id}")
        await cache.delete("stats_banned_users")

    async def unban_user(self, user_id: int):
        await self.col.update_one({"user_id": user_id}, {"$set": {"is_banned": False, "updated_at": time.time()}})
        await cache.set(f"banned_{user_id}", False, ttl=86400)
        await cache.delete(f"user_{user_id}")
        await cache.delete("stats_banned_users")

    async def is_banned(self, user_id: int) -> bool:
        cache_key = f"banned_{user_id}"
        cached = await cache.get(cache_key)
        if cached is not None:
            return cached
        u = await self.get_user(user_id)
        banned = bool(u.get("is_banned", False)) if u else False
        await cache.set(cache_key, banned, ttl=1800)
        return banned

    async def add_caption(self, user_id: int, caption_text: str):
        await self.col.update_one(
            {"user_id": user_id},
            {"$addToSet": {"captions_list": caption_text}, "$set": {"updated_at": time.time()}},
            upsert=True
        )
        await cache.delete(f"user_{user_id}")

    async def remove_caption(self, user_id: int, caption_text: str):
        await self.col.update_one(
            {"user_id": user_id},
            {"$pull": {"captions_list": caption_text}, "$set": {"updated_at": time.time()}}
        )
        await cache.delete(f"user_{user_id}")

user_repo = UserRepository()
