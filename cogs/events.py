from ast import excepthandler
import os, discord, json,asyncio
from os import path
from discord.ext import commands, tasks
from discord.ext.commands import cooldown
from cogs.bal_cache import cache_sync

with open("config.json") as f:
    config = json.load(f)

def error_embed(self, ctx, error):
    user = ctx.message.author
    embed = discord.Embed(title="ERROR!", color=discord.Color.red())
    embed.set_thumbnail(url="https://i.imgur.com/fZ4kVi0.png")
    embed.add_field(name="The following exception has occured", value=error)
    return embed

class events(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.counter = 0

    # Sys Events
    @commands.Cog.listener()
    async def on_ready(self):
        id = self.bot.user.id
        bot_user = self.bot.user.name
        print ("------------------------------------")
        print ("discord.py version: " + discord.__version__)
        print ("Bot ID: " + str(id))
        print ("Bot Name: " + bot_user)
        print ("------------------------------------")
        # await self.bot.change_presence(activity=discord.Game(name="Type "+ config["Discord"].get("prefix"), type=1))



    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        if isinstance(error, AttributeError):
            print('user not found')
            pass 

        if isinstance(error, commands.CommandOnCooldown):
            test = '```This command is on a cooldown, please try again in {:.2f}s```'.format(error.retry_after)
            cooldwn=await ctx.send(test)
            await ctx.message.delete()
            await cooldwn.delete(delay=2)

        if isinstance(error,commands.UserNotFound):
            print('something went wrong')

       # elif isinstance(error, commands.CheckFailure):
        #    ...
        
        #elif isinstance(error, commands.CommandNotFound):
           # ...

        #elif isinstance(error, commands.MissingRequiredArgument):
            #msg = "Missing required argument(s)!"
            #embed = error_embed(self=self, ctx=ctx, error=msg)
            #await ctx.send(embed=embed)

        #elif isinstance(error, commands.BadArgument):
            #msg = f"Could not find user \"{ctx.message.content[ctx.message.content.find(' ')+1::]}\""
            #embed = error_embed(self=self, ctx=ctx, error=msg)
            #await ctx.send(embed=embed)
        #else:
            #embed = error_embed(self=self, ctx=ctx, error=error)
            #await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(events(bot))
