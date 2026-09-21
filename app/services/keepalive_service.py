import os
import sys
import time
import socket
import asyncio
import urllib.request
from urllib.parse import urlparse
import http.client
import aiohttp
from config import Config
from app.utils.logger import logger

RESTART_MARKER_FILE = os.path.join(Config.DOWNLOAD_DIR, ".restarted_marker")

class KeepAliveManager:
    """
    Zero-dependency / no-extra-import Keep-Alive engine supporting 6 distinct ping types:
    1. aiohttp_get: Asynchronous HTTP GET ping (aiohttp).
    2. aiohttp_head: Asynchronous HTTP HEAD ping (aiohttp).
    3. urllib_get: Standard library urllib.request GET ping.
    4. http_client: Standard library http.client connection ping.
    5. tcp_socket: Standard library raw TCP socket ping.
    6. telegram_ping: Pyrogram bot Telegram API keepalive ping (bot.get_me).
    """
    def __init__(self, bot, target_url: str = None, interval: int = 6):
        self.bot = bot
        self.target_url = (target_url or Config.BASE_URL).rstrip("/")
        self.local_url = f"http://127.0.0.1:{Config.PORT}"
        self.interval = interval  # 6 seconds
        self._current_type_idx = 0

    async def ping_type_1_aiohttp_get(self) -> bool:
        try:
            url = f"{self.target_url}/health"
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=4)) as resp:
                    return resp.status in [200, 204, 301, 302]
        except Exception:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(f"{self.local_url}/health", timeout=aiohttp.ClientTimeout(total=3)) as resp:
                        return resp.status in [200, 204]
            except Exception as e:
                logger.debug(f"KeepAlive Type 1 (aiohttp_get) error: {e}")
                return False

    async def ping_type_2_aiohttp_head(self) -> bool:
        try:
            url = f"{self.target_url}/health"
            async with aiohttp.ClientSession() as session:
                async with session.head(url, timeout=aiohttp.ClientTimeout(total=4)) as resp:
                    return resp.status in [200, 204, 301, 302]
        except Exception:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.head(f"{self.local_url}/health", timeout=aiohttp.ClientTimeout(total=3)) as resp:
                        return resp.status in [200, 204]
            except Exception as e:
                logger.debug(f"KeepAlive Type 2 (aiohttp_head) error: {e}")
                return False

    async def ping_type_3_urllib_get(self) -> bool:
        loop = asyncio.get_running_loop()
        def _sync_urllib():
            for target in [f"{self.target_url}/health", f"{self.local_url}/health"]:
                try:
                    req = urllib.request.Request(target, headers={"User-Agent": "MMW-KeepAlive-Ping/1.0"})
                    with urllib.request.urlopen(req, timeout=4) as response:
                        if response.status in [200, 204, 301, 302]:
                            return True
                except Exception:
                    continue
            return False
        return await loop.run_in_executor(None, _sync_urllib)

    async def ping_type_4_http_client(self) -> bool:
        loop = asyncio.get_running_loop()
        def _sync_http_client():
            try:
                parsed = urlparse(self.target_url)
                host = parsed.hostname or "127.0.0.1"
                port = parsed.port or (443 if parsed.scheme == "https" else 80)
                conn_cls = http.client.HTTPSConnection if parsed.scheme == "https" else http.client.HTTPConnection
                conn = conn_cls(host, port, timeout=4)
                conn.request("GET", parsed.path or "/health")
                resp = conn.getresponse()
                conn.close()
                return resp.status in [200, 204, 301, 302]
            except Exception:
                try:
                    conn = http.client.HTTPConnection("127.0.0.1", Config.PORT, timeout=3)
                    conn.request("GET", "/health")
                    resp = conn.getresponse()
                    conn.close()
                    return resp.status in [200, 204]
                except Exception as e:
                    logger.debug(f"KeepAlive Type 4 (http_client) error: {e}")
                    return False
        return await loop.run_in_executor(None, _sync_http_client)

    async def ping_type_5_tcp_socket(self) -> bool:
        loop = asyncio.get_running_loop()
        def _sync_tcp_ping():
            try:
                sock = socket.create_connection(("127.0.0.1", Config.PORT), timeout=3)
                sock.close()
                return True
            except Exception as e:
                logger.debug(f"KeepAlive Type 5 (tcp_socket) error: {e}")
                return False
        return await loop.run_in_executor(None, _sync_tcp_ping)

    async def ping_type_6_telegram_ping(self) -> bool:
        try:
            if self.bot and getattr(self.bot, "is_connected", False):
                await self.bot.get_me()
                return True
        except Exception as e:
            logger.debug(f"KeepAlive Type 6 (telegram_ping) error: {e}")
        return False

    async def execute_ping(self, ping_type: int = None) -> bool:
        if ping_type is None:
            self._current_type_idx = (self._current_type_idx % 6) + 1
            ptype = self._current_type_idx
        else:
            ptype = ping_type

        handlers = {
            1: self.ping_type_1_aiohttp_get,
            2: self.ping_type_2_aiohttp_head,
            3: self.ping_type_3_urllib_get,
            4: self.ping_type_4_http_client,
            5: self.ping_type_5_tcp_socket,
            6: self.ping_type_6_telegram_ping
        }
        handler = handlers.get(ptype, self.ping_type_1_aiohttp_get)
        return await handler()

async def run_keepalive_worker(bot, interval: int = 6):
    manager = KeepAliveManager(bot=bot, interval=interval)
    logger.info(f"KeepAlive Engine active with 6 ping types (interval: {interval}s, zero extra imports).")
    await asyncio.sleep(5)
    while True:
        try:
            await manager.execute_ping()
        except Exception as e:
            logger.debug(f"Keepalive cycle exception: {e}")
        await asyncio.sleep(interval)

async def send_restart_notification(bot):
    message_text = "Here I am Restarted, Successfully"
    for admin_id in Config.ADMINS:
        try:
            await bot.send_message(chat_id=admin_id, text=message_text)
            logger.info(f"Restart notification sent to admin: {admin_id}")
        except Exception as e:
            logger.warning(f"Could not send restart notification to admin {admin_id}: {e}")

async def schedule_24h_restart(bot, interval: int = 86400):
    logger.info(f"24-Hour Auto-Restart scheduler active (interval: {interval} seconds).")
    while True:
        await asyncio.sleep(interval)
        logger.info("24 Hours elapsed. Initiating automatic restart sequence...")
        
        try:
            os.makedirs(Config.DOWNLOAD_DIR, exist_ok=True)
            with open(RESTART_MARKER_FILE, "w") as f:
                f.write(f"{time.time()}")
        except Exception as e:
            logger.error(f"Error writing restart marker: {e}")

        await send_restart_notification(bot)

        try:
            await bot.stop()
        except Exception:
            pass

        logger.info("Re-executing process with os.execl...")
        os.execl(sys.executable, sys.executable, *sys.argv)
