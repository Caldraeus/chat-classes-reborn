import sqlite3
import math
import aiosqlite

my_guild = 784842140764602398

class_main_stats = {
    'intelligence':[],
    'charisma':[],
    'strength':[],
    'constitution':[],
    'wisdom':[],
    'dexterity':[],
}

item_types = [
    "WEAPON_MELEE",
    "WEAPON_SHIELD",
    "WEAPON_RANGED",
    "ARMOR_LIGHT",
    "ARMOR_HEAVY",
    "WEAPON_FOCUS",
    "COMPANION"
]

item_types_equippable = [
    "WEAPON_MELEE",
    "WEAPON_SHIELD",
    "WEAPON_RANGED",
    "ARMOR_LIGHT",
    "ARMOR_HEAVY",
    "WEAPON_FOCUS",
    "COMPANION"
]

class_role_ids = {}

class_hp_base = {}

class_ids = {}

conn = sqlite3.connect('data/game.db')
class_data = conn.execute("SELECT * FROM classes;")
class_data = class_data.fetchall()
conn.close()

for class_info in class_data:
    # (1, 895103782273314868, 'Alchemist', 'Alchemists brew potions and create new alchemic inventions to fight', 'Intelligence', 6)
    primary_stat = class_info[4].lower()
    class_main_stats[primary_stat].append(class_info[2])
    class_role_ids[class_info[2]] = class_info[1]
    class_ids[class_info[2]] = class_info[0]
    class_hp_base[class_info[2]] = int(class_info[5])

def get_equipped_items(user_id):
    # Connect to the database
    conn = sqlite3.connect('data/game.db')
    cursor = conn.cursor()
    # Execute a query to fetch the equipped items for the user
    cursor.execute(
        'SELECT i.*, ci.equipped, ci.custom_name '
        'FROM character_inventory ci '
        'JOIN Items i ON ci.item_id = i.item_id '
        'WHERE ci.user_id = ? AND ci.equipped = 1',
        (user_id,)
    )
    # Fetch all the rows returned by the query
    equipped_items = cursor.fetchall()
    # Close the cursor and database connection
    cursor.close()
    conn.close()
    # Return the equipped items
    return equipped_items


def calc_base_hp(p_class, con):
    return int(class_hp_base[p_class] + gen_score(int(con)))

def get_character(user_id):
    # Open a connection to the database
    conn = sqlite3.connect('data/game.db')
    conn.row_factory = sqlite3.Row

    # Create a cursor object
    cur = conn.cursor()

    # Execute a SELECT query to get the character ID associated with the user ID
    cur.execute("SELECT * FROM Character_Stats WHERE user_id = ?", (user_id,))

    # Fetch the result of the query
    row = cur.fetchone()

    # Close the cursor and connection
    cur.close()
    conn.close()

    # Check if the row is not None, indicating that the user has a character
    if row is not None:
        return row
    else:
        character_id = None

    return character_id

def paginate(items, page_size):
    """
    Paginates a list of items.

    :param list items: The list of items to paginate.
    :param int page_size: The number of items to show on each page.
    """
    pages = [items[i:i + page_size] for i in range(0, len(items), page_size)]
    return pages

def xp_lvl(current_level: int) -> int:
    """
    Returns the amount of XP required to level up, based on current level.

    :param int current_level: The current character level.
    """
    
    # The maximum level that can be achieved
    max_level = 20
    
    # The base amount of XP required for level 1
    base_xp = 200
    
    # The growth rate at which the XP required for each level increases, including the XP factor
    growth_rate = 1.23
    
    if current_level >= max_level:
        return 0
    
    xp_needed = base_xp * (growth_rate ** current_level)
    
    return int(xp_needed)

def gen_score(num: int) -> int:
    """
    Generate a D&D 5e ability score modifier.

    :param int num: The number to generate a score for.
    """
    # Subtract 10 from the ability score and then divide the total by 2 (round down).
    return math.floor((num-10)/2)

# Helper functions. Blank right now. Update later

def count_hands(user):
    """
    Returns the amount of free hands a user has. A usr can have up to 9 hands, but no more.

    :param discord.User user: The user object.
    """
    hands = 2

    conn = sqlite3.connect('data/game.db')
    items = conn.execute(f"SELECT character_inventory.item_id, character_inventory.equipped, items.item_name, items.item_type, items.item_basic_rfplang FROM character_inventory INNER JOIN items ON character_inventory.item_id=items.item_id WHERE user_id = {user.id} AND equipped = 1;")
    items = items.fetchall()
    conn.close()

    for item_n in items:
        if "WEAPON" in item_n[3]:
            hands -= int([item for item in item_n[4].split("&&") if "HANDS(" in item][0].strip()[6])

    return hands 

def count_attune_slots(user):
    """
    Returns the amount of free attunement slots a user has. A usr can have up to 3 base default.

    :param discord.User user: The user object.
    """
    return 3