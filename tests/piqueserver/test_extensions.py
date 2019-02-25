"""
test piqueserver/extensions.py
"""

from twisted.trial import unittest
import piqueserver.extensions

class TestExtensions(unittest.TestCase):
    def test_checkscripts(self):
        scripts = []
        self.assertTrue(piqueserver.extensions.check_scripts(scripts))

        scripts = ['one']
        self.assertTrue(piqueserver.extensions.check_scripts(scripts))

        scripts = ['one', 'two', 'three']
        self.assertTrue(piqueserver.extensions.check_scripts(scripts))

        scripts = ['one', 'two', 'one', 'three']
        self.assertFalse(piqueserver.extensions.check_scripts(scripts))

        scripts = ['one', 'two', 'one', 'three', 'three']
        self.assertFalse(piqueserver.extensions.check_scripts(scripts))
