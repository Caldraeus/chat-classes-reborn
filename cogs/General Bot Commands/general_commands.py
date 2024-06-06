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

    @app_commands.command(name="leaderboard", description="Show the top 5 users with the highest coolness.")
    @app_commands.guild_only()
    async def leaderboard(self, interaction: discord.Interaction):
        async with aiosqlite.connect('data/main.db') as con:
            async with con.execute("SELECT user_id, coolness FROM users ORDER BY coolness DESC LIMIT 10;") as lb:
                stuff = await lb.fetchall()
        
        final = ""
        in_top = False
        total = 5
        amount_skipped = 0

        for i, user_data in enumerate(stuff):
            if i >= total:
                break

            user_id, coolness = user_data
            user = self.bot.get_user(int(user_id))

            if user is not None and user.id != interaction.user.id:
                final += f"#{i + 1 - amount_skipped} - {user.name} - {coolness} Coolness\n\n"
            elif user is not None and user.id == interaction.user.id:
                final += f"**#{i + 1 - amount_skipped} - {user.name} - {coolness} Coolness**\n\n"
                in_top = True

                if i + 1 - amount_skipped == 1:
                    await h.grant_achievement(interaction.channel, interaction.user, 5)
                    await h.grant_achievement(interaction.channel, interaction.user, 6)
                else:
                    await h.grant_achievement(interaction.channel, interaction.user, 6)
            elif user is None:
                final += f"#{i + 1 - amount_skipped} - Unknown User - {coolness} Coolness\n\n"
                amount_skipped += 1

        if not in_top:
            rank = 1
            coolness = 0
            for rank, user_data in enumerate(stuff, start=1):
                if user_data[0] == str(interaction.user.id):
                    coolness = user_data[1]
                    break

            final += f"**.  .  .\n\n#{rank} - {interaction.user.name} - {coolness} Coolness**"

        embed = discord.Embed(title="👑 The Coolest Kids 👑", colour=discord.Colour.from_rgb(255, 255, 0), description=final)
        embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/491359456337330198/733460129785184297/Funny-Dog-Wearing-Sunglasses.png")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

        if await h.get_coolness(interaction.user.id) <= -1000:
            await h.grant_achievement(interaction.channel, interaction.user, 4)

# A setup function the every cog has
async def setup(bot):
    await bot.add_cog(general_commands(bot))