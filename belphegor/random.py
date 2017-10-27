import discord
from discord.ext import commands
from . import utils
from .utils import checks
import aiohttp
import json
import xmltodict
import random
from bs4 import BeautifulSoup as BS

#==================================================================================================================================================

class RandomBot:
    '''
    Random pictures from various image boards.
    '''

    def __init__(self, bot):
        self.bot = bot
        self.retry = 3

    @commands.group(aliases=["random",])
    @commands.cooldown(rate=1, per=2, type=commands.BucketType.user)
    async def r(self, ctx):
        if ctx.invoked_subcommand is None:
            message = ctx.message
            message.content = ">>help random"
            await self.bot.process_commands(message)

    async def get_image_danbooru(self, tag, *, rating):
        params = {
            "tags":   f"rating:{rating} {tag}",
            "limit":  1,
            "random": "true"
        }
        bytes_ = await utils.fetch(self.bot.session, "https://danbooru.donmai.us/posts.json", params=params)
        pic = json.loads(bytes_)[0]
        title = "Danbooru" if rating=="safe" else "NSFW Danbooru"
        embed = discord.Embed(
            title=title,
            description=utils.discord_escape(pic.get("tag_string", "")),
            url=f"https://danbooru.donmai.us/posts/{pic['id']}",
            colour=discord.Colour.red()
        )
        embed.set_image(url=f"https://danbooru.donmai.us{pic['file_url']}")
        return embed

    async def get_image_konachan(self, tags, *, rating, page=1):
        params = {
            "tags":   f"rating:{rating} order:random {tags}",
            "limit":  1,
            "page":   page
        }
        domain = "net" if rating=="safe" else "com"
        bytes_ = await utils.fetch(self.bot.session, f"http://konachan.{domain}/post.json", params=params)
        pic = json.loads(bytes_)[0]
        title = "Konachan" if rating=="safe" else "NSFW Konachan"
        embed = discord.Embed(
            title=title,
            description=utils.discord_escape(pic.get("tags", "")),
            url=f"http://konachan.{domain}/post/show/{pic['id']}",
            colour=discord.Colour.red()
        )
        embed.set_image(url=f"http:{pic['sample_url']}")
        return embed

    async def get_image_safebooru(self, tags, *, page=1):
        params = {
            "page":   "dapi",
            "s":      "post",
            "q":      "index",
            "tags":   tags,
            "limit":  100,
            "pid":   page
        }
        bytes_ = await utils.fetch(self.bot.session, "https://safebooru.org/index.php", params=params)
        data = xmltodict.parse(bytes_.decode("utf-8"))
        pic = random.choice(data['posts']['post'])
        embed = discord.Embed(
            title="Safebooru",
            description=utils.discord_escape(pic.get("@tags", "")),
            url=f"https://safebooru.org/index.php?page=post&s=view&id={pic['@id']}",
            colour=discord.Colour.red()
        )
        embed.set_image(url=f"http:{pic['@file_url']}")
        return embed

    async def get_image_yandere(self, tags, *, page=1):
        params = {
            "tags":   tags,
            "limit":  100,
            "page":   page
        }
        bytes_ = await utils.fetch(self.bot.session, "https://yande.re/post.json", params=params)
        pics = json.loads(bytes_)
        pic = random.choice(pics)
        if pic["rating"] != "s":
            raise Exception("nsfw img")
        embed = discord.Embed(
            title="Yandere",
            description=utils.discord_escape(pic.get("tag", "")),
            url=f"https://yande.re/post/show/{pic['id']}",
            colour=discord.Colour.red()
        )
        embed.set_image(url=pic['sample_url'])
        return embed

    async def get_image_sancom(self, tags):
        params = {
            "tags":   f"rating:e order:random {tags}",
            "commit": "Search"
        }
        bytes_ = await utils.fetch(self.bot.session, "https://chan.sankakucomplex.com/", params=params)
        data = BS(bytes_.decode("utf-8"), "lxml")
        items = tuple(
            data.find_all(
                lambda x:
                    getattr(x, "name", None)=="span"
                    and x.get("class", None)==["thumb", "blacklisted"]
                    and x.parent.get("class", None)!=["popular-preview-post"]
            )
        )
        item = random.choice(items)
        a = item.find("a")
        post_url = f"https://chan.sankakucomplex.com{a['href']}"
        bytes_ = await utils.fetch(self.bot.session, post_url)
        post_data = BS(bytes_.decode("utf-8"), "lxml")
        img_link = post_data.find("a", id="highres")
        relevant = post_data.find("ul", id="tag-sidebar")
        pic_tags = " ".join([t.find("a").text.strip().replace(" ", r"\_") for t in relevant.find_all(True, recursive=False)])
        embed = discord.Embed(
            title="Sankaku Complex",
            description=pic_tags,
            url=post_url,
            colour=discord.Colour.red()
        )
        embed.set_image(url=f"https:{img_link['href']}")
        return embed

    async def retry_wrap(self, ctx, func, *args, **kwargs):
        retries = self.retry
        while retries > 0:
            try:
                embed = await func(*args, **kwargs)
                return await ctx.send(embed=embed)
            except IndexError:
                return await ctx.send("No result found.")
            except:
                retries -= 1
        await ctx.send("Query failed. Please try again.")

    @r.command(aliases=["d",])
    async def danbooru(self, ctx, tag=""):
        async with ctx.typing():
            await self.retry_wrap(ctx, self.get_image_danbooru, tag, rating="safe")

    @r.command(aliases=["dh"])
    @checks.nsfw()
    async def danbooru_h(self, ctx, tag=""):
        async with ctx.typing():
            await self.retry_wrap(ctx, self.get_image_danbooru, tag, rating="explicit")

    @r.command(aliases=["k",])
    async def konachan(self, ctx, *, tags=""):
        async with ctx.typing():
            await self.retry_wrap(ctx, self.get_image_konachan, tags, rating="safe")

    @r.command(aliases=["kh",])
    async def konachan_h(self, ctx, *, tags=""):
        async with ctx.typing():
            await self.retry_wrap(ctx, self.get_image_konachan, tags, rating="explicit")

    @r.command(aliases=["s",])
    async def safebooru(self, ctx, *, tags=""):
        async with ctx.typing():
            await self.retry_wrap(ctx, self.get_image_safebooru, tags)

    @r.command(aliases=["y",])
    async def yandere(self, ctx, *, tags=""):
        async with ctx.typing():
            await self.retry_wrap(ctx, self.get_image_yandere, tags)

    @r.command(aliases=["sc",])
    @checks.nsfw()
    async def sancom(self, ctx, *, tags=""):
        async with ctx.typing():
            await self.retry_wrap(ctx, self.get_image_sancom, tags)

    @r.command()
    @checks.owner_only()
    async def setretry(self, ctx, number:int):
        if number <= 0:
            await ctx.send("Number must be positive.")
        elif number > 10:
            await ctx.send("Sorry, can't retry that many times.")
        else:
            self.retry = number
            await ctx.send(f"Number of retries has been set to {number}.")

#==================================================================================================================================================

def setup(bot):
    bot.add_cog(RandomBot(bot))