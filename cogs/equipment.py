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
sys.path.append('/mnt/c/Users/perkettr/Desktop/Python/gilly-bot/cogs/views')
import nc_character_views as v

class equipment(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="inventory")
    @app_commands.guilds(discord.Object(id=h.my_guild))
    async def inventory(self, interaction: discord.Interaction) -> None:
        """View your inventory"""
        try:
            async with aiosqlite.connect('data/game.db') as conn:
                async with conn.execute(f"SELECT character_inventory.item_id, character_inventory.equipped, items.item_name, items.item_lore, items.item_rarity, items.item_min_level FROM character_inventory INNER JOIN items ON character_inventory.item_id=items.item_id WHERE user_id = {interaction.user.id} ORDER BY items.item_name") as inv_info:
                    inv = await inv_info.fetchall()

                assert(inv)
        except TypeError:
            await interaction.response.send_message("Please run `/character-create` first.", ephemeral=True)
        except AssertionError:
            await interaction.response.send_message("Please run `/character-create` first.", ephemeral=True)
        else:
            p_inv = h.paginate(inv, 10)

            profile = discord.Embed(title=f"Your Inventory", colour=discord.Colour(0x6eaf0b))
            profile.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar)

            for item in p_inv[0]:
                count = sum(1 for inv_item in inv if inv_item[0] == item[0])
                name = f"{item[2]} (x{count})"
                rarity_and_level = f"{item[4].title()} - Level {item[5]}"
                description = f"{item[3]}"
                profile.add_field(name=name, value=f"• {rarity_and_level}\n• {description}", inline=False)


            profile.set_footer(text=f"Page 1/{len(p_inv)}")
            await interaction.response.send_message(embed=profile, ephemeral=True, view=v.InventoryButtons(interaction.user, 0, p_inv, inv))


    @app_commands.command(name="equip")
    @app_commands.guilds(discord.Object(id=h.my_guild))
    async def equip(self, interaction: discord.Interaction, item: str):
        """Equip an item."""
        # 1. Determine that item exists.
        # Done by autocomplete.

        # 2. Determine if this is already equipped.
        async with aiosqlite.connect('data/game.db') as conn:
            async with conn.execute(f"SELECT character_inventory.item_id, character_inventory.equipped, items.item_type, items.item_name FROM character_inventory INNER JOIN items ON character_inventory.item_id=items.item_id WHERE user_id = {interaction.user.id} AND item_name = '{item}' LIMIT 1") as inv_info:
                inv = await inv_info.fetchone()

            is_equipped = inv[1]

            if is_equipped == 1:
                # Already equipped.
                await interaction.response.send_message("❌ | This item is already equipped!")
            elif inv[2] not in h.item_types_equippable:
                await interaction.response.send_message("❌ | This item is cannot be equipped!")
            else:
                # 3. Determine hands.
                async with conn.execute(f"SELECT character_inventory.item_id, character_inventory.equipped, items.item_name, items.item_type, items.item_basic_rfplang FROM character_inventory INNER JOIN items ON character_inventory.item_id=items.item_id WHERE user_id = {interaction.user.id} AND equipped = 1;") as equip_info:
                    equipped_stuff = await equip_info.fetchall()

                # For each equipped item, determine two things.
                # 1. Is the item an armor - the character can only have have 1 armor equipped.
                # 2. If they have open hands
                # 3. Finally, something with magic items. I think there will be a hard limit of three, but we can come back to this later.

                # Helper functions for customization later on.

                max_hand = h.count_hands(interaction.user)
                max_attune = h.count_attune_slots(interaction.user)
                
                armor = None
                hands = 0

                for item_n in equipped_stuff:
                    if "ARMOR" in item_n[3]:
                        armor = item_n
                    elif "WEAPON" in item_n[3]:
                        hands += int([item for item in item_n[4].split("&&") if "HANDS(" in item][0].strip()[6])
                    else:
                        print(f"Update the equip command for {item_n}")

                if hands > max_hand and "WEAPON" in inv[2]:
                    await interaction.response.send_message(f'You have no free hands! You currently only have < {max_hand} > hand(s) free.')
                else:
                    if armor != None and "ARMOR" in inv[2]:
                        # Unequip old armor, equip new armor.
                        async with aiosqlite.connect('data/game.db') as conn:
                            await conn.execute(f"UPDATE character_inventory SET equipped = 1 WHERE user_id = {interaction.user.id} and item_id = {inv[0]}")
                            await conn.execute(f"UPDATE character_inventory SET equipped = 0 WHERE user_id = {interaction.user.id} and item_id = {armor[0]}")
                            await conn.commit()
                    else:
                        async with aiosqlite.connect('data/game.db') as conn:
                            await conn.execute(f"UPDATE character_inventory SET equipped = 1 WHERE user_id = {interaction.user.id} and item_id = {inv[0]} LIMIT 1")
                            await conn.commit()

                    await interaction.response.send_message(f'✅ | You have equipped {item}.')

    @equip.autocomplete('item')
    async def item_autocomplete(self, interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
        async with aiosqlite.connect('data/game.db') as conn:
            async with conn.execute(
                "SELECT items.item_name FROM character_inventory "
                "INNER JOIN items ON character_inventory.item_id=items.item_id "
                "WHERE user_id = ? AND item_name LIKE ? LIMIT 25",
                (interaction.user.id, f'%{current}%')
            ) as inv_info:
                inv = await inv_info.fetchall()
        items = [app_commands.Choice(name=item[0], value=item[0]) for item in inv]
        return items

    @app_commands.command(name="unequip")
    @app_commands.guilds(discord.Object(id=h.my_guild))
    async def unequip(self, interaction: discord.Interaction, item: str):
        """Unequip an item."""
        async with aiosqlite.connect('data/game.db') as conn:
            async with conn.execute(f"SELECT character_inventory.item_id, character_inventory.equipped, items.item_name FROM character_inventory INNER JOIN items ON character_inventory.item_id=items.item_id WHERE user_id = {interaction.user.id} AND item_name = '{item}'") as inv_info:
                inv = await inv_info.fetchone()

            if not inv:
                # Item not found in inventory.
                await interaction.response.send_message(f"❌ | You don't have a {item} in your inventory!")
                return

            is_equipped = inv[1]

            if not is_equipped:
                # Item is not equipped.
                await interaction.response.send_message("❌ | This item is not equipped!")
                return

            await conn.execute(f"UPDATE character_inventory SET equipped = 0 WHERE item_id = {inv[0]}")
            await conn.commit()

            # Item unequipped!
            await interaction.response.send_message(f"✅ | {item} has been unequipped!")

    @unequip.autocomplete('item')
    async def item_autocomplete(self, interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
        async with aiosqlite.connect('data/game.db') as conn:
            async with conn.execute(
                "SELECT items.item_name FROM character_inventory "
                "INNER JOIN items ON character_inventory.item_id=items.item_id "
                "WHERE user_id = ? AND item_name LIKE ? LIMIT 25",
                (interaction.user.id, f'%{current}%')
            ) as inv_info:
                inv = await inv_info.fetchall()
        items = [app_commands.Choice(name=item[0], value=item[0]) for item in inv]
        return items

# A setup function the every cog has
async def setup(bot):
    await bot.add_cog(equipment(bot))