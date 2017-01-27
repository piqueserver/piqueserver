# feature_server/bansubscribe.py
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
# Original copyright: (C)2011-2012 Mathias Kaerlev
#

import json
from twisted.web.client import getPage
from twisted.internet.task import LoopingCall
from twisted.internet.defer import DeferredList

from networkdict import NetworkDict

UPDATE_INTERVAL = 5 * 60 # every 5 minute

# format is [{"ip" : "1.1.1.1", "reason : "blah"}, ...]

class BanManager(object):
    bans = None
    new_bans = None
    def __init__(self, protocol, config):
        self.protocol = protocol
        self.urls = [(str(item), filter) for (item, filter) in
            config.get('urls', [])]
        self.loop = LoopingCall(self.update_bans)
        self.loop.start(UPDATE_INTERVAL, now = True)

    def update_bans(self):
        self.new_bans = NetworkDict()
        defers = []
        for url, filter in self.urls:
            defers.append(self.protocol.getPage(url).addCallback(self.got_bans,
                filter))
        DeferredList(defers).addCallback(self.bans_finished)

    def got_bans(self, data, filter):
        bans = json.loads(data)
        for entry in bans:
            name = entry.get('name', None)
            if name is not None and name in filter:
                continue
            self.new_bans[str(entry['ip'])] = str(entry['reason'])

    def bans_finished(self, result):
        self.bans = self.new_bans
        self.new_bans = None

    def get_ban(self, ip):
        if self.bans is None:
            return None
        try:
            return self.bans[ip]
        except KeyError:
            return None
