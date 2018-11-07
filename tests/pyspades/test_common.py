# -*- encoding: utf-8 -*-
"""
test pyspades/common.pyx
"""

import math

from twisted.trial import unittest

from pyspades import common


def assert_math_isclose(first, second, rel_tol=1e-06, abs_tol=0.0, msg=None):
    if math.isclose(first, second, rel_tol=rel_tol, abs_tol=abs_tol):
        return
    standardMsg = (
        '{!r} != {!r} with relative tolerance of {:.3g}'
        ' and absolute tolerance of {:.3g}'
        ).format(first, second, rel_tol, abs_tol)
    if msg:
        raise AssertionError("{} : {}".format(standardMsg, msg))
    else:
        raise AssertionError(standardMsg)

class TestCommonThings(unittest.TestCase):

    def test_get_color(self):
        self.assertEqual(common.get_color(0xAABBCC), (0xAA, 0xBB, 0xCC))

    def test_make_color(self):
        self.assertEqual(common.make_color(0xAA, 0xBB, 0xCC), (0xAABBCC))

    def test_to_coords(self):
        self.assertEqual(common.to_coordinates(511, 511), "H8")

    def test_from_coords(self):
        self.assertEqual(common.coordinates("H8"), (448, 448))
        self.assertRaises(ValueError, lambda: common.coordinates(None))
        self.assertRaises(ValueError, lambda: common.coordinates("H"))
        self.assertRaises(ValueError, lambda: common.coordinates("H33"))
        self.assertRaises(ValueError, lambda: common.coordinates("HA"))

    def test_prettify_timespan(self):
        self.assertEqual(common.prettify_timespan(123456),
                         "1 day, 10 hours, 17 minutes")
        self.assertEqual(common.prettify_timespan(131),
                         "2 minutes")
        self.assertEqual(common.prettify_timespan(131, get_seconds=True),
                         "2 minutes, 11 seconds")
        self.assertEqual(common.prettify_timespan(1),
                         "1 second")

    def test_escape_control_codes(self):
        test_cases = [
            ("\x1b[6;30;42mGreen!\x1b[0m",
             "\\x1b[6;30;42mGreen!\\x1b[0m"),  # ANSI
            ("\x1b[6;30;42mGreen世界!\x1b[0m",
             "\\x1b[6;30;42mGreen世界!\\x1b[0m"),  # ANSI with utf-8
            ("hello\n\t", "hello\\n\\t"),  # acii controll codes
            ("hello ", "hello "),  # normal
            ("世界", "世界")  # normal utf-8
        ]
        for unescaped, want in test_cases:
            self.assertEqual(common.escape_control_codes(unescaped), want)


class TestVertex3(unittest.TestCase):
    def test_basics(self):
        v = common.Vertex3(10, 20, 30)
        self.assertEqual(v.x, 10)
        self.assertEqual(v.y, 20)
        self.assertEqual(v.z, 30)
        self.assertEqual(v.get(), (10, 20, 30))
        v.set(40, 50, 60)
        self.assertEqual(v.get(), (40, 50, 60))

    def test_basic_arithmetic(self):
        v_1 = common.Vertex3(10, 20, 30)
        v_2 = common.Vertex3(10, 1, 5)

        self.assertEqual((v_1 - v_2).get(), (0, 19, 25))
        self.assertEqual((v_1 + v_2).get(), (20, 21, 35))
        self.assertEqual((v_1 * 10).get(), (100, 200, 300))
        self.assertEqual((v_1 / 10).get(), (1, 2, 3))

        v_1 += v_2
        self.assertEqual(v_1.get(), (20, 21, 35))

        v_1 -= v_2
        self.assertEqual(v_1.get(), (10, 20, 30))

        v_1 *= 10
        self.assertEqual(v_1.get(), (100, 200, 300))

        v_1 /= 10
        self.assertEqual(v_1.get(), (10, 20, 30))

        v_1.translate(10, 20, 30)
        self.assertEqual(v_1.get(), (20, 40, 60))

    def test_vector_ops(self):
        v_1 = common.Vertex3(10, 20, 30)
        v_2 = common.Vertex3(10, 1, 5)

        self.assertEqual(v_1.dot(v_2), 120)
        self.assertEqual(v_1.perp_dot(v_2), -190)
        v_1.rotate(v_2)
        self.assertEqual(v_1.get(), (80, 210, 30))
        v_1.unrotate(v_2)
        self.assertEqual(v_1.get(), (1010, 2020, 30))

        v_3 = common.Vertex3(0, -10, 0)
        self.assertEqual(v_3.length(), 10)
        v_4 = common.Vertex3(10, -10.5, 500)
        assert_math_isclose(v_4.length(), 500.210205078125)
        self.assertEqual(v_3.normal().get(), (0, -1, 0))
        v_3.normalize()
        self.assertEqual(v_3.get(), (0, -1, 0))
