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
A few useful types used around the place.

IDPool is used to distribute the IDs given out by the Server

AttributeSet is used for tesint if various settings are active

MultikeyDict is used to make player names accessible by both id and name
"""

import itertools
from collections import namedtuple


class IDPool(object):
    """
    Manage pool of IDs

    >>> p = IDPool(start=10)
    >>> p.pop()
    10
    >>> p.pop()
    11
    >>> p.pop()
    12
    >>> p.put_back(11)
    >>> p.pop()
    11
    """

    def __init__(self, start=0):
        self.free_ids = []
        self.new_ids = itertools.count(start)

    def pop(self):
        if self.free_ids:
            return self.free_ids.pop()
        else:
            return next(self.new_ids)

    def put_back(self, id):
        self.free_ids.append(id)


class AttributeSet(set):
    """
    set with attribute access, i.e.

    >>> foo = AttributeSet(("eggs", ))
    >>> foo.eggs
    True
    >>> foo.spam
    False

    Also supports adding and removing elements

    >>> foo.bar = True
    >>> 'bar' in foo
    True
    >>> foo.bar = False
    >>> 'bar' in foo
    False

    This works as a quick shorthand for membership testing.
    """

    def __getattr__(self, name):
        return name in self

    def __setattr__(self, name, value):
        if value:
            self.add(name)
        else:
            self.discard(name)


DictItem = namedtuple("DictItem", ["keys", "value"])


class MultikeyDict(dict):
    """
    dict with multiple keys, i.e.

    >>> foo = MultikeyDict()
    >>> foo[1, 'bar'] = 'hello'
    >>> foo[1]
    'hello'
    >>> foo['bar']
    'hello'

    To delete: "del foo[1]" or "del foo['bar']" or "del foo['hello']"

    This is an alternative to maintaining 2 seperate dicts for e.g. player
    IDs and their names, so you can do both dict[player_id] and
    dict[player_name].

    note: Due to implementation details, the multikeydict can only save
    hashable values. It also can not save values used as key as value.
    """

    def __init__(self, *arg, **kw):
        dict.__init__(self, *arg, **kw)
        self.value_set = set()

    def __getitem__(self, key):
        item = dict.__getitem__(self, key)
        return item.value

    def __delitem__(self, key):
        item = dict.__getitem__(self, key)
        for key in item.keys:
            dict.__delitem__(self, key)
        self.value_set.remove(item.value)

    def __setitem__(self, keys, value):
        keys = list(keys)
        keys.append(value)
        new_item = DictItem(keys, value)
        self.value_set.add(value)
        for key in keys:
            if key in self:
                raise KeyError('key %s already exists' % key)
            dict.__setitem__(self, key, new_item)

    def get(self, key, default=None):
        return self[key] if key in self else default

    def clear(self):
        dict.clear(self)
        self.value_set.clear()

    def values(self):
        return self.value_set

    def itervalues(self):
        return iter(self.value_set)

    def __len__(self):
        return len(self.value_set)
