from urllib.parse import urlsplit
import discord
from discord.ext import commands
from discord import app_commands, ui
import helper as h
from typing import Literal, Type
import traceback
import sys
import aiosqlite
import aiohttp
import asyncio
import re
from typing import List
from datetime import timedelta
import os

"""
For achievement documentation, read ACHIVEMENTS.md.
"""

class achievements(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
    @discord.app_commands.command(name="achievements", description="Displays the achievements of a user.")
    @discord.app_commands.describe(target="The user whose achievements to display.")
    async def achievements(self, interaction: discord.Interaction, target: discord.Member = None):
        """Displays achievements for the user or the specified member."""
        if target is None:
            target = interaction.user
        
        achievements = await self.fetch_user_achievements(target.id)
        if not achievements:
            await interaction.response.send_message("🚫 No achievements found for this user.", ephemeral=True)
            return
        
        # Create the embed to display achievements
        embed = discord.Embed(title=f"{target.display_name}'s Achievements", description="\n".join(achievements), color=discord.Color.gold())
        embed.set_thumbnail(url=target.display_avatar.url)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

    async def fetch_user_achievements(self, user_id):
        """Retrieve achievements from the database for a given user ID."""
        async with aiosqlite.connect("data/main.db") as db:
            cursor = await db.execute("""
                SELECT achievements.name 
                FROM user_achievements 
                JOIN achievements ON user_achievements.achievement_id = achievements.achievement_id 
                WHERE user_id = ?;
            """, (user_id,))
            achievements = await cursor.fetchall()
            return [ach[0] for ach in achievements] if achievements else None
        
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if await h.user_exists(message.author.id) and await h.channel_check(message.channel.id):
            if message.author.bot or not message.guild:
                return
            if 'a' in message.content.lower():
                await h.grant_achievement(message.channel, message.author, 1)

    @commands.Cog.listener()
    async def on_app_command_completion(self, interaction: discord.Interaction, command: app_commands.Command) -> None:
        if command.name == 'profile': # We run this first since the channel_check and user_exists functions are slower.
            if await h.user_exists(interaction.user.id) and await h.channel_check(interaction.channel_id):
                    await h.grant_achievement(interaction.channel, interaction.user, 2)




# A setup function the every cog has
async def setup(bot):
    await bot.add_cog(achievements(bot))