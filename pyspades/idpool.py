# Copyright (c) Mathias Kaerlev 2011.

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
    _newIds = None
    _freeIds = None

    def __init__(self, start = 0):
        """
        Initializes a new pool, counting from start
        """
        self._freeIds = []
        self._newIds = itertools.count(start)

    def pop(self):
        """
        Take out an ID from the pool, and wait for it to be
        put back again (see L{putBack})
        @return: A new ID from the pool.
        """
        if self._freeIds:
            return self._freeIds.pop()
        else:
            return self._newIds.next()

    def put_back(self, id):
        """
        Puts back a previously popped ID.
        """
        self._freeIds.append(id)