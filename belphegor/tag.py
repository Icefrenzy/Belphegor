import discord
from discord.ext import commands
from fuzzywuzzy import process
from . import utils
from .utils import checks

#==================================================================================================================================================

class Tag:
    def __init__(self, bot):
        self.bot = bot
        self.tag_list = bot.db.tag_list

    async def get_tag(self, name, guild):
        tag = await self.tag_list.find_one({"guild_id": guild.id, "name": name})
        if tag:
            alias_of = tag.get("alias_of", None)
            if alias_of:
                tag = await self.tag_list.find_one({"guild_id": guild.id, "name": alias_of})
        return tag

    @commands.group(name="tag", invoke_without_command=True)
    @checks.guild_only()
    async def tag_cmd(self, ctx, *, name):
        '''
            `>>tag <name>`
            Display a tag.
        '''
        tag = await self.get_tag(name, ctx.guild)
        if tag is None:
            await ctx.send(f"Cannot find tag {name} in database.")
        else:
            await ctx.send(tag["content"])

    @tag_cmd.command()
    @checks.guild_only()
    async def create(self, ctx, name, *, content):
        '''
            `>>tag create <name> <content>`
            Create a tag.
            If name contains spaces, it must be enclosed in double quotes.
        '''
        value = {"guild_id": ctx.guild.id, "name": name.strip(), "content": content, "author_id": ctx.author.id}
        before = await self.tag_list.find_one_and_update({"guild_id": ctx.guild.id, "name": name.strip()}, {"$setOnInsert": value}, upsert=True)
        if before:
            await ctx.send(f"Cannot create already existed tag.")
        else:
            await ctx.send(f"Tag {name} created.")

    @tag_cmd.command()
    @checks.guild_only()
    async def edit(self, ctx, name, *, content):
        '''
            `>>tag edit <name> <content>`
            Edit a tag you own.
            If name contains spaces, it must be enclosed in double quotes.
        '''
        before = await self.tag_list.find_one_and_update(
            {"guild_id": ctx.guild.id, "name": name.strip(), "author_id": ctx.author.id, "content": {"$exists": True}},
            {"$set": {"content": content}}
        )
        if before is None:
            await ctx.send(f"Cannot edit tag.\nEither tag doesn't exist, tag is an alias or you are not the creator of the tag.")
        else:
            await ctx.send(f"Tag {name} edited.")

    @tag_cmd.command()
    @checks.guild_only()
    async def alias(self, ctx, name, *, alias_of):
        '''
            `>>tag alias <alias> <name>`
            Create an alias for a tag.
            If alias contains spaces, it must be enclosed in double quotes.
        '''
        base_tag = await self.get_tag(alias_of, ctx.guild)
        if base_tag:
            alias_of = base_tag["name"]
        else:
            return await ctx.send(f"Tag {alias_of} doesn't exist.")
        value = {"guild_id": ctx.guild.id, "name": name, "alias_of": alias_of, "author_id": ctx.author.id}
        before = await self.tag_list.find_one_and_update({"guild_id": ctx.guild.id, "name": name}, {"$setOnInsert": value}, upsert=True)
        if before:
            await ctx.send(f"Cannot create already existed tag.")
        else:
            await self.tag_list.update_one({"guild_id": ctx.guild.id, "name": alias_of, "aliases": {"$nin": [name]}}, {"$push": {"aliases": name}})
            await ctx.send(f"Tag alias {name} for {alias_of} created.")

    @tag_cmd.command()
    @checks.guild_only()
    async def delete(self, ctx, *, name):
        '''
            `>>tag delete <name>`
            Delete a tag you own.
            Server managers can still delete other people' tags tho.
        '''
        if not ctx.channel.permissions_for(ctx.author).manage_guild:
            q = {"author_id": ctx.author.id}
        else:
            q = {}
        q.update({"guild_id": ctx.guild.id, "name": name})
        before = await self.tag_list.find_one_and_delete(q)
        if before:
            aliases = before.get("aliases")
            if aliases:
                await self.tag_list.delete_many({"guild_id": ctx.guild.id, "name": {"$in": aliases}})
                await ctx.send(f"Tag {name} and its aliases deleted.")
            else:
                await ctx.send(f"Tag {name} deleted.")
        else:
            await ctx.send(f"Cannot delete tag.\nEither tag doesn't exist or you are not the creator of the tag.")

    @tag_cmd.command()
    @checks.guild_only()
    async def find(self, ctx, *, name):
        '''
            `>>tag find <name>`
            Find tags.
        '''
        tag_names = await self.tag_list.distinct("name", {"guild_id": ctx.guild.id})
        relevant = process.extract(name, tag_names, limit=10)
        text = "\n".join((f"{r[0]} ({r[1]}%)" for r in relevant if r[1]>50))
        await ctx.send(f"Result:\n```\n{text}\n```")

    @tag_cmd.command(name="list")
    @checks.guild_only()
    async def cmd_tag_list(self, ctx):
        '''
            `>>tag list`
            Display current server's all tags.
        '''
        tags = await self.tag_list.distinct("name", {"guild_id": ctx.guild.id})
        embeds = utils.embed_page_format(
            tags, 20,
            title=f"All ({len(tags)}) tags for this server",
            description=lambda i, x: f"{i+1}. {x}"
        )
        if embeds:
            await ctx.embed_page(embeds)
        else:
            await ctx.send("This server has no tag.")

#==================================================================================================================================================

def setup(bot):
    bot.add_cog(Tag(bot))
