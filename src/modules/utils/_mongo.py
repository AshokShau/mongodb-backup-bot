import asyncio
import subprocess

from datetime import datetime
from typing import Union

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

async def run_mongorestore(uri: str, backup_path: str) -> Union[types.Ok, types.Error]:
    """Execute mongorestore command."""
    if backup_path.endswith(".gz"):
        restore_command = [
            "mongorestore",
            "--uri", uri,
            "--archive", backup_path,
            "--gzip",
        ]
    else:
        restore_command = [
            "mongorestore",
            "--uri", uri,
            "--archive", backup_path,
        ]

    process = subprocess.Popen(
        restore_command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    _, stderr = process.communicate()

    if process.returncode != 0:
        error_msg = stderr if stderr else "Unknown error"
        return types.Error(code=400, message=error_msg)
    return types.Ok()
