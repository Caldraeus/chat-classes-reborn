import discord
from discord.ext import commands
from discord import app_commands
from discord.app_commands import Choice
import helper as h
import math
import time
import datetime
from datetime import datetime, timezone, timedelta
import aiosqlite
from typing import Literal

class general_commands(commands.Cog):
    """
    Display general information about the but, such as latency, version, library, etc.
    """
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="about")
    async def about(self, interaction: discord.Interaction) -> None:
        """ Display information about the bot, such as latency. """
        profile = discord.Embed(title=f"About Chat Classes Reborn", colour=discord.Colour(0x6fa8dc), description="")
        
        profile.set_footer(text=f"Bot Latency: {math.ceil(round(self.bot.latency * 1000, 1))} ms", icon_url="")
        profile.add_field(name="Bot Version", value="1.0.0 Alpha", inline=False)
        profile.add_field(name="Creator", value=f'@Caldraeus', inline=False)
        profile.add_field(name="Library", value=f'discord.py', inline=False)
        profile.set_thumbnail(url=self.bot.user.avatar.url)

        await interaction.response.send_message(embed=profile, ephemeral=True)

    @app_commands.command(name="info", description="Display diagnostic information about the bot.")
    async def info(self, interaction: discord.Interaction):
        now = datetime.now(timezone.utc)
        next_rollover = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        time_until_rollover = next_rollover - now

        hours, remainder = divmod(time_until_rollover.seconds, 3600)
        minutes, _ = divmod(remainder, 60)
        local_time = discord.utils.format_dt(next_rollover, style='F')

        async with aiosqlite.connect('data/main.db') as db:
            async with db.execute("SELECT COUNT(*) FROM users") as cursor:
                active_users = await cursor.fetchone()
            async with db.execute("SELECT SUM(gold) FROM users") as cursor:
                total_gold = await cursor.fetchone()
            async with db.execute("SELECT SUM(exp) FROM users") as cursor:
                total_experience = await cursor.fetchone()
            async with db.execute("SELECT SUM(coolness) FROM users") as cursor:
                total_coolness = await cursor.fetchone()
            async with db.execute("""
                SELECT classes.class_name, COUNT(*) 
                FROM classes 
                JOIN users ON classes.class_id = users.class_id 
                GROUP BY classes.class_id 
                ORDER BY COUNT(*) DESC LIMIT 1
            """) as cursor:
                most_common_class = await cursor.fetchone()
            async with db.execute("""
                SELECT classes.class_name, COUNT(*) 
                FROM classes 
                JOIN users ON classes.class_id = users.class_id 
                GROUP BY classes.class_id 
                ORDER BY COUNT(*) ASC LIMIT 1
            """) as cursor:
                rarest_class = await cursor.fetchone()
            async with db.execute("SELECT SUM(quests_completed) FROM users") as cursor:
                total_quests_completed = await cursor.fetchone()
            async with db.execute("SELECT SUM(amount) FROM user_inventory") as cursor:
                total_items = await cursor.fetchone()
            async with db.execute("""
                SELECT items.item_name, SUM(user_inventory.amount) 
                FROM items 
                JOIN user_inventory ON items.item_id = user_inventory.item_id 
                GROUP BY items.item_id 
                ORDER BY SUM(user_inventory.amount) DESC LIMIT 1
            """) as cursor:
                most_popular_item = await cursor.fetchone()
            async with db.execute("SELECT COUNT(*) FROM user_achievements") as cursor:
                total_achievements_awarded = await cursor.fetchone()
            async with db.execute("""
                SELECT achievements.name, COUNT(*) 
                FROM achievements 
                JOIN user_achievements ON achievements.achievement_id = user_achievements.achievement_id 
                GROUP BY achievements.achievement_id 
                ORDER BY COUNT(*) DESC LIMIT 1
            """) as cursor:
                most_common_achievement = await cursor.fetchone()

        avg_coolness_per_user = total_coolness[0] / active_users[0] if active_users[0] > 0 else 0
        total_servers = len(self.bot.guilds)  # Get total servers using discord API

        embed = discord.Embed(title="Bot Diagnostic Information", colour=discord.Colour.blue())
        embed.add_field(name="Hours until Rollover", value=f"{hours}h {minutes}m\n(Local Time: {local_time})", inline=False)
        embed.add_field(name="Active Users", value=f"{active_users[0]}", inline=True)
        embed.add_field(name="Total Gold in Circulation", value=f"{total_gold[0]}", inline=True)
        embed.add_field(name="Total Experience Gained", value=f"{total_experience[0]}", inline=True)
        embed.add_field(name="Total Coolness Gained", value=f"{total_coolness[0]}", inline=True)
        embed.add_field(name="Most Common Class", value=f"{most_common_class[0]} ({most_common_class[1]} users)", inline=True)
        embed.add_field(name="Rarest Class", value=f"{rarest_class[0]} ({rarest_class[1]} users)", inline=True)
        embed.add_field(name="Total Quests Completed", value=f"{total_quests_completed[0]}", inline=True)
        embed.add_field(name="Average Coolness per User", value=f"{avg_coolness_per_user:.2f}", inline=True)
        embed.add_field(name="Total Items in Circulation", value=f"{total_items[0]}", inline=True)
        embed.add_field(name="Most Popular Item", value=f"{most_popular_item[0]} ({most_popular_item[1]} in circulation)", inline=True)
        embed.add_field(name="Total Achievements Awarded", value=f"{total_achievements_awarded[0]}", inline=True)
        embed.add_field(name="Most Common Achievement", value=f"{most_common_achievement[0]} ({most_common_achievement[1]} times awarded)", inline=True)
        embed.add_field(name="Total Servers", value=f"{total_servers}", inline=True)

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="leaderboard", description="Show the top 10 users with the highest coolness.")
    @app_commands.guild_only()
    async def leaderboard(self, interaction: discord.Interaction):
        async with aiosqlite.connect('data/main.db') as con:
            async with con.execute("SELECT user_id, coolness FROM users ORDER BY coolness DESC;") as lb:
                all_users = await lb.fetchall()

        display_limit = 10
        final = ""
        in_top = False
        user_rank = None
        user_coolness = 0

        # Generate the leaderboard text
        for i, (user_id, coolness) in enumerate(all_users[:display_limit], start=1):
            user = self.bot.get_user(int(user_id))
            user_line = f"#{i} - {(user.name if user else 'Unknown User')} - {coolness} Coolness\n\n"
            if user and user.id == interaction.user.id:
                in_top = True
                user_line = f"**{user_line.strip()}**"
                user_rank = i
                user_coolness = coolness
            final += user_line

        # Add the user's own rank if they're not in the top displayed
        if not in_top:
            for rank, (user_id, coolness) in enumerate(all_users, start=1):
                if str(user_id) == str(interaction.user.id):
                    user_rank = rank
                    user_coolness = coolness
                    break
            if user_rank > display_limit:
                final += f"**.  .  .\n\n#{user_rank} - {interaction.user.name} - {user_coolness} Coolness**"

        embed = discord.Embed(title="👑 The Coolest Kids 👑", colour=discord.Colour.from_rgb(255, 255, 0), description=final)
        embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/491359456337330198/733460129785184297/Funny-Dog-Wearing-Sunglasses.png")
        await interaction.response.send_message(embed=embed, ephemeral=True)

        # Granting achievements based on conditions
        if user_rank == 1:
            await h.grant_achievement(interaction.channel, interaction.user, 5)  # Achievement for being #1
        if user_rank and user_rank <= 5:
            await h.grant_achievement(interaction.channel, interaction.user, 6)  # Achievement for being top 5
        if user_coolness <= -1000:
            await h.grant_achievement(interaction.channel, interaction.user, 4)  # Achievement for coolness <= -1000

# A setup function the every cog has
async def setup(bot):
    await bot.add_cog(general_commands(bot))