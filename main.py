import os
import asyncio
from config import Config
from plugins.core_utils import logger, to_smallcaps
from plugins.core_db import mongo
from plugins.core_bot import MMWProBot
from plugins.core_web import WebSupport
from plugins.core_services import (
    run_autodelete_sweeper,
    run_keepalive_worker,
    schedule_24h_restart,
    send_restart_notification,
    RESTART_MARKER_FILE
)

async def start_bot_and_services(bot: MMWProBot):
    try:
        await mongo.connect()
    except Exception as e:
        logger.warning(f"MongoDB connection warning: {e}. Continuing with unified In-Memory DB + FastMemoryCache.")

    if not Config.BOT_TOKEN:
        logger.warning("⚠️ BOT_TOKEN is not set in environment! Web server is running, waiting for BOT_TOKEN.")
        return

    try:
        await bot.start()

        if os.path.exists(RESTART_MARKER_FILE):
            try:
                os.remove(RESTART_MARKER_FILE)
            except Exception:
                pass
            await send_restart_notification(bot)

        asyncio.create_task(run_autodelete_sweeper(bot))
        asyncio.create_task(run_keepalive_worker(bot, interval=Config.KEEPALIVE_INTERVAL))
        asyncio.create_task(schedule_24h_restart(bot, interval=Config.RESTART_INTERVAL))

        logger.info(f"⚡ {to_smallcaps('mmw all-in-one pro engine running! 12 mb/s stream & 4 players ready.')}")
    except Exception as e:
        logger.error(f"Error starting bot services: {e}")

async def main():
    logger.info(f"⚡ {to_smallcaps('starting mmw pro engine with 12 mb/s web stream support...')}")
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
        logger.info("Application stopped gracefully.")
