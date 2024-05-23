import discord
from discord.ext import commands
from discord import app_commands
import helper as h
import aiosqlite

class owner_only(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @commands.is_owner()
    async def regenhps(self, ctx):
        async with aiosqlite.connect('data/game.db') as db:
            async with db.execute('SELECT user_id, class_name, constitution FROM Character_Stats INNER JOIN classes ON Character_Stats.class_id = classes.class_id') as cursor:
                async for row in cursor:
                    user_id = row[0]
                    class_name = row[1]
                    con = row[2]
                    print(f"User {user_id} is a {class_name}")
                    await db.execute('UPDATE Character_Stats SET MAXHP = ? WHERE user_id = ?', (h.calc_base_hp(class_name, int(con)), user_id,))
            await db.commit()

        await ctx.send("Fixed the stupid hp thing")
    
    @commands.command()
    @commands.is_owner()
    async def update(self, ctx, cog, new = None):
        if new == None:
            lists = self.bot.extensions
            for item in lists:
                item = item.split('.')
                if item[-1] == cog.lower():
                    pwd = '.'.join(item)
                    break
            try:
                await self.bot.reload_extension(str(pwd))
                await ctx.send(f"Successfully updated `{pwd}` with [0] errors.")
            except UnboundLocalError:
                await ctx.send(f"❗ | Cog `{cog}` not found.")
        else:
            try:
                await self.bot.load_extension(cog)
                await ctx.send(f"Loaded new cog `{cog}`.")
            except ValueError:
                await ctx.send(f"❗ | Invalid path for `{cog}`.")
    
    @commands.command()
    @commands.is_owner()
    async def sync(self, ctx):
        await self.bot.tree.sync(guild=discord.Object(784842140764602398))
        await ctx.send("Commands synchronized.")

    @commands.command()
    @commands.is_owner()
    async def parse(self, ctx, *, message):
        await ctx.send(h.parse_rfp(message))

    @commands.command()
    @commands.is_owner()
    async def say(self, ctx, *, message):
        await ctx.message.delete()
        await ctx.send(message)

# A setup function the every cog has
async def setup(bot):
    await bot.add_cog(owner_only(bot))