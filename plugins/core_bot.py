import asyncio
from pyrogram import Client
from config import Config
from plugins.core_utils import logger, to_smallcaps

class MMWProBot(Client):
    def __init__(self):
        super().__init__(
            name="MMW_PRO_BOT",
            api_id=Config.API_ID,
            api_hash=Config.API_HASH,
            bot_token=Config.BOT_TOKEN,
            workers=Config.WORKERS,
            sleep_threshold=15,
            max_concurrent_transmissions=10,
            plugins=dict(root="plugins")
        )
        self.helper_bots = []
        self.work_loads = {self: 0}
        self._work_lock = asyncio.Lock()

    async def acquire_stream_client(self):
        """Choose the least-busy connected client for one byte-range request."""
        async with self._work_lock:
            connected = [
                client for client, load in self.work_loads.items()
                if getattr(client, "is_connected", False)
            ] or [self]
            selected = min(connected, key=lambda client: self.work_loads.get(client, 0))
            self.work_loads[selected] = self.work_loads.get(selected, 0) + 1

        async def release():
            async with self._work_lock:
                self.work_loads[selected] = max(0, self.work_loads.get(selected, 1) - 1)

        return selected, release

    async def start(self):
        await super().start()
        me = await self.get_me()
        logger.info(f"⚡ {to_smallcaps('bot connected as')} @{me.username} ({me.id})")
        logger.info(f"🚀 {to_smallcaps('12 mb/s stream & watermark engine')}: {Config.WATERMARK}")
        for index, token in enumerate(Config.MULTI_TOKENS, 1):
            if token == Config.BOT_TOKEN:
                continue
            try:
                helper = Client(
                    name=f"MMW_STREAM_HELPER_{index}",
                    api_id=Config.API_ID,
                    api_hash=Config.API_HASH,
                    bot_token=token,
                    workers=max(4, Config.WORKERS // 2),
                    sleep_threshold=15,
                    max_concurrent_transmissions=10,
                )
                await helper.start()
                self.helper_bots.append(helper)
                self.work_loads[helper] = 0
                logger.info("Connected stream helper bot %d", index)
            except Exception as exc:
                logger.warning("Unable to start MULTI_TOKEN%d helper: %s", index, exc)

    async def stop(self, *args):
        for helper in self.helper_bots:
            try:
                await helper.stop()
            except Exception:
                pass
        await super().stop()
        logger.info("Bot disconnected gracefully.")
