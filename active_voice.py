import asyncio
from datetime import datetime, timedelta
import logging

from obrbot import hook
from obrbot.event import EventType

logger = logging.getLogger('obrbot')


@asyncio.coroutine
def get_active(event, channel, minutes):
    active_users = set()
    min_time = datetime.utcnow() - timedelta(minutes=minutes)
    for event_type, nick, *rest in (yield from channel.get_history(event, min_time)):
        if event_type in (EventType.message, EventType.action):
            active_users.add(nick.lower())
    return active_users


@asyncio.coroutine
def check_voices(event, conn, channel):
    active_users = yield from get_active(event, channel, 1440)
    for user in channel.users.values():
        if 'v' in user.mode:
            if user.nick.lower() not in active_users:
                conn.send("MODE {} -v {}".format(channel.name, user.nick))
            user.mode.replace('v', '')
        else:
            if user.nick.lower() in active_users:
                conn.send("MODE {} +v {}".format(channel.name, user.nick))
            user.mode += 'v'


@asyncio.coroutine
@hook.irc_raw('004')
def on_connected(event, conn):
    """
    :type event: obrbot.event.Event
    :type conn: obrbot.clients.irc.IrcConnection
    """
    yield from asyncio.gather(*(check_voices(event, conn, channel) for channel in conn.channels.values()),
                              loop=event.loop)

@asyncio.coroutine
@hook.event(EventType.join)
def on_join(event, conn):
    """
    :type event: obrbot.event.Event
    :type conn: obrbot.clients.irc.IrcConnection
    """
    if event.nick == conn.bot_nick:
        yield from check_voices(event, conn, event.channel)
@asyncio.coroutine
@hook.event(EventType.message, EventType.action)
def on_message(event, conn):
    """
    :type event: obrbot.event.Event
    :type conn: obrbot.clients.irc.IrcConnection
    """
    user = event.channel.users[event.nick]
    if 'v' not in user.mode:
        conn.send("MODE {} +v {}".format(event.channel.name, user.nick))

def get_all_channels(event):
    """
    :type event: obrbot.event.Event
    """
    for conn in event.bot.connections:
        for channel in conn.channels.values():
            yield conn, channel

@asyncio.coroutine
@hook.on_start()
def hourly_check(event):
    """
    :type event: obrbot.event.Event
    """
    while True:
        yield from asyncio.sleep(3600, loop=event.loop)
        yield from asyncio.gather(*(check_voices(event, conn, channel) for conn, channel in get_all_channels(event)),
                                  loop=event.loop)