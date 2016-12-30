"""
Demolition man script.
Copyright (c) 2013 learn_more
See the file license.txt or http://opensource.org/licenses/MIT for copying permission.

Restocks the user when reloading / throwing a nade.
"""

from commands import add, admin

DEMOLITION_ENABLED_AT_ROUND_START = False

@admin
def toggledemo(connection):
	connection.protocol.demolitionEnabled = not connection.protocol.demolitionEnabled
	message = 'Demolition is now disabled'
	if connection.protocol.demolitionEnabled:
		message = 'Demolition is now enabled'
	connection.protocol.send_chat(message, irc = True)
	return 'ok :)'

add(toggledemo)

def apply_script(protocol, connection, config):
	class DemolitionProtocol(protocol):
		demolitionEnabled = DEMOLITION_ENABLED_AT_ROUND_START

		def on_map_change(self, map):
			self.demolitionEnabled = DEMOLITION_ENABLED_AT_ROUND_START
			return protocol.on_map_change(self, map)

	class DemolitionConnection(connection):

		def _on_reload(self):
			if self.protocol.demolitionEnabled:
				self.refill()
			return connection._on_reload(self)

		def on_grenade_thrown(self, grenade):
			if self.protocol.demolitionEnabled:
				self.refill()
			return connection.on_grenade_thrown(self, grenade)

		def on_spawn(self, pos):
			if self.protocol.demolitionEnabled:
				self.send_chat('You are the demolition man, grenades & ammo will be restocked!')
			return connection.on_spawn(self, pos)

	return DemolitionProtocol, DemolitionConnection
