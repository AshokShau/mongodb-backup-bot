import os
import re

from typing import Optional, Union

from pytdbot import Client, types

from src.modules.utils import Filter, extract_argument, run_mongodump, run_mongorestore


@Client.on_message(filters=Filter.command("mongo"))
async def mongo_cmd(_: Client, msg: types.Message) -> None:
    """Handle MongoDB backup/restore commands."""
    args = extract_argument(msg.text)
    if not args:
        await msg.reply_text("❌ Please provide a MongoDB URI.")
        return None

    uri = extract_mongo_uri(args)
    if not uri:
        await msg.reply_text("❌ Invalid or missing MongoDB URI.")
        return None

    flags = args.lower()

    if "{import}" in flags:
        return await import_mongo(msg, uri)

    await handle_backup_request(msg, uri, flags)
    return None


async def handle_backup_request(msg: types.Message, uri: str, flags: str) -> None:
    """Handle MongoDB backup requests."""
    format_db = "json" if "{json}" in flags and "{gz}" not in flags else "gz"
    reply = await msg.reply_text(f"📦 Creating backup in <b>{format_db.upper()}</b> format...")

    backup_path = await run_mongodump(uri, format_db=format_db)
    if isinstance(backup_path, types.Error):
        await reply.edit_text(text=f"❌ Backup failed: {backup_path.message}")
        return

    done = await send_backup_file(msg, uri, format_db, backup_path)
    cleanup_file(backup_path)
    if isinstance(done, types.Error):
        await reply.edit_text(text=f"❌ Backup failed: {done.message}")

    await reply.delete()


async def import_mongo(msg: types.Message, target_uri: str) -> None:
    """Handle MongoDB import requests."""
    reply = await msg.getRepliedMessage() if msg.reply_to_message_id else None
    if not reply or isinstance(reply, types.Error):
        await msg.reply_text("❌ Please reply to a MongoDB backup file.")
        return

    if not isinstance(reply.content, types.MessageDocument):
        await msg.reply_text("❌ Please reply to a MongoDB backup file.")
        return

    file_name = reply.content.document.file_name
    if not is_valid_backup_file(file_name):
        await msg.reply_text("❌ Please reply to a valid MongoDB backup file (.gz or .json).")
        return

    await process_import(msg, reply, target_uri)


async def process_import(
        msg: types.Message,
        reply: types.Message,
        target_uri: str
) -> None:
    """Process the MongoDB import operation."""
    status_msg = await msg.reply_text("📦 Importing MongoDB backup...")

    backup_path = await reply.download()
    if isinstance(backup_path, types.Error):
        await status_msg.edit_text(f"❌ Failed to download backup file: {backup_path.message}")
        return

    result = await run_mongorestore(target_uri, backup_path.path)
    if isinstance(result, types.Error):
        await status_msg.edit_text(f"❌ MongoDB import failed: {result.message}")
        return

    await status_msg.edit_text(f"✅ MongoDB import complete to <code>{sanitize_uri(target_uri)}</code>.")
    cleanup_file(backup_path.path)


def extract_mongo_uri(text: str) -> Optional[str]:
    """Extract MongoDB URI from text."""
    uri_pattern = r"(mongodb(?:\+srv)?:\/\/[a-zA-Z0-9\-._~:\/?#[\]@!$&'()*+,;=]+)"
    match = re.search(uri_pattern, text)
    return match.group(0) if match else None


def is_valid_backup_file(filename: str) -> bool:
    """Check if file is a valid MongoDB backup."""
    return filename.endswith((".gz", ".json"))

async def send_backup_file(
        msg: types.Message,
        uri: str,
        format_db: str,
        backup_path: str
) -> Union[types.Message, types.Error]:
    """Send the backup file to the user."""
    return await msg.reply_document(
        document=types.InputFileLocal(backup_path),
        caption=(
            f"✅ MongoDB backup complete.\n\n"
            f"<b>URI:</b> <code>{sanitize_uri(uri)}</code>\n"
            f"<b>Format:</b> <code>{format_db.upper()}</code>"
        ),
        parse_mode="html",
    )


def sanitize_uri(uri: str) -> str:
    """Sanitize MongoDB URI for display (hides password)."""
    if "@" in uri:
        protocol, rest = uri.split("://", 1)
        credentials, host = rest.split("@", 1)
        if ":" in credentials:
            username = credentials.split(":")[0]
            return f"{protocol}://{username}:***@{host}"
    return uri


def cleanup_file(file_path: Optional[str]) -> None:
    """Clean up temporary files."""
    if file_path and os.path.exists(file_path):
        os.remove(file_path)
