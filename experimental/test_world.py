from pyspades.common import *
from pyspades.load import VXLData
import world
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