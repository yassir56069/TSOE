import os, discord, random, asyncio, json, time, platform
from os import path
from discord.ext import commands, tasks
from discord.ext.commands import cooldown

with open("config.json") as f:
    config = json.load(f)

#Path fuckery
fileDir = os.path.dirname(os.path.realpath('__file__'))
cogs_data =  os.path.join(fileDir, 'cogs_data/')


class owner(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.counter = 0
    "Owner only commands"
    

    #Commands
    @commands.has_permissions(administrator=True)
    @commands.command(name="reload", description="Reload extension")
    async def reload(self, ctx, cog):
        "Reloads a defined extension"
        self.bot.reload_extension("Modules."+cog)
        await ctx.send("[INFO] The Extension "+"``"+str(cog) +"``"+" has been reloaded!")

    @commands.has_permissions(administrator=True)
    @commands.command(name="cogs", description="Show all extenstions")
    async def cogs(self, ctx):
        "Lists all extensions inside the cogs directory"
        embed= discord.Embed(title="Cogs List")
        for i in self.bot.cogs:
            embed.add_field(name="\u200b", value=i, inline=True)

        await ctx.send(embed=embed)


    @commands.has_permissions(administrator=True)
    @commands.command(name="update", aliases=["pull", "gitpull"], description="Update the bot")
    async def gitpull(self, ctx):
        await ctx.send("Updating...")
        if platform.system() == "Windows":
            os.system("git pull")
        else:
            os.system("sudo git pull")
        await ctx.send("Done.")
        pass

    @commands.has_permissions(administrator=True)
    @commands.command(name="restart", description="Restart bot")
    async def reboot(self, ctx):
        await ctx.send("Restarting...")
        if platform.system() == "Windows":
            os.system("python main.py")
        else:
            os.system("sudo nohup python3 main.py & disown")
        await ctx.bot.logout()


def setup(bot):
    bot.add_cog(owner(bot))
    
