import re

deuce_name_pattern = re.compile("Deuce\d?\d?$")
chat_pattern = re.compile(".*how.*change.*name", re.IGNORECASE)

def deuce_howto_match(player, msg):
    return (not deuce_name_pattern.match(player.name) is None and
        not chat_pattern.match(msg) is None)

def apply_script(protocol, connection, config):
    class AutoHelpConnection(connection):
        def on_chat(self, value, global_message):
            if deuce_howto_match(self, value):
                self.send_chat("TO CHANGE YOUR NAME: Start Menu-> "
                    "All Programs-> Ace of Spades-> Configuration")
                self.protocol.irc_say("Sent help to %s" % self.name)
            connection.on_chat(self, value, global_message)
    return protocol, AutoHelpConnection