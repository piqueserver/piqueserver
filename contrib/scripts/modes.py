from commands import add, invisible, admin
from math import floor, atan2
from pyspades.constants import *
from pyspades.server import block_action
from pyspades.collision import distance_3d
from twisted.internet.task import LoopingCall

# This is how often the server will send out messages for cloak
# energy/teleportation energy updates
MESSAGE_UPDATE_RATE = 3

CLOAK_MAX_ENERGY = 20.0
CLOAK_REGEN_RATE = 0.5
CLOAK_DRAIN_RATE = 1.0
# Cloak cooldown is in units of seconds
CLOAK_COOLDOWN = 5.0
CLOAK_COOLDOWN_ENABLED = False
# To make sure that people don't cloak to the intel. Units in blocks.
CLOAK_INTEL_DISRUPTION = 64.0
# Sets if swinging the spade disables cloak
CLOAK_DISABLE_SPADE = True

# The max number of blocks someone can teleport
TELEPORTER_MAX_ENERGY = 130
# This rate is how much the teleporter recharges in blocks per second
TELEPORTER_RATE = 3.0
TELEPORTER_INTEL_DISRUPTION = 64.0

HEAL_RATE = 10

SOLDIER_HIT_BUFF = 0.7

SOLDIER_MODE = 0
ASSASSIN_MODE = 1
SNIPER_MODE = 2
MEDIC_MODE = 3

MODE_DESCRIPTION = (
    'Soldier: carries all guns, enemy fire and grenades do less damage',
    'Assassin: invisibility cloak, melee damage only',
    'Sniper: Teleportation gun',
    'Medic: Heal teammates, Instantly build structures')
MODE_WELCOME = (
    'Soldier: Can change weapons without dying. The damage you recieve is reduced by '
        +str(int((1-SOLDIER_HIT_BUFF)*100))+'%.',
    'Assassin: Switch to the grenade to toggle your invisibility cloak.',
    'Sniper: Shoot a surface block three times to teleport on top of it.',
    'Medic: Use the spade to heal teammates. Type /build to see the available structures.')

DEFAULT_MODE = SOLDIER_MODE
QUICKBUILD_WALL = ((0, 0, 0), (-1, 0, 0), (-1, 0, 1), (-2, 0, 0), (-2, 0, 1), 
                   (-3, 0, 0), (-3, 0, 1), (0, 0, 1), (1, 0, 0), (1, 0, 1), 
                   (2, 0, 0), (2, 0, 1), (3, 0, 0), (3, 0, 1))
QUICKBUILD_BUNKER = ((0, 0, 0), (-1, 0, 0), (-1, 0, 1), (-1, 0, 2), 
                     (0, 0, 2), (1, 0, 0), (1, 0, 1), (1, 0, 2), 
                     (2, 0, 0), (2, 0, 2), (-2, 0, 2), (-2, 0, 0), 
                     (3, 0, 0), (3, 0, 1), (3, 0, 2), (-3, 0, 0), 
                     (-3, 0, 1), (-3, 0, 2), (3, 0, 3), (2, 0, 3), 
                     (1, 0, 3), (0, 0, 3), (-1, 0, 3), (-2, 0, 3), 
                     (-3, 0, 3), (-3, -1, 0), (-3, -1, 1), (-3, -1, 2), 
                     (-3, -1, 3), (-3, -2, 3), (-3, -2, 2), (-3, -2, 1), 
                     (-3, -2, 0), (-3, -3, 0), (-3, -3, 1), (-3, -3, 2), 
                     (-3, -3, 3), (-2, -1, 3), (-2, -2, 3), (-2, -3, 3), 
                     (-1, -1, 3), (-1, -2, 3), (-1, -3, 3), (0, -1, 3), 
                     (0, -2, 3), (0, -3, 3), (1, -1, 3), (1, -2, 3), 
                     (1, -3, 3), (2, -1, 3), (2, -2, 3), (2, -3, 3), 
                     (3, -3, 3), (3, -3, 0), (3, -3, 1), (3, -3, 2), 
                     (3, -2, 3), (3, -2, 0), (3, -2, 1), (3, -2, 2), 
                     (3, -1, 0), (3, -1, 1), (3, -1, 2), (3, -1, 3))
QUICKBUILD_SNIPER_TOWER = ((0, 0, 0), (0, 1, 0), (0, 1, 1), (0, 2, 1), 
                           (0, 2, 2), (0, 3, 2), (0, 3, 3), (0, 4, 3), 
                           (0, 4, 4), (0, 5, 4), (0, 5, 5), (1, 5, 5), 
                           (2, 5, 5), (-1, 5, 5), (-2, 5, 5), (-2, 6, 5), 
                           (-2, 7, 5), (-2, 8, 5), (-2, 9, 5), (-1, 6, 5), 
                           (0, 6, 5), (1, 6, 5), (2, 6, 5), (-1, 7, 5), 
                           (0, 7, 5), (1, 7, 5), (2, 7, 5), (-1, 8, 5), 
                           (0, 8, 5), (1, 8, 5), (2, 8, 5), (-1, 9, 5), 
                           (0, 9, 5), (1, 9, 5), (2, 9, 5), (0, 7, 4), 
                           (0, 7, 3), (0, 7, 2), (0, 7, 1), (0, 7, 0), 
                           (2, 9, 4), (2, 9, 3), (2, 9, 2), (2, 9, 1), 
                           (2, 9, 0), (-2, 9, 4), (-2, 9, 3), (-2, 9, 2), 
                           (-2, 9, 1), (-2, 9, 0), (-2, 5, 4), (-2, 5, 3), 
                           (-2, 5, 2), (-2, 5, 1), (-2, 5, 0), (2, 5, 4), 
                           (2, 5, 3), (2, 5, 2), (2, 5, 1), (2, 5, 0), 
                           (-2, 9, 6), (-1, 9, 6), (0, 9, 6), (1, 9, 6), 
                           (2, 9, 6), (2, 8, 6), (2, 7, 6), (2, 6, 6), 
                           (2, 5, 6), (-2, 5, 6), (-2, 6, 6), (-2, 7, 6), 
                           (-2, 8, 6), (-2, 9, 7), (-2, 7, 7), (-2, 5, 7), 
                           (0, 9, 7), (2, 9, 7), (2, 7, 7), (2, 5, 7))
QUICKBUILD_BRIDGE = ((0, 0, 0), (1, 0, 0), (-1, 0, 0), (-1, 1, 0), 
                     (0, 1, 0), (1, 1, 0), (1, 2, 0), (0, 2, 0), 
                     (-1, 2, 0), (-1, 3, 0), (0, 3, 0), (1, 3, 0), 
                     (1, 4, 0), (0, 4, 0), (-1, 4, 0), (-1, 5, 0), 
                     (0, 5, 0), (1, 5, 0), (1, 6, 0), (0, 6, 0), 
                     (-1, 6, 0), (-1, 7, 0), (0, 7, 0), (1, 7, 0), 
                     (1, 8, 0), (0, 8, 0), (-1, 8, 0), (-1, 9, 0), 
                     (0, 9, 0), (1, 9, 0), (1, 10, 0), (0, 10, 0), 
                     (-1, 10, 0), (-1, 11, 0), (0, 11, 0), (1, 11, 0), 
                     (1, 12, 0), (0, 12, 0), (-1, 12, 0), (-1, 13, 0), 
                     (0, 13, 0), (1, 13, 0), (1, 14, 0), (0, 14, 0), 
                     (-1, 14, 0), (-1, 15, 0), (0, 15, 0), (1, 15, 0), 
                     (1, 16, 0), (0, 16, 0), (-1, 16, 0), (-1, 17, 0), 
                     (0, 17, 0), (1, 17, 0), (1, 18, 0), (0, 18, 0), 
                     (-1, 18, 0), (-1, 19, 0), (0, 19, 0), (1, 19, 0), 
                     (1, 20, 0), (0, 20, 0), (-1, 20, 0), (-1, 21, 0), 
                     (0, 21, 0), (1, 21, 0), (1, 22, 0), (0, 22, 0), 
                     (-1, 22, 0), (-1, 23, 0), (0, 23, 0), (1, 23, 0), 
                     (0, 24, 0), (1, 24, 0), (-1, 24, 0), (-1, 25, 0), 
                     (0, 25, 0), (1, 25, 0))
QUICKBUILD_STRUCTURES = (QUICKBUILD_WALL, QUICKBUILD_BUNKER,
                         QUICKBUILD_SNIPER_TOWER, QUICKBUILD_BRIDGE)
QUICKBUILD_DESCRIPTION = ('wall', 'bunker', 'sniper tower', 'bridge')
# Cost is in number of kills
QUICKBUILD_COST = (2, 3, 4, 5)

# Don't touch these values
EAST = 0
SOUTH = 1
WEST = 2
NORTH = 3
UPDATE_RATE = 1.0

CLOAK_REGEN_RATE *= UPDATE_RATE
CLOAK_DRAIN_RATE *= UPDATE_RATE
TELEPORTER_RATE *= UPDATE_RATE
HEAL_RATE *= UPDATE_RATE

# Use these commands to create quickbuild structures.
@admin
def qbtoggle(connection):
    connection.qbcreate = not connection.qbcreate

@admin
def qbprint(connection):
    print connection.recorded_blocks

@admin
def qbclear(connection):
    connection.recorded_blocks = []
    connection.origin_block = None

@admin
def qbundo(connection):
    connection.recorded_blocks.pop()

def mode(connection, mode = None):
    if mode == None:
        for i in xrange(len(MODE_DESCRIPTION)):
            connection.send_chat(str(i) + ': ' + MODE_DESCRIPTION[i])
        connection.send_chat('/mode MODENUMBER')
    else:
        invalid_mode = False
        try:
            mode = int(mode)
            if mode >= len(MODE_DESCRIPTION) or mode < 0:
                invalid_mode = True
            else:
                connection.mode = mode
        except ValueError:
            invalid_mode = True
        if invalid_mode == True:
            connection.send_chat('The mode you selected was invalid.')
            return
        if connection.invisible:
            invisible(connection)
        connection.send_chat(MODE_WELCOME[connection.mode])
        connection.kill()

def build(connection, structure = None):
    if connection.mode != MEDIC_MODE:
        connection.send_chat('You are not in builder mode.')
        return
    if structure == None:
        for i in xrange(len(QUICKBUILD_STRUCTURES)):
            connection.send_chat(str(i) + ': Build a '+
                QUICKBUILD_DESCRIPTION[i] +
                '. Requires '+str(QUICKBUILD_COST[i])+' kills.')
        connection.send_chat('/build BUILDNUMBER')
    else:
        if connection.quickbuild != None:
            connection.send_chat('You already have a structure ready to build.')
            return
        invalid_structure = False
        try:
            structure = int(structure)
            if structure >= len(QUICKBUILD_STRUCTURES) or structure < 0:
                invalid_structure = True
        except ValueError:
            invalid_structure = True
        if invalid_structure:
            connection.send_chat('The structure that you entered is invalid.')
            return
        cost = QUICKBUILD_COST[structure]
        if connection.quickbuild_points >= cost:
            connection.quickbuild_points -= cost
            connection.quickbuild = structure
            connection.send_chat('The next block you place will build a ' +
                                 QUICKBUILD_DESCRIPTION[structure]+'.')
            connection.quickbuild_enabled = True
        else:
            connection.send_chat('You need ' + 
                str(cost-connection.quickbuild_points) +
                ' more kills if you want to build this structure.')

def b(connection, structure = None):
    build(connection, structure)

add(mode)
add(build)
add(b)
add(qbtoggle)
add(qbprint)
add(qbclear)
add(qbundo)

def apply_script(protocol, connection, config):
    class ModesProtocol(protocol):
        def __init__(self, *arg, **kw):
            protocol.__init__(self, *arg, **kw)
            self.message_i = 0
            self.modes_loop = LoopingCall(self.modes_update)
            self.modes_loop.start(UPDATE_RATE)
        
        def modes_update(self):
            self.message_i += UPDATE_RATE
            for player in self.players.values():
                if player.mode == ASSASSIN_MODE:
                    if player.invisible:
                        player.cloak_energy -= CLOAK_DRAIN_RATE
                        if player.cloak_energy <= 0:
                            player.cloak_energy = 0
                            player.disable_cloak()
                        player_location = player.world_object.position
                        intel = player.team.other.flag
                        if intel.player == None or player.has_intel:
                            if player.has_intel or distance_3d(
                                                    (player_location.x,
                                                     player_location.y,
                                                     player_location.z),
                                                    (intel.x,
                                                     intel.y,
                                                     intel.z)
                                                   ) <= CLOAK_INTEL_DISRUPTION:
                                player.send_chat(
                                  'The enemy intel disrupts your cloaking field')
                                player.disable_cloak()
                        if player.world_object.fire:
                            if player.tool == SPADE_TOOL and CLOAK_DISABLE_SPADE == True:
                                player.send_chat(
                                  'The swinging spade disrputs your cloaking field')
                                player.disable_cloak()
                    else:
                        if player.cloak_energy < CLOAK_MAX_ENERGY:
                            player.cloak_energy += CLOAK_REGEN_RATE
                            if player.cloak_energy >= CLOAK_MAX_ENERGY:
                                player.cloak_energy = CLOAK_MAX_ENERGY
                                player.send_chat(
                                  'Cloak is charged to maximum capacity.')
                        if player.cloak_cooldown != None and CLOAK_COOLDOWN_ENABLED:
                            player.cloak_cooldown += 1
                            if player.cloak_cooldown >= CLOAK_COOLDOWN:
                                player.send_chat('Cloak cooldown ended.')
                                player.cloak_cooldown = None
                    if (player.cloak_energy < CLOAK_MAX_ENERGY and
                        self.message_i >= MESSAGE_UPDATE_RATE):
                        player.send_chat(str(player.cloak_energy) +
                            ' seconds of cloak energy are charged.')
                elif player.mode == SNIPER_MODE:
                    if player.teleporter_energy < TELEPORTER_MAX_ENERGY:
                        player.teleporter_energy += TELEPORTER_RATE
                        if player.teleporter_energy >= TELEPORTER_MAX_ENERGY:
                            player.teleporter_energy = TELEPORTER_MAX_ENERGY
                            player.send_chat(
                                'Teleporter is charged to maximum capacity.')
                        if self.message_i >= MESSAGE_UPDATE_RATE:
                            player.send_chat(str(player.teleporter_energy)+
                                ' blocks of teleportation energy are charged.')
                elif player.mode == MEDIC_MODE:
                    player.can_heal = True
                    player.health_message = True
            if self.message_i >= MESSAGE_UPDATE_RATE:
                self.message_i = 0
    
    class ModesConnection(connection):
        def enable_cloak(self):
            if not self.invisible:
                invisible(self)
                self.killing = True
                self.god = False
                self.god_build = False
        
        def disable_cloak(self):
            self.cloak_cooldown = 0
            if self.invisible:
                invisible(self)
                self.killing = True
                self.god = False
                self.god_build = False
        
        def get_direction(self):
            orientation = self.world_object.orientation
            angle = atan2(orientation.y, orientation.x)
            if angle < 0:
                angle += 6.283185307179586476925286766559
            # Convert to units of quadrents
            angle *= 0.63661977236758134307553505349006
            angle = round(angle)
            if angle == 4:
                angle = 0
            return angle
        
        def on_block_build_attempt(self, x, y, z):
            if self.qbcreate:
                if self.origin_block == None:
                    self.origin_block = (x, y, z)
                    self.recorded_blocks.append((0, 0, 0))
                else:
                    self.recorded_blocks.append((x-self.origin_block[0],
                                                 self.origin_block[1]-y,
                                                 self.origin_block[2]-z))
            if self.mode == MEDIC_MODE and self.quickbuild_enabled == True:
                self.quickbuild_enabled = False
                map = self.protocol.map
                block_action.value = BUILD_BLOCK
                block_action.player_id = self.player_id
                color = self.color + (255,)
                facing = self.get_direction()
                structure = QUICKBUILD_STRUCTURES[self.quickbuild]
                self.quickbuild = None
                for block in structure:
                    bx = block[0]
                    by = block[1]
                    bz = block[2]
                    if facing == NORTH:
                        bx, by = bx, -by
                    elif facing == WEST:
                        bx, by = -by, -bx
                    elif facing == SOUTH:
                        bx, by = -bx, by
                    elif facing == EAST:
                        bx, by = by, bx
                    bx, by, bz = x+bx, y+by, z-bz
                    if (bx < 0 or bx >= 512 or by < 0 or by >= 512 or bz < 0 or
                        bz >= 62):
                        continue
                    if map.get_solid(bx, by, bz):
                        continue
                    block_action.x = bx
                    block_action.y = by
                    block_action.z = bz
                    self.protocol.send_contained(block_action, save = True)
                    map.set_point(bx, by, bz, color, user = False)
            return connection.on_block_build_attempt(self, x, y, z)
        
        def on_block_destroy(self, x, y, z, value):
            if (self.mode == SNIPER_MODE and value == DESTROY_BLOCK and
                self.tool == WEAPON_TOOL):
                if self.weapon == SHOTGUN_WEAPON:
                    self.send_chat(
                        'Teleporting with the shotgun is disabled to prevent accidental teleportation.')
                    return
                elif self.weapon == SMG_WEAPON:
                    self.send_chat(
                        "Teleporting with the SMG is disabled. Snipers don't use such noisy guns!")
                map = self.protocol.map
                if (not map.get_solid(x, y, z-1) and not map.get_solid(x, y, z-2) and not
                    map.get_solid(x, y, z-3)):
                    block_location = (x, y, z-3)
                    player_location = self.world_object.position
                    player_location = (player_location.x, player_location.y, player_location.z)
                    intel = self.team.other.flag
                    if intel.player == None or self.has_intel:
                        if (self.has_intel or
                            distance_3d(block_location, (intel.x, intel.y, intel.z)) <= TELEPORTER_INTEL_DISRUPTION):
                            self.send_chat(
                                'The enemy intel is disrupting your teleporter.')
                            return False
                    dist = floor(distance_3d(player_location, block_location))
                    if dist <= self.teleporter_energy:
                        self.teleporter_energy -= dist
                        self.set_location(block_location)
                    else:
                        self.send_chat(
                            "Your teleporter doesn't have enough energy.")
                    return False
                else:
                    self.send_chat('Invalid teleportation target.')
            return connection.on_block_destroy(self, x, y, z, value)
        
        def on_flag_capture(self):
            self.has_intel = False
            return connection.on_flag_capture(self)
        
        def on_flag_drop(self):
            self.has_intel = False
            return connection.on_flag_drop(self)
        
        def on_flag_take(self):
            self.has_intel = True
            return connection.on_flag_take(self)
        
        def on_grenade(self, time_left):
            if self.mode == ASSASSIN_MODE:
                self.send_chat("Assassins' grenades do no damage.")
                return False
            return connection.on_grenade(self, time_left)
        
        def on_hit(self, hit_amount, hit_player):
            if self.mode == ASSASSIN_MODE and self.tool == WEAPON_TOOL:
                self.send_chat("Assassin's bullets do no damage")
                return False
            elif (self.mode == MEDIC_MODE and self.tool == SPADE_TOOL and 
                  self.team == hit_player.team and self.can_heal == True):
                if hit_player.hp >= 100:
                    if self.health_message == True:
                        self.health_message = False
                        self.send_chat(hit_player.name + ' is at full health.')
                elif hit_player.hp > 0:
                    self.can_heal = False
                    hit_player.set_hp(hit_player.hp + HEAL_RATE)
            elif hit_player.mode == SOLDIER_MODE and hit_amount <= 100:
                hit_amount *= SOLDIER_HIT_BUFF
                if hit_player != self:
                    hit_player.hit(hit_amount, self)
                else:
                    hit_player.hit(hit_amount, None)
                return False
            elif hit_player.mode == ASSASSIN_MODE:
                hit_player.disable_cloak()
            return connection.on_hit(self, hit_amount, hit_player)
        
        def on_join(self):
            self.can_heal = False
            self.health_message = False
            self.has_intel = False
            self.quickbuild = None
            self.quickbuild_points = 0
            self.quickbuild_enabled = False
            self.mode = DEFAULT_MODE
            self.teleporter_energy = TELEPORTER_MAX_ENERGY
            self.cloak_energy = CLOAK_MAX_ENERGY
            self.cloak_cooldown = None
            self.qbcreate = False
            self.origin_block = None
            self.recorded_blocks = []
            return connection.on_join(self)
        
        def on_kill(self, killer = None):
            if killer != None:
                if killer.mode == MEDIC_MODE and killer != self:
                    killer.quickbuild_points += 1
            return connection.on_kill(self, killer)
        
        def on_spawn(self, pos):
            if self.mode == ASSASSIN_MODE:
                self.cloak_energy = CLOAK_MAX_ENERGY
                self.cloak_cooldown = None
            elif self.mode == SNIPER_MODE:
                self.teleporter_energy = TELEPORTER_MAX_ENERGY
            elif self.mode == MEDIC_MODE:
                self.quickbuild_enabled = False
                self.can_heal = True
                self.health_message = True
            return connection.on_spawn(self, pos)
        
        def on_tool_set_attempt(self, tool):
            if tool == GRENADE_TOOL and self.mode == ASSASSIN_MODE:
                if self.invisible:
                    self.disable_cloak()
                else:
                    if (self.cloak_cooldown == None or
                        CLOAK_COOLDOWN_ENABLED == False):
                        self.enable_cloak()
                    else:
                        self.send_chat(
                            'Your cloak is in cooldown mode right now.')
            return connection.on_tool_set_attempt(self, tool)
        
        def on_weapon_set(self, weapon):
            if self.mode == SOLDIER_MODE:
                self.weapon = weapon
                self.set_weapon(weapon)
                return False
            return connection.on_weapon_set(self, weapon)
    
    return ModesProtocol, ModesConnection