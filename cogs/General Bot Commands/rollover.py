import discord
from discord.ext import commands, tasks
from discord import app_commands
import aiosqlite
from datetime import datetime, timezone, timedelta
import pickle
import asyncio
import signal

class rollover(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.variables_to_save = {
            'claimed': []
        }
        
        # Load state variables asynchronously and setup defaults
        asyncio.create_task(self.load_and_initialize_variables())

        self.rollover_task.start()

    async def load_and_initialize_variables(self):
        try:
            with open('data/economy_state.pkl', 'rb') as file:
                data = pickle.load(file)
                for key in self.variables_to_save:
                    setattr(self.bot, key, data.get(key, self.variables_to_save[key]))
        except FileNotFoundError:
            self.set_default_values()

    def set_default_values(self):
        # Set default values for all your variables
        self.bot.claimed = []
        # Initialize additional variables if needed

    async def save_variables(self):
        data = {key: getattr(self.bot, key) for key in self.variables_to_save}
        with open('data/economy_state.pkl', 'wb') as file:
            pickle.dump(data, file, protocol=pickle.HIGHEST_PROTOCOL)

    def cog_unload(self):
        self.rollover_task.cancel()

    async def reset_user_class_specific(self):
        class_cog = self.bot.get_cog('action_core')
        if class_cog:
            class_cog.nomad_homes.clear()
            class_cog.soulcrusher_souls.clear()
            class_cog.hired.clear()

    @tasks.loop(hours=24)
    async def rollover_task(self):
        await self.reset_users_ap()
        await self.reset_user_class_specific()
        self.bot.claimed.clear()
        print("Rollover completed: AP reset and claimed list cleared.")

    @rollover_task.before_loop
    async def before_rollover_task(self):
        await self.bot.wait_until_ready()
        now = datetime.now(timezone.utc)
        next_rollover = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        await discord.utils.sleep_until(next_rollover)

    async def reset_users_ap(self):
        self.bot.user_aps = {user_id: (20 if ap < 20 else ap) for user_id, ap in self.bot.user_aps.items()}
        self.bot.user_aps[217288785803608074] = 9999


    @app_commands.command(name="daily", description="Claim your daily rewards.")
    async def daily(self, interaction: discord.Interaction):
        amount = 200
        user_id = str(interaction.user.id)
        if user_id in self.bot.claimed:
            await interaction.response.send_message("You have already claimed your daily rewards today!", ephemeral=True)
            return

        async with aiosqlite.connect('data/main.db') as db:
            await db.execute("UPDATE users SET gold = gold + ?, coolness = coolness + 50 WHERE user_id = ?", (amount, user_id,))
            await db.commit()

        self.bot.claimed.append(user_id)
        await interaction.response.send_message(f"⭐ | You have claimed your daily rewards of {amount} gold and 50 coolness!", ephemeral=True)

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
    await bot.add_cog(rollover(bot))
