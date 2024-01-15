import unittest
from unittest.mock import MagicMock
from time import monotonic

from piqueserver.scripts import airstrike2
from piqueserver.player import FeatureConnection
from piqueserver.server import FeatureProtocol

class TestAirstrike2Time(unittest.TestCase):
    
    def test_start_zoomv(self):
        """Asserts that functionality inside of start_zoomv has the expected behavior
        depending on the last airstrike time, relative to monotonic()
        """
        connection = FeatureConnection
        protocol = FeatureProtocol

        airstrike_protocol, airstrike_connection = airstrike2.apply_script(protocol, connection, None)
        airstrike_connection.team = MagicMock()

        # Cooldown is 30 sec and we want to trigger the if statement on line 209
        # to check that the times work (function returns right after this)
        since_last_strike = 10
        airstrike_connection.team.last_airstrike = monotonic() - since_last_strike

        airstrike_connection.send_zoomv_chat = MagicMock()

        # Call start_zoomv
        airstrike_connection.start_zoomv(airstrike_connection)

        # Check that send_zoomv_chat was called with the correct message depending on the
        # team cooldown and s cooldown
        expected_message = airstrike2.S_COOLDOWN.format(seconds=int(airstrike2.TEAM_COOLDOWN-since_last_strike))
        airstrike_connection.send_zoomv_chat.assert_called_once_with(expected_message)

    def test_send_zoomv_chat(self):
        """Asserts that functionality inside of send_zoomv_chat has the expected behavior 
        depending on the time for the last_zoomv_message, relative to monotonic(),
        and that the new last_zoomv_message time is updated accordingly
        """
        connection = FeatureConnection
        protocol = FeatureProtocol

        airstrike_protocol, airstrike_connection = airstrike2.apply_script(protocol, connection, None)

        # Set the last message 2 seconds ago to enter the if statement branch that depends
        # on time
        airstrike_connection.last_zoomv_message = monotonic() - 2
        airstrike_connection.send_chat = MagicMock()

        # Call send_zoomv_chat
        airstrike_connection.send_zoomv_chat(airstrike_connection, "dummy")

        # Check that the time for the message sent is relative monotonic()
        # and that the functionality inside is called as expected
        assert abs(airstrike_connection.last_zoomv_message - monotonic()) < 0.1
        airstrike_connection.send_chat.assert_called_once_with("dummy")
        
