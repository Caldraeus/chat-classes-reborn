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


race_stat_bonuses = {
    "Dragonborn":["Constitution", 1],
    "Dwarf":["Constitution", 2],
    "Elf":["Dexterity", 2],
    "Animalfolk":["Class", 2],
    "Gnome":["Intelligence",2],
    "Half-Elf":["Charisma", 2, "Class", 1],
    "Halfling":["Dexterity", 2],
    "Human":["Class", 1],
    "Orc":["Strength", 2],
    "Tiefling":["Charisma", 2],
    "Weaveborn":["Charisma", 1]
}

class InventoryButtons(discord.ui.View):
    def __init__(self, author, page, inv, raw_inv):
        super().__init__()
        self.author = author
        self.page = page
        self.inv = inv
        self.raw_inv = raw_inv

    @discord.ui.button(label=f'<', style=discord.ButtonStyle.red)
    async def back(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page -= 1
        if self.page < 0:
            self.page = len(self.inv) - 1

        profile = discord.Embed(title=f"Your Inventory", colour=discord.Colour(0x6eaf0b))
        profile.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar)

        for item in self.inv[self.page]:
            count = sum(1 for inv_item in self.raw_inv if inv_item[0] == item[0])
            name = f"{item[2]} (x{count})"
            rarity_and_level = f"{item[4].title()} - Level {item[5]}"
            description = f"{item[3]}"
            profile.add_field(name=name, value=f"• {rarity_and_level}\n• {description}", inline=False)

        profile.set_footer(text=f"Page {self.page + 1}/{len(self.inv)}")

        view = InventoryButtons(self.author, self.page, self.inv, self.raw_inv)
        await interaction.response.edit_message(view=view, embed=profile)

        self.stop()

    @discord.ui.button(label='>', style=discord.ButtonStyle.green)
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page += 1
        if self.page+1 > len(self.inv):
            self.page = 0

        profile = discord.Embed(title=f"Your Inventory", colour=discord.Colour(0x6eaf0b))
        profile.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar)

        for item in self.inv[self.page]:
            count = sum(1 for inv_item in self.raw_inv if inv_item[0] == item[0])
            name = f"{item[2]} (x{count})"
            rarity_and_level = f"{item[4].title()} - Level {item[5]}"
            description = f"{item[3]}"
            profile.add_field(name=name, value=f"• {rarity_and_level}\n• {description}", inline=False)

        profile.set_footer(text=f"Page {self.page + 1}/{len(self.inv)}")

        view = InventoryButtons(self.author, self.page, self.inv, self.raw_inv)
        await interaction.response.edit_message(view=view, embed=profile)

        self.stop()

    async def interaction_check(self, interaction: discord.Interaction):
        return interaction.user.id == self.author.id

class ProfileMainButton(discord.ui.View):
    def __init__(self, author, target):
        super().__init__()
        self.target = target
        self.author = author

    @discord.ui.button(label='Equipment', style=discord.ButtonStyle.grey)
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
        async with aiosqlite.connect('data/game.db') as conn:
            async with conn.execute(f"SELECT * FROM character_stats WHERE user_id = {self.target.id};") as char_stat_info:
                char_info = await char_stat_info.fetchone()
            async with conn.execute(f"SELECT * FROM character_lore WHERE user_id = {self.target.id}") as character_lore_info:
                character_lore = await character_lore_info.fetchone()
            async with conn.execute(f"SELECT class_name FROM classes WHERE class_id = {char_info[9]}") as class_name_info:
                class_name = await class_name_info.fetchone()
            async with conn.execute(f"SELECT character_inventory.item_id, character_inventory.equipped, items.item_name, items.item_type FROM character_inventory INNER JOIN items ON character_inventory.item_id=items.item_id WHERE user_id = {self.target.id} AND equipped = 1;") as equip_info:
                equipped_stuff = await equip_info.fetchall()

        class_name = class_name[0]

        profile = discord.Embed(title=f"{character_lore[1]}'s Bio", colour=discord.Colour(0x6eaf0b))
        profile.set_author(name=self.target.display_name, icon_url=self.target.display_avatar)
        profile.set_image(url=character_lore[3])

        if equipped_stuff == []:
            profile.description = "Looks like they have nothing equipped!"
        else:
            items_by_type = {}
            for item in equipped_stuff:
                item_type = item[3].replace("_", " ")
                item_type = item_type.split()
                if item_type[0] not in items_by_type:
                    items_by_type[item_type[0]] = []
                items_by_type[item_type[0]].append(item[2])

            items_str = ""
            for item_type, item_names in items_by_type.items():
                items_str += f"**{item_type.title()}**:\n"
                items_str += "\n".join(f"- {name}" for name in item_names)
                items_str += "\n\n"

            profile.description = f"{character_lore[1]}'s currently equipped items:\n\n{items_str}"

        profile.set_footer(text=f'Level {char_info[2]} {class_name}')

        view = ProfileBackButton(self.author, self.target)
        await interaction.response.edit_message(embed=profile, view=view)

        self.stop()

    async def interaction_check(self, interaction: discord.Interaction):
        return interaction.user.id == self.author.id


class ProfileBackButton(discord.ui.View):
    def __init__(self, author, target):
        super().__init__()
        self.author = author
        self.target = target

    @discord.ui.button(label='Main Page', style=discord.ButtonStyle.grey)
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            async with aiosqlite.connect('data/game.db') as conn:
                async with conn.execute(f"SELECT * FROM character_stats WHERE user_id = {self.target.id};") as char_stat_info:
                    char_info = await char_stat_info.fetchone()
                async with conn.execute(f"SELECT * FROM character_lore WHERE user_id = {self.target.id}") as character_lore_info:
                    character_lore = await character_lore_info.fetchone()
                async with conn.execute(f"SELECT class_name FROM classes WHERE class_id = {char_info[9]}") as class_name_info:
                    class_name = await class_name_info.fetchone()
                async with conn.execute(f"SELECT character_faction_stats.reputation, factions.faction_id, factions.faction_name FROM character_faction_stats INNER JOIN factions ON character_faction_stats.faction_id=factions.faction_id WHERE user_id = {self.target.id}") as faction_info:
                    faction = await faction_info.fetchone()
        except TypeError:
            await interaction.response.send_message("The target does not have a character!", ephemeral=True)
        else:
            view = ProfileMainButton(self.author, self.target) # We pass in ctx.author in order to enforce author only button clicks.
            class_name = class_name[0]

            # print(char_info)
            # print(character_lore)

            profile = discord.Embed(title=f"{character_lore[1]}'s Bio", colour=discord.Colour(0x6eaf0b), description=character_lore[2].replace("\\n", "\n"))
            profile.set_author(name=self.target.display_name, icon_url=self.target.display_avatar)
            profile.set_image(url=character_lore[3])
            ###
            ###
            profile.add_field(name="Class", value=f'Level {char_info[2]} {class_name}', inline=False)
            profile.add_field(name="Race", value=f'{char_info[1]}', inline=False)
            profile.add_field(name="XP", value=f'{char_info[12]} / {h.xp_lvl(int(char_info[2]))}', inline=True)
            profile.add_field(name="Currency", value=f'{char_info[11]} sp', inline=True)

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

            await interaction.response.edit_message(embed=profile, view=view)

            self.stop()
    
    async def interaction_check(self, interaction: discord.Interaction): # Not needed when in an ephemeral message, but still worth running.
        return interaction.user.id == self.author.id

class RaceSelect(discord.ui.View):
    def __init__(self, author):
        super().__init__()
        self.author = author

    @discord.ui.select(placeholder="What race are you?", min_values=1, max_values=1, options=[
        discord.SelectOption(label='Dragonborn', description='+2 Con, Breath Weapon', emoji='🐉'),
        discord.SelectOption(label='Dwarf', description='+2 Con, +5 Poison Resist', emoji='⚒️'),
        discord.SelectOption(label='Elf', description='+2 Dex, +5 Charm Resist', emoji='🧝'),
        discord.SelectOption(label='Animalfolk', description='+2 to Class Ability, Natural Weapons', emoji='🦊'),
        discord.SelectOption(label='Gnome', description='+2 Int, +5 Arcane Resist', emoji='🍀'),
        discord.SelectOption(label='Half-Elf', description='+2 Cha, +1 to Class Ability', emoji='🧝‍♂️'),
        discord.SelectOption(label='Halfling', description='+2 Dex, Halfling Luck', emoji='🩳'),
        discord.SelectOption(label='Half-Orc', description='+2 Str, Relentless Endurance', emoji='🪓'),
        discord.SelectOption(label='Human', description='+1 to Class Ability, Adaptable (1.5x XP)', emoji='🧑'),
        discord.SelectOption(label='Orc', description='+2 Str, Aggresive', emoji='🧌'),
        discord.SelectOption(label='Tiefling', description='+2 Cha, +5 Fire Resist', emoji='😈'),
        discord.SelectOption(label='Weaveborn', description='+1 Cha, +1 Arcane Damage', emoji='✨'),
    ])
    async def selected_option(self, interaction: discord.Interaction, select: discord.ui.Select):
        race = select.values[0]
        view = ClassSelect(interaction.user, race) # We pass in ctx.author in order to enforce author only button clicks.
        await interaction.response.edit_message(content="Next, choose a class!", view=view)
        self.stop()

    async def interaction_check(self, interaction: discord.Interaction): # Not needed when in an ephemeral message, but still worth running.
        return interaction.user.id == self.author.id

class ClassSelect(discord.ui.View):
    def __init__(self, author, race):
        super().__init__()
        self.author = author
        self.race = race

    @discord.ui.select(placeholder="What class are you?", min_values=1, max_values=1, options=[
        discord.SelectOption(label='Alchemist', description='[INT] Alchemists brew potions and create new alchemic inventions to fight', emoji='⚗️'),
        discord.SelectOption(label='Artificer', description='[INT] Master of arcane tinkering, artificers combine magic and science to fight.', emoji='🔰'),
        discord.SelectOption(label='Barbarian', description='[STR] Fierce fighters that hit hard and can RAGE!', emoji='💢'),
        discord.SelectOption(label='Bard', description='[CHA] Magical casters who use performance to wow audiences and shock enemies.', emoji='🎸'),
        discord.SelectOption(label='Captain', description='[CHA] Leaders and fighters who command a squire in battle!', emoji='🚩'),
        discord.SelectOption(label='Cleric', description='[WIS] Holy fighters that specialise in a certain holy domain.', emoji='👼'),
        discord.SelectOption(label='Craftsman', description='[INT] Tinkerers and builders, craftsman make weapons and items!', emoji='🧰'),
        discord.SelectOption(label='Druid', description='[WIS] Magical fighters that can turn into an animal!', emoji='🐻'),
        discord.SelectOption(label='Fighter', description='[STR] Your main fighter! Can use most weapons and is adaptable.', emoji='⚔️'),
        discord.SelectOption(label='Gunslinger', description='[DEX] Wielders of an ancient weapon - firearms!', emoji='🔫'),
        discord.SelectOption(label='Investigator', description='[INT] Investigators are masters of ritual casting, and investigate the paranormal!', emoji='🔍'),
        discord.SelectOption(label='Martyr', description='[CON] Fated by the gods to die, Martyrs wield holy energy and fight with resolve.', emoji='✝️'),
        discord.SelectOption(label='Monk', description='[DEX] Warriors that fight with their fists and use mystical ki.', emoji='🤜'),
        discord.SelectOption(label='Necromancer', description='[INT] Specialised casters that manipulate the anima of the dead.', emoji='🧟'),
        discord.SelectOption(label='Paladin', description='[CHA] Virtuous protectors that follow a code.', emoji='🔰'),
        discord.SelectOption(label='Ranger', description='[DEX] Trackers and fighters, often times using a bow.', emoji='🏹'),
        discord.SelectOption(label='Rogue', description='[DEX] Sneaky by nature, rogue\'s are dexterity fighters that do sneak attacks!', emoji='⚔️'),
        discord.SelectOption(label='Sorcerer', description='[CHA] Magical casters due to heritage, Sorcerers cast spells and manipulate the weave.', emoji='✨'),
        discord.SelectOption(label='Warden', description='[CON] Hardy protectors, Wardens are usually the first line of defense in a party.', emoji='🛡️'),
        discord.SelectOption(label='Warlock', description='[CHA] Casters that have pacts with strong beings, Warlocks use a fraction of their patron\'s magic.', emoji='😈'),
        discord.SelectOption(label='Warmage', description='[INT] Cantrip masters, Warmages use cantrips as their main fighting tool.', emoji='🎴'),
        discord.SelectOption(label='Witch', description='[CHA] Always bearing a curse, a Witch is a caster that makes use of hexes and vexes.', emoji='🐈‍⬛'),
        discord.SelectOption(label='Wizard', description='[INT] Masters of the arcane, Wizards are known for their magical prowess.', emoji='🪄'),
    ])
    async def selected_option(self, interaction: discord.Interaction, select: discord.ui.Select):
        # Depending on their chosen class, output their primary stat.
        chosen_class = select.values[0]
        stats = h.class_main_stats

        values = list(stats.values())

        for sublist in values:
            if chosen_class in sublist:
                primary_stat = list(stats.keys())[values.index(sublist)]
                break
            else:
                pass # Keep looping until found.

        view = StatsSelectPart1(interaction.user, self.race, chosen_class, None, primary_stat) # We pass in ctx.author in order to enforce author only button clicks.
        await interaction.response.edit_message(content=f"Next, your stats! Because you are a {chosen_class.title()}, I recommend making **{primary_stat.title()}** your highest ability score.", view=view)
        self.stop()

    async def interaction_check(self, interaction: discord.Interaction): # Not needed when in an ephemeral message, but still worth running.
        return interaction.user.id == self.author.id


class StatsSelectPart1(discord.ui.View):
    def __init__(self, author, race, selected_class, stats = None, primary_stat = None):
        super().__init__()
        self.author = author
        self.race = race
        self.chosen_class = selected_class
        self.primary_stat = primary_stat

        if stats == None:
            self.stats = {
                'strength': None,
                'dexterity':None,
                'charisma':None,
                'constitution':None,
                'wisdom':None,
                'intelligence':None
            }
        else:
            self.stats = stats

        class_stats = h.class_main_stats
        values = list(class_stats.values())

    @discord.ui.select(placeholder="Strength", min_values=1, max_values=1, options=[
        discord.SelectOption(label='15', description=None, emoji=None),
        discord.SelectOption(label='14', description=None, emoji=None),
        discord.SelectOption(label='13', description=None, emoji=None),
        discord.SelectOption(label='12', description=None, emoji=None),
        discord.SelectOption(label='10', description=None, emoji=None),
        discord.SelectOption(label='8', description=None, emoji=None),
    ])
    async def strength(self, interaction: discord.Interaction, select: discord.ui.Select):
        self.stats["strength"] = select.values[0]
        await interaction.response.edit_message(content=f"Next, your stats! Because you are a {self.chosen_class.title()}, I recommend making **{self.primary_stat.title()}** your highest ability score.\n\n**STR: **{self.stats['strength']}\n**DEX: **{self.stats['dexterity']}\n**CON: **{self.stats['constitution']}\n**CHA: **{self.stats['charisma']}\n**INT: **{self.stats['intelligence']}\n**WIS: **{self.stats['wisdom']}")

    @discord.ui.select(placeholder="Dexterity", min_values=1, max_values=1, options=[
        discord.SelectOption(label='15', description=None, emoji=None),
        discord.SelectOption(label='14', description=None, emoji=None),
        discord.SelectOption(label='13', description=None, emoji=None),
        discord.SelectOption(label='12', description=None, emoji=None),
        discord.SelectOption(label='10', description=None, emoji=None),
        discord.SelectOption(label='8', description=None, emoji=None),
    ])
    async def dexterity(self, interaction: discord.Interaction, select: discord.ui.Select):
        self.stats["dexterity"] = select.values[0]
        await interaction.response.edit_message(content=f"Next, your stats! Because you are a {self.chosen_class.title()}, I recommend making **{self.primary_stat.title()}** your highest ability score.\n\n**STR: **{self.stats['strength']}\n**DEX: **{self.stats['dexterity']}\n**CON: **{self.stats['constitution']}\n**CHA: **{self.stats['charisma']}\n**INT: **{self.stats['intelligence']}\n**WIS: **{self.stats['wisdom']}")

    @discord.ui.select(placeholder="Charisma", min_values=1, max_values=1, options=[
        discord.SelectOption(label='15', description=None, emoji=None),
        discord.SelectOption(label='14', description=None, emoji=None),
        discord.SelectOption(label='13', description=None, emoji=None),
        discord.SelectOption(label='12', description=None, emoji=None),
        discord.SelectOption(label='10', description=None, emoji=None),
        discord.SelectOption(label='8', description=None, emoji=None),
    ])
    async def charisma(self, interaction: discord.Interaction, select: discord.ui.Select):
        self.stats["charisma"] = select.values[0]
        await interaction.response.edit_message(content=f"Next, your stats! Because you are a {self.chosen_class.title()}, I recommend making **{self.primary_stat.title()}** your highest ability score.\n\n**STR: **{self.stats['strength']}\n**DEX: **{self.stats['dexterity']}\n**CON: **{self.stats['constitution']}\n**CHA: **{self.stats['charisma']}\n**INT: **{self.stats['intelligence']}\n**WIS: **{self.stats['wisdom']}")

    @discord.ui.button(label='Next', style=discord.ButtonStyle.green)
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = StatsSelectPart2(interaction.user, self.race, self.chosen_class, self.stats, self.primary_stat) # We pass in ctx.author in order to enforce author only button clicks.
    
        await interaction.response.edit_message(content=f"Next, your stats! Because you are a {self.chosen_class.title()}, I recommend making **{self.primary_stat.title()}** your highest ability score.\n\n**STR: **{self.stats['strength']}\n**DEX: **{self.stats['dexterity']}\n**CON: **{self.stats['constitution']}\n**CHA: **{self.stats['charisma']}\n**INT: **{self.stats['intelligence']}\n**WIS: **{self.stats['wisdom']}", view=view)
        self.stop()

    async def interaction_check(self, interaction: discord.Interaction): # Not needed when in an ephemeral message, but still worth running.
        return interaction.user.id == self.author.id

class StatsSelectPart2(discord.ui.View):
    def __init__(self, author, race, selected_class, stats = None, primary_stat = None):
        super().__init__()
        self.author = author
        self.race = race
        self.chosen_class = selected_class
        self.primary_stat = primary_stat

        if stats == None:
            self.stats = {
                'strength': None,
                'dexterity':None,
                'charisma':None,
                'constitution':None,
                'wisdom':None,
                'intelligence':None
            }
        else:
            self.stats = stats

    @discord.ui.select(placeholder="Constitution", min_values=1, max_values=1, options=[
        discord.SelectOption(label='15', description=None, emoji=None),
        discord.SelectOption(label='14', description=None, emoji=None),
        discord.SelectOption(label='13', description=None, emoji=None),
        discord.SelectOption(label='12', description=None, emoji=None),
        discord.SelectOption(label='10', description=None, emoji=None),
        discord.SelectOption(label='8', description=None, emoji=None),
    ])
    async def constitution(self, interaction: discord.Interaction, select: discord.ui.Select):
        self.stats["constitution"] = select.values[0]
        await interaction.response.edit_message(content=f"Next, your stats! Because you are a {self.chosen_class.title()}, I recommend making **{self.primary_stat.title()}** your highest ability score.\n\n**STR: **{self.stats['strength']}\n**DEX: **{self.stats['dexterity']}\n**CON: **{self.stats['constitution']}\n**CHA: **{self.stats['charisma']}\n**INT: **{self.stats['intelligence']}\n**WIS: **{self.stats['wisdom']}")

    

    @discord.ui.select(placeholder="Wisdom", min_values=1, max_values=1, options=[
        discord.SelectOption(label='15', description=None, emoji=None),
        discord.SelectOption(label='14', description=None, emoji=None),
        discord.SelectOption(label='13', description=None, emoji=None),
        discord.SelectOption(label='12', description=None, emoji=None),
        discord.SelectOption(label='10', description=None, emoji=None),
        discord.SelectOption(label='8', description=None, emoji=None),
    ])
    async def wisdom(self, interaction: discord.Interaction, select: discord.ui.Select):
        self.stats["wisdom"] = select.values[0]
        await interaction.response.edit_message(content=f"Next, your stats! Because you are a {self.chosen_class.title()}, I recommend making **{self.primary_stat.title()}** your highest ability score.\n\n**STR: **{self.stats['strength']}\n**DEX: **{self.stats['dexterity']}\n**CON: **{self.stats['constitution']}\n**CHA: **{self.stats['charisma']}\n**INT: **{self.stats['intelligence']}\n**WIS: **{self.stats['wisdom']}")

    @discord.ui.select(placeholder="Intelligence", min_values=1, max_values=1, options=[
        discord.SelectOption(label='15', description=None, emoji=None),
        discord.SelectOption(label='14', description=None, emoji=None),
        discord.SelectOption(label='13', description=None, emoji=None),
        discord.SelectOption(label='12', description=None, emoji=None),
        discord.SelectOption(label='10', description=None, emoji=None),
        discord.SelectOption(label='8', description=None, emoji=None),
    ])
    async def intelligence(self, interaction: discord.Interaction, select: discord.ui.Select):
        self.stats["intelligence"] = select.values[0]
        await interaction.response.edit_message(content=f"Next, your stats! Because you are a {self.chosen_class.title()}, I recommend making **{self.primary_stat.title()}** your highest ability score.\n\n**STR: **{self.stats['strength']}\n**DEX: **{self.stats['dexterity']}\n**CON: **{self.stats['constitution']}\n**CHA: **{self.stats['charisma']}\n**INT: **{self.stats['intelligence']}\n**WIS: **{self.stats['wisdom']}")

    @discord.ui.button(label='Finish', style=discord.ButtonStyle.green)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        if(len(set(self.stats.values())) == len(self.stats.values()) and None not in self.stats.values()):
            # We have unique numbers in our array
            view = EquipmentSelect(interaction.user, self.race, self.chosen_class, self.stats, self.primary_stat) # We pass in ctx.author in order to enforce author only button clicks.

            await interaction.response.edit_message(content="Next, choose your starting kit!", view=view)
            self.stop()
        else:
            await interaction.response.edit_message(content=f"**ERROR:** Please ensure that you are not using a number more than once in your stats! You should have 15, 14, 13, 12, 10, and 8 be used once each.\n\nNext, your stats! Because you are a {self.chosen_class.title()}, I recommend making **{self.primary_stat.title()}** your highest ability score.\n\n**STR: **{self.stats['strength']}\n**DEX: **{self.stats['dexterity']}\n**CON: **{self.stats['constitution']}\n**CHA: **{self.stats['charisma']}\n**INT: **{self.stats['intelligence']}\n**WIS: **{self.stats['wisdom']}")

    @discord.ui.button(label="Back", style=discord.ButtonStyle.red)
    async def back(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = StatsSelectPart1(interaction.user, self.race, self.chosen_class, self.stats, self.primary_stat) # We pass in ctx.author in order to enforce author only button clicks.
        await interaction.response.edit_message(content=f"Next, your stats! Because you are a {self.chosen_class.title()}, I recommend making **{self.primary_stat.title()}** your highest ability score.\n\n**STR: **{self.stats['strength']}\n**DEX: **{self.stats['dexterity']}\n**CON: **{self.stats['constitution']}\n**CHA: **{self.stats['charisma']}\n**INT: **{self.stats['intelligence']}\n**WIS: **{self.stats['wisdom']}", view=view)
        self.stop()

    async def interaction_check(self, interaction: discord.Interaction): # Not needed when in an ephemeral message, but still worth running.
        return interaction.user.id == self.author.id

class EquipmentSelect(discord.ui.View):
    def __init__(self, author, race, chosen_class, stats, primary_stat):
        super().__init__()
        self.author = author
        self.race = race
        self.chosen_class = chosen_class
        self.stats = stats
        self.primary_stat = primary_stat

    @discord.ui.select(placeholder="Choose starting kit...", min_values=1, max_values=1, options=[
        discord.SelectOption(label='Basic Melee (STR)', description='A random light armor set, STR weapon, and a potion.', emoji='🎒'),
        discord.SelectOption(label='Basic Melee (DEX)', description='A random light armor set, DEX weapon, and a potion.', emoji='🎒'),
        discord.SelectOption(label='Basic Range (DEX)', description='A random light armor set, DEX weapon, and a potion.', emoji='🎒'),
        discord.SelectOption(label='Basic Tank (STR)', description='A random heavy armor set, STR weapon, and shield.', emoji='🎒'),
        discord.SelectOption(label='Basic Tank (DEX)', description='A random heavy armor set, DEX weapon, and shield.', emoji='🎒'),
        discord.SelectOption(label='Basic Caster (INT)', description='A random magic focus, light armor, and potion.', emoji='🎒'),
        discord.SelectOption(label='Basic Caster (CHA)', description='A random magic focus, light armor, and potion.', emoji='🎒'),
        discord.SelectOption(label='Basic Caster (WIS)', description='A random magic focus, light armor, and potion.', emoji='🎒')
    ])
    async def selected_option(self, interaction: discord.Interaction, select: discord.ui.Select):
        # view = Customization(interaction.user, self.race, self.chosen_class, self.stats, self.primary_stat, select.values[0]) # We pass in ctx.author in order to enforce author only button clicks.
        await interaction.response.send_modal(Customization(interaction.user, self.race, self.chosen_class, self.stats, self.primary_stat, select.values[0]))
        self.stop()

    async def interaction_check(self, interaction: discord.Interaction): # Not needed when in an ephemeral message, but still worth running.
        return interaction.user.id == self.author.id

class Customization(discord.ui.Modal, title='Character Information'):
    def __init__(self, author, race, chosen_class, stats, primary_stat, kit):
        super().__init__()
        self.author = author
        self.race = race
        self.chosen_class = chosen_class
        self.stats = stats
        self.primary_stat = primary_stat
        self.kit = kit
    
    # Our modal classes MUST subclass `discord.ui.Modal`,
    # but the title can be whatever you want.

    # This will be a short input, where the user can enter their name
    # It will also have a placeholder, as denoted by the `placeholder` kwarg.
    # By default, it is required and is a short-style input which is exactly
    # what we want.
    name = discord.ui.TextInput(
        label='Character Name',
        placeholder='Bilbo Baggins',
    )

    # This is a longer, paragraph style input, where user can submit feedback
    # Unlike the name, it is not required. If filled out, however, it will
    # only accept a maximum of 300 characters, as denoted by the
    # `max_length=300` kwarg.
    backstory = discord.ui.TextInput(
        label='What is your backstory?',
        style=discord.TextStyle.long,
        placeholder='A brave adventurer, they swore to fight evil!',
        required=False,
        max_length=500,
    )

    async def on_submit(self, interaction: discord.Interaction):
        response = f"""
Thanks for your feedback, {self.name.value}! Please review the following information to make sure it is correct.
**Name:** {self.name} \n(You can change this later if it's not correct right now!)
**Class:** {self.chosen_class}
**Race:** {self.race}
**Starting Kit:** {self.kit}

**STATS**
*STR:* {self.stats['strength']}
*CON:* {self.stats['constitution']}
*DEX:* {self.stats['dexterity']}
*INT:* {self.stats['intelligence']}
*WIS:* {self.stats['wisdom']}
*CHA:* {self.stats['charisma']}
Does this all look correct? Clicking "NO" will cancel the character creation process.

**NOTE:** Stats, class and race can NOT be changed later!
        """
        view = Finalize(interaction.user, self.race, self.chosen_class, self.stats, self.primary_stat, self.kit, self.name, self.backstory)
    
        await interaction.response.edit_message(content=response, view=view)
        self.stop()
        # await interaction.response.send_message(response, ephemeral=True)

    # async def on_error(self, interaction: discord.Interaction, error: Exception) -> None:
    #     await interaction.response.send_message('Oops! Something went wrong.', ephemeral=True)

    #     # Make sure we know what the error actually is
    #     traceback.print_tb(error.__traceback__)


class Finalize(discord.ui.View):
    def __init__(self, author, race, chosen_class, stats, primary_stat, kit, name, background):
        super().__init__()
        self.author = author
        self.race = race
        self.chosen_class = chosen_class
        self.stats = stats
        self.primary_stat = primary_stat
        self.kit = kit
        self.name = name
        self.bg = background

    @discord.ui.button(label='Finish', style=discord.ButtonStyle.green)
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="Done!", view=None)
        
        racial_bonus = race_stat_bonuses[self.race]

        for i in range(len(racial_bonus)):
            if type(racial_bonus[i]) == str:
                if racial_bonus[i] == "Class":
                    print(f"I will be adding {int(racial_bonus[i+1])} to {self.primary_stat.lower()} ({self.stats[self.primary_stat.lower()]})")
                    self.stats[self.primary_stat.lower()] = int(self.stats[self.primary_stat.lower()]) + int(racial_bonus[i+1])
                else:
                    self.stats[racial_bonus[i].lower()] = int(self.stats[racial_bonus[i].lower()]) + int(racial_bonus[i+1])

        # Insert character_stats information first.
        async with aiosqlite.connect('data/game.db') as conn:
            async with conn.execute(f"SELECT user_id FROM character_stats WHERE user_id = {self.author.id};") as person:
                user = await person.fetchone()
                if user: # They already have a profile.
                    await interaction.followup.send(content="Hey! You already have a character! Run the profile command to check it out!")
                else:
                    await interaction.followup.send(content=f"Everyone welcome {self.author.mention}'s new character, **{self.name}**! ({self.race} {self.chosen_class})")
                    # Actually insert them into the database.
                    await conn.execute(f"insert into character_stats values({self.author.id}, '{self.race}', 1, {self.stats['strength']}, {self.stats['dexterity']}, {self.stats['constitution']}, {self.stats['intelligence']}, {self.stats['wisdom']}, {self.stats['charisma']}, {h.class_ids[self.chosen_class]}, -1, 0, 0, {h.calc_base_hp(self.chosen_class, self.stats['constitution'])})")
                    await conn.commit()
        if user:
            print("Player Character already exists, moving on.")
        else:
            # Get their random equipment.
            if self.kit == "Basic Melee (STR)": 
                async with aiosqlite.connect('data/game.db') as conn:
                    async with conn.execute(f"SELECT item_id FROM items WHERE item_type IS 'WEAPON_MELEE' AND item_rarity IS 'COMMON' AND item_min_level IS 1 AND item_basic_rfplang LIKE '%STAT(STR)%'") as item_data:
                        chosen_weapon_id = await item_data.fetchall()
                        chosen_weapon_id = random.choice(chosen_weapon_id)[0]
                    async with conn.execute(f"SELECT item_id FROM items WHERE item_type IS 'CONSUMABLE_POTION' AND item_rarity IS 'COMMON' AND item_min_level IS 1") as potion_data:
                        chosen_potion_id = await potion_data.fetchall()
                        chosen_potion_id = random.choice(chosen_potion_id)[0]
                    async with conn.execute(f"SELECT item_id FROM items WHERE item_type IS 'ARMOR_LIGHT' AND item_rarity IS 'COMMON' AND item_min_level IS 1") as armor_data:
                        chosen_armor_id = await armor_data.fetchall()
                        chosen_armor_id = random.choice(chosen_armor_id)[0]
            elif self.kit == "Basic Melee (DEX)": 
                async with aiosqlite.connect('data/game.db') as conn:
                    async with conn.execute(f"SELECT item_id FROM items WHERE item_type IS 'WEAPON_MELEE' AND item_rarity IS 'COMMON' AND item_min_level IS 1 AND item_basic_rfplang LIKE '%STAT(DEX)%'") as item_data:
                        chosen_weapon_id = await item_data.fetchall()
                        chosen_weapon_id = random.choice(chosen_weapon_id)[0]
                    async with conn.execute(f"SELECT item_id FROM items WHERE item_type IS 'CONSUMABLE_POTION' AND item_rarity IS 'COMMON' AND item_min_level IS 1") as potion_data:
                        chosen_potion_id = await potion_data.fetchall()
                        chosen_potion_id = random.choice(chosen_potion_id)[0]
                    async with conn.execute(f"SELECT item_id FROM items WHERE item_type IS 'ARMOR_LIGHT' AND item_rarity IS 'COMMON' AND item_min_level IS 1") as armor_data:
                        chosen_armor_id = await armor_data.fetchall()
                        chosen_armor_id = random.choice(chosen_armor_id)[0]
            elif self.kit == "Basic Range (DEX)": 
                async with aiosqlite.connect('data/game.db') as conn:
                    async with conn.execute(f"SELECT item_id FROM items WHERE item_type IS 'WEAPON_RANGED' AND item_rarity IS 'COMMON' AND item_min_level IS 1 AND item_basic_rfplang LIKE '%STAT(DEX)%'") as item_data:
                        chosen_weapon_id = await item_data.fetchall()
                        chosen_weapon_id = random.choice(chosen_weapon_id)[0]
                    async with conn.execute(f"SELECT item_id FROM items WHERE item_type IS 'CONSUMABLE_POTION' AND item_rarity IS 'COMMON' AND item_min_level IS 1") as potion_data:
                        chosen_potion_id = await potion_data.fetchall()
                        chosen_potion_id = random.choice(chosen_potion_id)[0]
                    async with conn.execute(f"SELECT item_id FROM items WHERE item_type IS 'ARMOR_LIGHT' AND item_rarity IS 'COMMON' AND item_min_level IS 1") as armor_data:
                        chosen_armor_id = await armor_data.fetchall()
                        chosen_armor_id = random.choice(chosen_armor_id)[0]
            elif self.kit == "Basic Tank (STR)": 
                async with aiosqlite.connect('data/game.db') as conn:
                    async with conn.execute(f"SELECT item_id FROM items WHERE item_type IS 'WEAPON_MELEE' AND item_rarity IS 'COMMON' AND item_min_level IS 1 AND item_basic_rfplang LIKE '%STAT(STR)%'") as item_data:
                        chosen_weapon_id = await item_data.fetchall()
                        chosen_weapon_id = random.choice(chosen_weapon_id)[0]
                    async with conn.execute(f"SELECT item_id FROM items WHERE item_type IS 'WEAPON_SHIELD' AND item_rarity IS 'COMMON' AND item_min_level IS 1") as potion_data:
                        chosen_potion_id = await potion_data.fetchall()
                        chosen_potion_id = random.choice(chosen_potion_id)[0]
                    async with conn.execute(f"SELECT item_id FROM items WHERE item_type IS 'ARMOR_HEAVY' AND item_rarity IS 'COMMON' AND item_min_level IS 1") as armor_data:
                        chosen_armor_id = await armor_data.fetchall()
                        chosen_armor_id = random.choice(chosen_armor_id)[0]
            elif self.kit == "Basic Tank (DEX)": 
                async with aiosqlite.connect('data/game.db') as conn:
                    async with conn.execute(f"SELECT item_id FROM items WHERE item_type IS 'WEAPON_MELEE' AND item_rarity IS 'COMMON' AND item_min_level IS 1 AND item_basic_rfplang LIKE '%STAT(DEX)%'") as item_data:
                        chosen_weapon_id = await item_data.fetchall()
                        chosen_weapon_id = random.choice(chosen_weapon_id)[0]
                    async with conn.execute(f"SELECT item_id FROM items WHERE item_type IS 'WEAPON_SHIELD' AND item_rarity IS 'COMMON' AND item_min_level IS 1") as potion_data:
                        chosen_potion_id = await potion_data.fetchall()
                        chosen_potion_id = random.choice(chosen_potion_id)[0]
                    async with conn.execute(f"SELECT item_id FROM items WHERE item_type IS 'ARMOR_HEAVY' AND item_rarity IS 'COMMON' AND item_min_level IS 1") as armor_data:
                        chosen_armor_id = await armor_data.fetchall()
                        chosen_armor_id = random.choice(chosen_armor_id)[0]
            elif self.kit == "Basic Caster (INT)":
                async with aiosqlite.connect('data/game.db') as conn:
                    async with conn.execute(f"SELECT item_id FROM items WHERE item_type IS 'WEAPON_FOCUS' AND item_rarity IS 'COMMON' AND item_min_level IS 1 AND item_basic_rfplang LIKE '%STAT(INT)%'") as item_data:
                        chosen_weapon_id = await item_data.fetchall()
                        chosen_weapon_id = random.choice(chosen_weapon_id)[0]
                    async with conn.execute(f"SELECT item_id FROM items WHERE item_type IS 'CONSUMABLE_POTION' AND item_rarity IS 'COMMON' AND item_min_level IS 1") as potion_data:
                        chosen_potion_id = await potion_data.fetchall()
                        chosen_potion_id = random.choice(chosen_potion_id)[0]
                    async with conn.execute(f"SELECT item_id FROM items WHERE item_type IS 'ARMOR_LIGHT' AND item_rarity IS 'COMMON' AND item_min_level IS 1") as armor_data:
                        chosen_armor_id = await armor_data.fetchall()
                        chosen_armor_id = random.choice(chosen_armor_id)[0]
            elif self.kit == "Basic Caster (WIS)":
                async with aiosqlite.connect('data/game.db') as conn:
                    async with conn.execute(f"SELECT item_id FROM items WHERE item_type IS 'WEAPON_FOCUS' AND item_rarity IS 'COMMON' AND item_min_level IS 1 AND item_basic_rfplang LIKE '%STAT(WIS)%'") as item_data:
                        chosen_weapon_id = await item_data.fetchall()
                        chosen_weapon_id = random.choice(chosen_weapon_id)[0]
                    async with conn.execute(f"SELECT item_id FROM items WHERE item_type IS 'CONSUMABLE_POTION' AND item_rarity IS 'COMMON' AND item_min_level IS 1") as potion_data:
                        chosen_potion_id = await potion_data.fetchall()
                        chosen_potion_id = random.choice(chosen_potion_id)[0]
                    async with conn.execute(f"SELECT item_id FROM items WHERE item_type IS 'ARMOR_LIGHT' AND item_rarity IS 'COMMON' AND item_min_level IS 1") as armor_data:
                        chosen_armor_id = await armor_data.fetchall()
                        chosen_armor_id = random.choice(chosen_armor_id)[0]
            elif self.kit == "Basic Caster (CHA)":
                async with aiosqlite.connect('data/game.db') as conn:
                    async with conn.execute(f"SELECT item_id FROM items WHERE item_type IS 'WEAPON_FOCUS' AND item_rarity IS 'COMMON' AND item_min_level IS 1 AND item_basic_rfplang LIKE '%STAT(CHA)%'") as item_data:
                        chosen_weapon_id = await item_data.fetchall()
                        chosen_weapon_id = random.choice(chosen_weapon_id)[0]
                    async with conn.execute(f"SELECT item_id FROM items WHERE item_type IS 'CONSUMABLE_POTION' AND item_rarity IS 'COMMON' AND item_min_level IS 1") as potion_data:
                        chosen_potion_id = await potion_data.fetchall()
                        chosen_potion_id = random.choice(chosen_potion_id)[0]
                    async with conn.execute(f"SELECT item_id FROM items WHERE item_type IS 'ARMOR_LIGHT' AND item_rarity IS 'COMMON' AND item_min_level IS 1") as armor_data:
                        chosen_armor_id = await armor_data.fetchall()
                        chosen_armor_id = random.choice(chosen_armor_id)[0]

            # Next, apply their "class" role for the server.

            role_id = h.class_role_ids[self.chosen_class]
            role = get(interaction.guild.roles, id=role_id)
            member_obj = interaction.guild.get_member(self.author.id)

            await member_obj.add_roles(role)

            # Insert their lore into character-lore
            url = "https://learninghubblog.files.wordpress.com/2013/10/blank-2.png"
            async with aiosqlite.connect('data/game.db') as conn:
                query = "INSERT INTO character_lore VALUES('{}', '{}', '{}', '{}')".format(
                    self.author.id, self.name, self.bg, url
                )
                await conn.execute(query)

                # Insert equipment into character_inventory
                await conn.execute(f"INSERT INTO character_inventory VALUES({self.author.id}, {chosen_weapon_id}, 0, \'None\')")
                await conn.execute(f"INSERT INTO character_inventory VALUES({self.author.id}, {chosen_armor_id}, 0, \'None\')")
                await conn.execute(f"INSERT INTO character_inventory VALUES({self.author.id}, {chosen_potion_id}, 0, \'None\')")

                # Add default faction
                await conn.execute(f"INSERT INTO character_faction_stats VALUES({self.author.id}, 1, 0)")
                await conn.commit()

    @discord.ui.button(label='No', style=discord.ButtonStyle.red)
    async def stop(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content=f"Character creation process canceled!", view=None)

    async def interaction_check(self, interaction: discord.Interaction): # Not needed when in an ephemeral message, but still worth running.
        return interaction.user.id == self.author.id