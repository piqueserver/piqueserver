# -*- encoding: utf-8 -*-
"""
test pyspades/common.pyx
"""

from twisted.trial import unittest

from pyspades.common import escape_control_codes, get_color, to_coordinates, coordinates

class TestCommonThings(unittest.TestCase):

    def test_get_color(self):
        self.assertEqual(get_color(0xFFFFFF), (0xFF, 0xFF, 0xFF))

    def test_to_coords(self):
        self.assertEqual(to_coordinates(511, 511), "H8")

    def test_from_coords(self):
        self.assertEqual(coordinates("H8"), (448, 448))

    def test_escape_control_codes(self):
        test_cases = [
            ("\x1b[6;30;42mGreen!\x1b[0m", "\\x1b[6;30;42mGreen!\\x1b[0m"), # ANSI
            ("\x1b[6;30;42mGreen世界!\x1b[0m", "\\x1b[6;30;42mGreen世界!\\x1b[0m"), # ANSI with utf-8
            ("hello\n\t","hello\\n\\t"), # acii controll codes
            ("hello ", "hello "), # normal
            ("世界", "世界") # normal utf-8
        ]
        for unescaped, want in test_cases:
            self.assertEqual(escape_control_codes(unescaped), want)
