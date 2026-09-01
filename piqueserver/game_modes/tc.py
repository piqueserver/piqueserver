"""
Dummy TC gamemode for consistency.
"""

from pyspades.constants import TC_MODE


def apply_script(protocol, connection, config):
    class TcProtocol(protocol):
        game_mode = TC_MODE

    return TcProtocol, connection
