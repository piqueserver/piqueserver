"""
Minefield map extension.
Copyright (c) 2013 learn_more
See the file license.txt or http://opensource.org/licenses/MIT for copying permission.

Allows mappers to specify the map bounds, outside of which players will trip mines.
Breaking blocks (when standing close to the field) also triggers a mine.

example extension from mapname.txt:

extensions = {
	'minefields' : [
		#this minefield defines the border:
		{
			'border' : 1,
			'left' : 59,
			'top' : 154,
			'right' : 451,
			'bottom' : 355,
		},
		#this specifies an additional minefield (and shows a simpler syntax)
		{
			'area' : (183, 126, 224, 233),	#top left
			'height' : 60	#this specifies until which block mines are enabled (so you can build over it)
		}
	]
}

Support thread: http://buildandshoot.com/viewtopic.php?f=19&t=8089
Script location: https://github.com/learn-more/pysnip/blob/master/scripts/minefield.py
"""
#todo: reset intel in minefield

MINEFIELD_VERSION = 1.6

from pyspades.world import Grenade
from pyspades.server import grenade_packet, block_action, set_color
from pyspades.common import Vertex3, make_color
from pyspades.collision import collision_3d
from pyspades.constants import DESTROY_BLOCK, SPADE_DESTROY, BUILD_BLOCK
from pyspades.contained import BlockAction, SetColor
from twisted.internet.reactor import callLater
from commands import add, admin
from random import choice

KILL_MESSAGES = [
	'{player} wandered into a minefield',
	'{player} should not walk into a minefield',
	'{player} was not carefull enough in the minefield',
	'{player} thought those mines were toys!',
	#JoJoe's messages
	'{player} showed his team the minefield. What a hero!',
	'{player} should not use their spade to defuse mines.',
	'{player} made a huge mess in the minefield.',
	'{player} detected a mine.',
	'{player} has concluded the mine-sweeping demonstration.',
	'{player} now marks the edge of the minefield.',
	'{player} disarmed a mine by stomping on it.',
	'{player} should build a bridge across the minefield next time.',
	'{player} forgot about the minefield.',
	'Ummmm {player}, Accidentally , the minefield...',
	'{player} made soup in the minefield.',
	'Score Minefield: {mine_kills}, {player} 0, Minefield is Winning!!'
]


MINEFIELD_TIP = 'Be carefull, there are mines in this map!'
MINEFIELD_MOTD = 'Be carefull for minefields!'
MINEFIELD_HELP = 'There are mines in this map!'
MINEFIELD_DBG_MESSAGE = 'Block is at x={x}, y={y}, z={z}, in field:"{m}"'
MINEFIELD_TYPE_STRING = '{type} field({left}, {top}, {right}, {bottom})'
MINEFIELD_MINE_ENT = 'mine'

class Minefield:
	def __init__(self, ext):
		self.isBorder = ext.get('border', False)
		area = ext.get('area', False)
		if area:
			self.left, self.top, self.right, self.bottom = area
		else:
			self.left = ext.get('left', 0)
			self.top = ext.get('top', 0)
			self.right = ext.get('right', 512)
			self.bottom = ext.get('bottom', 512)
		self.height = ext.get('height', 0)

	def __str__(self):
		type = 'Border' if self.isBorder else 'Inner'
		return MINEFIELD_TYPE_STRING.format(type = type, left = self.left, top = self.top, right = self.right, bottom = self.bottom)

	def isValid(self):
		return self.left < self.right and self.top < self.bottom

	def check_hit(self, x, y, z):
		if z >= self.height:
			if self.isBorder:
				return self.left >= x or self.right <= x or self.top >= y or self.bottom <= y
			return x >= self.left and x <= self.right and y >= self.top and y <= self.bottom
		return False

	def singleBlock(self, protocol, x, y, z, color):
		if not protocol.map.get_solid(x, y, z):
			z += 1
		if protocol.map.get_color(x, y, z) == color:
			return
		block_action.x = x
		block_action.y = y
		block_action.z = z
		block_action.player_id = 32
		protocol.map.set_point(x, y, z, color)
		block_action.value = DESTROY_BLOCK
		protocol.send_contained(block_action, save = True)
		block_action.value = BUILD_BLOCK
		protocol.send_contained(block_action, save = True)

	def updateColor(self, protocol, color):
		set_color.value = make_color(*color)
		set_color.player_id = 32
		protocol.send_contained(set_color, save = True)
		return color

	def spawnDecal(self, connection, x, y, z):
		protocol = connection.protocol
		c = self.updateColor(protocol, (0,0,0))
		self.singleBlock(protocol, x, y, z, c)
		c = self.updateColor(protocol, (50,50,50))
		for cc in ((0,1), (1,0), (-1,0), (0,-1)):
			self.singleBlock(protocol, x + cc[0], y + cc[1], z, c)
		c = self.updateColor(protocol, (100,100,100))
		for cc in ((1,1), (1,-1), (-1,1), (-1,-1)):
			self.singleBlock(protocol, x + cc[0], y + cc[1], z, c)

	def spawnNade(self, connection, x, y, z):
		protocol = connection.protocol
		fuse = 0.1
		position = Vertex3(x, y, z)
		orientation = None
		velocity = Vertex3(0, 0, 0)
		grenade = protocol.world.create_object(Grenade, fuse, position, orientation, velocity, connection.grenade_exploded)
		grenade.name = MINEFIELD_MINE_ENT
		grenade_packet.value = grenade.fuse
		grenade_packet.player_id = 32
		grenade_packet.position = position.get()
		grenade_packet.velocity = velocity.get()
		protocol.send_contained(grenade_packet)
		if z >= 61.5:
			callLater(fuse + 0.1, self.spawnDecal, connection, x, y, z)

def parseField(ext):
	m = Minefield(ext)
	if m.isValid():
		return m
	return None

@admin
def minedebug(connection):
	proto = connection.protocol
	proto.minefield_debug = not proto.minefield_debug
	message = 'Minefield is now in debug' if proto.minefield_debug else 'Minefield is no longer in debug'
	proto.send_chat(message, global_message = True)
	return 'You toggled minefield debug'

add(minedebug)

def apply_script(protocol, connection, config):
	class MineConnection(connection):
		def on_position_update(self):
			ret = connection.on_position_update(self)
			if self.protocol.minefield_debug:
				return ret
			pos = self.world_object.position
			x, y, z = int(pos.x), int(pos.y), int(pos.z) + 3
			if self.world_object.crouch:
				z -= 1
			self.protocol.check_mine(self, x, y, z, spawnUp = True)
			return ret

		def on_block_destroy(self, x, y, z, mode):
			if self.protocol.minefield_debug:
				message = MINEFIELD_DBG_MESSAGE.format(x = x, y = y, z = z, m = self.protocol.minefieldAt(x, y, z) or 'None')
				self.send_chat(message)
				return False
			if mode == DESTROY_BLOCK or mode == SPADE_DESTROY:
				pos = self.world_object.position
				#xx, yy, zz = x + 0.5, y + 0.5, z + 0.5
				if collision_3d(x, y, z, pos.x, pos.y, pos.z, 10):
					self.protocol.check_mine(self, x, y, z)
			return connection.on_block_destroy(self, x, y, z, mode)

		def on_kill(self, killer, type, grenade):
			if grenade and grenade.name == MINEFIELD_MINE_ENT:
				self.protocol.mine_kills += 1
				message = choice(KILL_MESSAGES).format(player = self.name, mine_kills = self.protocol.mine_kills)
				self.protocol.send_chat(message, global_message = True)
			connection.on_kill(self, killer, type, grenade)

	class MineProtocol(protocol):
		minefield_enabled = False
		minefields = []
		minefield_version = MINEFIELD_VERSION
		minefield_debug = False

		def on_map_change(self, map):
			self.minefields = []
			self.minefield_enabled = False
			self.mine_kills = 0
			self.minefield_debug = False
			extensions = self.map_info.extensions
			for f in extensions.get('minefields', []):
				m = parseField(f)
				if not m is None:
					self.minefields.append(m)
			self.minefield_enabled = len(self.minefields) > 0
			return protocol.on_map_change(self, map)

		def addif(self, lst, entry):
			if lst is None or entry is None:
				return
			if self.minefield_enabled:
				if not entry in lst:
					lst.append(entry)
			else:
				if entry in lst:
					lst.remove(entry)

		def update_format(self):
			protocol.update_format(self)
			self.addif(self.tips, MINEFIELD_TIP)
			self.addif(self.motd, MINEFIELD_MOTD)
			self.addif(self.help, MINEFIELD_HELP)

		def minefieldAt(self, x, y, z):
			if self.minefield_enabled:
				for m in self.minefields:
					if m.check_hit(x, y, z):
						return m
			return None

		def check_mine(self, connection, x, y, z, waitTime = 0.1, spawnUp = False):
			m = self.minefieldAt(x, y, z)
			if m:
				if spawnUp:
					z -= 1
				callLater(waitTime, m.spawnNade, connection, x + 0.5, y + 0.5, z + 0.5)

	return MineProtocol, MineConnection
