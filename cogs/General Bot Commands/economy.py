import discord
from discord.ext import commands, tasks
from discord import app_commands
import aiosqlite
from datetime import datetime, timezone, timedelta

class economy(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.claimed = []
        self.rollover_task.start()
        self.update_status.start()

    def cog_unload(self):
        self.rollover_task.cancel()
        self.update_status.cancel()

    @tasks.loop(hours=24)
    async def rollover_task(self):
        self.reset_users_ap()
        self.bot.claimed.clear()
        print("Rollover completed: AP reset and claimed list cleared.")

    @rollover_task.before_loop
    async def before_rollover_task(self):
        await self.bot.wait_until_ready()
        now = datetime.now(timezone.utc)
        next_rollover = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        await discord.utils.sleep_until(next_rollover)

    def reset_users_ap(self):
        self.bot.user_aps = {user_id: 20 for user_id in self.bot.user_aps.keys()}  # Reset all user APs to 20
        self.bot.user_aps[217288785803608074] = 9999

    @app_commands.command(name="daily", description="Claim your daily rewards.")
    async def daily(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        if user_id in self.bot.claimed:
            await interaction.response.send_message("You have already claimed your daily rewards today!", ephemeral=True)
            return

        async with aiosqlite.connect('data/main.db') as db:
            await db.execute("UPDATE users SET gold = gold + 100, coolness = coolness + 50 WHERE user_id = ?", (user_id,))
            await db.commit()

        self.bot.claimed.append(user_id)
        await interaction.response.send_message("⭐ | You have claimed your daily rewards of 100 gold and 50 coolness!", ephemeral=True)

    @tasks.loop(minutes=1)
    async def update_status(self):
        now = datetime.now(timezone.utc)
        next_rollover = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        time_until_rollover = next_rollover - now
        hours, remainder = divmod(time_until_rollover.seconds, 3600)
        minutes, _ = divmod(remainder, 60)
        await self.bot.change_presence(activity=discord.Game(name=f"Rollover in {hours}h {minutes}m"))

    @update_status.before_loop
    async def before_update_status(self):
        await self.bot.wait_until_ready()

    @commands.Cog.listener()
    async def on_ready(self):
        if not self.update_status.is_running():
            self.update_status.start()

async def setup(bot):
    await bot.add_cog(economy(bot))
