"""
Gives a specified amount of medkits on spawn

Author: Booboorocks998
Maintainer: mat^2
"""

from piqueserver.commands import command
from pyspades.constants import FALL_KILL


@command('medkit', 'm')
def medkit(connection):
    if connection.medkits and connection.hp < 100:
        connection.set_hp(connection.hp + connection.protocol.heal_amount,
                          kill_type=FALL_KILL)
        connection.medkits -= 1
        connection.send_chat('You have been healed')
    else:
        connection.send_chat("You don't have any medkits or have full health!")


def apply_script(protocol, connection, config):
    default_medkits = config.get('medkits', 1)
    medkit_heal_amount = config.get('medkit_heal_amount', 40)

    class MedkitConnection(connection):
        medkits = 0

        def on_spawn(self, pos):
            self.medkits = default_medkits
            self.send_chat('You have %s medkit!' % self.medkits)
            return connection.on_spawn(self, pos)

    class MedkitProtocol(protocol):
        heal_amount = medkit_heal_amount

    return MedkitProtocol, MedkitConnection
