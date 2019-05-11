"""
tests for bytes.pyx
"""
from twisted.trial import unittest

from pyspades.bytes import ByteReader, ByteWriter

class TestByteReader(unittest.TestCase):
    """tests for ByteReader"""

    def test_read(self):
        inputs = (
            b"\x00\xF0\xFF",
            bytes(b"\x00\xF0\xFF"),
            bytearray([0x00, 0xF0, 0xFF]),
        )

        for i in inputs:
            reader = ByteReader(i)
            self.assertEqual(reader.read(1), b"\x00")
            self.assertEqual(reader.read(), b"\xF0\xFF")

    def test_readbyte(self):
        inputs = (
            b"\xF1\xF1\xF1",
            bytes(b"\xF1\xF1\xF1"),
            bytearray([0xF1, 0xF1, 0xF1]),
        )
        for i in inputs:
            reader = ByteReader(i)

            self.assertEqual(reader.readByte(False), -15)
            self.assertEqual(reader.readByte(True), 241)

    def test_readshort(self):
        inputs = (
            b"\xF1\x00\xF1\x00",
            bytes(b"\xF1\x00\xF1\x00"),
            bytearray([0xF1, 0x00, 0xF1, 0x00]),
        )
        for i in inputs:
            reader = ByteReader(i)

            self.assertEqual(reader.readShort(False), -3840)
            self.assertEqual(reader.readShort(True), 61696)

            # Small endian
            reader = ByteReader(i)
            self.assertEqual(reader.readShort(False, False), 241)
            self.assertEqual(reader.readShort(True, False), 241)

    def test_readint(self):
        inputs = (
            b"\xF1\x00\xF1\x00\xF1\x00\xF1\x00",
            bytes(b"\xF1\x00\xF1\x00\xF1\x00\xF1\x00"),
            bytearray([0xF1, 0x00, 0xF1, 0x00, 0xF1, 0x00, 0xF1, 0x00]),
        )
        for i in inputs:
            reader = ByteReader(i)

            self.assertEqual(reader.readInt(False), -251596544)
            self.assertEqual(reader.readInt(True), 4043370752)

            # Small endian
            reader = ByteReader(i)
            self.assertEqual(reader.readInt(False, False), 15794417)
            self.assertEqual(reader.readInt(True, False), 15794417)

    def test_readfloat(self):
        inputs = (
            b"\xF1\x00\xF1\x00\xF1\x00\xF1\x00",
            bytes(b"\xF1\x00\xF1\x00\xF1\x00\xF1\x00"),
            bytearray([0xF1, 0x00, 0xF1, 0x00, 0xF1, 0x00, 0xF1, 0x00]),
        )
        for i in inputs:
            reader = ByteReader(i)

            self.assertEqual(reader.readFloat(False), 2.2132692287005784e-38)
            self.assertEqual(reader.readFloat(True), -6.384869180745487e+29)

    # TODO: test rest of bytes.pyx, moving on to more useful modules for now
