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
    protocol = None
    
    def __init__(self, protocol):
        self.protocol = protocol
        Resource.__init__(self)

    def getChild(self, name, request):
        return self

    def render_GET(self, request):
        dictionary = {
            "bans":self.protocol.bans
            }

        return json.dumps(dictionary)

class PublishServerFactory(object):
    def __init__(self, protocol, config):
        publish_resource = PublishResource(protocol)
        site = server.Site(publish_resource)
        reactor.listenTCP(config.get('port', 38825), site)
