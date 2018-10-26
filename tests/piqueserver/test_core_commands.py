from twisted.trial import unittest
from unittest.mock import Mock

from piqueserver import core_commands


class DummyTest(unittest.TestCase):
    def test_get_ban_argument(self):
        conn = Mock()
        conn.protocol = Mock()
        conn.protocol.default_ban_time = 1423
        dur, reas = core_commands.get_ban_arguments(conn, ["120", "123"])
        self.assertEqual(dur, 120)
        self.assertEqual(reas, "123")

        dur, reas = core_commands.get_ban_arguments(conn, [])
        self.assertEqual(dur, 1423)
        self.assertEqual(reas, None)

        dur, reas = core_commands.get_ban_arguments(conn, ["hi", "you"])
        self.assertEqual(dur, 1423)
        self.assertEqual(reas, "hi you")

        # Does this make sense? Not sure it does
        # This is what the code does atm, anyway
        dur, reas = core_commands.get_ban_arguments(conn, ["perma", "you"])
        self.assertEqual(dur, None)
        self.assertEqual(reas, "you")
