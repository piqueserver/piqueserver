import zlib

COMPRESSION_LEVEL = 9

class ProgressiveMapGenerator(object):
    data = b''
    done = False

    # parent attributes
    all_data = ''
    pos = 0

    def __init__(self, map_, parent=False):
        self.parent = parent
        self.generator = map_.get_generator()
        self.compressor = zlib.compressobj(COMPRESSION_LEVEL)

    def get_size(self):
        return 1.5 * 1024 * 1024  # 2 mb

    def read(self, size):
        data = self.data
        generator = self.generator
        if len(data) < size and generator is not None:
            while 1:
                map_data = generator.get_data(size)
                if generator.done:
                    self.generator = None
                    data += self.compressor.flush()
                    break
                data += self.compressor.compress(map_data)
                if len(data) >= size:
                    break
        if self.parent:
            # save the data in case we are a parent
            self.all_data += data
            self.pos += len(data)
        else:
            self.data = data[size:]
            return data[:size]

    def get_child(self):
        return MapGeneratorChild(self)

    def data_left(self):
        return bool(self.data) or self.generator is not None

class MapGeneratorChild(object):
    pos = 0

    def __init__(self, generator):
        self.parent = generator

    def get_size(self):
        return self.parent.get_size()

    def read(self, size):
        pos = self.pos
        if pos + size > self.parent.pos:
            self.parent.read(size)
        data = self.parent.all_data[pos:pos + size]
        self.pos += len(data)
        return data

    def data_left(self):
        return self.parent.data_left() or self.pos < self.parent.pos
