import discord
from discord.ext import commands
from discord import app_commands
from discord.app_commands import Choice
import helper as h
import math
from typing import Literal

class general_commands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="about")
    @app_commands.guilds(discord.Object(id=h.my_guild))
    async def about(self, interaction: discord.Interaction) -> None:
        """ Display information about the bot, such as latency. """
        profile = discord.Embed(title=f"About Gilly", colour=discord.Colour(0x6fa8dc), description="")
        
        profile.set_footer(text=f"Bot Latency: {math.ceil(round(self.bot.latency * 1000, 1))} ms", icon_url="")
        profile.add_field(name="Bot Version", value="1.0", inline=False)
        profile.add_field(name="Creator", value=f'Caldraeus#0404', inline=False)
        profile.add_field(name="Library", value=f'discord.py', inline=False)
        profile.set_thumbnail(url=self.bot.user.avatar.url)

        await interaction.response.send_message(embed=profile, ephemeral=True)

# A setup function the every cog has
async def setup(bot):
    await bot.add_cog(general_commands(bot))