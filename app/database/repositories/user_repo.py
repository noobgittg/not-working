import time
from typing import Optional, Dict, Any, List

from pymongo import ReturnDocument
from app.database.mongodb import mongo
from app.database.models import new_user_dict
from app.utils.cache import cache


class UserRepository:
    @property
    def col(self):
        if mongo.db is None:
            raise RuntimeError("MongoDB is not connected")
        return mongo.db.users

    async def get_or_create(self, user_id: int, first_name: str, username: Optional[str] = None) -> Dict[str, Any]:
        now = time.time()
        defaults = new_user_dict(user_id, first_name, username)
        # Fields written by $set must not also exist in $setOnInsert: MongoDB
        # rejects overlapping update paths as a conflicting update.
        for key in ("first_name", "username", "updated_at"):
            defaults.pop(key, None)
        cache_key = f"user_{user_id}"
        cached = await cache.get(cache_key)
        if cached:
            return cached

        user = await self.col.find_one_and_update(
            {"user_id": user_id},
            {
                "$set": {
                    "first_name": first_name or "User",
                    "username": username,
                    "updated_at": now,
                },
                "$setOnInsert": defaults,
            },
            upsert=True,
            return_document=ReturnDocument.AFTER,
        )
        user.pop("_id", None)
        await cache.set(cache_key, user, ttl=600)
        await cache.delete("stats_total_users")
        return user

    async def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        cache_key = f"user_{user_id}"
        cached = await cache.get(cache_key)
        if cached:
            return cached
        user = await self.col.find_one({"user_id": user_id}, {"_id": 0})
        if user:
            await cache.set(cache_key, user, ttl=600)
        return user

    async def update_user(self, user_id: int, data: Dict[str, Any]):
        updates = dict(data)
        updates["updated_at"] = time.time()
        defaults = new_user_dict(user_id, "User", None)
        for key in list(updates):
            defaults.pop(key, None)
        defaults.pop("updated_at", None)
        await self.col.update_one(
            {"user_id": user_id},
            {"$set": updates, "$setOnInsert": defaults},
            upsert=True,
        )
        await cache.delete(f"user_{user_id}")
        if "is_banned" in updates:
            await cache.delete(f"banned_{user_id}")
            await cache.delete("stats_banned_users")

    async def get_total_users(self) -> int:
        cached = await cache.get("stats_total_users")
        if cached is not None:
            return int(cached)
        count = await self.col.count_documents({})
        await cache.set("stats_total_users", count, ttl=300)
        return count

    async def get_banned_users_count(self) -> int:
        cached = await cache.get("stats_banned_users")
        if cached is not None:
            return int(cached)
        count = await self.col.count_documents({"is_banned": True})
        await cache.set("stats_banned_users", count, ttl=300)
        return count

    async def get_all_users(self) -> List[Dict[str, Any]]:
        cursor = self.col.find({}, {"user_id": 1, "_id": 0})
        return await cursor.to_list(length=1_000_000)

    async def ban_user(self, user_id: int):
        await self.update_user(user_id, {"is_banned": True})
        await cache.set(f"banned_{user_id}", True, ttl=86400)

    async def unban_user(self, user_id: int):
        await self.update_user(user_id, {"is_banned": False})
        await cache.set(f"banned_{user_id}", False, ttl=86400)

    async def is_banned(self, user_id: int) -> bool:
        cache_key = f"banned_{user_id}"
        cached = await cache.get(cache_key)
        if cached is not None:
            return bool(cached)
        u = await self.get_user(user_id)
        banned = bool(u.get("is_banned", False)) if u else False
        await cache.set(cache_key, banned, ttl=1800)
        return banned

    async def add_caption(self, user_id: int, caption_text: str):
        now = time.time()
        defaults = new_user_dict(user_id, "User", None)
        defaults.pop("captions_list", None)
        defaults.pop("updated_at", None)
        await self.col.update_one(
            {"user_id": user_id},
            {
                "$addToSet": {"captions_list": caption_text},
                "$set": {"updated_at": now},
                "$setOnInsert": defaults,
            },
            upsert=True,
        )
        await cache.delete(f"user_{user_id}")

    async def remove_caption(self, user_id: int, caption_text: str):
        await self.col.update_one(
            {"user_id": user_id},
            {"$pull": {"captions_list": caption_text}, "$set": {"updated_at": time.time()}},
        )
        await cache.delete(f"user_{user_id}")


user_repo = UserRepository()
