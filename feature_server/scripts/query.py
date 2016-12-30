"""
Query support.
Copyright (c) 2013 learn_more
See the file license.txt or http://opensource.org/licenses/MIT for copying permission.

Allows server browsers and management tools to query the server for info.
The protocol used is the warsow version of the quake query protocol.
"""

from re import sub

STATUS_REQUEST = '\xff\xff\xff\xffgetstatus'
STATUS_REPLY = '\xff\xff\xff\xffstatusResponse'
INFO_KEYVALUE = '\\{key}\\{value}'
PLAYER_STRING = '{score} {ping} "{name}" {team}\n'

def makeValid(key):
	k1 = sub(r'[\\\;"]', '', key)
	if len(k1) >= 64:
		return k1[:64]
	return k1

def getTeamId(id):		#warsow: spec = 0, no team = 1, alpha = 2, beta = 3
	if id == 0:
		return 2
	elif id == 1:
		return 3
	return 0

def apply_script(protocol, connection, config):
	class QueryProtocol(protocol):
		def handleQuery(self, challenge):
			options = {'gamename' : 'Ace of Spades', 'fs_game' : 'pysnip'}
			chall = makeValid(challenge)
			if len(chall) > 0:
				options['challenge'] = chall
			options['sv_hostname'] = makeValid(self.name)
			options['version'] = makeValid(self.server_version)
			options['mapname'] = makeValid(self.map_info.name)
			options['gametype'] = makeValid(self.get_mode_name())
			options['sv_maxclients'] = self.max_players
			players = []
			for p in self.players.values():
				players.append({ 'score' : p.kills, 'ping' : p.latency, 'name' : makeValid(p.name), 'team' : getTeamId(p.team.id) })
			options['clients'] = len(players)
			return (options, players);
		def receive_callback(self, address, data):
			if data and data.startswith(STATUS_REQUEST):
				data = data[len(STATUS_REQUEST):].strip()
				options, players = self.handleQuery(data)
				msg = ''
				for k in options:
					msg += INFO_KEYVALUE.format(key = k, value = options[k])
				plr = ''
				for p in players:
					plr += PLAYER_STRING.format(**p)
				binmsg = '\n'.join([STATUS_REPLY, msg.encode('ascii', 'ignore'), plr.encode('ascii', 'ignore')])
				self.host.socket.send(address, binmsg)
			else:
				protocol.receive_callback(self, address, data)

	return QueryProtocol, connection
