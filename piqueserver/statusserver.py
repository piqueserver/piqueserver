# Copyright (c) junk/someonesomewhere 2011.

# This file is part of pyspades.

# pyspades is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# pyspades is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with pyspades.  If not, see <http://www.gnu.org/licenses/>.

import asyncio
from twisted.internet.defer import Deferred
import aiohttp
from aiohttp import web
from multidict import MultiDict

from jinja2 import Environment, PackageLoader
import json
import time
from PIL import Image
from io import BytesIO
from aiohttp.abc import AbstractAccessLogger
from twisted.logger import Logger
from piqueserver.utils import as_deferred

from piqueserver.config import config, cast_duration

status_server_config = config.section("status_server")
host_option = status_server_config.option("host", "0.0.0.0")
port_option = status_server_config.option("port", 32886)
logging_option = status_server_config.option("logging", False)
interval_option = status_server_config.option(
    "update_interval", default="1min", cast=cast_duration)
scripts_option = config.option("scripts", [])


class AccessLogger(AbstractAccessLogger):

    def log(self, request, response, time):
        self.logger.info(
            "{remote} {method} {url}: {status} {time:0.2f}ms -- {ua}",
            remote=request.remote,
            ua=request.headers["User-Agent"],
            method=request.method,
            url=request.url,
            time=time * 1000,
            status=response.status)


async def set_default_headers(request, response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Credentials'] = 'true'


def current_state(protocol):
    """Gathers data on current server/game state from protocol class"""
    players = []

    for player in protocol.players.values():
        player_data = {
            'name': player.name,
            'latency': player.latency,
            'client': player.client_string,
            'kills': player.kills,
            'team': player.team.name
        }

        players.append(player_data)

    dictionary = {
        "serverIdentifier": protocol.identifier,
        "serverName": protocol.name,
        "serverVersion": protocol.version,
        "serverUptime": time.time() - protocol.start_time,
        "gameMode": protocol.game_mode_name,
        "map": {
            "name": protocol.map_info.name,
            "version": protocol.map_info.version,
            "author": protocol.map_info.author
        },
        "scripts": scripts_option.get(),
        "players": players,
        "maxPlayers": protocol.max_players,
        "scores": {
            "currentBlueScore": protocol.blue_team.score,
            "currentGreenScore": protocol.green_team.score,
            "maxScore": protocol.max_score}
    }

    return dictionary


class StatusServer:
    def __init__(self, protocol):
        self.protocol = protocol
        self.last_update = None
        self.last_map_name = None
        self.cached_overview = None
        env = Environment(loader=PackageLoader('piqueserver.web'))
        self.status_template = env.get_template('status.html')

    async def json(self, request):
        state = current_state(self.protocol)
        return web.json_response(state)

    @property
    def current_map(self):
        return self.protocol.map_info.name

    def update_cached_overview(self):
        """Updates cached overview"""
        overview = self.protocol.map.get_overview(rgba=True)
        image = Image.frombytes('RGBA', (512, 512), overview)
        data = BytesIO()
        image.save(data, 'png')
        self.cached_overview = data.getvalue()
        self.last_update = time.time()
        self.last_map_name = self.protocol.map_info.name

    async def overview(self, request):
        # update cache on a set interval or map change or initialization
        if (self.cached_overview is None or
                self.last_map_name != self.current_map or
                time.time() - self.last_update > interval_option.get()):
            self.update_cached_overview()

        return web.Response(body=self.cached_overview,
                            content_type='image/png')

    async def index(self, request):
        rendered = self.status_template.render(server=self.protocol)
        return web.Response(body=rendered, content_type='text/html')

    def create_app(self):
        app = web.Application()
        app.on_response_prepare.append(set_default_headers)
        app.add_routes([
            web.get('/json', self.json),
            web.get('/overview', self.overview),
            web.get('/', self.index)
        ])
        return app

    async def listen(self):
        """Starts the status server on configured host/port"""
        app = self.create_app()
        logger = Logger() if logging_option.get() else None
        log_class = AccessLogger if logging_option.get() else None
        runner = web.AppRunner(app,
                               access_log=logger,
                               access_log_class=log_class)
        await as_deferred(runner.setup())
        site = web.TCPSite(runner, host_option.get(), port_option.get())
        await as_deferred(site.start())

        # TODO: explain why we do this
        await Deferred()
