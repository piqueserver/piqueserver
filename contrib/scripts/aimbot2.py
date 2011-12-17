from twisted.internet.task import LoopingCall
from pyspades.constants import *
from pyspades.weapon import Shotgun
from math import sqrt, cos, acos, pi, tan
from commands import add, admin
from twisted.internet import reactor

KICK_SNAP_HEADSHOT = True
# Hit near miss ratio
KICK_HNM_RATIO = False
KICK_DAMAGE_HACK = True
KICK_KILLS_IN_TIME = True

# A near miss occurs when the player is NEAR_MISS_ANGLE degrees or less off
# of an enemy
NEAR_MISS_ANGLE = 10.0

# Approximate size of player's heads in blocks
HEAD_RADIUS = 0.7

# When the user's orientation angle (degrees) changes more than this amount,
# check if the user snapped to an enemy's head. If it is aligned with a head,
# record this as a headshot snap
SNAP_HEADSHOT_ANGLE = 90.0

# If the number of headshot snaps exceeds the SNAP_HEADSHOT_THRESHOLD in the
# given SNAP_HEADSHOT_TIME, kick the player. This check is performed every
# time somebody performs a headshot snap
SNAP_HEADSHOT_TIME = 20.0
SNAP_HEADSHOT_THRESHOLD = 4

# 128 is the approximate fog distance, but bump it up a little
# just in case
FOG_DISTANCE = 135.0

# The minimum number of near misses + hits that are fired before
# we can kick someone using the hit/near miss ratio check
SEMI_KICK_MINIMUM = 15
SMG_KICK_MINIMUM = 40
SHOTGUN_KICK_MINIMUM = 15

# Kick a player if the above minimum is met and if the
# hit to near miss ratio is greater than or equal to this amount
SEMI_KICK_RATIO = 1.2
SMG_KICK_RATIO = 0.8
SHOTGUN_KICK_RATIO = 0.8

# Valid damage values for each gun
SEMI_DAMAGE = (33,49,100)
SMG_DAMAGE = (16,24,75)
SHOTGUN_DAMAGE = (14,21,24,42,63,72)

# If a player gets more kills than the KILL_THRESHOLD in the given
# KILL_TIME, kick the player. This check is performed every
# time somebody kills someone with a gun
KILL_TIME = 20.0
KILL_THRESHOLD = 10

# Don't touch any of this stuff
HALF_SHOTGUN = 0.5*Shotgun.delay
FOG_DISTANCE2 = FOG_DISTANCE**2
NEAR_MISS_COS = cos(NEAR_MISS_ANGLE * (pi/180.0))
SNAP_HEADSHOT_ANGLE_COS = cos(SNAP_HEADSHOT_ANGLE * (pi/180.0))

def point_distance2(c1, c2):
    p1 = c1.world_object.position
    p2 = c2.world_object.position
    return (p1.x - p2.x)**2 + (p1.y - p2.y)**2 + (p1.z - p2.z)**2

def dot3d(v1, v2):
    return v1[0] * v2[0] + v1[1] * v2[1] + v1[2] * v2[2]

def magnitude(v):
    return sqrt(v[0]**2 + v[1]**2 + v[2]**2)

def scale(v, scale):
    return (v[0]*scale, v[1]*scale, v[2]*scale)

def subtract(v1, v2):
    return (v1[0]-v2[0], v1[1]-v2[1], v1[2]-v2[2])

def apply_script(protocol, connection, config):    
    class Aimbot2Connection(connection):
        def __init__(self, *arg, **kw):
            connection.__init__(self, *arg, **kw)
            self.semi_hits = self.smg_hits = self.shotgun_hits = 0
            self.semi_near_misses = self.smg_near_misses = self.shotgun_near_misses = 0
            self.last_target = None
            self.first_orientation = True
            self.kill_times = []
            self.headshot_snap_times = []
            self.bullet_loop = LoopingCall(self.on_bullet_fire)
            self.bullet_loop_running = False
            self.shotgun_time = 0.0
        
        def on_spawn(self, pos):
            self.first_orientation = True
            return connection.on_spawn(self, pos)

        def bullet_loop_start(self, interval):
            if self.bullet_loop_running == False:
                self.bullet_loop_running = True
                self.bullet_loop.start(interval)
        
        def bullet_loop_stop(self):
            if self.bullet_loop_running == True:
                self.bullet_loop_running = False
                self.bullet_loop.stop()

        def on_orientation_update(self, x, y, z):
            if KICK_SNAP_HEADSHOT == True:
                if self.first_orientation == False:
                    orient = self.world_object.orientation
                    old_orient_v = (orient.x, orient.y, orient.z)
                    new_orient_v = (x, y, z)
                    theta = dot3d(old_orient_v, new_orient_v)
                    if theta <= SNAP_HEADSHOT_ANGLE_COS:
                        self_pos = self.world_object.position
                        current_time = reactor.seconds()
                        for enemy in self.team.other.get_players():
                            enemy_pos = enemy.world_object.position
                            position_v = (enemy_pos.x - self_pos.x, enemy_pos.y - self_pos.y, enemy_pos.z - self_pos.z)
                            c = scale(new_orient_v, dot3d(new_orient_v, position_v))
                            h = magnitude(subtract(position_v, c))
                            if h <= HEAD_RADIUS:
                                headshot_snap_count = 1
                                pop_count = 0
                                for old_time in self.headshot_snap_times:
                                    if current_time - old_time <= SNAP_HEADSHOT_TIME:
                                        headshot_snap_count += 1
                                    else:
                                        pop_count += 1
                                if headshot_snap_count >= SNAP_HEADSHOT_THRESHOLD:
                                    self.kick('Aimbot detected - T1')
                                    return
                                for i in xrange(0, pop_count):
                                    self.headshot_snap_times.pop(0)
                                self.headshot_snap_times.append(current_time)
                else:
                    self.first_orientation = False
            return connection.on_orientation_update(self, x, y, z)
        
        def on_shoot_set(self, shoot):
            if self.tool == WEAPON_TOOL:
                if shoot == True and self.bullet_loop_running == False:
                    self.possible_targets = []
                    for enemy in self.team.other.get_players():
                        if point_distance2(self, enemy) <= FOG_DISTANCE2:
                            self.possible_targets.append(enemy)
                    self.bullet_loop_start(self.weapon_object.delay)
                elif shoot == False:
                    self.bullet_loop_stop()
            return connection.on_shoot_set(self, shoot)
        
        def kill(self, by = None, type = WEAPON_KILL):
            if (type == WEAPON_KILL or type == HEADSHOT_KILL) and KICK_KILLS_IN_TIME == True:
                current_time = reactor.seconds()
                kill_count = 1
                pop_count = 0
                for old_time in by.kill_times:
                    if current_time - old_time <= KILL_TIME:
                        kill_count += 1
                    else:
                        pop_count += 1
                if kill_count >= KILL_THRESHOLD:
                    by.kick('Aimbot detected - T2')
                    return
                for i in xrange(0, pop_count):
                    by.kill_times.pop(0)
                by.kill_times.append(current_time)
            return connection.kill(self, by, type)

        def hit(self, value, by = None, type = WEAPON_KILL):
            if (type == WEAPON_KILL or type == HEADSHOT_KILL) and by != None:
                # Any hit will be counted as a near miss
                if by.weapon == SEMI_WEAPON:
                    if (value in SEMI_DAMAGE) == False and KICK_DAMAGE_HACK == True:
                        by.kick('Damage hack detected')
                        return
                    else:
                        by.semi_hits += 1
                        by.semi_near_misses = max(0, by.semi_near_misses - 1)
                elif by.weapon == SMG_WEAPON:
                    if (value in SMG_DAMAGE) == False and KICK_DAMAGE_HACK == True:
                        by.kick('Damage hack detected')
                        return
                    else:
                        by.smg_hits += 1
                        by.semi_near_misses = max(0, by.semi_near_misses - 1)
                elif by.weapon == SHOTGUN_WEAPON:
                    if (value in SHOTGUN_DAMAGE) == False and KICK_DAMAGE_HACK == True:
                        by.kick('Damage hack detected')
                        return
                    else:
                        current_time = reactor.seconds()
                        if current_time - by.shotgun_time >= HALF_SHOTGUN:
                            by.shotgun_hits += 1
                            by.shotgun_near_misses = max(0, by.shotgun_near_misses - 1)
                            by.shotgun_time = current_time
            return connection.hit(self, value, by, type)
        
        def check_ratio(self):
            if KICK_HNM_RATIO == True:
                if self.weapon == SEMI_WEAPON:
                    if (self.semi_hits + self.semi_near_misses) >= SEMI_KICK_MINIMUM:
                        if self.semi_near_misses == 0:
                            self.kick('Aimbot detected - T3')
                            return
                        elif float(self.semi_hits)/float(self.semi_near_misses) >= SEMI_KICK_RATIO:
                            self.kick('Aimbot detected - T3')
                            return
                elif self.weapon == SMG_WEAPON:
                    if (self.smg_hits + self.smg_near_misses) >= SMG_KICK_MINIMUM:
                        if self.smg_near_misses == 0:
                            self.kick('Aimbot detected - T3')
                            return
                        elif float(self.smg_hits)/float(self.smg_near_misses) >= SMG_KICK_RATIO:
                            self.kick('Aimbot detected - T3')
                            return
                elif self.weapon == SHOTGUN_WEAPON:
                    if (self.shotgun_hits + self.shotgun_near_misses) >= SHOTGUN_KICK_MINIMUM:
                        if self.shotgun_near_misses == 0:
                            self.kick('Aimbot detected - T3')
                            return
                        elif float(self.shotgun_hits)/float(self.shotgun_near_misses) >= SHOTGUN_KICK_RATIO:
                            self.kick('Aimbot detected - T3')
                            return

        def on_bullet_fire(self):
            # Remembering the past offers a performance boost, particularly with the SMG
            if self.last_target != None:
                if self.last_target.hp != None:
                    if self.check_near_miss(self.last_target) == True:
                        self.check_ratio()
                        return
            for enemy in self.possible_targets:
                if enemy.hp != None and enemy != self.last_target:
                    if self.check_near_miss(enemy) == True:
                        self.last_target = enemy
                        self.check_ratio()
                        return

        def check_near_miss(self, target):
            p_self = self.world_object.position
            p_targ = target.world_object.position
            position_v = (p_targ.x - p_self.x, p_targ.y - p_self.y, p_targ.z - p_self.z)
            orient = self.world_object.orientation
            orient_v = (orient.x, orient.y, orient.z)
            if (dot3d(orient_v, position_v)/magnitude(position_v)) >= NEAR_MISS_COS:
                if self.weapon == SEMI_WEAPON:
                    self.semi_near_misses += 1
                elif self.weapon == SMG_WEAPON:
                    self.smg_near_misses += 1
                elif self.weapon == SHOTGUN_WEAPON:
                    self.shotgun_near_misses += 1
                return True
            return False
        
        # Data collection stuff
        def on_disconnect(self):
            self.bullet_loop_stop()
            if self.name != None:
                with open('aimbot2log.txt','a') as myfile:
                    output = self.name.replace(',','') + ','
                    output += str(self.semi_hits) + ',' + str(self.semi_near_misses) + ','
                    output += str(self.smg_hits) + ',' + str(self.smg_near_misses) + ','
                    output += str(self.shotgun_hits) + ',' + str(self.shotgun_near_misses) + '\n'
                    myfile.write(output)
                    myfile.close()
            return connection.on_disconnect(self)
    
    return protocol, Aimbot2Connection