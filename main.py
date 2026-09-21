import asyncio
import os

from config import Config
from app.bot.client import MMWProBot
from app.database import mongo
from app.services.autodel_service import run_autodelete_sweeper
from app.services.keepalive_service import (
    RESTART_MARKER_FILE,
    run_keepalive_worker,
    schedule_24h_restart,
    send_restart_notification,
)
from app.utils.logger import logger
from app.web.web_support import WebSupport


async def main():
    Config.validate()
    logger.info("Starting MMW Pro Engine...")
    bot = MMWProBot()
    tasks = []
    try:
        await mongo.connect()
        await bot.start()
        if os.path.exists(RESTART_MARKER_FILE):
            try:
                os.remove(RESTART_MARKER_FILE)
            except OSError:
                pass
            await send_restart_notification(bot)

        tasks = [
            asyncio.create_task(run_autodelete_sweeper(bot), name="autodelete-sweeper"),
            asyncio.create_task(run_keepalive_worker(bot, interval=10), name="keepalive"),
            asyncio.create_task(schedule_24h_restart(bot, interval=86400), name="scheduled-restart"),
        ]
        logger.info("MMW All-In-One Pro Engine running. Watermark: %s", Config.WATERMARK)
        server = WebSupport(bot).get_server()
        await server.serve()
    except asyncio.CancelledError:
        raise
    except Exception:
        logger.exception("Fatal startup/runtime error")
        raise
    finally:
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        try:
            await bot.stop()
        except Exception:
            pass
        try:
            await mongo.close()
        except Exception:
            pass
        logger.info("MMW Pro Engine stopped cleanly.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Application stopped.")
