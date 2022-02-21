import os, discord, random, asyncio, json, time
from os import path
from discord.ext import commands, tasks
from discord.ext.commands import cooldown

with open("config.json") as f:
    config = json.load(f)



class commands(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.counter = 0

    @commands.command(name="ping", pass_context=True)
    async def pingt(self, ctx):
        "Shows latency"
        channel = ctx.message.channel
        t1 = time.perf_counter()
        await ctx.trigger_typing()
        t2 = time.perf_counter()
        await ctx.send("Pong: ``{}ms`` :ping_pong:".format(round((t2-t1)*1000)))
    


def setup(bot):
    bot.add_cog(commands(bot))
    
