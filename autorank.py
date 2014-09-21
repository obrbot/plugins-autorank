import asyncio
import logging

logger = logging.getLogger('obrbot')

channel_ranks_key = 'obrbot:plugins:autorank:ranks:{}'


@asyncio.coroutine
def get_ranks(event, channel=None):
    """
    :type event: obrbot.event.Event
    """

    if not channel:
        channel = event.channel
    key = channel_ranks_key.format(channel)

    raw_result = yield from event.async(event.db.hgetall, key)
    return raw_result
