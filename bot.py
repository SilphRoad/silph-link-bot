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
import signal

from aiotg import Bot, Chat
from silph.models import User, UserLogin

from database import Database


debug = os.getenv('DEBUG')

if debug:
    logging.basicConfig(level=logging.DEBUG)
else:
    logging.basicConfig(level=logging.INFO)


def cleanup():
    raise KeyboardInterrupt()


log = logging.getLogger('silph-link.bot')


class SilphLinkBot(Bot):

    def __init__(self, *args, **kwargs):
        self.redis_url = kwargs.get('redis_url')
        self.mysql_url = kwargs.get('mysql_url')

        self._loop = kwargs.get('loop', asyncio.get_event_loop())

        botargs = {
            'api_token': kwargs.get('api_token'),
        }

        super().__init__(**botargs)
        self.db = Database(self.redis_url, self.mysql_url, self._loop)

        self.default(self.code_check)
        self.add_command('/start', self.greet)

        for signame in ('SIGINT', 'SIGTERM'):
            self._loop.add_signal_handler(getattr(signal, signame), cleanup)

    def start(self):
        self._loop.run_until_complete(self.loop())

    async def loop(self):
        self.me = await self.get_me()
        log.info(
            'Hello, I am {} bot ID {}'.format(self.me['username'], self.me['id'])
        )
        await super().loop()

    async def greet(self, chat: Chat, match):
        user_id = chat.sender['id']
        user = None

        async with self.db.mysql.get_session() as sess:
            ul = await sess.select(UserLogin).where(UserLogin.vendor == 4,
                                                    UserLogin.identifier == user_id).first()
            if ul:
                user = await sess.select(User).where(User.id == ul.user).first()

        if user:
            txt = (
               'Howdy Traveler! This Telegram account is already linked to https://sil.ph/{}. If '
               'this is not you, email team@thesilphroad.com'
            )

            await chat.send_text(txt.format(user.name))

        msg = (
            'Hello traveler! @SilphLinkBot can link your Telegram account to your Travelers Card. '
            'If you already have a code for linking your Telegram account to a Silph Traveler '
            'Card enter it now! (e.g. `xxxxxx`)\n\nIf you require a code, first login to your '
            'Silph Road account and select EDIT on your Travelers Card. Once there click the '
            'Telegram icon to get your connect code.'
        )

        await chat.send_text(msg, parse_mode='markdown')

    async def code_check(self, chat: Chat, message):
        code = message['text']

        if chat.is_group():
            return

        if not code:
            return

        user_id = await self.db.redis.get('silph.ai:telegram:link:{}'.format(code))

        if not user_id:
            fail_txt = (
                'The code you have provided is incorrect. Please head to your travelers card and '
                'generate a new one',
            )

            return await chat.send_text(fail_txt)

        async with self.db.mysql.get_session() as sess:
            ul = await sess \
                .select(UserLogin) \
                .where(UserLogin.user == user_id, UserLogin.vendor == 4) \
                .first()

            if ul:
                return await chat.send_text(
                    'You have already linked a Telegram account to this travelers card',
                )

            tg_login = UserLogin(
                vendor=4,
                identifier=chat.sender['id'],
                username=chat.sender['username'],
                user=user_id
            )

            await sess.save(tg_login)

        await self.send_text('Telegram <-> Silph Traveler Card link successful!')


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
    bot.stop()
