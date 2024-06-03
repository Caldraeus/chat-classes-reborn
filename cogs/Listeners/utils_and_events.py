from ast import Pass
import discord
from discord.ext import commands
from discord.ext import tasks
import random
import aiosqlite
import helper as h
import logging

class utils_and_events(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.status_change.start()
        self.statuses = [
            "something new."
        ]

    def cog_unload(self):
        self.status_change.cancel()

    @tasks.loop(seconds=3600.0) # Every hour
    async def status_change(self):
        await self.bot.change_presence(activity=discord.Game(name=random.choice(self.statuses)))

    @status_change.before_loop
    async def before_printer(self):
        await self.bot.wait_until_ready()

    # @commands.Cog.listener('on_member_join')
    # async def on_member_join(self, member):
    #     guild = self.bot.get_guild(784842140764602398)
    #     channel = guild.get_channel(892840442020904991)

    #     amount_users = len(guild.members)
    #     amount_users = str(amount_users) + {1: 'st', 2: 'nd', 3: 'rd'}.get(4 if 10 <= amount_users % 100 < 20 else amount_users % 10, "th")

    #     embed = discord.Embed(title="Welcome to our server!", colour=discord.Colour.from_rgb(201,31,55), description=f"You are our **{amount_users}** member to join!\n──────\n 🔹 Make sure to read the rules!\n\n🔸 Feel free to ask any questions about the server!\n\n🔹 Most of all, have a good time!")

    #     embed.set_image(url="https://cdn.discordapp.com/splashes/784842140764602398/2370139055711deb72ee7f84369b7a01.jpg?size=1024")
    #     embed.set_thumbnail(url="https://pbs.twimg.com/profile_images/1349406311985934337/hdshQN7l_400x400.jpg")
    #     embed.set_author(name=str(member), icon_url=member.avatar.url)

    #     await channel.send(f"✨ Welcome to Veilrune, {member.mention}! ✨", embed=embed)

    @commands.Cog.listener("on_ready")
    async def on_ready(self):
        """
        On bot load, update some global bot variables.
        These are cached for frequent access without needing to query the DB repeatedly.

        NOTE: Currently not implemented. This was a feature of the old Chat Classes which has since been deprecated.
        """

        self.bot.quest_manager = h.QuestManager('data/main.db', self.bot)

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