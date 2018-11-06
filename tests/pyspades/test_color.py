from twisted.trial import unittest
from unittest.mock import Mock

from pyspades import color

import colorsys

class ColorTest(unittest.TestCase):
    def test_wrap(self):
        self.assertEqual(color.wrap(12, 43, 120), 27)

    def test_hsb_to_rgb(self):
        self.assertEqual(color.hsb_to_rgb(0.5, 0.4, 0.3), (45, 76, 76))
        self.assertEqual(color.hsb_to_rgb(0.1, 0.2, 0.3), (76, 70, 61))

    def test_insterpolate(self):
        self.assertEqual(color.interpolate_rgb(
            (45, 76, 76), (100, 142, 123), 0.1), (50, 82, 80))
        self.assertEqual(color.interpolate_rgb(
            (76, 70, 61), (127, 40, 81), 0.7), (111, 49, 75))
        self.assertEqual(color.interpolate_hsb(
            (0.4, 0.76, 0.76), (0.1, 0.14, 0.12), 0.1), (0.37, 0.698, 0.696))
        self.assertEqual(color.interpolate_hsb(
            (0.7, 0.7, 0.1), (0.12, 0.4, 0.8), 0.7), (0.294, 0.49, 0.59))

    def test_distance(self):
        self.assertEqual(color.rgb_distance((1, 2, 3), (9, 8, 7)), 18)
