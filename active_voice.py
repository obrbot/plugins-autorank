import asyncio
from datetime import datetime, timedelta
import logging

from obrbot import hook
from obrbot.event import EventType

logger = logging.getLogger('obrbot')

channel_serve = "ChanServ"
use_channel_serve = True


@asyncio.coroutine
def get_active(event, channel, minutes):
    active_users = set()
    min_time = datetime.utcnow() - timedelta(minutes=minutes)
    for event_type, nick, *rest in (yield from channel.get_history(event, min_time)):
        if event_type in (EventType.message, EventType.action):
            active_users.add(nick.lower())
    return active_users


def set_voice(conn, channel, user, voice):
    """
    :type conn: obrbot.connection.Connection | obrbot.clients.irc.IrcConnection
    :type channel: obrbot.connection.Channel
    :type user: obrbot.connection.User
    :type voice: bool
    """
    if voice and 'v' not in user.mode:
        user.mode += 'v'
    if not voice and 'v' in user.mode:
        user.mode.replace('v', '')

    if use_channel_serve:
        command = "VOICE" if voice else "DEVOICE"
        conn.message(channel_serve, "{} {} {}".format(command, channel.name, user.nick))
    else:
        mode = "+v" if voice else "-v"
        conn.send("MODE {} {} {}".format(channel.name, mode, user.nick))


@asyncio.coroutine
def check_voices(event, conn, channel):
    """
    :type event: obrbot.event.Event
    :type conn: obrbot.connection.Connection
    :type channel: obrbot.connection.Channel
    """
    active_users = yield from get_active(event, channel, 1440)
    for user in channel.users.values():
        if 'v' in user.mode:
            if user.nick.lower() not in active_users:
                set_voice(conn, channel, user, True)
        else:
            if user.nick.lower() in active_users:
                set_voice(conn, channel, user, False)


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
    if event.channel is None:
        return
    user = event.channel.users[event.nick]
    if 'v' not in user.mode:
        set_voice(conn, event.channel, user, True)


def get_all_channels(bot):
    """
    :type bot: obrbot.bot.ObrBot
    """
    for conn in bot.connections:
        for channel in conn.channels.values():
            yield conn, channel


@asyncio.coroutine
@hook.on_start()
def start_hourly_check(event):
    """
    :type event: obrbot.event.Event
    """
    asyncio.async(hourly_check(event), loop=event.loop)


@asyncio.coroutine
def hourly_check(event):
    """
    :type event: obrbot.event.Event
    """
    while True:
        yield from asyncio.sleep(3600, loop=event.loop)
        yield from asyncio.gather(*(check_voices(event, conn, channel)
                                    for conn, channel in get_all_channels(event.bot)), loop=event.loop)
