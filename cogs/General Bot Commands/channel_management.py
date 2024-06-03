import discord
from discord.ext import commands
from discord import app_commands
import aiosqlite
import helper as h

class ChannelManagement(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @discord.app_commands.command(name="channel")
    @discord.app_commands.describe(action="Enable or disable the channel for bot commands and messages.")
    @discord.app_commands.choices(action=[
        app_commands.Choice(name="disable", value="disable"),
        app_commands.Choice(name="enable", value="enable")
    ])
    async def channel(self, interaction: discord.Interaction, action: str):
        """Manage channel settings for bot interaction."""
        # Check permissions
        if not interaction.user.guild_permissions.manage_channels:
            await interaction.response.send_message("You do not have permission to manage channels.", ephemeral=True)
            return 

        channel_id = interaction.channel_id
        guild_id = interaction.guild_id

        async with aiosqlite.connect('data/main.db') as db:
            # Check current status first
            cursor = await db.execute("SELECT 1 FROM servers WHERE server_id = ? AND channel_id = ?", (guild_id, channel_id))
            exists = await cursor.fetchone()

            if action == "disable":
                if not exists:
                    await db.execute("INSERT INTO servers (server_id, channel_id) VALUES (?, ?)", (guild_id, channel_id))
                    await interaction.response.send_message(f"This channel has been disabled for commands and bot messages.", ephemeral=True)
                else:
                    await interaction.response.send_message(f"This channel is already disabled.", ephemeral=True)
            elif action == "enable":
                if exists:
                    await db.execute("DELETE FROM servers WHERE server_id = ? AND channel_id = ?", (guild_id, channel_id))
                    await interaction.response.send_message(f"This channel has been enabled for commands and bot messages.", ephemeral=True)
                else:
                    await interaction.response.send_message(f"This channel is already enabled.", ephemeral=True)

            await db.commit()


async def setup(bot):
    await bot.add_cog(ChannelManagement(bot))
