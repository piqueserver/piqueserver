"""
tests for bytes.pyx
"""
from twisted.trial import unittest

from pyspades.vxl import VXLData
from io import BytesIO


SINGLE_SPAN_COLUMN = bytes([
    0x00,  # this column has only one span, so it's the last one
    61,  # our colored blocks start at 61
    61,  # our colored blocks end at 61
    0x00,  # there are no more spans, so this air byte does not matter
    0xAA,  # The color is #AABBCC
    0xBB,
    0xCC,
    0x00,  # no shading
])

class TestVXLData(unittest.TestCase):
    """tests for VXLData"""

    def test_flat_map(self):
        d = VXLData(BytesIO(SINGLE_SPAN_COLUMN * 512 * 512))
        solid, _ = d.get_point(0, 0, 0)
        self.assertFalse(solid)

    def test_flat_ocean_eof(self):
        with self.assertRaises(ValueError):
            d = VXLData(BytesIO(SINGLE_SPAN_COLUMN * 512 * 511))
