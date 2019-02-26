"""
test piqueserver/extensions.py
"""
import os

from twisted.trial import unittest

from piqueserver import extensions
from piqueserver.config import config
from piqueserver.server import FeatureProtocol
from piqueserver.player import FeatureConnection

class TestExtensions(unittest.TestCase):
    # Define scripts
    script_names = ['test_script_game_mode', 'test_script_regular']
    script_names_length = len(script_names)
    # Get current directory
    curr_dir = os.getcwd()
    script_dir = os.path.join(curr_dir, 'piqueserver/test_scripts/')
    # Load modules
    script_objects = extensions.load_scripts(script_names, script_dir, 'testscript')

    def test_checkscripts(self):
        scripts = []
        self.assertTrue(extensions.check_scripts(scripts))

        scripts = ['one']
        self.assertTrue(extensions.check_scripts(scripts))

        scripts = ['one', 'two', 'three']
        self.assertTrue(extensions.check_scripts(scripts))

        scripts = ['one', 'two', 'one', 'three']
        self.assertFalse(extensions.check_scripts(scripts))

        scripts = ['one', 'two', 'one', 'three', 'three']
        self.assertFalse(extensions.check_scripts(scripts))

    def test_load_scripts(self):
        self.assertTrue(len(self.script_objects) == self.script_names_length)
        # apply_script method should exist in all modules
        for i in range(0,len(self.script_objects)):
            self.assertTrue("apply_script" in dir(self.script_objects[i]))

    def test_apply_scripts(self):
        protocol_class = FeatureProtocol
        connection_class = FeatureConnection

        self.assertNotEqual(protocol_class.game_mode, "testing")
        self.assertTrue(connection_class.killing)

        (protocol_class, connection_class) = extensions.apply_scripts(self.script_objects, config, protocol_class, connection_class)

        self.assertEqual(protocol_class.game_mode, "testing")
        self.assertFalse(connection_class.killing)

