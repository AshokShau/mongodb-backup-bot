import os
import re
import uuid
from typing import Optional, Union, Any

from pytdbot import Client, types
from pytdbot.types import Error, Ok

from src.modules.utils import (
    Filter,
    extract_argument,
    get_db_list,
    run_mongodump,
    run_mongorestore,
)

backup_jobs = {}

def extract_mongo_uri(text: str) -> Optional[str]:
    """Extract MongoDB URI from text."""
    uri_pattern = r"(mongodb(?:\+srv)?:\/\/[a-zA-Z0-9\-._~:\/?#[\]@!$&'()*+,;=]+)"
    match = re.search(uri_pattern, text)
    return match[0] if match else None

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

    db_list = await get_db_list(uri)
    if isinstance(db_list, types.Error):
        await msg.reply_text(f"❌ Could not connect to MongoDB: {db_list.message}")
        return None

    if not db_list:
        await msg.reply_text("🤷 No databases found to back up.")
        return None

    job_id = str(uuid.uuid4())
    sender = msg.sender_id
    if not isinstance(sender, types.MessageSenderUser):
        await msg.reply_text("❌ This command can only be used by a user.")
        return None

    db_mapping = {str(i): db for i, db in enumerate(db_list)}
    backup_jobs[job_id] = {
        "uri": uri,
        "flags": flags,
        "chat_id": msg.chat_id,
        "user_id": sender.user_id,
        "db_mapping": db_mapping,
        "reverse_mapping": {v: k for k, v in db_mapping.items()}
    }

    format_db = "json" if "{json}" in flags and "{gz}" not in flags else "gz"

    buttons = [
        [types.InlineKeyboardButton(
            text=db, 
            type=types.InlineKeyboardButtonTypeCallback(
                data=f"backup_{job_id}_{i}_{format_db}".encode()
            )
        )]
        for i, db in db_mapping.items()
    ]
    buttons.append(
        [
            types.InlineKeyboardButton(
                text="Backup All", 
                type=types.InlineKeyboardButtonTypeCallback(
                    data=f"backup_{job_id}_all_{format_db}".encode()
                )
            )
        ]
    )
    buttons.append(
        [types.InlineKeyboardButton(
            text="Cancel", 
            type=types.InlineKeyboardButtonTypeCallback(
                data=f"backup_{job_id}_cancel".encode()
            )
        )]
    )

    keyboard = types.ReplyMarkupInlineKeyboard(buttons)
    await msg.reply_text("👇 Select a database to back up:", reply_markup=keyboard)
    return None


@Client.on_updateNewCallbackQuery()
async def on_callback_query(_: Client, cq: types.UpdateNewCallbackQuery) -> None | Error | Ok | Any:
    data = cq.payload.data.decode()
    if not data or not data.startswith("backup_"):
        return None

    parts = data.split("_")
    if len(parts) < 3 or len(parts) > 4:
        return await cq.answer("Invalid callback data", show_alert=True)

    job_id = parts[1]
    db_key = parts[2]
    format_db = parts[3] if len(parts) > 3 else ""

    job_info = backup_jobs.get(job_id)
    if not job_info or job_info["user_id"] != cq.sender_user_id:
        return await cq.answer("This is not for you!", show_alert=True)

    if db_key in ["all", "cancel"]:
        db_name = db_key
    else:
        db_name = job_info.get("db_mapping", {}).get(db_key)
        if not db_name:
            return await cq.answer("Invalid database selection", show_alert=True)

    if db_name == "cancel":
        if job_id in backup_jobs:
            del backup_jobs[job_id]
        return await cq.edit_message_text("🚫 Backup canceled.")

    await cq.edit_message_text(f"📦 Creating backup for <b>{db_name}</b>...", parse_mode="html")

    db_to_backup = db_name if db_name != "all" else None
    backup_path = await run_mongodump(
        job_info["uri"], format_db=format_db, db_name=db_to_backup
    )

    if isinstance(backup_path, types.Error):
        await cq.edit_message_text(f"❌ Backup failed: {backup_path.message}")
    else:
        msg = await cq.getMessage()
        if isinstance(msg, types.Error):
            return await cq.edit_message_text(f"❌ Backup failed: {msg.message}")

        await send_backup_file(
            msg, job_info["uri"], format_db, backup_path, db_name
        )
        await msg.delete()

    if job_id in backup_jobs:
        del backup_jobs[job_id]
    return None


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
        await msg.reply_text(
            "❌ Please reply to a valid MongoDB backup file (.gz or .json)."
        )
        return

    await process_import(msg, reply, target_uri)


async def process_import(
    msg: types.Message, reply: types.Message, target_uri: str
) -> None:
    """Process the MongoDB import operation."""
    status_msg = await msg.reply_text("📦 Importing MongoDB backup...")

    backup_path = await reply.download()
    if isinstance(backup_path, types.Error):
        await status_msg.edit_text(
            f"❌ Failed to download backup file: {backup_path.message}"
        )
        return

    result = await run_mongorestore(target_uri, backup_path.path)
    if isinstance(result, types.Error):
        await status_msg.edit_text(f"❌ MongoDB import failed: {result.message}")
        return

    await status_msg.edit_text(
        f"✅ MongoDB import complete to <code>{sanitize_uri(target_uri)}</code>."
    )
    cleanup_file(backup_path.path)


def is_valid_backup_file(filename: str) -> bool:
    """Check if file is a valid MongoDB backup."""
    return filename.endswith((".gz", ".json", ".zip"))


async def send_backup_file(
    msg: types.Message,
    uri: str,
    format_db: str,
    backup_path: str,
    db_name: Optional[str] = None,
) -> Union[types.Message, types.Error]:
    """Send the backup file to the user."""
    db_info = (
        f"<b>Database:</b> <code>{db_name}</code>\n"
        if db_name is not None
        else "<b>Database:</b> <code>All databases</code>\n"
    )
    return await msg.reply_document(
        document=types.InputFileLocal(backup_path),
        caption=(
            f"✅ MongoDB backup complete.\n\n"
            f"<b>URI:</b> <code>{sanitize_uri(uri)}</code>\n"
            f"{db_info}"
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
