import discord
from discord.ext import commands
from . import utils
from .utils import checks, data_type
from io import StringIO
import traceback
from contextlib import redirect_stdout
import importlib
from bs4 import BeautifulSoup as BS
import json
import os
from shutil import copyfile
from distutils.dir_util import copy_tree
import subprocess
import copy
import sys
import textwrap

#==================================================================================================================================================

class Admin:
    '''
        I should just call it OwnerOnlyCog but errr....
    '''

    def __init__(self, bot):
        self.bot = bot
        self.belphegor_config = bot.db.belphegor_config

    async def reload_extension(self, ctx, extension):
        try:
            self.bot.unload_extension(extension)
            self.bot.load_extension(extension)
            print(f"Reloaded {extension}")
            await ctx.confirm()
        except:
            print(f"Failed reloading {extension}:\n{traceback.format_exc()}")
            await ctx.deny()

    async def reload_all_extensions(self, ctx):
        for extension in tuple(self.bot.extensions.keys()):
            self.bot.unload_extension(extension)
        check = True
        for extension in self.bot.initial_extensions:
            try:
                self.bot.load_extension(extension)
                print(f"Reloaded {extension}")
            except Exception as e:
                print(f"Failed reloading {extension}:\n{traceback.format_exc()}")
                check = False
        if check:
            await ctx.confirm()
        else:
            await ctx.deny()

    @commands.command(hidden=True)
    @checks.owner_only()
    async def reload(self, ctx, extension=""):
        if extension:
            await self.reload_extension(ctx, f"belphegor.{extension}")
        else:
            await self.reload_all_extensions(ctx)

    @commands.command(hidden=True)
    @checks.owner_only()
    async def unload(self, ctx, extension):
        e = f"belphegor.{extension}"
        if e in self.bot.extensions:
            self.bot.unload_extension(e)
            print(f"Unloaded {e}")
            await ctx.confirm()
        else:
            print(f"Extension {e} doesn't exist.")
            await ctx.deny()

    @commands.command(hidden=True)
    @checks.owner_only()
    async def reimport(self, ctx, module_name):
        module = sys.modules.get(f"belphegor.{module_name}")
        try:
            importlib.reload(module)
        except:
            traceback.print_exc()
            await ctx.deny()
        else:
            print(f"Reimported belphegor.{module_name}")
            await ctx.confirm()

    @commands.command(hidden=True)
    @checks.owner_only()
    async def status(self, ctx, *, stuff):
        data = stuff.partition(" ")
        await self.bot.change_presence(activity=discord.Activity(type=getattr(discord.ActivityType, data[0]), name=data[2]))

    @commands.command(hidden=True)
    @checks.owner_only()
    async def restart(self, ctx):
        self.bot.restart_flag = True
        await self.bot.logout()

    @commands.command(hidden=True)
    @checks.owner_only()
    async def logout(self, ctx):
        cog = self.bot.get_cog("Statistics")
        if cog:
            msg = await ctx.send("Updating stats...")
            await cog.update_all()
            await msg.edit(content="Done.")
        await self.bot.logout()

    @commands.command(name="eval", hidden=True)
    @checks.owner_only()
    async def _eval(self, ctx, *, data: str):
        data = utils.clean_codeblock(data)
        code = f"async def func():\n{textwrap.indent(data, '    ')}"
        env = {
            "bot": self.bot,
            "ctx": ctx,
            "discord": discord,
            "commands": commands,
            "utils": utils
        }
        try:
            exec(code, env)
        except Exception as e:
            return await ctx.send(f"```py\n{e}\n```")
        stdout = StringIO()
        func = env["func"]
        try:
            with redirect_stdout(stdout):
                await func()
        except:
            add_text = f"\n{traceback.format_exc()}"
        else:
            add_text = ""
        finally:
            value = stdout.getvalue()
            if value or add_text:
                await ctx.send(f'```\n{value}{add_text}\n```')

    @commands.command(hidden=True)
    @checks.owner_only()
    async def block(self, ctx, user: discord.User):
        self.bot.blocked_user_ids.add(user.id)
        result = await self.belphegor_config.update_one({"category": "block"}, {"$addToSet": {"blocked_user_ids": user.id}})
        if result.modified_count > 0:
            await ctx.send(f"{user} has been blocked.")
        else:
            await ctx.send(f"{user} is already blocked.")

    @commands.command(hidden=True)
    @checks.owner_only()
    async def unblock(self, ctx, user: discord.User):
        self.bot.blocked_user_ids.discard(user.id)
        result = await self.belphegor_config.update_one({"category": "block"}, {"$pull": {"blocked_user_ids": user.id}})
        if result.modified_count > 0:
            await ctx.send(f"{user} has been unblocked.")
        else:
            await ctx.send(f"{user} is not blocked.")

    @commands.command(hidden=True)
    @checks.owner_only()
    async def hackblock(self, ctx, user_id: int):
        self.bot.blocked_user_ids.add(user_id)
        result = await self.belphegor_config.update_one({"category": "block"}, {"$addToSet": {"blocked_user_ids": user_id}})
        if result.modified_count > 0:
            await ctx.confirm()
        else:
            await ctx.deny()

    @commands.command(hidden=True)
    @checks.owner_only()
    async def mongoitem(self, ctx, col, *, query="{}"):
        data = await self.bot.db[col].find_one(eval(query))
        if data:
            data.pop("_id")
            await ctx.send(file=discord.File(json.dumps(data, indent=4, ensure_ascii=False).encode("utf-8"), filename="data.json"))
        else:
            await ctx.send("Nothing found.")

    @commands.command(hidden=True, aliases=["sudo"])
    @checks.owner_only()
    async def force(self, ctx, *, cmd):
        msg = copy.copy(ctx.message)
        msg.content = f"{ctx.me.mention} {cmd}"
        new_ctx = await self.bot.get_context(msg, cls=data_type.BelphegorContext)
        await new_ctx.reinvoke()

    @commands.command(hidden=True, aliases=["impersonate"])
    @checks.owner_only()
    async def runas(self, ctx, member: discord.Member, *, cmd):
        msg = copy.copy(ctx.message)
        msg.content = f"{ctx.me.mention} {cmd}"
        msg.author = member
        await self.bot.process_commands(msg)

    @commands.command(hidden=True)
    @checks.owner_only()
    async def changeavatar(self, ctx, *, img_url):
        bytes_ = await self.bot.fetch(img_url)
        await ctx.bot.user.edit(avatar=bytes_)
        await ctx.confirm()

    @commands.command(hidden=True)
    @checks.owner_only()
    async def prettify(self, ctx, url, *, params="None"):
        try:
            bytes_ = await self.bot.fetch(url, params=eval(params))
            data = BS(bytes_.decode("utf-8"), "lxml")
        except Exception as e:
            print(e)
            await ctx.deny()
        else:
            await ctx.send(file=discord.File(data.prettify().encode("utf-8"), filename="data.html"))

#==================================================================================================================================================

def setup(bot):
    bot.add_cog(Admin(bot))
