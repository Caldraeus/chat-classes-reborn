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
        await ctx.send("Syncing commands to the specific guild...")
        await self.bot.tree.sync(guild=discord.Object(id=741447688079540224))  # Ensure to use `id=` for clarity
        await ctx.send("Commands synchronized locally. Run ;globalsync for full tree sync.")

    @commands.command()
    @commands.is_owner()
    async def globalsync(self, ctx):
        await ctx.send("Syncing...")
        await self.bot.tree.sync()
        await ctx.send("Commands sync'd globally. This will take some time to be visible.")
        

    @commands.command()
    @commands.is_owner()
    async def say(self, ctx, *, message):
        await ctx.message.delete()
        await ctx.send(message)

    @commands.command()
    @commands.guild_only()
    @commands.is_owner()
    async def fquest(self, ctx, target: discord.User = None):
        if target: # message, bot, uid=None, override=False
            await self.bot.quest_manager.fetch_random_quest(ctx.message, target)
        else:
            await ctx.send("Fetching a quest.")
            await self.bot.quest_manager.fetch_random_quest(ctx.message)

    @commands.command()
    @commands.guild_only()
    @commands.is_owner()
    async def give_gold(self, ctx, target: discord.User = None, amount: int = 0):
        await h.add_gold(target.id, amount)
        await ctx.send(f"Added {amount} gold to {target.display_name}.")

    @commands.command()
    @commands.is_owner()
    async def reset_ap(self, ctx, user: discord.Member):
        self.bot.user_aps[user.id] = 20
        await ctx.send("✅ Set user's AP back to 20.")

    @commands.command(name="change_class")
    @commands.is_owner()
    async def change_class(self, ctx, user: discord.Member, class_name: str):
        try:
            await h.alter_class(user, class_name)
            await ctx.send(f"✅ Class for {user.display_name} has been changed to {class_name}.")
        except ValueError as ve:
            await ctx.send(str(ve))
        except Exception as e:
            await ctx.send(f"❌ Failed to change class: {e}")

    @commands.command()
    @commands.is_owner()
    async def status(self, ctx, target: discord.User, effect, amount: int):
        cog = self.bot.get_cog("statuses")
        await cog.apply_status_effect(target.id, effect, stacks=amount)
        await ctx.send(f"Applied {amount} stacks of {effect} to user.")



# A setup function the every cog has
async def setup(bot):
    await bot.add_cog(owner_only(bot))