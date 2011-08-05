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
from twisted.web import static, server
from twisted.web.resource import Resource
from string import Template
import json

STATUS_FILE = './web/status.html'

class StatusResource(Resource):
    protocol = None
    
    def __init__(self, protocol):
        self.protocol = protocol
        Resource.__init__(self)

    def getChild(self, name, request):
        return self

    def render_GET(self, request):
        path = request.path
        protocol = self.protocol
        if path == '/json':
            blues = []
            greens = []
        
            for player in protocol.players.values():
                if player.team is protocol.blue_team:
                    blues.append(player.name)
                else:
                    greens.append(player.name)
                                    
            dictionary = {
                "serverName" : protocol.name,
                "serverVersion": protocol.version,
                "map" : {
                    "name": protocol.map_info.name,
                    "version": protocol.map_info.version
                },
                "players" : {
                    "blue": blues,
                    "green": greens,
                    "maxPlayers": protocol.max_players,
                },
                "scores" : {
                    "currentBlueScore": protocol.blue_team.score,
                    "currentGreenScore": protocol.green_team.score,
                "maxScore": protocol.max_score}
                }

            return json.dumps(dictionary)
        else:
            data = open(STATUS_FILE).read()
            data = data % {
                'name' : protocol.name,
                'players' : len(protocol.connections),
                'max_players' : protocol.max_players
            }
            return str(data)

class StatusServerFactory(object):
    def __init__(self, protocol, config):
        status_resource = StatusResource(protocol)
        site = server.Site(status_resource)
        reactor.listenTCP(config.get('port', 32886), site)
