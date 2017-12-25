"""
test pyspades/common.pyx
"""

from __future__ import print_function

from twisted.trial import unittest

from pyspades.common import get_color, to_coordinates, coordinates

class TestCommonThings(unittest.TestCase):

    def test_get_color(self):
        self.assertEqual(get_color(0xFFFFFF), (0xFF, 0xFF, 0xFF))

    def test_to_coords(self):
        self.assertEqual(to_coordinates(511, 511), "H8")

    def test_from_coords(self):
        self.assertEqual(coordinates("H8"), (448, 448))
