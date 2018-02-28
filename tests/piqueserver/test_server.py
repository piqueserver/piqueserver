"""
test piqueserver/server.py
"""

from twisted.trial import unittest
import piqueserver.server


class TestServer(unittest.TestCase):
    def test_dummy(self):
        piqueserver.server

    def test_checkscripts(self):
        scripts = []
        self.assertTrue(piqueserver.server.check_scripts(scripts))

        scripts = ['one']
        self.assertTrue(piqueserver.server.check_scripts(scripts))

        scripts = ['one', 'two', 'three']
        self.assertTrue(piqueserver.server.check_scripts(scripts))

        scripts = ['one', 'two', 'one', 'three']
        self.assertFalse(piqueserver.server.check_scripts(scripts))

        scripts = ['one', 'two', 'one', 'three', 'three']
        self.assertFalse(piqueserver.server.check_scripts(scripts))
