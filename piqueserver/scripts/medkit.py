"""
Gives a specified amount of medkits on spawn

Commands
^^^^^^^^

* ``/medkit or /m`` utilizes available medkits to heal

Options
^^^^^^^

.. code-block:: guess

   [medkit]
   medkits = 1 # no. of medkits
   medkit_heal_amount = 40 # how much hp. it gives

.. codeauthor:: Booboorocks998 & mat^2
"""

from piqueserver.commands import command
from piqueserver.config import config
from pyspades.constants import FALL_KILL

medkit_config = config.section("medkit")
default_medkits = medkit_config.option("medkits", 1)
medkit_heal_amount = medkit_config.option("medkit_heal_amount", 40)

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
    class MedkitConnection(connection):
        medkits = 0

        def on_spawn(self, pos):
            self.medkits = default_medkits.get()
            self.send_chat('You have %s medkit!' % self.medkits)
            return connection.on_spawn(self, pos)

    class MedkitProtocol(protocol):
        heal_amount = medkit_heal_amount.get()

    return MedkitProtocol, MedkitConnection
