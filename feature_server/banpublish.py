# feature_server/banpublish.py
#
#   This file is licensed under the GNU General Public License version 3.
# In accordance to the license, there are instructions for obtaining the
# original source code. Furthermore, the changes made to this file can
# be seem by using diff tools and/or git-compatible software.
#
#   The license full text can be found in the "LICENSE" file, at the root
# of this repository. The original PySpades code can be found in this URL:
# https://github.com/infogulch/pyspades/releases/tag/v0.75.01.
#
# Original copyright: (C)2011 James W. Hofmann
#

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
                bans.append({"ip": network, "reason": reason})
        self.json_bans = json.dumps(bans)
