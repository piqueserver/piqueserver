"""
test piqueserver/scripts/badmin.py
"""

from twisted.trial import unittest
from twisted.internet import reactor
from unittest.mock import MagicMock
from piqueserver.scripts.badmin import *

def get_mock_block():
    b = MagicMock(), MagicMock()
    return b

class TestBAdmin(unittest.TestCase):

    def test_score_grief_0(self):
        connection = MagicMock()
        player = MagicMock()
        score = score_grief(connection, player)
        self.assertTrue(score is 0)

    def test_score_grief_1(self):
        connection = MagicMock()
        player = MagicMock()
        player.blocks_removed = [(reactor.seconds(), get_mock_block())]
        score = score_grief(connection, player)
        self.assertTrue(score is 0)
