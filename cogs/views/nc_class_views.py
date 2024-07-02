import discord
import helper as h
import aiosqlite

async def fetch_demons():
    db_path = 'data/class_specific.db'
    async with aiosqlite.connect(db_path) as conn:
        cursor = await conn.execute("SELECT demon_id, demon_name, demon_desc, demon_img FROM pacted_demons_list")
        demons = await cursor.fetchall()
        return [{'demon_id': demon[0], 'demon_name': demon[1], 'demon_desc': demon[2], 'demon_img': demon[3]} for demon in demons]

async def update_user_demon(demon_id, user_id):
    db_path = 'data/class_specific.db'
    async with aiosqlite.connect(db_path) as conn:
        # Check if there's already an entry for this user
        async with conn.execute("SELECT demon_id FROM pacted_user_list WHERE user_id = ?", (user_id,)) as cursor:
            existing = await cursor.fetchone()
        
        if existing:
            # If an entry exists, update it
            await conn.execute("UPDATE pacted_user_list SET demon_id = ? WHERE user_id = ?", (demon_id, user_id))
        else:
            # If no entry exists, insert a new one
            await conn.execute("INSERT INTO pacted_user_list (user_id, demon_id) VALUES (?, ?)", (user_id, demon_id))
        
        await conn.commit()

class DemonSelect(discord.ui.Select):
    def __init__(self, demons):
        options = [
            discord.SelectOption(label=demon['demon_name'], description=demon['demon_desc'][:100], value=str(demon['demon_id']))
            for demon in demons
        ]
        super().__init__(placeholder='Choose your demon...', min_values=1, max_values=1, options=options)
        self.demons = demons

    async def callback(self, interaction: discord.Interaction):
        selected_demon = next(demon for demon in self.demons if str(demon['demon_id']) == self.values[0])

        embed = discord.Embed(title=f"🔥 Previewing Demon: {selected_demon['demon_name']} 🔥", description=selected_demon['demon_desc'], color=0x750385)
        if selected_demon['demon_img']:
            embed.set_image(url=selected_demon['demon_img'])

        await interaction.response.edit_message(content="Review your selected demon:", embed=embed, view=self.view)

class ConfirmButton(discord.ui.Button):
    def __init__(self, label="Confirm Demon", style=discord.ButtonStyle.green):
        super().__init__(label=label, style=style)

    async def callback(self, interaction: discord.Interaction):
        demon_id = self.view.children[0].values[0]  # Assuming the first child is the Select menu
        user_id = interaction.user.id
        await update_user_demon(int(demon_id), user_id)
        
        selected_demon = next(demon for demon in self.view.children[0].demons if str(demon['demon_id']) == demon_id)
        await interaction.response.send_message(f"You have chosen the demon **{selected_demon['demon_name']}**.", ephemeral=True)
        self.view.stop()

class DemonSelection(discord.ui.View):
    def __init__(self, demons, user_id):
        super().__init__(timeout=180)
        self.user_id = user_id
        self.add_item(DemonSelect(demons))
        self.add_item(ConfirmButton())

async def handle_demon_choice(interaction):
    demons = await fetch_demons()
    view = DemonSelection(demons, interaction.user.id)
    await interaction.response.send_message("Choose your demon:", view=view, ephemeral=True)

class TradeView(discord.ui.View):
    def __init__(self, inventory, target):
        super().__init__()
        self.add_item(TradeDropdown(inventory, target))

class TradeDropdown(discord.ui.Select):
    def __init__(self, inventory, target):
        # Using both item_id and item_name directly as part of the options
        options = [
            discord.SelectOption(label=f"{item_name} (Qty: {amount})", description=f"{amount} available", value=f"{item_id},{item_name}")
            for item_id, amount, item_name in inventory
        ]
        super().__init__(placeholder="Choose an item to trade...", min_values=1, max_values=1, options=options)
        self.target = target

    async def callback(self, interaction: discord.Interaction):
        selected_value = self.values[0]
        item_id, item_name = selected_value.split(',', 1)  # Splitting to get both ID and name
        modal = TradeModal(item_name, item_id, self.target)
        await interaction.response.send_modal(modal)

class TradeModal(discord.ui.Modal, title="Trade Details"):
    def __init__(self, item_name, item_id, target):
        self.item_name = item_name
        self.item_id = item_id  # Keeping the item_id for transactions
        self.target = target
        super().__init__()
        self.quantity = discord.ui.TextInput(label="Quantity to Trade", style=discord.TextStyle.short)
        self.add_item(self.quantity)
        self.price = discord.ui.TextInput(label="Asking Price", style=discord.TextStyle.short)
        self.add_item(self.price)

    async def on_submit(self, interaction: discord.Interaction):
        quantity = int(self.quantity.value)
        price = int(self.price.value)
        confirm_view = ConfirmTradeView(self.item_name, self.item_id, quantity, price, interaction.user, self.target)
        await interaction.response.send_message(f"{self.target.mention}, {interaction.user.display_name} wants to trade {quantity} {self.item_name} for {price} Gold. Accept the trade?", view=confirm_view, ephemeral=False)

class ConfirmTradeView(discord.ui.View):
    def __init__(self, item_name, item_id, quantity, price, sender, target):
        super().__init__()
        self.item_name = item_name
        self.item_id = item_id
        self.quantity = quantity
        self.price = price
        self.sender = sender
        self.target = target

    @discord.ui.button(label="Accept Trade", style=discord.ButtonStyle.success)
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Ensure only the target can press this button
        if interaction.user.id != self.target.id:
            await interaction.response.send_message("You are not authorized to accept this trade.", ephemeral=True)
            return

        # Check if the target has enough gold
        if not await h.check_gold(self.target.id, self.price):
            await interaction.response.send_message("You do not have enough gold to accept this trade.", ephemeral=True)
            return

        # Check if the sender still has the item and the quantity
        if not await h.check_item_quantity(self.sender.id, self.item_name, self.quantity):
            await interaction.response.send_message("The trade could not be completed. Item or quantity unavailable.", ephemeral=True)
            return
        
        if self.price < 0:
            await interaction.response.send_message("Wait, negative gold!? Nice try, buddy! Trade automatically declined!")
            return

        # Process the trade using item_id directly
        await h.give_item(self.target.id, self.item_id, self.quantity)
        await h.remove_item(self.sender.id, self.item_id, self.quantity)
        await h.transfer_gold(self.target.id, self.sender.id, self.price)
        await interaction.response.send_message(f"Trade accepted! {self.target.display_name} received {self.quantity} {self.item_name} for {self.price} G.", ephemeral=False)
        if (self.item_name.lower()) == 'nft':
            await h.grant_achievement(interaction.channel, self.sender, 8)
        self.stop()

    @discord.ui.button(label="Deny Trade", style=discord.ButtonStyle.danger)
    async def deny(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Ensure only the target can press this button
        if interaction.user.id != self.target.id:
            await interaction.response.send_message("You are not authorized to deny this trade.", ephemeral=True)
            return

        await interaction.response.send_message("Trade denied.", ephemeral=False)
        self.stop()

class OfferServiceModal(discord.ui.Modal, title="Offer Service"):
    def __init__(self, cog, target):
        self.cog = cog
        self.target = target
        super().__init__()
        self.price = discord.ui.TextInput(label="Price for Services (in Gold)", style=discord.TextStyle.short)
        self.add_item(self.price)

    async def on_submit(self, interaction: discord.Interaction):
        price = int(self.price.value)
        confirm_view = ConfirmHireView(price, interaction.user, self.target, self.cog)
        if price < 0:
            await interaction.response.send_message(f"{interaction.user.mention}, nice try.", ephemeral=True)
        else:
            await interaction.response.send_message(f"{self.target.mention}, {interaction.user.display_name} offers their services for {price} Gold. Do you accept?", view=confirm_view, ephemeral=False)

class ConfirmHireView(discord.ui.View):
    def __init__(self, price, sellsword, target, cog):
        super().__init__()
        self.price = price
        self.sellsword = sellsword
        self.target = target
        self.cog = cog

    @discord.ui.button(label="Hire Sellsword", style=discord.ButtonStyle.success)
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.target.id:
            await interaction.response.send_message("You are not authorized to accept this offer.", ephemeral=True)
            return

        if self.sellsword.id in self.cog.hired:
            await interaction.response.send_message("This sellsword has already been hired for the day!", ephemeral=True)
            return

        if interaction.user.id in self.cog.hired.values():
            await interaction.response.send_message("You have already hired a sellsword for the day!", ephemeral=True)
            return

        # Check if the hiring user has enough gold
        if not await h.check_gold(interaction.user.id, self.price):
            await interaction.response.send_message("You do not have enough gold to hire this sellsword.", ephemeral=True)
            return

        # Process the hiring
        await h.add_gold(interaction.user.id, -self.price)
        await h.add_gold(self.sellsword.id, self.price)
        self.cog.hired[self.sellsword.id] = interaction.user.id
        await interaction.response.send_message(f"{interaction.user.mention} has hired {self.sellsword.mention} for the rest of the day! The Sellsword will get 100 coolness every time you are attacked!", ephemeral=False)
        self.stop()

    @discord.ui.button(label="Decline", style=discord.ButtonStyle.danger)
    async def deny(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.target.id:
            await interaction.response.send_message("You are not authorized to decline this offer.", ephemeral=True)
            return

        await interaction.response.send_message("Offer declined.", ephemeral=False)
        self.stop()