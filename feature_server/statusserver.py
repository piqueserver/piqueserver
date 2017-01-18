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

from twisted.internet import reactor
from twisted.web import server
from twisted.web.resource import Resource
from string import Template
from PIL import Image
from jinja2 import Environment, PackageLoader
import json
from cStringIO import StringIO

OVERVIEW_UPDATE_INTERVAL = 1 * 60 # 1 minute

class CommonResource(Resource):
    protocol = None
    isLeaf = True

    def __init__(self, parent):
        self.protocol = parent.protocol
        self.env = parent.env
        self.parent = parent
        Resource.__init__(self)

class JSONPage(CommonResource):
    def render_GET(self, request):
        protocol = self.protocol

        players = []

        for player in protocol.players.values():
            player_data = {}
            player_data['name'] = player.name
            player_data['latency'] = player.latency
            player_data['kills'] = player.kills
            player_data['team'] = player.team.name

            players.append(player_data)

        dictionary = {
            "serverName" : protocol.name,
            "serverVersion": protocol.version,
            "serverUptime" : reactor.seconds() - protocol.start_time,
            "gameMode" : protocol.game_mode_name,
            "map" : {
                "name": protocol.map_info.name,
                "version": protocol.map_info.version,
                "author": protocol.map_info.author
            },
            "scripts" : protocol.config.get("scripts", []),
            "players" : players,
            "maxPlayers": protocol.max_players,
            "scores" : {
                "currentBlueScore": protocol.blue_team.score,
                "currentGreenScore": protocol.green_team.score,
            "maxScore": protocol.max_score}
            }

        return json.dumps(dictionary)

class StatusPage(CommonResource):
    def render_GET(self, request):
        protocol = self.protocol
        status = self.env.get_template('status.html')
        return status.render(server = self.protocol, reactor = reactor).encode(
            'utf-8', 'replace')


class MapOverview(CommonResource):
    def render_GET(self, request):
        overview = self.parent.get_overview()
        request.setHeader("content-type", 'png/image')
        request.setHeader("content-length", str(len(overview)))
        if request.method == "HEAD":
            return ''
        return overview
    render_HEAD = render_GET

class StatusServerFactory(object):
    last_overview = None
    last_map_name = None
    overview = None
    def __init__(self, protocol, config):
        self.env = Environment(loader = PackageLoader('web'))
        self.protocol = protocol
        root = Resource()
        root.putChild('json', JSONPage(self))
        root.putChild('', StatusPage(self))
        root.putChild('overview', MapOverview(self))
        site = server.Site(root)

        logging = config.get('logging', False)
        site.noisy = logging
        if not logging:
            site.log = lambda _: None

        protocol.listenTCP(config.get('port', 32886), site)

    def get_overview(self):
        current_time = reactor.seconds()
        if (self.last_overview is None or
        self.last_map_name != self.protocol.map_info.name or
        current_time - self.last_overview > OVERVIEW_UPDATE_INTERVAL):
            overview = self.protocol.map.get_overview(rgba = True)
            image = Image.frombytes('RGBA', (512, 512), overview)
            data = StringIO()
            image.save(data, 'png')
            self.overview = data.getvalue()
            self.last_overview = current_time
            self.last_map_name = self.protocol.map_info.name
        return self.overview
