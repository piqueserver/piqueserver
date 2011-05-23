from pyspades.load import VXLData

map = VXLData(open('sinc0.vxl', 'rb'))
open('sinc1.vxl', 'wb').write(map.generate())