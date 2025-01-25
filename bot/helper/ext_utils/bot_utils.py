from asyncio import (
    create_subprocess_exec,
    create_subprocess_shell,
    run_coroutine_threadsafe,
    sleep,
)
from asyncio.subprocess import PIPE
from concurrent.futures import ThreadPoolExecutor
from functools import partial, wraps
from httpx import AsyncClient

from bot import bot_loop, config_dict, user_data, LOGGER
from bot.helper.ext_utils.help_messages import (
    CLONE_HELP_DICT,
    MIRROR_HELP_DICT,
    YT_HELP_DICT,
)
from bot.helper.ext_utils.telegraph_helper import telegraph
from pyrogram.types import BotCommand
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.button_build import ButtonMaker


THREADPOOL = ThreadPoolExecutor(
    max_workers=1000
)
COMMAND_USAGE = {}

class setInterval:
    def __init__(self, interval, action, *args, **kwargs):
        self.interval = interval
        self.action = action
        self.task = bot_loop.create_task(self._set_interval(*args, **kwargs))

    async def _set_interval(self, *args, **kwargs):
        while True:
            await sleep(self.interval)
            await self.action(*args, **kwargs)

    def cancel(self):
        self.task.cancel()


def create_help_buttons():
    buttons = ButtonMaker()
    for name in list(MIRROR_HELP_DICT.keys())[1:]:
        buttons.ibutton(name, f"help mirror {name}")
    buttons.ibutton("Close", "help close")
    COMMAND_USAGE["mirror"] = [MIRROR_HELP_DICT["main"], buttons.build_menu(3)]
    buttons.reset()
    for name in list(YT_HELP_DICT.keys())[1:]:
        buttons.ibutton(name, f"help yt {name}")
    buttons.ibutton("Close", "help close")
    COMMAND_USAGE["yt"] = [YT_HELP_DICT["main"], buttons.build_menu(3)]
    buttons.reset()
    for name in list(CLONE_HELP_DICT.keys())[1:]:
        buttons.ibutton(name, f"help clone {name}")
    buttons.ibutton("Close", "help close")
    COMMAND_USAGE["clone"] = [CLONE_HELP_DICT["main"], buttons.build_menu(3)]


def bt_selection_buttons(id_):
    gid = id_[:12] if len(id_) > 25 else id_
    pincode = "".join([n for n in id_ if n.isdigit()][:4])
    buttons = ButtonMaker()
    BASE_URL = config_dict["BASE_URL"]
    if config_dict["WEB_PINCODE"]:
        buttons.ubutton("Pilih File", f"{BASE_URL}/app/files/{id_}")
        buttons.ibutton("Kode Pin", f"sel pin {gid} {pincode}")
    else:
        buttons.ubutton(
            "Pilih File", f"{BASE_URL}/app/files/{id_}?pin_code={pincode}"
        )
    buttons.ibutton("Selesai Memilih", f"sel done {gid} {id_}")
    buttons.ibutton("Batalkan", f"sel cancel {gid}")
    return buttons.build_menu(2)


async def get_telegraph_list(telegraph_content):
    path = [
        (
            await telegraph.create_page(
                title="Pencari KQRM Bot", content=content
            )
        )["path"]
        for content in telegraph_content
    ]
    if len(path) > 1:
        await telegraph.edit_telegraph(path, telegraph_content)
    buttons = ButtonMaker()
    buttons.ubutton("🔎 Lihat", f"https://telegra.ph/{path[0]}")
    return buttons.build_menu(1)


def arg_parser(items, arg_base):
    if not items:
        return
    bool_arg_set = {
        "-b",
        "-e",
        "-z",
        "-s",
        "-j",
        "-d",
        "-sv",
        "-ss",
        "-f",
        "-fd",
        "-fu",
        "-sync",
        "-ml",
    }
    t = len(items)
    i = 0
    arg_start = -1

    while i + 1 <= t:
        part = items[i]
        if part in arg_base:
            if arg_start == -1:
                arg_start = i
            if (
                i + 1 == t
                and part in bool_arg_set
                or part in ["-s", "-j", "-f", "-fd", "-fu", "-sync", "-ml"]
            ):
                arg_base[part] = True
            else:
                sub_list = []
                for j in range(i + 1, t):
                    item = items[j]
                    if item in arg_base:
                        if part in bool_arg_set and not sub_list:
                            arg_base[part] = True
                        break
                    sub_list.append(item)
                    i += 1
                if sub_list:
                    arg_base[part] = " ".join(sub_list)
        i += 1
    if "link" in arg_base and items[0] not in arg_base:
        link = []
        if arg_start == -1:
            link.extend(iter(items))
        else:
            link.extend(items[r] for r in range(arg_start))
        if link:
            arg_base["link"] = " ".join(link)


def getSizeBytes(size):
    size = size.lower()
    if size.endswith("mb"):
        size = size.split("mb")[0]
        size = int(float(size) * 1048576)
    elif size.endswith("gb"):
        size = size.split("gb")[0]
        size = int(float(size) * 1073741824)
    else:
        size = 0
    return size


async def get_content_type(url):
    try:
        async with AsyncClient() as client:
            response = await client.get(url, allow_redirects=True, verify=False)
            return response.headers.get("Content-Type")
    except Exception:
        return None


def update_user_ldata(id_, key, value):
    user_data.setdefault(id_, {})
    user_data[id_][key] = value


async def retry_function(func, *args, **kwargs):
    try:
        return await func(*args, **kwargs)
    except Exception:
        return await retry_function(func, *args, **kwargs)


async def cmd_exec(cmd, shell=False):
    if shell:
        proc = await create_subprocess_shell(cmd, stdout=PIPE, stderr=PIPE)
    else:
        proc = await create_subprocess_exec(*cmd, stdout=PIPE, stderr=PIPE)
    stdout, stderr = await proc.communicate()
    try:
        stdout = stdout.decode().strip()
    except Exception:
        stdout = "Unable to decode the response!"
    try:
        stderr = stderr.decode().strip()
    except Exception:
        stderr = "Unable to decode the error!"
    return stdout, stderr, proc.returncode


def new_task(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        return bot_loop.create_task(func(*args, **kwargs))

    return wrapper


async def sync_to_async(func, *args, wait=True, **kwargs):
    pfunc = partial(func, *args, **kwargs)
    future = bot_loop.run_in_executor(THREADPOOL, pfunc)
    return await future if wait else future


def async_to_sync(func, *args, wait=True, **kwargs):
    future = run_coroutine_threadsafe(func(*args, **kwargs), bot_loop)
    return future.result() if wait else future


def new_thread(func):
    @wraps(func)
    def wrapper(*args, wait=False, **kwargs):
        future = run_coroutine_threadsafe(func(*args, **kwargs), bot_loop)
        return future.result() if wait else future

    return wrapper

async def set_commands(client):
    try:
        bot_cmds = [
            BotCommand(
                BotCommands.MirrorCommand[0],
                f'or /{BotCommands.MirrorCommand[1]} Mirror [links/media/rclone_path]',
            ),
            BotCommand(
                BotCommands.LeechCommand[0],
                f'or /{BotCommands.LeechCommand[1]} Leech [links/media/rclone_path]',
            ),
            BotCommand(
                BotCommands.QbMirrorCommand[0],
                f'or /{BotCommands.QbMirrorCommand[1]} Mirror magnet/torrent using qBittorrent',
            ),
            BotCommand(
                BotCommands.QbLeechCommand[0],
                f'or /{BotCommands.QbLeechCommand[1]} Leech magnet/torrent using qBittorrent',
            ),
            BotCommand(
                BotCommands.NzbMirrorCommand[0],
                f'or /{BotCommands.NzbMirrorCommand[1]} Mirror nzb/usenet using sabnzbd',
            ),
            BotCommand(
                BotCommands.NzbLeechCommand[0],
                f'or /{BotCommands.NzbLeechCommand[1]} Leech nzb/usenet using sabnzbd to telegram',
            ),
            BotCommand(
                BotCommands.YtdlCommand[0],
                f'or /{BotCommands.YtdlCommand[1]} Mirror yt-dlp supported links via bot',
            ),
            BotCommand(
                BotCommands.YtdlLeechCommand[0],
                f'or /{BotCommands.YtdlLeechCommand[1]} Leech yt-dlp supported links via bot',
            ),
            BotCommand(
                BotCommands.CloneCommand[0],
                f'or /{BotCommands.CloneCommand[1]} Copy file/folder to Drive (GDrive/RClone)',
            ),
            BotCommand(
                BotCommands.CountCommand,
                f'[drive_url]: Count file/folder of Google Drive/RClone Drives',
            ),
            BotCommand(
                BotCommands.StatusCommand[0],
                f'or /{BotCommands.StatusCommand[1]} Get Bot All Status Stats Message',
            ),
            BotCommand(
                BotCommands.StatsCommand[0],
                f'or /{BotCommands.StatsCommand[1]} Check Bot & System stats',
            ),
            BotCommand(
                BotCommands.CancelTaskCommand[1],
                f'or /{BotCommands.StatsCommand[0]} Cancel a Task of yours!',
            ),
            BotCommand(
                BotCommands.CancelAllCommand[0],
                f'Cancel all Tasks in whole Bots.',
            ),
            BotCommand(
                BotCommands.ForceStartCommand[0],
                f'or /{BotCommands.ForceStartCommand[1]} Force a task to run in a queue',
            ),
            BotCommand(BotCommands.ListCommand[0], 
                f'Search in Drive(s)'
            ),
            
            BotCommand(
                BotCommands.SearchCommand[0],
                f'Search in Torrent via qBit clients!',
            ),
            BotCommand(
                BotCommands.HelpCommand[0],
                f'Get detailed help about the WZML-X Bot',
            ),
            BotCommand(
                BotCommands.RssCommand[0],
                f'Set RSS feed to bot',
            ),
            BotCommand(
                BotCommands.ShellCommand[0],
                f'Use shell command (Owner or Sudo Only)',
            ),
            BotCommand(
                BotCommands.UserSetCommand[0],
                f"or /{BotCommands.UserSetCommand[1]} User's Personal Settings (Open in PM)",
            ),
            BotCommand(
                BotCommands.UsersCommand[0],
                f"View's user Settings",
            ),
            BotCommand(
                BotCommands.BotSetCommand[0],
                f'Bot settings',
            ),
            BotCommand(
                BotCommands.PingCommand[0],
                f'Ping bot latency',
            ),
            BotCommand(
                BotCommands.SpeedCommand[0],
                f'or /{BotCommands.SpeedCommand[1]} Check Server Up & Down Speed & Details',
            ),
            BotCommand(
                BotCommands.BotSetCommand[0],
                f"or /{BotCommands.BotSetCommand[1]} Bot's Personal Settings (Owner or Sudo Only)",
            ),
            BotCommand(
                BotCommands.RestartCommand[0],
                f'or /{BotCommands.RestartCommand[1]} Restart & Update the Bot (Owner or Sudo Only)',
            ),
            BotCommand(
                BotCommands.ExecCommand[0],
                f'Use execute code command (Owner or Sudo Only)',
            ),
            BotCommand(
                BotCommands.AExecCommand[0],
                f'Use asynchronous execute code command (Owner or Sudo Only)',
            ),
            BotCommand(
                BotCommands.LogCommand[0],
                f'Check log bot (Owner or Sudo Only)',
            ),
        ]
        await client.set_bot_commands(bot_cmds)
        LOGGER.info('Bot Commands have been Set & Updated')
    except Exception as err:
        LOGGER.error(err)
