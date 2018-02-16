
import re
import aioredis
import logging

from asyncqlio import DatabaseInterface

log = logging.getLogger('silph-link.database')


class Database(object):
    def __init__(self, redis_url, mysql_url, loop):
        self.loop = loop
        self.redis_url = redis_url
        self.mysql_url = mysql_url
        self.loop.create_task(self.create())
        self.redis_address = parse_redis_url(redis_url)

    async def create(self):
        log.debug('Creating Redis instance')
        self.redis = await aioredis.create_redis(
            self.redis_address,
            encoding='utf8',
            db=0, #lol
        )

        log.debug('Creating MySQL instance')
        self.mysql = DatabaseInterface(self.mysql_url)
        await self.mysql.connect()

        from silph.models.base import Table

        log.debug('Binding MySQL to ORM')
        self.mysql.bind_tables(Table.metadata)

    async def close(self):
        await self.mysql.close()
        await self.redis.quit()


def parse_redis_url(redis_url):
    pattern = r'redis:\/\/([a-zA-Z0-9.]*):?([0-9]*)?'
    result = re.match(pattern, redis_url).groups()
    if result[1]:
        return (result[0], int(result[1]))
    else:
        return (result[0], 6379)
