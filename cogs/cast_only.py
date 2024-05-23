import discord
from discord.ext import commands
from discord import app_commands
from discord.utils import get
import helper as h

class cast_only(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(name="live")
    @app_commands.guilds(discord.Object(id=h.my_guild))
    @app_commands.describe(txt='Optional text to have Gilly say before our twitch link.')
    @app_commands.checks.has_role(892835307114876938)
    async def live(self, interaction: discord.Interaction, txt: str = "We are now live on Twitch! Come stop by!"):
        """ Announce that we are live on Twitch to the server. """
        annc_channel = self.bot.get_channel(892838667318607934)
        
        guild = annc_channel.guild
        
        role = get(guild.roles, id=904746679255859220)
        
        await annc_channel.send(content=f"{role.mention}\n\n" + txt + "\n\nhttps://www.twitch.tv/rollforperformance")

        await interaction.response.send_message(content="Successfully sent server announcement.", ephemeral=True)
        
    

# A setup function the every cog has
async def setup(bot):
    await bot.add_cog(cast_only(bot))