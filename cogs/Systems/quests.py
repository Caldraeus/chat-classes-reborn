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
import re
from typing import List
import random

class quests(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="quest")
    
    @app_commands.choices(action=[
        app_commands.Choice(name='current', value='current'),
        app_commands.Choice(name='abandon', value='abandon')
    ])
    @discord.app_commands.describe(
        action="The action you would like to take - view your current quest or abandon it."
    )
    async def quest(self, interaction: discord.Interaction, action: str):
        """View or abandon your current quest."""
        user_id = interaction.user.id
        if action == 'current':
            async with aiosqlite.connect('data/main.db') as conn:
                cursor = await conn.execute("""
                    SELECT q.quest_name, q.description, q.img_url, up.current_count, o.target, 
                        r.reward_type, r.reward_value, 
                        (SELECT quest_name FROM quests WHERE quest_id IN 
                            (SELECT quest_id FROM quest_prerequisites WHERE prerequisite_quest_id = q.quest_id))
                    FROM user_quest_progress up
                    JOIN quest_objectives o ON up.objective_id = o.objective_id
                    JOIN quests q ON o.quest_id = q.quest_id
                    LEFT JOIN rewards r ON q.quest_id = r.quest_id
                    WHERE up.user_id = ? AND up.current_count < o.target;
                """, (user_id,))
                quest = await cursor.fetchone()

                if quest:
                    quest_name, description, img_url, current_count, target, reward_type, reward_value, next_quest = quest
                    embed = discord.Embed(
                        title=f"🔍 Current Quest: {quest_name}",
                        description=f"**Description:**\n{description}",
                        color=discord.Colour.blue()
                    )
                    embed.add_field(name="Progress", value=f"{current_count}/{target}", inline=False)
                    if img_url:
                        embed.set_thumbnail(url=img_url)
                    if reward_type and reward_value:
                        embed.add_field(name="Reward", value=f"{reward_value} {reward_type.capitalize()}", inline=True)
                    if next_quest:
                        embed.add_field(name="Next Quest", value=next_quest, inline=True)

                    embed.set_footer(text="Keep going! You're doing great.")
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                else:
                    await interaction.response.send_message("You are currently not on any quest.", ephemeral=True)

        elif action == 'abandon':
            async with aiosqlite.connect('data/main.db') as conn:
                await conn.execute("DELETE FROM user_quest_progress WHERE user_id = ?;", (user_id,))
                await conn.commit()
            await interaction.response.send_message("You have abandoned your current quest.", ephemeral=True)

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild:
            return  # Ignore bot messages and DMs

        # Check if the user exists and if the channel is allowed for interactions
        if not (await h.user_exists(message.author.id) and await h.channel_check(message.channel.id)):
            return  # Skip processing if user doesn't exist or channel is not allowed

        # Fetch random quest on-message
        if random.random() <= 0.01:  # Assuming a 1% chance to check for quest assignment
            await self.bot.quest_manager.fetch_random_quest(message)

        # Progress on_message based quests.
        # Starting with standard "send messages"
        quest_type = await self.bot.quest_manager.get_quest_type(message.author.id)
        if quest_type == 'message':
            await self.bot.quest_manager.update_quest_progress(message.author.id, message.channel.id, 1)

    @commands.Cog.listener()
    async def on_app_command_completion(self, interaction: discord.Interaction, command: app_commands.Command) -> None:
        if not (await h.user_exists(interaction.user.id) and await h.channel_check(interaction.channel.id)):
            return  # Skip processing if user doesn't exist or channel is not allowed
        
        quest_type = await self.bot.quest_manager.get_quest_type(interaction.user.id)
        if quest_type:
            if len(quest_type.split('_')) > 0 and (quest_type.split('_')[0] == 'command' and quest_type.split('_')[1].lower() == command.name.lower()):
                await self.bot.quest_manager.update_quest_progress(interaction.user.id, interaction.channel.id, 1)




async def setup(bot):
    await bot.add_cog(quests(bot))
