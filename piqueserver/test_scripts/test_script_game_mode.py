"""
A game mode script that can be used for testing. See file test_extension.

Version 1(2019.02.25)

.. codeauthor:: AlbertoDubbini
"""

from pyspades.constants import CTF_MODE

def apply_script(protocol, connection, config):

    class TestScriptRegularProtocol(protocol):
        game_mode = CTF_MODE
        def test_true(self):
            return True

    class TestScriptRegularConnection(connection):

        def test_false(self):
            return False

    return TestScriptRegularProtocol, TestScriptRegularConnection
