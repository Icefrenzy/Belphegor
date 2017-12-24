import discord
from discord.ext import commands
import random
from . import utils, board_game
from .utils import config, checks
from bs4 import BeautifulSoup as BS
import asyncio
import unicodedata
import re
from pymongo import ReturnDocument
import json
from urllib.parse import quote

FANCY_CHARS = {
    "A": "\U0001F1E6", "B": "\U0001F1E7", "C": "\U0001F1E8", "D": "\U0001F1E9", "E": "\U0001F1EA",
    "F": "\U0001F1EB", "G": "\U0001F1EC", "H": "\U0001F1ED", "I": "\U0001F1EE", "J": "\U0001F1EF",
    "K": "\U0001F1F0", "L": "\U0001F1F1", "M": "\U0001F1F2", "N": "\U0001F1F3", "O": "\U0001F1F4",
    "P": "\U0001F1F5", "Q": "\U0001F1F6", "R": "\U0001F1F7", "S": "\U0001F1F8", "T": "\U0001F1F9",
    "U": "\U0001F1FA", "V": "\U0001F1FB", "W": "\U0001F1FC", "X": "\U0001F1FD", "Y": "\U0001F1FE",
    "Z": "\U0001F1FF", "!": "\u2757", "?": "\u2753",
    "0": "\u0030\u20E3", "1": "\u0031\u20E3", "2": "\u0032\u20E3", "3": "\u0033\u20E3", "4": "\u0034\u20E3",
    "5": "\u0035\u20E3", "6": "\u0036\u20E3", "7": "\u0037\u20E3", "8": "\u0038\u20E3", "9": "\u0039\u20E3"
}

GLITCH_TEXT = "¡¢£¤¥¦§¨©ª«¬®¯°±²³´µ¶·¸¹º»¼½¾¿ÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖ×ØÙÚÛÜÝÞßàáâãäåæçèéêëìíîïðñòóôõö÷øùúûüýþÿĀāĂăĄąĆćĈĉĊċČčĎďĐđĒēĔĕĖėĘęĚěĜĝĞğĠġĢģĤĥĦħĨĩĪīĬĭĮįİıĲĳĴĵĶķĸĹĺĻļĽľĿŀŁłŃńŅņŇňŉŊŋŌōŎŏŐőŒœŔŕŖŗŘřŚśŜŝŞşŠšŢţŤťŦŧŨũŪūŬŭŮůŰűŲųŴŵŶŷŸŹźŻżŽž"

GLITCH_UP = tuple("̍	̎	̄	̅	̿	̑	̆	̐	͒	͗͑	̇	̈	̊	͂	̓	̈́	͊	͋	͌̃	̂	̌	͐	̀	́	̋	̏	̒	̓̔	̽	̉	ͣ	ͤ	ͥ	ͦ	ͧ	ͨ	ͩͪ	ͫ	ͬ	ͭ	ͮ	ͯ	̾	͛	͆	̚".split())

GLITCH_MIDDLE = tuple("̕	̛	̀	́	͘	̡	̢	̧	̨	̴̵	̶	͏	͜	͝	͞	͟	͠	͢	̸̷	͡	҉".split())

GLITCH_DOWN = tuple("̖	̗	̘	̙	̜	̝	̞	̟	̠	̤̥	̦	̩	̪	̫	̬	̭	̮	̯	̰̱	̲	̳	̹	̺	̻	̼	ͅ	͇	͈͉	͍	͎	͓	͔	͕	͖	͙	͚	̣".split())

GLITCH_ALL = tuple(i for j in (GLITCH_UP, GLITCH_MIDDLE, GLITCH_DOWN) for i in j)

QUOTES = {
    "win": [
        "I won! Yay!",
        "Hehehe, I'm good at this.",
        "Lalala~"
    ],
    "draw": [
        "It's a tie.",
        "It's a draw.",
        "Again!"
    ],
    "lose": [
        "I-I lost...",
        "I won't lose next time!",
        "Why?"
    ],
    "winstreak": [
        "I'm invincible!",
        "I'm on a roll!",
        "Triple kill! Penta kill!!!",
        "(smug)"
    ],
    "drawstreak": [
        "This kinda... draws out for too long.",
        "Tie again... How many tie in a row did we have?",
        "(staaaareeee~)"
    ],
    "losestreak": [
        "E-eh? Did you cheat or something?",
        "Mwuu... this is frustrating...",
        "Eeeeeek! EEEEEEEKKKKKKK!",
        "(attemp to logout to reset the game)"
    ]
}

#==================================================================================================================================================

class Misc:
    '''
    Stuff that makes no difference if they aren't there.
    '''

    def __init__(self, bot):
        self.bot = bot
        self.jankenpon_record = bot.db.jankenpon_record
        self.google_lock = asyncio.Lock()

    def quote(self, streak):
        if streak.endswith("ddd"):
            return random.choice(QUOTES["drawstreak"] + QUOTES["draw"])
        elif streak.count("w") > 2:
            if streak[-1] == "w":
                return random.choice(QUOTES["winstreak"] + QUOTES["win"])
        elif 0 < streak.count("w") <= 2:
            if streak[-1] == "w":
                return random.choice(QUOTES["win"])
        elif streak.count("l") > 2:
            if streak[-1] == "l":
                return random.choice(QUOTES["losestreak"] + QUOTES["lose"])
        elif 0 < streak.count("l") <= 2:
            if streak[-1] == "l":
                return random.choice(QUOTES["lose"])
        return random.choice(QUOTES["draw"])

    @commands.command(aliases=["jkp",])
    async def jankenpon(self, ctx):
        embed = discord.Embed(description="What will you use? Rock, paper or scissor?")
        message = await ctx.send(embed=embed)
        possible_reactions = ("\u270a", "\u270b", "\u270c", "\u274c")
        for e in possible_reactions:
            await message.add_reaction(e)
        record = await self.jankenpon_record.find_one_and_update(
            {"id": ctx.author.id},
            {"$setOnInsert": {"id": ctx.author.id, "win": 0, "draw": 0, "lose": 0}},
            return_document=ReturnDocument.AFTER,
            upsert=True
        )
        streak = ""
        while True:
            try:
                reaction, user = await self.bot.wait_for(
                    "reaction_add",
                    check=lambda r,u: u.id==ctx.author.id and r.emoji in possible_reactions and r.message.id==message.id,
                    timeout=30
                )
            except:
                embed.description = "\"I'm tir..e...d.....zzzz...........\""
                await message.clear_reactions()
                await message.edit(embed=embed)
                break
            roll = random.randint(0,2)
            value = possible_reactions.index(reaction.emoji)
            if value == 3:
                embed.title = ""
                embed.description = "\"No more jankenpon? Yay!!!\""
                await message.clear_reactions()
                await message.edit(embed=embed)
                break
            else:
                await message.remove_reaction(reaction, user)
                if (value - roll) % 3 == 0:
                    record["draw"] += 1
                    streak = f"{streak}d"
                elif (value - roll) % 3 == 2:
                    record["lose"] += 1
                    if "w" in streak:
                        streak = f"{streak}w"
                    else:
                        streak = "w"
                else:
                    record["win"] += 1
                    if "l" in streak:
                        streak = f"{streak}l"
                    else:
                        streak = "l"
                embed.title = f"I use {possible_reactions[roll]}"
                embed.description = f"*\"{self.quote(streak)}\"*"
                embed.set_footer(text=f"{record['win']}W - {record['draw']}D - {record['lose']}L")
                await message.edit(embed=embed)
        await self.jankenpon_record.update_one(
            {"id": ctx.author.id},
            {"$set": {"win": record["win"], "draw": record["draw"], "lose": record["lose"]}}
        )

    async def on_message(self, message):
        if message.author.bot:
            return
        inp = message.content
        if inp[:3] in ("/o/", "\\o\\"):
            reply = ""
            for index, ch in enumerate(inp):
                current = inp[index:index+3]
                if current == "\\o\\":
                    reply = f"{reply} /o/"
                elif current == "/o/":
                    reply = f"{reply} \\o\\"
                else:
                    pass
            await message.channel.send(reply)
        elif inp == "ping":
            msg = await message.channel.send("pong")
            await msg.edit(content=f"pong (ws: {int(1000*self.bot.latency)}ms, edit: {int(1000*(msg.created_at-message.created_at).total_seconds())}ms)")

    @commands.command()
    async def avatar(self, ctx, *, member:discord.Member=None):
        if not member:
            member = ctx.author
        embed = discord.Embed(title=f"{member.display_name}'s avatar", url=member.avatar_url)
        embed.set_image(url=member.avatar_url_as(static_format="png"))
        await ctx.send(embed=embed)

    @commands.command()
    async def dice(self, ctx, max_side: int, number_of_dices: int):
        if 120 >= max_side > 3 and 0 < number_of_dices <= 100:
            rng = board_game.Dices(max_side, number_of_dices)
            roll_result = rng.roll()
            await ctx.send(
                "```\nRoll result:\n{}\n\nDistribution:\n{}\n```"
                .format(", ".join([str(r) for r in roll_result]), "\n".join(["{} showed up {} times.".format(i, roll_result.count(i)) for i in range(1, max_side+1)]))
            )
        else:
            await ctx.send("Max side must be between 4 and 120 and number of dices must be between 1 and 100")

    @commands.command()
    @commands.cooldown(rate=1, per=5, type=commands.BucketType.user)
    async def stats(self, ctx):
        async with ctx.typing():
            bytes_ = await utils.fetch(
                self.bot.session,
                "https://api.github.com/repos/nguuuquaaa/Belphegor/commits",
                headers={"User-Agent": "nguuuquaaa"}
            )
            commits = json.loads(bytes_)
            desc = "\n".join((f"[`{c['sha'][:7]}`]({c['html_url']}) {c['commit']['message']}" for c in commits[:3]))
            process = self.bot.process
            embed = discord.Embed(description=f"**Lastest changes:**\n{desc}", colour=discord.Colour.blue())
            embed.set_author(name="{}".format(self.bot.user), icon_url=self.bot.user.avatar_url)
            owner = self.bot.get_user(config.OWNER_ID)
            embed.add_field(name="Owner", value=f"{owner.name}#{owner.discriminator}")
            embed.add_field(name="Library", value="[discord.py\\[rewrite\\]](https://github.com/Rapptz/discord.py/tree/rewrite)")
            embed.add_field(name="Created at", value=str(self.bot.user.created_at)[:10])
            embed.add_field(name="Guilds", value=f"{len(self.bot.guilds)} guilds")
            cpu_percentage = process.cpu_percent(None)
            embed.add_field(name="Process", value=f"CPU: {(cpu_percentage/self.bot.cpu_count):.2f}%\nRAM: {(process.memory_info().rss/1024/1024):.2f} MBs")
            now_time = utils.now_time()
            uptime = int((now_time - self.bot.start_time).total_seconds())
            d = uptime // 86400
            h = (uptime % 86400) // 3600
            m = (uptime % 3600) // 60
            s = uptime % 60
            embed.add_field(name="Uptime", value=f"{d}d {h}h{m}m{s}s")
            embed.set_footer(text=utils.format_time(now_time.astimezone()))
            await ctx.send(embed=embed)

    @commands.command()
    async def fancy(self, ctx, *, textin:str):
        textin = textin.upper()
        await ctx.send(" ".join((FANCY_CHARS.get(charin, charin) for charin in textin)))

    @commands.command(aliases=["hello",])
    async def hi(self, ctx):
        await ctx.send("*\"Go away...\"*")

    @commands.group(invoke_without_command=True)
    async def say(self, ctx, *, something):
        if ctx.invoked_subcommand is None:
            await ctx.send(f"*\"{something}\"*")

    @say.command(aliases=["hello",], name="hi")
    async def say_hi(self, ctx):
        await ctx.send("*\"No. Go away, I just want to sleep...\"*")

    @say.command(name="welcome")
    async def say_welcome(self, ctx):
        await ctx.send("*\"You are welcome to leave me alone...\"*")

    def parse_google(self, bytes_):
        data = BS(bytes_.decode("utf-8"), "lxml")
        for script in data("script"):
            script.decompose()

        search_results = []
        for tag in data.find_all("a"):
            attributes = tag.attrs
            if "onmousedown" in attributes.keys() and len(attributes) == 2:
                tag['href'] = utils.safe_url(tag['href'])
                search_results.append(tag)
            if len(search_results) > 4:
                break

        #unit convert
        results = data.find_all("div", class_="_cif")
        try:
            unit_in = results[0].find("select").find(selected=1)
            unit_out = results[1].find("select").find(selected=1)
            embed = discord.Embed(title="Search result:", description="**Unit convert**", colour=discord.Colour.dark_orange())
            embed.add_field(name=unit_in.text, value=results[0].input['value'])
            embed.add_field(name=unit_out.text, value=results[1].input['value'])
            embed.add_field(name="See also:", value='\n\n'.join((f"[{utils.discord_escape(t.text)}]({t['href']})" for t in search_results[0:4])), inline=False)
            return embed
        except:
            pass

        #timezone convert
        try:
            zone_data = data.find('div', class_="vk_c vk_gy vk_sh card-section _MZc")
            text = "\n".join((t.get_text().strip() for t in zone_data.find_all(True, recursive=False)))
            embed = discord.Embed(
                title="Search result:",
                description=f"**Timezone**\n{text}",
                colour=discord.Colour.dark_orange()
            )
            embed.add_field(name="See also:", value='\n\n'.join((f"[{utils.discord_escape(t.text)}]({t['href']})" for t in search_results[0:4])), inline=False)
            return embed
        except:
            pass

        #currency convert
        tag = data.find("div", class_="ccw_form_layout")
        try:
            inp = tag.find_all("input")
            unit = tag.find_all("option", selected=1)
            embed = discord.Embed(title="Search result:", description="**Currency**", colour=discord.Colour.dark_orange())
            embed.add_field(name=unit[0]['value'], value=inp[0]['value'])
            embed.add_field(name=unit[1]['value'], value=inp[1]['value'])
            embed.add_field(name="See also:", value='\n\n'.join((f"[{utils.discord_escape(t.text)}]({t['href']})" for t in search_results[0:4])), inline=False)
            return embed
        except:
            pass

        #calculator
        try:
            inp = data.find("span", class_="cwclet").text
            out = data.find("span", class_="cwcot").text
            embed = discord.Embed(title="Search result:", description=f"**Calculator**\n{inp}\n\n {out}", colour=discord.Colour.dark_orange())
            embed.add_field(name="See also:", value='\n\n'.join((f"[{utils.discord_escape(t.text)}]({t['href']})" for t in search_results[0:4])), inline=False)
            return embed
        except:
            pass

        #video
        tag = data.find("div", class_="_PWc")
        if tag:
            other = '\n\n'.join([f"<{t['href']}>" for t in search_results[1:5]])
            return f"**Search result:**\n{tag.find('a')['href']}\n\n**See also:**\n{other}"

        #wiki
        tag = data.find("div", id="rhs")
        try:
            title = tag.find("div", class_="_Q1n").div.text
            url_tag = tag.find("a", class_="q _KCd _tWc fl")
            try:
                url = f"\n[{url_tag.text}]({utils.safe_url(url_tag['href'])})"
            except:
                url = ""
            description = f"**{title}**\n{tag.find('div', class_='_cgc').find('span').text.replace('MORE', '').replace('…', '')}{url}"
            embed = discord.Embed(title="Search result:", description=description, colour=discord.Colour.dark_orange())
            embed.add_field(name="See also:", value='\n\n'.join((f"[{utils.discord_escape(t.text)}]({t['href']})" for t in search_results[0:4])), inline=True)
            return embed
        except:
            pass

        #definition
        tag = data.find("div", class_="lr_container")
        try:
            relevant_data = tag.find_all(
                lambda t:
                    (
                        t.name=="div"
                        and (
                            t.get("data-dobid")=="dfn"
                            or t.get("class") in (["lr_dct_sf_h"], ["xpdxpnd", "vk_gy"], ["vmod", "vk_gy"])
                            or t.get("style")=="float:left"
                        )
                    )
                    or
                    (
                        t.name=="span"
                        and (
                            t.get("data-dobid")=="hdw"
                            or t.get("class")==["lr_dct_ph"]
                        )
                    )
            )
            word = ""
            pronoun = ""
            current_page = -1
            defines = []
            for t in relevant_data:
                if t.name == "span":
                    if t.get("data-dobid") == "hdw":
                        word = t.text
                    else:
                        pronoun = t.text
                else:
                    if t.get("class") == ["lr_dct_sf_h"]:
                        current_page += 1
                        defines.append(f"**{word}**\n/{pronoun}\n")
                    elif "vk_gy" in t.get("class", []):
                        form = ""
                        for child_t in t.find_all(True):
                            if child_t.name == "b":
                                form = f"{form}*{child_t.find(text=True, recursive=False)}*"
                            else:
                                form = f"{form}{child_t.find(text=True, recursive=False)}"
                        defines[current_page] = f"{defines[current_page]}\n{form}"
                    elif t.get("style") == "float:left":
                        defines[current_page] = f"{defines[current_page]}\n**{t.text}**"
                    else:
                        defines[current_page] = f"{defines[current_page]}\n- {t.text}"
            see_also = '\n\n'.join((f"[{utils.discord_escape(t.text)}]({t['href']})" for t in search_results[1:5]))
            embeds = []
            max_page = len(defines)
            for i, d in enumerate(defines):
                embed = discord.Embed(title="Search result:", description=f"{defines[i]}\n\n(Page {i+1}/{max_page})", colour=discord.Colour.dark_orange())
                embed.add_field(name="See also:", value=see_also, inline=False)
                embeds.append(embed)
            return embeds
        except:
            pass

        #weather
        tag = data.find("div", class_="g tpo knavi obcontainer mod")
        try:
            embed = discord.Embed(
                title="Search result:",
                description=f"**Weather**\n[More on weather.com]({utils.safe_url(tag.find('td', class_='_Hif').a['href'])})",
                colour=discord.Colour.dark_orange()
            )
            embed.set_thumbnail(url=f"https:{tag.find('img', id='wob_tci')['src']}")
            embed.add_field(
                name=tag.find("div", class_="vk_gy vk_h").text,
                value=f"{tag.find('div', id='wob_dts').text}\n{tag.find('div', id='wob_dcp').text}",
                inline=False
            )
            embed.add_field(name="Temperature", value=f"{tag.find('span', id='wob_tm').text}°C | {tag.find('span', id='wob_ttm').text}°F")
            embed.add_field(name="Precipitation", value=tag.find('span', id='wob_pp').text)
            embed.add_field(name="Humidity", value=tag.find('span', id='wob_hm').text)
            embed.add_field(name="Wind", value=tag.find('span', id='wob_ws').text)
            embed.add_field(name="See also:", value='\n\n'.join((f"[{utils.discord_escape(t.text)}]({t['href']})" for t in search_results[1:5])), inline=False)
            return embed
        except:
            pass

        #simple wiki
        tag = data.find("div", class_="_oDd")
        try:
            embed = discord.Embed(title="Search result:", description=f"{tag.text}\n[{search_results[0].text}]({search_results[0]['href']})", colour=discord.Colour.dark_orange())
            embed.add_field(name="See also:", value='\n\n'.join((f"[{utils.discord_escape(t.text)}]({t['href']})" for t in search_results[1:5])), inline=False)
            return embed
        except:
            pass

        #translate
        tag = data.find("div", class_="_NId")
        try:
            inp = tag.find("a", id="tw-nosp")
            out = tag.find("pre", id="tw-target-text")
            link = tag.find("a", id="tw-gtlink")
            langs = tag.find_all("option", selected="1")
            embed = discord.Embed(title="Search result:", description=f"[Google Translate]({link['href']})", colour=discord.Colour.dark_orange())
            embed.add_field(name=langs[0].text, value=inp.text)
            embed.add_field(name=langs[1].text, value=out.text)
            embed.add_field(name="See also:", value='\n\n'.join((f"[{utils.discord_escape(t.text)}]({t['href']})" for t in search_results[0:4])), inline=False)
            return embed
        except:
            pass

        #non-special search
        other = '\n\n'.join((f"<{r['href']}>" for r in search_results[1:5]))
        return f"**Search result:**\n{search_results[0]['href']}\n**See also:**\n{other}"

    @commands.command(aliases=["g"])
    @commands.cooldown(rate=1, per=10, type=commands.BucketType.user)
    async def google(self, ctx, *, search):
        async with self.google_lock:
            async with ctx.typing():
                params = {
                    "q": quote(search),
                    "safe": "on",
                    "lr": "lang_en",
                    "hl": "en"
                }
                if ctx.channel.nsfw:
                    params["safe"] = "off"
                bytes_ = await utils.fetch(self.bot.session, "https://www.google.com/search", params=params)
                result = await self.bot.loop.run_in_executor(None, self.parse_google, bytes_)
                if isinstance(result, discord.Embed):
                    return await ctx.send(embed=result)
                elif isinstance(result, str):
                    return await ctx.send(result)
                elif isinstance(result, list):
                    pass
        await ctx.embed_page(result)

    @google.error
    async def google_error(self, ctx, error):
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send("Whoa slow down your Google search! You can only search once every 10 seconds.")

    @commands.command(aliases=["translate"])
    @commands.cooldown(rate=1, per=10, type=commands.BucketType.user)
    async def gtrans(self, ctx, *, search):
        async with self.google_lock:
            async with ctx.typing():
                params = {
                    "tl": "en",
                    "hl": "en",
                    "sl": "auto",
                    "ie": "UTF-8",
                    "q": quote(search)
                }
                bytes_ = await utils.fetch(self.bot.session, "http://translate.google.com/m", params=params)
                data = BS(bytes_.decode("utf-8"), "lxml")
                tag = data.find("div", class_="t0")
                embed = discord.Embed(colour=discord.Colour.dark_orange())
                embed.add_field(name="Detect", value=search)
                embed.add_field(name="English", value=tag.get_text())
                await ctx.send(embed=embed)

    @gtrans.error
    async def gtrans_error(self, ctx, error):
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send("Whoa slow down your Google translate! You can only do it once every 10 seconds.")

    @commands.command()
    async def char(self, ctx, *, characters):
        characters = re.sub(r"\s", "", characters)
        if len(characters) > 20:
            await ctx.send("Too many characters.")
        else:
            await ctx.send("\n".join([f"`\\U{ord(c):08x}` - `{c}` - {unicodedata.name(c, 'No name found.')}" for c in characters]))

    @commands.command()
    async def poll(self, ctx, *, data):
        stuff = data.strip().splitlines()
        items = stuff[1:10]
        int_to_emoji = {}
        emoji_to_int = {}
        for i in range(len(items)):
            e = FANCY_CHARS[str(i+1)]
            int_to_emoji[i+1] = e
            emoji_to_int[e] = i+1
        embed = discord.Embed(title=f"Polling: {stuff[0]}", description="\n".join((f"{int_to_emoji[i+1]} {s}" for i, s in enumerate(items))), colour=discord.Colour.dark_green())
        message = await ctx.send(embed=embed)
        for i in range(len(items)):
            await message.add_reaction(int_to_emoji[i+1])
        embed.set_footer(text="Poll will close in 1 minute.")
        await message.edit(embed=embed)
        await asyncio.sleep(60)
        message = await ctx.get_message(message.id)
        result = {}
        for r in message.reactions:
            if r.emoji in emoji_to_int.keys():
                result[r.emoji] = r.count
        await message.clear_reactions()
        max_result = []
        max_number = max(result.values())
        for key, value in result.items():
            if value == max_number:
                max_result.append(items[emoji_to_int[key]-1])
        await ctx.send(f"Poll ended.\nHighest vote: {' and '.join(max_result)} with {max_number} votes.")

    @commands.group(invoke_without_command=True)
    async def glitch(self, ctx, *, text):
        if ctx.invoked_subcommand is None:
            data = text.partition(" ")
            try:
                weight = int(data[0])
            except:
                weight = 20
            else:
                text = data[2]
            if 0 < weight <= 50:
                try:
                    await ctx.message.delete()
                except:
                    pass
                await ctx.send(
                    embed=discord.Embed(
                        title=f"{ctx.author.display_name} said:",
                        description=
                            "".join((
                                "".join((
                                    c,
                                    "".join((random.choice(GLITCH_ALL) for i in range(weight)))
                                )) for c in text
                            )),
                        colour=discord.Colour.red()
                    )
                )
            else:
                await ctx.send("Weight value can only be between 1 and 50.")

    @glitch.command(aliases=["m"])
    async def meaningless(self, ctx, length: int=0):
        if 0 <= length <= 500:
            if length == 0:
                length = random.randrange(20, 50)
            try:
                await ctx.message.delete()
            except:
                pass
            text_body = "".join((random.choice(GLITCH_TEXT) for i in range(length)))
            await ctx.send(
                embed=discord.Embed(
                    title=f"{ctx.author.display_name} said:",
                    description="\n".join((text_body[i:i+50] for i in range(0, len(text_body), 50))),
                    colour=discord.Colour.red()
                )
            )
        else:
            await ctx.send("Wha hold your horse with the length.")

#==================================================================================================================================================

def setup(bot):
    bot.add_cog(Misc(bot))
