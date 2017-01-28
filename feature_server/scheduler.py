# feature_server/scheduler.py
#
#   This file is licensed under the GNU General Public License version 3.
# In accordance to the license, there are instructions for obtaining the
# original source code. Furthermore, the changes made to this file can
# be seem by using diff tools and/or git-compatible software.
#
#   The license full text can be found in the "LICENSE" file, at the root
# of this repository. The original PySpades code can be found in this URL:
# https://github.com/infogulch/pyspades/releases/tag/v0.75.01.
#
# Original copyright: (C)2012 Mathias Kaerlev
#

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
