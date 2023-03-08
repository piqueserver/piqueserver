import unittest
from unittest.mock import MagicMock

from piqueserver.scripts import markers
from piqueserver.player import FeatureConnection
from piqueserver.server import FeatureProtocol

from time import monotonic

class TestMarkersTime(unittest.TestCase):
    
    def test_markers_make_marker(self):
        """Asserts that the time for the last_marker set in 
        make marker is consistent with monotonic()
        """
        connection = FeatureConnection
        protocol = FeatureProtocol

        markers_protocol, markers_connection = markers.apply_script(protocol, connection, None)

        marker_class = MagicMock()
        marker_class.maximum_instances = None
        #marker_class = lambda self, proto, team, location: []
        
        markers_connection.protocol = MagicMock()
        markers_connection.team = MagicMock()

        markers_connection.make_marker(markers_connection, marker_class, (1, 1, 1))

        assert abs(markers_connection.last_marker - monotonic() < 0.1)


    def test_markers_on_animation_update(self):
        """Asserts that the functionality in on_animation_update() behaves as expected
        with regards to the times passed in for last_marker and sneak_presses.
        That is, a marker should be created if cooldown has passed, and sneak presses
        are as specified in on_animation_update() line 679
        """
        connection = FeatureConnection
        protocol = FeatureProtocol

        markers_protocol, markers_connection = markers.apply_script(protocol, connection, None)

        # Mock everything we need such that we can pass all if statements and code
        # that leads to checking if the functionality was as expected with regards
        # to input times, i.e. the monotonic() calls.
        markers_connection.allow_markers = True

        markers_protocol.allow_markers = True
        markers_protocol.broadcast_contained = lambda msg, team="team": []

        
        markers_connection.world_object = MagicMock()
        markers_connection.world_object.sneak = False
        markers_connection.protocol = markers_protocol

        markers_connection.last_marker = monotonic() - markers.COOLDOWN - 1
        markers_connection.sneak_presses = [monotonic() - markers.VV_TIMEFRAME + 1]
        markers_connection.get_there_location = lambda: (1, 1)
        markers_connection.team = "team"
        markers_connection.player_id = 123

        markers_connection.make_marker = MagicMock()  
        markers_connection.fly = False

        markers_connection.on_animation_update(markers_connection, False, False, True, False)

        # Checks that a marker has been created given the above input times for 
        # last_marker and sneak_presses
        markers_connection.make_marker.assert_called_once()

    def test_markers_on_chat(self):
        """Asserts that time dependent functionality in on_chat() behaves
        as expected with regards to the time passed for last_marker.
        That is, send_chat() should be called with S_WAIT since the input
        time is within the cooldown window
        """
        connection = FeatureConnection
        protocol = FeatureProtocol

        markers_protocol, markers_connection = markers.apply_script(protocol, connection, False)
        
        # Use mocking to get to the part of on_chat() that is time dependent (elif on line 706)
        markers_connection.allow_markers = True
        markers_protocol.allow_markers = True

        markers_connection.team = MagicMock()
        markers_connection.team.spectator = False

        # Cooldown should not have passed as we want to check if the 
        # time is checked correctly we check if S_WAIT is sent via send_chat()
        markers_connection.last_marker = monotonic() - markers.COOLDOWN + 5
        markers_connection.send_chat = MagicMock()

        markers_connection.protocol = markers_protocol

        # To get past FeatureConnection on_chat() that is called in the return statement (the parent class)
        markers_connection.mute = False
        markers_connection.chat_limiter = MagicMock()
        markers_connection.record_event = MagicMock()
        markers_connection.chat_limiter.above_limit = MagicMock(return_value=False)
        markers_connection.name = "Player"

        # Message has to contain a trigger (such as "!help") so that we reach the time sensitive elif statement
        # on line 706 (needed to pass the try except block and end up in else)
        markers_connection.on_chat(markers_connection, "!help msg", None)

        # send_chat() should be sent with S_WAIT since the cooldown has not passed
        # since last_marker was placed (see line 706 in markers.py)
        markers_connection.send_chat.assert_called_once_with(markers.S_WAIT)

