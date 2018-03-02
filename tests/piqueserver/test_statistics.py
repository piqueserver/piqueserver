"""
test piqueserver/server.py
"""

from unittest.mock import Mock
from twisted.trial import unittest
from piqueserver import statistics


class TestStatsServer(unittest.TestCase):
    def test_login_valid(self):
        server = statistics.StatsServer()
        server.timeout_call = Mock()
        server.transport = Mock()
        server.transport.loseConnection = Mock()
        server.factory = Mock()
        server.factory.password = "test"
        server.connection_accepted = Mock()
        msg = (b'{"type": "auth", "password": "test",'
               b'"name": "testname"}')
        server.stringReceived(msg)
        self.assertTrue(server.connection_accepted.called)
        self.assertFalse(server.transport.loseConnection.called)

    def test_login_invalid(self):
        server = statistics.StatsServer()
        server.timeout_call = Mock()
        server.transport = Mock()
        server.transport.loseConnection = Mock()
        server.factory = Mock()
        server.factory.password = "falsepass"
        server.connection_accepted = Mock()
        msg = (b'{"type": "auth", "password": "test",'
               b'"name": "testname"}')
        server.stringReceived(msg)
        self.assertFalse(server.connection_accepted.called)
        self.assertTrue(server.transport.loseConnection.called)
