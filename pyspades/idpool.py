# Copyright (c) 2011 Mathias Kaerlev.
# See LICENSE for details.

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

    def putBack(self, id):
        """
        Puts back a previously popped ID.
        """
        self._freeIds.append(id)