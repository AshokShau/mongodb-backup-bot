#  Copyright (c) 2025 AshokShau
#  Licensed under the GNU AGPL v3.0: https://www.gnu.org/licenses/agpl-3.0.html
#  Part of the TgMusicBot project. All rights reserved where applicable.


import asyncio
import inspect
import io
import os
import re
import sys
import time
import traceback
import uuid
import humanize
from html import escape
from typing import Any, Optional, Tuple, Union

from humanize import naturalsize
from meval import meval
from pytdbot import Client, types

from src.modules.utils import Filter, extract_argument
from .. import config


def format_exception(
    exp: BaseException, tb: Optional[list[traceback.FrameSummary]] = None
) -> str:
    """
    Formats an exception traceback as a string, similar to the Python interpreter.
    """

    if tb is None:
        tb = traceback.extract_tb(exp.__traceback__)

    # Replace absolute paths with relative paths
    cwd = os.getcwd()
    for frame in tb:
        if cwd in frame.filename:
            frame.filename = os.path.relpath(frame.filename)

    stack = "".join(traceback.format_list(tb))
    msg = str(exp)
    if msg:
        msg = f": {msg}"

    return f"Traceback (most recent call last):\n{stack}{type(exp).__name__}{msg}"


@Client.on_message(filters=Filter.command("ev"))
async def exec_eval(c: Client, m: types.Message) -> None:
    """
    Run python code.
    """
    user_id = m.from_id
    if user_id != config.OWNER_ID:
        return None

    text = m.text.split(None, 1)
    if len(text) <= 1:
        reply = await m.reply_text("Usage: /eval &lt code &gt")
        if isinstance(reply, types.Error):
            c.logger.warning(reply.message)
        return None

    code = text[1]
    out_buf = io.StringIO()

    async def _eval() -> Tuple[str, Optional[str]]:
        async def send(
            *args: Any, **kwargs: Any
        ) -> Union["types.Error", "types.Message"]:
            return await m.reply_text(*args, **kwargs)

        def _print(*args: Any, **kwargs: Any) -> None:
            if "file" not in kwargs:
                kwargs["file"] = out_buf
                return print(*args, **kwargs)
            return None

        eval_vars = {
            "loop": c.loop,
            "client": c,
            "stdout": out_buf,
            "c": c,
            "m": m,
            "msg": m,
            "types": types,
            "send": send,
            "print": _print,
            "inspect": inspect,
            "os": os,
            "re": re,
            "sys": sys,
            "traceback": traceback,
            "uuid": uuid,
            "io": io,
        }

        try:
            return "", await meval(code, globals(), **eval_vars)
        except Exception as e:
            first_snip_idx = -1
            tb = traceback.extract_tb(e.__traceback__)
            for i, frame in enumerate(tb):
                if frame.filename == "<string>" or frame.filename.endswith("ast.py"):
                    first_snip_idx = i
                    break

            # Re-raise exception if it wasn't caused by the snippet
            if first_snip_idx == -1:
                raise e

            # Return formatted stripped traceback
            stripped_tb = tb[first_snip_idx:]
            formatted_tb = format_exception(e, tb=stripped_tb)
            return "⚠️ Error:\n\n", formatted_tb

    prefix, result = await _eval()

    if not out_buf.getvalue() or result is not None:
        print(result, file=out_buf)

    out = out_buf.getvalue()
    if out.endswith("\n"):
        out = out[:-1]

    result = f"""{prefix}<b>In:</b>
<pre language="python">{escape(code)}</pre>
<b>ᴏᴜᴛ:</b>
<pre language="python">{escape(out)}</pre>"""

    if len(result) > 2000:
        filename = f"database/{uuid.uuid4().hex}.txt"
        with open(filename, "w", encoding="utf-8") as file:
            file.write(out)

        caption = f"""{prefix}<b>ᴇᴠᴀʟ:</b>
    <pre language="python">{escape(code)}</pre>
    """
        reply = await m.reply_document(
            document=types.InputFileLocal(filename),
            caption=caption,
            disable_notification=True,
            parse_mode="html",
        )
        if isinstance(reply, types.Error):
            c.logger.warning(reply.message)

        if os.path.exists(filename):
            os.remove(filename)

        return None

    reply = await m.reply_text(str(result), parse_mode="html")
    if isinstance(reply, types.Error):
        c.logger.warning(reply.message)
    return None

async def run_shell_command(cmd: str, timeout: int = 60) -> tuple[str, str, int]:
    """Execute shell command and return stdout, stderr, returncode."""
    process = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    try:
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        process.kill()
        await process.wait()
        return "", f"Command timed out after {timeout} seconds", -1

    return stdout.decode().strip(), stderr.decode().strip(), process.returncode


async def shellrunner(message: types.Message) -> types.Ok | types.Error | types.Message:
    text = message.text.split(None, 1)
    if len(text) <= 1:
        reply = await message.reply_text("Usage: /sh &lt cmd &gt")
        return reply if isinstance(reply, types.Error) else types.Ok()
    command = text[1]
    """
    # Security check - prevent dangerous commands
    if any(blocked in command.lower() for blocked in [
        'rm -rf', 'sudo', 'dd ', 'mkfs', 'fdisk',
        ':(){:|:&};:', 'chmod 777', 'wget', 'curl'
    ]):
        return await message.reply_text("⚠️ Dangerous command blocked!")
    """

    try:
        # Execute single command or multiple commands separated by newlines
        if "\n" in command:
            commands = [cmd.strip() for cmd in command.split("\n") if cmd.strip()]
            output_parts = []

            for cmd in commands:
                stdout, stderr, retcode = await run_shell_command(cmd)

                output_parts.append(f"<b>🚀 Command:</b> <code>{cmd}</code>")
                if stdout:
                    output_parts.append(f"<b>📤 Output:</b>\n<pre>{stdout}</pre>")
                if stderr:
                    output_parts.append(f"<b>❌ Error:</b>\n<pre>{stderr}</pre>")
                output_parts.append(f"<b>🔢 Exit Code:</b> <code>{retcode}</code>\n")

            output = "\n".join(output_parts)
        else:
            stdout, stderr, retcode = await run_shell_command(command)

            output = f"<b>🚀 Command:</b> <code>{command}</code>\n"
            if stdout:
                output += f"<b>📤 Output:</b>\n<pre>{stdout}</pre>\n"
            if stderr:
                output += f"<b>❌ Error:</b>\n<pre>{stderr}</pre>\n"
            output += f"<b>🔢 Exit Code:</b> <code>{retcode}</code>"

        if not output.strip():
            output = "<b>📭 No output was returned</b>"

        if len(output) <= 2000:
            return await message.reply_text(str(output), parse_mode="html")

        filename = f"database/{uuid.uuid4().hex}.txt"
        with open(filename, "w", encoding="utf-8") as file:
            file.write(output)
        reply = await message.reply_document(
            document=types.InputFileLocal(filename),
            caption="📁 Output too large, sending as file:",
            disable_notification=True,
            parse_mode="html",
        )
        if isinstance(reply, types.Error):
           return reply

        if os.path.exists(filename):
            os.remove(filename)

        return types.Ok()
    except Exception as e:
        return await message.reply_text(
            f"⚠️ <b>Error:</b>\n<pre>{str(e)}</pre>", parse_mode="html"
        )


@Client.on_message(filters=Filter.command("sh"))
async def shell_command(c: Client, m: types.Message) -> None:


    done = await shellrunner(m)
    if isinstance(done, types.Error):
        c.logger.warning(done.message)
        return None
    return None

@Client.on_message(filters=Filter.command("dl"))
async def dl_handler(c: Client, msg: types.Message) -> None:
    if msg.from_id != config.OWNER_ID:
        return None

    reply = await msg.getRepliedMessage() if msg.reply_to_message_id else None
    if not reply:
        await msg.reply_text("❌ Reply to a media/file message to download.")
        return None

    status = await msg.reply_text("⏳ Starting download...")

    start = time.time()
    result = await reply.download()
    if isinstance(result, types.Error):
        await status.edit_text(f"❌ Download failed: {result.message}")
        return None

    end = time.time()
    duration = end - start
    downloaded_bytes = result.downloaded_size or 0

    size_h = naturalsize(downloaded_bytes, binary=True)
    speed_bps = downloaded_bytes / duration if duration > 0 else 0
    speed_h = naturalsize(speed_bps, binary=True) + "/s"
    time_h = f"{duration:.2f}s"

    text = (
        f"Downloaded: {size_h}\n"
        f"Time: {time_h}\n"
        f"Avg Speed: {speed_h}\n"
        f"Result: {str(result)}\n"
    )

    await status.edit_text(text)
    return None

@Client.on_message(filters=Filter.command("ul"))
async def ul_handler(c: Client, msg: types.Message) -> None:
    if msg.from_id != config.OWNER_ID:
        return None

    args = extract_argument(msg.text)
    if not args:
        await msg.reply_text("No file path provided.")
        return None

    if not os.path.exists(args):
        await msg.reply_text("File not found on server.")
        return None

    file_size = os.path.getsize(args)
    file_size_h = naturalsize(file_size, binary=True)

    status = await msg.reply_text(
        f"Starting upload...\n"
        f"File: {args}\n"
        f"Size: {file_size_h}"
    )

    start = time.time()
    ok = await c.sendDocument(
        chat_id=msg.chat_id,
        document=types.InputFileLocal(args),
        caption="📁 File uploaded successfully",
        disable_notification=True,
    )
    if isinstance(ok, types.Error):
        await status.edit_text(f"Upload failed: {ok.message}")
        return None

    end = time.time()
    duration = end - start
    speed_bps = file_size / duration if duration > 0 else 0
    speed_h = naturalsize(speed_bps, binary=True) + "/s"
    await status.edit_text(
        "Upload Completed\n\n"
        f"File:{args}\n"
        f"Size:{file_size_h}\n"
        f"Time {duration:.2f}s\n"
        f"Avg Upload Speed: {speed_h}\n"
    )
    return None
