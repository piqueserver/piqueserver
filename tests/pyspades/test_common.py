"""
test pyspades/common.pyx
"""

from __future__ import print_function

from twisted.trial import unittest

from pyspades.common import get_color

class TestCommonThings(unittest.TestCase):

    def test_get_color(self):
        self.assertEqual(get_color(0xFFFFFF), (0xFF, 0xFF, 0xFF))
