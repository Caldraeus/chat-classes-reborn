import helper as h
import discord
import rfplang
import aiosqlite

class PlayerState:
    def __init__(self, player_obj: discord.User, ready = False, current = False):
        self.player_obj = player_obj
        self.ready = ready
        self.current = current
        self.name = player_obj.display_name
        self.char_data = h.get_character(player_obj.id)
        
        # -------------- #
        # Load all stats #
        # -------------- #
        self.ac = 10 + h.gen_score(self.char_data["dexterity"])
        self.hp = int(self.char_data["MAXHP"])
        self.max_hp = int(self.char_data["MAXHP"])

        self.race = self.char_data["race"]
        self.level = self.char_data["level"]

        self.str = self.char_data["strength"]
        self.dex = self.char_data["dexterity"]
        self.con = self.char_data["constitution"]
        self.int = self.char_data["intelligence"]
        self.wis = self.char_data["wisdom"]
        self.cha = self.char_data["charisma"]

        # ----------------------------------- #
        # Load all passive effects from items #
        # ----------------------------------- #
        self.items = h.get_equipped_items(player_obj.id)

        self.passive_effects_self = {}
        for item in self.items:
            self.passive_effects_self = rfplang.parse_psv_rfplang(item[4], 'SELF', self.passive_effects_self)

        self.passive_effects_enemy = {}
        for item in self.items:
            self.passive_effects_self = rfplang.parse_psv_rfplang(item[4], 'ENEMY', self.passive_effects_enemy)

        # ---------------------------------------------------------- #
        # Load all attacks, class skills, spells... etc... oh god... #
        # ---------------------------------------------------------- #



