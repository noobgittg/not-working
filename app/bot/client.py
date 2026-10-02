from pyrogram import Client
from config import Config
from app.utils.logger import logger

class MMWProBot(Client):
    def __init__(self):
        super().__init__(
            name="MMW_PRO_BOT",
            api_id=Config.API_ID,
            api_hash=Config.API_HASH,
            bot_token=Config.BOT_TOKEN,
            workers=Config.WORKERS,
            sleep_threshold=15,
            plugins=dict(root="app/bot/handlers")
        )

    async def start(self):
        await super().start()
        me = await self.get_me()
        logger.info(f"Bot connected as @{me.username} ({me.id})")
        logger.info(f"Watermark Engine: {Config.WATERMARK} ({Config.WATERMARK_URL})")

    async def stop(self, *args):
        await super().stop()
        logger.info("Bot disconnected gracefully.")
