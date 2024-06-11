from urllib.parse import urlsplit
import discord
from discord.ext import commands
from discord import app_commands
from discord import ui
import helper as h
from typing import Literal, Type
import traceback
import sys
import aiosqlite
import aiohttp
import asyncio
import re
from typing import List
import random
import datetime
from datetime import timedelta
import os
import requests
from PIL import Image, ImageOps
from io import BytesIO

from openai import AsyncOpenAI
client = AsyncOpenAI()

# Initialize the OpenAI client
client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

class class_core(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.base_classes = {
            1 : 'Apprentice',
            2 : 'Swordsman',
            3 : 'Rogue',
            4 : 'Archer',
        }
        self.active_clones = {} 

    async def owner_only(interaction: discord.Interaction) -> bool:
        """Check if the interaction is from the bot owner."""
        owner_id = 217288785803608074 
        if interaction.user.id == owner_id:
            return True
        await interaction.response.send_message("This command is restricted to the bot's owner.", ephemeral=True)
        return False

    async def mirror_image_and_get_url(self, user_avatar_url):
        try:
            # Fetch the original avatar image
            response = requests.get(user_avatar_url)
            if response.status_code != 200:
                raise Exception("Failed to download image")
            
            # Open the image and apply the mirroring effect
            avatar_img = Image.open(BytesIO(response.content))
            mirrored_avatar = ImageOps.mirror(avatar_img)
            
            # Prepare the mirrored image for uploading
            output_buffer = BytesIO()
            mirrored_avatar.save(output_buffer, 'PNG')
            output_buffer.seek(0)
            
            # Send the mirrored image to a specific Discord channel
            image_channel = self.bot.get_channel(1245875103099518986)  # Ensure this is the correct channel ID
            discord_file = discord.File(fp=output_buffer, filename='mirrored_avatar.png')
            message = await image_channel.send(file=discord_file)
            
            # Return the URL of the uploaded mirrored image
            return message.attachments[0].url

        except Exception as e:
            print(f"Error during image mirroring or upload: {str(e)}")
            return None  # You might want to handle this case in your calling function

    @discord.app_commands.command(name="clone")
    @discord.app_commands.describe(user="The user to clone.")
    @app_commands.check(owner_only)
    async def clone(self, interaction: discord.Interaction, user: discord.Member):
        if user.id in self.active_clones:
            await interaction.response.send_message("This user has already been cloned and is currently active.", ephemeral=True)
            return
        
        try:
            # Mirroring the avatar and sending the initial message
            mirrored_avatar_url = await self.mirror_image_and_get_url(user.display_avatar.url)
            response_msg = f"🔮 | Mystical energies surround {user.display_name}... and suddenly, there's two of them!"
            await interaction.response.send_message(response_msg, ephemeral=False)
            
            # Gather previous messages to create context
            messages = [msg async for msg in interaction.channel.history(limit=100) if msg.author == user]
            context = " ".join(msg.content for msg in messages[:50])

            # Generate the initial clone introduction
            response = await client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": f"Mimic the personality and typing style provided: {context}. Responses are sent through discord, so if you wish, make use of discord markdown and whatnot. statusesDo not introduce emojis into your response."},
                    {"role": "user", "content": f"Say hello as {user.display_name}, acting like you just woke up and had a weird dream about being a simulacrum."}
                ],
                max_tokens=50,  # Adjust this to control the length
                temperature=0.7  # Adjust temperature to control randomness (0.7 is a good balance)
            )

            ai_response = response.choices[0].message.content.strip()

            # Check for a webhook or create one if needed
            async with aiohttp.ClientSession() as session:
                webhook_url = await h.webhook_safe_check(interaction.channel)
                webhook = discord.Webhook.from_url(webhook_url, session=session)

                # Send the initial AI-generated message through the webhook
                await webhook.send(ai_response, username=user.display_name, avatar_url=mirrored_avatar_url)

            # Storing the necessary details including the mirrored avatar URL
            self.active_clones[user.id] = {
                "webhook_url": webhook,
                "username": user.display_name,
                "avatar_url": mirrored_avatar_url,
                "context": context,
                "guild_id": interaction.guild.id  # Store the guild ID
            }

            # Setting a timer to remove the clone after one hour
            self.bot.loop.create_task(self.remove_clone_after_time(user.id, 3600, interaction.channel))
        except Exception as e:
            await interaction.followup.send(f"An error occurred: {str(e)}", ephemeral=True)
            
    async def remove_clone_after_time(self, user_id, delay, channel):
        """Remove the clone after a specified time."""
        await asyncio.sleep(delay)
        if user_id in self.active_clones:
            username = self.active_clones[user_id]['username']
            del self.active_clones[user_id]
            await channel.send(f"⚱️ | The simulacrum of **{username}** crumbles to ash...")

    @commands.Cog.listener('on_message')
    async def on_message(self, message: discord.Message):
        if await h.user_exists(message.author.id) and await h.channel_check(message.channel.id):
            if message.author.id == self.bot.user.id or message.application_id is not None:
                return  # Avoid the bot responding to its own messages

            # Create a copy of the keys to safely iterate
            active_clone_keys = list(self.active_clones.keys())
            for user_id in active_clone_keys:
                if user_id in self.active_clones and message.guild.id == self.active_clones[user_id]['guild_id']:  # Check if the message is from the same guild
                    clone_data = self.active_clones[user_id]
                    if random.randint(1, 25) == 1 or clone_data['username'].lower() in message.content.lower() or f"<@{user_id}>" in message.content:
                        user_prompt = f"Respond to \"{message.content}\" sent by {message.author.display_name}" + (", who is also a clone of you." if user_id == message.author.id else ".")

                        # Generate the AI response
                        response = await client.chat.completions.create(
                            model="gpt-4o",
                            messages=[
                                {"role": "system", "content": f"Assume the identity of {clone_data['username']}. Analyze the provided text and closely imitate the personality, typing style, and any idiosyncrasies found in the previous messages: {clone_data['context']}. Your responses should not only remain in character but also reflect the same level of formality, slang usage, and emotive expressions as seen in the historical messages. Try to keep responses concise when able. statusesDo not introduce emojis into your response.. Your messages are going to be sent on discord."},
                                {"role": "user", "content": user_prompt}
                            ],
                            max_tokens=80,
                            temperature=0.8
                        )

                        ai_response = response.choices[0].message.content.strip()

                        async with aiohttp.ClientSession() as session:
                            url = await h.webhook_safe_check(message.channel)
                            hook = discord.Webhook.from_url(url, session=session)
                            await hook.send(ai_response, username=clone_data['username'], avatar_url=clone_data['avatar_url'])
        
    @app_commands.command(name="start")
    async def start(self, interaction: discord.Interaction) -> None:
        """Begin your Chat Classes journey!"""
        random.seed(interaction.user.id) # "It's their destiny to be an archer!"
        num = random.randint(1,4)
        clss = self.base_classes[num]
        lead = "a"
        if num == 4:
            lead += "n" # Proper english is an important part of the user experience.
        
        async with aiosqlite.connect('data/main.db') as conn:
            user_id = interaction.user.id 
            async with conn.execute("SELECT EXISTS(SELECT 1 FROM users WHERE user_id = ?)", (user_id,)) as cursor:
                exists = await cursor.fetchone()
                if exists[0]:
                    await interaction.response.send_message("You already have a profile! Use `/class` to see what you can do!", ephemeral=True)
                else:
                    # Add user to database with initial values for exp, gold, coolness, and level.
                    await conn.execute(
                        "INSERT INTO users (user_id, class_id, exp, gold, coolness, level) VALUES (?, ?, ?, ?, ?, ?)",
                        (user_id, num, 0, 0, 0, 1)
                    )
                    await conn.commit()  # Make sure to commit changes
                    # Send a confirmation message to the user
                    await interaction.response.send_message(f"You are now {lead} {clss}! Your adventure starts here!", ephemeral=True)

    async def autocomplete_class_names(self, interaction: discord.Interaction, current: str):
        """Autocomplete function that provides class name suggestions."""
        async with aiosqlite.connect('data/main.db') as db:
            cursor = await db.execute("SELECT class_name FROM classes WHERE class_name LIKE ?", (f'%{current}%',))
            class_names = await cursor.fetchall()
            return [discord.app_commands.Choice(name=cls[0], value=cls[0]) for cls in class_names]
        
    @app_commands.command(name="origin")
    @discord.app_commands.describe(
        class_name="The class you wish to find the origin of."
    )
    @app_commands.autocomplete(class_name=autocomplete_class_names)
    async def class_origin(self, interaction: discord.Interaction, class_name: str = None) -> None:
        """Find the path to become a certain class."""
        origin_str = await h.find_origin(class_name)
        await interaction.response.send_message(f"🔍 | To become a {class_name}, you have to take the following path.\n**{origin_str}**", ephemeral=True)

    @app_commands.command(name="profile")
    @discord.app_commands.describe(
        user="The user who's profile you wish to view."
    )
    async def profile(self, interaction: discord.Interaction, user: discord.Member = None) -> None:
        """View your profile or another user's profile"""
        if user is None:
            user = interaction.user
        try:
            profile = await h.genprof(user, self.bot.user_aps, self.bot) 
            if profile:
                await interaction.response.send_message(embed=profile, ephemeral=True)
            else:
                raise SyntaxError
        except SyntaxError:
            await interaction.response.send_message("User does not have a profile! Run `/start` to get one!", ephemeral=True)

        
    @app_commands.command(name="class-info", description="Displays detailed information about a class.")
    @app_commands.describe(class_name="Name of the class to get information about.")
    @app_commands.autocomplete(class_name=autocomplete_class_names)
    async def class_info(self, interaction: discord.Interaction, class_name: str = None):
        """Fetches class details from the database and displays them."""
        async with aiosqlite.connect('data/main.db') as db:
            if class_name is None:
                # Fetch user's current class from the database
                cursor = await db.execute("SELECT class_id FROM users WHERE user_id = ?", (interaction.user.id,))
                user_class = await cursor.fetchone()
                if not user_class:
                    await interaction.response.send_message("You are not assigned to any class.", ephemeral=True)
                    return
                class_id = user_class[0]

                cursor = await db.execute("SELECT class_name FROM classes WHERE class_id = ?", (class_id,))
                class_name = await cursor.fetchone()
                if not class_name:
                    await interaction.response.send_message("Class information not found.", ephemeral=True)
                    return
                class_name = class_name[0]

            # Fetch class details including achievement locks, previous class, and image URL
            cursor = await db.execute("""
                SELECT classes.class_name, classes.class_description, classes.commands, classes.previous_class_id, 
                    classes.ach_lock, achievements.name, classes.image_url
                FROM classes
                LEFT JOIN achievements ON classes.ach_lock = achievements.achievement_id
                WHERE class_name = ?;
            """, (class_name,))
            class_info = await cursor.fetchone()

            # Convert class name to RGB color
            rgb_color = h.hash_class_name_to_rgb(class_name)
            color = discord.Color.from_rgb(*rgb_color)

            if class_info:
                class_name, description, commands, previous_class_id, ach_lock, achievement_name, image_url = class_info
                # Build the embed
                embed = discord.Embed(title=f"Class: {class_name}", description=description, color=color)
                if commands:
                    commands_list = commands.split('|')
                    embed.add_field(name="Commands", value='\n'.join(commands_list), inline=False)

                # Fetch and display previous class if exists
                if previous_class_id:
                    cursor = await db.execute("SELECT class_name FROM classes WHERE class_id = ?", (previous_class_id,))
                    prev_class_name = await cursor.fetchone()
                    if prev_class_name:
                        embed.add_field(name="Previous Class", value=prev_class_name[0], inline=True)

                # Count how many users are currently this class
                cursor = await db.execute("SELECT COUNT(*) FROM users WHERE class_id = (SELECT class_id FROM classes WHERE class_name = ?)", (class_name,))
                user_count = await cursor.fetchone()
                embed.add_field(name=f"Current {class_name} Players", value=user_count[0], inline=True)

                # If class is achievement locked, display the achievement name
                if ach_lock:
                    embed.set_footer(text=f"Unlock Requirement: {achievement_name}")

                # Set the thumbnail if image_url is present and not null
                if image_url:
                    embed.set_thumbnail(url=image_url)

                await interaction.response.send_message(embed=embed, ephemeral=True)
            else:
                await interaction.response.send_message("Class not found.", ephemeral=True)

    @app_commands.command(name="progression", description="Displays class progression for the specified class.")
    @app_commands.describe(clss="The class to display progression for.")
    @app_commands.autocomplete(clss=autocomplete_class_names)
    async def progression(self, interaction: discord.Interaction, clss: str):
        async with aiosqlite.connect('data/main.db') as conn:
            cursor = await conn.execute("""
                SELECT class_name, class_description, ach_lock
                FROM classes
                WHERE previous_class_id = (SELECT class_id FROM classes WHERE class_name = ?);
            """, (clss,))
            class_info = await cursor.fetchall()

        profile = discord.Embed(title=f"🌟 {clss.title()} Class Progression 🌟", colour=discord.Colour.from_rgb(255, 165, 0))
        profile.set_footer(text="A lock symbol next to a class name means there's an achievement required to choose it!", icon_url="")

        if class_info:
            for (class_name, class_description, ach_lock) in class_info:
                if ach_lock:
                    profile.add_field(name=f"🔒 | {class_name.title()}", value=class_description, inline=False)
                else:
                    profile.add_field(name=class_name.title(), value=class_description, inline=False)
            await interaction.response.send_message(embed=profile, ephemeral=True)
        else:
            await interaction.response.send_message("That class either doesn't exist or doesn't have any class progressions!", ephemeral=True)

    @app_commands.command(name="classup", description="Level up your class.")
    async def classup(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        async with aiosqlite.connect('data/main.db') as conn:
            async with conn.execute("SELECT exp, level, class_id FROM users WHERE user_id = ?", (user_id,)) as profile:
                prof = await profile.fetchone()
            
            async with conn.execute("SELECT achievement_id FROM user_achievements WHERE user_id = ?", (user_id,)) as ach_info:
                user_achievements = [row[0] for row in await ach_info.fetchall()]

            async with conn.execute("SELECT class_id, class_name FROM classes WHERE class_id = ?", (prof[2],)) as class_info:
                current_class = await class_info.fetchone()

        xp = prof[0]
        current_lvl = prof[1]
        current_class_id = current_class[0]

        print(f"User {interaction.user.name} with class {current_class[1]} (ID: {current_class_id}) is checking for class-up options.")

        if (current_lvl + 1) % 10 == 0 and xp >= h.max_xp(current_lvl):
            allowed_classes = []

            async with aiosqlite.connect('data/main.db') as conn:
                async with conn.execute("""
                    SELECT class_id, class_name, class_description, ach_lock FROM classes 
                    WHERE previous_class_id = ?;
                """, (current_class_id,)) as cinfo:
                    class_info = await cinfo.fetchall()

            print(f"Fetched class_info: {class_info}")

            profile = discord.Embed(title=f"🌟 CLASS-UP! 🌟", colour=discord.Colour.from_rgb(255, 165, 0))
            for potential_class in class_info:
                class_id, class_name, class_description, ach_lock = potential_class
                print(f"Processing class {class_name} with ach_lock {ach_lock}")
                if ach_lock and ach_lock in user_achievements:
                    profile.add_field(name=class_name.title(), value=class_description.replace(r'\n', '\n'), inline=False)
                    allowed_classes.append((class_id, class_name.lower()))
                elif ach_lock == 0 or ach_lock is None:
                    profile.add_field(name=class_name.title(), value=class_description.replace(r'\n', '\n'), inline=False)
                    allowed_classes.append((class_id, class_name.lower()))

            print(f"Allowed classes: {allowed_classes}")

            if not allowed_classes:
                await interaction.response.send_message("You do not have any classes available for progression.", ephemeral=True)
                return

            await interaction.response.send_message(embed=profile, ephemeral=True)

            options = [discord.SelectOption(label=class_name.title(), value=str(class_id)) for class_id, class_name in allowed_classes]
            select = discord.ui.Select(placeholder="Choose your next class...", options=options)

            async def select_callback(select_interaction: discord.Interaction):
                selected_class_id = int(select.values[0])
                selected_class_name = next((name for cid, name in allowed_classes if cid == selected_class_id), "Unknown Class")
                await select_interaction.response.send_message(f"You selected {selected_class_name}. Click confirm to proceed.", ephemeral=True)
                confirm_button = discord.ui.Button(label="Confirm", style=discord.ButtonStyle.green)

                async def confirm_callback(confirm_interaction: discord.Interaction):
                    async with aiosqlite.connect('data/main.db') as conn:
                        await conn.execute("""
                            UPDATE users 
                            SET class_id = ?, exp = 0, level = ? 
                            WHERE user_id = ?;
                        """, (selected_class_id, current_lvl + 1, user_id))
                        await conn.commit()

                    # Charming class-up message
                    class_up_message = (
                        f"Alright! Here we go! \n\n"
                        f"*3...*\n\n"
                        f"*<:STEASnothing:517873442381627392>2...*\n\n"
                        f"*<:STEASnothing:517873442381627392><:STEASnothing:517873442381627392>1... and...!*\n\n"
                        f"<:STEASnothing:517873442381627392><:STEASnothing:517873442381627392><:STEASnothing:517873442381627392>"
                        f"<:STEASnothing:517873442381627392>☁️ **P O O F !** ☁️\n\n"
                        f"{interaction.user.mention} is now a **{selected_class_name.title()}**! Congratulations!"
                    )
                    await confirm_interaction.response.send_message(class_up_message, ephemeral=False)

                confirm_button.callback = confirm_callback
                view = discord.ui.View()
                view.add_item(confirm_button)
                await select_interaction.followup.send(view=view, ephemeral=True)

            select.callback = select_callback
            view = discord.ui.View()
            view.add_item(select)
            await interaction.followup.send(view=view, ephemeral=True)

        else:
            await interaction.response.send_message("Sorry, you can't change classes yet! Come back when you're higher level.", ephemeral=True)



# A setup function the every cog has
async def setup(bot):
    await bot.add_cog(class_core(bot))