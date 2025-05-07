import asyncio
from datetime import datetime
from typing import Literal, Union

from pytdbot import types

from src import BACKUP_FOLDER


async def run_mongodump(uri: str,format_db: str = "gz") -> Union[str, types.Error]:
    """
    Dumps a MongoDB backup in the specified format.

    Args:
        uri: MongoDB connection URI.
        format_db: Either 'gz' for archive.gz or 'json' for bson/json folder.

    Returns:
        Path to the backup file or folder, or types.Error on failure.
    """
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")

    if format_db == "gz":
        backup_path = f"{BACKUP_FOLDER}/mongo_backup_{timestamp}.gz"
        command = f"mongodump --uri='{uri}' --archive={backup_path} --gzip"
    elif format_db == "json":
        # This actually dumps BSON files, but can be converted later
        backup_path = f"{BACKUP_FOLDER}/mongo_backup_{timestamp}"
        command = f"mongodump --uri='{uri}' --out={backup_path}"
    else:
        return types.Error(code=400, message="Invalid format")

    proc = await asyncio.create_subprocess_shell(
        command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )

    stdout, stderr = await proc.communicate()

    if proc.returncode != 0:
        print(f"[mongodump error]: {stderr.decode()}")
        return types.Error(code=400, message=stderr.decode())

    return backup_path
