import time
import re
from typing import Optional, Dict, Any, List

from pymongo import ReturnDocument

from app.database.mongodb import mongo
from app.utils.cache import cache


class FileRepository:
    @property
    def col(self):
        if mongo.db is None:
            raise RuntimeError("MongoDB is not connected")
        return mongo.db.files

    async def save_file(
        self,
        file_id: str,
        chat_id: int,
        message_id: int,
        file_name: str,
        file_size: int,
        mime_type: str,
    ) -> Dict[str, Any]:
        now = time.time()
        data = {
            "file_id": file_id,
            "chat_id": chat_id,
            "message_id": message_id,
            "file_name": file_name,
            "file_size": int(file_size or 0),
            "mime_type": mime_type or "application/octet-stream",
            "updated_at": now,
        }
        stored = await self.col.find_one_and_update(
            {"file_id": file_id},
            {"$set": data, "$setOnInsert": {"created_at": now}},
            upsert=True,
            return_document=ReturnDocument.AFTER,
        )
        stored = dict(stored or data)
        stored.pop("_id", None)
        await cache.set(f"file_{file_id}", stored, ttl=1800)
        await cache.delete("stats_total_files")
        return stored

    async def get_file(self, file_id: str) -> Optional[Dict[str, Any]]:
        cache_key = f"file_{file_id}"
        cached = await cache.get(cache_key)
        if cached:
            return cached
        file_doc = await self.col.find_one({"file_id": file_id}, {"_id": 0})
        if file_doc:
            await cache.set(cache_key, file_doc, ttl=1800)
        return file_doc

    async def get_total_files(self) -> int:
        cached = await cache.get("stats_total_files")
        if cached is not None:
            return int(cached)
        count = await self.col.count_documents({})
        await cache.set("stats_total_files", count, ttl=300)
        return count

    async def search_files(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        safe_query = re.escape((query or "").strip())
        limit = max(1, min(int(limit), 100))
        cursor = self.col.find(
            {"file_name": {"$regex": safe_query, "$options": "i"}},
            {"_id": 0},
        ).sort("created_at", -1).limit(limit)
        return await cursor.to_list(length=limit)

    async def get_recent_files(self, limit: int = 10) -> List[Dict[str, Any]]:
        limit = max(1, min(int(limit), 100))
        cursor = self.col.find({}, {"_id": 0}).sort("created_at", -1).limit(limit)
        return await cursor.to_list(length=limit)


file_repo = FileRepository()
