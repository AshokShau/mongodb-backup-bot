import os
import re
import subprocess

from pytdbot import Client, types

from src.modules.utils import Filter, extract_argument, run_mongodump


@Client.on_message(filters=Filter.command("mongo"))
async def mongo_cmd(_: Client, msg: types.Message) -> None:
    args = extract_argument(msg.text)
    if not args:
        await msg.reply_text("❌ Please provide a MongoDB URI.")
        return None

    uri_pattern = r"(mongodb(?:\+srv)?:\/\/[a-zA-Z0-9\-._~:\/?#[\]@!$&'()*+,;=]+)"
    match = re.search(uri_pattern, args)

    if not match:
        await msg.reply_text("❌ Invalid or missing MongoDB URI.")
        return None

    uri = match.group(0)
    flags = args.lower()

    if "{import}" in flags:
        return await import_mongo(msg, uri)

    if "{json}" in flags and "{gz}" not in flags:
        format_db = "json"
    else:
        format_db = "gz"

    reply = await msg.reply_text(f"📦 Creating backup in <b>{format_db.upper()}</b> format...")

    backup_path = await run_mongodump(uri, format_db=format_db)
    if isinstance(backup_path, types.Error):
        await reply.edit_text(text=f"❌ Backup failed: {backup_path.message}")
        return None

    await msg.reply_document(
        document=types.InputFileLocal(backup_path),
        caption=f"✅ MongoDB backup complete.\n\n<b>URI:</b> <code>{uri}</code>\n<b>Format:</b> <code>{format_db.upper()}</code>",
        parse_mode="html",
    )

    if os.path.exists(backup_path):
        os.remove(backup_path)
    await reply.delete()
    return None


async def import_mongo(msg: types.Message, target_uri: str) -> None:
    reply = await msg.getRepliedMessage() if msg.reply_to_message_id else None
    if not reply or isinstance(reply, types.Error):
        await msg.reply_text("❌ Please reply to a MongoDB backup file.")
        return None

    if not isinstance(reply.content, types.MessageDocument):
        await msg.reply_text("❌ Please reply to a MongoDB backup file.")
        return None

    file_name = reply.content.document.file_name
    if not file_name.endswith(".gz") and not file_name.endswith(".json"):
        await msg.reply_text("❌ Please reply to a MongoDB backup file.")
        return None

    await msg.reply_text("📦 Importing MongoDB backup...")
    backup_path = await reply.download()
    if isinstance(backup_path, types.Error):
        await msg.reply_text(f"❌ Failed to download backup file: {backup_path.message}")
        return None

    path = backup_path.path

    if path.endswith(".gz"):
        restore_command = [
            "mongorestore",
            "--uri", target_uri,
            "--archive", path,
            "--gzip",
        ]
    elif path.endswith(".json"):
        restore_command = [
            "mongorestore",
            "--uri", target_uri,
            "--archive", path,
        ]
    else:
        await msg.reply_text("❌ Unsupported backup format. Please provide a gzipped or JSON backup.")
        return None

    process = subprocess.Popen(restore_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = process.communicate()

    if process.returncode != 0:
        await msg.reply_text(f"❌ Import failed: {stderr.decode()}")
        return None

    await msg.reply_text(f"✅ MongoDB import complete to <code>{target_uri}</code>.")
    if os.path.exists(path):
        os.remove(path)

    return None
