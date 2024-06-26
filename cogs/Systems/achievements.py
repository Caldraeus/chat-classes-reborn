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
        
    @app_commands.command(name="achievements", description="Displays the achievements of a user.")
    @app_commands.describe(target="The user whose achievements to display.")
    async def achievements(self, interaction: discord.Interaction, target: discord.Member = None):
        """Displays achievements for the user or the specified member."""
        if target is None:
            target = interaction.user
        
        achievements = await self.fetch_user_achievements(target.id)
        if not achievements:
            await interaction.response.send_message("🚫 No achievements found for this user.", ephemeral=True)
            return
        
        # Create the embed to display achievements
        embed = discord.Embed(title=f"{target.display_name}'s Achievements", color=discord.Color.gold())
        embed.set_thumbnail(url=target.display_avatar.url)
        
        for name, description, unlocks, class_name in achievements:
            achievement_info = description
            if class_name:
                achievement_info += f" (Unlocks: {class_name})"
            embed.add_field(name=name, value=achievement_info, inline=False)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

    async def fetch_user_achievements(self, user_id):
        async with aiosqlite.connect('data/main.db') as conn:
            cursor = await conn.execute("""
                SELECT a.name, a.description, a.unlocks, c.class_name FROM user_achievements ua
                JOIN achievements a ON ua.achievement_id = a.achievement_id
                LEFT JOIN classes c ON a.unlocks = c.class_id
                WHERE ua.user_id = ?;
            """, (user_id,))
            achievements = await cursor.fetchall()
        return achievements
        
    key_phrases_necromancer = [
        r"\b(kms)\b",
        r"\bi want to die\b",
        r"\byou want me to die\b",
        r"\bi feel like dying\b",
        r"\bi want to end it\b",
        r"\bi can't go on\b",
        r"\blife is pointless\b",
        r"\bno reason to live\b",
        r"\bi hate my life\b",
        r"\bim going to kill myself",
    ]

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if await h.user_exists(message.author.id) and await h.channel_check(message.channel.id):
            if message.author.bot or not message.guild:
                return
            if 'a' in message.content.lower():
                await h.grant_achievement(message.channel, message.author, 1)
            for phrase in self.key_phrases_necromancer:
                if re.search(phrase, message.content, re.IGNORECASE):
                    await h.grant_achievement(message.channel, message.author, 3)

    @commands.Cog.listener()
    async def on_app_command_completion(self, interaction: discord.Interaction, command: app_commands.Command) -> None:
        if command.name == 'profile': # We run this first since the channel_check and user_exists functions are slower.
            if await h.user_exists(interaction.user.id) and await h.channel_check(interaction.channel_id):
                    await h.grant_achievement(interaction.channel, interaction.user, 2)




# A setup function the every cog has
async def setup(bot):
    await bot.add_cog(achievements(bot))