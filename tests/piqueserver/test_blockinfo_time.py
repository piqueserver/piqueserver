import unittest
from unittest.mock import MagicMock

from piqueserver.scripts import blockinfo
from piqueserver.player import FeatureConnection
from piqueserver.server import FeatureProtocol

from time import monotonic

class TestBlockInfoTime(unittest.TestCase):

    def test_blockinfo_on_block_removed(self):
        """Asserts that the time the block was removed is not prone to leap seconds
        by checking that it is always within a small error range from monotonic()
        """
        connection = FeatureConnection
        protocol = FeatureProtocol

        blockinfo_protocol, blockinfo_connection = blockinfo.apply_script(protocol, connection, None)

        blockinfo_connection.blocks_removed = None
        blockinfo_connection.protocol = MagicMock()
        blockinfo_connection.protocol.block_info = None

        blockinfo_connection.on_block_removed(blockinfo_connection, 1, 1, 1)
        time_of_removal = monotonic()

        assert abs(time_of_removal - blockinfo_connection.blocks_removed[0][0]) < 0.1 


    def test_blockinfo_on_kill(self):
        """Asserts that the time the kill happened is not prone to leap seconds
        by checking that it is always within a small error range from monotonic()
        """
        killer = MagicMock()
        killer.team = "Team"

        killer.teamkill_times = None

        connection = FeatureConnection
        protocol = FeatureProtocol

        blockinfo_protocol, blockinfo_connection = blockinfo.apply_script(protocol, connection, None)
        blockinfo_connection.team = "Team"
        
        blockinfo_connection.on_kill(blockinfo_connection, killer, None, None)

        time_of_kill = monotonic()

        assert abs(time_of_kill - killer.teamkill_times[0]) < 0.1
    

    def test_badmin_grief_check(self):
        """Asserts that the result of badmin grief_check() is consistent with
        the times spefified in the input protocol and player
        """
        player = "#123"
        connection = MagicMock()

        connection.protocol = MagicMock()

        # Set up the player object to be checked within grief_check()
        player_object = MagicMock()

        # Removed 5 blocks in the last 2 minutes
        # Last one 9 seconds ago ( range = [5, 10) )
        player_object.blocks_removed = [(monotonic() - i, ("name", "team")) for i in range(5, 10)]

        # Switched team 1 minute ago
        player_object.last_switch = monotonic() - 60

        # Killed 10 teammembers in the last 2 minutes
        player_object.teamkill_times = [monotonic() - i for i in range(10, 20)]

        # To be returned by get_player() inside of grief_check()
        connection.protocol.players = {123: player_object}

        result_msg = blockinfo.grief_check(connection, player, minutes=2)

        # Check that the output contains the expected values, all of these values
        # are dependent on the time being correct.
        assert "removed 5 blocks in the last 2.0 minutes" in result_msg
        assert "Last one was destroyed 9 seconds ago" in result_msg
        assert "team 1 minute ago" in result_msg
        assert "killed 10 teammates in the last 2.0 minutes" in result_msg
        
