"""
test piqueserver/server.py
"""

from itertools import count

from twisted.trial import unittest
from unittest.mock import Mock

import piqueserver.server
from piqueserver.server import FeatureProtocol


class TestServer(unittest.TestCase):
    def test_dummy(self):
        piqueserver.server


class FeatureProtocolGameLifecycleTest(unittest.TestCase):
    """``FeatureProtocol`` wires ``on_game_start`` into map changes, round
    restarts, and externally-forced map advances (time-up, ``/advancemap``,
    ``/loadmap``)."""

    def _make_protocol(self, advance_on_win=0, game_active=False,
                       advancing=False):
        # Bypass __init__ — it touches the network, config, IRC, etc.
        protocol = FeatureProtocol.__new__(FeatureProtocol)
        protocol._game_active = game_active
        protocol._advancing = advancing
        protocol.on_game_start = Mock()
        protocol.advance_on_win = advance_on_win
        protocol.win_count = count(1)
        protocol.advance_rotation = Mock()
        protocol.irc_say = Mock()
        protocol.set_fog_color = Mock()
        protocol.default_fog = (0, 0, 0)
        protocol.map_info = Mock()
        protocol.map_info.on_map_change = None
        protocol.map_info.on_map_leave = None
        return protocol

    def test_on_map_change_fires_on_game_start(self):
        protocol = self._make_protocol()
        protocol.on_map_change(Mock())
        protocol.on_game_start.assert_called_once()
        self.assertTrue(protocol._game_active)

    def test_on_map_change_clears_advancing_flag(self):
        protocol = self._make_protocol(advancing=True)
        protocol.on_map_change(Mock())
        self.assertFalse(protocol._advancing)

    def test_on_game_end_bails_while_advancing(self):
        # When advance_rotation has set _advancing=True before firing
        # end_game(), the built-in advance/restart logic must not run —
        # otherwise it would race the in-flight map change.
        protocol = self._make_protocol(advance_on_win=1, game_active=True,
                                       advancing=True)
        FeatureProtocol.on_game_end(protocol)
        protocol.advance_rotation.assert_not_called()
        protocol.on_game_start.assert_not_called()

    def test_on_game_end_starts_next_round_on_same_map(self):
        # advance_on_win=0 → round restarts in place, no map advance.
        protocol = self._make_protocol(advance_on_win=0)
        FeatureProtocol.on_game_end(protocol)
        protocol.advance_rotation.assert_not_called()
        protocol.on_game_start.assert_called_once()
        self.assertTrue(protocol._game_active)

    def test_on_game_end_advances_without_restarting_in_place(self):
        # advance_on_win=1 → every game advances; the new map's on_map_change
        # is responsible for on_game_start, not on_game_end.
        protocol = self._make_protocol(advance_on_win=1)
        FeatureProtocol.on_game_end(protocol)
        protocol.advance_rotation.assert_called_once()
        protocol.on_game_start.assert_not_called()
