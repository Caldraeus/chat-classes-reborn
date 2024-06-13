from discord.ext import commands
import discord
from discord import app_commands
import aiosqlite
import helper as h
from typing import List
import random

class items_and_inventory(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.item_actions = {
            "Hot Dog": self.use_simple_item,
            "Snake Oil": self.use_simple_item,
            "NFT":self.use_simple_item,
            "World War II Souvenir":self.use_simple_item,
            "Monster Energy":self.use_simple_item
        }

    item_group = discord.app_commands.Group(name="item", description="Manage your items")

    # Autocomplete function for item names based on user inventory
    async def autocomplete_item_names_inventory(self, interaction: discord.Interaction, current: str):
        async with aiosqlite.connect('data/main.db') as conn:
            cursor = await conn.execute("""
                SELECT item_name FROM user_inventory
                JOIN items ON user_inventory.item_id = items.item_id
                WHERE user_id = ? AND item_name LIKE ?;
            """, (interaction.user.id, f'%{current}%'))
            items = await cursor.fetchall()
            print(items)
            return [discord.app_commands.Choice(name=item[0], value=item[0]) for item in items]

    async def autocomplete_item_names(self, interaction: discord.Interaction, current: str):
        # First, retrieve the user's class to determine which items they should see
        user_class = await h.get_user_class(interaction.user.id)

        async with aiosqlite.connect('data/main.db') as conn:
            if user_class == 'Trader':
                # If the user is a Trader, include items that are not secret or sourced from 'Trader'
                cursor = await conn.execute("""
                    SELECT item_name FROM items
                    WHERE (item_secret = 0 OR item_source = 'Trader') AND item_name LIKE ?;
                """, (f'%{current}%',))
            else:
                # For users who are not Traders, only show items that are not secret
                cursor = await conn.execute("""
                    SELECT item_name FROM items
                    WHERE item_secret = 0 AND item_name LIKE ?;
                """, (f'%{current}%',))
            
            items = await cursor.fetchall()
            print(items)  # Debugging print to check fetched items
            # Create choices for the autocomplete feature
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

    async def item_use_autocomplete(self, interaction: discord.Interaction, current: str):
        """Provides autocomplete for any items in the user's inventory."""
        async with aiosqlite.connect('data/main.db') as conn:
            cursor = await conn.execute("""
                SELECT item_name FROM user_inventory
                JOIN items ON user_inventory.item_id = items.item_id
                WHERE user_id = ? AND item_name LIKE ?
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
    @discord.app_commands.autocomplete(item_name=autocomplete_item_names_inventory)
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

    @item_group.command(name="buy")
    @discord.app_commands.describe(
        item_name="The name of the item to buy",
        amount="The amount of the item to buy (default is 1)"
    )
    @discord.app_commands.autocomplete(item_name=autocomplete_item_names)
    async def item_buy(self, interaction: discord.Interaction, item_name: str, amount: int = 1):
        """Buy an item from the shop."""
        user_id = interaction.user.id
        async with aiosqlite.connect('data/main.db') as conn:
            cursor = await conn.execute("""
                SELECT items.item_id, items.item_price, items.item_secret, items.item_source
                FROM items
                WHERE item_name = ?;
            """, (item_name,))
            item = await cursor.fetchone()

            if not item:
                await interaction.response.send_message("🚫 | Item not found.", ephemeral=True)
                return

            # Fetch the user's class
            user_class = await h.get_user_class(user_id)

            if item[2] and (item[3] != user_class):  # Check if the item is secret and not available to the user's class
                await interaction.response.send_message("🚫 | This item cannot be bought by your class.", ephemeral=True)
                return

            total_cost = item[1] * amount

            # Check if the user has enough gold
            cursor = await conn.execute("SELECT gold FROM users WHERE user_id = ?;", (user_id,))
            user_gold = await cursor.fetchone()

            if not user_gold or user_gold[0] < total_cost:
                await interaction.response.send_message(f"🚫 | You do not have enough gold. You need {total_cost} G.", ephemeral=True)
                return

            # Deduct gold from the user
            await conn.execute("UPDATE users SET gold = gold - ? WHERE user_id = ?;", (total_cost, user_id))

            # Add item to user's inventory
            cursor = await conn.execute("SELECT amount FROM user_inventory WHERE user_id = ? AND item_id = ?;", (user_id, item[0]))
            existing = await cursor.fetchone()
            total_amount = (existing[0] + amount) if existing else amount

            if existing:
                await conn.execute("UPDATE user_inventory SET amount = ? WHERE user_id = ? AND item_id = ?;", (total_amount, user_id, item[0]))
            else:
                await conn.execute("INSERT INTO user_inventory (user_id, item_id, amount) VALUES (?, ?, ?);", (user_id, item[0], total_amount))

            await conn.commit()
        if total_amount > 100:
            await h.grant_achievement(interaction.channel, interaction.user, 7)
        await interaction.response.send_message(f"✅ | You have bought {amount} {item_name} for {total_cost} G.", ephemeral=True)


    @item_group.command(name="shop")
    async def item_shop(self, interaction: discord.Interaction):
        """Displays the item shop with pagination."""
        user_class = await h.get_user_class(interaction.user.id)

        if user_class == 'Trader':
            async with aiosqlite.connect('data/main.db') as conn:
                cursor = await conn.execute("""
                    SELECT item_name, item_description, item_price
                    FROM items
                    WHERE item_secret = 0 OR item_source = 'Trader'
                    ORDER BY item_name;
                """)
                items = await cursor.fetchall()
        else:
            async with aiosqlite.connect('data/main.db') as conn:
                cursor = await conn.execute("""
                    SELECT item_name, item_description, item_price
                    FROM items
                    WHERE item_secret = 0
                    ORDER BY item_name;
                """)
                items = await cursor.fetchall()

        if not items:
            await interaction.response.send_message("🚫 | The shop is empty!", ephemeral=True)
            return

        # Create pages from items
        pages = h.paginate(items, page_size=5)

        view = self.ShopView(interaction.user, 0, pages)
        embed = view.create_embed()
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @item_group.command(name="use")
    @discord.app_commands.describe(
        item_name="The name of the item to use"
    )
    @discord.app_commands.autocomplete(item_name=item_use_autocomplete)
    async def item_use(self, interaction: discord.Interaction, item_name: str):
        """Use an item from your inventory."""
        async with aiosqlite.connect('data/main.db') as conn:
            cursor = await conn.execute("""
                SELECT items.item_id, items.item_description FROM items
                JOIN user_inventory ON items.item_id = user_inventory.item_id
                WHERE user_inventory.user_id = ? AND items.item_name = ?;
            """, (interaction.user.id, item_name))
            item = await cursor.fetchone()

            if not item:
                await interaction.response.send_message("🚫 | You do not have this item in your inventory.", ephemeral=True)
                return

        item_id, item_description = item

        # Check if the item requires a target
        if item_name in self.item_actions:
            action = self.item_actions[item_name]
            await action(interaction, item_name, item_id)
        else:
            await interaction.response.send_message("🚫 | This item cannot be used.", ephemeral=True)
    """
    ==============================================================================
    =============================== ITEM FUNCTIONS ===============================
    ==============================================================================
    """
    async def use_simple_item(self, interaction, item_name, item_id):
        if item_name == "Hot Dog":
            self.bot.user_aps[interaction.user.id] += 2
            await interaction.response.send_message("🌭 | You consume your delicious Hot Dog! Yum! **(+2 AP)**")
            await h.remove_item(interaction.user.id, item_id)
        elif item_name == "Monster Energy":
            self.bot.user_aps[interaction.user.id] += 5
            await interaction.response.send_message("<:monster:1250620428435587103> | You drink your monster energy... it's energizing! Now you have a bit more energy. **(+5 AP)**")
            await h.remove_item(interaction.user.id, item_id)
        elif item_name == "Snake Oil":
            cog = self.bot.get_cog('statuses')
            random_status = random.choice(list(cog.status_effects.keys()))
            random_stacks = random.randint(1,20)
            await interaction.response.send_message(f"🐍 | You drink your snake oil... holy hell, what was in that stuff!? You feel like you're... {random_status}!?")
            await cog.apply_status_effect(interaction.user.id, random_status, random_stacks)
            await h.remove_item(interaction.user.id, item_id)
        elif item_name == "NFT":
            user_class = await h.get_user_class(interaction.user.id)
            if user_class == 'Trader':
                await interaction.response.send_message(f'Woah there buddy, as a Trader, you wouldn\'t lay a finger on NFT\'s, since they\'re a scam and all. Try selling them to someone instead!', ephemeral=True)
                return
            
            is_scammed = random.random() <= 0.8

            amount = random.randint(100, 1000)

            if is_scammed:
                await interaction.response.send_message(f"🐒 | You take your NFT and... oh shit, you got scammed! You lose {amount} G.\n\nAnd for even trying to use an NFT, you also lose that same amount in coolness. Bummer, dude!")
                await h.add_gold(interaction.user.id, -amount)
                await h.add_coolness(interaction.user.id, -amount)
            else:
                await interaction.response.send_message(f"🐒 | You take your NFT and... do whatever people do with NFT's! It's a success! You gain {amount} G.\n\nBut honestly? NFT's suck. That's why you just lost that same amount in coolness.")
                await h.add_gold(interaction.user.id, amount)
                await h.add_coolness(interaction.user.id, -amount)
            await h.remove_item(interaction.user.id, item_id)
        elif item_name == "World War II Souvenir":
            
            exploded = random.random() <= 0.25

            amount = random.randint(200, 1500)

            if exploded:
                await interaction.response.send_message(f"💥 | You take out your World War II Souvenir and... oh, fuck this has been a bomb the whole time? Your souvenir explodes! You live, but that explosion was not cool, man. You lose {amount*3} coolness.")
                await h.add_coolness(interaction.user.id, -amount*3)
                await h.remove_item(interaction.user.id, item_id)
            else:
                await interaction.response.send_message(f"💣 | You take your World War II Souvenir out and show it off. Wow! That's pretty cool, especially the soft ticking noise! You put your souvenir back into your pocket for later. (**+{amount} Coolness!**)")
                await h.add_coolness(interaction.user.id, amount)

    # Example method for an item requiring a target
    async def use_targeted_item(self, interaction, item_name):
        await interaction.response.send_message(
            "Please select a target:",
            view=self.TargetSelectionView(self.bot, interaction.user.id, item_name)
        )

    class TargetSelectionView(discord.ui.View):
        def __init__(self, bot, user_id, item_name):
            super().__init__(timeout=60)
            self.bot = bot
            self.user_id = user_id
            self.item_name = item_name

        @discord.ui.button(label="Select Target", style=discord.ButtonStyle.primary)
        async def select_target(self, interaction: discord.Interaction, button: discord.ui.Button):
            await interaction.response.send_message("Please mention the user you want to target.")

        async def interaction_check(self, interaction: discord.Interaction):
            if interaction.user.id != self.user_id:
                await interaction.response.send_message("❌ | You do not have permission to interact with this.", ephemeral=True)
                return False
            return True

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
        
    class ShopView(discord.ui.View):
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
            embed = discord.Embed(title="🍺 Consumables Shop 🍺", description=f"Page {self.page + 1} of {len(self.pages)}", color=discord.Colour.gold())
            embed.set_thumbnail(url='https://cdn-icons-png.flaticon.com/512/513/513893.png')
            for item_name, item_description, item_price in items:
                embed.add_field(name=f"{item_name} - {item_price} G", value=item_description, inline=False)
            return embed

        async def interaction_check(self, interaction: discord.Interaction):
            if interaction.user.id != self.author.id:
                await interaction.response.send_message("❌ | You do not have permission to interact with this shop.", ephemeral=True)
                return False
            return True
        
async def setup(bot):
    await bot.add_cog(items_and_inventory(bot))