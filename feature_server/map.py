from pyspades.load import VXLData

import os
import json

class MapNotFound(IOError):
    pass

class Map(object):
    name = None
    author = None
    version = None
    description = None
    indestructable_blocks = None
    
    data = None
    info = None
    def __init__(self, name, load_dir = './maps'):
        info_file = os.path.join(load_dir, '%s.txt' % name)
        data_file = os.path.join(load_dir, '%s.vxl' % name)
        if not os.path.isfile(data_file):
            raise MapNotFound('map %s does not exist' % name)
        self.data = VXLData(open(data_file, 'rb'))
        try:
            info = json.load(open(info_file, 'rb'))
        except IOError:
            info = {}
            
        self.name = info.get('name', name)
        self.author = info.get('author', '(unknown)')
        self.version = info.get('version', '1.0')
        self.description = info.get('description', '')
        self.indestructable_blocks = info.get('indestructable_blocks', [])