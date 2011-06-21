from pyspades.load import VXLData

import os
import imp

import mapmaker

class MapNotFound(IOError):
    pass

class Map(object):
    name = None
    author = None
    version = None
    description = None
    
    data = None
    info = None
    
    def __init__(self, name, load_dir = './maps'):
        Map.loaded_map = self
        self.load_information(name, load_dir)
        if not self.generate_map(name):
            self.load_vxl(name, load_dir)

    def load_information(self, name, load_dir):
        info_file = os.path.join(load_dir, '%s.txt' % name)
        try:
            info = imp.load_source(name, info_file)
        except IOError:
            info = None
        self.name = getattr(info, 'name', name)
        self.author = getattr(info, 'author', '(unknown)')
        self.version = getattr(info, 'version', '1.0')
        self.description = getattr(info, 'description', '')
        self.extensions = getattr(info, 'extensions', {})
        self.script = getattr(info, 'apply_script', None)
        
    def apply_script(self, protocol, connection, config):
        if self.script is not None:
            protocol, connection = self.script(protocol, connection, config)
        return protocol, connection

    def load_vxl(self, name, load_dir):
        data_file = os.path.join(load_dir, '%s.vxl' % name)
        if not os.path.isfile(data_file):
            raise MapNotFound('map %s does not exist' % name)
        self.data = VXLData(open(data_file, 'rb'))

    def generate_map(self, name):
        if name == 'random':
            self.data = mapmaker.generator_random()
            self.author = "Triplefox"
            return True
        else:
            return False
