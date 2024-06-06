import aiosqlite
import discord
import random
from discord.ext import commands
import hashlib
import math

my_guild = 741447688079540224

body_parts = ['bones', 'hair', 'fingernail', 'thumb', 'middle finger', 'big toe', 'knees', 'kneecap', 'bum', 'cheek', 'bumcheek', 'leg hair', 'skeleton', 'ligaments', 'muscles', 'tendons', 'teeth', 'mouth', 'tongue', 'larynx', 'esophagus', 'stomach', 'small intestine', 'large intestine', 'liver', 'gallbladder', 'mesentery', 'pancreas', 'anus', 'nasal cavity', 'pharynx', 'larynx', 'trachea', 'lungs', 'diaphragm', 'groin', 'kidneys', 'heart', 'spleen', 'thymus', 'brain', 'cerebellum', 'spine', 'eye', 'ear', 'arm', 'leg', 'chest', 'neck', 'toe', 'finger']

# conn = sqlite3.connect('data/game.db')
# class_data = conn.execute("SELECT * FROM classes;")
# class_data = class_data.fetchall()
# conn.close()

class APError(Exception):
    def __init__(self, message="Not enough Action Points (AP) to perform this action."):
        self.message = message
        super().__init__(self.message)

class UserNonexistentError(Exception):
    def __init__(self, message="User does not currently exist."):
        self.message = message
        super().__init__(self.message)
    
async def alter_ap(bot, user_id, base_ap_cost):
    """
    Alters the user's AP by deducting the action cost and raises an error if the user cannot afford the cost.

    bot: The instance of the bot accessing this function.
    user_id (str): The ID of the user whose AP is being modified.
    action_cost (int): The AP cost of the action being performed.
    """
   # Calculate the actual AP cost including any modifications from status effects
    actual_ap_cost = await calculate_ap_cost(bot, user_id, base_ap_cost)

    # Ensure the user is initialized in the AP dictionary
    if user_id not in bot.user_aps:
        bot.user_aps[user_id] = 20  # Initialize with default AP if not previously set

    # Check if the user can afford the action
    if bot.user_aps[user_id] >= actual_ap_cost:
        bot.user_aps[user_id] -= actual_ap_cost  # Deduct the actual AP cost
    else:
        raise APError(f"You need at least {actual_ap_cost} AP to perform this action, but you only have {bot.user_aps[user_id]} AP.")
    
async def calculate_ap_cost(bot, user_id, base_ap_cost):
    """
    Calculates the completed Action Point (AP) cost for a given action.

    :param bot: The bot object
    :param user_id: The user ID to calculate the AP for.
    :param base_ap_cost: The base cost of the action.
    """
    # Check if user exists in user_aps, if not and exists in DB, initialize with 20 AP
    if user_id not in bot.user_aps:
        # This check can be expanded to verify user existence if necessary
        bot.user_aps[user_id] = 20  # Default AP if user exists in the DB

    # Apply status effects to modify the base AP cost
    current_ap_effects = bot.user_effects.get(user_id, [])
    for effect in current_ap_effects:
        pass # TODO: Implement this later.

    return max(0, base_ap_cost)  # Ensure AP cost doesn't drop below 1


async def crit_handler(bot, attacker_usr, defender_usr, channel, boost=0) -> bool:
    """
    Evaluates and handles critical hit chances based on user roles, locations, and status effects.

    bot: The instance of the bot accessing this function.
    attacker_usr (discord.Member): The user performing the attack.
    defender_usr (discord.Member): The user defending against the attack.
    channel (discord.Channel): The channel where the attack takes place.
    boost (int): Initial modification to critical chance (default 0).
    """
    crit_thresh = 1  # Base threshold for a critical hit
    crit_max = 20  # Maximum range for critical hit roll

    crit_thresh += boost  # Apply any initial boost to the critical threshold

    # Calculate the final crit chance
    crit_result = random.randint(1, crit_max) <= crit_thresh

    return crit_result

async def alter_class(user: discord.Member, new_class_name: str):
    """
    Changes the class of a specified user to a new class by name.

    :param user: discord.Member - The user whose class is to be changed.
    :param new_class_name: str - The name of the new class to assign to the user.
    """
    async with aiosqlite.connect('data/main.db') as db:
        # Fetch the class_id corresponding to the class name
        cursor = await db.execute("""
            SELECT class_id FROM classes WHERE class_name = ?;
        """, (new_class_name,))
        class_row = await cursor.fetchone()

        if class_row:
            new_class_id = class_row[0]
            # Update the user's class_id in the users table
            await db.execute("""
                UPDATE users SET class_id = ? WHERE user_id = ?;
            """, (new_class_id, user.id))
            await db.commit()
        else:
            raise ValueError(f"No class found with the name {new_class_name}")

async def give_item(user_id, item_id, amount=1):
    """
    Gives a specified amount of an item to a user.

    :param user_id: ID of the user to give the item to.
    :param item_id: ID of the item to give.
    :param amount: Amount of the item to give. Default is 1.
    """
    if not await user_exists(user_id):
        # Exit if user does not exist.
        return
    async with aiosqlite.connect('data/main.db') as conn:
        cursor = await conn.execute("""
            SELECT amount FROM user_inventory WHERE user_id = ? AND item_id = ?
        """, (user_id, item_id))
        existing_item = await cursor.fetchone()

        if existing_item:
            # If the user already has the item, update the amount
            await conn.execute("""
                UPDATE user_inventory SET amount = amount + ? WHERE user_id = ? AND item_id = ?
            """, (amount, user_id, item_id))
        else:
            # If the user does not have the item, insert a new row
            await conn.execute("""
                INSERT INTO user_inventory (user_id, item_id, amount) VALUES (?, ?, ?)
            """, (user_id, item_id, amount))

        await conn.commit()

async def remove_item(user_id, item_id, amount=1):
    """
    Removes a specified amount of an item from a user.

    :param user_id: ID of the user to remove the item from.
    :param item_id: ID of the item to remove.
    :param amount: Amount of the item to remove. Default is 1.
    """
    if not await user_exists(user_id):
        # Exit if user does not exist.
        return
    async with aiosqlite.connect('data/main.db') as conn:
        cursor = await conn.execute("""
            SELECT amount FROM user_inventory WHERE user_id = ? AND item_id = ?
        """, (user_id, item_id))
        existing_item = await cursor.fetchone()

        if existing_item:
            new_amount = existing_item[0] - amount
            if new_amount > 0:
                # If the new amount is greater than 0, update the amount
                await conn.execute("""
                    UPDATE user_inventory SET amount = ? WHERE user_id = ? AND item_id = ?
                """, (new_amount, user_id, item_id))
            else:
                # If the new amount is 0 or less, delete the item from the inventory
                await conn.execute("""
                    DELETE FROM user_inventory WHERE user_id = ? AND item_id = ?
                """, (user_id, item_id))

            await conn.commit()


async def channel_check(channel_id) -> bool:
    """
    Check if a channel is disabled.

    :param int channel_id: The channel id. 
    :return bool: Boolean value representing whether or not a channe is blacklisted or not.
    """
    async with aiosqlite.connect('data/main.db') as db:
        cursor = await db.execute("SELECT 1 FROM servers WHERE channel_id = ?", (channel_id,))
        is_disabled = await cursor.fetchone()
        if is_disabled:
            # Optionally send an ephemeral message if the channel is disabled
            return False
        else:
            return True
        
def ordinal(n) -> str:
    """
    Return the ordinal number of a given integer, as a string.
    
    :param n: The number to generate a suffix for.
    :return str: The ordinal suffix for the given number n.
    """
    if 10 <= n % 100 <= 20:
        suffix = 'th'
    else:
        suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')
    return f"{n}{suffix}"

async def get_coolness(user_id):
    """
    Return the coolness of a given user

    :param user_id: The user's id
    :return: Their coolness
    """
    async with aiosqlite.connect('data/main.db') as con:
        async with con.execute("SELECT coolness FROM users WHERE user_id = ?", (user_id,)) as cursor:
            result = await cursor.fetchone()
    return result[0] if result else 0
        
async def grant_achievement(channel, user, achievement_id):
    """
    Grant an achievement.

    :param channel: Discord channel to send the notification to.
    :param user_id: The user you're granting an achievement to.
    :param achievement_id: The achievement ID.
    """
    async with aiosqlite.connect('data/main.db') as db:
        # Check if user already has this achievement
        cursor = await db.execute("SELECT 1 FROM user_achievements WHERE user_id = ? AND achievement_id = ?", (user.id, achievement_id))
        if await cursor.fetchone():
            return  # User already has this achievement, no need to grant it again

        # Fetch how many have this achievement before adding the new one
        cursor = await db.execute("SELECT COUNT(*) FROM user_achievements WHERE achievement_id = ?", (achievement_id,))
        count_before = (await cursor.fetchone())[0]

        # Insert the achievement for the user
        await db.execute("INSERT INTO user_achievements (user_id, achievement_id) VALUES (?, ?)", (user.id, achievement_id))

        # Fetch achievement details
        cursor = await db.execute("""
            SELECT name, description, img_url, unlocks, value 
            FROM achievements 
            WHERE achievement_id = ?
        """, (achievement_id,))
        achievement = await cursor.fetchone()

        if achievement:
            name, description, img_url, unlocks, coolness_value = achievement

            # Update coolness points
            await db.execute("UPDATE users SET coolness = coolness + ? WHERE user_id = ?", (coolness_value, user.id))

            # User is the nth person to get this achievement
            nth_person = count_before + 1

            # Create and send the embed
            embed = discord.Embed(title=f"🎉 Achievement Get! \"{name}\" 🎉", description=f"{description}\n\n**+ {coolness_value}** Coolness", color=discord.Color.gold())
            embed.set_footer(text=f"You are the {ordinal(nth_person)} person to earn this achievement.")
            if img_url:
                embed.set_thumbnail(url=img_url)
            if unlocks:
                # Assuming 'unlocks' is the ID of a class that gets unlocked
                cursor = await db.execute("SELECT class_name FROM classes WHERE class_id = ?", (unlocks,))
                class_name = (await cursor.fetchone())[0]
                embed.add_field(name="Unlocks", value=f"You've unlocked access to the class: {class_name}")

            await channel.send(content=user.mention, embed=embed, delete_after=10)

        await db.commit()

def max_xp(lvl) -> int:
    """
    Math to generate the maximum XP required for a level.

    :param int lvl: The level to calculate experience for.
    :return: Integer representing the maximum xp for the given level.
    """
    return 20 * (lvl ^ 35) + 250 * lvl + 25

async def genrank(uid) -> int:
    """
    Generate the user's rank based on their coolness.

    :param int uid: User's ID
    :return rank: The numerical value of a user's position on the leaderboard.
    """
    async with aiosqlite.connect('data/main.db') as con:
        async with con.execute("SELECT * FROM users ORDER BY coolness DESC;") as lb:
            stuff = await lb.fetchall()
            rank = 1
            for usr in stuff:
                if int(usr[0]) == uid: 
                    break
                else:
                    rank += 1
            
            return rank
        
async def user_exists(user_id) -> bool:
    """
    Check if a user exists in the database.
    
    :param user_id: The user's ID.
    """
    async with aiosqlite.connect('data/main.db') as db:
        cursor = await db.execute("SELECT 1 FROM users WHERE user_id = ?", (user_id,))
        exists = await cursor.fetchone()
    return bool(exists)

def paginate(items, page_size) -> list:
    """
    Paginates a list of items.

    :param list items: The list of items to paginate.
    :param int page_size: The number of items to show on each page.
    :return list: Pages of items created from given page size/list.
    """
    pages = [items[i:i + page_size] for i in range(0, len(items), page_size)]
    return pages

async def genprof(uid, aps, bot):
    """
    Helper function to generate a profile embed.
    :param discord.Member uid: User object for the profile being made.
    :param dict aps: The saved user AP value from self.bot.
    :param discord.Bot bot: The self.bot pointer.
    """
    async with aiosqlite.connect('data/main.db') as conn:
        # Fetch the user's data
        async with conn.execute("""
            SELECT user_id, class_id, exp, gold, coolness, level, quests_completed 
            FROM users 
            WHERE user_id = ?;
        """, (uid.id,)) as user_info:
            user = await user_info.fetchone()
            if user is None:
                return None  # Handle the case where no user info is found

        user_id, class_id, exp, gold, coolness, level, completed_quests = user

        # Fetch the class name from the class_id
        async with conn.execute("SELECT class_name FROM classes WHERE class_id = ?;", (class_id,)) as class_info:
            class_result = await class_info.fetchone()
            class_name = class_result[0].replace("_", " ").title() if class_result else "Unknown Class"
        
        rgb_color = hash_class_name_to_rgb(class_name)
        color = discord.Color.from_rgb(*rgb_color)

        # Fetch the total number of achievements
        async with conn.execute("SELECT COUNT(*) FROM achievements;") as ach_count:
            total_achievements = (await ach_count.fetchone())[0]

        # Fetch the number of achievements the user has unlocked
        async with conn.execute("SELECT COUNT(*) FROM user_achievements WHERE user_id = ?;", (user_id,)) as user_ach_count:
            user_achievements = (await user_ach_count.fetchone())[0]

    # Calculate max XP
    max_xp_value = max_xp(level) 

    # Build the profile embed
    profile = discord.Embed(title=f"{uid.display_name}'s Profile", colour=color, description="")
    profile.set_thumbnail(url=uid.display_avatar.url)
    profile.set_footer(text=f"Global Coolness Ranking: {await genrank(uid.id)}", icon_url="")
    profile.add_field(name="Class & Level", value=f"{class_name} ║ Level {level}", inline=False)
    profile.add_field(name="Coolness", value=coolness)
    profile.add_field(name="Gold", value=gold)
    profile.add_field(name="Achievements", value=f"{user_achievements} of {total_achievements} Unlocked ({int((user_achievements / total_achievements) * 100)}%)", inline=False)
    profile.add_field(name="Experience", value=f"{exp} / {max_xp_value} ({int((exp / max_xp_value) * 100)}%)", inline=False)
    profile.add_field(name="Completed Quests", value=completed_quests if completed_quests is not None else "N/A", inline=False)
    profile.add_field(name="Action Points", value=aps.get(uid.id, 0), inline=False)

    return profile

def hash_class_name_to_rgb(class_name: str) -> tuple:
    """
    Convert a class name to an RGB color using a hash function.

    :param class_name: The name of the class.
    :return: A tuple representing the RGB color (r,g,b).
    """
    # Create a hash object
    # This converts the text into bytes, with encode.
    # Then, hashlib turns it into a hash.
    # For example, the md5 can be 5d93ceb70e2a49e19a95b8a92989129b
    hash_object = hashlib.md5(class_name.encode())
    
    # Get the hexadecimal hash value
    # The hexdigest() method then gives a hexadecimal representation of this hash.
    # Basically, a 32-character hexadecimal string.
    hex_dig = hash_object.hexdigest()

    # Convert the first 6 characters of the hash to RGB values
    # When you convert a hexadecimal number to a decimal (base 10) number, 
    # you multiply each digit by 16 raised to the power of its position (starting from 0 on the right).
    # We can accomplish this by doing int(x, 16) apparently.

    # This works because, guess what - RGB values are built for Hexadecimal! Each hexidecimal value is one byte (which is 0 - 255)
    # Since the maximum value for a two-digit hexadecimal number is FF (255 in decimal), 
    # the resulting RGB values will always be within the 0-255 range, which is valid for RGB color representation. Pretty cool.
    # This is why red, for example, is also #FF0000 (255/FF 0/00 0/00)
    r = int(hex_dig[0:2], 16)
    g = int(hex_dig[2:4], 16)
    b = int(hex_dig[4:6], 16)

    return (r, g, b)

async def add_coolness(user_id, coolness_amount):
    """
    Adds coolness to the specified user. This function handles its own database connection.

    :param user_id: ID of the user.
    :param coolness_amount: Amount of coolness to add.
    """
    if not await user_exists(user_id):
        # Exit if user does not exist.
        return
    async with aiosqlite.connect('data/main.db') as conn:
        await conn.execute("""
            UPDATE users SET coolness = coolness + ? WHERE user_id = ?;
        """, (coolness_amount, user_id))
        await conn.commit()

async def add_gold(user_id, gold_amount):
    """
    Adds gold to the specified user. This function handles its own database connection.

    :param user_id: ID of the user.
    :param gold_amount: Amount of gold to add.
    """
    if not await user_exists(user_id):
        # Exit if user does not exist.
        return
    async with aiosqlite.connect('data/main.db') as conn:
        await conn.execute("""
            UPDATE users SET gold = gold + ? WHERE user_id = ?;
        """, (gold_amount, user_id))
        await conn.commit()

async def add_xp(user_id, xp_amount):
    """
    Adds experience points to the specified user. This function handles its own database connection.
    It does not accept negative values for XP to ensure that XP can't be inadvertently reduced.

    :param user_id: ID of the user.
    :param xp_amount: Amount of experience points to add, must be non-negative.
    """
    if not await user_exists(user_id):
        # Exit if user does not exist.
        return
    async with aiosqlite.connect('data/main.db') as conn:
        await conn.execute("""
            UPDATE users SET xp = xp + ? WHERE user_id = ?;
        """, (xp_amount, user_id))
        await conn.commit()

async def find_origin(user_class):
    """
    Finds the origin of the given user class by tracing back its lineage to a base class.
    
    :param user_class: The class name to trace back.
    :return: A string representing the path from the origin class to the given class.
    """
    async with aiosqlite.connect('data/main.db') as conn:
        # Fetch class names and their previous class IDs
        async with conn.execute("SELECT class_name, class_id, previous_class_id FROM classes") as cursor:
            clss = await cursor.fetchall()

    # Create dictionaries for quick lookup
    id_to_name = {item[1]: item[0] for item in clss}
    name_to_previous_id = {item[0]: item[2] for item in clss}

    path = [user_class.title()]
    current_id = name_to_previous_id.get(user_class.title())

    # Trace back the lineage using previous class IDs
    iterations = 0
    while current_id and iterations < 10:
        iterations += 1
        previous_class_name = id_to_name.get(current_id)
        if previous_class_name:
            path.append(previous_class_name)
            current_id = name_to_previous_id.get(previous_class_name)
        else:
            break

    if iterations >= 10:
        path.append("Unknown")  # Failsafe to handle potential circular references / excessive depth

    path.reverse()
    return ' ➔ '.join(path)

class QuestManager:
    def __init__(self, db_path, bot):
        """
        Initializes the QuestManager with the database path.
        
        :param db_path: Path to the SQLite database file.
        """
        self.db_path = db_path
        self.bot = bot

    async def fetch_random_quest(self, mss: discord.Message, uid=None):
        """
        Attempt to fetch a random quest for the user.

        :param mss: The message triggering the random quest fetch.
        :param uid: Optional user ID to override the message author.
        """
        user_id = str(uid.id) if uid else str(mss.author.id)

        if not await user_exists(user_id):
            # Exit if user does not exist.
            return

        async with aiosqlite.connect(self.db_path) as conn:
            # Check if the user already has an active quest
            cursor = await conn.execute("""
                SELECT 1 FROM user_quest_progress WHERE user_id = ?
            """, (user_id,))
            result = await cursor.fetchone()
            if result is not None:
                return

            # Check the number of completed quests for the user
            cursor = await conn.execute("""
                SELECT quests_completed FROM users WHERE user_id = ?
            """, (user_id,))
            quests_completed = await cursor.fetchone()
            if quests_completed is None or quests_completed[0] is None or quests_completed[0] == 0:
                chosen_quest_id = 1
                cursor = await conn.execute("""
                    SELECT q.quest_name, q.description, q.img_url, r.reward_type, r.reward_value
                    FROM quests q
                    LEFT JOIN rewards r ON q.quest_id = r.quest_id
                    WHERE q.quest_id = 1
                """)
                chosen_quest = await cursor.fetchone()
                if chosen_quest:
                    quest_name, description, img_url, reward_type, reward_value = chosen_quest
            else:
                # Fetch quests that are generally available or specifically available to the user's class
                cursor = await conn.execute("""
                    SELECT q.quest_id, q.quest_name, q.description, q.img_url, r.reward_type, r.reward_value
                    FROM quests q
                    LEFT JOIN quest_eligibility qe ON q.quest_id = qe.quest_id
                    LEFT JOIN users u ON u.class_id = qe.class_id AND u.user_id = ?
                    LEFT JOIN rewards r ON q.quest_id = r.quest_id
                    WHERE q.is_randomly_obtainable = 1 AND (qe.quest_id IS NULL OR u.user_id = ?)
                """, (user_id, user_id))
                eligible_quests = await cursor.fetchall()

                if not eligible_quests:
                    print("Somehow no eligible quests were found.")
                    return

                chosen_quest = random.choice(eligible_quests)
                chosen_quest_id, quest_name, description, img_url, reward_type, reward_value = chosen_quest

            # Determine follow-up quest
            follow_up_cursor = await conn.execute("""
                SELECT quest_name FROM quests WHERE quest_id IN (
                    SELECT quest_id FROM quest_prerequisites WHERE prerequisite_quest_id = ?
                )
            """, (chosen_quest_id,))
            follow_up_quest = await follow_up_cursor.fetchone()
            follow_up_quest_name = follow_up_quest[0] if follow_up_quest else None

            # Initialize quest progress for the chosen quest
            await conn.execute("""
                INSERT INTO user_quest_progress (user_id, objective_id, current_count)
                SELECT ?, objective_id, 0 FROM quest_objectives WHERE quest_id = ?
            """, (user_id, chosen_quest_id))
            await conn.commit()

        # Create and send an embed with quest details
        embed = discord.Embed(
            title=f"✨ New Quest: {quest_name}! ✨",
            colour=discord.Colour.from_rgb(255, 200, 0),
            description=f"{description}\n**Reward**: {reward_value} {reward_type}"
        )
        if img_url:
            embed.set_thumbnail(url=img_url)
        if follow_up_quest_name:  # Only add this field if there is a follow-up quest
            embed.add_field(name="Next Quest", value=follow_up_quest_name, inline=False)
        embed.set_footer(text="Good luck on your quest!")
        await self.bot.get_channel(mss.channel.id).send(content=mss.author.mention, embed=embed, delete_after=10)


    async def get_quest_type(self, user_id) -> str:
        """
        Retrieves the action type of the current active quest for a specified user.

        :param user_id: ID of the user.
        :return str: The action type of the current active quest, or None if no active quest exists.
        """
        async with aiosqlite.connect(self.db_path) as conn:
            # Query to fetch the action type of the active quest based on the user's current quest progress
            cursor = await conn.execute("""
                SELECT qo.action_type
                FROM quest_objectives qo
                JOIN user_quest_progress uqp ON qo.objective_id = uqp.objective_id
                WHERE uqp.user_id = ? AND uqp.current_count < qo.target
                LIMIT 1;
            """, (user_id,))
            
            quest_type = await cursor.fetchone()
            if quest_type:
                return quest_type[0]  # Return the action type of the quest
            
            return None  # Return None if there is no active quest


    async def update_quest_progress(self, user_id, channel_id, increment):
        """
        Updates quest progress based on the action taken by the user.
        
        :param user_id: ID of the user.
        :param channel_id: Channel ID where notifications are sent.
        :param increment: Number to increment progress by.
        """
        async with aiosqlite.connect(self.db_path) as conn:
            # Fetch the active quest for the user
            cursor = await conn.execute("""
                SELECT q.quest_id, o.objective_id, o.target, up.current_count
                FROM user_quest_progress up
                JOIN quest_objectives o ON up.objective_id = o.objective_id
                JOIN quests q ON o.quest_id = q.quest_id
                WHERE up.user_id = ? AND up.current_count < o.target
                LIMIT 1;
            """, (user_id,))

            quest = await cursor.fetchone()
            if quest:
                quest_id, objective_id, target, current_count = quest
                new_count = current_count + increment
                # Update existing quest progress
                await conn.execute("""
                    UPDATE user_quest_progress
                    SET current_count = ?
                    WHERE user_id = ? AND objective_id = ?;
                """, (new_count, user_id, objective_id))

                # Commit changes before checking if the quest is completed
                await conn.commit()

                if new_count >= target:
                    # Complete the quest if the target is met
                    await self.complete_quest(user_id, quest_id, channel_id)


    async def complete_quest(self, user_id, quest_id, channel_id):
        """
        Completes a quest for a user, applies the reward, checks for and initializes a follow-up quest,
        and sends a notification to a specific channel.

        :param user_id: User ID.
        :param quest_id: ID of the quest being completed.
        :param channel_id: Channel ID to send the notification message.
        """
        description, reward_type, reward_value, img_url, follow_up_quest_id, follow_up_description = None, None, None, None, None, None

        # First, open a connection to fetch necessary data
        async with aiosqlite.connect(self.db_path) as conn:
            # Fetch reward details and quest description
            cursor = await conn.execute("""
                SELECT q.description, r.reward_type, r.reward_value, q.img_url
                FROM quests q
                JOIN rewards r ON q.quest_id = r.quest_id
                WHERE q.quest_id = ?;
            """, (quest_id,))
            quest_details = await cursor.fetchone()

            if quest_details:
                description, reward_type, reward_value, img_url = quest_details

            # Fetch the single follow-up quest, if any
            cursor = await conn.execute("""
                SELECT qp.quest_id, q.description FROM quests q
                JOIN quest_prerequisites qp ON qp.quest_id = q.quest_id
                WHERE qp.prerequisite_quest_id = ?;
            """, (quest_id,))
            follow_up_quest = await cursor.fetchone()
            if follow_up_quest:
                follow_up_quest_id, follow_up_description = follow_up_quest

            # Remove the quest from active progress
            await conn.execute("""
                DELETE FROM user_quest_progress WHERE user_id = ?;
            """, (user_id,))
            
            # Increment quests_completed, initializing to 0 if null
            await conn.execute("""
                UPDATE users SET quests_completed = COALESCE(quests_completed, 0) + 1 WHERE user_id = ?;
            """, (user_id,))
            
            await conn.commit()

        # Now handle user rewards outside the database connection
        if reward_type == 'coolness':
            await add_coolness(user_id, reward_value)
        elif reward_type == 'gold':
            await add_gold(user_id, reward_value)
        elif reward_type == 'xp':
            await add_xp(user_id, reward_value)
        elif reward_type == 'item':
            # TODO: Implement this reward value.
            pass
        elif reward_type == 'achievement':
            # TODO: implement this reward value.
            # NOTE: Probably shouldn't reward achievements on `randomly_obtainable` quests.
            pass
        elif reward_type == 'status':
            # TODO: Implement this reward value.
            pass

        # Reopen the connection to handle follow-up quests
        async with aiosqlite.connect(self.db_path) as conn:
            if follow_up_quest_id:
                # Initialize the follow-up quest
                await conn.execute("""
                    INSERT INTO user_quest_progress (user_id, objective_id, current_count)
                    SELECT ?, objective_id, 0 FROM quest_objectives WHERE quest_id = ?;
                """, (user_id, follow_up_quest_id))
                await conn.commit()

        # Send notification
        embed = discord.Embed(
            title="🏆 Quest Completed! 🏆",
            description=f"**{description}**\nCongratulations! You've received {reward_value} {reward_type}.",
            color=discord.Colour.gold()
        )
        if img_url:
            embed.set_thumbnail(url=img_url)
        if follow_up_description:
            embed.add_field(name="Next Quest", value=f"**{follow_up_description}**", inline=False)

        embed.set_footer(text=f"Great job, {self.bot.get_user(user_id).display_name}!")
        await self.bot.get_channel(channel_id).send(embed=embed, delete_after=10)
    
async def webhook_safe_check(channel) -> str:
    """
    Ensures that a valid webhook exists for the given channel. If a webhook does not exist, it creates a new one
    and stores it in the database before returning the webhook URL.

    :param channel (discord.TextChannel): The channel for which to check or create a webhook.
    :return str: The URL of the webhook for the specified channel.
    """
    async with aiosqlite.connect('data/main.db') as conn:
        # Check for existing webhook in the database
        cursor = await conn.execute(
            "SELECT webhook_url FROM webhooks WHERE server_id = ? AND channel_id = ?", 
            (channel.guild.id, channel.id)
        )
        hook = await cursor.fetchone()

        if hook:
            return hook[0]  # Return existing webhook URL

        # No existing webhook, create a new one
        try:
            new_hook = await channel.create_webhook(name=f"Chat Classes {channel.name} Webhook")
            # Store the new webhook in the database
            await conn.execute(
                "INSERT INTO webhooks (server_id, channel_id, webhook_url) VALUES (?, ?, ?)",
                (channel.guild.id, channel.id, new_hook.url)
            )
            await conn.commit()
            return new_hook.url  # Return new webhook URL
        except Exception as e:
            print(f"Failed to create webhook: {e}")
            raise

magnitudeDict={0:'', 1:'Thousand', 2:'Million', 3:'Billion', 4:'Trillion', 5:'Quadrillion', 6:'Quintillion', 7:'Sextillion', 8:'Septillion', 9:'Octillion', 10:'Nonillion', 11:'Decillion'}

def simplify(num) -> str:
    """
    A function to simplify a large number.

    :param int num: The number to return a format string for.
    :return str: The simplified large number.
    """
    num=math.floor(num)
    magnitude=0
    while num>=1000.0:
        magnitude+=1
        num=num/1000.0
    return(f'{math.floor(num*100.0)/100.0} {magnitudeDict[magnitude]}')