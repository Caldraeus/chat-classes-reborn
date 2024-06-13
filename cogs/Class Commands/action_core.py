import discord
from discord.ext import commands
import aiosqlite
import helper as h
import json
import random
import sys
from ..views import nc_class_views as v
import math
import asyncio
import signal
import pickle

class action_core(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.variables_to_save = {
            'pyrolevels': {},
            'waterlevels': {},
            'earth_shards': {},
            'nomad_homes': {},
            'ashen_sage_cinders': {},
            'soulcrusher_souls': {}
        }

        # Load state variables asynchronously and setup defaults
        asyncio.create_task(self.load_and_initialize_variables())

        # Initialize your action handlers and other structures
        self.action_handlers_with_target = {
            "blast": self.handle_blast,
            "slice": self.handle_slice,
            "ignite": self.handle_ignite,
            "douse": self.handle_douse,
            "shank": self.handle_shank,
            "shoot": self.handle_shoot,
            "stone": self.handle_stone,
            "punch": self.handle_punch,
            "trade": self.handle_trade
        }

        self.action_handlers_without_target = {
            "study": self.handle_study,
            "crime": self.handle_crime,
            "perform": self.handle_perform,
            "home": self.handle_home,
            "consume": self.handle_consume
        }

        # Load JSON data for class-specific hooks
        self.class_actions = {}
        self.load_class_actions_from_json()

    async def load_and_initialize_variables(self):
        try:
            with open('data/action_core_state.pkl', 'rb') as file:
                data = pickle.load(file)
                for key in self.variables_to_save:
                    setattr(self, key, data.get(key, self.variables_to_save[key]))
        except FileNotFoundError:
            self.set_default_values()

    def set_default_values(self):
        # Set default values for all your variables
        self.pyrolevels = {}
        self.waterlevels = {}
        self.earth_shards = {}
        self.nomad_homes = {}
        self.ashen_sage_cinders = {}
        self.soulcrusher_souls = {}
        # Initialize additional variables if needed

    async def save_variables(self):
        try:
            data = {key: getattr(self, key) for key in self.variables_to_save}
            with open('data/action_core_state.pkl', 'wb') as file:
                pickle.dump(data, file)
            print(f"{self.__class__.__name__}: Variables saved successfully.")
        except Exception as e:
            print(f"{self.__class__.__name__}: Failed to save variables due to {e}")


    def load_class_actions_from_json(self):
        with open('data/class_hooks.json', "r") as f:
            self.hooks_data = json.loads(f.read())

    def cog_unload(self):
        """Handle tasks on cog unload."""
        asyncio.create_task(self.save_variables())

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
        user_class = await h.get_user_class(user_id)
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
        user_class = await h.get_user_class(user_id)  # Retrieve user's class

        # Retrieve the AP cost using the preloaded class action data
        action_ap_cost = self.class_actions.get(user_class, {}).get(action)

        if action_ap_cost is not None:
            try:
                # Attempt to alter AP based on the cost of the action
                await h.alter_ap(self.bot, user_id, action_ap_cost)

                action_key = action.split()[0]
                
                if action_key in self.action_handlers_with_target:
                    handler = self.action_handlers_with_target[action_key]
                    await handler(interaction, target, user_class)
                elif action_key in self.action_handlers_without_target:
                    handler = self.action_handlers_without_target[action_key]
                    await handler(interaction, user_class)
                else:
                    await interaction.response.send_message(f"Action '{action}' is not available or not applicable for your class {user_class}.", ephemeral=True)
            except h.APError as e:
                await interaction.response.send_message(str(e), ephemeral=True)
            except h.AttackBlockedError as e:
                pass
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
    async def handle_trade(self, interaction, target, user_class=None):
        # Get the user's inventory
        inventory = await h.get_user_inventory(interaction.user.id)
        if not inventory:
            await interaction.response.send_message("You do not have any items to trade.", ephemeral=True)
            return

        # Create a dropdown menu for the user to select an item from their inventory
        view = v.TradeView(inventory, target)
        await interaction.response.send_message("Select an item to trade:", view=view, ephemeral=True)

    async def handle_study(self, interaction, user_class):
        is_critical = await h.crit_handler(self.bot, interaction.user, None, interaction)

        user_level = await h.get_user_level(interaction.user.id)

        # Calculate base XP based on the user's level
        max_xp = h.max_xp(user_level)
        base_xp = random.randint(max_xp // 50, (max_xp // 50)*2)  # A reasonable portion of max_xp, adjustable as needed

        # Adjust XP for critical hits
        is_critical = await h.crit_handler(self.bot, interaction.user, None, interaction)
        xp_gain = base_xp * 2 if is_critical else base_xp

        if user_class == 'Scholar':
            if is_critical:
                additional_msg = "**💡[EPIPHANY]💡** | "
                hook = random.choice(self.hooks_data[user_class.lower()]["crit"])
            else:
                hook = random.choice(self.hooks_data[user_class.lower()]["normal"])
                additional_msg = ""
        hook = hook.replace("usr1", f"**{interaction.user.display_name}**")
        hook = hook.replace('bdypart', random.choice(h.body_parts))
        await h.add_xp(interaction.user.id, xp_gain)
        await interaction.response.send_message(additional_msg + hook + f" **(+{xp_gain} XP)**")

    async def handle_consume(self, interaction, user_class=None):
        if self.ashen_sage_cinders.get(interaction.user.id, 0) == 0:
            await interaction.response.send_message('🔥 | You have no cinders to consume.', ephemeral=True)
        else:
            cinder_count = self.ashen_sage_cinders.get(interaction.user.id, 0)

            if cinder_count >= 10:
                await h.grant_achievement(interaction.channel, interaction.user.id, 9)

            ap_regain = await self.calculate_ap_gain_ashen(cinder_count)
            gold = round((ap_regain ** 2)**1.5)
            await interaction.response.send_message(f'🔥 | You consume your {cinder_count} cinders... you regain **{ap_regain}** AP and gain **{gold}** Gold!', ephemeral=False)
            await h.add_ap(self.bot, interaction.user.id, ap_regain)
            await h.add_gold(interaction.user.id, gold)
            self.ashen_sage_cinders[interaction.user.id] = 0

    async def handle_home(self, interaction, user_class=None):
        # Use helper function to find the nomad of the current channel
        current_channel_home_owner = await self.get_channel_nomad(interaction.channel.id)

        message = ""

        if current_channel_home_owner:
            # Get the owner's user object
            owner = await self.bot.fetch_user(current_channel_home_owner)
            owner_name = owner.display_name if owner else "an unknown user"

            if interaction.user.id == current_channel_home_owner:
                message += f"This channel is your home, **{owner_name}**!"
            else:
                message += f"This channel is currently the home of **{owner_name}**."
        else:
            message += "This channel is not claimed as a home by any nomad."

        # Use helper function to find the home channel of the interacting user
        user_home_channel_id = await self.get_nomad_home(interaction.user.id)

        if user_home_channel_id:
            user_home_channel = self.bot.get_channel(user_home_channel_id)
            if user_home_channel:
                message += f" Your home is in **#{user_home_channel.name}**."
            else:
                message += " It seems your home is in a channel that might no longer exist."
        else:
            message += " You do not have a home set."

        await interaction.response.send_message(message, ephemeral=True)

    async def handle_blast(self, interaction, target, user_class):
        if not target or target == interaction.user or target.id == 1243216875622764574:
            await interaction.response.send_message("Invalid target for attacking.", ephemeral=True)
            return

        # Example critical hit check, simplified
        is_critical = await h.crit_handler(self.bot, interaction.user, target, interaction)

        additional_msg = ""
        hook = ""

        if user_class in ['Apprentice', 'Dark Mage', 'Toxinmancer', 'Soulcrusher']:
            # Handle critical hits
            if is_critical:
                hook = random.choice(self.hooks_data[user_class.lower()]["crit"])
                if user_class == 'Toxinmancer':
                    hook += '\n\nusr2 is badly *poisoned*!'
                    additional_msg = "**<:poison:1250164881139826738>[CRITICAL]<:poison:1250164881139826738>** + 100 Coolness |"
                    await self.bot.get_cog("statuses").apply_status_effect(target.id, 'poisoned', stacks=random.randint(2,4))
                elif user_class == 'Soulcrusher':
                    if target.id in self.soulcrusher_souls.get(interaction.user.id, []):
                        # Soul already claimed, now crushed
                        hook = random.choice(self.hooks_data[user_class.lower()]["soulcrush"]) + '\n\nusr2 feels *Fatigued!*'
                        additional_coolness = 500 + 100 * (len(self.soulcrusher_souls[interaction.user.id]) - 1)
                        additional_msg = f"**💥[SOUL CRUSHED]💥** + {additional_coolness} Coolness | "
                        await h.add_coolness(interaction.user.id, additional_coolness)
                        await self.bot.get_cog("statuses").apply_status_effect(target.id, 'fatigued', stacks=(len(self.soulcrusher_souls[interaction.user.id])))
                        self.soulcrusher_souls[interaction.user.id].remove(target.id)  # Remove the soul after crushing
                        if not self.soulcrusher_souls[interaction.user.id]:  # Remove key if list is empty
                            del self.soulcrusher_souls[interaction.user.id]
                    else:
                        # Attempt to steal the soul
                        self.soulcrusher_souls.setdefault(interaction.user.id, []).append(target.id)
                        additional_msg = "**💀[SOUL STOLEN]💀** + 100 Coolness | "
                        await h.add_coolness(interaction.user.id, 100)
                else:
                    additional_msg = "**✨[CRITICAL]✨** + 100 Coolness | "
                await h.add_coolness(interaction.user.id, 100)
            else:
                # Normal hit
                hook = random.choice(self.hooks_data[user_class.lower()]["normal"])

        # Replace placeholders
        hook = hook.replace("usr1", f"**{interaction.user.display_name}**")
        hook = hook.replace("usr2", f"**{target.display_name}**")
        hook = hook.replace('bdypart', random.choice(h.body_parts))

        # Send final message
        await interaction.response.send_message(additional_msg + hook)

    async def handle_punch(self, interaction, target, user_class):
        if not target or target == interaction.user or target.id == 1243216875622764574:
            await interaction.response.send_message("Invalid target for attacking.", ephemeral=True)
            return

        # Example critical hit check, simplified
        is_critical = await h.crit_handler(self.bot, interaction.user, target, interaction)

        if user_class == 'Boxer':
            if is_critical:
                hook = random.choice(self.hooks_data[user_class.lower()]["crit"]) + f"\n\n***{target.display_name}** loses 2 AP from the beating!*"
                additional_msg = "**🥊[KNOCKOUT]🥊** + 100 Coolness | "
                await h.add_coolness(interaction.user.id, 100)
                await h.deduct_ap(self.bot, target.id, 2)
            else:
                hook = random.choice(self.hooks_data[user_class.lower()]["normal"])
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
        is_critical = await h.crit_handler(self.bot, interaction.user, target, interaction)

        if user_class == 'Swordsman' or user_class == 'Warrior':
            if is_critical:
                hook = random.choice(self.hooks_data[user_class.lower()]["crit"])
                additional_msg = "**✨[CRITICAL]✨** + 100 Coolness | "
                await h.add_coolness(interaction.user.id, 100)
            else:
                hook = random.choice(self.hooks_data[user_class.lower()]["normal"])
                additional_msg = ""
        elif user_class == 'Samurai':
            if is_critical:
                hook = random.choice(self.hooks_data[user_class.lower()]["crit"])
                additional_msg = "**🌸[SENBONZAKURA!]🌸** + 250 Coolness | "
                await h.add_coolness(interaction.user.id, 100)
            else:
                hook = random.choice(self.hooks_data[user_class.lower()]["normal"])
                additional_msg = ""

        hook = hook.replace("usr1", f"**{interaction.user.display_name}**")
        hook = hook.replace("usr2", f"**{target.display_name}**")
        hook = hook.replace('bdypart', random.choice(h.body_parts))
        await interaction.response.send_message(additional_msg + hook)

    async def handle_crime(self, interaction, user_class):
        # Crime handling logic
        is_critical = await h.crit_handler(self.bot, interaction.user, None, interaction)
        user_level = await h.get_user_level(interaction.user.id)
        reward_str = random.choice(['exp', 'gold', 'coolness'])
        reward_value = random.randint(50, 150)

        # Calculate base XP based on the user's level
        if reward_str == 'exp':  # Need scaling to make this worth it as a reward.
            max_xp = h.max_xp(user_level)
            base_xp = random.randint(max_xp // 100, (max_xp // 100) * 2)  # A reasonable portion of max_xp, adjustable as needed
            reward_value = base_xp
        elif reward_str == 'gold':
            reward_value /= 2

        # Adjust XP for critical hits
        if user_class == 'Criminal':
            if is_critical:
                hook = random.choice(self.hooks_data[user_class.lower()]["crime-crit"]) + f" **(+{reward_value * 2} {reward_str})**"
                additional_msg = f"**💰[HUGE SUCCESS]💰** | "
                reward_value *= 2
            elif is_critical is None:
                hook = random.choice(self.hooks_data[user_class.lower()]["crime-fail"]) + "\n\nYou lose *all* of your AP!"
                additional_msg = f"**🚔[BUSTED]🚔** | "
                self.bot.user_aps[interaction.user.id] = 0
            else:
                hook = random.choice(self.hooks_data[user_class.lower()]["crime"]) + f" **(+{reward_value} {reward_str})**"
                additional_msg = ""

        hook = hook.replace("usr1", f"**{interaction.user.display_name}**")
        hook = hook.replace('bdypart', random.choice(h.body_parts))
        await interaction.response.send_message(additional_msg + hook)

        # Update the user's rewards in the database
        async with aiosqlite.connect('data/main.db') as db:
            await db.execute(f"UPDATE users SET {reward_str} = {reward_str} + ? WHERE user_id = ?", (reward_value, interaction.user.id))
            await db.commit()


    async def handle_shank(self, interaction, target, user_class):
        if not target or target == interaction.user or target.id == 1243216875622764574:
            await interaction.response.send_message("Invalid target for attacking.", ephemeral=True)
            return

        # Example critical hit check, simplified
        is_critical = await h.crit_handler(self.bot, interaction.user, target, interaction)

        if is_critical:
            hook = random.choice(self.hooks_data[user_class.lower()]["crit"])
            amount = 125 if user_class == 'Rogue' else 100
            additional_msg = f"**✨[CRITICAL]✨** + {amount} Coolness | "
            if user_class == 'Nomad' and await self.get_channel_nomad(interaction.channel_id) == None and await self.get_nomad_home(interaction.user.id) == None:
                hook += f'\n\n*{interaction.user.display_name} claims this channel as their home for the day!*'
                self.nomad_homes[interaction.channel.id] = interaction.user.id
            await h.add_coolness(interaction.user.id, amount)
        else:
            hook = random.choice(self.hooks_data[user_class.lower()]["normal"])
            additional_msg = ""

        hook = hook.replace("usr1", f"**{interaction.user.display_name}**")
        hook = hook.replace("usr2", f"**{target.display_name}**")
        hook = hook.replace('bdypart', random.choice(h.body_parts))
        await interaction.response.send_message(additional_msg + hook)

    async def handle_shoot(self, interaction, target, user_class):
        if not target or target == interaction.user or target.id == 1243216875622764574:
            await interaction.response.send_message("Invalid target for attacking.", ephemeral=True)
            return

        is_critical = await h.crit_handler(self.bot, interaction.user, target, interaction)
        print(is_critical)

        # Determine the appropriate message hook based on user class and critical hit
        hook_key = "crit" if is_critical == True else "normal"
        if user_class in ['Archer', 'Hunter', 'Gunner', 'Tamer']:
            hook = random.choice(self.hooks_data[user_class.lower()][hook_key])
            additional_msg = ""

            # Set specific messages and actions for critical hits
            if is_critical:
                if user_class in ['Archer', 'Hunter', 'Tamer']:
                    additional_msg = "**✨[CRITICAL]✨** + 100 Coolness | "
                    await h.add_coolness(interaction.user.id, 100)
                elif user_class == 'Gunner':
                    additional_msg = "**🎯[HEADSHOT]🎯** + 200 Coolness | "
                    await h.add_coolness(interaction.user.id, 200)

                # Additional status effect for Hunter
                if user_class == 'Hunter':
                    hook += f'\n\nusr1 has been *marked* by usr2!'
                    await self.bot.get_cog("statuses").apply_status_effect(target.id, 'marked', stacks=1)

        # Replace placeholders in the hook
        hook = hook.replace("usr1", f"**{interaction.user.display_name}**")
        hook = hook.replace("usr2", f"**{target.display_name}**")
        hook = hook.replace('bdypart', random.choice(h.body_parts))

        # Send the final response message
        await interaction.response.send_message(additional_msg + hook)

    async def handle_ignite(self, interaction, target, user_class):
        if not target or target == interaction.user or target.id == 1243216875622764574:
            await interaction.response.send_message("Invalid target for attacking.", ephemeral=True)
            return

        is_critical = await h.crit_handler(self.bot, interaction.user, target, interaction)

        # Ensure pyrolevels for the user is initialized
        if (current_pyro_level := self.pyrolevels.get(interaction.user.id)) is None:
            self.pyrolevels[interaction.user.id] = current_pyro_level = 0

        additional_msg = ""
        hook = ""

        if user_class in ['Pyromancer', 'Flameborn', 'Ashen Sage', 'Pyrokinetic']:
            # Handle critical hits
            if is_critical:
                hook = random.choice(self.hooks_data[user_class.lower()]["crit"])
                additional_msg = "**✨[CRITICAL]✨** + 100 Coolness | "
                await h.add_coolness(interaction.user.id, 100)
            elif current_pyro_level >= 100:
                # Handle overheat scenario
                hook = random.choice(self.hooks_data[user_class.lower()]["overheat"])

                if user_class == 'Ashen Sage': # Moved logic to overheat.
                    additional_msg = "**🔥[OVERHEAT!]🔥** + 75 Coolness, +1 Cinder | "
                else:
                    additional_msg = "**🔥[OVERHEAT!]🔥** + 75 Coolness | "
                await h.add_coolness(interaction.user.id, 75)
                self.pyrolevels[interaction.user.id] = -10

                # Apply specific class effects
                if user_class == 'Flameborn':
                    statuses = self.bot.get_cog('statuses')
                    await statuses.apply_status_effect(interaction.user.id, 'embershield', stacks=random.randint(3, 5))
                    hook += '\n\n*usr1 forms an Embershield!*'
                elif user_class == 'Ashen Sage':
                    if (cinders := self.ashen_sage_cinders.get(interaction.user.id)) is None:
                        self.ashen_sage_cinders[interaction.user.id] = cinders = 1
                    else:
                        self.ashen_sage_cinders[interaction.user.id] += 1
            else:
                # Normal hit
                hook = random.choice(self.hooks_data[user_class.lower()]["normal"])

        # Increment pyro level if not overheated
        if current_pyro_level <= 100:
            self.pyrolevels[interaction.user.id] += random.randint(1, 17)
            if user_class == 'Pyrokinetic':
                self.pyrolevels[interaction.user.id] *= 2
            for temp, message in self.pyro_intensities:
                if self.pyrolevels[interaction.user.id] <= temp:
                    hook += f"\n\n*{interaction.user.display_name}'s inner fire {message} at {self.pyrolevels[interaction.user.id]+20}°C...*"
                    break

        # Add Ashen Sage cinders count
        if user_class == 'Ashen Sage' and self.ashen_sage_cinders.get(interaction.user.id) is not None and self.ashen_sage_cinders.get(interaction.user.id) != 0:
            hook += f"\n\n*usr1 currently has {self.ashen_sage_cinders[interaction.user.id]} ashes!*"

        # Replace placeholders
        hook = hook.replace("usr1", f"**{interaction.user.display_name}**")
        hook = hook.replace("usr2", f"**{target.display_name}**")
        hook = hook.replace('bdypart', random.choice(h.body_parts))

        # Send final message
        await interaction.response.send_message(additional_msg + hook)
    
    async def handle_perform(self, interaction, user_class):
        is_critical = await h.crit_handler(self.bot, interaction.user, None, interaction)
        user_level = await h.get_user_level(interaction.user.id)
        reward_str = random.choice(['exp', 'gold', 'coolness'])

        # Calculate base XP based on the user's level
        if reward_str == 'exp':  # Need scaling to make this worth it as a reward.
            max_xp = h.max_xp(user_level)
            base_xp = random.randint(max_xp // 100, (max_xp // 100) * 2)  # A reasonable portion of max_xp, adjustable as needed
            reward_value = base_xp
        else:
            reward_value = random.randint(50, 150)

        # Adjust XP for critical hits
        if user_class == 'Entertainer':
            if is_critical:
                hook = random.choice(self.hooks_data[user_class.lower()]["normal"]) + f" **(+{reward_value * 2} {reward_str})**"
                additional_msg = f"**🎵[ENCORE]🎵** | "
                reward_value *= 2
                random_users = await h.get_random_users(self.bot, interaction.guild_id, 3)
                hook += f'\n\n{h.format_user_list(random_users)} are *inspired!*' if random_users != [] else '\n\nThere\'s no one around to inspire...'
                for user in random_users:
                    await self.bot.get_cog("statuses").apply_status_effect(user.id, 'inspired', stacks=5)
            else:
                hook = random.choice(self.hooks_data[user_class.lower()]["crit"]) + f" **(+{reward_value} {reward_str})**"
                additional_msg = ""

        hook = hook.replace("usr1", f"**{interaction.user.display_name}**")
        hook = hook.replace('bdypart', random.choice(h.body_parts))
        await interaction.response.send_message(additional_msg + hook)
        
        # Update the user's rewards in the database
        async with aiosqlite.connect('data/main.db') as db:
            await db.execute(f"UPDATE users SET {reward_str} = {reward_str} + ? WHERE user_id = ?", (reward_value, interaction.user.id))
            await db.commit()

    def format_user_list(users):
        """
        Formats a list of Discord Member objects into a grammatically correct string.

        :param users: A list of discord.Member objects.
        :return: A formatted string.
        """
        if not users:
            return None

        # Extract display names and bold them
        user_names = [f"**{user.display_name}**" for user in users]

        # Format based on the number of users
        if len(user_names) == 1:
            return user_names[0]
        elif len(user_names) == 2:
            return f"{user_names[0]} and {user_names[1]}"
        else:
            return ', '.join(user_names[:-1]) + f", and {user_names[-1]}"

    async def handle_douse(self, interaction, target, user_class):
        if not target or target == interaction.user or target.id == 1243216875622764574:
            await interaction.response.send_message("Invalid target for attacking.", ephemeral=True)
            return

        # Example critical hit check, simplified
        is_critical = await h.crit_handler(self.bot, interaction.user, target, interaction)

        if user_class == 'Hydromancer':
            restoration_amount = 5 # Amount of AP an overflow restores.
            if (current_water_level := self.waterlevels.get(interaction.user.id)) is None:
                self.waterlevels[interaction.user.id] = current_water_level = 0
            if is_critical:
                hook = random.choice(self.hooks_data[user_class.lower()]["crit"])
                additional_msg = "**✨[CRITICAL]✨** + 100 Coolness | "
                await h.add_coolness(interaction.user.id, 100)
            elif current_water_level >= 100:
                hook = random.choice(self.hooks_data[user_class.lower()]["overflow"])
                additional_msg = f"**💧[OVERFLOW]💧** + {restoration_amount} AP | "
                await h.set_ap(self.bot, interaction.user.id, 0)
                self.waterlevels[interaction.user.id] = 0
            else:
                hook = random.choice(self.hooks_data[user_class.lower()]["normal"])
                additional_msg = ""

        if current_water_level <= 100:
            self.waterlevels[interaction.user.id] += random.randint(0,20)
            for temp, message in self.water_intensities:
                if self.waterlevels[interaction.user.id] <= temp:
                    hook +=  f"\n\n*usr1's water level {message} at {min(self.waterlevels.get(interaction.user.id, 0), 100)}%.*"
                    break

        hook = hook.replace("usr1", f"**{interaction.user.display_name}**")
        hook = hook.replace("usr2", f"**{target.display_name}**")
        hook = hook.replace('bdypart', random.choice(h.body_parts))
        await interaction.response.send_message(additional_msg + hook)

    async def handle_stone(self, interaction, target, user_class):
        if not target or target == interaction.user or target.id == 1243216875622764574:
            await interaction.response.send_message("Invalid target for attacking.", ephemeral=True)
            return

        # Example critical hit check, simplified
        is_critical = await h.crit_handler(self.bot, interaction.user, target, interaction)

        if user_class == 'Terramancer':
            if (current_shards := self.earth_shards.get(interaction.user.id)) is None:
                self.earth_shards[interaction.user.id] = current_shards = 0
            
            if current_shards >= 5:
                hook = random.choice(self.hooks_data[user_class.lower()]["mega-crit"])
                additional_msg = "**🪨[MEGA-CRIT!]🪨** + 750 Coolness | "
                await h.add_coolness(interaction.user.id, 750)
                self.earth_shards[interaction.user.id] = 0
            elif is_critical:
                hook = random.choice(self.hooks_data[user_class.lower()]["crit"])
                additional_msg = "**✨[CRITICAL]✨** + 100 Coolness, +1 Earth Shard | "
                self.earth_shards[interaction.user.id] = current_shards + 1
                await h.add_coolness(interaction.user.id, 100)
            else:
                hook = random.choice(self.hooks_data[user_class.lower()]["normal"])
                additional_msg = ""
        
        if current_shards > 0 and current_shards < 5:
            hook += f"\n\n*usr1 has {current_shards}/5 Earth Shards!*"

        hook = hook.replace("usr1", f"**{interaction.user.display_name}**")
        hook = hook.replace("usr2", f"**{target.display_name}**")
        hook = hook.replace('bdypart', random.choice(h.body_parts))
        await interaction.response.send_message(additional_msg + hook)

    async def get_channel_nomad(self, channel_id):
        """
        Returns the nomad ID who has claimed the channel as their home.

        :param channel_id: The ID of the channel.
        :return: The user ID of the nomad or None if the channel is not claimed.
        """
        return self.nomad_homes.get(channel_id, None)


    async def get_nomad_home(self, nomad_id):
        """
        Returns the home channel ID of a nomad.

        :param nomad_id: The user ID of the nomad.
        :return: The channel ID of the nomad's home or None if not set.
        """
        inverted_homes = {v: k for k, v in self.nomad_homes.items()}
        return inverted_homes.get(nomad_id, None)

    async def calculate_ap_gain_ashen(self, stacks: int) -> int:
        if stacks <= 10:
            # Exponential growth to gradually reach 10 AP
            ap_gain = 10 * (1 - math.exp(-0.3 * stacks))
        else:
            # Apply diminishing returns for stacks greater than 10
            base_ap = 10 * (1 - math.exp(-0.3 * stacks))
            diminishing_stacks = stacks - base_ap
            diminishing_ap = diminishing_stacks ** 0.5  # Example of diminishing returns formula
            ap_gain = base_ap + diminishing_ap

        return round(ap_gain)

async def setup(bot):
    await bot.add_cog(action_core(bot))