"""
test piqueserver/scripts/blockinfo.py
"""
from twisted.trial import unittest
from twisted.internet.reactor import seconds
from unittest.mock import MagicMock, patch
from piqueserver.scripts.blockinfo import grief_check

def get_player_side_effect(protocol, player, spectators=True):
    return player

class TestBlockinfo(unittest.TestCase):

    @patch('piqueserver.scripts.blockinfo.get_player', side_effect=get_player_side_effect)
    def test_grief_check_0(self, get_player):
        """
        Just passing through the function with default values (except for time)
        should cause the function to return a string stating that no blocks were removed.
        """
        connection = MagicMock()
        player = MagicMock(last_switch=None)
        message = grief_check(connection, player, minutes=3)
        self.assertTrue(message.endswith("removed no blocks in the last 3.0 minutes."))

    @patch('piqueserver.scripts.blockinfo.get_player', side_effect=get_player_side_effect)
    def test_grief_check_1(self, get_player):
        """
        If the player changed teams less than a second ago, the function should
        state this.
        """
        connection = MagicMock()
        player = MagicMock(last_switch=seconds())
        message = grief_check(connection, player, minutes=3)
        self.assertTrue(message.endswith("team less than a second ago."))
