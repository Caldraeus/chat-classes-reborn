import discord
from discord.ext import commands
from discord import app_commands
import sys, traceback
from os import listdir
from os.path import isfile, join
import os
import asyncio
import math
import helper as h
from dotenv import load_dotenv
import aiosqlite
import logging
import signal
import contextlib
import pickle  

load_dotenv()
intents = discord.Intents.all()  # All intents, alter if needed.

class commandTree(app_commands.CommandTree):
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Global check to determine if an interaction should be processed by the tree."""
        if interaction.command.name.lower() == "channel":
            return True
        else:
            if interaction.guild:  # Check only applies to interactions within guilds
                async with aiosqlite.connect('data/main.db') as db:
                    cursor = await db.execute("SELECT 1 FROM servers WHERE channel_id = ?", (interaction.channel_id,))
                    is_disabled = await cursor.fetchone()
                    if is_disabled:
                        # Optionally send an ephemeral message if the channel is disabled
                        if interaction.response.is_done():
                            await interaction.followup.send("Commands are disabled in this channel.", ephemeral=True)
                        else:
                            await interaction.response.send_message("Commands are disabled in this channel.", ephemeral=True)
                        return False
            return True

prefix = ';'

bot = commands.Bot(command_prefix=prefix, description="Bot", case_insensitive=True, intents=intents, tree_cls=commandTree)
bot.remove_command("help")

# Global variables
bot.user_aps = {}
bot.user_effects = {}

async def load_user_aps():
    """Load user_aps from file."""
    try:
        with open('data/user_aps.pkl', 'rb') as file:
            bot.user_aps = pickle.load(file)
    except (FileNotFoundError, EOFError):
        bot.user_aps = {}

async def save_user_aps():
    """Save user_aps to file."""
    with open('data/user_aps.pkl', 'wb') as file:
        pickle.dump(bot.user_aps, file)

async def load_dir_files(path, dash) -> None:
    for item in listdir(path):
        if os.path.isdir(path) and item != ".DS_Store" and item != "__pycache__" and not item.endswith(".py") and not item.endswith(".md") and not item.endswith(".json"):
            new_path = path + f"/{item}"
            await load_dir_files(new_path, f"{dash} {item} ───")
        elif item.endswith(".py"):
            new_path = path + f"/{item}"
            new_path = new_path.replace(".py", "")
            load_path = new_path.replace("/", ".")
            empty = " " * (80 - len(str(item + dash)))
            try:
                if not "nc_" in item:
                    print(f"{dash} Loading {item}...", end=" ")
                    await bot.load_extension(load_path)
                    print(f"{empty}[SUCCESS]")
                else:
                    pass
            except (discord.ClientException, ModuleNotFoundError):
                print(f"\n{empty}[FAILURE]")
                print(f'Failed to load extension {item}.\n')
                traceback.print_exc()

async def shutdown(signal, loop):
    print(f"Received exit signal {signal.name}...")

    print("Saving user AP.")
    await save_user_aps()

    print("Cancelling all pending tasks and unloading cogs.\n-----------------------------------------\n")
    tasks = [t for t in asyncio.all_tasks(loop) if t is not asyncio.current_task()]
    for task in tasks:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    print("Closing the bot.\n==============================\n")
    await bot.close()
    loop.stop()

def setup_signal_handlers(loop):
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, lambda sig=sig: asyncio.create_task(shutdown(sig, loop)))

async def main():
    discord.utils.setup_logging()
    await load_user_aps()
    await load_dir_files('cogs', "├─")
    await bot.start(os.getenv("BOT_ID"))

loop = asyncio.get_event_loop()
setup_signal_handlers(loop)

try:
    loop.run_until_complete(main())
except KeyboardInterrupt:
    print("Keyboard interrupt received, shutting down...")
    loop.run_until_complete(shutdown(signal.SIGINT, loop))
except asyncio.exceptions.CancelledError as e:
    print(f'\nAll set. Note: {e}\n')
finally:
    print("Final cleanup of tasks.")
    pending = asyncio.all_tasks(loop)
    for task in pending:
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            loop.run_until_complete(task)
    loop.close()