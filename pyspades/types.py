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

import itertools

class IDPool(object):
    """
    Manage pool of IDs
    """
    
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

class AttributeSet(set):
    """
    set with attribute access
    """
    
    def __getattr__(self, name):
        return name in self
    
    def __setattr__(self, name, value):
        if value:
            self.add(name)
        else:
            self.discard(name)

class DictItem(object):
    keys = None
    value = None
    
    def __init__(self, keys, value):
        self.keys = keys
        self.value = value

    def __str__(self):
        return str(self.value)

    def __repr__(self):
        return repr(self.value)

class MultikeyDict(dict):
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
        newItem = DictItem(keys, value)
        self.value_set.add(value)
        for key in keys:
            if key in self:
                raise KeyError('key %s already exists' % key)
            dict.__setitem__(self, key, newItem)
    
    def values(self):
        return self.value_set
    
    def __len__(self):
        return len(self.value_set)