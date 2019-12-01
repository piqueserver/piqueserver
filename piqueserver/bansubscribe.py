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
from twisted.web.client import getPage
from twisted.logger import Logger

from piqueserver.networkdict import NetworkDict
from piqueserver.config import config, cast_duration

log = Logger()

# format is [{"ip" : "1.1.1.1", "reason : "blah"}, ...]


def validate_bansub_config(c):
    if not isinstance(c, list):
        return False

    for item in c:
        if not item.get('url') or not isinstance(item.get('whitelist'), list):
            return False

    return True

bans_config = config.section('bans')
bans_config_urls = bans_config.option('bansubscribe', default=[], validate=validate_bansub_config)
bans_config_interval = bans_config.option('bansubscribe_interval', default="5min",
                                          cast=cast_duration)


class BanManager:
    bans = None
    new_bans = None

    def __init__(self, protocol):
        self.protocol = protocol
        self.urls = [(entry.get('url'), entry.get('whitelist')) for entry in
                     bans_config_urls.get()]
        self.loop = LoopingCall(self.update_bans)
        self.loop.start(bans_config_interval.get(), now=True)

    def update_bans(self):
        self.new_bans = NetworkDict()
        defers = []
        for url, url_filter in self.urls:
            defers.append(getPage(url.encode('utf8')).addCallback(self.got_bans,
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
        log.info("successfully updated bans from bansubscribe urls")

    def get_ban(self, ip):
        if self.bans is None:
            return None
        try:
            return self.bans[ip]
        except KeyError:
            return None
