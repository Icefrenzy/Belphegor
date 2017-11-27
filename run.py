import discord
from discord.ext import commands
from belphegor import utils
from belphegor.utils import token, config, context
import asyncio
import aiohttp
import psutil
import os
import time
from motor import motor_asyncio

#==================================================================================================================================================

class Belphegor(commands.Bot):
    def __init__(self, **kwargs):
        super().__init__(None, **kwargs)
        self.default_prefix = kwargs.get("default_prefix", (">>",))
        self.guild_prefixes = {}
        self.session = aiohttp.ClientSession(loop=self.loop)
        self.process = psutil.Process(os.getpid())
        self.cpu_count = psutil.cpu_count()
        self.process.cpu_percent(None)
        self.start_time = utils.now_time()
        self.loop.create_task(self.load())
        self.mongo_client = motor_asyncio.AsyncIOMotorClient()
        self.db = self.mongo_client.belphydb

    async def get_prefix(self, message):
        prefixes = {f"<@{self.user.id}> ", f"<@!{self.user.id}> "}
        gp = self.guild_prefixes.get(message.guild.id)
        if gp:
            prefixes.update(gp)
        else:
            prefixes.update(self.default_prefix)
        return prefixes

    async def process_commands(self, message):
        ctx = await self.get_context(message, cls=context.BelphegorContext)
        await self.invoke(ctx)

    async def on_message(self, message):
        if message.author.bot:
            return
        await self.process_commands(message)

    async def on_ready(self):
        print('Logged in as')
        print(self.user.name)
        print(self.user.id)
        print('------')
        await asyncio.sleep(5)
        await self.change_presence(game=discord.Game(name='with Chronos-senpai'))

    def remove_cog(self, name):
        cog = self.get_cog(name)
        try:
            cog.cleanup()
        except:
            pass
        super().remove_cog(name)

    async def close(self):
        await self.session.close()
        await super().close()

    async def load(self):
        await self.wait_until_ready()
        async for guild_data in self.db.guild_data.find({"prefixes": {"$exists": True}}, projection={"_id": -1, "guild_id": 1, "prefixes": 1}):
            if guild_data["prefixes"]:
                self.guild_prefixes[guild_data["guild_id"]] = guild_data["prefixes"]
        blocked_data = await self.db.belphegor_config.find_one({"category": "blocked"}, projection={"_id": -1, "user_ids": 1})
        self.blocked_users = set(blocked_data["user_ids"])
        self.add_check(self.block_or_not)
        for extension in config.all_extensions:
            try:
                self.load_extension(extension)
                print(f"Loaded {extension}")
            except Exception as e:
                print(f"Failed loading {extension}: {e}")
                return await self.logout()
        print("Done")

    async def block_or_not(self, ctx):
        if ctx.author.id in self.blocked_users:
            if ctx.author.id != self.owner_id:
                await ctx.send("You are already blocked.")
                return False
        return True

#==================================================================================================================================================

if __name__ == "__main__":
    belphybot = Belphegor(owner_id=config.OWNER_ID)
    belphybot.run(token.TOKEN)
