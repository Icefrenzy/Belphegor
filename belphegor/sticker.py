import discord
from discord.ext import commands
import re
from fuzzywuzzy import process
from . import utils
from .utils import checks
import pymongo

#==================================================================================================================================================

DEFAULT_PREFIX_REGEX = re.compile(r"(?<=\$)\w+")
NO_SPACE_REGEX = re.compile(r"\S+")
NO_WORD_REGEX = re.compile(r"\W+")

#==================================================================================================================================================

class Sticker:
    def __init__(self, bot):
        self.bot = bot
        self.sticker_list = self.bot.db.sticker_list
        self.guild_data = bot.db.guild_data
        self.sticker_regexes = {}
        bot.loop.create_task(self.get_all_prefixes())

    async def get_all_prefixes(self):
        async for data in self.guild_data.find(
            {"sticker_prefix": {"$exists": True}},
            projection={"_id": False, "guild_id": True, "sticker_prefix": True}
        ):
            self.sticker_regexes[data["guild_id"]] = re.compile(fr"(?<={re.escape(data['sticker_prefix'])})\w+")

    async def on_message(self, message):
        if message.author.bot:
            return
        result = self.sticker_regexes.get(getattr(message.guild, "id", None), DEFAULT_PREFIX_REGEX).findall(message.content)
        query = {"name": {"$in": result}}
        if message.guild:
            query["banned_guilds"] = {"$ne": message.guild.id}
        st = await self.sticker_list.find_one(query)
        if st:
            embed = discord.Embed()
            embed.set_image(url=st["url"])
            await message.channel.send(embed=embed)

    @commands.group()
    async def sticker(self, ctx):
        '''
            `>>sticker`
            Base command. Does nothing, but with subcommands can be used to set and view stickers.
        '''
        if ctx.invoked_subcommand is None:
            pass

    @sticker.command()
    async def add(self, ctx, name, url):
        '''
            `>>sticker add <name> <url>`
            Add a sticker.
            Name can't contain spaces.
        '''
        name = NO_WORD_REGEX.sub("", name)
        if url.startswith(("https://", "http://")):
            value = {"name": name, "url": url, "author_id": ctx.author.id}
            before = await self.sticker_list.find_one_and_update({"name": name}, {"$setOnInsert": value}, upsert=True)
            if before is not None:
                await ctx.send("Cannot add already existed sticker.")
            else:
                await ctx.send(f"Sticker {name} added.")
        else:
            await ctx.send("Url should start with http or https.")

    @sticker.command()
    async def edit(self, ctx, name, url):
        '''
            `>>sticker edit <name> <url>`
            Edit a sticker you own.
        '''
        before = await self.sticker_list.find_one_and_update({"name": name, "author_id": ctx.author.id}, {"$set": {"url": url}})
        if before is None:
            await ctx.send(f"Cannot edit sticker.\nEither sticker doesn't exist or you are not the creator of the sticker.")
        else:
            await ctx.send(f"Sticker {name} edited.")

    @sticker.command()
    async def delete(self, ctx, name):
        '''
            `>>sticker delete <name>`
            Delete a sticker you own.
        '''
        result = await self.sticker_list.delete_one({"name": name, "author_id": ctx.author.id})
        if result.deleted_count > 0:
            await ctx.send(f"Sticker {name} deleted.")
        else:
            await ctx.send(f"Cannot delete sticker.\nEither sticker doesn't exist or you are not the creator of the sticker.")

    @sticker.command()
    async def find(self, ctx, name):
        '''
            `>>sticker find <name>`
            Find stickers.
        '''
        sticker_names = await self.sticker_list.distinct("name", {})
        relevant = process.extract(name, sticker_names, limit=10)
        text = "\n".join((f"{r[0]} ({r[1]}%)" for r in relevant if r[1]>50))
        await ctx.send(f"Result:\n```\n{text}\n```")

    @sticker.command()
    @checks.guild_only()
    @checks.manager_only()
    async def ban(self, ctx, name):
        '''
            `>>sticker ban <name>`
            Ban a sticker in current guild.
        '''
        result = await self.sticker_list.update_one({"name": name}, {"$addToSet": {"banned_guilds": ctx.guild.id}})
        if result.matched_count > 0:
            await ctx.confirm()
        else:
            await ctx.deny()

    @sticker.command()
    @checks.guild_only()
    @checks.manager_only()
    async def unban(self, ctx, name):
        '''
            `>>sticker unban <name>`
            Unban a sticker in current guild.
        '''
        result = await self.sticker_list.update_one({"name": name}, {"$pull": {"banned_guilds": ctx.guild.id}})
        if result.matched_count > 0:
            await ctx.confirm()
        else:
            await ctx.deny()

    @sticker.command()
    async def banlist(self, ctx):
        '''
            `>>sticker banlist`
            Display current guild's sticker ban list.
        '''
        banned_stickers = await self.sticker_list.distinct("name", {"banned_guilds": ctx.guild.id})
        if banned_stickers:
            embeds = utils.embed_page_format(
                banned_stickers, 10,
                title="Banned stickers for this server",
                description=lambda i, x: f"`{i+1}.` {x}"
            )
            await ctx.embed_page(embeds)
        else:
            await ctx.send("There's no banned sticker.")

    @sticker.command()
    @checks.guild_only()
    @checks.manager_only()
    async def prefix(self, ctx, new_prefix):
        '''
            `>>sticker prefix <`
        '''
        if new_prefix == "$":
            self.sticker_regexes.pop(guild.id, None)
            await self.guild_data.update_one(
                {"guild_id": guild.id},
                {"$unset": {"sticker_prefix": None}}
            )
            await ctx.confirm()
        elif NO_SPACE_REGEX.fullmatch(new_prefix):
            self.sticker_regexes[guild.id] = re.compile(fr"(?<={re.escape(new_prefix)})\w+")
            await self.guild_data.update_one(
                {"guild_id": guild.id},
                {"$set": {"sticker_prefix": new_prefix}}
            )
            await ctx.confirm()

#==================================================================================================================================================

def setup(bot):
    bot.add_cog(Sticker(bot))
