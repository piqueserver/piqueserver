"""
test pyspades/server.py
"""

from twisted.trial import unittest
from unittest.mock import Mock
from pyspades import server
from pyspades.server import ServerProtocol


class BaseConnectionTest(unittest.TestCase):
    def test_test(self):
        pass


class GameLifecycleTest(unittest.TestCase):
    """``start_game`` / ``end_game`` are guarded by ``_game_active`` so each
    hook fires at most once per transition."""

    def _make_protocol(self):
        # Bypass __init__ (which opens an enet socket).
        protocol = ServerProtocol.__new__(ServerProtocol)
        protocol._game_active = False
        protocol.on_game_start = Mock()
        protocol.on_game_end = Mock()
        return protocol

    def test_start_fires_once_until_end(self):
        protocol = self._make_protocol()
        protocol.start_game()
        protocol.start_game()
        self.assertEqual(protocol.on_game_start.call_count, 1)
        self.assertTrue(protocol._game_active)

    def test_end_without_start_is_noop(self):
        protocol = self._make_protocol()
        protocol.end_game()
        protocol.on_game_end.assert_not_called()
        self.assertFalse(protocol._game_active)

    def test_end_fires_once_until_start(self):
        protocol = self._make_protocol()
        protocol.start_game()
        protocol.end_game()
        protocol.end_game()
        self.assertEqual(protocol.on_game_end.call_count, 1)
        self.assertFalse(protocol._game_active)

    def test_full_cycle(self):
        protocol = self._make_protocol()
        protocol.start_game()
        protocol.end_game()
        protocol.start_game()
        protocol.end_game()
        self.assertEqual(protocol.on_game_start.call_count, 2)
        self.assertEqual(protocol.on_game_end.call_count, 2)
