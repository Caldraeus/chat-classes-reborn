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
import aiohttp
import asyncio
import re
from typing import List
import random
import datetime
from datetime import timedelta
import os
import requests
from PIL import Image, ImageOps
from io import BytesIO
import pickle

class experience(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.user_streaks = {}
        self.last_message_time = {}
        self.notified = []

        self.variables_to_save = {
            'notified': []
        }

        # Load state variables asynchronously and setup defaults
        asyncio.create_task(self.load_and_initialize_variables())

    async def load_and_initialize_variables(self):
        try:
            with open('data/experience_state.pkl', 'rb') as file:
                data = pickle.load(file)
                for key in self.variables_to_save:
                    setattr(self, key, data.get(key, self.variables_to_save[key]))
        except FileNotFoundError:
            self.set_default_values()

    def set_default_values(self):
        self.notified = []

    async def save_variables(self):
        try:
            data = {key: getattr(self, key) for key in self.variables_to_save}
            with open('data/experience_state.pkl', 'wb') as file:
                pickle.dump(data, file)
            print(f"{self.__class__.__name__}: Variables saved successfully.")
        except Exception as e:
            print(f"{self.__class__.__name__}: Failed to save variables due to {e}")

    def cog_unload(self):
        """Handle tasks on cog unload."""
        asyncio.create_task(self.save_variables())

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return  # Ignore bot messages and DMs

        user_id = message.author.id
        current_time = datetime.datetime.now()

        # Enforce a 5-second cooldown for XP gain
        if user_id in self.last_message_time and (current_time - self.last_message_time[user_id]).total_seconds() < 10:
            return

        # Update last message time
        self.last_message_time[user_id] = current_time
        
        # Process XP gain
        await self.process_xp_gain(message, current_time)

    async def process_xp_gain(self, message, current_time):
        user_id = message.author.id
        xp_gain = random.randint(5, 100)  # Base XP gain

        # Check and update streaks
        if user_id in self.user_streaks and (current_time - self.user_streaks[user_id]['last_time']).total_seconds() <= 300:
            streak = min(self.user_streaks[user_id]['streak'] + 1, 5)  # Increment streak, max of 5
        else:
            streak = 1  # Reset streak

        self.user_streaks[user_id] = {'last_time': current_time, 'streak': streak}
        xp_gain += xp_gain * 0.05 * streak  # Increase XP based on streak

        async with aiosqlite.connect('data/main.db') as conn:
            cursor = await conn.execute("SELECT exp, level FROM users WHERE user_id = ?", (user_id,))
            profile = await cursor.fetchone()
            if not profile:
                return  # If user does not exist, do not process further

            xp, level = profile
            new_xp = xp + xp_gain
            max_xp_needed = h.max_xp(level)

            if new_xp >= max_xp_needed:
                await self.handle_level_up(conn, message, level, new_xp)
            else:
                await conn.execute("UPDATE users SET exp = ? WHERE user_id = ?", (round(new_xp), user_id))
            await conn.commit()

    async def handle_level_up(self, conn, message, current_level, current_xp):
        user = message.author
        new_level = current_level + 1
        max_xp_for_current_level = h.max_xp(current_level)

        if current_xp >= max_xp_for_current_level:
            xp_over = round(current_xp - max_xp_for_current_level)
        else:
            xp_over = 0

        embed = discord.Embed(color=discord.Color.purple())
        embed.set_thumbnail(url=user.display_avatar.url)
        embed.set_author(name=user.display_name, icon_url=user.display_avatar.url)

        if new_level % 10 == 0:
            duration = 15
            if await h.channel_check(message.channel.id):
                await conn.execute("UPDATE users SET exp = ? WHERE user_id = ?", (max_xp_for_current_level, user.id))
                if user.id in self.notified:
                    return 
                else:
                    #return
                    # This line is to prevent the annoyingness during testing.
                    self.notified.append(user.id)
                    embed.title = f"🌟 Milestone Level {new_level - 1} Achieved!"
                    embed.description = (f"🔒 You've filled your XP bar at level {new_level - 1}, {user.display_name}!\n"
                                        f"To advance to level {new_level}, you must use the `/classup` command.")
                    embed.set_footer(text="Run /classup to unlock your next class and abilities!")
        else:
            self.notified.remove(user.id) if user.id in self.notified else None
            duration = 5
            await conn.execute("UPDATE users SET level = ?, exp = ? WHERE user_id = ?", (new_level, xp_over, user.id))
            embed.title = f"✨ Congratulations on Leveling Up!"
            embed.description = f"You are now level {new_level}! Keep up the great work."
            embed.add_field(name="Extra XP", value=f"{xp_over} XP rolls over to your next level.", inline=False)
        
        await conn.commit()

        # This allows the user to still gain experience in banned channels, but won't notify them when they level up.
        if await h.channel_check(message.channel.id):
            await message.channel.send(embed=embed, delete_after=duration)
        else:
            pass

# A setup function the every cog has
async def setup(bot):
    await bot.add_cog(experience(bot))