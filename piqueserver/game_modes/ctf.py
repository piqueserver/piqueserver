"""
Dummy CTF gamemode for consistency.
"""

from pyspades.constants import CTF_MODE


def apply_script(protocol, connection, config):
    class CtfProtocol(protocol):
        game_mode = CTF_MODE

    return CtfProtocol, connection
