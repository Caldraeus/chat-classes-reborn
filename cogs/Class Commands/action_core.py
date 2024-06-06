import discord
from discord.ext import commands
import aiosqlite
import helper as h
import json
import random

class action_core(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.class_actions = {}
        with open('data/class_hooks.json', "r") as f:
            self.hooks_data = json.loads(f.read())

    @commands.Cog.listener()
    async def on_ready(self):
        await self.load_class_actions()

    async def load_class_actions(self):
        """Load actions and AP costs for each class from the database into memory."""
        async with aiosqlite.connect('data/main.db') as db:
            cursor = await db.execute("SELECT class_name, commands FROM classes")
            class_data = await cursor.fetchall()
            for class_name, commands in class_data:
                if commands:  # Ensure commands is not None
                    action_list = commands.split('|')
                    self.class_actions[class_name] = {
                        self.simplify_action_name(action): self.extract_ap_cost(action) 
                        for action in action_list if action.strip()
                    }
        print(self.class_actions)

    async def autocomplete_action(self, interaction: discord.Interaction, current: str) -> list:
        user_id = interaction.user.id
        user_class = await self.get_user_class(user_id)
        if user_class in self.class_actions:
            actions = self.class_actions[user_class]
            return [
                discord.app_commands.Choice(name=action, value=action)
                for action in actions if current.lower() in action.lower()
            ]
        return []

    def simplify_action_name(self, action_str):
        # Check if the action string is not empty
        if action_str:
            parts = action_str.split()
            # Check if there are enough parts to avoid IndexError
            if len(parts) > 1:
                return parts[1]  # Assumes the action is always the second word
            else:
                return "Undefined Action"  # Default fallback if not enough parts
        else:
            print("Received empty action string.")
            return "Undefined Action"  # Handling empty or malformed action strings


    async def get_user_class(self, user_id):
        async with aiosqlite.connect('data/main.db') as db:
            cursor = await db.execute("""
                SELECT class_name FROM classes
                JOIN users ON classes.class_id = users.class_id
                WHERE users.user_id = ?;
            """, (user_id,))
            result = await cursor.fetchone()
            return result[0] if result else None

    async def get_action_ap_cost(self, user_id, action_name):
        """
        Fetches the AP cost for a specific action based on the user's class.

        :param user_id: The user's ID to determine their class and available actions.
        :param action_name: The name of the action to fetch the AP cost for.
        :return: The AP cost of the action if found, otherwise None if the action does not exist.
        """
        async with aiosqlite.connect('data/main.db') as db:
            cursor = await db.execute("""
                SELECT commands FROM classes
                JOIN users ON classes.class_id = users.class_id
                WHERE users.user_id = ?;
            """, (user_id,))
            result = await cursor.fetchone()
            if result:
                actions = result[0].split('|')
                for action in actions:
                    if action_name in action:
                        return self.extract_ap_cost(action)
        return None  # Return None if no action found or no AP cost associated

    def extract_ap_cost(self, action_str):
        """Extracts the AP cost from an action string formatted as '/action name @target (X AP)'."""
        import re
        match = re.search(r'\((\d+) AP\)', action_str)
        return int(match.group(1)) if match else 0

    @discord.app_commands.command(name="action", description="Perform an action, optionally targeting another user.")
    @discord.app_commands.describe(action="The action you want to perform.")
    @discord.app_commands.describe(target="Optional target user for the action.")
    @discord.app_commands.autocomplete(action=autocomplete_action)
    async def action(self, interaction: discord.Interaction, action: str, target: discord.Member = None):
        user_id = interaction.user.id
        user_class = await self.get_user_class(user_id)  # Retrieve user's class

        # Retrieve the AP cost using the preloaded class action data
        # This also validates their class to action.
        action_ap_cost = self.class_actions.get(user_class, {}).get(action)

        if action_ap_cost is not None:
            try:
                # Attempt to alter AP based on the cost of the action
                await h.alter_ap(self.bot, user_id, action_ap_cost)

                # Handle the action if AP was successfully deducted
                if "blast" in action:
                    await self.handle_blast(interaction, target, user_class)
                elif "slice" in action:
                    await self.handle_slice(interaction, target, user_class)
                elif "shank" in action:
                    await self.handle_shank(interaction, target, user_class)
                elif "shoot" in action:
                    await self.handle_shoot(interaction, target, user_class)
            except h.APError as e:
                await interaction.response.send_message(str(e), ephemeral=True)
            except Exception as e:
                await interaction.response.send_message(f"An error occurred: {str(e)}", ephemeral=True)
        else:
            await interaction.response.send_message(f"Action '{action}' is not available or not applicable for your class {user_class}.", ephemeral=True)
    
    """
    ========================= ACTION FUNCTIONS ==========================
    ===== This area is where we will contain ALL. I reapeat, ALL of =====
    ===== the unique class code for their actions. It is likely to  =====
    ===== going to get messy and hard to follow, but using a CTRL + =====
    ===== F search for class names will likely help. Godspeed, self =====
    =====================================================================
    """
    async def handle_blast(self, interaction, target, user_class):
        if not target or target == interaction.user or target.id == 1243216875622764574:
            await interaction.response.send_message("Invalid target for attacking.", ephemeral=True)
            return

        # Example critical hit check, simplified
        is_critical = await h.crit_handler(self.bot, interaction.user, target, interaction.channel)

        if user_class == 'Apprentice':
            if is_critical:
                hook = random.choice(self.hooks_data["apprentice"]["crit"])
                additional_msg = "**✨[CRITICAL]✨** + 100 Coolness | "
                await h.add_coolness(interaction.user.id, 100)
            else:
                hook = random.choice(self.hooks_data["apprentice"]["normal"])
                additional_msg = ""

        hook = hook.replace("usr1", f"**{interaction.user.display_name}**")
        hook = hook.replace("usr2", f"**{target.display_name}**")
        hook = hook.replace('bdypart', random.choice(h.body_parts))
        await interaction.response.send_message(additional_msg + hook)

    async def handle_slice(self, interaction, target, user_class):
        if not target or target == interaction.user or target.id == 1243216875622764574:
            await interaction.response.send_message("Invalid target for attacking.", ephemeral=True)
            return

        # Example critical hit check, simplified
        is_critical = await h.crit_handler(self.bot, interaction.user, target, interaction.channel)

        if user_class == 'Swordsman':
            if is_critical:
                hook = random.choice(self.hooks_data["swordsman"]["crit"])
                additional_msg = "**✨[CRITICAL]✨** + 100 Coolness | "
                await h.add_coolness(interaction.user.id, 100)
            else:
                hook = random.choice(self.hooks_data["swordsman"]["normal"])
                additional_msg = ""

        hook = hook.replace("usr1", f"**{interaction.user.display_name}**")
        hook = hook.replace("usr2", f"**{target.display_name}**")
        hook = hook.replace('bdypart', random.choice(h.body_parts))
        await interaction.response.send_message(additional_msg + hook)

    async def handle_shank(self, interaction, target, user_class):
        if not target or target == interaction.user or target.id == 1243216875622764574:
            await interaction.response.send_message("Invalid target for attacking.", ephemeral=True)
            return

        # Example critical hit check, simplified
        is_critical = await h.crit_handler(self.bot, interaction.user, target, interaction.channel)

        if user_class == 'Rogue':
            if is_critical:
                hook = random.choice(self.hooks_data["shank"]["crit"])
                additional_msg = "**✨[CRITICAL]✨** + 125 Coolness | "
                await h.add_coolness(interaction.user.id, 125)
            else:
                hook = random.choice(self.hooks_data["rogue"]["normal"])
                additional_msg = ""

        hook = hook.replace("usr1", f"**{interaction.user.display_name}**")
        hook = hook.replace("usr2", f"**{target.display_name}**")
        hook = hook.replace('bdypart', random.choice(h.body_parts))
        await interaction.response.send_message(additional_msg + hook)

    async def handle_shoot(self, interaction, target, user_class):
        if not target or target == interaction.user or target.id == 1243216875622764574:
            await interaction.response.send_message("Invalid target for attacking.", ephemeral=True)
            return

        # Example critical hit check, simplified
        is_critical = await h.crit_handler(self.bot, interaction.user, target, interaction.channel)

        if user_class == 'Archer':
            if is_critical:
                hook = random.choice(self.hooks_data["archer"]["crit"])
                additional_msg = "**✨[CRITICAL]✨** + 100 Coolness | "
                await h.add_coolness(interaction.user.id, 100)
            else:
                hook = random.choice(self.hooks_data["archer"]["normal"])
                additional_msg = ""

        hook = hook.replace("usr1", f"**{interaction.user.display_name}**")
        hook = hook.replace("usr2", f"**{target.display_name}**")
        hook = hook.replace('bdypart', random.choice(h.body_parts))
        await interaction.response.send_message(additional_msg + hook)

async def setup(bot):
    await bot.add_cog(action_core(bot))