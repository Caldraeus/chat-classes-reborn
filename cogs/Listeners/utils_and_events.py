from ast import Pass
import discord
from discord.ext import commands
from discord.ext import tasks
import random
import aiosqlite
import helper as h
import logging
import asyncio
import signal

class utils_and_events(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.quest_manager = h.QuestManager('data/main.db', self.bot)

    async def initialize_user_aps(self):
        async with aiosqlite.connect('data/main.db') as db:
            cursor = await db.execute("SELECT user_id FROM users")
            users = await cursor.fetchall()
            for user in users:
                self.bot.user_aps[user[0]] = 20  # Initialize with default AP. This can/will be changed later.
            self.bot.user_aps[217288785803608074] = 9999

    @commands.Cog.listener("on_ready")
    async def on_ready(self):
        """
        On bot load, update some global bot variables.
        These are cached for frequent access without needing to query the DB repeatedly.
        """
        if self.bot.user_aps == {}:
            await self.initialize_user_aps()

        logging.info("Bot is ready and data has been loaded!")

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        # Try to find a suitable channel to send the greeting message
        # If the guild has set a system channel, we use it; otherwise, we look for a general or text channel
        if guild.system_channel:
            channel = guild.system_channel
        else:
            # Attempt to find a channel named 'general' if no system channel is available
            channel = discord.utils.find(lambda x: x.name == 'general', guild.text_channels)
            if channel is None:
                # If no channel named 'general', use the first available text channel
                channel = guild.text_channels[0] if guild.text_channels else None

        if channel:
            # Send the disclaimer message
            await channel.send(
                """
👋 Hello! Thanks for adding me to your server!

⚠️ **Important:**
1. One of the classes in the bot (`Archmage`) has AI integration. It reads 50 messages from a user when activated. If there’s a channel with information you don’t want shared with OpenAI, please use `/channel disable`. (*Note that these messages read by the bot are [never saved](https://openai.com/policies/privacy-policy).*)
2. I also do a lot of fun and silly things with chat and people's messages. If this isn’t okay, you should run the same `/channel disable` command.
3. Please ensure that you have obtained consent from your users before enabling features that affect their messages. Make sure to inform your users about these functionalities or disable the bot in channels that might be heavily affected by the silliness!


🔗 **Need help or have questions?**
Run `/server` to join our official support server!

Enjoy your time and feel free to customize your experience!
                """
            )
            


async def setup(bot):
    await bot.add_cog(utils_and_events(bot))