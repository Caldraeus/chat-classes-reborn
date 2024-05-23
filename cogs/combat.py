from urllib.parse import urlsplit
import discord
from discord.ext import commands
from discord import app_commands
from discord import ui
import helper as h
from typing import Literal, Type
import traceback
import sys
import aiosqlite
import re
import asyncio
sys.path.append('/mnt/c/Users/perkettr/Desktop/Python/gilly-bot/cogs/views')
# /mnt/c/Users/perkettr/Desktop/Python/gilly-bot/cogs/views for bad pc
# /mnt/c/users/richa/desktop/code/Python/Discord Bots/gilly_bot/cogs/views for good pc
import nc_combat_views as v

class combat(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="battle")
    @app_commands.guilds(discord.Object(id=h.my_guild))
    async def battle(self, interaction: discord.Interaction, target: discord.Member) -> None:
        """Challenge another player to a PvP battle."""
        if target is None:
            await interaction.response.send_message("❌ | You can't fight nothing!")
            return
        elif target == interaction.user:
            await interaction.response.send_message("❌ | You can't fight yourself!")
            return
        elif h.get_character(target.id) == None:
            await interaction.response.send_message("❌ | You can't this player, they have no character!")
            return
        else:
            assert(target is not None and target != interaction.user and h.get_character(target.id) != None)

        view = v.Challenge(interaction.user, target)
        await interaction.response.send_message(view=view)

# A setup function the every cog has
async def setup(bot):
    await bot.add_cog(combat(bot))