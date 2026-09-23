import os
import sys
import time
import asyncio
from config import Config
from app.utils.logger import logger
from app.database import mongo
from app.bot.client import MMWProBot
from app.web.web_support import WebSupport
from app.services.autodel_service import run_autodelete_sweeper
from app.services.keepalive_service import (
    run_keepalive_worker,
    schedule_24h_restart,
    send_restart_notification,
    RESTART_MARKER_FILE
)

async def start_bot_and_services(bot: MMWProBot):
    try:
        await mongo.connect()
    except Exception as e:
        logger.error(f"MongoDB connection warning: {e}. Bot will continue with cached state.")

    try:
        await bot.start()
        
        if os.path.exists(RESTART_MARKER_FILE):
            try:
                os.remove(RESTART_MARKER_FILE)
            except Exception:
                pass
            await send_restart_notification(bot)

        asyncio.create_task(run_autodelete_sweeper(bot))
        asyncio.create_task(run_keepalive_worker(bot, interval=6))
        asyncio.create_task(schedule_24h_restart(bot, interval=86400))
        
        logger.info(f"⚡ MMW All-In-One Pro Engine running. Watermark: {Config.WATERMARK}")
    except Exception as e:
        logger.error(f"Error starting bot services: {e}")

async def main():
    logger.info("⚡ Starting MMW Pro Engine with Koyeb Web Support...")
    bot = MMWProBot()
    
    web_support = WebSupport(bot)
    server = web_support.get_server()

    asyncio.create_task(start_bot_and_services(bot))

    try:
        await server.serve()
    finally:
        logger.info("Gracefully stopping engine...")
        try:
            await bot.stop()
        except Exception:
            pass
        try:
            await mongo.close()
        except Exception:
            pass

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Application stopped.")
