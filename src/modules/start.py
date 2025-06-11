#  Copyright (c) 2025 AshokShau
#  Licensed under the GNU AGPL v3.0: https://www.gnu.org/licenses/agpl-3.0.html
#  Part of the TgMusicBot project. All rights reserved where applicable.

import time
from datetime import datetime

from pytdbot import Client, types

from src import __version__, StartTime
from src.modules.utils import Filter


@Client.on_message(filters=Filter.command(["start", "help"]))
async def start_cmd(c: Client, message: types.Message):
    text = (
        "👋 <b>Welcome to the MongoDB Backup & Restore Bot!</b>\n\n"
        "This bot lets you <b>create</b> and <b>import</b> MongoDB backups easily using the <code>/mongo</code> command.\n\n"
        "🛠️ <b>Commands</b>:\n"
        "<code>/mongo &lt;uri&gt; {format}</code> - Create a backup of the given MongoDB URI.\n"
        "<code>/mongo &lt;uri&gt; {import}</code> - Import a backup (must be used in reply to a .gz or .zip file).\n\n"
        "📦 <b>Supported Formats</b>:\n"
        "• <code>{gz}</code> — Create a compressed backup in .gz format (default).\n"
        "• <code>{json}</code> — Create a plain JSON format backup.\n\n"
        "📥 <b>Import Example</b>:\n"
        "1. Reply to a backup file with:\n"
        "<code>/mongo &lt;destination_uri&gt; {import}</code>\n\n"
        "📤 <b>Export Example</b>:\n"
        "<code>/mongo mongodb://localhost:27017 {gz}</code>\n\n"
        "If both <code>{gz}</code> and <code>{json}</code> are given, <code>{gz}</code> will be used.\n\n"
        "💡 <b>Note:</b> Your MongoDB URI should be valid.\n\n"
        "Made with ❤️ using <b>pytdbot</b>"
    )

    reply = await message.reply_text(text, parse_mode="html", disable_web_page_preview=True)
    if isinstance(reply, types.Error):
        c.logger.warning(f"Error sending start/help message: {reply.message}")
    return None


@Client.on_message(filters=Filter.command("ping"))
async def ping_cmd(client: Client, message: types.Message) -> None:
    start_time = time.monotonic()
    reply_msg = await message.reply_text("🏓 Pinging...")
    latency = (time.monotonic() - start_time) * 1000  # in ms
    uptime = datetime.now() - StartTime
    uptime_str = str(uptime).split(".")[0]

    response = (
        "📊 <b>System Performance Metrics</b>\n\n"
        f"⏱️ <b>Bot Latency:</b> <code>{latency:.2f} ms</code>\n"
        f"🕒 <b>Uptime:</b> <code>{uptime_str}</code>\n"
        f"🤖 <b>Bot Version:</b> <code>{__version__}</code>"
    )
    done = await reply_msg.edit_text(response, disable_web_page_preview=True)
    if isinstance(done, types.Error):
        client.logger.warning(f"Error sending message: {done}")
    return None

@Client.on_message(filters=Filter.command("privacy"))
async def privacy_handler(_: Client, message: types.Message):
    await message.reply_text(
        "🔒 <b>Privacy Policy</b>\n\n"
        "This bot does <b>not store</b> any of your data.\n"
        "No logs, no backups, no user tracking.\n\n"
        "All operations (backup/import) are handled <i>in-memory</i> and deleted after use.\n"
        "Even the database itself isn’t connected — everything is local.\n\n"
        "🛠️ <b>Open Source</b>: You can verify this at:\n"
        "🔗 <a href=\"https://github.com/AshokShau/TgMongoBot\">github.com/AshokShau/TgMongoBot</a>",
        parse_mode="html",
        disable_web_page_preview=True
    )
