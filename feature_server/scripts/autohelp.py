"""
Helps Deuces automagically when they ask in the chat for help.

Maintainer: ?
"""

from twisted.internet import reactor
import re

deuce_name_pattern = re.compile("Deuce\d?\d?$")
nick_chat_pattern = re.compile(".*how.*(set|change|choo?se|make|pick).*(name|nick)",
    re.IGNORECASE)
airstrike_chat_pattern = re.compile(".*how.*(to|make|use|get).*(airstrike|killstreak|airsupport)",
    re.IGNORECASE)
	
def deuce_howto_match(player, msg):
	return (not deuce_name_pattern.match(player.name) is None and
		not nick_chat_pattern.match(msg) is None)
def airstrike_howto_match(player, msg):
	return (not airstrike_chat_pattern.match(msg) is None)
	
def apply_script(protocol, connection, config):
	def send_help_nick(connection):
		connection.protocol.send_chat("TO CHANGE YOUR NAME: Start Menu-> "
			"All Programs-> Ace of Spades-> Configuration")
		connection.protocol.irc_say("* Sent nick help to %s" % connection.name)
	
	def send_help_airstrike(connection):
		connection.protocol.send_chat("TO USE AN AIRSTRIKE: Once you have 15 points, "
			"get a 6 killstreak ->                  "
			"Then type /airstrike G4 if you want the strike to hit G4")
		connection.protocol.irc_say("* Sent airstrike help to %s" % connection.name)
		
	class AutoHelpConnection(connection):
		def on_chat(self, value, global_message):
			if deuce_howto_match(self, value):
				reactor.callLater(1.0, send_help_nick, self)
			if airstrike_howto_match(self, value):
				reactor.callLater(1.0, send_help_airstrike, self)
			return connection.on_chat(self, value, global_message)
	return protocol, AutoHelpConnection