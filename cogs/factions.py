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
from typing import List
sys.path.append('/mnt/c/Users/perkettr/Desktop/Python/gilly-bot/cogs/views')
import nc_faction_views as v

class factions(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="factions")
    @app_commands.guilds(discord.Object(id=h.my_guild))
    async def factions(self, interaction: discord.Interaction) -> None:
        """View the catalogue of factions"""
        try:
            async with aiosqlite.connect('data/game.db') as conn:
                async with conn.execute("SELECT faction_name, COUNT(character_faction_stats.user_id) AS num_members, faction_img_link, faction_description, faction_rgb FROM factions LEFT JOIN character_faction_stats ON factions.faction_id=character_faction_stats.faction_id WHERE factions.faction_id != 1 GROUP BY factions.faction_id ORDER BY faction_name") as factions_info:
                    factions = await factions_info.fetchall()

                assert factions
        except AssertionError:
            await interaction.response.send_message("No factions found.", ephemeral=True)
        else:
            page = 0
            faction = factions[page]
            
            rgb = tuple(int(c) for c in faction[4].split("|"))

            embed = discord.Embed(title=f"Factions Catalogue: {faction[0]}", color=discord.Color.from_rgb(rgb[0], rgb[1], rgb[2]), description=faction[3].replace("\\n", "\n"))

            embed.add_field(name="Details", value=f"__Number of Members: {faction[1]}__", inline=True)
            embed.set_image(url=faction[2])

            embed.set_footer(text=f"Page {page + 1}/{len(factions)}")

            view = v.FactionButtons(interaction.user, page, factions)

            await interaction.response.send_message(embed=embed, ephemeral=True, view=view)


# A setup function the every cog has
async def setup(bot):
    await bot.add_cog(factions(bot))