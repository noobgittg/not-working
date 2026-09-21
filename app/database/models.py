import time
from typing import Optional, Dict, Any, List

def new_user_dict(user_id: int, first_name: str, username: Optional[str] = None) -> Dict[str, Any]:
    return {
        "user_id": user_id,
        "first_name": first_name,
        "username": username,
        "is_banned": False,
        "thumb_id": None,
        "tham_url": None,
        "custom_caption": None,
        "captions_list": [],
        "prefix": "",
        "suffix": "",
        "rename_format": None,
        "auto_delete_time": 0,
        "compression_preset": "superfast",
        "resolution": "720p",
        "created_at": time.time(),
        "updated_at": time.time()
    }

def new_chat_dict(chat_id: int, title: str, chat_type: str) -> Dict[str, Any]:
    return {
        "chat_id": chat_id,
        "title": title,
        "chat_type": chat_type,
        "auto_thumbnail": True,
        "tham_url": None,
        "auto_caption": None,
        "auto_delete_time": 0,
        "clean_service_messages": True,
        "auto_approve_joins": True,
        "created_at": time.time(),
        "updated_at": time.time()
    }
