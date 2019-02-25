"""
test piqueserver/extensions.py
"""
import os

from twisted.trial import unittest
from piqueserver import extensions
from piqueserver.config import config
# from piqueserver.server import scripts_option
scripts_option = config.option('test_scripts', default=[], validate=extensions.check_scripts)

class TestExtensions(unittest.TestCase):
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
        # Define scripts
        script_names = ['test_script_game_mode', 'test_script_regular']
        script_names_length = len(script_names)
        # Get current directory
        curr_dir = os.getcwd()
        script_dir = os.path.join(curr_dir, 'piqueserver/test_scripts/')

        modules = extensions.load_scripts(script_names, script_dir)
        self.assertTrue(len(modules) == script_names_length)

        # apply_script method should exist in all modules
        for i in range(0,len(modules)):
            self.assertTrue("apply_script" in dir(modules[i]))

    def test_apply_scripts(self):
        # How to test if a single script has been applied?
        # Should return a protocol and connection class that has been modified
        # Compare first protocol class and the modified protocol class ?
        # Same with connection?
        self.fail()

