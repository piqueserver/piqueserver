"""
test piqueserver/scripts/badmin.py
"""

from twisted.trial import unittest
from unittest.mock import MagicMock
from piqueserver.scripts.badmin import score_grief

class TestBAdmin(unittest.TestCase):

    def test_score_grief_0(self):
        connection = MagicMock()
        player = MagicMock()
        score = score_grief(connection, player)
        self.assertTrue(score is 0)
