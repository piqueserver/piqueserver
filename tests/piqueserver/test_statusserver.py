from twisted.trial import unittest
from unittest.mock import Mock, patch
from aiohttp.test_utils import AioHTTPTestCase, unittest_run_loop
from aiohttp import web
import piqueserver.statusserver


class StatusSeverTest(AioHTTPTestCase):
    async def get_application(self):
        protocol = Mock()
        status_server = piqueserver.statusserver.StatusServer(protocol)
        return status_server.create_app()

    @unittest_run_loop
    async def test_json(self):
        state_fixture = {
            "serverIdentifier": "aos://914572903:32887",
            "serverName": "piqueserver instance",
            "serverVersion": 3,
            "serverUptime": 69.83471703529358,
            "gameMode": "ctf",
            "map": {
                "name": "classicgen #261969101",
                "version": "1.0",
                "author": "Tom Dobrowolski"
            },
            "scripts": [
                "piqueserver.scripts.rollback",
                "piqueserver.scripts.protect",
                "piqueserver.scripts.map_extensions",
                "piqueserver.scripts.disco",
                "piqueserver.scripts.votekick",
                "piqueserver.scripts.trusted",
                "piqueserver.scripts.ratio",
                "piqueserver.scripts.passreload",
                "piqueserver.scripts.blockinfo",
                "piqueserver.scripts.squad",
                "piqueserver.scripts.afk"
            ],
            "players": [],
            "maxPlayers": 32,
            "scores": {
                "currentBlueScore": 0,
                "currentGreenScore": 0,
                "maxScore": 10
            }
        }
        with patch('piqueserver.statusserver.current_state', return_value=state_fixture):
            resp = await self.client.request("GET", '/json')
            self.assertEqual(resp.status, 200)
            state = await resp.json()
            self.assertEqual(state, state_fixture)
