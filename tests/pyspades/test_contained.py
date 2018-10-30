"""
tests for contained.pyx
"""
from twisted.trial import unittest

from pyspades import contained
from pyspades.bytes import ByteWriter, ByteReader

class TestContained(unittest.TestCase):
    """tests for ByteReader"""

    def test_write_feature_exchange(self):
        features = [
            (1, b"\xFF\x12"),
            (2, b"a"),
            (5, b"\x00"),
            (255, b"A" * 12),
        ]

        cnt = contained.FeatureExchange()
        cnt.features = features
        self.assertEqual(
            bytes(cnt.generate()),
            b'\x01\x02\xff\x12\x02\x01a\x05\x01\x00\xff\x0cAAAAAAAAAAAA'
        )

    def test_write_invalid_feature_exchange(self):
        cnt = contained.FeatureExchange()

        cnt.features = [(1, b"\x00" * 256)]
        self.assertRaises(ValueError, cnt.generate)

        cnt.features = [(-2, b"\x00")]
        self.assertRaises(ValueError, cnt.generate)

        cnt.features = [(300, b"\x00")]
        self.assertRaises(ValueError, cnt.generate)

    def test_read_feature_exchange(self):
        data = b'\x10\x03\xff\x00\x12\x02\x01a\xff\x03123'

        reader = ByteReader(data)
        cnt = contained.FeatureExchange(reader)
        self.assertEqual(
            cnt.features,
            [
                (16, b"\xff\x00\x12"),
                (2, b"a"),
                (255, b"123"),
            ]
        )
