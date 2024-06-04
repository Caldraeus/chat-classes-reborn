import discord
from discord.ext import commands
import aiosqlite
import helper as h
import json

class action_core(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Initialize the dispatch dictionary
        # self.action_dispatch = {
        #     ('apprentice', 'attack'): self.basic_attack,
        #     ('swordsman', 'attack'): self.basic_attack,
        #     ('archer', 'attack'): self.basic_attack,
        #     ('rogue', 'attack'): self.basic_attack
        #     # Add other class and action combinations
        # }
        with open('data/class_hooks.json', "r") as f:
            self.class_hooks = json.loads(f.read())

    @discord.app_commands.command(name="action", description="Perform an action, optionally targeting another user.")
    @discord.app_commands.describe(action="The action you want to perform.")
    @discord.app_commands.describe(target="Optional target user for the action.")
    async def action(self, interaction: discord.Interaction, action: str, target: discord.Member = None):
        # Handle the action based on the selected command and target
        if target:
            response = f"{action.capitalize()} targeting {target.display_name} performed!"
        else:
            response = f"{action.capitalize()} performed!"

        await interaction.response.send_message(response)

    @action.autocomplete('action')
    async def action_autocomplete(self, interaction: discord.Interaction, current: str):
        user_id = interaction.user.id
        actions = await self.fetch_available_actions(user_id)
        return [discord.app_commands.Choice(name=action, value=action) for action in actions if current.lower() in action.lower()]

    async def fetch_available_actions(self, user_id):
        async with aiosqlite.connect('data/main.db') as db:
            # Fetch the user's class ID based on user ID
            cursor = await db.execute("SELECT class_id FROM users WHERE user_id = ?", (user_id,))
            class_info = await cursor.fetchone()
            if class_info:
                class_id = class_info[0]
                # Fetch the commands for the class
                cursor = await db.execute("SELECT commands FROM classes WHERE class_id = ?", (class_id,))
                commands_data = await cursor.fetchone()
                if commands_data:
                    return self.process_commands(commands_data[0])
            return []

    def process_commands(self, commands_str):
        # Split the commands and process each to remove parameters and only leave the action description
        commands = commands_str.split('|')
        processed_commands = []
        for command in commands:
            # Simplifying command strings, e.g., remove parameters and details not needed for autocomplete
            if "(" in command:
                command = command[:command.index("(")].strip()
            processed_commands.append(command.replace("/action ", "").strip())
        return processed_commands

async def setup(bot):
    await bot.add_cog(action_core(bot))