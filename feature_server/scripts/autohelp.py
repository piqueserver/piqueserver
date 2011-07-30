from twisted.internet import reactor
import re

deuce_name_pattern = re.compile("Deuce\d?\d?$")
chat_pattern = re.compile(".*how.*(set|change|choo?se|make|pick).*(name|nick)",
    re.IGNORECASE)

def deuce_howto_match(player, msg):
    return chat_pattern.match(msg) is not None

def apply_script(protocol, connection, config):
    def send_help(connection):
        connection.protocol.send_chat("TO CHANGE YOUR NAME: Start Menu-> "
            "All Programs-> Ace of Spades-> Configuration")
        connection.protocol.irc_say("* Sent help to %s" % connection.name)
    
    class AutoHelpConnection(connection):
        def on_chat(self, value, global_message):
            if deuce_howto_match(self, value):
                reactor.callLater(1.0, send_help, self)
            return connection.on_chat(self, value, global_message)
    return protocol, AutoHelpConnection