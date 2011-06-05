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


class StatusServer(Resource):
        
    info = None
   
    def setInfo(self, info):
        self.info = info     

    def getChild(self, name, request):
        return self

    def render_GET(self, request):
                
        blues = []
        greens = []
    
        for player in self.info.players.values():
            if player.team is self.info.blue_team:
                blues.append(player.name)
            else:
                greens.appnd(player.name)
                
                
        dictionary = {"serverName": self.info.name,
            "serverVersion": self.info.version,
            "map": {
                "name": self.info.map_info.name,
                "version": self.info.map_info.version
            },
            "players": {
                "blue": blues,
                "green": greens,
                "maxPlayers": self.info.max_players,
            },
            "scores": {
                "currentBlueScore": self.info.blue_team.score,
                "currentGreenScore": self.info.green_team.score,
            "maxScore": self.info.max_scores}
            }

        output = StatusEncoder().encode(dictionary)
                
        #json = self.json_template.substitute(
        #server_version = str(self.info.version),
        #name = str(self.info.name),
        #map_name = str(self.info.map_info.name),
        #map_version = str(self.info.map_info.version),
        #blue_players = str(self.info.blue_team.count()),
        #green_players = str(self.info.green_team.count()),
        #max_players = str(self.info.max_players),
        #blue_score= str(self.info.blue_team.score),
        #green_score = str(self.info.green_team.score),
        #max_score = str(self.info.max_scores)
        #)

        
        return output

class StatusEncoder(json.JSONEncoder):
     def default(self, obj):
         if isinstance(obj, complex):
             return [obj.real, obj.imag]
         return json.JSONEncoder.default(self, obj)

class StatusServerFactory(object):
    def __init__(self, pyServer, config):
        statusServer = StatusServer()
        site = server.Site(statusServer)
        statusServer.setInfo(pyServer)
        reactor.listenTCP(config.get('port', 38826), site)
