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

import msvcrt
import sys
from commands import handle_input
from twisted.internet import reactor
from twisted.protocols.basic import LineReceiver

stdout = sys.__stdout__

if sys.platform == 'win32':
    # StandardIO on Windows does not work, so we create a silly replacement
    class StandardIO(object):
        disconnecting = False
        interval = 0.01
        input = ''
        def __init__(self, protocol):
            self.protocol = protocol
            protocol.makeConnection(self)
            self.get_input()

        def get_input(self):
            while msvcrt.kbhit():
                c = msvcrt.getch()
                if c == '\r': # new line
                    c = '\n'
                    stdout.write(c)
                    self.input += c
                    self.protocol.dataReceived(self.input.decode('cp437'))
                    self.input = ''
                elif c in ('\xE0', '\x00'):
                    # ignore special characters
                    msvcrt.getch()
                elif c == '\x08': # delete
                    self.input = self.input[:-1]
                    stdout.write('\x08 \x08')
                else:
                    self.input += c
                    stdout.write(c)
            reactor.callLater(self.interval, self.get_input)
    
        def write(self, data):
            stdout.write(data)

        def writeSequence(self, seq):
            stdout.write(''.join(seq))
else:
    from twisted.internet.stdio import StandardIO

class ConsoleInput(LineReceiver):
    name = 'Console'
    admin = True
    delimiter = '\n'

    def __init__(self, protocol):
        self.protocol = protocol

    def lineReceived(self, line):
        if line.startswith('/'):
            line = line[1:]
            result = handle_input(self, line)
            if result is not None:
                print result
        else:
            self.protocol.send_chat(line)

def create_console(protocol):
    console = ConsoleInput(protocol)
    StandardIO(console)