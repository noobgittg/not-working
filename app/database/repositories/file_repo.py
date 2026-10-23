import re
import time
from typing import Optional, Dict, Any, List
from app.database.mongodb import mongo
from app.database.models import new_file_dict
from app.utils.cache import cache

class FileRepository:
    """
    Production-ready MongoDB repository for streamed and stored files.
    Full CRUD implementation: create_data, get_data, update_data, delete_data, search_files, revoke_file.
    """
    @property
    def col(self):
        return mongo.db.files

    # --- CREATE ---
    async def create_file(
        self,
        file_id: str,
        chat_id: int,
        message_id: int,
        file_name: str,
        file_size: int,
        mime_type: str,
        user_id: int = 0,
        metadata: Optional[Dict[str, Any]] = None,
        thumb_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """CREATE: Saves a new file reference into the database and caches it."""
        data = new_file_dict(
            file_id=file_id,
            chat_id=chat_id,
            message_id=message_id,
            file_name=file_name,
            file_size=file_size,
            mime_type=mime_type,
            user_id=user_id,
            metadata=metadata,
            thumb_id=thumb_id
        )
        await self.col.update_one({"file_id": file_id}, {"$set": data}, upsert=True)
        await cache.set(f"file_{file_id}", data, ttl=1800)
        await cache.delete("stats_total_files")
        return data

    async def save_file(
        self,
        file_id: str,
        chat_id: int,
        message_id: int,
        file_name: str,
        file_size: int,
        mime_type: str,
        user_id: int = 0,
        metadata: Optional[Dict[str, Any]] = None,
        thumb_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Alias for create_file for backward compatibility."""
        return await self.create_file(
            file_id=file_id,
            chat_id=chat_id,
            message_id=message_id,
            file_name=file_name,
            file_size=file_size,
            mime_type=mime_type,
            user_id=user_id,
            metadata=metadata,
            thumb_id=thumb_id
        )

    # Standard explicit CRUD alias
    async def create_data(self, *args, **kwargs) -> Dict[str, Any]:
        return await self.create_file(*args, **kwargs)

    # --- READ ---
    async def get_file(self, file_id: str, include_revoked: bool = False) -> Optional[Dict[str, Any]]:
        """READ: Retrieves file metadata by file_id from cache or database."""
        cache_key = f"file_{file_id}"
        cached = await cache.get(cache_key)
        if cached:
            if not include_revoked and cached.get("is_revoked"):
                return None
            return cached

        file_doc = await self.col.find_one({"file_id": file_id}, {"_id": 0})
        if file_doc:
            await cache.set(cache_key, file_doc, ttl=1800)
            if not include_revoked and file_doc.get("is_revoked"):
                return None
        return file_doc

    # Standard explicit CRUD alias
    async def get_data(self, file_id: str, include_revoked: bool = False) -> Optional[Dict[str, Any]]:
        return await self.get_file(file_id, include_revoked=include_revoked)

    async def get_total_files(self) -> int:
        """READ: Retrieves total count of active indexed files with caching."""
        cached = await cache.get("stats_total_files")
        if cached is not None:
            return cached
        count = await self.col.count_documents({"is_revoked": {"$ne": True}})
        await cache.set("stats_total_files", count, ttl=300)
        return count

    async def get_recent_files(self, limit: int = 15) -> List[Dict[str, Any]]:
        """READ: Retrieves the most recently indexed non-revoked files."""
        cursor = self.col.find({"is_revoked": {"$ne": True}}, {"_id": 0}).sort("created_at", -1).limit(limit)
        return await cursor.to_list(length=limit)

    async def search_files(self, query: str, limit: int = 15) -> List[Dict[str, Any]]:
        """READ: Searches active indexed files by filename regex."""
        if not query or not query.strip():
            return []
        safe_q = re.escape(query.strip())
        cursor = self.col.find(
            {"file_name": {"$regex": safe_q, "$options": "i"}, "is_revoked": {"$ne": True}},
            {"_id": 0}
        ).sort("created_at", -1).limit(limit)
        return await cursor.to_list(length=limit)

    # --- UPDATE ---
    async def update_file(self, file_id: str, data: Dict[str, Any]) -> bool:
        """UPDATE: Updates metadata of an existing file and invalidates cache."""
        data["updated_at"] = float(time.time())
        res = await self.col.update_one({"file_id": file_id}, {"$set": data})
        await cache.delete(f"file_{file_id}")
        return res.acknowledged

    async def revoke_file(self, file_id: str) -> bool:
        """UPDATE: Permanently disables/revokes stream access for a file."""
        now_ts = float(time.time())
        res = await self.col.update_one(
            {"file_id": file_id},
            {"$set": {"is_revoked": True, "updated_at": now_ts}}
        )
        await cache.delete(f"file_{file_id}")
        await cache.delete("stats_total_files")
        return res.acknowledged

    async def unrevoke_file(self, file_id: str) -> bool:
        """UPDATE: Restores previously revoked stream access for a file."""
        now_ts = float(time.time())
        res = await self.col.update_one(
            {"file_id": file_id},
            {"$set": {"is_revoked": False, "updated_at": now_ts}}
        )
        await cache.delete(f"file_{file_id}")
        await cache.delete("stats_total_files")
        return res.acknowledged

    # Standard explicit CRUD alias
    async def update_data(self, file_id: str, data: Dict[str, Any]) -> bool:
        return await self.update_file(file_id, data)

    # --- DELETE ---
    async def delete_file(self, file_id: str) -> bool:
        """DELETE: Deletes a file entry from database and invalidates cache."""
        res = await self.col.delete_one({"file_id": file_id})
        await cache.delete(f"file_{file_id}")
        await cache.delete("stats_total_files")
        return res.deleted_count > 0

    # Standard explicit CRUD alias
    async def delete_data(self, file_id: str) -> bool:
        return await self.delete_file(file_id)

file_repo = FileRepository()
