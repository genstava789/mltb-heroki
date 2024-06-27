from io import BytesIO
from pyrogram.filters import command
from pyrogram.handlers import MessageHandler, EditedMessageHandler
from pyrogram.types import Message

from bot import bot 
from bot.helper.ext_utils.bot_utils import cmd_exec, new_task
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.message_utils import sendMessage, sendFile


@new_task
async def shell(_, message: Message):
    cmd = message.text.split(maxsplit=1)
    if len(cmd) == 1:
        return await sendMessage(
            message=message,
            text="<b>Tidak ada perintah untuk dieksekusi!</b>",
        )
    
    cmd = cmd[1]
    result = str()
    caption = str()
    caption += f"<b>Input :</b>\n<pre language='bash'>{cmd}</pre>"
    
    stdout, stderr, _ = await cmd_exec(cmd, shell=True)
    
    if len(stdout) != 0:
        result += stdout

    if len(stderr) != 0:
        result += stderr

    if len(result) > 4096:
        with BytesIO(str.encode(result)) as file:
            file.name = "Output.txt"
            await sendFile(
                message=message,
                file=file,
                caption=caption,
            )

    elif len(result) != 0:
        caption += f"\n\n<b>Output :</b>\n<pre language='bash'>{result}</pre>"

        await sendMessage(
            message=message,
            text=caption,
        )

    else:
        await sendMessage(
            message=message, 
            text="<b>Tidak ada balasan!</b>",
        )


bot.add_handler(
    MessageHandler(
        shell, 
        filters=command(
            BotCommands.ShellCommand
        ) & CustomFilters.owner
    )
)

bot.add_handler(
    EditedMessageHandler(
        shell, 
        filters=command(
            BotCommands.ShellCommand
        ) & CustomFilters.owner
    )
)