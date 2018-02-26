"""
test piqueserver/scripts/blockinfo.py
"""
from twisted.trial import unittest
from unittest.mock import MagicMock, patch
from piqueserver.scripts.blockinfo import grief_check

def get_player_side_effect(protocol, player, spectators=True):
    return player

class TestBlockinfo(unittest.TestCase):

    @patch('piqueserver.scripts.blockinfo.get_player', side_effect=get_player_side_effect)
    def test_grief_check_0(self, get_player):
        connection = MagicMock()
        player = MagicMock(last_switch=None)
        message = grief_check(connection, player, minutes=3)
        self.assertTrue(message.endswith("removed no blocks in the last 3.0 minutes."))
