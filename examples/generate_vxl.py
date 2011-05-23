from pyspades.load import VXLData

map = VXLData()

for x in xrange(50, 512 - 50):
    for y in xrange(50, 512 - 50):
        for z in xrange(20, 58):
            map.set_point(x, y, z, (20, 20, 30, 40))

for x in range(512):
    for y in xrange(512):
        map.set_point(x, y, 62, (20, 20, 30, 40))
        map.set_point(x, y, 63, (20, 20, 30, 40))

for z in range(5, 64):
    map.set_point(256, 256, z, (20, 20, 30, 40))

print 'generating'

open('worldstick.vxl', 'wb').write(map.generate())