import os, discord, random, asyncio, json, time
from discord.ext import commands

class games(commands.Cog):
    def __init__(self,bot):
        self.coin_toss=0
        self.bot=bot
        self.counter = 0

    @commands.command(name="FLIP",aliases=['FLIP`'])
    async def coin_toss(self,ctx,choice):
        #choice must be either H or T
        self.coin_toss=random.randint(0,1)
        if choice == 'H' or choice == 'T':
            if choice== 'H':
                choice_text='Heads'
                if self.coin_toss==0:
                    won_text='And Won!'
                else:   
                    won_text='You Lost!'
            else:
                choice_text='Tails'
                if self.coin_toss==1:
                    won_text='And Won!'
                else:
                    won_text='You Lost!'

            coin_embed=discord.Embed(title="The Coin Is Being Tossed",description="You're Betting On "+choice_text ,colour=discord.Colour.gold())
            coin_embed.set_author(name=ctx.author.name,icon_url=ctx.author.avatar_url)
            coin_embed.set_image(url="https://cdn.dribbble.com/users/1493264/screenshots/5573460/coin-flip-dribbble.gif")
            coin_embed.set_thumbnail(url="https://i.imgur.com/YTg8cjS.png")

            heads_embed=discord.Embed(title="The Coin Has Been Tossed",description="You Got Heads! "+won_text  ,colour=discord.Colour.gold())
            heads_embed.set_author(name=ctx.author.name,icon_url=ctx.author.avatar_url)
            heads_embed.set_image(url="https://rollthedice.online/assets/images/upload/dice/dado-cara-cruz/cara_moneda.png")

            tails_embed=discord.Embed(title="The Coin Has Been Tossed",description="You Got Tails! "+won_text ,colour=discord.Colour.gold())
            tails_embed.set_author(name=ctx.author.name,icon_url=ctx.author.avatar_url)
            tails_embed.set_image(url="https://rollthedice.online/assets/images/upload/dice/dado-cara-cruz/cruz_moneda.png")

            loading=await ctx.send(embed=coin_embed)    
            await asyncio.sleep(7)
            await loading.delete()
            if self.coin_toss==0:
                await ctx.send(embed=heads_embed)
            else:
                await ctx.send(embed=tails_embed)

            if choice == "H" and self.coin_toss==0 or choice == "T" and self.coin_toss==1:
                
                print("COIN: PLAYER WON")
            else:
                print("COIN: PLAYER LOST")
        else:
            await ctx.send('``INCORRECT FORMAT: PLEASE DO `FLIP` H OR `FLIP` T ``')

    
    @commands.group()
    async def cool(self,ctx):

            if ctx.invoked_subcommand is None:
                await ctx.send("No")

    @cool.command(name='bot',aliases=['TESTB'])
    async def _bot(self,ctx):
            await ctx.send('Yes, the bot is cool.')

    @commands.group(name="DUNGEON",aliases=['DNG`'],invoke_without_command=True)
    @commands.has_role('Owner')
    async def dungeon_game(self,ctx,choice=None):
        self.dungeon_current=ctx.author.id
        self.is_playing=True
        dungeon_embed=discord.Embed(title="THE DUNGEON",description="To start the game do `DNG` START",colour=discord.Colour.dark_red())
        dungeon_embed.set_author(name=ctx.author.name,icon_url=ctx.author.avatar_url)
        dungeon_embed.set_image(url="https://cdn.discordapp.com/attachments/732597615199387820/732603048664236082/Untitled13_20200714182238.png")
        dungeon_embed.set_thumbnail(url="https://i.imgur.com/YTg8cjS.png")
        dungeon_embed.add_field(name="Description:",value='"The Dungeon" is a Dungeon crawler game where your goal is to roam the dungeon to try and find loot,and finally make a swift exit,careful of the skeleton mobs that may end up catching you ending your run! find the exit as fast as possible with the maximum amount of loot.')
        startup=await ctx.send(embed=dungeon_embed)
        

    @commands.command(name="DUNGEONT",aliases=['DT`'])
    @commands.has_role('Owner')
    async def dungeon_test(self,ctx,choice=None):
        print(choice)
        i=0
        if choice ==None:
            await ctx.send("hello")

            def check(m):
                return m.content == ('hello') or m.content == ('hi')

            for i in range(10):
                msg = await self.bot.wait_for('message', check=check)
                if msg.content== ('hello'):
                    print('y')
                elif msg.content==('hi'):
                    print('n')
                i+=1
    

def setup(client):
    client.add_cog(games(client))
