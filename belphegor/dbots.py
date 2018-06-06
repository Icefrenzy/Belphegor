import discord
from discord.ext import commands
from . import utils
from .utils import token
import json

#==================================================================================================================================================

class DBots:
    def __init__(self, bot):
        self.bot = bot
        self.base_url = f"https://bots.discord.pw/api/bots/{bot.user.id}/stats"
        self.headers = {
            "User-Agent": "Belphegor",
            "Authorization": token.DBOTS_TOKEN,
            "content-type": "application/json"
        }

    async def update(self):
        payload = {"server_count": len(self.bot.guilds)}
        data = json.dumps(payload)
        async with self.bot.session.post(self.base_url, headers=self.headers, data=data) as resp:
            pass

    async def on_guild_join(self, guild):
        await self.update()

    async def on_guild_remove(self, guild):
        await self.update()

    async def on_ready(self):
        await self.update()

#==================================================================================================================================================

def setup(bot):
    bot.add_cog(DBots(bot))