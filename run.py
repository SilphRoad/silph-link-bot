# This bot is super simple, and it exists for one reason and one reason only.
# Telegram's Login Widget is dumb. It's a widget that provides no control over
# styling or event workflow. It embeds an iframe on the site. It requires a lot
# of javascript and doesn't implement and of the tried and true handshake protocols
# like OpenID, OpenConnect, or OAuth. As a result we'll make our own identity
# tool, where a code is provided to authenticated users on a webpage - they enter
# that code into the bot and the bot confirms the Telegram identity.

import os
import logging
import asyncio

from bot import SilphLinkBot


debug = os.getenv('DEBUG')

if debug:
    logging.basicConfig(level=logging.DEBUG)
else:
    logging.basicConfig(level=logging.INFO)

token = os.getenv('TELEGRAM_TOKEN')
redis_url = os.getenv('REDIS_URL')
db_url = os.getenv('MYSQL_URL').format(os.getenv('DB_PASS'))

loop = asyncio.get_event_loop()

bot = SilphLinkBot(
    redis_url=redis_url,
    mysql_url=db_url,
    api_token=token,
    loop=loop,
)

try:
    bot.start()
except KeyboardInterrupt:
    print('Good night, sweet prince')
    loop.run_until_complete(bot.stop())
