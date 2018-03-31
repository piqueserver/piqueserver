"""
test piccolo/server.py
"""

from twisted.trial import unittest
import piccolo.server


class TestServer(unittest.TestCase):
    def test_dummy(self):
        piccolo.server

    def test_checkscripts(self):
        scripts = []
        self.assertTrue(piccolo.server.check_scripts(scripts))

        scripts = ['one']
        self.assertTrue(piccolo.server.check_scripts(scripts))

        scripts = ['one', 'two', 'three']
        self.assertTrue(piccolo.server.check_scripts(scripts))

        scripts = ['one', 'two', 'one', 'three']
        self.assertFalse(piccolo.server.check_scripts(scripts))

        scripts = ['one', 'two', 'one', 'three', 'three']
        self.assertFalse(piccolo.server.check_scripts(scripts))
