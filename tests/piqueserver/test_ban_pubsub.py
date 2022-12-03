import asyncio
from typing import Any, Dict
from unittest.mock import Mock

import pytest
from aiohttp import web

from piqueserver import bansubscribe


async def mock_server(data: Dict[Any, Any], port: int):
    async def handler(request):
        return web.json_response(data)
    app = web.Application()
    app.router.add_get('/', handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, 'localhost', port)
    return site

@pytest.mark.asyncio
async def test_ban_manger_update_bans():
    data = [
        {"ip":"189.5.43.17","name":"GreaseMonkey","reason":"Cheating"},
        {"ip":"177.142.42.13","name":"Danko","reason":"Cheating"},
    ]
    site = await mock_server(data, 9191)
    await site.start()

    banm = bansubscribe.BanManager(Mock())
    banm.urls = [("http://localhost:9191/", ["Danko"])]
    await banm.update_bans()
    assert banm.get_ban("189.5.43.17") is not None
    assert banm.get_ban("177.142.42.13") is None
    await site.stop()
