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
import aiohttp
import datetime

class action_core(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # These are non-saved variables.
        self.crusade = None
        # This marks the end of the non-saved variables.
        self.variables_to_save = {
            'pyrolevels': {},
            'waterlevels': {},
            'earth_shards': {},
            'nomad_homes': {},
            'ashen_sage_cinders': {},
            'soulcrusher_souls': {},
            'rituals':  {},
            'involved': {},
            'impaled': [],
            'hired':{},
            'combos':{}
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
            "trade": self.handle_trade,
            "heal": self.handle_heal,
            "freeze": self.handle_freeze,
            "offer": self.handle_offer
        }

        self.action_handlers_without_target = {
            "study": self.handle_study,
            "crime": self.handle_crime,
            "perform": self.handle_perform,
            "home": self.handle_home,
            "consume": self.handle_consume,
            "invoke":self.handle_invoke,
            "demon":self.handle_demon,
            "pray":self.handle_pray,
            "crusade":self.handle_crusade
        }

        self.pyro_intensities = [
            (25, "kindles lightly"),
            (50, "burns"),
            (75, "burns strongly"),
            (99, "roars"),
            (150, "is about to burst")
        ]

        self.water_intensities = [
            (25, "sits lowly"),
            (50, "sits comfortably"),
            (75, "sits highly"),
            (99, "is close to overflowing"),
            (150, "starts to spill")
        ]

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
        self.rituals = {}
        self.involved = {}
        self.impaled = []
        self.hired = {},
        self.combos = {}
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
        base_xp = random.randint(max_xp // 50, (max_xp // 20))  # A reasonable portion of max_xp, adjustable as needed

        # Adjust XP for critical hits
        is_critical = await h.crit_handler(self.bot, interaction.user, None, interaction)
        xp_gain = base_xp * 2 if is_critical else base_xp

        if user_class in ['Scholar', 'Proficient Scholar']:
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
        cinder_count = self.ashen_sage_cinders.get(interaction.user.id, 0)
        if cinder_count == 0:
            await interaction.response.send_message('🔥 | You have no cinders to consume.', ephemeral=True)
        else:
            ap_regain, gold = await self.calculate_ap_gain_ashen(cinder_count, interaction)
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

        if user_class in ['Apprentice', 'Dark Mage', 'Toxinmancer', 'Soulcrusher', 'Fogwalker', 'Psychic']:
            # Handle critical hits
            if is_critical:
                hook = random.choice(self.hooks_data[user_class.lower()]["crit"])
                if user_class == 'Toxinmancer':
                    hook += '\n\nusr2 is badly *poisoned*!'
                    additional_msg = "**<:poison:1250164881139826738>[CRITICAL]<:poison:1250164881139826738>** + 100 Coolness |"
                    await self.bot.get_cog("statuses").apply_status_effect(target.id, 'poisoned', stacks=random.randint(2,4))
                elif user_class == 'Psychic':
                    additional_msg = "**:eye:[CRITICAL]:eye:** + 100 Coolness | "
                    hook += '\n\nusr2\'s mind is *Shattered!*'
                    await self.bot.get_cog("statuses").apply_status_effect(target.id, 'shattered', stacks=random.randint(5,10))
                elif user_class == 'Fogwalker':
                    additional_msg = "**✨[CRITICAL]✨** + 100 Coolness | "
                    hook += '\n\nusr1 regenerates **5 AP**!'
                    await h.add_ap(self.bot, interaction.user.id, 5)
                elif user_class == 'Soulcrusher':
                    if target.id in self.soulcrusher_souls.get(interaction.user.id, []):
                        # Soul already claimed, now crushed
                        hook = random.choice(self.hooks_data[user_class.lower()]["soulcrush"]) + '\n\nusr2 feels *Fatigued!*'
                        additional_coolness = 500 + 100 * (len(self.soulcrusher_souls[interaction.user.id]) - 1)
                        additional_msg = f"**💥[SOUL CRUSHED]💥** + {additional_coolness} Coolness | "
                        await h.add_coolness(self.bot, interaction.user.id, additional_coolness)
                        await self.bot.get_cog("statuses").apply_status_effect(target.id, 'fatigued', stacks=(len(self.soulcrusher_souls[interaction.user.id])))
                        self.soulcrusher_souls[interaction.user.id].remove(target.id)  # Remove the soul after crushing
                        if not self.soulcrusher_souls[interaction.user.id]:  # Remove key if list is empty
                            del self.soulcrusher_souls[interaction.user.id]
                    else:
                        # Attempt to steal the soul
                        self.soulcrusher_souls.setdefault(interaction.user.id, []).append(target.id)
                        additional_msg = "**💀[SOUL STOLEN]💀** + 100 Coolness | "
                else:
                    additional_msg = "**✨[CRITICAL]✨** + 100 Coolness | "
                
                await h.add_coolness(self.bot, interaction.user.id, 100)
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
                await h.add_coolness(self.bot, interaction.user.id, 100)
                await h.deduct_ap(self.bot, target.id, 2)
            else:
                hook = random.choice(self.hooks_data[user_class.lower()]["normal"])
        elif user_class == 'Underdog':
            if is_critical:
                hook = random.choice(self.hooks_data[user_class.lower()]["crit"]) + f"\n\n***{target.display_name}** is drained 5 AP from the beating!*"
                additional_msg = "**🥊[KNOCKOUT]🥊** + 100 Coolness, +5 AP | "
                await h.add_coolness(self.bot, interaction.user.id, 100)
                await h.deduct_ap(self.bot, target.id, 5)
                await h.add_ap(self.bot, interaction.user.id, 5)
            else:
                hook = random.choice(self.hooks_data[user_class.lower()]["normal"])
        elif user_class == 'Martial Artist':
            # Retrieve combo count
            combo = self.combos.get(interaction.user.id, 1)

            # Award achievement if combo is 10 or more
            if combo >= 10:
                await h.grant_achievement(interaction.channel, interaction.user, 10)

            # Perform critical hit check with combo as boost
            is_critical = await h.crit_handler(self.bot, interaction.user, target, interaction, boost=combo)

            if not is_critical:
                hook = random.choice(self.hooks_data[user_class.lower()]["normal"])
                # Increment combo count
                self.combos[interaction.user.id] = combo + 1
                additional_msg = f"**[COMBO X{combo}]** | "
            else:
                hook = random.choice(self.hooks_data[user_class.lower()]["crit"])
                # Reset combo count and handle critical hit
                self.combos[interaction.user.id] = 0
                additional_msg = "**✨[COMBO BREAKER]✨** + 100 Coolness | "
                await h.add_coolness(self.bot, interaction.user.id, 100)
        else:
            await interaction.response.send_message("Invalid user class for this action.", ephemeral=True)
            return

        hook = hook.replace("usr1", f"**{interaction.user.display_name}**")
        hook = hook.replace("usr2", f"**{target.display_name}**")
        hook = hook.replace('bdypart', random.choice(h.body_parts))
        await interaction.response.send_message(additional_msg + hook)


    async def handle_heal(self, interaction, target, user_class):
        if not target or target == interaction.user or target.id == 713506775424565370:
            await interaction.response.send_message("Invalid target for healing.", ephemeral=True)
            return

        # Example critical heal check, simplified
        is_critical = await h.crit_handler(self.bot, interaction.user, target, interaction)

        if user_class.lower() == 'healer':
            if is_critical:
                hook = random.choice(self.hooks_data[user_class.lower()]["crit"])
                additional_msg = "**✨[MIRACULOUS HEALING]✨** + 200 Coolness | "
                await h.add_coolness(self.bot, interaction.user.id, 200)
                statuses = self.bot.get_cog('statuses')
                await statuses.remove_all_negative_statuses(target.id)
                ap_healed = random.randint(5, 10)  # More AP healed on a critical
                hook += f', restoring **{ap_healed} AP** to them.\n\n*usr2 is cleansed of any negative status effects!*'
            else:
                hook = random.choice(self.hooks_data[user_class.lower()]["normal"])
                additional_msg = ""
                ap_healed = random.randint(1, 5)  # Standard AP healed
                hook += f', restoring **{ap_healed} AP** to them.'

            await h.add_ap(self.bot, target.id, ap_healed)  # Adjust AP of the target

            hook = hook.replace("usr1", f"**{interaction.user.display_name}**")
            hook = hook.replace("usr2", f"**{target.display_name}**")
            hook = hook.replace('bdypart', random.choice(h.body_parts))

            # Send the final message with coolness gain details
            await interaction.response.send_message(additional_msg + hook)

    async def handle_slice(self, interaction, target, user_class):
        if not target or target == interaction.user or target.id == 1243216875622764574:
            await interaction.response.send_message("Invalid target for attacking.", ephemeral=True)
            return
        
        # Check if the attacker is a sellsword and the target is their client
        if user_class == "Sellsword" and target.id == self.hired.get(interaction.user.id):
            await interaction.response.send_message("You cannot attack your client.", ephemeral=True)
            return

        # Initialize the critical hit boost
        boost = 0

        # Check if there is an ongoing crusade and if the attacker is a knight
        if self.crusade and user_class == 'Knight':
            boost = 9  # Crusade boosts crit chance by 9

        # Conduct the critical hit check with the possible boost
        is_critical = await h.crit_handler(self.bot, interaction.user, target, interaction, boost)

        # Determine the response based on the user class and whether the hit was critical
        hook = ""
        additional_msg = ""
        if user_class == 'Knight':
            if is_critical:
                hook = random.choice(self.hooks_data[user_class.lower()]["crit"])
                if self.crusade:
                    additional_msg = "**✨[HOLY CRITICAL]✨** + 300 Coolness | "
                    await h.add_coolness(self.bot, interaction.user.id, 300)
                else:
                    additional_msg = "**✨[CRITICAL]✨** + 100 Coolness | "
                    await h.add_coolness(self.bot, interaction.user.id, 100)
            else:
                hook = random.choice(self.hooks_data[user_class.lower()]["normal"])
                crusade_chance = random.randint(1, 1)
                
                if crusade_chance == 1 and not self.crusade:
                    asyncio.create_task(self.start_crusade(interaction))  # Start crusade with automatic ending in the background
                    hook += "\n\n🚩 | *You have started a crusade!*"
        elif user_class in ['Swordsman', 'Warrior', 'Sellsword']:
            if is_critical:
                hook = random.choice(self.hooks_data[user_class.lower()]["crit"])
                additional_msg = "**✨[CRITICAL]✨** + 100 Coolness | "
                await h.add_coolness(self.bot, interaction.user.id, 100)
            else:
                hook = random.choice(self.hooks_data[user_class.lower()]["normal"])
        elif user_class == 'Samurai':
            if is_critical:
                hook = random.choice(self.hooks_data[user_class.lower()]["crit"])
                additional_msg = "**🌸[SENBONZAKURA!]🌸** + 250 Coolness | "
                await h.add_coolness(self.bot, interaction.user.id, 250)
            else:
                hook = random.choice(self.hooks_data[user_class.lower()]["normal"])
        elif user_class == 'Spirit Blade':
            if is_critical:
                hook = random.choice(self.hooks_data[user_class.lower()]["crit"])
                additional_msg = "**🌸[SENBONZAKURA]🌸** + 250 Coolness | "
                await h.add_coolness(self.bot, interaction.user.id, 250)
                hook += '\n\n*usr1 activates their Spirit Shroud!*'
            else:
                hook = random.choice(self.hooks_data[user_class.lower()]["normal"])
        elif user_class == 'Shogun':
            if is_critical:
                hook = random.choice(self.hooks_data[user_class.lower()]["crit"])
                additional_msg = "**🌸[SENBONZAKURA!]🌸** + 250 Coolness | "
                await h.add_coolness(self.bot, interaction.user.id, 250)
                random_users = await h.get_random_users(self.bot, interaction.guild_id, 3)
                hook += f'\n\n{h.format_user_list(random_users)} are *inspired!*' if random_users != [] else '\n\nThere\'s no one around to inspire...'
                for user in random_users:
                    await self.bot.get_cog("statuses").apply_status_effect(user.id, 'inspired', stacks=10)
            else:
                hook = random.choice(self.hooks_data[user_class.lower()]["normal"])
        elif user_class == 'Swashbuckler':
            if is_critical:
                hook = random.choice(self.hooks_data[user_class.lower()]["crit"])

                targets = random.randint(2,8)
                random_users = await h.get_random_users(self.bot, interaction.guild_id, targets, self_allowed=False, active=True)
                amount = 100
                await h.add_coolness(self.bot, interaction.user.id, 100)
                if len(random_users) >= 2:
                    hook += f"\n\nYour ship's cannons fire upon {h.format_user_list(random_users)}, earning you an additional 50 coolness per target!"
                    amount += 50*targets
                else:
                    hook += "\n\nYour ship's cannons don't fire..."
                additional_msg = f"**☠️[CRITICAL!]☠️** + {amount} Coolness | "
            else:
                hook = random.choice(self.hooks_data[user_class.lower()]["normal"])
                additional_msg = ""

        hook = hook.replace("usr1", f"**{interaction.user.display_name}**")
        hook = hook.replace("usr2", f"**{target.display_name}**")
        hook = hook.replace('bdypart', random.choice(h.body_parts))
        await interaction.response.send_message(additional_msg + hook)
    
    async def handle_crusade(self, interaction, user_class=None):
        if self.crusade:
            end_timestamp = int(datetime.datetime.fromisoformat(self.crusade['end_time']).timestamp())
            await interaction.response.send_message(
                f"**🚩 Crusade is active!**\n"
                f"Started by: **{self.crusade['starter']}**\n"
                f"Start Time: <t:{int(datetime.datetime.fromisoformat(self.crusade['start_time']).timestamp())}:F>\n"
                f"End Time: <t:{end_timestamp}:R>"
            )
        else:
            await interaction.response.send_message(
                "No active crusade. The holy lands are safe, for now."
            )

    async def handle_offer(self, interaction, target, user_class):
        if user_class != "Sellsword":
            await interaction.response.send_message("Only Sellswords can offer their services.", ephemeral=True)
            return

        if not target:
            await interaction.response.send_message("You need to specify a target to offer your services.", ephemeral=True)
            return

        # Check if the Sellsword is already hired
        if interaction.user.id in self.hired:
            await interaction.response.send_message("You have already been hired for the day.", ephemeral=True)
            return

        # Check if the target has already hired a Sellsword
        if target.id in self.hired.values():
            await interaction.response.send_message("The target has already hired a Sellsword for the day.", ephemeral=True)
            return

        # Create a modal for the Sellsword to set their price
        modal = v.OfferServiceModal(self, target)
        await interaction.response.send_modal(modal)    
    
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

        if user_class == 'Thief':
            if is_critical:
                hook = random.choice(self.hooks_data[user_class.lower()]["crit"])
                additional_msg = "**✨[CRITICAL]✨** + 100 Coolness | "
                await h.add_coolness(self.bot, interaction.user.id, 100)

                steal_chance = random.randint(1, 10)

                if steal_chance == 1:
                    try:
                        async with aiosqlite.connect('data/main.db') as conn:
                            async with conn.execute(f"""
                                SELECT ui.item_id, i.item_name
                                FROM user_inventory ui
                                JOIN items i ON ui.item_id = i.item_id
                                WHERE ui.user_id = ?
                            """, (target.id,)) as chan:
                                stuff = await chan.fetchall()

                        if stuff:
                            stolen_item_id, stolen_item_name = random.choice(stuff)  # Extract item_id and item_name from the tuple
                            await h.remove_item(target.id, stolen_item_id, 1)
                            await h.give_item(interaction.user.id, stolen_item_id, 1)
                            hook += f"\n\n*{interaction.user.display_name} steals {target.display_name}'s **{stolen_item_name}**!*"
                        else:
                            hook += f"\n\n*{interaction.user.display_name} tries to steal an item, but {target.display_name} has nothing to steal!*"
                    except IndexError:
                        pass
                else:
                    gold_to_steal = 200
                    async with aiosqlite.connect('data/main.db') as conn:
                        async with conn.execute(f"SELECT gold FROM users WHERE user_id = ?", (target.id,)) as cursor:
                            result = await cursor.fetchone()
                            target_gold = result[0] if result else 0

                    if target_gold > 0:
                        if target_gold >= gold_to_steal:
                            await h.add_gold(interaction.user.id, gold_to_steal)
                            await h.add_gold(target.id, -gold_to_steal)
                            hook += f"\n\n*{interaction.user.display_name} steals 200 gold from {target.display_name}!*"
                        else:
                            await h.add_gold(interaction.user.id, target_gold)
                            await h.add_gold(target.id, -target_gold)
                            hook += f"\n\n*{interaction.user.display_name} steals {target_gold} gold from {target.display_name}!*"
                    else:
                        await h.add_gold(interaction.user.id, gold_to_steal)
                        hook += f"\n\n*{interaction.user.display_name} gives {target.display_name} 200 gold, then instantly steals it back!*"
            else:
                hook = random.choice(self.hooks_data[user_class.lower()]["normal"])
                additional_msg = ""
        else:
            if is_critical:
                hook = random.choice(self.hooks_data[user_class.lower()]["crit"])
                amount = 125 if user_class == 'Rogue' else 100
                additional_msg = f"**✨[CRITICAL]✨** + {amount} Coolness | "
                if user_class == 'Nomad' and await self.get_channel_nomad(interaction.channel_id) == None and await self.get_nomad_home(interaction.user.id) == None:
                    hook += f'\n\n*{interaction.user.display_name} claims this channel as their home for the day!*'
                    self.nomad_homes[interaction.channel.id] = interaction.user.id
                await h.add_coolness(self.bot, interaction.user.id, amount)
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

        # Determine the appropriate message hook based on user class and critical hit
        hook_key = "crit" if is_critical == True else "normal"
        if user_class in ['Archer', 'Hunter', 'Gunner', 'Tamer']:
            hook = random.choice(self.hooks_data[user_class.lower()][hook_key])
            additional_msg = ""

            # Set specific messages and actions for critical hits
            if is_critical:
                if user_class in ['Archer', 'Hunter', 'Tamer']:
                    additional_msg = "**✨[CRITICAL]✨** + 100 Coolness | "
                    await h.add_coolness(self.bot, interaction.user.id, 100)
                elif user_class == 'Gunner':
                    additional_msg = "**🎯[HEADSHOT]🎯** + 200 Coolness | "
                    await h.add_coolness(self.bot, interaction.user.id, 200)

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
                await h.add_coolness(self.bot, interaction.user.id, 100)
            elif current_pyro_level >= 100:
                # Handle overheat scenario
                hook = random.choice(self.hooks_data[user_class.lower()]["overheat"])

                if user_class == 'Ashen Sage': # Moved logic to overheat.
                    additional_msg = "**🔥[OVERHEAT!]🔥** + 75 Coolness, +1 Cinder | "
                else:
                    additional_msg = "**🔥[OVERHEAT!]🔥** + 75 Coolness | "
                await h.add_coolness(self.bot, interaction.user.id, 75)
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

    async def handle_douse(self, interaction, target, user_class):
        if not target or target == interaction.user or target.id == 1243216875622764574:
            await interaction.response.send_message("Invalid target for attacking.", ephemeral=True)
            return

        # Example critical hit check, simplified
        is_critical = await h.crit_handler(self.bot, interaction.user, target, interaction)

        if user_class in ['Hydromancer', 'Tidal Mage']:
            restoration_amount = 5 # Amount of AP an overflow restores.
            if (current_water_level := self.waterlevels.get(interaction.user.id)) is None:
                self.waterlevels[interaction.user.id] = current_water_level = 0
            if is_critical:
                hook = random.choice(self.hooks_data[user_class.lower()]["crit"])
                additional_msg = "**✨[CRITICAL]✨** + 100 Coolness | "
                await h.add_coolness(self.bot, interaction.user.id, 100)
            elif current_water_level >= 100:
                hook = random.choice(self.hooks_data[user_class.lower()]["overflow"])
                additional_msg = f"**💧[OVERFLOW]💧** + {restoration_amount} AP | "
                await h.add_ap(self.bot, interaction.user.id, 5)
                self.waterlevels[interaction.user.id] = 0
            else:
                hook = random.choice(self.hooks_data[user_class.lower()]["normal"])
                additional_msg = ""

        if current_water_level <= 100:
            if user_class == 'Hydromancer':
                self.waterlevels[interaction.user.id] += random.randint(0,20)
            elif user_class == 'Tidal Mage':
                self.waterlevels[interaction.user.id] += random.randint(0,40)
            for temp, message in self.water_intensities:
                if self.waterlevels[interaction.user.id] <= temp:
                    hook +=  f"\n\n*usr1's water level {message} at {min(self.waterlevels.get(interaction.user.id, 0), 100)}%.*"
                    break

        hook = hook.replace("usr1", f"**{interaction.user.display_name}**")
        hook = hook.replace("usr2", f"**{target.display_name}**")
        hook = hook.replace('bdypart', random.choice(h.body_parts))
        await interaction.response.send_message(additional_msg + hook)

    async def handle_freeze(self, interaction, target, user_class):
        if not target or target == interaction.user or target.id == 1243216875622764574:
            await interaction.response.send_message("Invalid target for attacking.", ephemeral=True)
            return

        # Example critical hit check, simplified
        is_critical = await h.crit_handler(self.bot, interaction.user, target, interaction)

        if user_class == 'Cryomancer':
            if target.id not in self.impaled:
                if not is_critical:
                    hook = random.choice(self.hooks_data[user_class.lower()]["normal"])
                else:
                    self.impaled.append(target.id)
                    hook = random.choice(self.hooks_data[user_class.lower()]["crit"])
                    additional_msg = "**<:ice:1252693113189961881>[IMPALEMENT!]<:ice:1252693113189961881>** + 100 Coolness | "
                    await h.add_coolness(self.bot, interaction.user.id, 100)
                    await interaction.response.send_message(additional_msg + hook.replace("usr1", f"**{interaction.user.display_name}**").replace("usr2", f"**{target.display_name}**").replace('bdypart', random.choice(h.body_parts)))
                    return
            else:
                chance_to_stay = random.randint(1,5)
                hook = random.choice(self.hooks_data[user_class.lower()]["minicrit"])
                additional_msg = "**✨[MINI-CRIT]✨** + 75 Coolness | "
                if chance_to_stay != 1:
                    self.impaled.remove(target.id)
                    hook += "\n\n*The icicle is dislodged!*"
                else:
                    hook += "\n\n*The icicle stays lodged!*"

                await h.add_coolness(self.bot, interaction.user.id, 75)
                await interaction.response.send_message(additional_msg + hook.replace("usr1", f"**{interaction.user.display_name}**").replace("usr2", f"**{target.display_name}**").replace('bdypart', random.choice(h.body_parts)))
                return

            # This section is reached only if it's a normal hit on a non-impaled target
            await interaction.response.send_message(hook.replace("usr1", f"**{interaction.user.display_name}**").replace("usr2", f"**{target.display_name}**").replace('bdypart', random.choice(h.body_parts)))

    async def handle_stone(self, interaction, target, user_class):
        if not target or target == interaction.user or target.id == 1243216875622764574:
            await interaction.response.send_message("Invalid target for attacking.", ephemeral=True)
            return

        is_critical = await h.crit_handler(self.bot, interaction.user, target, interaction)

        if user_class in ['Terramancer', 'Dune Wizard', 'Igneous Mage', 'Mineral Mage']:
            if (current_shards := self.earth_shards.get(interaction.user.id)) is None:
                self.earth_shards[interaction.user.id] = current_shards = 0
            
            if current_shards >= 5:
                hook = random.choice(self.hooks_data[user_class.lower()]["mega-crit"])
                amount = 1250
                additional_msg = f"**🪨[MEGA-CRIT!]🪨** + {amount} Coolness | "
                await h.add_coolness(self.bot, interaction.user.id, amount)
                self.earth_shards[interaction.user.id] = 0
                if user_class == 'Igneous Mage':
                    hook += '\n\nusr2 is set ablaze!'
                    await self.bot.get_cog("statuses").apply_status_effect(target.id, 'burning', stacks=random.randint(5,15))
                elif user_class == 'Mineral Mage':
                    # Handle Mineral Mage specific logic for setting a spike
                    hook += "\n\nusr2 is impaled with a volatile gem spike! Watch out, everyone!"
                    def check(m):
                        return m.author != interaction.user and m.channel == interaction.channel

                    hook = hook.replace("usr1", f"**{interaction.user.display_name}**")
                    hook = hook.replace("usr2", f"**{target.display_name}**")
                    hook = hook.replace('bdypart', random.choice(h.body_parts))
                    await interaction.response.send_message(additional_msg + hook)
                    msg = await self.bot.wait_for('message', check=check)
                    await interaction.channel.send(f"**[CRYSTAL DETONATION!]** +75 Coolness | The mineral spike explodes as **{msg.author.display_name}** speaks, launching shards everywhere!")
                    await h.add_coolness(self.bot, interaction.author.id, 75)
                    return  # Stop further execution to ensure spike logic dominates this path
            elif is_critical:
                hook = random.choice(self.hooks_data[user_class.lower()]["crit"])
                additional_msg = "**✨[CRITICAL]✨** + 100 Coolness, +1 Earth Shard | "
                self.earth_shards[interaction.user.id] = current_shards + 1
                await h.add_coolness(self.bot, interaction.user.id, 100)
            else:
                hook = random.choice(self.hooks_data[user_class.lower()]["normal"])
                additional_msg = ""
        
        if current_shards > 0 and current_shards < 5:
            hook += f"\n\n*usr1 has {current_shards}/5 Earth Shards!*"

        hook = hook.replace("usr1", f"**{interaction.user.display_name}**")
        hook = hook.replace("usr2", f"**{target.display_name}**")
        hook = hook.replace('bdypart', random.choice(h.body_parts))
        await interaction.response.send_message(additional_msg + hook)


    async def handle_demon(self, interaction, user_class):
        user_id = interaction.user.id
        demon = await self.get_user_demon(user_id)
        
        if demon:
            demon_name = demon['demon_name']
            demon_desc = demon['demon_desc']
            demon_img = demon['demon_img']  # Assuming 'demon_img' contains a valid URL to an image

            embed = discord.Embed(title=f"🔥 Your Demon: {demon_name} 🔥", description=demon_desc, color=0x750385)
            embed.add_field(name='Level', value=f'{await h.get_user_level(interaction.user.id) % 10}')
            embed.set_image(url=demon_img)
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            response = "You haven't chosen a demon yet. Let's fix that!\n\n**# You cannot change your demon once chosen; so choose carefully!**"
            # Sending an interactive view to let them choose a demon
            await interaction.response.send_message(response, view=v.DemonSelection(demons=await v.fetch_demons(), user_id=interaction.user.id), ephemeral=True)

    async def handle_invoke(self, interaction, user_class):
        user_id = interaction.user.id
        demon = await self.get_user_demon(user_id)

        if demon:
            demon_name = demon['demon_name']
            response = f"🔮 You invoke **{demon_name}**."
        else:
            response = "You haven't chosen a demon yet. Let's fix that!\n\n**# You cannot change your demon once chosen; so choose carefully!**"
            # Sending an interactive view to let them choose a demon
            await interaction.response.send_message(response, view=v.DemonSelection(demons=await v.fetch_demons(), user_id=interaction.user.id), ephemeral=True)
        
        await interaction.response.send_message(response)
    
    async def handle_pray(self, interaction, user_class):
        guild_id = interaction.guild_id
        user_id = interaction.user.id

        # Start or increment a ritual
        if guild_id not in self.rituals:
            self.rituals[guild_id] = 1
            self.involved[guild_id] = [user_id]
        else:
            self.rituals[guild_id] += 1
            if user_id not in self.involved[guild_id]:
                self.involved[guild_id].append(user_id)

        progress = self.rituals[guild_id]
        image_urls = [
            "http://kaktuskontainer.wdfiles.com/local--files/7/0.png",
            "http://kaktuskontainer.wdfiles.com/local--files/7/1.png",
            "http://kaktuskontainer.wdfiles.com/local--files/7/2.png",
            "http://kaktuskontainer.wdfiles.com/local--files/7/3.png",
            "http://kaktuskontainer.wdfiles.com/local--files/7/4.png",
            "http://kaktuskontainer.wdfiles.com/local--files/7/5.png",
            "http://kaktuskontainer.wdfiles.com/local--files/7/6.png",
            "http://kaktuskontainer.wdfiles.com/local--files/7/7.png"
        ]

        embed = discord.Embed(title=f"Ritual Progress: {progress}/8", colour=discord.Colour.dark_gold())
        embed.set_image(url=image_urls[progress] if progress < 8 else image_urls[len(image_urls)-1])  # Indexing starts at 0 so subtract 1

        if progress < 8:
            await interaction.response.send_message(f"*Your voice calls out into the void... ({progress}/8)*", embed=embed)
        else:
            await interaction.response.send_message(f"*Your voice calls out into the void... ({progress}/8)*", embed=embed)
            await self.conclude_ritual(interaction, guild_id)

    async def conclude_ritual(self, interaction, guild_id):
        self.rituals[guild_id] = 0
        # Conclude the ritual with the summoning of a random entity
        choice = random.randint(1, 5)  # Choose a random demon for the conclusion

        async with aiohttp.ClientSession() as session:
            url = await h.webhook_safe_check(interaction.channel)
            webhook = discord.Webhook.from_url(url, session=session)
            await webhook.send(content="**The ground trembles as the ritual reaches its climax...**", username="Narrator", avatar_url='https://upload.wikimedia.org/wikipedia/commons/thumb/8/89/HD_transparent_picture.png/800px-HD_transparent_picture.png')
            await asyncio.sleep(3)
            await webhook.send(content="**From the depths, a voice booms, echoing throughout the void...**", username="Narrator", avatar_url='https://upload.wikimedia.org/wikipedia/commons/thumb/8/89/HD_transparent_picture.png/800px-HD_transparent_picture.png')
            await asyncio.sleep(3)

           # choice = 5

            if choice == 1:
                # Karzul the Unseen
                await webhook.send(content="# **WHO DARES DISTURB MY SLUMBER?**", username="Karzul the Unseen", avatar_url="https://www.absolutearts.com/portfolio3/v/vasillisalov/the_demon_of_chaos_4-1489226035m.jpg")
                await asyncio.sleep(3)
                await webhook.send(content="# **FOR YOUR BRAVERY, I GRANT YOU A BOON. BE WARNED, MORTALS, DO NOT CALL UPON ME LIGHTLY AGAIN.**", username="Karzul the Unseen", avatar_url="https://www.absolutearts.com/portfolio3/v/vasillisalov/the_demon_of_chaos_4-1489226035m.jpg")
                boon_amount = 5000
                message = f"Karzul the Unseen has granted each cultist a boon of {boon_amount} gold!"
            elif choice == 2:
                # Molthor the Firelord
                await webhook.send(content="# **YOU HAVE AWAKENED ME FROM MY FIERY SLUMBER!**", username="Molthor the Firelord", avatar_url="https://nexuscompendium.com/images/portraits/ragnaros.png")
                await asyncio.sleep(3)
                await webhook.send(content="# **TAKE THIS GIFT OF INFERNAL ENERGY, AND USE IT WISELY.**", username="Molthor the Firelord", avatar_url="https://nexuscompendium.com/images/portraits/ragnaros.png")
                boon_amount = 30  # Grant AP instead of gold
                message = f"Molthor the Firelord has enhanced each cultist with {boon_amount} additional AP!"
                for user_id in self.involved[guild_id]:
                    await h.add_ap(self.bot, user_id, boon_amount)  # Assuming add_ap is a correct function
            elif choice == 3:
                # Elyssia, the Whisper of Wind
                await webhook.send(content="# **YOUR CALL HAS REACHED THE ETERNAL WINDS.**", username="Elyssia, Whisper of Wind", avatar_url="https://thumbs.dreamstime.com/b/god-wind-sky-children-s-oil-painting-depicting-head-152316011.jpg")
                await asyncio.sleep(3)
                await webhook.send(content="# **I GIFT YOU THE BREATH OF WISDOM. YOU CAN DO A SICK ASS KICKFLIP WITH IT.**", username="Elyssia, Whisper of Wind", avatar_url="https://thumbs.dreamstime.com/b/god-wind-sky-children-s-oil-painting-depicting-head-152316011.jpg")
                boon_amount = 5000  # Grant Coolness
                message = f"Elyssia, the Whisper of Wind has granted each cultist a boon of {boon_amount} coolness!"
                for user_id in self.involved[guild_id]:
                    await h.add_coolness(self.bot, user_id, boon_amount)  # Assuming add_coolness is a correct function
            elif choice == 4:  # The Hotdog Demon
                await webhook.send(content="*The summoning circle pulsates as...* ***A LARGE FLESHY HAND GRIPS THE SIDE!***", username="Narrator", avatar_url='https://upload.wikimedia.org/wikipedia/commons/thumb/8/89/HD_transparent_picture.png/800px-HD_transparent_picture.png')
                await asyncio.sleep(3)
                await webhook.send(content="***A LARGE FLESHY BEAST PULLS HIMSELF OUT OF THE SUMMONING CIRCLE!***", username="Narrator", avatar_url='https://upload.wikimedia.org/wikipedia/commons/thumb/8/89/HD_transparent_picture.png/800px-HD_transparent_picture.png')
                await asyncio.sleep(3)
                await webhook.send(content="***OH GOD, OH FUCK! IT'S THE HOTDOG DEMON! PANIC!***", username="Narrator", avatar_url='https://upload.wikimedia.org/wikipedia/commons/thumb/8/89/HD_transparent_picture.png/800px-HD_transparent_picture.png')
                await asyncio.sleep(3)
                await webhook.send(content="**KILLLLLLL MEEEEEEEE!!!!**", username="THE HOTDOG DEMON", avatar_url="https://images-cdn.9gag.com/photo/aO7e1BN_700b.jpg")
                await asyncio.sleep(3)
                chosen_cultist = random.choice(self.involved[guild_id])
                await webhook.send(content=f"*The Hotdog Demon grabs <@{chosen_cultist}> and begins regurgitating hotdogs all over them.*", username="Narrator", avatar_url='https://upload.wikimedia.org/wikipedia/commons/thumb/8/89/HD_transparent_picture.png/800px-HD_transparent_picture.png')
                await asyncio.sleep(3)
                await webhook.send(content="**I'M TOO PERFECT! TOO PERFECT FOR THIS WORLD! AAAAAAAAAAAAAAAAAAAA!!!**", username="THE HOTDOG DEMON", avatar_url="https://images-cdn.9gag.com/photo/aO7e1BN_700b.jpg")
                await asyncio.sleep(3)
                hot_dog_amount = random.randint(20,40)
                message = f"*The Hotdog Demon then melts all over <@{chosen_cultist}>, leaving {hot_dog_amount} hotdogs behind, which they pick up.*"
                await h.give_item(chosen_cultist, 1, hot_dog_amount)
            elif choice == 5:  # Xoth, the Barterer
                await interaction.followup.send("*A slow, brooding fog begins to spread around the cultists...*")
                await asyncio.sleep(3)
                await webhook.send(content="*Ahhh.... Hello there...*", username="Xoth, The Barterer")
                await asyncio.sleep(3)
                chosen_cultist = random.choice(self.involved[interaction.guild.id])
                await webhook.send(content=f"*Hey, hey... <@{chosen_cultist}>... let's make a deal...*", username="Xoth, The Barterer")
                await asyncio.sleep(3)
                await webhook.send(content="*I'll make you richhhhh... in exchange for your fellow cultists sufferinggg...*", username="Xoth, The Barterer")
                await asyncio.sleep(3)
                await webhook.send(content="***Do we have a deal...?***", username="Xoth, The Barterer")

                def check(m):
                    return m.author.id == chosen_cultist and m.channel.id == interaction.channel.id

                try:
                    response = await self.bot.wait_for('message', check=check, timeout=30.0)
                    if response.content.lower() in ['yes', 'y']:
                        await webhook.send(content="*Excellent! Our deal is sealed...*", username="Xoth, The Barterer")
                        gold_gained = 1000
                        coolness_lost = 500
                        await h.add_gold(chosen_cultist, gold_gained)
                        await h.add_coolness(self.bot, chosen_cultist, -coolness_lost)
                        for cultist in self.involved[interaction.guild.id]:
                            if cultist != chosen_cultist:
                                await h.add_gold(cultist, -gold_gained)
                        await interaction.followup.send(f"<@{chosen_cultist}> gains {gold_gained} gold but loses {coolness_lost} coolness! The other cultists just lose {gold_gained} gold - lame!")
                    else:
                        await webhook.send(content="*Very well, perhaps another time...*", username="Xoth, The Barterer")
                except asyncio.TimeoutError:
                    await webhook.send(content="*Alas, time has run out and the offer has expired...*", username="Xoth, The Barterer")

            # Send followup message and reset the ritual progress
            self.involved[guild_id] = []
            await interaction.followup.send(message)
    """
    =====================================================
    ========== CLASS SPECIFIC HELPER FUNCTIONS ==========
    =====================================================
    """
    async def start_crusade(self, interaction):
        """Starts a crusade, calculates its duration, waits, and then automatically ends it."""
        start_time = discord.utils.utcnow()
        duration_hours = 2  # Crusade lasts for 2 hours
        end_time = start_time + datetime.timedelta(hours=duration_hours)

        # Store crusade information
        self.crusade = {
            'starter': interaction.user.display_name,
            'start_time': start_time.isoformat(),
            'end_time': end_time.isoformat()
        }

        # Calculate the seconds until the crusade ends for the delay
        seconds_until_end = (end_time - discord.utils.utcnow()).total_seconds()
        await asyncio.sleep(seconds_until_end)  # Wait for the crusade duration to end

        # Automatically end the crusade
        self.crusade = None
        print("Crusade has ended.")  # Optional: Send a message or log that the crusade has ended

    async def get_user_demon(self, user_id: int) -> dict:
        """Fetches the demon associated with the user from the database."""
        db_path = 'data/class_specific.db'
        
        async with aiosqlite.connect(db_path) as conn:
            async with conn.cursor() as cursor:
                # Join the user list with the demons list to get the correct demon
                await cursor.execute("""
                    SELECT d.demon_name, d.demon_desc, d.demon_img
                    FROM pacted_user_list u 
                    JOIN pacted_demons_list d ON u.demon_id = d.demon_id 
                    WHERE u.user_id = ?
                    """, (user_id,))
                result = await cursor.fetchone()
                if result:
                    return {'demon_name': result[0], 'demon_desc': result[1], 'demon_img': result[2]}
                return None


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

    async def calculate_ap_gain_ashen(self, stacks: int, interaction) -> tuple:
        if stacks >= 10:
            await h.grant_achievement(interaction.channel, interaction.user, 9)

        if stacks <= 10:
            # Linear gain for AP and gold for up to 10 cinders
            ap_gain = 3 * stacks  # e.g., 3 AP per cinder
            gold_gain = 500 * stacks  # e.g., 500 gold per cinder
        else:
            # Fixed rewards at exactly 10 cinders
            ap_gain = 30  # Directly assign the AP value at 10 cinders
            gold_gain = 5000  # Directly assign the gold value at 10 cinders
            # Diminishing returns for any cinders beyond 10
            excess_stacks = stacks - 10
            ap_gain += 5 * math.log1p(excess_stacks)  # Diminishing AP gain for extra cinders
            gold_gain += 1000 * math.log1p(excess_stacks)  # Diminishing gold gain for extra cinders

        return int(ap_gain), int(gold_gain)  # Return integer values for AP and gold

async def setup(bot):
    await bot.add_cog(action_core(bot))