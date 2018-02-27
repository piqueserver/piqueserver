"""
The map generator is responsible for generatoring the map bytes that get sent
to the client on connect
"""
import zlib

COMPRESSION_LEVEL = 9


class ProgressiveMapGenerator(object):
    """
    Progressively generates the stream of bytes sent to the client for map
    downloads.

    It supports two modes. In the default parent=False mode, reading is normal.

    In the `parent=True` mode a child generator is created with `get_child` to
    actually read the data. This is presumably done so that the work of map
    generation is not duplicated for each client if several connect at the same
    time.
    """
    data = b''
    done = False

    # parent attributes
    all_data = b''
    pos = 0

    def __init__(self, map_, parent=False, read_size=8192):
        # parent=True enables saving all data sent instead of just
        # deleting it afterwards.
        self.parent = parent
        self.generator = map_.get_generator(read_size)
        self.compressor = zlib.compressobj(COMPRESSION_LEVEL)
        self.read_size = read_size

    def get_size(self):
        """get the map size, for display of the loading bar on the client"""
        # This is currently just an estimate, since due to compression
        # magic, we don't actually know what size the file will be when sent
        # over the wire
        return 1.5 * 1024 * 1024  # 2MB

    def __iter__(self):
        return self

    # Python 3 compatibility
    def __next__(self):
        return self.next()

    def next(self):
        if self.data_left():
            return self.read()
        else:
            raise StopIteration()

    def read(self):
        """read size bytes from the map generator"""
        size = self.read_size
        data = self.data
        generator = self.generator
        if len(data) < size and generator is not None:
            while True:
                map_data = generator.get_data()
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
        """return a new child generator"""
        if self.parent:
            return MapGeneratorChild(self)
        else:
            raise NotImplementedError(
                "get_child is not implemented for non-parent generators")

    def data_left(self):
        """return True if any data is left"""
        return bool(self.data) or self.generator is not None


class MapGeneratorChild(object):
    pos = 0

    def __init__(self, generator):
        self.parent = generator

    def get_size(self):
        """get the size of the parent map generator"""
        return self.parent.get_size()

    def __iter__(self):
        while self.parent.data_left() or self.pos < self.parent.pos:
            size = self.parent.read_size
            pos = self.pos
            if pos + size > self.parent.pos:
                self.parent.read()
            data = self.parent.all_data[pos:pos + size]
            self.pos += len(data)
            yield data
        raise StopIteration
