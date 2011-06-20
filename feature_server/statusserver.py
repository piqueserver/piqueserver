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

class StatusResource(Resource):
    protocol = None
    
    def __init__(self, protocol):
        self.protocol = protocol
        Resource.__init__(self)

    def getChild(self, name, request):
        return self

    def render_GET(self, request):
        blues = []
        greens = []
    
        for player in self.protocol.players.values():
            if player.team is self.protocol.blue_team:
                blues.append(player.name)
            else:
                greens.appnd(player.name)
                                
        dictionary = {
            "serverName": self.protocol.name,
            "serverVersion": self.protocol.version,
            "map": {
                "name": self.protocol.map_info.name,
                "version": self.protocol.map_info.version
            },
            "players": {
                "blue": blues,
                "green": greens,
                "maxPlayers": self.protocol.max_players,
            },
            "scores": {
                "currentBlueScore": self.protocol.blue_team.score,
                "currentGreenScore": self.protocol.green_team.score,
            "maxScore": self.protocol.max_score}
            }

        return json.dumps(dictionary)

class StatusServerFactory(object):
    def __init__(self, protocol, config):
        status_resource = StatusResource(protocol)
        site = server.Site(status_resource)
        reactor.listenTCP(config.get('port', 38826), site)
