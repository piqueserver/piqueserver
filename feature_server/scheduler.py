# Copyright (c) Mathias Kaerlev 2012.

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

from twisted.internet import reactor
from twisted.internet.task import LoopingCall
try:
    from weakref import WeakSet
except ImportError:
    # python 2.6 support (sigh)
    from weakref import WeakKeyDictionary
    class WeakSet(object):
        def __init__(self):
            self._dict = WeakKeyDictionary()

        def add(self, value):
            self._dict[value] = True

        def remove(self, value):
            del self._dict[value]

        def __iter__(self):
            for key in self._dict.keys():
                yield key

        def __contains__(self, other):
            return other in self._dict

        def __len__(self):
            return len(self._dict)

class Scheduler(object):
    def __init__(self, protocol):
        self.protocol = protocol
        self.calls = WeakSet()
        self.loops = WeakSet()
    
    def call_later(self, *arg, **kw):
        call = reactor.callLater(*arg, **kw)
        self.calls.add(call)
        return call
    
    def call_end(self, *arg, **kw):
        call = self.protocol.call_end(*arg, **kw)
        self.calls.add(call)
        return call
    
    def loop_call(self, delay, func, *arg, **kw):
        loop = LoopingCall(func, *arg, **kw)
        loop.start(delay, False)
        self.loops.add(loop)
        return loop
    
    def reset(self):
        for call in self.calls:
            if call.active():
                call.cancel()
        for loop in self.loops:
            if loop.running:
                loop.stop()
        self.calls = WeakSet()
        self.loops = WeakSet()