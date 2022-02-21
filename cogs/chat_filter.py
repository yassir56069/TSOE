import os, discord, random, asyncio, json, time
from os import path
from discord.ext import commands, tasks
from discord.ext.commands import cooldown
from cogs.owner import fileDir, cogs_data 
from discord.utils import get
from cogs.bal_cache import fetch_from_json,reveal_cache,retrieve_cache,role_ini,cache_sync,backup_cache_sync
from discord.ext.commands.cooldowns import BucketType
from lru import LRU





class chat_filter(commands.Cog):
    def __init__(self, bot):
        self.flood_rate=5
        self.bot=bot
        self.bal=LRU(30)






def setup(bot):
    bot.add_cog(chat_filter(bot))