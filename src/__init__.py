import logging
import os
import shutil
from datetime import datetime

from pytdbot import Client, types


logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s - %(levelname)s] - %(name)s - %(filename)s:%(lineno)d - %(message)s",
    datefmt="%d-%b-%y %H:%M:%S",
    handlers=[logging.StreamHandler()],
)


LOGGER = logging.getLogger("Bot")

__version__ = "0.1.0"

from src import config

StartTime = datetime.now()

BACKUP_FOLDER = "./backups"


class Telegram(Client):
    def __init__(self) -> None:
        super().__init__(
            token=config.TOKEN,
            api_id=config.API_ID,
            api_hash=config.API_HASH,
            default_parse_mode="html",
            td_verbosity=2,
            td_log=types.LogStreamEmpty(),
            plugins=types.plugins.Plugins(folder="src/modules"),
            files_directory="",
            database_encryption_key="",
            options={"ignore_background_updates": True},
        )


    async def start(self) -> None:
        if shutil.which("mongodump") is None:
            print("❌ mongodump is not installed. Please install MongoDB tools:")
            print("• Arch: yay -S mongodb-tools-bin")
            print("• Ubuntu/Docker: use official .tgz tools from https://www.mongodb.com/try/download/database-tools")

        await super().start()
        os.makedirs(BACKUP_FOLDER, exist_ok=True)
        self.logger.info(f"Bot started in {datetime.now() - StartTime} seconds.")
        self.logger.info(f"Version: {__version__}")

    async def stop(self) -> None:
        await super().stop()


client: Telegram = Telegram()
