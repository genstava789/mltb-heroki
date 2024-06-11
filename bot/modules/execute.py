from aiofiles import open as aiopen
from contextlib import redirect_stdout
from io import StringIO, BytesIO
from os import path as ospath, getcwd, chdir
from pyrogram.filters import command
from pyrogram.handlers import MessageHandler
from pyrogram.types import Message
from textwrap import indent
from traceback import format_exc

from bot import LOGGER, bot
from bot.helper.ext_utils.bot_utils import sync_to_async, new_task
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import sendFile, sendMessage


nameSpace = dict()

@new_task
async def execute(_, message: Message):
    cmd = message.text.split(maxsplit=1)

    if len(cmd) == 1:
        await sendMessage(
            message=message, 
            text="<b>Tidak ada perintah untuk dieksekusi!</b>",
        )
        return
    
    await sendResult(
        message=message,
        result=(await doExeCute(message=message, function="exec")),
    )


@new_task
async def aioexecute(_, message: Message):
    cmd = message.text.split(maxsplit=1)

    if len(cmd) == 1:
        await sendMessage(
            message=message, 
            text="<b>Tidak ada perintah untuk dieksekusi!</b>",
        )
        return
    
    await sendResult(
        message=message,
        result=(await doExeCute(message=message, function="aexec")),
    )


async def clear(_, message: Message):
    global nameSpace
    if message.chat.id in nameSpace:
        del nameSpace[message.chat.id]
    
    await sendMessage(
        message=message,
        text="<b>Local berhasil dihapus!</b>",
    )

async def sendResult(message: Message, result: str):
    caption = str()
    caption += f"<b>Input :</b>\n<pre language='python'>{message.text.split(maxsplit=1)[-1]}</pre>"

    if len(caption + str(result)) > 4096:
        with BytesIO(str.encode(result)) as file:
            file.name = "Output.txt"
            await sendFile(
                message=message,
                file=file,
                caption=caption,
            )
    
    else:
        caption += f"\n\n<b>Output :</b>\n<pre language='json'>{result}</pre>"
        
        await sendMessage(
            message=message,
            text=caption,
        )


async def doExeCute(message: Message, function: str):
    cmd = message.text.split(maxsplit=1)
    cmd = cmd[1]
    
    if (
        cmd.startswith("```")
        and cmd.endswith("```")
    ):
        cmd = "\n".join(cmd.split("\n")[1:-1])

    cmd = cmd.strip("` \n")
    stdout = StringIO()
    environment = nameSpaces(message=message)

    try:
        if function == "exec":
            exec(f"def func():\n{indent(text=cmd, prefix='  ')}", environment)
        
        else:
            exec(f"async def func():\n{indent(text=cmd, prefix='  ')}", environment)

    except Exception as error:
        return f"{error.__class__.__name__}: {error}"
    
    returnFunction = environment["func"]

    try:
        with redirect_stdout(stdout):
            functionResult = (
                await sync_to_async(returnFunction)
                if function == "exec"
                else await returnFunction()
            )
    
    except Exception:
        value = stdout.getvalue()
        
        return f"{value}{format_exc()}"

    else:
        value = stdout.getvalue()
        result = None

        if functionResult is None:
            if value:
                result = f"{value}"
            
            else:
                try:
                    result = f"{repr(await sync_to_async(eval, cmd, environment))}"

                except Exception:
                    pass
        
        else:
            result = f"{value}{functionResult}"
        
        if result:
            return result


def nameSpaces(message: Message):
    if message.chat.id not in nameSpace:
        nameSpace[message.chat.id] = {
            "__builtins__": globals()["__builtins__"],
            "bot": bot,
            "chat": message.chat,
            "message": message,
            "user": message.from_user or message.sender_chat,
        }

    return nameSpace[message.chat.id]


bot.add_handler(
    MessageHandler(
        execute, filters=command(
            BotCommands.ExecCommand
        ) & CustomFilters.owner
    )
)
bot.add_handler(
    MessageHandler(
        aioexecute, filters=command(
            BotCommands.AExecCommand
        ) & CustomFilters.owner
    )
)
bot.add_handler(
    MessageHandler(
        clear, filters=command(
            BotCommands.ClearLocalsCommand
        ) & CustomFilters.owner
    )
)
