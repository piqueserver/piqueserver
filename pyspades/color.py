from math import floor
import colorsys
from typing import Tuple

ColorTuple = Tuple[float, float, float]


def wrap(minimum: float, maximum: float, value: float) -> float:
    return value - floor(
        (value - minimum) / (maximum - minimum)) * (maximum - minimum)


def hsb_to_rgb(hue: float, sat: float, bri: float) -> ColorTuple:
    r, g, b = colorsys.hsv_to_rgb(hue, sat, bri)
    return int(r * 255), int(g * 255), int(b * 255)


def interpolate_rgb(xyz1, xyz2, t):
    (r1, g1, b1) = xyz1
    (r2, g2, b2) = xyz2
    return (int(r1 + (r2 - r1) * t),
            int(g1 + (g2 - g1) * t),
            int(b1 + (b2 - b1) * t))


def interpolate_hsb(xyz1: ColorTuple, xyz2: ColorTuple, t: float) -> ColorTuple:
    (h1, s1, b1) = xyz1
    (h2, s2, b2) = xyz2
    return (h1 + (h2 - h1) * t, s1 + (s2 - s1) * t, b1 + (b2 - b1) * t)


def rgb_distance(xyz1, xyz2):
    (r1, g1, b1) = xyz1
    (r2, g2, b2) = xyz2
    return int(abs(r1 - r2) + abs(g1 - g2) + abs(b1 - b2))
