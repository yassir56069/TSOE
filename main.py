import discord, os, json,asyncio, asyncpg
from discord.ext import commands
from os import path
from cogs.bal_cache import pgdb

#CONFIG
if path.exists("config.json") == False:
    with open('config.json', 'w') as configout:
        json.dump({
        "token": "",
        "prefix": "!",
        "owner": [350765965278969860]
         }, configout)
    print("[INFO] config.json generated!")
    quit()
else:
    with open("config.json") as f:
        config = json.load(f)

#Generate cogs_data directory if there is none
if path.exists("cogs_data") == False:
    os.mkdir("cogs_data")
    print("[INFO] cogs_data direcotry generated!")

#Cogs
initial_extensions = ['cogs.events',
                      'cogs.owner',
                      'cogs.commands',
                       'cogs.currency',
                       'cogs.chat_filter'
                       ]    


#Setup

intents= discord.Intents.all()
bot = commands.Bot(command_prefix=config.get("prefix"), help_command=None, case_insensitive=True, self_bot=False, intents=intents, owner=config.get("owner"))

#Loaading cogs

if __name__ == '__main__':
    for extension in initial_extensions:
        bot.load_extension(extension)


if config.get('token') == "":
    print("[ERROR] No token present!")
else:
    print("[INFO] Starting up and logging in...")
    loop = asyncio.get_event_loop()
    loop.run_until_complete(pgdb.run_db())
    bot.run(config.get("token"), bot=True, reconnect=True)


