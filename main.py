import os
import sys
import asyncio

PLUGIN_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "plugins")
if PLUGIN_DIR not in sys.path:
    sys.path.insert(0, PLUGIN_DIR)
from config import Config
from logger import logger
from mongodb import mongo
from client import MMWProBot
from web_support import WebSupport
from autodel_service import run_autodelete_sweeper
from keepalive_service import (
    run_keepalive_worker,
    schedule_24h_restart,
    send_restart_notification,
    RESTART_MARKER_FILE
)

async def start_bot_and_services(bot: MMWProBot):
    await mongo.connect()
    await bot.start()

    if os.path.exists(RESTART_MARKER_FILE):
        try:
            os.remove(RESTART_MARKER_FILE)
        except OSError as exc:
            logger.warning("Could not clear restart marker (%s).", type(exc).__name__)
        try:
            await send_restart_notification(bot)
        except Exception as exc:
            logger.warning("Restart notification failed (%s).", type(exc).__name__)

    asyncio.create_task(run_autodelete_sweeper(bot), name="auto-delete-sweeper")
    asyncio.create_task(run_keepalive_worker(bot, interval=6), name="keepalive-worker")
    asyncio.create_task(schedule_24h_restart(bot, interval=86400), name="daily-restart")
    logger.info("MMW All-In-One Pro Engine running. Watermark: %s", Config.WATERMARK)


async def main():
    logger.info("Starting MMW Pro Engine with Koyeb Web Support...")
    bot = MMWProBot()
    web_support = WebSupport(bot)
    server = web_support.get_server()

    try:
        await start_bot_and_services(bot)
        await server.serve()
    finally:
        logger.info("Gracefully stopping engine...")
        if getattr(bot, "is_connected", False):
            try:
                await bot.stop()
            except Exception as exc:
                logger.warning("Bot shutdown encountered an error (%s).", type(exc).__name__)
        try:
            await mongo.close()
        except Exception as exc:
            logger.warning("MongoDB shutdown encountered an error (%s).", type(exc).__name__)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Application stopped gracefully.")
