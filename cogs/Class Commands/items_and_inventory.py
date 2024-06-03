from discord.ext import commands
import discord
from discord import app_commands
import aiosqlite
import helper as h
from typing import List

class items_and_inventory(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    item_group = discord.app_commands.Group(name="item", description="Manage your items")

    # Autocomplete function for item names based on user inventory
    async def autocomplete_item_names(self, interaction: discord.Interaction, current: str):
        async with aiosqlite.connect('data/main.db') as conn:
            cursor = await conn.execute("""
                SELECT item_name FROM user_inventory
                JOIN items ON user_inventory.item_id = items.item_id
                WHERE user_id = ? AND item_name LIKE ?;
            """, (interaction.user.id, f'%{current}%'))
            items = await cursor.fetchall()
            return [discord.app_commands.Choice(name=item[0], value=item[0]) for item in items]
        
    async def item_give_autocomplete(self, interaction: discord.Interaction, current: str):
        """Provides autocomplete for items that are not secret and can be given to other users."""
        async with aiosqlite.connect('data/main.db') as conn:
            cursor = await conn.execute("""
                SELECT item_name FROM user_inventory 
                JOIN items ON user_inventory.item_id = items.item_id
                WHERE user_id = ? AND item_secret = 0 AND item_name LIKE ? 
                ORDER BY item_name LIMIT 25;
            """, (interaction.user.id, f'%{current}%'))
            items = await cursor.fetchall()
        return [discord.app_commands.Choice(name=item[0], value=item[0]) for item in items]
    
    @item_group.command(name="give")
    @discord.app_commands.describe(
        item_name="The name of the item to give",
        receiver="The user who will receive the item",
        amount="The amount of the item to give"
    )
    @discord.app_commands.autocomplete(item_name=item_give_autocomplete)
    async def item_give(self, interaction: discord.Interaction, item_name: str, receiver: discord.Member, amount: int):
        """Allows a user to give an item to another user."""
        async with aiosqlite.connect('data/main.db') as conn:
            # Check if the user has the item and the amount
            cursor = await conn.execute("""
                SELECT user_inventory.item_id, user_inventory.amount FROM user_inventory
                JOIN items ON user_inventory.item_id = items.item_id
                WHERE user_id = ? AND item_name = ? AND item_secret = 0;
            """, (interaction.user.id, item_name))
            item = await cursor.fetchone()

            if not item or item[1] < amount:
                await interaction.response.send_message("❌ | You do not have enough of this item or it is a secret item.", ephemeral=True)
                return

            # Update the giver's inventory
            new_amount = item[1] - amount
            if new_amount > 0:
                await conn.execute("UPDATE user_inventory SET amount = ? WHERE user_id = ? AND item_id = ?;", (new_amount, interaction.user.id, item[0]))
            else:
                await conn.execute("DELETE FROM user_inventory WHERE user_id = ? AND item_id = ?;", (interaction.user.id, item[0]))

            # Update the receiver's inventory
            cursor = await conn.execute("SELECT amount FROM user_inventory WHERE user_id = ? AND item_id = ?;", (receiver.id, item[0]))
            existing = await cursor.fetchone()
            if existing:
                new_receiver_amount = existing[0] + amount
                await conn.execute("UPDATE user_inventory SET amount = ? WHERE user_id = ? AND item_id = ?;", (new_receiver_amount, receiver.id, item[0]))
            else:
                await conn.execute("INSERT INTO user_inventory (user_id, item_id, amount) VALUES (?, ?, ?);", (receiver.id, item[0], amount))

            await conn.commit()
        await interaction.response.send_message(f"✅ | You have given {amount} of {item_name} to {receiver.display_name}.")

    @item_group.command(name="info")
    @discord.app_commands.describe(item_name="The name of the item to get information about")
    @discord.app_commands.autocomplete(item_name=autocomplete_item_names)
    async def item_info(self, interaction: discord.Interaction, item_name: str):
        """Provides detailed information about an item, sending ephemeral for secret items."""
        async with aiosqlite.connect('data/main.db') as conn:
            cursor = await conn.execute("""
                SELECT item_name, item_description, item_image, item_price, item_source, item_secret
                FROM items
                WHERE item_name = ?;
            """, (item_name,))
            item = await cursor.fetchone()

        if not item:
            await interaction.response.send_message("🚫 | Item not found.", ephemeral=True)
            return

        # Creating the embed for item information
        embed = discord.Embed(
            title=f"🔍 Item Info: {item[0]}",
            description=item[1],
            color=discord.Colour.blue()
        )
        if item[2]:  # If there's an image URL
            embed.set_image(url=item[2])
        embed.add_field(name="Gold Value", value=f"{item[3]} G", inline=True)
        embed.add_field(name="Source", value=item[4], inline=True)

        # Check if the item is marked as secret
        is_secret = item[5]  # Assuming item[5] is the item_secret field
        if is_secret:
            # Send the response as ephemeral if the item is secret
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            # Send a normal response if the item is not secret
            await interaction.response.send_message(embed=embed)

    @discord.app_commands.command(name="inventory")
    @discord.app_commands.guilds(discord.Object(id=741447688079540224))
    async def inventory(self, interaction: discord.Interaction, user: discord.Member = None):
        """View your inventory or another user's inventory."""
        user = user if user else interaction.user
        async with aiosqlite.connect('data/main.db') as conn:
            cursor = await conn.execute("""
                SELECT items.item_id, items.item_name, items.item_description, SUM(user_inventory.amount) AS total_amount
                FROM user_inventory
                JOIN items ON user_inventory.item_id = items.item_id
                WHERE user_id = ?
                GROUP BY items.item_id
                ORDER BY items.item_name;
            """, (user.id,))
            items = await cursor.fetchall()

        if not items:
            await interaction.response.send_message("🚫 | The inventory is empty!", ephemeral=True)
            return

        # Create pages from items
        page_size = 10
        pages = [items[i:i + page_size] for i in range(0, len(items), page_size)]

        view = self.InventoryView(user, 0, pages)
        embed = view.create_embed()
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    class InventoryView(discord.ui.View):
        def __init__(self, author, page, pages):
            super().__init__(timeout=180)  # Timeout after 180 seconds of inactivity
            self.author = author
            self.page = page
            self.pages = pages

        @discord.ui.button(label='Previous', style=discord.ButtonStyle.blurple)
        async def previous_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            if self.page > 0:
                self.page -= 1
            else:
                self.page = len(self.pages) - 1
            await interaction.response.edit_message(embed=self.create_embed(), view=self)

        @discord.ui.button(label='Next', style=discord.ButtonStyle.blurple)
        async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            if self.page < len(self.pages) - 1:
                self.page += 1
            else:
                self.page = 0
            await interaction.response.edit_message(embed=self.create_embed(), view=self)

        def create_embed(self):
            items = self.pages[self.page]
            embed = discord.Embed(title="🎒 Your Inventory", description=f"Page {self.page + 1} of {len(self.pages)}", color=discord.Colour.blue())
            embed.set_author(name=self.author.display_name, icon_url=self.author.display_avatar.url)
            for item_id, item_name, item_description, total_amount in items:
                embed.add_field(name=f"{item_name} (x{total_amount})", value=f"{item_description}", inline=False)
            return embed

        async def interaction_check(self, interaction: discord.Interaction):
            if interaction.user.id != self.author.id:
                await interaction.response.send_message("❌ | You do not have permission to interact with this inventory.", ephemeral=True)
                return False
            return True
        
    
async def setup(bot):
    await bot.add_cog(items_and_inventory(bot))