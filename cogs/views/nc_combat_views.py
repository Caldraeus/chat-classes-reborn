import traceback
import discord
from discord.ext import commands
from discord import app_commands
from discord import ui
from discord.utils import get
import asyncio
import aiosqlite
import helper as h
import combat_helper as c
import random

        
class Challenge(discord.ui.View):
    def __init__(self, author, target):
        super().__init__()
        self.author = author
        self.target = target

        self.first: c.PlayerState = c.PlayerState(author)
        self.second: c.PlayerState = c.PlayerState(target)

        random.choice([self.first, self.second]).current = True

        self.add_item(ReadyButton(self.author, self.first, self.second))
        self.add_item(ReadyButton(self.target, self.second, self.first))

    async def interaction_check(self, interaction: discord.Interaction):
        return interaction.user.id in [self.author.id, self.target.id]

    def both_players_ready(self) -> bool:
        return self.first.ready and self.second.ready

class ReadyButton(discord.ui.Button['Challenge']):
    def __init__(self, player, player_state, enemy_state) -> None:
        super().__init__(label=f"{player.display_name} - Click to Accept!", style=discord.ButtonStyle.green)
        self.player = player
        self.player_state = player_state
        self.enemy_state = enemy_state

        self.enemy_button = None

        self.interact = None

        self.game = Game(self.player_state, self.enemy_state, self)

        if self.player_state.current:
            self.mss = "It is your turn!"
        else:
            self.mss = "It is the enemy's turn, hang tight!"

    async def callback(self, interaction: discord.Interaction) -> None:
        assert self.view is not None
        assert interaction.message is not None

        if self.view.children[0].player == self.player:
            self.enemy_button = self.view.children[1]
        else:
            self.enemy_button = self.view.children[0]

        if interaction.user.id != self.player.id:
            await interaction.response.send_message('This ready button is not for you, sorry', ephemeral=True)
            return

        self.player_state.ready = True

        if self.enemy_button.player_state.ready:
            await self.enemy_button.begin(interaction=self.enemy_button.interact)
            
            await interaction.response.send_message(content="Both players are ready! " + self.mss, ephemeral=True, view=self.game, embed=self.game.embed)
            self.interact = interaction
        else:
            await interaction.response.send_message("You've readied up! Now we wait for your opponent to ready up.", ephemeral=True)
            self.interact = interaction

    async def begin(self, interaction: discord.Interaction) -> None:
        await self.interact.edit_original_response(content="Both players are ready! " + self.mss, view=self.game, embed=self.game.embed)
        self.interact = interaction
        
    async def resume(self, mss, embed) -> None:
        self.game.embed = embed
        await self.interact.edit_original_response(content=None, view=self.game, embed=self.game.embed)
        self.game.log = mss

class Game(discord.ui.View):
    def __init__(self, player: c.PlayerState, enemy: c.PlayerState, parent_button: ReadyButton):
        super().__init__()
        self.player = player
        self.enemy = enemy
        self.parent_button: ReadyButton = parent_button
        self.parent_view: Challenge = parent_button.view

        self.log = ""
        self.embed = discord.Embed(title="Game Log", description=self.log, color=discord.Color.blurple())
        self.embed.set_author(name=self.player.name, icon_url=self.parent_button.player.avatar._url)

    @discord.ui.button(label='Attack', style=discord.ButtonStyle.green)
    async def attack(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.log += f"\n**{self.player.name}** attacks, dealing 5 damage to **{self.enemy.name}**"
        self.embed.description = self.log
        await interaction.response.edit_message(embed=self.embed, view=None)
        await self.sync() # Should edit the other player's log.
        self.player.current = False
        self.enemy.current = True

    async def interaction_check(self, interaction: discord.Interaction):
        if self.player.current:
            return True
        else:
            await interaction.response.send_message("It's not your turn yet!", ephemeral=True, delete_after=3.0)
            return False

    async def sync(self):
        await self.parent_button.enemy_button.resume(mss=self.log, embed=self.embed)

    async def on_timeout(self):
        self.log += f"\n{self.player.name} ran out of time and loses!"
        self.embed.description = self.log
        self.embed.color = discord.Color.red()
        await self.parent_view.message.edit(embed=self.embed)