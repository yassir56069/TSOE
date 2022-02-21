from cogs.bal_cache import pgdb
import asyncpg
import asyncio
import time

whitelist = [
    'https://imgur.com',
    'https://64.media.tumblr.com',
    'https://preview.redd.it',
    'https://pbs.twimg.com/media/',
    'https://gfycat.com/',
    'https://tenor.com/view/'
]


async def db_addimg(ctx, link, name= None):
    found = False
    img_flag = False
    print(name)
    db = pgdb.retrieve_db()

                
    if link_flag(link) == True:
        count = await db.fetchval('SELECT COUNT(*) FROM imgs')

        if name == None:
            for links in whitelist:
                if links in link:
                    old_name = link.replace(links,'')[:32]
                    name = old_name

        if count != 0:
            imgs = await db.fetch('SELECT img_no , img_link FROM imgs')
            for img_no, img_link in dict(imgs).items():
                if link in img_link:
                    msg = (f"```LINK ALREADY EXISTS AT ID {img_no}```")
                    found = True
                    await ctx.send(msg, delete_after=5) 
                    break

                img_name = await db.fetch('SELECT img_no, img_name FROM imgs')
                if name in dict(img_name).values():
                    found = True
                    await ctx.send(f"```NAME IS ALREADY BEING USED BY ID {img_no}```", delete_after=5)
                    break 

        

        if found == False:
            await db.execute(f"""
                INSERT INTO imgs (img_name, img_link, img_submittor, date_of_submission )
                VALUES('{name}','{link}',{ctx.author.id},'{time.time()}');
                """)
            img_no = await db.fetchval(f"SELECT img_no FROM imgs where img_link = '{link}'")
            img_flag = True
            return img_flag
    else:
        await ctx.send(f"```LINK FROM UNAUTHORIZED SOURCE!```", delete_after=5)
        img_flag = False
        return img_flag

def link_flag(link):
    flag = False

    for links in whitelist:
        if links in link:
            flag = True

    return flag 
