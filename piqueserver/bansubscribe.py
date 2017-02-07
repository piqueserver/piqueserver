# Copyright (c) Mathias Kaerlev 2011-2012.

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

import json
from twisted.internet.task import LoopingCall
from twisted.internet.defer import DeferredList

from piqueserver.networkdict import NetworkDict

UPDATE_INTERVAL = 5 * 60  # every 5 minute

# format is [{"ip" : "1.1.1.1", "reason : "blah"}, ...]


class BanManager(object):
    bans = None
    new_bans = None

    def __init__(self, protocol, config):
        self.protocol = protocol
        self.urls = [(str(item), name_filter) for (item, name_filter) in
                     config.get('urls', [])]
        self.loop = LoopingCall(self.update_bans)
        self.loop.start(UPDATE_INTERVAL, now=True)

    def update_bans(self):
        self.new_bans = NetworkDict()
        defers = []
        for url, url_filter in self.urls:
            defers.append(self.protocol.getPage(url).addCallback(self.got_bans,
                                                                 url_filter))
        DeferredList(defers).addCallback(self.bans_finished)

    def got_bans(self, data, name_filter):
        bans = json.loads(data)
        for entry in bans:
            name = entry.get('name', None)
            if name is not None and name in name_filter:
                continue
            self.new_bans[str(entry['ip'])] = str(entry['reason'])

    def bans_finished(self, _result):
        self.bans = self.new_bans
        self.new_bans = None

    def get_ban(self, ip):
        if self.bans is None:
            return None
        try:
            return self.bans[ip]
        except KeyError:
            return None
