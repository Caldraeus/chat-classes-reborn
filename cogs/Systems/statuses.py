import discord
from discord.ext import commands
import aiohttp
import json
import random
from discord import app_commands
import helper as h
import signal
import pickle
import asyncio

class statuses(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.status_effects = self.load_status_effects()
        self.user_status_effects = {}  # {user_id: {effect_name: stacks}}
        asyncio.create_task(self.load_user_status_effects())

    async def load_user_status_effects(self):
        """Load user status effects from file."""
        try:
            with open('data/user_status_effects.pkl', 'rb') as file:
                self.user_status_effects = pickle.load(file)
        except FileNotFoundError:
            self.user_status_effects = {}  # Initialize to empty if no file exists

    async def save_user_status_effects(self):
        """Save user status effects to file."""
        try:
            with open('data/user_status_effects.pkl', 'wb') as file:
                pickle.dump(self.user_status_effects, file)
            print(f"{self.__class__.__name__}: Variables saved successfully.")
        except Exception as e:
            print(f"{self.__class__.__name__}: Failed to save variables due to {e}")

    def cog_unload(self):
        """Handle tasks on cog unload."""
        asyncio.create_task(self.save_user_status_effects())
        
    def load_status_effects(self):
        with open('data/status_effect.json', 'r') as f:
            effects = json.load(f)
        return {effect.lower(): data for effect, data in effects.items()}  # Normalize keys to lowercase

    async def apply_status_effect(self, user_id, effect_name, stacks=1):
        effect_name = effect_name.lower()  # Normalize to lowercase
        if user_id not in self.user_status_effects:
            self.user_status_effects[user_id] = {}
        if effect_name in self.status_effects:
            if effect_name in self.user_status_effects[user_id]:
                self.user_status_effects[user_id][effect_name] += stacks
            else:
                self.user_status_effects[user_id][effect_name] = stacks

    async def remove_status_effect(self, user_id, effect_name, stacks=1):
        effect_name = effect_name.lower()  # Normalize to lowercase
        if user_id in self.user_status_effects and effect_name in self.user_status_effects[user_id]:
            self.user_status_effects[user_id][effect_name] -= stacks
            if self.user_status_effects[user_id][effect_name] <= 0:
                del self.user_status_effects[user_id][effect_name]
            if not self.user_status_effects[user_id]:
                del self.user_status_effects[user_id]

    async def remove_all_positive_statuses(self, user_id):
        """Removes all positive status effects from a user."""
        if user_id in self.user_status_effects:
            positive_effects = [effect for effect in self.user_status_effects[user_id] if self.status_effects[effect]['positive']]
            for effect in positive_effects:
                del self.user_status_effects[user_id][effect]
            if not self.user_status_effects[user_id]:
                del self.user_status_effects[user_id]
            await self.save_user_status_effects()

    async def remove_all_negative_statuses(self, user_id):
        """Removes all negative status effects from a user."""
        if user_id in self.user_status_effects:
            negative_effects = [effect for effect in self.user_status_effects[user_id] if not self.status_effects[effect]['positive']]
            for effect in negative_effects:
                del self.user_status_effects[user_id][effect]
            if not self.user_status_effects[user_id]:
                del self.user_status_effects[user_id]
            await self.save_user_status_effects()

    async def get_random_status_effect_from_user(self, user_id):
        """Gets a random status effect that the user has and returns it along with the stack count."""
        if user_id in self.user_status_effects and self.user_status_effects[user_id]:
            effect, stacks = random.choice(list(self.user_status_effects[user_id].items()))
            return effect, stacks
        return None, 0
    
    async def get_status_effect_positive_or_negative(self, effect_name):
        """Determines if a status effect is positive or negative."""
        effect_name = effect_name.lower()  # Normalize to lowercase
        if effect_name in self.status_effects:
            return self.status_effects[effect_name]['positive']
        return None

    async def handle_message_effects(self, message):
        user_id = message.author.id
        if len(message.content.split()) >= 2:
            if user_id in self.user_status_effects:
                modified_content = message.content
                message_altered = False
                effects_to_remove = []
                for effect, stacks in list(self.user_status_effects[user_id].items()):
                    if self.status_effects[effect].get("message", False) == True:
                        if effect == "burning":
                            modified_content = self.apply_burning_effect(modified_content)
                        elif effect == "shattered":
                            modified_content = self.apply_shatter_effect(modified_content)
                        message_altered = True
                        effects_to_remove.append((effect, 1))
                for effect, stacks in effects_to_remove:
                    await self.remove_status_effect(user_id, effect, stacks)
                if message_altered and modified_content != message.content:
                    message.content = modified_content
                    return True  # Message was altered
            return False  # Message was not altered

    def apply_burning_effect(self, content):
        burning_phrases = [
            "🔥 OOH AAAA HOT HOT 🔥", "🔥 SHIT SHIT HOT AHHHHH 🔥", "🔥 HOT HOT HOT 🔥",
            "🔥 FIRE AHHHH IM BURNING 🔥", "🔥 AHH AHH AHH 🔥", "🔥 FIRE FIRE AHHHHH 🔥",
            "🔥 AHHH FIRE FIRE FIRE 🔥", "🔥 HOT FIRE HOT 🔥",
            "🔥 A" + "H" * random.randint(5, 15) + " 🔥", "🔥 AH AH AH HELP 🔥",
            "🔥 FIRE FIRE FIRE 🔥", "🔥 OW OW OW OW FIRE 🔥", "🔥 OWCH OWIE FIRE 🔥",
            "🔥 FIRE BURNS HELP 🔥", "🔥 I AM ON FIRE HELP 🔥", "🔥 HOT OW HOT 🔥",
            "🔥 AH SHIT OWCH 🔥", "🔥 OWCH OWCH OWCH OWCH FIRE 🔥", "🔥 SOMEONE GET ME SOME WATER 🔥"
        ]
        words = content.split()
        modified_words = []
        for word in words:
            word_to_add = random.choice(burning_phrases)
            potential_addition = " ".join(modified_words + [word, word_to_add])
            if len(potential_addition) <= 1900:
                modified_words.append(word)
                if random.random() < 0.5:
                    modified_words.append(word_to_add)
            else:
                # If adding both exceeds the limit, check if just adding the word is okay
                if len(" ".join(modified_words + [word])) <= 1900:
                    modified_words.append(word)
                break  # Stop adding any further words or phrases once we reach the limit
        return " ".join(modified_words)

    def apply_shatter_effect(self, content):
        words = content.split()

        # If there are exactly two words, swap them
        if len(words) == 2:
            return " ".join([words[1], words[0]])
        
        random.shuffle(words)  # Shuffle the words in the list
        return " ".join(words)  # Join the shuffled words back into a single string

    @commands.Cog.listener()
    async def on_message(self, message):
        if await h.channel_check(message.channel.id):
            if message.author.bot:
                return
            message_altered = await self.handle_message_effects(message)
            if message_altered:
                async with aiohttp.ClientSession() as session:
                    url = await h.webhook_safe_check(message.channel)
                    clone_hook = discord.Webhook.from_url(url, session=session)

                    # Check if the message is a reply
                    if message.reference and isinstance(message.reference.resolved, discord.Message):
                        replied_user = message.reference.resolved.author
                        content = f"{replied_user.mention} {message.content}"
                    else:
                        content = message.content

                    # Check if the message has attachments
                    files = [await attachment.to_file() for attachment in message.attachments]

                    await clone_hook.send(
                        content=content,
                        username=message.author.display_name,
                        avatar_url=message.author.display_avatar.url,
                        files=files,
                    )

                    # Delete the original message
                    await message.delete()

    @app_commands.command(name="status", description="Displays current status effects with descriptions and stack counts.")
    @app_commands.describe(user="The user whose status you want to check.")
    async def status(self, interaction: discord.Interaction, user: discord.User = None):
        # If no user is specified, default to the user who invoked the command
        target_user = user or interaction.user
        user_id = target_user.id

        if user_id not in self.user_status_effects or not self.user_status_effects[user_id]:
            await interaction.response.send_message(f"🚫 | {target_user.display_name} has no active status effects.", ephemeral=True)
            return

        embed = discord.Embed(title=f"{target_user.display_name}'s Status Effects", color=discord.Color.gold())
        for effect, stacks in self.user_status_effects[user_id].items():
            description = self.status_effects[effect]['description']
            embed.add_field(name=f"{effect.capitalize()} x{stacks}", value=description, inline=False)

        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(statuses(bot))
