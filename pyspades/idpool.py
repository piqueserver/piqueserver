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

"""
Manage pool of IDs.
"""

import itertools

class IDPool(object):
    def __init__(self, start = 0):
        self.free_ids = []
        self.new_ids = itertools.count(start)

    def pop(self):
        if self.free_ids:
            return self.free_ids.pop()
        else:
            return self.new_ids.next()

    def put_back(self, id):
        self.free_ids.append(id)