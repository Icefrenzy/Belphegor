from unicodedata import normalize, category
import re
import asyncio
from datetime import datetime, timedelta
import pytz
from pytz import timezone
from urllib.parse import quote

_keep_char = (".", "_", " ")

def safe_filename(any_string):
    return ''.join((c for c in any_string if c.isalnum() or c in _keep_char))

_keep_special_char = ("\n", "\t")

def unifix(any_string):
    return "".join((c for c in normalize("NFKC", any_string) if category(c)[0]!="C" or c in _keep_special_char)).strip()

def split_page(text, split_len, *, safe_mode=True):
    description = re.split(r"(\s)", text)
    description_page = ["",]
    cur_index = 0
    for word in description:
        if word=="@everyone":
            word = "@\u200beveryone"
        elif word=="@here":
            word = "@\u200bhere"
        if safe_mode:
            if word[:7]=="http://" or word[:8]=="https://":
                word = safe_url(word)
            else:
                word = discord_escape(word)
        cur_node = description_page[cur_index]
        if len(cur_node) + len(word) < split_len:
            description_page[cur_index] = f"{cur_node}{word}"
        else:
            if len(word) < split_len:
                description_page[cur_index] = f"{cur_node}..."
                description_page.append(f"...{word}")
                cur_index += 1
            else:
                left = split_len - len(cur_node)
                description_page[cur_index] = f"{cur_node}{word[:left]}..."
                stuff = [f"...{word[i+left:i+split_len+left]}..." for i in range(0, len(word)-left, split_len)]
                stuff[-1] = stuff[-1][:-3]
                description_page.extend(stuff)
                cur_index += len(stuff)
    return description_page

def seconds_to_text(seconds):
    seconds = int(seconds)
    wt = [
        ("year", seconds//31536000),
        ("month", seconds%31536000//2592000),
        ("week", seconds%31536000%2592000//604800),
        ("day", seconds%31536000%2592000%604800//86400),
        ("hour", seconds%86400//3600),
        ("minute", seconds%3600//60),
        ("second", seconds%60)
    ]
    text_body = ""
    for item in wt:
        if item[1] > 1:
            text_body = f"{text_body} {item[1]} {item[0]}s"
        elif item[1] == 1:
            text_body = f"{text_body} {item[1]} {item[0]}"
    return text_body.strip()

time_regex = re.compile(
    r"(?:[\s\b]*)"
    r"(?:for|in|and|,|;|&)?(?:\s*)"
    r"(\d+\.?\d*)(?:\s*)"
    r"(w(?:(?:eek)?s?)?|d(?:(?:ay)s?)?|h(?:(?:our)s?)?|m(?:(?:in)(?:ute)?s?)?|s(?:(?:ec)(?:ond)?s?)?)"
    r"(?:[\s\b]*)",
    flags=re.I
)

def extract_time(text):
    extract = time_regex.findall(text)
    new_text = time_regex.sub("", text)
    result = {"weeks": 0, "days": 0, "hours": 0, "minutes": 0, "seconds": 0}
    if extract:
        for wt in extract:
            fc = wt[1][:1].lower()
            if fc == "w":
                result["weeks"] += float(wt[0])
            elif fc == "d":
                result["days"] += float(wt[0])
            elif fc == "h":
                result["hours"] += float(wt[0])
            elif fc == "m":
                result["minutes"] += float(wt[0])
            elif fc == "s":
                result["seconds"] += float(wt[0])
    return new_text, timedelta(**result)

def now_time(tzinfo=pytz.utc):
    return datetime.now(tzinfo)

def format_time(dt_obj):
    return dt_obj.strftime("%a, %Y-%m-%d at %I:%M:%S %p, GMT%z")

jp_timezone = timezone("Asia/Tokyo")

def jp_time(dt_obj):
    return dt_obj.astimezone(jp_timezone).strftime("%a, %Y-%m-%d at %I:%M:%S %p, GMT%z (Tokyo/Japan)")

discord_regex = re.compile(r"(?<!\\)[*_\[\]~`]")

def _match_this(match):
    return f"\\{match.group(0)}"

def discord_escape(any_string):
    return discord_regex.sub(_match_this, any_string)

def safe_url(any_url):
    return quote(any_url, safe=r":/&$+,;=@#~%")