"""
Runs the garbage collector at a given interval and displays any uncollected
garbage found.

Maintainer: mat^2
"""

from twisted.internet import reactor
from twisted.internet.task import LoopingCall
import gc

INTERVAL = 60 * 10
VERBOSE = False

def apply_script(protocol, connection, config):
    def run_gc():
        ret = gc.collect()
        if VERBOSE:
            print 'gc.collect() ->', ret
        if not gc.garbage:
            return
        print 'Memory leak detected!'
        print 'Contents of gc.garbage:', gc.garbage
    loop = LoopingCall(run_gc)
    loop.start(INTERVAL, now = False)
    return protocol, connection