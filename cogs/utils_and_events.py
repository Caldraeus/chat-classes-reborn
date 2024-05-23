from ast import Pass
import discord
from discord.ext import commands
from discord.ext import tasks
import random

class utils_and_events(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.status_change.start()
        self.statuses = [
            "with Grumm's axe.",
            "with Prodigy's gem.",
            "with Kruber.",
            "around the town.",
            "with Tallie's bottles.",
            "with Bradley.",
            "with a big knife!",
            "with the RFP cast.",
            "Elden Ring™️",
            "with Ivona",
            "in Tallie's lab",
            "with Guul",
            "in the Kruber Prison",
            "running from Tamiya",
            "with the final thread",
            "in the Scorclands"
        ]

    def cog_unload(self):
        self.status_change.cancel()

    @tasks.loop(seconds=3600.0) # Every hour
    async def status_change(self):
        await self.bot.change_presence(activity=discord.Game(name=random.choice(self.statuses)))

    @status_change.before_loop
    async def before_printer(self):
        await self.bot.wait_until_ready()

    @commands.Cog.listener('on_member_join')
    async def on_member_join(self, member):
        guild = self.bot.get_guild(784842140764602398)
        channel = guild.get_channel(892840442020904991)

        amount_users = len(guild.members)
        amount_users = str(amount_users) + {1: 'st', 2: 'nd', 3: 'rd'}.get(4 if 10 <= amount_users % 100 < 20 else amount_users % 10, "th")

        embed = discord.Embed(title="Welcome to the Roll For Performance Server!", colour=discord.Colour.from_rgb(201,31,55), description=f"You are our **{amount_users}** member to join!\n──────\n 🔹 Make sure to read the rules!\n\n🔸 Feel free to ask any questions about the server!\n\n🔹 Most of all, have a good time!")

        embed.set_image(url="https://cdn.discordapp.com/splashes/784842140764602398/2370139055711deb72ee7f84369b7a01.jpg?size=1024")
        embed.set_thumbnail(url="https://pbs.twimg.com/profile_images/1349406311985934337/hdshQN7l_400x400.jpg")
        embed.set_author(name=str(member), icon_url=member.avatar.url)

        await channel.send(f"✨ Welcome to Veilrune, {member.mention}! ✨", embed=embed)

    @commands.Cog.listener("on_ready")
    async def on_ready(self):
        print(f'Success - Logged in.')
        # self.status_change.start() --- Don't do this in on_ready since it can be called multiple times!

    @commands.Cog.listener('on_message')
    async def on_message(self, message: discord.Message):
        pass

async def setup(bot):
    await bot.add_cog(utils_and_events(bot))