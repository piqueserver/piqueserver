import unittest
from unittest.mock import MagicMock

import piqueserver.scripts.afk as afk
from piqueserver.config import config

from piqueserver.player import FeatureConnection
from piqueserver.server import FeatureProtocol

from time import monotonic



class TestAfkTime(unittest.TestCase):
    def test_afk(self):

        connection = MagicMock()
        connection.protocol = MagicMock()
        player_obj = MagicMock()
        player_obj.name = "TestPlayer"
        player_obj.last_activity =  monotonic() - 600
        connection.protocol.players = {1 : player_obj}

        result = afk.afk(connection, connection.protocol.players[1])
        
        self.assertEqual(result, "TestPlayer has been inactive for 10 minutes")
