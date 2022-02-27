from datetime import datetime, date
from hashlib import new
import os
import discord
import random
import asyncio
import asyncpg
import json
import time
import re
from os import path
from discord.ext import commands, tasks
from discord.ext.commands import cooldown
from cogs.owner import fileDir, cogs_data
from discord.utils import get
from cogs.img_cache import db_addimg, whitelist
from cogs.bal_cache import fetch_from_json, reveal_cache, retrieve_cache, role_ini, peak_ini, cache_sync, backup_cache_sync, fast_retrieve, db_decay_data, db_dump_decay, pgdb
from discord.ext.commands.cooldowns import BucketType
from lru import LRU


intents = discord.Intents(members=True)

# Generate config for cog
if path.exists(cogs_data+"currency_config.json") == False:
    with open(cogs_data+'currency_config.json', 'w') as configout:
        json.dump({
            "Ban_Role": 0,
            "Message_cost": -1
        }, configout)
    print("[INFO] currency_config.json generated!")
else:
    with open(cogs_data+"currency_config.json") as f:
        currency_config = json.load(f)


class currency(commands.Cog):

    def __init__(self, bot):
        self.bot = bot        
        self.counter = 0
        self.msg_count = 0
        self.db_add.start()
        self.db_update.start()
        self.Peaktime_setter.start()
        self.Event_RFSH.start()
        self.amount_checker.start()
        self.booster_clear.start()
        self.mute_trigger.start()
        self.week_test.start()

        self.Peakrun = False



        # DB Stuff
        self.count = 0

        # Timing Stuff
        # Default is 60 (turn time into minutes instead of seconds)
        self.peak_time = 60
        self.peak_rnd = [5, 20]

        # memory usage, LRUs act as cache
        self.bal = LRU(30)
        self.msg_counts = LRU(5)
        self.dwn_streaks = LRU(15)
        self.up_streaks = LRU(15)
        self.streaks_decay = 10
        self.peak = dict()
        self.roles = dict()
        role_ini(self)
        peak_ini(self)


        self.rolevals = {
            0 : 883769327713660969,
            1 : 883763180189388870,
            2 : 883770839680577588,
            1000: int(self.roles['1000EP'][0]),
            2500: int(self.roles['2500EP'][0]),
            5000: int(self.roles['5000EP'][0]),
            10000: int(self.roles['10,000EP'][0]),
            25000: int(self.roles['25,000EP'][0]),
            50000: int(self.roles['50,000EP'][0]),
            100000: int(self.roles['100,000EP'][0]),
            250000: int(self.roles['250,000EP'][0]),
            500000: int(self.roles['500,000EP'][0]),
            1000000: int(self.roles['1,000,000EP'][0])
        }

        self.streak_emotes = {
            1: '',  # no reaction added
            2: '<:Streak2:881403696641105921>',
            3: '<:Streak3:881403697043742760>',
            4: '<:Streak4:881403697635164241>',
        }
        # Message costs
        self.booster_length = 30
        self.no_boost = -1
        self.peak_pay = 4
        self.b1_payout = 6
        self.b2_payout = 20
        self.b3_payout = 50

        # Image stuff
        self.whitelist = whitelist
        self.image_cost = 1000

        # chat content filter
        self.flood_rate = 5
        self.filter_tax = 0.05
        self.filter_warn_delay = 3

        # Message costs (debug)
        print("||||||||||||INITIAL VALUES___|||")
        print("self.no_boost: " + str(self.no_boost))
        print("self.b1_payout: " + str(self.b1_payout))
        print("self.b2_payout: " + str(self.b2_payout))
        print("self.b3_payout: " + str(self.b3_payout))
        print("||||||||||||_________________|||")
        self.boosters = {
            1: (self.roles['boost1'][0]),
            2: (self.roles['boost2'][0]),
            3: (self.roles['boost3'][0])
        }

    # Listener events
    # cache sync
    @commands.Cog.listener()
    async def on_ready(self):
        await cache_sync(self, True)
        await backup_cache_sync(self, True)

    # handles message costs and payouts 
    @commands.Cog.listener("on_message")
    async def currency_manipulation(self, message):
        guild = self.bot.get_guild(int(self.roles['SERVERID'][0]))
        bot_role = guild.get_role(726741576495398933) 
        try:           
            if not (bot_role in message.author.roles or message.channel.id == 726441555660898354):  # EP CALC PER MESSAGE
                reveal_cache(self)
                self.msg_count = self.msg_count+1
                userid = str(message.author.id)
                await fast_retrieve(self, userid)
                #fetch_from_json(self, userid)
                users = retrieve_cache(self)
                guild = self.bot.get_guild(int(self.roles['SERVERID'][0]))
                user = guild.get_member(int(userid))
                val = users[str(message.author.id)]['amount']
                if val == 0:
                    role = guild.get_role(int(self.roles['Ban'][0]))
                    await message.author.add_roles(role)

                try:
                    if int(users[str(userid)]['msg_payout']) < self.peak_pay and self.Peakrun == True:
                        users[str(userid)]['msg_payout'] = self.peak_pay
                        amount = int(users[str(userid)]['msg_payout'])
                    else:
                        amount = int(users[str(userid)]['msg_payout'])
                except:
                    users[str(userid)]['msg_decay'] = 'None'
                    users[str(userid)]['msg_payout'] = self.no_boost
                    amount = int(users[str(userid)]['msg_payout'])

                await create_user(self, users, message.author)
                await update_json(self, users, message.author, amount, message)
                self.text_chnl = message.channel

        except AttributeError as exception:
            print(f'Message Error: {exception}')
            pass

    # handles all chat filtering and moderation
    @commands.Cog.listener("on_message")
    async def chat_filter(self, message):
        guild = self.bot.get_guild(int(self.roles['SERVERID'][0]))
        owner_role = guild.get_role(678547289824034846) #owner
        partner_role = guild.get_role(726501556324663437) #partner

        try:
            if not owner_role in message.author.roles or not partner_role in message.author.roles and message.channel.id != 726441555660898354:
                # URL detection
                URL_REG = re.compile(r'https?://(?:www\.)?.+')
                if message.author.id != self.bot.user.id:
                    if re.search( URL_REG , str(message.content)) != None:
                        await message.delete()
                        if message.channel.id != (944572217000341584): #if not terminal channel
                            await link_punish(self , message)

                # flood detection
                if message.author.id != self.bot.user.id:
                    if len(message.content.split("\n")) >= self.flood_rate:
                        user = guild.get_member(int(message.author.id))
                        mute_role = guild.get_role(int(726446379823530015))
                        await user.add_roles(mute_role)
                        await message.delete()
                        await filtered_msg_handling(self, "flooding", message.author.id)

                # spam detection
                if message.author.id != self.bot.user.id:
                    try:
                        self.msg_counts[str(message.author.id)]['rate'] = self.msg_counts[str(
                            message.author.id)]['rate']+1
                    except:
                        self.msg_counts[str(message.author.id)] = {}
                        self.msg_counts[str(message.author.id)]['rate'] = 0

        except AttributeError as exception:
            print(f'Filter Error: {exception}')
            pass

    @commands.Cog.listener()
    @commands.cooldown(2, 3, BucketType.guild)
    async def on_typing(self, channel, user, when):
        guild = self.bot.get_guild(int(678151676862922792))
        userid = str(user.id)
        await fast_retrieve(self, userid)
        #fetch_from_json(self, userid)
        try: 
            users = retrieve_cache(self)
            bot_role = guild.get_role(int(self.roles['Bots'][0]))
            if userid in users:
                val = users[str(user.id)]['amount']
                rnd_val = (int(val)) / 1000
                rnd_val = round(rnd_val) * 1000

                if user != self.bot.user.id:
                    if bot_role not in user.roles:
                        for key in self.rolevals.keys():
                            if rnd_val >= key:
                                role = guild.get_role(self.rolevals[key])
                                await user.add_roles(role)
                            if rnd_val < key:
                                role = guild.get_role(self.rolevals[key])
                                await user.remove_roles(role)

        except AttributeError as exception:
            print(f'Typing Error: {exception}')
            pass

    # On Join add user to users.json
    @commands.Cog.listener()
    async def on_member_join(self, member):
        await fast_retrieve(self, member.id)
        #fetch_from_json(self, member.id)
        users = retrieve_cache(self)
        guild = self.bot.get_guild(int(self.roles['SERVERID'][0]))
        ep_role = guild.get_role(self.rolevals[1000])
        await member.add_roles(ep_role)
        for key in self.rolevals.keys():
            if key < 3:
                default_role = guild.get_role(self.rolevals[key])
                if default_role not in member.roles:
                    await member.add_roles(default_role)
            else:
                break

    # (REACTION EVENTS) When the '❔' emote is reacted on a any cmd(cmds list) by a user,the user is explained the command by the bot in dms!(NOW USES A CUSTOM EMOTE)
    @commands.Cog.listener(name="on_reaction_add")
    @commands.has_role('Owner')
    async def on_reaction_add1(self, Reaction, user):
        cmds = ['`ff`', '`null`', '`ft`', '`del`']
        if Reaction.emoji == self.bot.get_emoji(int(self.roles['?HELP_EMOTE'][0])):
            msg = Reaction.message.content
            if cmds[0] in msg[:4]:
                ff_msg = await user.send("> `ff` **@User : __Upvote User__**")
                await asyncio.sleep(5)
                await ff_msg.delete()
            elif cmds[1] in msg[:6]:
                null_msg = await user.send("> `null` **@User : __Mutes a user for 10 minutes,costs value a % of user's current EP Value. Just writing `null` will mute the latest user in channel__**")
                await asyncio.sleep(5)
                await null_msg.delete()
            elif cmds[2] in msg[:4]:
                ft_msg = await user.send("> `ft` **@User : __Downvote User ,does not work on newpog users.__**")
                await asyncio.sleep(5)
                await ft_msg.delete()
            elif cmds[3] in msg[:5]:
                #print('yes')
                del_msg = await user.send("> `del` **@User : __delete user's latest messages,costs a % of user's current EP,does not work on newpog users__**")
                await asyncio.sleep(5)
                await del_msg.delete()

    # BOOSTER COMMANDS
    @commands.command(name="boost1", aliases=['b1'])
    async def b1(self, ctx):
        await fast_retrieve(self, ctx.author.id)
        users = retrieve_cache(self)
        user_to_check = ctx.author.id
        found = await role_check(self, user_to_check, int(self.roles['SERVERID'][0]), str(self.roles['boost1'][0])+'#' + str(self.roles['boost2'][0])+'#' + str(self.roles['boost3'][0]))
        if found == False:
            await booster_create(self, ctx, 2000, int(self.roles['SERVERID'][0]), int(self.roles['boost1'][0]), self.b1_payout, 'boost 1')
        else:
            await already_booster(self, ctx)
            await ctx.message.delete(delay=5)

    @commands.command(name="boost2", aliases=['b2'])
    async def b2(self, ctx):
        await fast_retrieve(self, ctx.author.id)
        users = retrieve_cache(self)
        user_to_check = ctx.author.id
        found = await role_check(self, user_to_check, int(self.roles['SERVERID'][0]), str(self.roles['boost1'][0])+'#' + str(self.roles['boost2'][0])+'#' + str(self.roles['boost3'][0]))
        if found == False:
            await booster_create(self, ctx, 10000, int(self.roles['SERVERID'][0]), int(self.roles['boost2'][0]), self.b2_payout, 'boost 2')
        else:
            await already_booster(self, ctx)
            await ctx.message.delete(delay=5)

    @commands.command(name="boost3", aliases=['b3'])
    async def b3(self, ctx):
        await fast_retrieve(self, ctx.author.id)
        users = retrieve_cache(self)
        user_to_check = ctx.author.id
        found = await role_check(self, user_to_check, int(self.roles['SERVERID'][0]), str(self.roles['boost1'][0])+'#' + str(self.roles['boost2'][0])+'#' + str(self.roles['boost3'][0]))
        if found is False:
            await booster_create(self, ctx, 50000, int(self.roles['SERVERID'][0]), int(self.roles['boost3'][0]), self.b3_payout, 'boost 3')
        else:
            await already_booster(self, ctx)
            await ctx.message.delete(delay=5)

    # LEADERBOARD COMMANDS

    @commands.command(name="week", aliases=['wk'])
    @ commands.has_role(678547289824034846)
    async def weekr435_test(self, ctx):
        db = pgdb.retrieve_db()
        db_bals = await db.fetch('SELECT userid , balance FROM users')
        for userid, balance in dict(db_bals).items():
            await db.execute(f'UPDATE users SET weekly_bal = {balance} WHERE userid = {userid}    ')

    @ commands.cooldown(1, 30, commands.BucketType.guild)
    @commands.command(name="alltimelb", aliases=['atlb', 'atleaderboard', 'alltimeleaderboard'])
    async def alltime_leaderboard(self, ctx):
        db = pgdb.retrieve_db()
        db_bals = await db.fetch('''SELECT distinct userid , balance FROM users
                                    ORDER BY balance DESC
                                    FETCH FIRST 10 ROWS ONLY
                                    ''')
        lb_embed = await create_atlb_embed(self, db_bals)
        print(lb_embed)
        await ctx.send(embed=lb_embed)

    @ commands.cooldown(1, 30, commands.BucketType.guild)
    @commands.command(name="weeklylb", aliases=['wlb', 'wleaderboard', 'weeklyleaderboard', 'lb', 'leaderboard'])
    async def weekly_leaderboard(self, ctx):
        db = pgdb.retrieve_db()
        db_bals = await db.fetch('''SELECT userid , balance - weekly_bal AS weekly_lb FROM users
                                    ORDER BY weekly_lb DESC
                                    FETCH FIRST 10 ROWS ONLY;
                                    ''')
        lb_embed = await create_wlb_embed(self, db_bals)
        print('another test 2')
        await ctx.send(embed=lb_embed)

    @ commands.cooldown(1, 30, commands.BucketType.guild)
    @commands.command(name="whitelist", aliases=['wlist'])
    async def display_whitelist(self, ctx):
        msg_string = (f"```ACCEPTED IMAGE LINKS: ```")
        for link in self.whitelist:
            msg_string = msg_string + (f"<{link}> \n")
        msg_string = msg_string + (f"```WHITELIST```")
        await ctx.send(msg_string, delete_after = 10)

    @tasks.loop(seconds=30)
    async def db_add(self):
        '''Add user from cache if not in database'''
        #print('Performing Database Addition Check')
        db = pgdb.retrieve_db()
        users = retrieve_cache(self)

        for userid in dict(users).keys():
            try:
                await db.execute(f"""
                                INSERT INTO users (userid, balance, weekly_bal )
                                VALUES('{userid}','{int(users[str(userid)]['amount'])}','{int(users[str(userid)]['amount'])}');
                                """)

                #print(
                #    f"{'_'*50} \nDATABASE ENTRY ADDED \nTIME: {datetime.now()} \n {'_'*50}")

            except asyncpg.UniqueViolationError or asyncpg.PostgresSyntaxError:
                pass

    @tasks.loop(seconds=15)
    async def db_update(self):
        '''If user in database, update their balance'''
        db = pgdb.retrieve_db()
        users = retrieve_cache(self)
        db_users = await db.fetch('SELECT userid , balance FROM users')
        #print('Performing Database Update Check..')
        for userid in dict(users).keys():
            if int(userid) in dict(db_users).keys():
                await fast_retrieve(self, userid)
                if self.Peakrun == False:
                    await db.execute("""
                            UPDATE msgs
                            SET payout = -1
                            WHERE decay_date = 'None'; """)

                await db.execute(f"""
                            UPDATE users
                            SET balance = {users[str(userid)]['amount']} 
                            WHERE userid = '{userid}';
                            UPDATE msgs
                            SET decay_date = '{users[str(userid)]['msg_decay']}',
                                payout = {users[str(userid)]['msg_payout']}
                            WHERE userid = '{userid}';
                            """)
    
    @tasks.loop(seconds=3600)
    async def week_test(self):
        if date.today().weekday() == 6:
            db = pgdb.retrieve_db()
            db_bals = await db.fetch('SELECT userid , balance FROM users')
            for userid, balance in dict(db_bals).items():
                await db.execute(f'UPDATE users SET weekly_bal = {balance} WHERE userid = {userid}    ')
            await asyncio.sleep(86400) #sleep for a day


    @tasks.loop(seconds=1)
    async def Peaktime_setter(self):
        # Initiate: Peaktime state and Roles.json
        guild = self.bot.get_guild(int(self.roles['SERVERID'][0]))
        channel = guild.get_channel(int(self.roles['!channel_general'][0]))
        role = guild.get_role(int(self.roles['PEAKTIME'][0]))
        bot_user = guild.get_member(int(self.roles['BOT_USER_ID'][0]))
        if self.Peakrun == False:

            await bot_user.remove_roles(role)
            try:
                await self.embed_run.delete()
                Peak_end_embed = await Peak_fnc(self, self.peak_duration, exit_embed='yes')
                embed_end = await channel.send(embed=Peak_end_embed)
                await embed_end.delete(delay=7)
            except AttributeError as e:
                print(e)

            self.peak_cooldown = random.randint(3,15)
            print('Next Peak In: ' + str(self.peak_cooldown) + " Minutes")
            await asyncio.sleep(self.peak_cooldown*60)

            self.Peakrun = True

        else:
            self.peak_duration = random.randint(self.peak_rnd[0], self.peak_rnd[1])
            await bot_user.add_roles(role)
            Peak_embed = await Peak_fnc(self, self.peak_duration)
            self.embed_run = await channel.send(embed=Peak_embed)
            await asyncio.sleep(self.peak_duration*60)

            self.Peakrun = False

    # PEAKTIME RANDOMISER
    @tasks.loop(seconds=10)
    async def Peaktime_RNG(self):
        # Initiate: Peaktime state and Roles.json
        self.Peakrun = False
        guild = self.bot.get_guild(int(self.roles['SERVERID'][0]))
        channel = guild.get_channel(int(self.roles['!channel_general'][0]))
        role = guild.get_role(int(self.roles['PEAKTIME'][0]))
        bot_user = guild.get_member(int(self.roles['BOT_USER_ID'][0]))

        # Cooldown time before next peaktime
        if int(self.peak['cooldown'][0]) == 0:
            self.peak['duration'][0] = 0
            self.peak_cooldown = random.randint(1,3)  # randomise cooldown duration
            print('Next Peak In: ' + str(self.peak_cooldown) + " Minutes")
            self.peak['cooldown'][0] = time.time(
            ) + self.peak_cooldown 

            self.peak_cooldown = datetime.fromtimestamp(
                int(self.peak['cooldown'][0]))

        if self.peak['duration'][0] == 0:  # start peak
            if datetime.now() < self.peak_cooldown:
                # sleep until peaktime
                #print('peaktime sleep..')
                pass
            else:
                # Peaktime run
                self.peak_duration = random.randint(
                    self.peak_rnd[0], self.peak_rnd[1])
                self.peak['duration'][0] = time.time(
                ) + self.peak_duration * self.peak_time
                self.Peakrun = True
                await bot_user.add_roles(role)
                Peak_embed = await Peak_fnc(self, self.peak_duration)
                self.embed_run = await channel.send(embed=Peak_embed)

                # sleep until peaktime ends
                self.peak_duration = datetime.fromtimestamp(
                    int(self.peak['duration'][0]))

        if self.peak['duration'][0] != 0:  # end peak
            if datetime.now() < self.peak_duration:
                #print('peaktime sleep..(DURATION)')
                pass
            else:
                await bot_user.remove_roles(role)
                self.peak['duration'][0] = 0
                self.peak['cooldown'][0] = 0
                # Sending embed for peaktime ended and removing the role off the bot
                if self.Peakrun == True:
                    await self.embed_run.delete()

                Peak_end_embed = await Peak_fnc(self, self.peak_duration, exit_embed='yes')
                embed_end = await channel.send(embed=Peak_end_embed)
                await embed_end.delete(delay=5)

    @ tasks.loop(seconds=2)
    async def Event_RFSH(self):
        if self.msg_count == 8:
            await self.text_chnl.edit(slowmode_delay=2)
            await asyncio.sleep(25)
            await self.text_chnl.edit(slowmode_delay=0)
        self.msg_count = 0

    # mute trigger (individual msg_count)
    @ tasks.loop(seconds=2)
    async def mute_trigger(self):
        for users in self.msg_counts.keys():
            if self.msg_counts[str(users)]['rate'] >= 4:
                self.msg_counts[str(users)]['rate'] = 0
                guild = self.bot.get_guild(int(self.roles['SERVERID'][0]))
                user = guild.get_member(int(users))
                role = guild.get_role(int(726446379823530015))
                await user.add_roles(role)
                await filtered_msg_handling(self, "spamming", users)
            self.msg_counts[str(users)]['rate'] = 0

    # updating boosters
    @ tasks.loop(seconds=5)
    async def amount_checker(self):
        users = retrieve_cache(self)
        
        for userid in users.keys():
            await fast_retrieve(self, userid)
            await db_decay_data(self,userid)

            if int(users[str(userid)]['msg_payout']) < self.peak_pay and self.Peakrun == True:
                users[str(userid)]['msg_payout'] = self.peak_pay
                await db_dump_decay(self,userid)
            else:
                if users[str(userid)]['msg_decay'] != 'decayed':
                    if users[str(userid)]['msg_decay'] != 'None':
                        if time.time() >= float(users[str(userid)]['msg_decay']):
                            users[str(userid)]['msg_payout'] = self.no_boost
                            users[str(userid)]['msg_decay'] = 'decayed'
                            await db_dump_decay(self,userid)
                    else:
                        users[str(userid)]['msg_payout'] = self.no_boost

    # AUTOMATIC ROLE REMOVAL (BOOSTER)
    @ tasks.loop(seconds=10)
    async def booster_clear(self):
        users = retrieve_cache(self)
        for userid in users.keys():
            await fast_retrieve(self, userid)
            await db_decay_data(self,userid)

            if users[str(userid)]['msg_decay'] == 'decayed':
                for i in range(1, 4):
                    await role_rmv(self, int(self.roles['SERVERID'][0]), int(self.roles['boost'+str(i)][0]), userid)
                    #print("BOOST " + str(i) + " REMOVED")
                users[str(userid )]['msg_decay'] = 'None'
                await db_dump_decay(self,userid)

    @ Peaktime_setter.before_loop
    async def before_printer(self):
        print('waiting...')
        await self.bot.wait_until_ready()
        guild = self.bot.get_guild(int(self.roles['SERVERID'][0]))
        role = guild.get_role(int(self.roles['PEAKTIME'][0]))
        down_role = guild.get_role(947507959066402887)
        bot_user = guild.get_member(int(self.roles['BOT_USER_ID'][0]))
        await bot_user.remove_roles(role)
        await bot_user.remove_roles(down_role)
 

        print("Peaktime_setter Running!")

    @ db_update.before_loop
    async def before_printer(self):
        print('db_update |waiting...')
        await self.bot.wait_until_ready()
        print('db_update Running!')

    @ db_add.before_loop
    async def before_printer(self):
        print('db_add   |waiting...')
        await self.bot.wait_until_ready()
        self.db_log = self.bot.get_channel(int(942716604616167464))
        print('log channel initialized')
        print('db_add Running!')

    @ week_test.before_loop
    async def before_printer(self):
        print('week_test  |waiting...')
        await self.bot.wait_until_ready()
        print('week test Running!')

    @ commands.command(name="VCING", aliases=['vc`'])
    @ commands.cooldown(2000, 5, BucketType.guild)
    @ commands.has_role('Owner')
    async def VC(self, ctx):
        users = retrieve_cache(self)
        userid = ctx.author.id
        sndep = users[str(userid)]['amount']
        sndep = sndep-100
        if sndep > 0:
            users[str(userid)]['amount'] = sndep
            await role_add(self, int(self.roles['SERVERID'][0]), int(self.roles["VoiceTicket"][0]), userid, 3600)

    # OWNER COMMANDS: MODERATION___________________________________________________________________________

    @commands.has_permissions(administrator=True)
    @commands.command(name="shutdown",  aliases=['q', 'kill','stop', 'exit'], description="Turns the bot off")
    async def poweroff(self, ctx):
        guild = self.bot.get_guild(int(self.roles['SERVERID'][0]))
        down_role = guild.get_role(947507959066402887) 
        bot_user = guild.get_member(726487824639197184)
        await ctx.send('```Shutting down..```', delete_after = 2)
        await bot_user.add_roles(down_role)
        #overwrite = discord.PermissionOverwrite(send_messages = False) 
        #await guild.default_role.edit(Permissions=overwrite)
        await asyncio.sleep(2)

        await ctx.bot.close()

    @commands.has_permissions(administrator=True)
    @commands.command(name="turnon",  aliases=['on', 'run','start', 'open'], description="Turns the bot on")
    async def poweron(self, ctx):
        guild = self.bot.get_guild(int(self.roles['SERVERID'][0]))
        down_role = guild.get_role(947507959066402887) 
        bot_user = guild.get_member(726487824639197184)
        await ctx.send('```Fake Power On For Debug Purposes..```', delete_after = 2)
        #overwrite = discord.PermissionOverwrite(send_messages = False) 
        #await guild.default_role.edit(Permissions=overwrite)
        await bot_user.remove_roles(down_role)

    @ commands.command(name="PRINTROLES", aliases=['IDS'])
    @ commands.has_role('Owner')
    async def IDS(self, ctx):
        print('ROLE ---------> ID')
        for i, j in sorted(self.roles.items()):
            print(i, '---->', j)
        print('THESE ARE NOT THE ACTUAL ROLE NAMES,JUST THE ONES USED TO REPRESENT EACH ID')

    @ commands.command(name="PRINTUSERS", aliases=['users'])
    @ commands.has_role('Owner')
    async def USERS(self, ctx):
        users = retrieve_cache(self)
        guild = self.bot.get_guild(int(self.roles['SERVERID'][0]))
        print('USER ---------> ID')
        for i, j in sorted(users.items()):
            user = guild.get_member(int(i))
            print(i, 'NAME:', str(user), 'VALUE--->', j)
        print('THESE ARE NOT THE ACTUAL ROLE NAMES,JUST THE ONES USED TO REPRESENT EACH ID')

    @ commands.command(name="CHANGEVALS", aliases=['cv'])
    @ commands.has_role(678547289824034846) #Owner
    async def VAL(self, ctx, val, rcv: discord.Member):
        users = retrieve_cache(self)
        rcvid = rcv.id
        guild = self.bot.get_guild(int(self.roles['SERVERID'][0]))
        role = guild.get_role(int(self.roles['Ban'][0]))
        oldval = users[str(rcvid)]['amount']
        if oldval == 0:
            await rcv.remove_roles(role)

        users[str(rcvid)]['amount'] = int(val)  
        print('cv | change successful')

    @ commands.command(name="ADDUSER", aliases=['uadd'])
    @ commands.has_role(678547289824034846)
    async def Uadd(self, ctx, rcv: discord.Member):
        users = retrieve_cache(self)
        await fast_retrieve(self, rcv.id)

    # CURRENCY COMMANDS___________________________________________________________________________________
    # bal command (user balance and proxity balances)
    @ commands.command(name='daily_balance', aliases=['d'])
    @ commands.cooldown(1, 86400, commands.BucketType.user)
    @ commands.has_role(678547289824034846)
    async def daily_balance(self, ctx):
        users = retrieve_cache(self)
        rcvep = users[str(ctx.author.id)]['amount']
        Nrcvep = rcvep+100
        with open(cogs_data+"users.json", 'w') as f:
            users[str(ctx.author.id)]['amount'] = Nrcvep
            json.dump(users, f)

        daily_embed = discord.Embed(title="𝘿𝘼𝙄𝙇𝙔 𝙍𝙀𝘿𝙀𝙀𝙈𝙀𝘿", description="Your Account Balance Increased To : **__"+str(
            users[str(ctx.author.id)]['amount'])+" EP__**", colour=discord.Colour.gold())
        daily_embed.set_thumbnail(url='https://i.imgur.com/3zNEuX4.png')
        await ctx.send(embed=daily_embed)

    # bal command (user balance and proxity balances)
    @ commands.command(name='Balance_cmd', aliases=['bal'])
    @ commands.cooldown(10, 60, commands.BucketType.user)
    async def balance(self, ctx):
        await fast_retrieve(self, ctx.author.id)
        #fetch_from_json(self, ctx.author.id)
        users = retrieve_cache(self)
        proxy_bal_1 = None
        proxy_bal_2 = None
        sndid = ctx.author.id
        sndep = users[str(sndid)]['amount']
        guild = self.bot.get_guild(int(self.roles['SERVERID'][0]))
        for user in users.keys():
            if user != str(ctx.author.id):
                proxy_bal_user = guild.get_member(int(user))
                if proxy_bal_user != None:
                    if proxy_bal_1 == None:
                        proxy_bal_1_user = guild.get_member(int(user))
                        proxy_bal_1 = round(
                            users[str(proxy_bal_user.id)]['amount'], 2)
                    else:
                        if user != str(proxy_bal_1_user.id):
                            proxy_bal_2_user = guild.get_member(int(user))
                            proxy_bal_2 = round(
                                users[str(proxy_bal_user.id)]['amount'], 2)

        if proxy_bal_1 == None:
            await Bal_fnc(self, ctx, sndep)
            await ctx.message.delete(delay=10)
        elif proxy_bal_2 == None:
            await Bal_fnc(self, ctx, sndep, proxy_bal_1=proxy_bal_1, proxy_bal_1_user=proxy_bal_1_user)
            await ctx.message.delete(delay=12)
        else:
            await Bal_fnc(self, ctx, sndep, proxy_bal_1=proxy_bal_1, proxy_bal_1_user=proxy_bal_1_user, proxy_bal_2=proxy_bal_2, proxy_bal_2_user=proxy_bal_2_user)
            await ctx.message.delete(delay=15)

    @ commands.command(name='submit_image', aliases=['submit','s'])
    @ commands.cooldown(5, 60, commands.BucketType.guild)
    async def submit_img(self, ctx, link, name=None):
        self.whitelist = self.bot.get_channel(int(944571917598343248))
        await fast_retrieve(self, ctx.author.id)
        users = retrieve_cache(self)
        if users[str(ctx.author.id)]['amount'] > self.image_cost:
            users[str(ctx.author.id)]['amount'] = users[str(ctx.author.id)]['amount'] - self.image_cost
            run = True
        else:
            run = False

        img_flag =  await db_addimg(ctx, link, name)    
        if run == True:
            if img_flag == True:
                db = pgdb.retrieve_db()
                img = await db.fetchrow(f"SELECT img_no, img_name FROM imgs WHERE img_link = '{link}'")
                img_dict = dict(img)

                await self.whitelist.send(f"```ID: {list(img_dict.values())[0]} NAME: {list(img_dict.values())[1]}```{ctx.author.mention} {link}")
        else:
            ctx.message.send('```INSUFFICIENT FUNDS TO SUBMIT IMAGE```', delete_after=3)

    @ commands.command(name='post_image', aliases=['post','p'])
    @ commands.cooldown(4, 1, commands.BucketType.guild)
    async def post_img(self, ctx, *text_input):
        db = pgdb.retrieve_db()
        if text_input[0][:1] == '`' and text_input[0][-1] == '`':
            link = await db.fetchval(f"SELECT img_link FROM imgs WHERE img_no ='{text_input[0][1:-1]}'")  
        else:
            link = await db.fetchval(f"SELECT img_link FROM imgs WHERE img_name ='{text_input[0]}'") 
        
        if link == None:
            await ctx.send("```IMG NOT FOUND OR INVALID INPUT```", delete_after=3)
        else:
            await ctx.send(link)

    # up command (upvotes)
    @ commands.command(name="Upvote_cmd", aliases=['up', 'upvote'])
    @ commands.cooldown(4, 1, commands.BucketType.guild)
    async def up(self, ctx, rcv: discord.User):
        await fast_retrieve(self, ctx.author.id)
        await fast_retrieve(self, rcv.id)
        #fetch_from_json(self, ctx.author.id)
        #fetch_from_json(self, rcv.id)
        # add reaction based on streak value

        async def streaks_reactions(message, mult):
            await message.add_reaction(str(self.streak_emotes[mult]))

        async def streak_sleep():
            if self.up_streaks[str(rcvid)]['Current Streak:'] < 3:
                await asyncio.sleep(self.streaks_decay)
                self.up_streaks[str(rcvid)]['Current Streak:'] = 0

        users = retrieve_cache(self)
        sndid = ctx.author.id
        rcvid = rcv.id
        guild = self.bot.get_guild(int(self.roles['SERVERID'][0]))
        role = guild.get_role(int(self.roles['Ban'][0]))
        user = guild.get_member(rcvid)
        message = ctx.message
        mult = await add_up_streaks(self, ctx.author.id, rcvid)
        if sndid != rcvid:
            sndep = users[str(sndid)]['amount']
            sndep = sndep-10
            rcvep = users[str(rcvid)]['amount']
            rcvep = rcvep+(12 * mult)
            if sndep > 0:
                await streaks_reactions(message, mult)
                users[str(sndid)]['amount'] = sndep
                users[str(rcvid)]['amount'] = rcvep
                await streak_sleep(self)
                if rcvep > 0:
                    await user.remove_roles(role)
            else:
                await ctx.send("```TRANSACTION FAILED: INSUFFICIENT FUNDS```", delete_after=2)
        else:
            await ctx.message.delete()

    # dn command (downvotes)
    @ commands.command(name="Downvote_cmd", aliases=['dn', 'downvote'])
    @ commands.cooldown(4, 1, commands.BucketType.guild)
    async def dn(self, ctx, rcv: discord.User):
        print(self.dwn_streaks)
        await fast_retrieve(self, ctx.author.id)
        await fast_retrieve(self, rcv.id)

        # add reaction based on streak value
        async def streaks_reactions(message, mult):
            await message.add_reaction(str(self.streak_emotes[mult]))

        async def streak_sleep():
            if self.dwn_streaks[str(rcvid)]['Current Streak:'] < 3:
                await asyncio.sleep(self.streaks_decay)
                self.dwn_streaks[str(rcvid)]['Current Streak:'] = 0

        sndid = ctx.author.id
        rcvid = rcv.id
        message = ctx.message
        mult = await add_dn_streaks(self, ctx.author.id, rcvid)
        if sndid != rcvid:
            users = retrieve_cache(self)
            sndep = users[str(sndid)]['amount']
            sndep = sndep-10
            rcvep = users[str(rcvid)]['amount']
            rcvep = rcvep-(12*mult)
            if sndep > 10:
                await streaks_reactions(message, mult)
                if rcvep > 0:
                    users[str(sndid)]['amount'] = sndep
                    users[str(rcvid)]['amount'] = rcvep
                    await streak_sleep(self)
                else:
                    await ctx.send("```STREAK RESET: RECEIVER IS BROKE!```", delete_after=2)
                    self.dwn_streaks[str(rcvid)]['Current Streak:'] = 0
            else:
                await ctx.send("```TRANSACTION FAILED: INSUFFICIENT FUNDS```", delete_after=2)

        else:
            await ctx.message.delete()

    # add reaction based on streak value
    async def streaks_reactions(self, message, mult):
        await message.add_reaction(str(self.streak_emotes[mult]))

    # null command (muting for 10 mins)
    @ commands.command(name="Muting_cmd", aliases=['null'])
    @ commands.cooldown(1, 10, commands.BucketType.user)
    async def nl(self, ctx, rcv: discord.User):
        await fast_retrieve(self, ctx.author.id)
        await fast_retrieve(self, rcv.id)
        trn_run = False
        sndid = ctx.author.id
        rcvid = rcv.id
        (sndep, newep, cost) = cost_calc(self, ctx, rcv, rcvid, sndid, 0.5)
        users = retrieve_cache(self)
        guild = self.bot.get_guild(int(self.roles['SERVERID'][0]))

        user = guild.get_member(rcvid)
        Mute = guild.get_role(int(self.roles['Muted'][0]))

        if newep > 0:
            if Mute in user.roles:
                await ctx.send('```CANNOT MUTE USER: ALREADY MUTED```', delete_after=5)
            else:
                trn_embed, reactor, trn_run = await transaction_embed(self, ctx, rcv, int(self.roles['SERVERID'][0]), '𝙉𝙐𝙇𝙇 𝙏𝙍𝘼𝙉𝙎𝘼𝘾𝙏𝙄𝙊𝙉', ("Transaction: **__-" + str(cost) + "EP__**, Balance: **__" + str(newep) + "EP__**"))
        else:
            await ctx.send('```TRANSACTION FAILED: INSUFFICIENT FUNDS```', delete_after=1)

        if trn_run == True:
            if sndep > cost:
                users[str(sndid)]['amount'] = newep
                # RECEIVER REPLICATIONS
                userid = rcvid
                await role_add(self, int(self.roles['SERVERID'][0]), int(self.roles['Muted'][0]), userid, 300)
        else:
            await ctx.message.delete()

    # clear command
    @ commands.command(name="Delete_cmd", aliases=['del'])
    @ commands.cooldown(20, 5, commands.BucketType.guild)
    async def clear(self, ctx, rcv: discord.User):
        trn_run = False
        await fast_retrieve(self, ctx.author.id)
        await fast_retrieve(self, rcv.id)
        rcvid = rcv.id
        sndid = ctx.author.id 
        channel = ctx.channel 
        
        (sndep, newep, cost) = cost_calc(self, ctx, rcv, rcvid, sndid, 0.1)
        users = retrieve_cache(self)
        if sndep > cost:
            trn_embed, reactor, trn_run = await transaction_embed(self, ctx, rcv, int(self.roles['SERVERID'][0]), '𝘿𝙀𝙇 𝙏𝙍𝘼𝙉𝙎𝘼𝘾𝙏𝙄𝙊𝙉', ("Transaction: **__-" + str(cost) + "EP__**, Balance: **__" + str(newep) + "EP__**"))

        if trn_run == True:
                if sndep > cost:
                    users[str(sndid)]['amount'] = newep
                    async for message in channel.history(limit=100, oldest_first=False):
                        if message.author.id == rcvid:
                            await message.delete()
                            break
                else:
                    await ctx.send('```TRANSACTION FAILED: INSUFFICIENT FUNDS```', delete_after=3)
        else:
            await ctx.send('```TRANSACTION FAILED: INSUFFICIENT FUNDS```', delete_after=3)
            await ctx.message.delete()

    # transfers,uses rates,delay in between the transfer of 15 mins (currently disabled!)
    @ commands.command(name='Transfer_cmd', aliases=['t'])
    @ commands.cooldown(2000, 5, commands.BucketType.guild)
    @ commands.has_role(678547289824034846)
    async def trns(self, ctx, val, rcv: discord.User):
        await fast_retrieve(self, ctx.author.id)
        await fast_retrieve(self, rcv.id)
        self.run = False
        sndid, rcvid, newep, Nrcvep, rcvep = transfer_calc(
            self, ctx, val, rcv, 1.2)
        users = retrieve_cache(self)
        guild = self.bot.get_guild(int(self.roles['SERVERID'][0]))
        role = guild.get_role(int(self.roles['Ban'][0]))
        if newep > 0:
            self.run = True
            trn_embed, reactor = await transaction_embed(self, ctx, rcv, int(self.roles['SERVERID'][0]), '𝙀𝙋 𝙏𝙍𝘼𝙉𝙎𝙁𝙀𝙍', ("Your Balance After Transaction:  **__" + str(newep) + "Ep__**, Recipient's Balance After Transaction **__"+str(Nrcvep)+"Ep__**"))
        else:
            trn_fail = await ctx.send('```TRANSACTION FAILED: INSUFFICIENT FUNDS```')
            await asyncio.sleep(5)
            await trn_fail.delete()
        if self.run == True:
            if newep > 0:
                if Nrcvep > 0:
                    if rcvep == 0:
                        await rcv.remove_roles(role)
                    users[str(sndid)]['amount'] = newep
                    users[str(rcvid)]['amount'] = Nrcvep
        else:
            await ctx.message.delete()

# filter message and penalty
async def filtered_msg_handling(self, reason, msg_author):
    guild = self.bot.get_guild(int(self.roles['SERVERID'][0]))
    user = guild.get_member(int(msg_author))
    role = guild.get_role(int(726446379823530015))
    users = retrieve_cache(self)

    #print("ADDED ROLE")

    user_bal = users[str(msg_author)]['amount']
    cost = round(self.filter_tax*user_bal, 2)
    user_bal = user_bal-cost
    users[str(msg_author)]['amount'] = user_bal
    duration = 30

    #print("CALCULATIONS DONE, ABOUT TO SEND EMBED")
    warn_msg = await self.text_chnl.send(f'``` {user} has been charged {cost} EP and muted for {reason}: {duration} seconds.```')

    await asyncio.sleep(duration)  # MUTE DURATION

    warn_done = True
    await user.remove_roles(role)
    await warn_msg.delete()
    return warn_done

async def link_punish(self, message):
    guild = self.bot.get_guild(int(self.roles['SERVERID'][0]))
    user = guild.get_member(int(message.author.id))
    role = guild.get_role(int(726446379823530015))

    await user.add_roles(role)                  
    users = retrieve_cache(self)
    user_bal = users[str(message.author.id)]['amount']
    cost = round((self.filter_tax*user_bal)*2, 2)
    user_bal = user_bal-cost
    users[str(message.author.id)]['amount'] = user_bal
    duration = 60
    warn = (f"```Links not allowed in this channel: {user} has been charged {cost} EP and muted for {duration} seconds.```")
    warn_msg = await message.channel.send(warn)

    await asyncio.sleep(duration)  # MUTE DURATION

    warn_done = True
    await user.remove_roles(role)
    await warn_msg.delete()
    return warn_done

# removes a role

async def role_rmv(self, guildid, roleid, userid):
    guild = self.bot.get_guild(guildid)
    role = guild.get_role(roleid)
    user = guild.get_member(int(userid))
    while role in user.roles:
        await user.remove_roles(role)

# adds a role,and delay(in seconds) defines how long until the role is removed,if delay is -1,the role is never removed

async def role_add(self, guildid, roleid, userid, delay):
    guild = self.bot.get_guild(guildid)
    role = guild.get_role(roleid)
    user = guild.get_member(userid)
    if delay != -1:
        await user.add_roles(role)
        await asyncio.sleep(delay)
        await user.remove_roles(role)
    else:
        await user.add_roles(role)

    return guild, role, user

# checks if users have a role,prioritises TRUE. seperate roleids with "#",takes a string

async def role_check(self, userid, guildid, roleid):
    guild = self.bot.get_guild(guildid)
    member = guild.get_member(userid)
    msg = str(roleid)
    role = msg.split('#')
    for i in role:
        role_to_check = guild.get_role(int(i))
        if role_to_check in member.roles:
            found = True
            break
        else:
            found = False
    return found

# makes a booster that gives the role for 24 hours,at the given cost (test amount is 5 seconds for now)

async def booster_create(self, ctx, cost, guildid, roleid, msg_payout, boostername):
    trn_run = False
    rcv = ''
    sndid = ctx.author.id
    await fast_retrieve(self, sndid)
    users = retrieve_cache(self)
    sndep = users[str(sndid)]['amount']
    sndep = sndep-cost
    if sndep > 0:
        trn_embed, reactor, trn_run = await transaction_embed(self, ctx, rcv, int(self.roles['SERVERID'][0]), '𝘽𝙊𝙊𝙎𝙏𝙀𝙍 𝙋𝙐𝙍𝘾𝙃𝘼𝙎𝙀', (boostername+" Purchase :**__-" + str(cost) + "EP__**, Balance: **__" + str(sndep) + "EP__**"))
    else:
        await ctx.send('```TRANSACTION FAILED: INSUFFICIENT FUNDS```', delete_after=3)

    if trn_run == True:
        if sndep > 0:
            userid = sndid
            users[str(sndid)]['amount'] = sndep
            await role_add(self, guildid, roleid, userid, -1)
            users[str(sndid)]['msg_decay'] = time.time()+self.booster_length
            users[str(sndid)]['msg_payout'] = msg_payout
            await db_dump_decay(self,userid)

    else:
        await ctx.message.delete()

# Embed functions

async def create_atlb_embed(self, db_bals):
    msg_string = f'{chr(173)}'
    guild = self.bot.get_guild(int(self.roles['SERVERID'][0]))
    lb_embed = discord.Embed(title="𝕬𝔩𝔩  𝕿𝔦𝔪𝔢 𝕷𝔢𝔞𝔡𝔢𝔯𝔟𝔬𝔞𝔯𝔡",
                             description="*The Ten Richest Members*", colour=discord.Colour.gold())
    lb_embed.set_footer(text='𝕿𝔥𝔢 𝕾𝔞𝔫𝔱𝔲𝔞𝔯𝔶 𝕺𝔣 𝕰𝔱𝔢𝔯𝔫𝔞𝔩𝔰',
                        icon_url='https://i.imgur.com/3zNEuX4.png')

    for userid, balance in dict(db_bals).items():
        ind = {k: i for i, k in enumerate(dict(db_bals).keys())}
        user = guild.get_member(userid)
        try:
            msg_string = msg_string + (f'`{int(ind[userid]) + 1}▐ `{user.mention}`- 𝕭𝔞𝔩𝔞𝔫𝔠𝔢: {balance}`\n')
        except:
            msg_string = msg_string + (f'`{int(ind[userid]) + 1}▐ {userid}- 𝕭𝔞𝔩𝔞𝔫𝔠𝔢: {balance}`\n')
        msg_string = msg_string + '\n'

    lb_embed.add_field(name=chr(173), value=msg_string)
    return lb_embed

async def create_wlb_embed(self, db_bals):
    msg_string = f'{chr(173)}'
    guild = self.bot.get_guild(int(self.roles['SERVERID'][0]))
    print('another test 3')
    lb_embed = discord.Embed(title="𝖂𝔢𝔢𝔨𝔩𝔶 𝕷𝔢𝔞𝔡𝔢𝔯𝔟𝔬𝔞𝔯𝔡",
                             description="*The Ten Highest Earners This Week*", colour=discord.Colour.gold())
    lb_embed.set_footer(text='𝕿𝔥𝔢 𝕾𝔞𝔫𝔱𝔲𝔞𝔯𝔶 𝕺𝔣 𝕰𝔱𝔢𝔯𝔫𝔞𝔩𝔰',
                        icon_url='https://i.imgur.com/3zNEuX4.png')

    print('another test 4')
    for userid, balance in dict(db_bals).items():
        ind = {k: i for i, k in enumerate(dict(db_bals).keys())}
        user = guild.get_member(userid)
        try:
            msg_string = msg_string + (f'`{int(ind[userid]) + 1}▐ `{user.mention}`- 𝕭𝔞𝔩𝔞𝔫𝔠𝔢: {balance}`\n')
        except:
            msg_string = msg_string + (f'`{int(ind[userid]) + 1}▐ {userid}- 𝕭𝔞𝔩𝔞𝔫𝔠𝔢: {balance}`\n')

        msg_string = msg_string + '\n'
        print('another test 5')
    print('another test 6')
    lb_embed.add_field(name=chr(173), value=msg_string)
    print('another test 7')
    return lb_embed

async def Peak_fnc(self, peak_duration, exit_embed=None):
    Peak_embed = discord.Embed(title="𝙋𝙀𝘼𝙆𝙏𝙄𝙈𝙀 𝘼𝘾𝙏𝙄𝙑𝘼𝙏𝙀𝘿",
                               description="Sending Messages Rewards EP⠀", colour=discord.Colour.green())
    Peak_embed.set_thumbnail(url='https://i.imgur.com/3zNEuX4.png')
    Peak_embed.add_field(name='Peaktime Will Last: ' +
                         str(peak_duration) + ' Minutes', value='🍀⠀⠀⠀⠀⠀')

    Peak_end_embed = discord.Embed(
        title="𝙋𝙀𝘼𝙆𝙏𝙄𝙈𝙀 𝙀𝙉𝘿𝙀𝘿", description="Messages Now Cost Ep⠀", colour=discord.Colour.dark_red())
    Peak_end_embed.set_thumbnail(url='https://i.imgur.com/3zNEuX4.png')
    Peak_end_embed.add_field(name='Peaktime Will Be Back.', value='🚫⠀⠀⠀⠀⠀')
    if exit_embed == None:
        return Peak_embed
    else:
        return Peak_end_embed

async def transaction_embed(self, ctx, rcv, guildid, title, costmsg):
    Warn_embed = discord.Embed(
        title=title, description=costmsg, colour=discord.Colour.purple())
    Warn_embed.set_thumbnail(url='https://i.imgur.com/3zNEuX4.png')
    Warn_embed.add_field(name='Confirm Transaction?', value='⚜⠀⠀⠀⠀⠀')

    new_embed = discord.Embed(title="𝙏𝙍𝘼𝙉𝙎𝘼𝘾𝙏𝙄𝙊𝙉 𝘿𝙀𝙉𝙄𝙀𝘿",
                              description="**Your Trasaction Has Been Denied As The User Is __Newpog__**", colour=discord.Colour.dark_purple())
    new_embed.set_thumbnail(url='https://i.imgur.com/3zNEuX4.png')
    new_embed.add_field(
        name="Transaction Can't Be Confirmed..", value='⚜⠀⠀⠀')

    async def addreactionss(message):
        await message.add_reaction('✔')
        await message.add_reaction('✖')

    def check(reaction, user):
        return user == ctx.author and str(reaction.emoji) == '✔'

    reactor = ctx.author.id
    user = ctx.author
    trn_embed = await ctx.send(embed=Warn_embed, delete_after=5)
    await addreactionss(trn_embed)
    try:
        reaction, user = await self.bot.wait_for('reaction_add', timeout=10, check=check)
    except Exception as e:
        print(str(e))
    else:
        trn_run = True

    return trn_embed, reactor, trn_run

# yes I know proxy doesn't mean proximity but shh
async def Bal_fnc(self, ctx, ctx_bal, proxy_bal_1=None, proxy_bal_1_user=None, proxy_bal_2=None, proxy_bal_2_user=None):
    if proxy_bal_1 == None:
        Bal_no_proxy = discord.Embed(title="𝘽𝘼𝙇𝘼𝙉𝘾𝙀", description="Your Account Balance Is: **__"+str(
            round(ctx_bal, 2))+" EP__**", colour=discord.Colour.teal())
        Bal_no_proxy.set_thumbnail(url='https://i.imgur.com/3zNEuX4.png')
        Bal_no_proxy.add_field(
            name='No Proximity Balances Found!', value='💸⠀⠀⠀⠀⠀')
        msg = await ctx.send(embed=Bal_no_proxy)
        await msg.delete(delay=15)

    elif proxy_bal_2 == None:
        Bal_1_proxy = discord.Embed(title="𝘽𝘼𝙇𝘼𝙉𝘾𝙀", description="Your Account Balance Is: **__"+str(
            round(ctx_bal, 2))+" EP__**", colour=discord.Colour.dark_teal())
        Bal_1_proxy.set_thumbnail(url='https://i.imgur.com/3zNEuX4.png')
        Bal_1_proxy.add_field(
            name='👤⠀`'+str(proxy_bal_1_user)+'`', value='💸⠀`'+str(proxy_bal_1)+' EP`')
        msg = await ctx.send(embed=Bal_1_proxy)
        await msg.delete(delay=15)

    else:
        Bal_2_proxy = discord.Embed(title="𝘽𝘼𝙇𝘼𝙉𝘾𝙀", description="Your Account Balance Is: **__"+str(
            round(ctx_bal, 2))+" EP__**", colour=discord.Colour.dark_teal())
        Bal_2_proxy.set_thumbnail(url='https://i.imgur.com/3zNEuX4.png')
        Bal_2_proxy.add_field(
            name='👤⠀`'+str(proxy_bal_1_user)+'`', value='💸⠀`'+str(proxy_bal_1)+' EP`')
        Bal_2_proxy.add_field(
            name='👤⠀`'+str(proxy_bal_2_user)+'`', value='💸⠀`'+str(proxy_bal_2)+' EP`')
        msg = await ctx.send(embed=Bal_2_proxy)
        await msg.delete(delay=15)

async def already_booster(self, ctx):
    boost_deny_embed = discord.Embed(
        title="𝙏𝙍𝘼𝙉𝙎𝘼𝘾𝙏𝙄𝙊𝙉 𝘿𝙀𝙉𝙄𝙀𝘿", description="**__You Cannot Buy A Booster__**", colour=discord.Colour.dark_red())
    boost_deny_embed.set_thumbnail(url='https://i.imgur.com/3zNEuX4.png')
    boost_deny_embed.add_field(
        name='🚫**Reason:**', value='*You Have A Booster Already.*')
    msg = await ctx.send(embed=boost_deny_embed)
    await msg.delete(delay=5)

# reaction functions

async def reactionassign(self, ctx, msg):
    async def addreactionss(message):
        await message.add_reaction('✔')
        await message.add_reaction('✖')

    reactor = ctx.author.id
    trn_embed = msg
    await addreactionss(trn_embed)

# calculates the cost of each command,modify cost_mul to change the cost!

def cost_calc(self, ctx, rcv, rcvid, sndid, cost_mul):
    users = retrieve_cache(self)
    sndep = users[str(sndid)]['amount']
    rcvep = users[str(rcvid)]['amount']
    rcvep = rcvep/100
    # defaults: 0.5 for nl, 0.1 for clear
    cost = cost_mul*(round(((rcvep))*100))
    newep = sndep-cost
    cost = round(cost, 2)
    sndep = round(sndep, 2)
    newep = round(newep, 2)

    return (sndep, newep, cost)

# calculates the cost of each transfer,modify cost_mul to change the cost!

def transfer_calc(self, ctx, val, rcv, cost_mul):
    sndid = ctx.author.id
    rcvid = rcv.id
    users = retrieve_cache(self)
    sndep = users[str(sndid)]['amount']
    rcvep = users[str(rcvid)]['amount']
    sndC = (int(val) * cost_mul)
    newep = (sndep-sndC)
    Nrcvep = int(rcvep)+int(val)
    return (sndid, rcvid, newep, Nrcvep, rcvep)


# Add a user to the streaks dictionary, user is removed after self.streak_decay seconds


async def add_up_streaks(self, userid, rcvid):
    try:
        mult = str(self.up_streaks[str(rcvid)]['Current Streak:'])
    except:
        mult = 1

    # setup streaks for user
    if int(mult) < 4:
        if str(rcvid) not in self.up_streaks.keys():
            self.up_streaks[str(rcvid)] = {}
            self.up_streaks[str(rcvid)]['Current Streak:'] = 1
        else:
            mult = int(mult) + 1
            self.up_streaks[str(rcvid)]['Current Streak:'] = mult
    else:
        mult = 4
        return mult

    return int(mult)


async def add_dn_streaks(self, userid, rcvid):
    try:
        mult = str(self.dwn_streaks[str(rcvid)]['Current Streak:'])
    except:
        mult = 1

    # setup streaks for user
    if int(mult) < 4:
        if str(rcvid) not in self.dwn_streaks.keys():
            self.dwn_streaks[str(rcvid)] = {}
            self.dwn_streaks[str(rcvid)]['Current Streak:'] = 1
        else:
            mult = int(mult) + 1
            self.dwn_streaks[str(rcvid)]['Current Streak:'] = mult
    else:
        mult = 4
        return mult

    return int(mult)


# Functions for playing with json data
async def create_user(self, users, user):
    if not str(user.id) in users:
        users[str(user.id)] = {}
        users[str(user.id)]['amount'] = 1000
        users[str(user.id)]['msg_payout'] = self.no_boost
        users[str(user.id)]['msg_decay'] = 'None'


async def assn_role(self, rolename, roleid):
    roles = self.roles
    id_found = False
    role_lengh = False
    if len(roleid) > 17:
        role_lengh = True
    else:
        print('INVALID ROLE ID')

    for x in roles:
        idcheck = roles[x]
        if roleid in idcheck:
            id_found = True
            break

    if id_found is False and role_lengh is True:
        roles[rolename] = [roleid]
    else:
        print('ERROR')

    with open(cogs_data+'roles.json', 'w') as f:
        json.dump(roles, f)


async def update_json(self, users, user, amount, message):
    val = int(users[str(user.id)]['amount'])
    if val <= 0:  # Ensure user doesnt go under 0
        return
    else:
        users[str(user.id)]['amount'] += amount  # Update data

    if val <= 0:  # Give a role when user runs out of currency
        guild = message.guild
        role = guild.get_role(int(self.roles['Ban'][0]))
        user = guild.get_member(user.id)
        print(user)
        print(role)
        await user.add_roles(role)
    if val > 0:  # Remove the role once user has currency
        guild = message.guild
        role = guild.get_role(int(self.roles['Ban'][0]))
        user = guild.get_member(user.id)
        await user.remove_roles(role)


# Cog end
def setup(bot):
    bot.add_cog(currency(bot))
