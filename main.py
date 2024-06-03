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

load_dotenv()
intents = discord.Intents.all() # All intents, alter if needed.

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

"""
Global variables
 > These are variables that I don't want to store permanently, things that aren't worth saving somewhere.
 > Things like status effects, their action points, who's claimed their daily rewards... while I could save
 > these in a more permanent manner, it's just not worth the overhead. This might change later down the line,
 > but for now this is what I've decided.
""" 
bot.users_ap = {}
bot.registered_users = {}
bot.users_classes = {}
bot.users_ap = {}
bot.user_status = {}
# These global variables are currently not used; this wis subject to change.

async def load_dir_files(path, dash) -> None:
    #print("\n")
    for item in listdir(path):
        if os.path.isdir(path) and item != ".DS_Store" and item != "__pycache__" and not item.endswith(".py") and not item.endswith(".md") and not item.endswith(".json"):
            new_path = path+f"/{item}"
            await load_dir_files(new_path, f"{dash} {item} ───")
        elif item.endswith(".py"):
            new_path = path+f"/{item}"
            new_path = new_path.replace(".py", "")
            load_path = new_path.replace("/", ".")
            empty = " " * (80 - len(str(item + dash)))
            try:
                if not "nc_" in item:
                    print(f"{dash} Loading {item}...", end = " ")
                    await bot.load_extension(load_path)
                    print(f"{empty}[SUCCESS]")
                else:
                    pass
            except (discord.ClientException, ModuleNotFoundError):
                print(f"\n{empty}[FAILURE]")
                print(f'Failed to load extension {item}.\n')
                traceback.print_exc()

async def main():
    discord.utils.setup_logging()
    await load_dir_files('cogs' ,"├─")
    await bot.start(os.getenv("BOT_ID"))
    

asyncio.run(main())

# interaction.command?