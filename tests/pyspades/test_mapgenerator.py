"""
test pyspades/mapgenerator.py
"""
from __future__ import print_function
from pyspades.mapgenerator import ProgressiveMapGenerator as PMG
from pyspades.mapgenerator import MapGeneratorChild as MGC
from unittest import mock, TestCase, expectedFailure
from os import urandom


def mock_map(data):
    done_data = [False]*len(data) + [True]
    map_data = data + [None]

    ret = mock.MagicMock()
    ret.get_generator().get_data.side_effect=map_data
    type(ret.get_generator()).done = mock.PropertyMock(side_effect=done_data)
    return ret

def mock_compressor():
    ret = mock.MagicMock()
    ret.flush.return_value=b''
    ret.compress.side_effect=lambda x: x
    return ret


class TestProgressiveMapGenerator(TestCase):
    """It's impractical to do systematic testing when test results depends on
    a compression algorithm. Therefore, compression is disabled where necessary
    to evaluate the correctness of the ProgressiveMapGenerator.

    It is also impractical to use an actual piqueserver.py::Map object as input
    to the `ProgressiveMapGenerator` -- doing so would require either precise
    mock data or to load a map from disk. Unfortunately vxl.pyx::Generator are
    hard to use here as well -- it more or less acts as a wrapper over the
    `generate_map_data` function which can't be mocked easily (which would be
    ideal) since it's a native function. Therefore the whole Map object,
    including the vxl.pyx::Generator are mocked when used as input data to
    ProgressiveMapGenerator. This does not, however, currently impact the
    correctness of these tests.
    """

    # The above should be enough to motivate the lack of tests for REQ-A.1 and
    # REQ-A.3. The same goes for REQ-C.1 to REQ-C.4


    # REQ-A.4
    def test_get_size(self):
        """ get_size returns a constant, hard coded value. This test acts as a
        canary, signaling that the constant has changed.
        """
        mg = PMG(mock.MagicMock())
        assert mg.get_size() == 1.5*1024*1024


    # REQ-A.5
    def test_generator_chunk_size_1(self):
        """ ProgressiveMapGenerator should return chunks in size of its
        read_size parameter when it's left to the default value.
        """

        map_ = mock_map([urandom(8192*2)])
        mg = PMG(map_, )
        mg.compressor = mock_compressor()
        assert len(next(mg)) == 8192
        assert len(next(mg)) == 8192

    def test_generator_chunk_size_2(self):
        """ ProgressiveMapGenerator should return chunks in size of its
        read_size parameter when it's set manually
        """

        map_ = mock_map([urandom(10*2)])
        mg = PMG(map_, read_size=10)
        mg.compressor = mock_compressor()
        assert len(next(mg)) == 10
        assert len(next(mg)) == 10

    # REQ-A.5
    def test_generator_chunk_size_3(self):
        """ When the size of the compressed data is a multiple of read_size,
        the last chunk should be an empty byte array
        """

        map_ = mock_map([urandom(8192*2)])
        mg = PMG(map_, read_size=8192)
        mg.compressor = mock_compressor()
        next(mg)
        next(mg)
        assert len(next(mg)) == 0

    def test_generator_chunk_size_4(self):
        """ When the size of the compressed data not is a multiple of
        read_size the last chunk should have size less than read_size
        """

        map_ = mock_map([urandom(8192*2 + 8191)])
        mg = PMG(map_, read_size=8192)
        mg.compressor = mock_compressor()
        next(mg)
        next(mg)
        assert len(next(mg)) < 8192

    def test_generator_chunk_size_5(self):
        """ When the size of the compressed data not is a multiple of
        read_size there should not be any empty byte arrays following the
        last chunk
        """

        map_ = mock_map([urandom(8192*2 + 8191)])
        mg = PMG(map_, read_size=8192)
        mg.compressor = mock_compressor()
        next(mg)
        next(mg)
        next(mg)
        with self.assertRaises(StopIteration):
            next(mg)

    # REQ-B.3
    def test_generator_iterable_1(self):
        """ ProgressiveMapGenerator should be iterable
        """
        data = [b'test1', b'test2', b'test3']
        map_ = mock_map(data)
        mg = PMG(map_, read_size=5)
        mg.compressor = mock_compressor()

        # It's supposed to have a trailing empty byte array in this case
        self.assertSequenceEqual([x for x in mg], data + [b''])

    # REQ-A.2
    def test_generator_parent_1(self):
        """ If ProgressiveMapGenerator is a parent it shouldn't return any data
        """
        map_ = mock_map([urandom(8192*3 + 1)])
        mg = PMG(map_, parent=True)
        assert next(mg) == None

class TestMapGeneratorChild(TestCase):

    # REQ-A.2
    # REQ-A.7
    # REQ-A.8
    @expectedFailure
    def test_get_child_1(self):
        """ get_child() should raise an exception if the parent flag is not set
        for ProgressiveMapGenerator. This might change in future versions.
        """

        mg = PMG(mock.MagicMock())
        mg.get_child()

    # REQ-A.7
    # REQ-B.1
    def test_get_child_2(self):
        """ get_child() should return a MapGeneratorChild if the parent flag
        is set
        """

        mg = PMG(mock.MagicMock(), parent=True)
        assert type(mg.get_child()) is MGC

    # REQ-A.7
    # REQ-B.1
    # REQ-B.2
    def test_get_child_3(self):
        """ The child of a ProgressiveMapGenerator must be a MapGeneratorChild
        """

        mg = PMG(mock.MagicMock(), parent=True)
        c = mg.get_child()
        assert c.parent is mg

    # REQ-A.7
    def test_generator_child_size_1(self):
        """ The sice of a MapGeneratorChild should be equal to its parents
        size
        """

        mg = PMG(mock.MagicMock(), parent=True)
        c = mg.get_child()
        assert mg.get_size() == c.get_size()

    # REQ-A.7
    def test_get_child_iterable_1(self):
        """ MapGeneratorChild shouldn't read ahead of its parent
        """

        map_ = mock_map([urandom(8192*2 + 8191)])
        mg = PMG(map_, parent=True)
        c = mg.get_child()
        for x in c:
            pass
        assert c.pos <= mg.pos

    # REQ-A.6
    # REQ-A.7
    def test_multi_child_iterable(self):
        """ MapGeneratorChildren should end up at the same positions
        """

        map_ = mock_map([urandom(8192*2 + 8191)])
        mg = PMG(map_, parent=True)
        c1 = mg.get_child()
        c2 = mg.get_child()
        for x in c1:
            pass
        for x in c2:
            pass
        assert c1.pos == c2.pos


    # REQ-A.6
    # REQ-A.7
    def test_multi_child_iterable(self):
        """ MapGeneratorChildren should do the same amount of rounds and get the same data
        """

        map_ = mock_map([urandom(8192*2 + 8191)])
        mg = PMG(map_, parent=True)
        c1 = mg.get_child()
        c2 = mg.get_child()
        i1 = 0
        total1 = b''
        total2 = b''
        for x in c1:
            i1 += 1
            total1 += x
        i2 = 0
        for x in c2:
            i1 += 1
            total2 += x
        assert c1.pos == c2.pos
        assert total1 == total2
