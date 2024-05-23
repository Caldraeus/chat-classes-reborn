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

load_dotenv()
intents = discord.Intents.all() # All intents, alter if needed.

prefix = ';'

bot = commands.Bot(command_prefix=prefix, description="Bot", case_insensitive=True, intents=intents)
bot.remove_command("help")

async def load_dir_files(path, dash) -> None:
    #print("\n")
    for item in listdir(path):
        if os.path.isdir(path) and item != ".DS_Store" and item != "__pycache__" and not item.endswith(".py") and not item.endswith(".md") and not item.endswith(".json"):
            new_path = path+f"/{item}"
            await load_dir_files(new_path, f"{dash}───")
        elif item.endswith(".py"):
            new_path = path+f"/{item}"
            new_path = new_path.replace(".py", "")
            load_path = new_path.replace("/", ".")
            num = 80
            for letter in str(item + dash):
                num -= 1
            empty = ""
            for i in range(num): # Makes things look nicer in the console... lol
                empty += " "
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