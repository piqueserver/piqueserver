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

import asyncio
import json
from itertools import chain
from typing import List

import aiohttp
from twisted.logger import Logger

from piqueserver.config import cast_duration, config
from piqueserver.networkdict import NetworkDict

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

    def __init__(self, protocol):
        self.protocol = protocol
        self.urls = [(entry.get('url'), entry.get('whitelist')) for entry in
                     bans_config_urls.get()]

    async def start(self):
        while True:
            await self.update_bans()
            await asyncio.sleep(bans_config_interval.get())

    async def fetch_filtered_bans(self, url: str, whitelist: List[str]):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    # blacklist.spadille.net doesn't set json content type ¯\_(ツ)_/¯
                    banslist = json.loads(await resp.text())
                    return [ban for ban in banslist if ban.get('name', None) not in whitelist]
        except Exception as e:
            log.error("Failed to fetch bans from {url}: {err}", url=url, err=e)
            return []

    async def update_bans(self):
        coros = []
        for url, whitelist in self.urls:
            coros.append(self.fetch_filtered_bans(url, whitelist))
        log.info("fetching bans from bansubscribe urls")
        banlists = await asyncio.gather(*coros)
        bans = list(chain(*banlists))
        new_bans = NetworkDict()
        for ban in bans:
            new_bans[ban['ip']] = ban['reason']
        self.bans = new_bans
        log.info("successfully updated bans from bansubscribe urls")

    def get_ban(self, ip):
        if self.bans is None:
            return None
        try:
            return self.bans[ip]
        except KeyError:
            return None
