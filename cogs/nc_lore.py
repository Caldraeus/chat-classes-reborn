# import string
# from tokenize import String
# import discord
# from discord.ext import commands
# from discord import app_commands
# from discord.app_commands import Choice
# import helper as h
# import math
# from typing import Literal
# import random
# import json

# class lore(commands.Cog):
#     def __init__(self, bot):
#         self.bot = bot

#         with open('data/characters.json') as f:
#             self.characters = json.load(f)
    

#         self.fun_facts = {
#             "prodigy" : [
#                 "Prodigy percieves the world differently than the other characters, with objects having sharp edges and colors being more enhanced.",
#                 "He once visited a country full of awoken animals, where he met a business partner who asked him to travel to the Kruber Dynasty in exchange for fine fabrics. This is where he got arrested.",
#                 "Prodigy has no legal name, nor family, nor place of residence.",
#                 "Oftentimes, Prodigy will speak to inanimate objects or animals as though they can fully comprehend him. Someday he hopes they will.",
#                 "Prodigy's pet rabbit (who he has named \"Nix\") is totally a dragon."
#             ], # Prodigy

#             "grumm" : [
#                 "Grumm's favorite meal is a root vegetable stew with a side of mashed potatos.",
#                 "There is a town Grumm once saved from a group of bandits without any of the townsfolk knowing who he was. Afterwards, he was known as “The Chained Stranger”",
#                 "Grumm wishes to one day open an adventurer's supply/training store to prepare a new generation of heroes.",
#                 "Out of all the orcs in his clan, Grumm was the only one to learn how to play the recorder, albeit poorly.",
#                 "Grumm has tried (and failed) to grow a full beard for years and has wimped out after the first few days because it looks bad."
#             ], # Grumm
#             "brayoft" : [
#                 "Brayoft never uses weapons because he knows it would make him too overpowered and he wants his foes to have a fair fight.",
#                 "Despite his character sheet saying he's 3'3\", Brayoft is actually 5'9\" and everyone who says otherwise is a liar.",
#                 "Brayoft has to constantly fend away the advances of women because he is really cool and everyone wants to be with him.",
#                 "Brayoft slayed a dragon but it was so easy he barely remembers it and that's why the details keep changing so you can stop asking.",
#                 "Brayoft actually can read and is not dictating these fun facts through a third party."
#             ], # Brayoft
#             "tallie" : [
#                 "Tallie has never done anything wrong.",
#                 "Great ambitions are only as great as you can make them.",
#                 "If Tallie had an copper piece for every time their research accidentally produced an amphetamine, they'd have two copper pieces. Which isn't a lot, but it's weird it's happened twice.",
#                 "Despite calling The Untamed Horde their home, they actually grew up relatively close to the north eastern border of the Felnorian Trade Company.",
#                 "Tallie knows the Invisibility spell and mage hand cantrip despite their player often forgetting."
#             ]  # Tallie
#         }

#     @app_commands.command(name="character-info")
#     @app_commands.describe(character='The character whose bio you want to see.')
#     
#     @app_commands.choices(character=[
#         Choice(name='Prodigy', value=1),
#         Choice(name='Grumm', value=2),
#         Choice(name='Brayoft', value=3),
#         Choice(name='Tallie', value=4)
#     ])
#     async def character_info(self, interaction: discord.Interaction, character: Choice[int]):
#         """ Display one of the official player character's information profiles! """
#         character = character.name.lower()
        
#         player = await interaction.guild.fetch_member(int(self.characters[character]["user_id"]))

#         profile = discord.Embed(title=self.characters[character]["full_name"], colour=discord.Colour(0x6fa8dc), description=self.characters[character]["backstory"])
#         ###
#         ###
#         profile.add_field(name="Class & Level", value=self.characters[character]["class"], inline=True)
#         profile.add_field(name="Race", value=self.characters[character]["race"], inline=True)
#         profile.add_field(name="Player", value = str(player), inline = False)
        
#         profile.set_thumbnail(url=self.characters[character]["image_link"])

#         profile.set_footer(text=f"\"{random.choice(self.fun_facts[character])}\"", icon_url=player.avatar.url)

#         await interaction.response.send_message(embed=profile, ephemeral=False)

# # A setup function the every cog has
# async def setup(bot):
#     await bot.add_cog(lore(bot))