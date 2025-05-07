import asyncio
import shutil
from datetime import datetime
from typing import Union

from pytdbot import types

from src import BACKUP_FOLDER


async def run_mongodump(uri: str, format_db: str = "gz") -> Union[str, types.Error]:
    """
    Dumps a MongoDB backup in the specified format.

    Args:
        uri: MongoDB connection URI.
        format_db: Either 'gz' for archive.gz or 'json' for bson/json folder.

    Returns:
        Path to the backup file or folder, or types.Error on failure.
    """
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    dump_folder = None
    backup_path = None

    if format_db == "gz":
        backup_path = f"{BACKUP_FOLDER}/mongo_backup_{timestamp}.gz"
        command = f"mongodump --uri='{uri}' --archive={backup_path} --gzip"

    elif format_db == "json":
        dump_folder = f"{BACKUP_FOLDER}/mongo_backup_{timestamp}"
        command = f"mongodump --uri='{uri}' --out={dump_folder}"
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

    if format_db == "json":
        zip_path = f"{dump_folder}.zip"
        shutil.make_archive(dump_folder, "zip", dump_folder)
        shutil.rmtree(dump_folder)
        return zip_path

    return backup_path


async def run_mongorestore(uri: str, backup_path: str) -> Union[types.Ok, types.Error]:
    """
    Restores a MongoDB backup from either a .gz archive or extracted folder/zip.

    Args:
        uri: MongoDB connection URI.
        backup_path: Path to the backup file (.gz or .zip) or folder.

    Returns:
        types.Ok on success, or types.Error on failure.
    """
    if backup_path.endswith(".gz"):
        restore_command = f"mongorestore --uri='{uri}' --archive={backup_path} --gzip"
    elif backup_path.endswith(".zip"):
        unzip_dir = backup_path.replace(".zip", "")
        shutil.unpack_archive(backup_path, unzip_dir)
        restore_command = f"mongorestore --uri='{uri}' {unzip_dir}"
    else:
        restore_command = f"mongorestore --uri='{uri}' {backup_path}"

    proc = await asyncio.create_subprocess_shell(
        restore_command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )

    stdout, stderr = await proc.communicate()

    if proc.returncode != 0:
        return types.Error(code=400, message=stderr.decode())

    return types.Ok()
