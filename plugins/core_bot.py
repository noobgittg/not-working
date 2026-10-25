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
    async def start(self):
        await super().start()
        me = await self.get_me()
        logger.info(f"⚡ {to_smallcaps('bot connected as')} @{me.username} ({me.id})")
        logger.info(f"🚀 {to_smallcaps('12 mb/s stream & watermark engine')}: {Config.WATERMARK}")
    async def stop(self, *args):
        await super().stop()
        logger.info("Bot disconnected gracefully.")
