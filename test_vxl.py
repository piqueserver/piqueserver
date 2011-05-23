from pyspades.load import VXLData
# data = VXLData2(open('sinc0.vxl', 'rb').read())
# print data.get_point(0, 0, 52)
# for x in xrange(512):
    # for y in xrange(512):
        # for z in xrange(64):
            # if data.get_point(x, y, z) is None:
                # print 'NAY', x, y, z
                # raw_input()

map = VXLData(open('sinc0.vxl', 'rb'))
map.remove_point(20, 20, 20)
print 'done'
# new_data = map.generate()
# open('output.vxl', 'wb').write(new_data)
# if open('sinc0.vxl', 'rb').read() != new_data:
    # print 'NOOO'

import time

for _ in xrange(10):
    start = time.clock()
    # data = map.generate()
    map.remove_point(20, 20, 20)
    print 'took:', (time.clock() - start)
raw_input()