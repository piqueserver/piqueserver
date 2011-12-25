from twisted.internet.task import LoopingCall
from pyspades.constants import *
from pyspades.weapon import Shotgun
from math import sqrt, cos, acos, pi, tan
from commands import add, admin
from twisted.internet import reactor

# This is an option for data collection. Data is outputted to aimbot2log.txt
DATA_COLLECTION = False

# This controls which detection methods are enabled. If a player is detected
# using one of these methods, the player is kicked.
DETECT_SNAP_HEADSHOT = True
DETECT_HIT_PERCENT = True
DETECT_DAMAGE_HACK = True
DETECT_KILLS_IN_TIME = True

# If both the below and above controls are set to True, a player will be
# banned instead of kicked
SNAP_HEADSHOT_BAN = False
HIT_PERCENT_BAN = False
DAMAGE_HACK_BAN = True
KILLS_IN_TIME_BAN = True

# These controls are only used if banning instead of kicking is enabled
# Time is given in minutes. Set to 0 for a permaban
SNAP_HEADSHOT_BAN_DURATION = 60
HIT_PERCENT_BAN_DURATION = 120
DAMAGE_HACK_BAN_DURATION = 2880
KILLS_IN_TIME_BAN_DURATION = 2880

# The minimum number of near misses + hits that are fired before
# we can kick or ban someone using the hit percentage check
SEMI_KICK_MINIMUM = 15
SMG_KICK_MINIMUM = 40
SHOTGUN_KICK_MINIMUM = 15

# Kick a player if the above minimum is met and if the
# bullet hit percentage is greater than or equal to this amount
SEMI_KICK_PERC = 0.85
SMG_KICK_PERC = 0.70
SHOTGUN_KICK_PERC = 0.85

# If a player gets more kills than the KILL_THRESHOLD in the given
# KILL_TIME, kick or ban the player. This check is performed every
# time somebody kills someone with a gun
KILL_TIME = 20.0
KILL_THRESHOLD = 10

# If the number of headshot snaps exceeds the SNAP_HEADSHOT_THRESHOLD in the
# given SNAP_HEADSHOT_TIME, kick or ban the player. This check is performed every
# time somebody performs a headshot snap
SNAP_HEADSHOT_TIME = 20.0
SNAP_HEADSHOT_THRESHOLD = 6

# When the user's orientation angle (degrees) changes more than this amount,
# check if the user snapped to an enemy's head. If it is aligned with a head,
# record this as a headshot snap
SNAP_HEADSHOT_ANGLE = 90.0

# A near miss occurs when the player is NEAR_MISS_ANGLE degrees or less off
# of an enemy
NEAR_MISS_ANGLE = 10.0

# Valid damage values for each gun
SEMI_DAMAGE = (33,49,100)
SMG_DAMAGE = (16,24,75)
SHOTGUN_DAMAGE = (14,21,24,42,63,72)

# Approximate size of player's heads in blocks
HEAD_RADIUS = 0.7

# 128 is the approximate fog distance, but bump it up a little
# just in case
FOG_DISTANCE = 135.0

# Don't touch any of this stuff
HALF_SHOTGUN = 0.5*Shotgun.delay
FOG_DISTANCE2 = FOG_DISTANCE**2
NEAR_MISS_COS = cos(NEAR_MISS_ANGLE * (pi/180.0))
SNAP_HEADSHOT_ANGLE_COS = cos(SNAP_HEADSHOT_ANGLE * (pi/180.0))

def point_distance2(c1, c2):
    if c1.world_object is not None and c2.world_object is not None:
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
            self.semi_count = self.smg_count = self.shotgun_count = 0
            self.last_target = None
            self.first_orientation = True
            self.kill_times = []
            self.headshot_snap_times = []
            self.bullet_loop = LoopingCall(self.on_bullet_fire)
            self.shotgun_time = 0.0
        
        def on_spawn(self, pos):
            self.first_orientation = True
            return connection.on_spawn(self, pos)

        def bullet_loop_start(self, interval):
            if not self.bullet_loop.running:
                self.bullet_loop.start(interval)
        
        def bullet_loop_stop(self):
            if self.bullet_loop.running:
                self.bullet_loop.stop()
        
        def on_orientation_update(self, x, y, z):
            if DETECT_SNAP_HEADSHOT:
                if not self.first_orientation and self.world_object is not None:
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
                                    if SNAP_HEADSHOT_BAN:
                                        self.ban('Aimbot detected - T1', SNAP_HEADSHOT_BAN_DURATION)
                                    else:
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
                if shoot and not self.bullet_loop.running:
                    self.possible_targets = []
                    for enemy in self.team.other.get_players():
                        if point_distance2(self, enemy) <= FOG_DISTANCE2:
                            self.possible_targets.append(enemy)
                    self.bullet_loop_start(self.weapon_object.delay)
                elif not shoot:
                    self.bullet_loop_stop()
            return connection.on_shoot_set(self, shoot)
        
        def kill(self, by = None, type = WEAPON_KILL):
            if by is not None and by is not self and DETECT_KILLS_IN_TIME:
                if type == WEAPON_KILL or type == HEADSHOT_KILL:
                    current_time = reactor.seconds()
                    kill_count = 1
                    pop_count = 0
                    for old_time in by.kill_times:
                        if current_time - old_time <= KILL_TIME:
                            kill_count += 1
                        else:
                            pop_count += 1
                    if kill_count >= KILL_THRESHOLD:
                        if KILLS_IN_TIME_BAN:
                            by.ban('Aimbot detected - T2', KILLS_IN_TIME_BAN_DURATION)
                        else:
                            by.kick('Aimbot detected - T2')
                        return
                    for i in xrange(0, pop_count):
                        by.kill_times.pop(0)
                    by.kill_times.append(current_time)
            return connection.kill(self, by, type)
        
        def damage_hack_eject(self):
            if DAMAGE_HACK_BAN:
                self.ban('Damage hack detected', DAMAGE_HACK_BAN_DURATION)
            else:
                self.kick('Damage hack detected')

        def hit(self, value, by = None, type = WEAPON_KILL):
            if by is not None and by is not self:
                if type == WEAPON_KILL or type == HEADSHOT_KILL:
                    if by.weapon == SEMI_WEAPON:
                        if (not (value in SEMI_DAMAGE)) and DETECT_DAMAGE_HACK:
                            by.damage_hack_eject()
                            return
                        else:
                            by.semi_hits += 1
                    elif by.weapon == SMG_WEAPON:
                        if (not (value in SMG_DAMAGE)) and DETECT_DAMAGE_HACK:
                            by.damage_hack_eject()
                            return
                        else:
                            by.smg_hits += 1
                    elif by.weapon == SHOTGUN_WEAPON:
                        if (not (value in SHOTGUN_DAMAGE)) and DETECT_DAMAGE_HACK:
                            by.damage_hack_eject()
                            return
                        else:
                            current_time = reactor.seconds()
                            if current_time - by.shotgun_time >= HALF_SHOTGUN:
                                by.shotgun_hits += 1
                                by.shotgun_time = current_time
            return connection.hit(self, value, by, type)
        
        def hit_percent_eject(self):
            if HIT_PERCENT_BAN:
                self.ban('Aimbot detected - T3', HIT_PERCENT_BAN_DURATION)
            else:
                self.kick('Aimbot detected - T3')

        def check_percent(self):
            if DETECT_HIT_PERCENT:
                if self.weapon == SEMI_WEAPON:
                    if self.semi_count >= SEMI_KICK_MINIMUM:
                        if float(self.semi_hits)/float(self.semi_count) >= SEMI_KICK_PERC:
                            self.hit_percent_eject()
                            return
                elif self.weapon == SMG_WEAPON:
                    if self.smg_count >= SMG_KICK_MINIMUM:
                        if float(self.smg_hits)/float(self.smg_count) >= SMG_KICK_PERC:
                            self.hit_percent_eject()
                            return
                elif self.weapon == SHOTGUN_WEAPON:
                    if self.shotgun_count >= SHOTGUN_KICK_MINIMUM:
                        if float(self.shotgun_hits)/float(self.shotgun_count) >= SHOTGUN_KICK_PERC:
                            self.hit_percent_eject()
                            return

        def on_bullet_fire(self):
            # Remembering the past offers a performance boost, particularly with the SMG
            if self.last_target is not None:
                if self.last_target.hp is not None:
                    if self.check_near_miss(self.last_target):
                        self.check_percent()
                        return
            for enemy in self.possible_targets:
                if enemy.hp is not None and enemy is not self.last_target:
                    if self.check_near_miss(enemy):
                        self.last_target = enemy
                        self.check_percent()
                        return

        def check_near_miss(self, target):
            if self.world_object is not None and target.world_object is not None:
                p_self = self.world_object.position
                p_targ = target.world_object.position
                position_v = (p_targ.x - p_self.x, p_targ.y - p_self.y, p_targ.z - p_self.z)
                orient = self.world_object.orientation
                orient_v = (orient.x, orient.y, orient.z)
                if (dot3d(orient_v, position_v)/magnitude(position_v)) >= NEAR_MISS_COS:
                    if self.weapon == SEMI_WEAPON:
                        self.semi_count += 1
                    elif self.weapon == SMG_WEAPON:
                        self.smg_count += 1
                    elif self.weapon == SHOTGUN_WEAPON:
                        self.shotgun_count += 1
                    return True
            return False
        
        # Data collection stuff
        def on_disconnect(self):
            self.bullet_loop_stop()
            if DATA_COLLECTION:
                if self.name != None:
                    with open('aimbot2log.txt','a') as myfile:
                        output = self.name.encode('ascii','ignore').replace(',','') + ','
                        output += str(self.semi_hits) + ',' + str(self.semi_count) + ','
                        output += str(self.smg_hits) + ',' + str(self.smg_count) + ','
                        output += str(self.shotgun_hits) + ',' + str(self.shotgun_count) + '\n'
                        myfile.write(output)
                        myfile.close()
            return connection.on_disconnect(self)
    
    return protocol, Aimbot2Connection