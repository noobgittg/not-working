import time
import re
from typing import Optional, Dict, Any, List
from app.database.mongodb import mongo
from app.utils.cache import cache

class FileRepository:
    @property
    def col(self):
        return mongo.db.files

    async def save_file(
        self,
        file_id: str,
        chat_id: int,
        message_id: int,
        file_name: str,
        file_size: int,
        mime_type: str,
        metadata: Optional[Dict[str, Any]] = None,
        thumb_id: Optional[str] = None
    ) -> Dict[str, Any]:
        data = {
            "file_id": file_id,
            "chat_id": chat_id,
            "message_id": message_id,
            "file_name": file_name,
            "file_size": file_size,
            "mime_type": mime_type,
            "metadata": metadata or {},
            "thumb_id": thumb_id,
            "created_at": time.time()
        }
        await self.col.update_one({"file_id": file_id}, {"$set": data}, upsert=True)
        await cache.set(f"file_{file_id}", data, ttl=1800)
        await cache.delete("stats_total_files")
        return data

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
            return cached
        count = await self.col.count_documents({})
        await cache.set("stats_total_files", count, ttl=300)
        return count

    async def search_files(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        safe_query = re.escape(query.strip())
        cursor = self.col.find(
            {"file_name": {"$regex": safe_query, "$options": "i"}},
            {"_id": 0}
        ).sort("created_at", -1).limit(limit)
        return await cursor.to_list(length=limit)

    async def get_recent_files(self, limit: int = 10) -> List[Dict[str, Any]]:
        cursor = self.col.find({}, {"_id": 0}).sort("created_at", -1).limit(limit)
        return await cursor.to_list(length=limit)

file_repo = FileRepository()
