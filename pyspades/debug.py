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
Oh-so-messy debugging stuff. Beware of the inferior code quality.
"""

isClient = None
mapBytes = 0
packets = 0
map_data = {}
is_relay = False
sequence = None

chunks = {}

current_id = 0
def write_packet(data):
    global current_id
    open('packets/%s.dat' % current_id, 'wb').write(str(data))
    current_id += 1

def open_debug_log(file_name='debug.log'):
    DebugLog.filehandle = open(file_name,'w')

def get_refcounts():
    d = {}
    import sys
    import types
    # collect all classes
    for m in sys.modules.values():
        for sym in dir(m):
            o = getattr (m, sym)
            if type(o) is types.ClassType:
                d[o] = sys.getrefcount (o)
    # sort by refcount
    pairs = map (lambda x: (x[1],x[0]), d.items())
    pairs.sort()
    pairs.reverse()
    return pairs

def print_top_100():
    if DebugLog.filehandle:
        DebugLog.filehandle.write('***Reference counts\n')
        for n, c in get_refcounts()[:100]:
            DebugLog.filehandle.write('%10d %s\n' % (n, c.__name__))
        DebugLog.filehandle.flush()

def debug_csv_line(listdata):
    if DebugLog.filehandle:
        DebugLog.filehandle.write(','.join(map(str, listdata)) )
        DebugLog.filehandle.write('\n')
        DebugLog.filehandle.flush()

class DebugLog:
    filehandle = None
