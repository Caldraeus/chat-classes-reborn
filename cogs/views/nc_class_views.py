import discord
import helper as h

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
