import os,random, asyncio, json, time
from os import path
from cogs.owner import fileDir, cogs_data 
from functools import lru_cache
from lru import LRU
import asyncpg

class db():
    def __init__(self):
        '''Postgres Database Object'''
        self.credentials = {"user": "tsoe_admin", "password": '123getcool', "database": "tsoedb", "host": "127.0.0.1"}

    async def run_db(self):
        self.pool = await asyncpg.create_pool(**self.credentials)
        await self.pool.execute(f"""
                                CREATE TABLE IF NOT EXISTS users(
                                    userid bigint PRIMARY KEY, 
                                    balance bigint DEFAULT 1000, 
                                    weekly_bal bigint DEFAULT 1000
                                    );
                                CREATE TABLE IF NOT EXISTS imgs(
                                    img_no bigserial PRIMARY KEY,
                                    img_name text DEFAULT NULL,
                                    img_link text,
                                    img_submittor bigint,
                                    date_of_submission text
                                );
                                CREATE TABLE IF NOT EXISTS msgs(
                                    userid bigint PRIMARY KEY REFERENCES users,
                                    decay_date text DEFAULT 'None',
                                    payout integer DEFAULT -1 
                                );""")
        
        print("Database running...")

    def retrieve_db(self):
        return self.pool

#Balances_cache
def fetch_from_json(self,userid): #fetches user from json to store in cache, if not already in cache
    if str(userid) not in self.bal:
       users=json_read()
       if str(userid) not in users:
            users[str(userid)] = {}
            users[str(userid)]['amount'] = 1000
            users[str(userid)]['msg_decay']='None'
            users[str(userid)]['msg_payout']=self.no_boost
            json_write(users)
       val=users[str(userid)]['amount']
       self.bal[str(userid)] = {}
       self.bal[str(userid)]['amount']= val
    return userid

async def fast_retrieve(self, userid):
    if str(userid) not in self.bal:
        db = pgdb.retrieve_db()
        users = await db.fetch('SELECT userid, balance FROM users')
        if str(userid) not in dict(users).keys():
            await db_new(userid)

        self.bal[str(userid)] = {}
        self.bal[str(userid)]['amount'] = int (await db_fetch_bal(userid))
        self.bal[str(userid)]['msg_decay'] = await db_fetch_decay(userid)
        self.bal[str(userid)]['msg_payout'] = int (await db_fetch_payout(userid))
        
async def db_decay_data(self,userid):
    '''overwrite cache msgs data with database'''
    self.bal[str(userid)] = self.bal[str(userid)] 
    self.bal[str(userid)]['amount'] = self.bal[str(userid)]['amount'] 
    self.bal[str(userid)]['msg_decay'] = await db_fetch_decay(userid)
    self.bal[str(userid)]['msg_payout'] = int (await db_fetch_payout(userid))

async def db_dump_decay(self,userid):
    '''dump decay cache data into database'''
    db = pgdb.retrieve_db()
    await db.execute(f"""
                UPDATE msgs
                SET decay_date = '{self.bal[str(userid)]['msg_decay']}',
                    payout = {self.bal[str(userid)]['msg_payout']}
                WHERE userid = '{userid}';
                """) 

def retrieve_cache(self):
    return self.bal

def reveal_cache(self): #displays current cache
    print(self.bal)

def clear_cache(self):
    self.bal={}

#role cache
def role_ini(self):
    with open(cogs_data+'roles.json', 'r') as f:
        self.roles= json.load(f)

#peak_cache
def peak_ini(self):
    with open(cogs_data+'peak.json', 'r') as f:
        self.peak= json.load(f)

#Database access functions
async def db_read():
    db = pgdb.retrieve_db()
    users = await db.fetch('SELECT userid, balance FROM users')
    return users

async def db_new(userid):
    '''Adds a new user to database, including all default values'''
    db = pgdb.retrieve_db()
    try:
        await db.execute(f"""
                        INSERT INTO users (userid, balance, weekly_bal )
                        VALUES('{userid}','{1000}','{1000}');
                        """)

        await db.execute(f"""
                        INSERT INTO msgs (userid, decay_date, payout)
                        VALUES('{userid}','None',-1)
                        ;""")

    except asyncpg.UniqueViolationError or asyncpg.PostgresSyntaxError:
                pass

async def db_fetch_decay(userid):
    db = pgdb.retrieve_db()
    decay = await db.fetchval(f"SELECT decay_date FROM msgs WHERE userid = '{userid}'")
    return decay 

async def db_fetch_payout(userid):
    db = pgdb.retrieve_db()
    payout = await db.fetchval(f"SELECT payout FROM msgs WHERE userid = '{userid}'")
    return payout

async def db_fetch_bal(userid):
    db = pgdb.retrieve_db()
    bal = await db.fetchval(f"SELECT balance FROM users WHERE userid = '{userid}'")
    return int(bal)

#json read and write functions
def json_read():
    with open(cogs_data+"users.json", 'r') as f:
            users = json.load(f)
    return users 

def json_write(users):
    with open(cogs_data+"users.json", 'w') as f:
        json.dump(users, f)

def oldjson_read():
    with open(cogs_data+"C:/Users/hooss/Documents/TSOE User Backups/users.json", 'r') as f:
         users = json.load(f)
        

    return users 

def oldjson_write(users):
    with open(cogs_data+"C:/Users/hooss/Documents/TSOE User Backups/users.json", 'w') as f:
        json.dump(users, f)

#updating json
async def cache_sync(self,switch):
        while switch == True:
            await asyncio.sleep(5)
            users=json_read()
            for cache_key in self.bal.keys():
                for json_key in users:
                    if cache_key == json_key :
                        try:
                            users[str(json_key)]['amount'] = self.bal[str(cache_key)]['amount']
                            users[str(json_key)]['msg_decay']= self.bal[str(cache_key)]['msg_decay']
                            users[str(json_key)]['msg_payout']= self.bal[str(cache_key)]['msg_payout']
                            json_write(users)
                        except:
                            print("Cache Empty")

async def backup_cache_sync(self,switch):
        while switch == True:
            print("Backup JSON Synced!")
            await asyncio.sleep(10)
            users=json_read()
            oldjson_write(users)

pgdb = db()
