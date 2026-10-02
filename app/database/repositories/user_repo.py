import time
from typing import Optional, Dict, Any, List
from app.database.mongodb import mongo
from app.database.models import new_user_dict
from app.utils.cache import cache

class UserRepository:
    """
    Production-ready MongoDB repository for user data with dual-layer caching.
    Full CRUD implementation: create_user, get_user, update_user, delete_user.
    """
    @property
    def col(self):
        return mongo.db.users

    # --- CREATE ---
    async def create_user(self, user_id: int, first_name: str, username: Optional[str] = None) -> Dict[str, Any]:
        """CREATE: Inserts a new user document into the database."""
        user_data = new_user_dict(user_id, first_name, username)
        await self.col.update_one({"user_id": user_id}, {"$setOnInsert": user_data}, upsert=True)
        await cache.set(f"user_{user_id}", user_data, ttl=600)
        await cache.delete("stats_total_users")
        return user_data

    async def get_or_create(self, user_id: int, first_name: str, username: Optional[str] = None) -> Dict[str, Any]:
        """Fetches existing user from cache/DB or creates a new user if not found."""
        cache_key = f"user_{user_id}"
        cached = await cache.get(cache_key)
        if cached:
            return cached

        user = await self.col.find_one({"user_id": user_id})
        if not user:
            user = new_user_dict(user_id, first_name, username)
            await self.col.insert_one(user)
            await cache.delete("stats_total_users")
        
        await cache.set(cache_key, user, ttl=600)
        return user

    # --- READ ---
    async def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        """READ: Retrieves user data by user_id from cache or database."""
        cache_key = f"user_{user_id}"
        cached = await cache.get(cache_key)
        if cached:
            return cached
        user = await self.col.find_one({"user_id": user_id})
        if user:
            await cache.set(cache_key, user, ttl=600)
        return user

    async def get_all_users(self) -> List[Dict[str, Any]]:
        """READ: Retrieves all registered users (ID projection for efficient memory)."""
        cursor = self.col.find({}, {"user_id": 1, "_id": 0})
        return await cursor.to_list(length=100000)

    async def get_users_paginated(self, skip: int = 0, limit: int = 10) -> List[Dict[str, Any]]:
        """READ: Retrieves a paginated list of users sorted by registration date."""
        cursor = self.col.find({}, {"_id": 0}).sort("created_at", -1).skip(skip).limit(limit)
        return await cursor.to_list(length=limit)

    async def get_total_users(self) -> int:
        """READ: Retrieves total user count with caching."""
        cached = await cache.get("stats_total_users")
        if cached is not None:
            return cached
        count = await self.col.count_documents({})
        await cache.set("stats_total_users", count, ttl=300)
        return count

    async def get_banned_users_count(self) -> int:
        """READ: Retrieves total count of banned users with caching."""
        cached = await cache.get("stats_banned_users")
        if cached is not None:
            return cached
        count = await self.col.count_documents({"is_banned": True})
        await cache.set("stats_banned_users", count, ttl=300)
        return count

    async def is_banned(self, user_id: int) -> bool:
        """READ: Check if user is banned with dedicated cache layer."""
        cache_key = f"banned_{user_id}"
        cached = await cache.get(cache_key)
        if cached is not None:
            return cached
        user = await self.get_user(user_id)
        banned = bool(user.get("is_banned", False)) if user else False
        await cache.set(cache_key, banned, ttl=1800)
        return banned

    # --- UPDATE ---
    async def update_user(self, user_id: int, data: Dict[str, Any]) -> bool:
        """UPDATE: Updates fields on an existing user document and invalidates cache."""
        data["updated_at"] = float(time.time())
        res = await self.col.update_one({"user_id": user_id}, {"$set": data}, upsert=True)
        await cache.delete(f"user_{user_id}")
        return res.acknowledged

    async def ban_user(self, user_id: int):
        """UPDATE: Sets banned status to True."""
        now_ts = float(time.time())
        await self.col.update_one({"user_id": user_id}, {"$set": {"is_banned": True, "updated_at": now_ts}})
        await cache.set(f"banned_{user_id}", True, ttl=86400)
        await cache.delete(f"user_{user_id}")
        await cache.delete("stats_banned_users")

    async def unban_user(self, user_id: int):
        """UPDATE: Sets banned status to False."""
        now_ts = float(time.time())
        await self.col.update_one({"user_id": user_id}, {"$set": {"is_banned": False, "updated_at": now_ts}})
        await cache.set(f"banned_{user_id}", False, ttl=86400)
        await cache.delete(f"user_{user_id}")
        await cache.delete("stats_banned_users")

    async def add_caption(self, user_id: int, caption_text: str):
        """UPDATE: Appends a caption template to dynamic caption list."""
        now_ts = float(time.time())
        await self.col.update_one(
            {"user_id": user_id},
            {"$addToSet": {"captions_list": caption_text}, "$set": {"updated_at": now_ts}},
            upsert=True
        )
        await cache.delete(f"user_{user_id}")

    async def remove_caption(self, user_id: int, caption_text: str):
        """UPDATE: Removes a caption from dynamic caption list."""
        now_ts = float(time.time())
        await self.col.update_one(
            {"user_id": user_id},
            {"$pull": {"captions_list": caption_text}, "$set": {"updated_at": now_ts}}
        )
        await cache.delete(f"user_{user_id}")

    async def delete_caption(self, user_id: int, caption_text: str):
        """UPDATE / DELETE: Alias for remove_caption."""
        await self.remove_caption(user_id, caption_text)

    # --- DELETE ---
    async def delete_user(self, user_id: int) -> bool:
        """DELETE: Deletes a user document completely from database."""
        res = await self.col.delete_one({"user_id": user_id})
        await cache.delete(f"user_{user_id}")
        await cache.delete(f"banned_{user_id}")
        await cache.delete("stats_total_users")
        await cache.delete("stats_banned_users")
        return res.deleted_count > 0

user_repo = UserRepository()
