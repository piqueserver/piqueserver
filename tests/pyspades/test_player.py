"""
test pyspades/protocol.py
"""

from twisted.trial import unittest
from pyspades import player
from unittest.mock import Mock

class BaseConnectionTest(unittest.TestCase):
    def test_dummy(self):
        pass

    def test_repr(self):
        ply = player.ServerConnection(Mock(), Mock())
        repr(ply)
