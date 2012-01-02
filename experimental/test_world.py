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
sys.path.append('..')

from pyspades.common import *
from pyspades.load import VXLData
from pyspades import world
from twisted.internet import reactor
from twisted.internet.task import LoopingCall

new_world = world.World(VXLData(open('../data/sinc0.vxl')))
nade = new_world.create_object(world.Character,
    Vertex3(20.0, 20.0, 5.0), Vertex3())

def update():
    dt = 1 / 60.0
    new_world.update(dt)
    for instance in new_world.objects:
        position = instance.position
        print position.x, position.y, position.z

caller = LoopingCall(update)
caller.start(1 / 60.0, now = False)
reactor.run()