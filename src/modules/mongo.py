import os
import re
import uuid
from dataclasses import dataclass
from typing import Optional, Union, Any, Dict

from pytdbot import Client, types
from pytdbot.types import Error, Ok

from src.modules.utils import (
    Filter,
    extract_argument,
    get_db_list,
    run_mongodump,
    run_mongorestore,
    drop_all_dbs,
)
from pytdbot.exception import StopHandlers

from src.config import DATABASES_PER_PAGE


@dataclass
class CallbackData:
    action: str
    job_id: str
    page: int = 0
    format_db: str = 'gz'
    db_index: Optional[str] = None


backup_jobs = {}


def build_pagination_keyboard(
        db_mapping: Dict[str, str], job_id: str, format_db: str, page: int = 0
) -> types.ReplyMarkupInlineKeyboard:
    """Generate a paginated keyboard for database selection.

    Args:
        db_mapping: Dictionary mapping database indexes to names
        job_id: Unique identifier for the backup job
        format_db: Backup format ('json' or 'gz')
        page: Current page number (0-based)

    Returns:
        ReplyMarkupInlineKeyboard with paginated database buttons
    """
    total_dbs = len(db_mapping)
    if not total_dbs:
        return types.ReplyMarkupInlineKeyboard([[]])

    max_page = (total_dbs - 1) // DATABASES_PER_PAGE
    page = max(0, min(page, max_page))

    start_index = page * DATABASES_PER_PAGE
    end_index = min(start_index + DATABASES_PER_PAGE, total_dbs)
    db_page = list(db_mapping.items())[start_index:end_index]

    buttons = []
    row = []
    for i, db in db_page:
        row.append(
            types.InlineKeyboardButton(
                text=db,
                type=types.InlineKeyboardButtonTypeCallback(
                    data=f"backup_{job_id}_{i}_{format_db}".encode()
                ),
            )
        )
        if len(row) == 2:
            buttons.append(row)
            row = []

    if row:
        buttons.append(row)

    pagination_buttons = []
    if page > 0:
        pagination_buttons.append(
            types.InlineKeyboardButton(
                text="< Prev",
                type=types.InlineKeyboardButtonTypeCallback(
                    data=f"backup_{job_id}_prev_{page - 1}_{format_db}".encode()
                ),
            )
        )

    total_pages = (total_dbs + DATABASES_PER_PAGE - 1) // DATABASES_PER_PAGE
    if total_pages > 1:
        pagination_buttons.append(
            types.InlineKeyboardButton(
                text=f"{page + 1}/{total_pages}",
                type=types.InlineKeyboardButtonTypeCallback(data=b"noop"),
            )
        )

    if end_index < total_dbs:
        pagination_buttons.append(
            types.InlineKeyboardButton(
                text="Next >",
                type=types.InlineKeyboardButtonTypeCallback(
                    data=f"backup_{job_id}_next_{page + 1}".encode()
                ),
            )
        )

    if pagination_buttons:
        buttons.append(pagination_buttons)

    buttons.extend(
        (
            [
                types.InlineKeyboardButton(
                    text="Backup All",
                    type=types.InlineKeyboardButtonTypeCallback(
                        data=f"backup_{job_id}_all_{format_db}".encode()
                    ),
                )
            ],
            [
                types.InlineKeyboardButton(
                    text="Back to Menu",
                    type=types.InlineKeyboardButtonTypeCallback(
                        data=f"backup_{job_id}_menuBack".encode()
                    ),
                )
            ],
        )
    )
    return types.ReplyMarkupInlineKeyboard(buttons)


def build_menu_keyboard(job_id: str) -> types.ReplyMarkupInlineKeyboard:
    """Generate the main menu keyboard."""
    return types.ReplyMarkupInlineKeyboard([
        [
            types.InlineKeyboardButton(
                text="Backup All",
                type=types.InlineKeyboardButtonTypeCallback(
                    data=f"backup_{job_id}_mainAll".encode()
                )
            ),
            types.InlineKeyboardButton(
                text="Single DB",
                type=types.InlineKeyboardButtonTypeCallback(
                    data=f"backup_{job_id}_mainSingle".encode()
                )
            )
        ],
        [
            types.InlineKeyboardButton(
                text="Wipe DB / Delete All",
                type=types.InlineKeyboardButtonTypeCallback(
                    data=f"backup_{job_id}_mainDelete".encode()
                )
            )
        ],
        [
            types.InlineKeyboardButton(
                text="Cancel",
                type=types.InlineKeyboardButtonTypeCallback(
                    data=f"backup_{job_id}_menuCancel".encode()
                )
            )
        ]
    ])


def build_delete_confirm_keyboard(job_id: str) -> types.ReplyMarkupInlineKeyboard:
    """Generate confirmation keyboard for deleting all databases."""
    return types.ReplyMarkupInlineKeyboard([
        [
            types.InlineKeyboardButton(
                text="Yes, Delete Everything",
                type=types.InlineKeyboardButtonTypeCallback(
                    data=f"backup_{job_id}_confirmDelete".encode()
                )
            )
        ],
        [
            types.InlineKeyboardButton(
                text="No, Cancel",
                type=types.InlineKeyboardButtonTypeCallback(
                    data=f"backup_{job_id}_menuBack".encode()
                )
            )
        ]
    ])


def extract_mongo_uri(text: str) -> Optional[str]:
    """Extract MongoDB URI from text."""
    uri_pattern = r"(mongodb(?:\+srv)?:\/\/[a-zA-Z0-9\-._~:\/?#[\]@!$&'()*+,;=]+)"
    match = re.search(uri_pattern, text)
    return match[0] if match else None


async def _handle_mongo_command(_: Client, msg: types.Message, is_regex: bool = False) -> None:
    """Handle MongoDB backup/restore commands.

    Args:
        _: The client instance
        msg: The message object
        is_regex: Whether this was triggered by a regex pattern
    """
    args = msg.text if is_regex else extract_argument(msg.text)
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

    job_id = str(uuid.uuid4())
    sender = msg.sender_id
    if not isinstance(sender, types.MessageSenderUser):
        await msg.reply_text("❌ This command can only be used by a user.")
        return None

    backup_jobs[job_id] = {
        "uri": uri,
        "flags": flags,
        "chat_id": msg.chat_id,
        "user_id": sender.user_id,
        "db_mapping": {},
        "reverse_mapping": {}
    }

    keyboard = build_menu_keyboard(job_id)
    await msg.reply_text("👇 Choose an action:", reply_markup=keyboard)
    return None


@Client.on_message(filters=Filter.command("mongo"))
async def mongo_cmd(_: Client, msg: types.Message) -> None:
    """Handle /mongo command."""
    await _handle_mongo_command(_, msg, is_regex=False)
    raise StopHandlers


@Client.on_message(filters=Filter.regex(r'^\s*(?:mongo|mongodb)\b'), position=-1)
async def mongo_regex(_: Client, msg: types.Message) -> None:
    """Handle messages starting with 'mongo' or 'mongodb'."""
    await _handle_mongo_command(_, msg, is_regex=True)
    raise StopHandlers


@Client.on_updateNewCallbackQuery()
async def on_callback_query(_: Client, cq: types.UpdateNewCallbackQuery) -> None | Error | Ok | Any:
    data = cq.payload.data.decode()
    if not data or not data.startswith("backup_"):
        return None

    if data == "noop":
        return await cq.answer("Invalid action !", show_alert=True)

    parts = data.split("_")
    job_id = parts[1]

    job_info = backup_jobs.get(job_id)
    if not job_info or job_info["user_id"] != cq.sender_user_id:
        return await cq.answer("This is not for you or job not found!", show_alert=True)

    action = parts[2]
    flags = job_info.get("flags", "")
    format_db = "json" if "{json}" in flags and "{gz}" not in flags else "gz"

    # Handle Menu Actions
    if action == "mainAll":
        # Trigger backup all
        db_name = "all"
        await cq.edit_message_text(f"📦 Creating backup for <b>All Databases</b>...", parse_mode="html")

    elif action == "mainSingle":
        db_list = await get_db_list(job_info["uri"])
        if isinstance(db_list, types.Error):
            return await cq.answer(f"❌ Could not connect: {db_list.message}", show_alert=True)

        if not db_list:
            return await cq.answer("🤷 No databases found.", show_alert=True)

        db_mapping = {str(i): db for i, db in enumerate(db_list)}
        job_info["db_mapping"] = db_mapping
        job_info["reverse_mapping"] = {v: k for k, v in db_mapping.items()}

        keyboard = build_pagination_keyboard(db_mapping, job_id, format_db, page=0)
        return await cq.edit_message_text("👇 Select a database to back up:", reply_markup=keyboard)

    elif action == "mainDelete":
        keyboard = build_delete_confirm_keyboard(job_id)
        return await cq.edit_message_text(
            "⚠️ <b>DANGER ZONE</b> ⚠️\n\nAre you sure you want to delete ALL databases? This action cannot be undone!",
            parse_mode="html", reply_markup=keyboard)

    elif action == "confirmDelete":
        await cq.edit_message_text("🗑️ Deleting all databases... Please wait.")
        result = await drop_all_dbs(job_info["uri"])
        if isinstance(result, types.Error):
            await cq.edit_message_text(f"❌ Deletion failed: {result.message}")
        else:
            await cq.edit_message_text("✅ All databases have been deleted.")

        if job_id in backup_jobs:
            del backup_jobs[job_id]
        return None

    elif action == "menuCancel":
        if job_id in backup_jobs:
            del backup_jobs[job_id]
        return await cq.edit_message_text("🚫 Operation canceled.")

    elif action == "menuBack":
        keyboard = build_menu_keyboard(job_id)
        return await cq.edit_message_text("👇 Choose an action:", reply_markup=keyboard)


    elif action in ["next", "prev"]:
        page = int(parts[3])
        keyboard = build_pagination_keyboard(
            job_info["db_mapping"], job_id, format_db, page
        )
        return await cq.edit_message_reply_markup(reply_markup=keyboard)

    elif action == "all":
        db_name = "all"
        await cq.edit_message_text(f"📦 Creating backup for <b>All Databases</b>...", parse_mode="html")

    else:
        db_name = job_info.get("db_mapping", {}).get(action)
        if not db_name:
            if action not in ["mainAll", "all"]:
                return await cq.answer("Invalid database selection", show_alert=True)

        if action not in ["mainAll", "all"]:
            await cq.edit_message_text(f"📦 Creating backup for <b>{db_name}</b>...", parse_mode="html")

    if len(parts) > 3 and action not in ["next", "prev"]:
        format_db = parts[3]

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
