from config import Config

def is_admin(user_id: int) -> bool:
    return int(user_id) in Config.ADMINS

async def require_admin(message_or_query) -> bool:
    user = getattr(message_or_query, "from_user", None)
    return bool(user and is_admin(user.id))
