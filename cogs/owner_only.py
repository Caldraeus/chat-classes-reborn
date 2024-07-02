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
    async def force_rollover(self, ctx):
        cog = self.bot.get_cog('rollover')
        await cog.reset_users_ap()
        await cog.reset_user_class_specific()
        self.bot.claimed.clear()
        await ctx.send('✅ | Forced a rollover.')

    @commands.command()
    @commands.guild_only()
    @commands.is_owner()
    async def give_gold(self, ctx, target: discord.User = None, amount: int = 0):
        await h.add_gold(target.id, amount)
        await ctx.send(f"Added {amount} gold to {target.display_name}.")

    @commands.command()
    @commands.guild_only()
    @commands.is_owner()
    async def debug(self, ctx, amount: int = 0):
        cog = self.bot.get_cog('action_core')
        cog.impaled = []
        await ctx.send(f"Debugged.")

    @commands.command()
    @commands.guild_only()
    @commands.is_owner()
    async def give_coolness(self, ctx, target: discord.User = None, amount: int = 0):
        await h.add_coolness(self.bot, target.id, amount)
        await ctx.send(f"Added {amount} coolness to {target.display_name}.")

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

    @commands.command()
    @commands.is_owner()
    async def owner_commands(self, ctx):
        """Lists all owner-only commands and their parameters."""
        commands_list = [
            {"name": "update", "params": "cog, new=None", "description": "Updates or loads a specified cog."},
            {"name": "sync", "params": "", "description": "Syncs commands to the specific guild."},
            {"name": "globalsync", "params": "", "description": "Syncs commands globally."},
            {"name": "say", "params": "message", "description": "Sends a message as the bot."},
            {"name": "fquest", "params": "target: discord.User = None", "description": "Fetches a random quest for a specified user or self."},
            {"name": "force_rollover", "params": "", "description": "Forces a rollover of daily limits."},
            {"name": "give_gold", "params": "target: discord.User, amount: int", "description": "Gives a specified amount of gold to a user."},
            {"name": "debug", "params": "amount: int = 0", "description": "Resets the debug state."},
            {"name": "give_coolness", "params": "target: discord.User, amount: int", "description": "Gives a specified amount of coolness to a user."},
            {"name": "reset_ap", "params": "user: discord.Member", "description": "Resets a user's AP to 20."},
            {"name": "change_class", "params": "user: discord.Member, class_name: str", "description": "Changes the class of a specified user."},
            {"name": "status", "params": "target: discord.User, effect: str, amount: int", "description": "Applies a status effect to a user."},
        ]

        embed = discord.Embed(title="Owner-Only Commands", color=discord.Color.gold())
        for cmd in commands_list:
            embed.add_field(
                name=f";{cmd['name']} {cmd['params']}",
                value=cmd["description"],
                inline=False
            )

        await ctx.send(embed=embed)

# A setup function the every cog has
async def setup(bot):
    await bot.add_cog(owner_only(bot))