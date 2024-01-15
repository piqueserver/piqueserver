import json
import time

from piqueserver import bansubscribe
from piqueserver.banpublish import PublishServer
from typing import Any, Dict, List, Union
from unittest.mock import Mock
import pytest
from aiohttp import web

from piqueserver.networkdict import NetworkDict


class test_server():
    bans = None
    server = None

    def __init__(self):
        ban_list = [
            ["Danko", "187.16.185.94", ": AIMBOT", time.time() + 50000],
            ["Danko", "94.193.254.118", ": ESP", time.time() - 50000],
            ["Danko2", "187.16.185.95", ": AIMBOT", time.time() + 50000],
        ]
        self.bans = NetworkDict()
        self.bans.read_list(ban_list)
        self.server = PublishServer(self, 9191)  # This one is just for

    def listenTCP(self, *arg, **kw):
        pass


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
async def test_time_ban():
    server = test_server()
    data = server.server.json_bans
    list = json.loads(data)
    datalist = []
    for element in list:
        dataDict = {}
        dataDict["ip"] = element["ip"]
        dataDict["name"] = "Danko"
        dataDict["reason"] = element["reason"].split(":")[1].strip()
        datalist.append(dataDict)
    print(datalist)
    site = await mock_server(datalist, 9192)
    await site.start()
    banm = bansubscribe.BanManager(Mock())
    banm.urls = [("http://localhost:9192/", [""])]
    await banm.update_bans()
    print(banm.bans.make_list())
    assert banm.get_ban("187.16.185.93") is None
    assert banm.get_ban("187.16.185.94") is not None
    assert banm.get_ban("187.16.185.95") is not None
    assert banm.get_ban("94.193.254.118") is None
    await site.stop()
