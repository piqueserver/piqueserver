"""
Kicks jerks for 'PRESS ALT-F4 FOR AIRSTRIKES' and so on.

Options
^^^^^^^

.. code-block:: guess

   [antijerk]
   ban_duration = "15min"

.. codeauthor:: ?
"""

import re
from piqueserver.config import config, cast_duration

chat_pattern = re.compile(".*(airstrike).*(esc|escape|alt-f4|alt f4)",
                          re.IGNORECASE)
chat_pattern_2 = re.compile(".*(esc|escape|alt-f4|alt f4).*(airstrike)",
                            re.IGNORECASE)
admin_pattern = re.compile(".*(admin)",
                           re.IGNORECASE)
antijerk_config = config.section("antijerk")
ban_duration = antijerk_config.option("ban_duration", default="15min", cast=cast_duration)


def antijerk_match(player, msg):
    if not (player.user_types.trusted or player.admin):
        return chat_pattern.match(msg) or chat_pattern_2.match(msg) or\
            admin_pattern.match(player.name)


def apply_script(protocol, connection, config):
    def jerk_kick(connection):
        connection.ban('Autoban: anti-jerk', ban_duration.get())

    class AntiJerkConnection(connection):

        def on_chat(self, value, global_message):
            if antijerk_match(self, value):
                jerk_kick(self)
            else:
                return connection.on_chat(self, value, global_message)

        def on_login(self, name):
            if admin_pattern.match(name):
                self.send_chat('Anti-jerk: Please remove "Admin" from your ' +
                               'name: TALKING WILL AUTOBAN YOU!')
            return connection.on_login(self, name)

    return protocol, AntiJerkConnection
