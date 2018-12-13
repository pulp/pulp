from aiohttp import web

from django.conf import settings

from .handler import Handler


handler = Handler()


async def server(*args, **kwargs):
    app = web.Application()
    app.add_routes([web.get(settings.CONTENT_PATH_PREFIX + '{path:.+}', handler.stream_content)])
    return app
