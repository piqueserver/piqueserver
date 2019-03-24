
from twisted.trial import unittest
from unittest.mock import Mock

from pyspades import world

import colorsys

class WorldTest(unittest.TestCase):
    def test_giant_cube_line(self):
        world.cube_line(1, 1, 1, 100, 100, 100)
        world.cube_line(100, 100, 100, 1, 1, 1)
        world.cube_line(1, 1, 1, 1, 100, 100)
        world.cube_line(1, 1, 1, 1, 5000, 100)

    def test_simple_cube_line(self):
        line = world.cube_line(1, 1, 1, 10, 1, 1)
        line_should = [(x, 1, 1) for x in range(1, 11)]
        self.assertEqual(line, line_should)

    def test_complex_cube_line(self):
        line = world.cube_line(10, 10, 10, 21, 19, 12)
        line_should = [(10, 10, 10), (11, 10, 10), (11, 11, 10), (12, 11, 10),
                       (12, 12, 10), (13, 12, 10), (13, 12, 11), (13, 13, 11),
                       (14, 13, 11), (14, 14, 11), (15, 14, 11), (15, 15, 11),
                       (16, 15, 11), (17, 15, 11), (17, 16, 11), (18, 16, 11),
                       (18, 17, 11), (18, 17, 12), (19, 17, 12), (19, 18, 12),
                       (20, 18, 12), (20, 19, 12), (21, 19, 12)]
        self.assertEqual(line, line_should)
