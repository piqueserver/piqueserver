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
    # Define test scripts
    script_names = ['test_script_game_mode', 'test_script_regular']
    script_names_length = len(script_names)

    def get_test_scripts(self):
        # Get test scripts directory
        script_dir = os.path.join(os.path.dirname(__file__), "test_scripts/")
        # Load modules
        return extensions.load_scripts(
            self.script_names, script_dir, 'testscript')

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
        script_objects = self.get_test_scripts()
        self.assertTrue(len(script_objects) == self.script_names_length)

        # apply_script method should exist in all modules
        for script in script_objects[:]:
            self.assertTrue("apply_script" in dir(script))

    def test_apply_scripts(self):
        script_objects = self.get_test_scripts()
        protocol_class = FeatureProtocol
        connection_class = FeatureConnection

        # TODO: figure out what this was supposed to do
        # self.assertNotEqual(protocol_class.game_mode, "testing")
        # self.assertTrue(connection_class.killing)

        (protocol_class, connection_class) = extensions.apply_scripts(
            script_objects, config, protocol_class, connection_class)

        # self.assertEqual(protocol_class.game_mode, "testing")
        # self.assertFalse(connection_class.killing)

    def test_check_game_mode(self):
        self.assertFalse(extensions.check_game_mode('ctf'))
        self.assertFalse(extensions.check_game_mode('tc'))
        self.assertTrue(extensions.check_game_mode('tcc'))
        self.assertTrue(extensions.check_game_mode('md'))
