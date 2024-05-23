import traceback
import discord
from discord.ext import commands
from discord import app_commands
from discord import ui
from discord.utils import get
import asyncio
import aiosqlite
import helper as h
import random

class FactionButtons(discord.ui.View):
    def __init__(self, author, page, factions):
        super().__init__()
        self.author = author
        self.page = page
        self.factions = factions
        self.faction = factions[page]

    @discord.ui.button(label='<', style=discord.ButtonStyle.red)
    async def back(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page -= 1
        if self.page < 0:
            self.page = len(self.factions) - 1

        self.faction = self.factions[self.page]
        rgb = tuple(int(c) for c in self.faction[4].split("|"))

        embed = discord.Embed(title=f"Factions Catalogue: {self.faction[0]}", color=discord.Color.from_rgb(rgb[0], rgb[1], rgb[2]), description=self.faction[3].replace("\\n", "\n"))

        embed.add_field(name="Details", value=f"__Number of Members: {self.faction[1]}__", inline=True)
        embed.set_image(url=self.faction[2])

        embed.set_footer(text=f"Page {self.page + 1}/{len(self.factions)}")

        view = FactionButtons(self.author, self.page, self.factions)
        await interaction.response.edit_message(view=view, embed=embed)

        self.stop()


    @discord.ui.button(label='>', style=discord.ButtonStyle.green)
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page += 1
        if self.page >= len(self.factions):
            self.page = 0

        self.faction = self.factions[self.page]
        rgb = tuple(int(c) for c in self.faction[4].split("|"))

        embed = discord.Embed(title=f"Factions Catalogue: {self.faction[0]}", color=discord.Color.from_rgb(rgb[0], rgb[1], rgb[2]), description=self.faction[3].replace("\\n", "\n"))

        embed.add_field(name="Details", value=f"__Number of Members: {self.faction[1]}__", inline=True)
        embed.set_image(url=self.faction[2])

        embed.set_footer(text=f"Page {self.page + 1}/{len(self.factions)}")

        view = FactionButtons(self.author, self.page, self.factions)
        await interaction.response.edit_message(view=view, embed=embed)

        self.stop()

    async def interaction_check(self, interaction: discord.Interaction):
        return interaction.user.id == self.author.id