import time
import asyncio
import uvicorn
from config import Config
from app.utils.logger import logger
from app.web.app import create_app

class WebSupport:
    def __init__(self, bot):
        self.bot = bot
        self.app = create_app(bot)
        self.start_time = time.time()
        self.server = None

    def get_server(self) -> uvicorn.Server:
        config = uvicorn.Config(
            app=self.app,
            host=Config.BIND_ADDRESS,
            port=Config.PORT,
            log_level="warning",
            access_log=False
        )
        self.server = uvicorn.Server(config)
        return self.server

    async def start(self):
        server = self.get_server()
        logger.info(f"⚡ Koyeb Web Support active on {Config.BIND_ADDRESS}:{Config.PORT}")
        await server.serve()
