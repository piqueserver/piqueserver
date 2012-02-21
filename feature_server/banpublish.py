# Copyright (c) James W. Hofmann 2011.

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

class PublishResource(Resource):
    def __init__(self, factory):
        self.factory = factory
        Resource.__init__(self)

    def getChild(self, name, request):
        return self

    def render_GET(self, request):
        return self.factory.json_bans

class PublishServer(object):
    def __init__(self, protocol, config):
        self.protocol = protocol
        publish_resource = PublishResource(self)
        site = server.Site(publish_resource)
        protocol.listenTCP(config.get('port', 32885), site)
        self.update()
    
    def update(self):
        bans = []
        for network, (name, reason, timestamp) in self.protocol.bans.iteritems():
            if timestamp is None or reactor.seconds() < timestamp:
                bans.append({"ip" : network, "reason" : reason})
        self.json_bans = json.dumps(bans)
