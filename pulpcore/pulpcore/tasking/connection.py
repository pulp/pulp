from django.conf import settings  # noqa
from redis import Redis

_conn = None


def get_redis_connection():
    global _conn

    if _conn is None:
        _conn = Redis(host=settings.REDIS['host'], port=settings.REDIS['port'],
                      password=settings.REDIS['password'])
    return _conn
