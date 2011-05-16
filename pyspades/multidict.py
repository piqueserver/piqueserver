# Copyright (c) 2011 Mathias Kaerlev.
# See LICENSE for details.

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
    items = None
    def __init__(self, *arg, **kw):
        dict.__init__(self, *arg, **kw)
        self.items = []
    
    def __getitem__(self, key):
        items = dict.__getitem__(self, key)
        return [item.value for item in items]
    
    def __delitem__(self, key):
        item = dict.__getitem__(self, key)
        if len(item) > 1:
            raise KeyError('cannot remove a multi item key')
        item, = item
        self.items.remove(item)
        for itemKey in item.keys:
            itemList = dict.__getitem__(self, itemKey)
            if len(itemList) > 1:
                itemList.remove(item)
            else:
                dict.__delitem__(self, itemKey)
    
    def __setitem__(self, keys, value):
        keys = list(keys) + [value]
        newItem = DictItem(keys, value)
        self.items.append(newItem)
        for key in keys:
            if key in self:
                dict.__getitem__(self, key).append(newItem)
            else:
                dict.__setitem__(self, key, [newItem])
    
    def values(self):
        return [item.value for item in self.items]
        
    def itervalues(self):
        return (item.value for item in self.items)
    
    def __len__(self):
        return len(self.items)