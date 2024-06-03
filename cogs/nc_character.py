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
import asyncio
sys.path.append('/mnt/c/Users/perkettr/Desktop/Python/gilly-bot/cogs/views')
# /mnt/c/Users/perkettr/Desktop/Python/gilly-bot/cogs/views for bad pc
# /mnt/c/users/richa/desktop/code/Python/Discord Bots/gilly_bot/cogs/views for good pc
import nc_character_views as v

class character(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="character-create")
    async def create_character(self, interaction: discord.Interaction) -> None:
        """Create your character profile!"""
        # We create the view  and assign it to a variable so we can wait for it later.
        view = v.RaceSelect(interaction.user) # We pass in ctx.author in order to enforce author only button clicks.
        await interaction.response.send_message(content='First, choose a race!', view=view, ephemeral=True)

    @app_commands.command(name="profile")
    async def profile(self, interaction: discord.Interaction, target: discord.Member = None) -> None:
        """View someone's profile"""
        if target is None:
            target = interaction.user
        else:
            pass

        # Get the target information.
        try:
            async with aiosqlite.connect('data/game.db') as conn:
                async with conn.execute(f"SELECT * FROM character_stats WHERE user_id = {target.id};") as char_stat_info:
                    char_info = await char_stat_info.fetchone()
                async with conn.execute(f"SELECT * FROM character_lore WHERE user_id = {target.id}") as character_lore_info:
                    character_lore = await character_lore_info.fetchone()
                async with conn.execute(f"SELECT class_name FROM classes WHERE class_id = {char_info[9]}") as class_name_info:
                    class_name = await class_name_info.fetchone()
                async with conn.execute(f"SELECT character_faction_stats.reputation, factions.faction_id, factions.faction_name FROM character_faction_stats INNER JOIN factions ON character_faction_stats.faction_id=factions.faction_id WHERE user_id = {target.id}") as faction_info:
                    faction = await faction_info.fetchone()

                assert(character_lore[2])
        except TypeError:
            await interaction.response.send_message("The target does not have a character!", ephemeral=True)
        else:
            view = v.ProfileMainButton(interaction.user, target) # We pass in ctx.author in order to enforce author only button clicks.
            class_name = class_name[0]

            # print(char_info)
            # print(character_lore)

            try:
                profile = discord.Embed(title=f"{character_lore[1]}'s Bio", colour=discord.Colour(0x6eaf0b), description=character_lore[2].replace("\\n", "\n"))
            except TypeError:
                profile = discord.Embed(title=f"{character_lore[1]}'s Bio", colour=discord.Colour(0x6eaf0b), description="No bio.".replace("\\n", "\n"))
            profile.set_author(name=target.display_name, icon_url=target.display_avatar)
            profile.set_image(url=character_lore[3])
            ###
            ###
            profile.add_field(name="Class", value=f'Level {char_info[2]} {class_name}', inline=False)
            profile.add_field(name="Race", value=f'{char_info[1]}', inline=False)
            profile.add_field(name="**XP**", value=f'{char_info[12]} / {h.xp_lvl(int(char_info[2]))}', inline=True)
            profile.add_field(name="**Currency**", value=f'{char_info[11]} sp', inline=True)


            # Faction stuff
            if faction[1] == 1:
                profile.add_field(name="Faction", value=f'{faction[2]}', inline=False)
            else:
                profile.add_field(name="Faction", value=f'{faction[2]} (+{faction[0]} reputation)', inline=False)

            profile.add_field(name="Strength", value=f'{char_info[3]} ({h.gen_score(char_info[3]):+g})', inline=True) 
            profile.add_field(name="Dexterity", value=f'{char_info[4]} ({h.gen_score(char_info[4]):+g})', inline=True)
            profile.add_field(name="Constitution", value=f'{char_info[5]} ({h.gen_score(char_info[5]):+g})', inline=True)
            profile.add_field(name="Intelligence", value=f'{char_info[6]} ({h.gen_score(char_info[6]):+g})', inline=True)
            profile.add_field(name="Wisdom", value=f'{char_info[7]} ({h.gen_score(char_info[7]):+g})', inline=True)
            profile.add_field(name="Charisma", value=f'{char_info[8]} ({h.gen_score(char_info[8]):+g})', inline=True)

            await interaction.response.send_message(embed=profile, ephemeral=False, view=view)

    @app_commands.command(name="set-image")
    
    @app_commands.describe(url='An image link ending in .png, .jpg, or similar')
    async def set_prof_image(self, interaction: discord.Interaction, url: str) -> None:
        """Set your profile image to a new url."""
        # Sets the image url of a profile to a given url, in the form of a string.
        if re.search("(http(s?):)([/|.|\w|\s|-])*\.(?:jpg|jpeg|png|webp|avif|gif|svg)", url):
            async with aiosqlite.connect('data/game.db') as conn:
                await conn.execute(f"UPDATE character_lore SET character_img_link = '{url}' WHERE user_id = {interaction.user.id}")
                await conn.commit()
            await interaction.response.send_message("✅ | Updated your character image!", ephemeral=True)
        else:
            await interaction.response.send_message(content="Hey! That's not a valid image url. An image url ends in .png, .jpg, or another image file format.", ephemeral=True)

    @app_commands.command(name="edit-name")
    
    @app_commands.describe(name='A new name for your character.')
    async def set_name(self, interaction: discord.Interaction, name: str) -> None:
        """Change your character's name"""
        async with aiosqlite.connect('data/game.db') as conn:
            await conn.execute(
                "UPDATE character_lore SET character_name = ? WHERE user_id = ?",
                (name, interaction.user.id)
            )
            await conn.commit()
        await interaction.response.send_message("✅ | Updated your character name!", ephemeral=True)

    @app_commands.command(name="edit-backstory")
    
    @app_commands.describe(backstory='Update your character\'s backstory.')
    async def set_backstory(self, interaction: discord.Interaction, backstory: str) -> None:
        """Change your character's backstory"""
        async with aiosqlite.connect('data/game.db') as conn:
            await conn.execute(
                "UPDATE character_lore SET character_backstory = ? WHERE user_id = ?",
                (backstory, interaction.user.id)
            )
            await conn.commit()
        await interaction.response.send_message("✅ | Updated your character backstory!", ephemeral=True)

    @app_commands.command(name="delete-character")
    
    async def delete_character(self, interaction: discord.Interaction):
        """Deletes a user's character."""
        await interaction.response.send_message("⚠️ | Are you sure you want to delete your character? This action cannot be undone. Type `CONFIRM` to proceed or anything else to cancel.")

        def check_message(message):
            return message.author.id == interaction.user.id and message.channel.id == interaction.channel_id

        try:
            message = await self.bot.wait_for("message", check=check_message, timeout=60.0)
        except asyncio.TimeoutError:
            await interaction.followup.send("❌ | Time's up! Your character has not been deleted.", ephemeral=True)
            return

        if message.content == "CONFIRM":
            async with aiosqlite.connect('data/game.db') as conn:
                await conn.execute(f"DELETE FROM character_stats WHERE user_id = {interaction.user.id}")
                await conn.execute(f"DELETE FROM character_lore WHERE user_id = {interaction.user.id}")
                await conn.execute(f"DELETE FROM character_inventory WHERE user_id = {interaction.user.id}")
                await conn.execute(f"DELETE FROM character_faction_stats WHERE user_id = {interaction.user.id}")
                await conn.commit()
            await interaction.followup.send("✅ | Your character has been deleted.")
        else:
            await interaction.followup.send("❌ | Deletion canceled.")



# A setup function the every cog has
async def setup(bot):
    await bot.add_cog(character(bot))