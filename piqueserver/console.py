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

import sys

from typing import List
import traceback

from twisted.internet import reactor
from twisted.protocols.basic import LineReceiver

from pyspades.types import AttributeSet
from piqueserver import commands

stdout = sys.__stdout__

if sys.platform == 'win32':
    # StandardIO on Windows does not work, so we create a silly replacement
    import msvcrt  # pylint: disable=import-error

    class StandardIO:
        disconnecting = False
        interval = 0.01
        input = ''

        def __init__(self, protocol):
            self.protocol = protocol
            protocol.makeConnection(self)
            self.get_input()

        def get_input(self):
            while msvcrt.kbhit():
                c = msvcrt.getwch()
                if c == '\r':  # new line
                    c = '\n'
                    stdout.write(c)
                    self.input += c
                    self.protocol.dataReceived(self.input)
                    self.input = ''
                elif c in ('\xE0', '\x00'):
                    # ignore special characters
                    msvcrt.getwch()
                elif c == '\x08':  # delete
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
    delimiter = b'\n'

    def __init__(self, protocol):
        self.protocol = protocol
        self.user_types = AttributeSet(['admin', 'console'])
        self.rights = AttributeSet()
        for user_type in self.user_types:
            self.rights.update(commands.get_rights(user_type))

    def lineReceived(self, line):
        if not line:
            return

        try:
            result = commands.handle_input(self, line.decode())
        # pylint: disable=broad-except
        except Exception:
            traceback.print_exc()
        else:
            if result is not None:
                print(result)

    # methods used to emulate the behaviour of regular Connection objects to
    # prevent errors when command writers didn't test that their scripts would
    # work when run on the console
    def send_chat(self, value: str, _):
        print(value)

    def send_lines(self, lines: List[str]):
        print("\n".join(lines))


def create_console(protocol):
    console = ConsoleInput(protocol)
    StandardIO(console)
