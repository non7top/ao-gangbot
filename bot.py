# -*- coding: utf8 -*-
import discord
from discord.ext import commands

from datetime import datetime

from sqlite3 import OperationalError
import aiosqlite3

from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

GANG_DB="gangbot.db"

bot = commands.Bot(command_prefix='!')

class gangbot_db:
    def __init__(self, db_file):
        self.db_file = db_file
        return None

    async def _insert(self, query):
        print(query)
        async with aiosqlite3.connect(self.db_file) as db:
            cursor = await db.execute(query)
            ret = cursor.lastrowid
            await db.commit()
            await cursor.close()
            await db.close()
        return ret

    async def _select(self, query):
        print(query)
        async with aiosqlite3.connect(self.db_file) as db:
            async with db.cursor() as cursor:
                await cursor.execute(query)
                r = await cursor.fetchall()
        return r

    async def _loot_start(self, loot_name, start_time, guild):
        query="INSERT INTO gang_session (loot, start_time, guild) values ('{}', '{}', '{}');".format( \
                loot_name, start_time, guild)
        return await self._insert(query)

    async def _set_money(self, session, guild, money):
        query="UPDATE gang_session SET money='{}' WHERE id='{}' and guild='{}';".format( \
                money, session, guild)
        return await self._insert(query)

    async def _set_pay(self, member_id, session_id):
        query="UPDATE gang_members SET got_money='1' where id='{}';".format( \
                member_id)
        return await self._insert(query)

    async def _loot_join(self, session_id, user_id, start_time):
        query="INSERT INTO gang_members (session_id, start_time, user_id) values ('{}', '{}', '{}');".format( \
                session_id, start_time, user_id)
        return await self._insert(query)

    async def _loot_leave(self, session_id, user_id, stop_time):
        query="UPDATE gang_members SET stop_time='{}' WHERE ifnull(stop_time, '')='' AND session_id='{}' AND user_id='{}';".format( \
                stop_time, session_id, user_id)
        return await self._insert(query)

    async def _loot_stop(self, loot_name, stop_time, guild):
        query="UPDATE gang_session SET stop_time='{}' WHERE ifnull(stop_time, '')='' AND id='{}' AND guild='{}';".format( \
                stop_time, loot_name, guild )
        return await self._insert(query)

    async def _loot_list(self, loot_name, guild):
        query="SELECT * FROM gang_session WHERE ifnull(stop_time, '')='' AND guild='{}';".format( \
                guild )
        return await self._select(query)

    async def _loot_member_details_by_name(self, session_id, user_id):
        query="SELECT * FROM gang_members WHERE session_id='{}' AND user_id='{}'".format( \
                session_id, user_id)
        return await self._select(query)

    async def _get_sess(self, loot_name, guild):
        # Loot can be id or name
        try:
            _id=int(loot_name)
            query="SELECT * FROM gang_session WHERE id='{}' and guild='{}';".format( \
                _id, guild)
        except:
            #query="SELECT * FROM gang_session WHERE ifnull(stop_time, '')='' AND guild='{}' AND loot='{}';".format( \
            query="SELECT * FROM gang_session WHERE guild='{}' AND loot='{}' ORDER BY id DESC LIMIT 1;".format( \
                guild, loot_name)

        return await self._select(query)

    async def _loot_members(self, session_id):
        query="SELECT * FROM gang_members WHERE session_id='{}';".format( \
                session_id)
        return await self._select(query)

gb=gangbot_db(GANG_DB)

async def action_show_help(ctx):
    help_msg='''Usage:
        session_id - [##] number in square brackets before loot name
        player_id - [##] number in square brackets before player name in (!g show ##)
        !g list - list active gang sessions
        !g start loot1 - start gang session with name loot1, will output session id
        !g stop loot1|session_id - stop session, will part remaining memebrs
        !g show loot1|session_id - show details about session
        !g join loot1|session_id - join gang session
        !g leave loot1|session_id - leave session
        !g sold session_id - set money earned form selling that loot
        !g pay player_id session_id - set that player got his money, do not abuse
        '''
    await ctx.author.send(help_msg)

async def action_loot_start(ctx, loot_name="active"):
    print("Starting " + loot_name)

    # If loot_name = default (active) then error out
    if loot_name == 'active':
        await ctx.send("Usage !g start LOOT_NAME (i.e. !g start loot1) ")
        return

    _time = datetime.now()
    _pp_time=_time.strftime('%d %B %Y, %H:%M')

    session_id = await gb._loot_start(loot_name,_time,ctx.guild.id)
    await ctx.send("Registered [{}] {}".format(session_id, loot_name))

    await action_loot_join(ctx, loot_name)

async def action_loot_join(ctx, loot_name):
    _time = datetime.now()
    print("Add new member " + str(ctx.author.display_name) + " to " + loot_name)
    # Get the id of the latest loot with given name
    sess_id = await gb._get_sess(loot_name, ctx.guild.id)

    # Can't join inactive session
    if sess_id[0][4] != None:
        await ctx.send("Can't join ended session >> {} ".format(ctx.author.display_name))
        return

    # Can't join twice, unless other sessions are inactive
    _details = await gb._loot_member_details_by_name(sess_id[0][0], ctx.author.display_name)
    for d in _details:
        if d[3] == None: #there is an active session
            await ctx.send("Can't join twice >> {} ".format(ctx.author.display_name))
            return


    _id = await gb._loot_join(sess_id[0][0], str(ctx.author.display_name),_time)

    msg = "Registered `[{}] {}` in [{}] {}".format(_id, str(ctx.author.display_name), sess_id[0][0], loot_name)
    await ctx.author.send(msg)

async def action_loot_leave(ctx, loot_name):
    _time = datetime.now()
    print("Parting _" + str(ctx.author.display_name) + "_ from " + loot_name)
    # Get the id of the latest loot with given name
    sess_id = await gb._get_sess(loot_name, ctx.guild.id)

    # Can't leave inactive session
    if sess_id[0][4] != None:
        await ctx.send("Can't leave ended session >> {} ".format(ctx.author.display_name))
        return

    await gb._loot_leave(sess_id[0][0], str(ctx.author.display_name),_time)

    msg = str(ctx.author.display_name) + " left " + loot_name

async def action_loot_stop(ctx, loot_name):
    print("Stopping " + loot_name)
    _time = datetime.now()


    # Part all members first
    sess_id = await gb._get_sess(loot_name, ctx.guild.id)
    members = await gb._loot_members(sess_id[0][0])
    for m in members:
        if m[3] == None:
            await gb._loot_leave(sess_id[0][0], m[4],_time)

    await gb._loot_stop(sess_id[0][0],_time,ctx.guild.id)
    await action_loot_show(ctx, loot_name)

async def action_loot_list(ctx):
    print("Listing active loots")
    _list=await gb._loot_list("active",ctx.guild.id)
    _now = datetime.now()

    embed=discord.Embed(title="Active gang sessions", description="Слава Украине!", color=0x00ff40)
    for gang in _list:

        _time=datetime.strptime(gang[3], '%Y-%m-%d %H:%M:%S.%f')
        _duration=(_now - _time).total_seconds()
        hours, remainder = divmod(_duration, 3600)
        minutes, seconds = divmod(remainder, 60)
        duration = '{:1.0f}h{:1.0f}m'.format(hours,minutes)

        members = await gb._loot_members(gang[0])

        value = '{} with {} ppl'.format(duration, len(members))

        _name="[{}] {}".format(gang[0], gang[2])
        embed.add_field(name=_name, value=value, inline=False)
    await ctx.send(embed=embed)

async def date_from_str(k):
    return datetime.strptime(k, '%Y-%m-%d %H:%M:%S.%f')

async def session_length(start, stop):
    # accept 2 datetime objects
    # return seconds
    #print("Start type: " + str(type(start)) + str(start))
    #print("Stop type: " + str(type(stop)) + str(stop))
    if isinstance(start, str):
        start=await date_from_str(start)

    if isinstance(stop, str):
        stop=await date_from_str(stop)

    return int((stop - start).total_seconds())

async def pretty_length(lenght):
    # accept int seconds
    # return 1h30m
    hours, remainder = divmod(lenght, 3600)
    minutes, seconds = divmod(remainder, 60)
    duration = '{:1.0f}h{:1.0f}m'.format(hours,minutes)
    return duration

async def action_loot_sold(ctx, loot_name, money):
    # FIXME check that money is int
    session = await gb._get_sess(loot_name, ctx.guild.id)

    await gb._set_money(session[0][0], ctx.guild.id, money)

    await ctx.send("Loot [**{}**] {} sold for **{}**! You can now get your money for participation.".format( \
            session[0][0], session[0][2], money))
    await action_loot_show(ctx, session[0][0])

async def action_loot_pay(ctx, member_id, session_id):

    session = await gb._get_sess(session_id, ctx.guild.id)
    print(session)
    if len(session) == 0:
        await ctx.send("Gang session {} was not found for your guild".format( \
                session_id))
        return

    await gb._set_pay(member_id, session_id)


async def action_loot_show(ctx, loot_name):
    print("Show loot " + str(loot_name))
    # Can show using int id and name
    session = await gb._get_sess(loot_name, ctx.guild.id)

    # If session hasn't ended, use current time as stop_time
    _time = datetime.now()
    if session[0][4] == None:
        stop_time=_time
    else:
        stop_time=session[0][4]

    print("Stop time: " + str(stop_time))

    duration = await session_length(session[0][3], stop_time)
    pretty_duration = await pretty_length(duration)

    sess_id = session[0][0]
    session_name = session[0][2]
    money = session[0][5]
    if money == None:
        money="not sold yet"

    members = await gb._loot_members(sess_id)

    _name = "[{}] {} > {} <".format(sess_id, session_name, str(money))
    description = "{} with {}ppl".format(pretty_duration, len(members))

    embed=discord.Embed(title=_name, description=description, color=0x369dc9)

    # Calculate total time players spent in this loot session
    total_time=0
    for m in members:
        _start=m[2]
        _stop=m[3]
        if _stop == None:
            _stop = _time
        _duration = await session_length(_start, _stop)
        total_time = ( total_time + _duration )

    print(members)
    for m in members:
        _start=m[2]
        _stop=m[3]
        if _stop == None:
            _stop = _time
        _duration = await session_length(_start, _stop)
        share = (_duration/total_time * 100 )
        pretty_duration = await pretty_length(_duration)

        name="[{}] {}".format(m[0], m[4])


        _share = "{:.0f}% {}".format(share, pretty_duration)
        # if member stop_time==None
        if m[3] == None:
            print("active")
            _share = "{} **active**".format(_share)


        # If sold, add money share
        if money != "not sold yet":
            _share2 = ( int(share) / 100 * int(money) )
            got_money=''
            if m[5] == 1:
                got_money=':white_check_mark:'
            _share = "{}   **{:.0f}** {}".format(_share, _share2, got_money)

        embed.add_field(name=name, value=_share, inline=False)

    await ctx.send(embed=embed)


@bot.command(name='g', help='manage gang session && loot', no_pm=True)
async def loot(ctx, *args):
    if ctx.guild == None:
        await ctx.send("Personal messages not allowed")
        return

    print(args)
    try:
        loot_action=args[0]
    except IndexError:
        await action_show_help(ctx)
        return

    try:
        loot_name=args[1]
    except:
        pass

    if loot_action == "start":
        await action_loot_start(ctx, loot_name)
    elif loot_action == "stop":
        await action_loot_stop(ctx, loot_name)
    elif loot_action == "join":
        await action_loot_join(ctx, loot_name)
    elif loot_action == "leave":
        await action_loot_leave(ctx, loot_name)
    elif loot_action == "list":
        await action_loot_list(ctx)
    elif loot_action == "show":
        await action_loot_show(ctx, loot_name)
    elif loot_action == "sold":
        await action_loot_sold(ctx, loot_name, args[2])
    elif loot_action == "pay":
        await action_loot_pay(ctx, args[1], args[2])
    else:
        await ctx.send("Usage: !g start|stop|join|leave loot3|id")

@bot.event
async def on_ready():
    print('Logged in as')
    print(bot.user.name)
    print(bot.user.id)
    print(bot.guilds)
    print('------')


bot.run(TOKEN)
