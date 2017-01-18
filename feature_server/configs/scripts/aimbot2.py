from twisted.internet.task import LoopingCall
from pyspades.constants import *
from math import sqrt, cos, acos, pi, tan
from commands import add, admin, get_player
from twisted.internet import reactor
import re

DISABLED, KICK, BAN, WARN_ADMIN = xrange(4)

# This is an option for data collection. Data is outputted to aimbot2log.txt
DATA_COLLECTION = False

# This controls which detection methods are enabled. If a player is detected
# using one of these methods, the player is kicked.
HEADSHOT_SNAP = WARN_ADMIN
HIT_PERCENT = WARN_ADMIN
KILLS_IN_TIME = WARN_ADMIN
MULTIPLE_BULLETS = WARN_ADMIN

DETECT_DAMAGE_HACK = True

# Minimum amount of time that must pass between admin warnings that are
# triggered by the same detection method. Time is in seconds.
WARN_INTERVAL_MINIMUM = 300

# These controls are only used if banning is enabled
# Time is given in minutes. Set to 0 for a permaban
HEADSHOT_SNAP_BAN_DURATION = 1400
HIT_PERCENT_BAN_DURATION = 1440
KILLS_IN_TIME_BAN_DURATION = 2880
MULTIPLE_BULLETS_BAN_DURATION = 10080

# If more than or equal to this number of weapon hit packets are recieved
# from the client in half the weapon delay time, then an aimbot is detected.
# This method of detection should have 100% detection and no false positives
# with the current aimbot.
# Note that the current aimbot does not modify the number of bullets
# of the shotgun, so this method will not work if the player uses a shotgun.
# These values may need to be changed if an update to the aimbot is released.
RIFLE_MULTIPLE_BULLETS_MAX = 8
SMG_MULTIPLE_BULLETS_MAX = 8

# The minimum number of near misses + hits that are fired before kicking,
# banning, or warning an admin about someone using the hit percentage check
RIFLE_KICK_MINIMUM = 45
SMG_KICK_MINIMUM = 90
SHOTGUN_KICK_MINIMUM = 45

# Kick, ban, or warn when the above minimum is met and the
# bullet hit percentage is greater than or equal to this amount
RIFLE_KICK_PERC = 0.90
SMG_KICK_PERC = 0.80
SHOTGUN_KICK_PERC = 0.90

# If a player gets more kills than the KILL_THRESHOLD in the given
# KILL_TIME, kick, ban, or warn. This check is performed every
# time somebody kills someone with a gun
KILL_TIME = 20.0
KILL_THRESHOLD = 15

# If the number of headshot snaps exceeds the HEADSHOT_SNAP_THRESHOLD in the
# given HEADSHOT_SNAP_TIME, kick, ban, or warn. This check is performed every
# time somebody performs a headshot snap
HEADSHOT_SNAP_TIME = 20.0
HEADSHOT_SNAP_THRESHOLD = 6

# When the user's orientation angle (degrees) changes more than this amount,
# check if the user snapped to an enemy's head. If it is aligned with a head,
# record this as a headshot snap
HEADSHOT_SNAP_ANGLE = 90.0

# A near miss occurs when the player is NEAR_MISS_ANGLE degrees or less off
# of an enemy
NEAR_MISS_ANGLE = 10.0

# Valid damage values for each gun
RIFLE_DAMAGE = (33, 49, 100)
SMG_DAMAGE = (18, 29, 75)
SHOTGUN_DAMAGE = (16, 27, 37)

# Approximate size of player's heads in blocks
HEAD_RADIUS = 0.7

# 128 is the approximate fog distance, but bump it up a little
# just in case
FOG_DISTANCE = 135.0

# Don't touch any of this stuff
FOG_DISTANCE2 = FOG_DISTANCE**2
NEAR_MISS_COS = cos(NEAR_MISS_ANGLE * (pi/180.0))
HEADSHOT_SNAP_ANGLE_COS = cos(HEADSHOT_SNAP_ANGLE * (pi/180.0))

aimbot_pattern = re.compile(".*(aim|bot|ha(ck|x)|cheat).*", re.IGNORECASE)

def aimbot_match(msg):
    return (not aimbot_pattern.match(msg) is None)

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

def accuracy(connection, name = None):
    if name is None:
        player = connection
    else:
        player = get_player(connection.protocol, name)
    return accuracy_player(player)

def accuracy_player(player, name_info = True):
    if player.rifle_count != 0:
        rifle_percent = str(int(100.0 * (float(player.rifle_hits)/float(player.rifle_count)))) + '%'
    else:
        rifle_percent = 'None'
    if player.smg_count != 0:
        smg_percent = str(int(100.0 * (float(player.smg_hits)/float(player.smg_count)))) + '%'
    else:
        smg_percent = 'None'
    if player.shotgun_count != 0:
        shotgun_percent = str(int(100.0 * (float(player.shotgun_hits)/float(player.shotgun_count)))) + '%'
    else:
        shotgun_percent = 'None'
    s = ''
    if name_info:
        s += player.name + ' has an accuracy of: '
    s += 'Rifle: %s SMG: %s Shotgun: %s.' % (rifle_percent, smg_percent, shotgun_percent)
    return s

add(accuracy)

@admin
def hackinfo(connection, name):
    player = get_player(connection.protocol, name)
    return hackinfo_player(player)

def hackinfo_player(player):
    info = "%s #%s (%s) has an accuracy of: " % (player.name, player.player_id, player.address[0])
    info += accuracy_player(player, False)
    ratio = player.ratio_kills/float(max(1,player.ratio_deaths))
    info += " Kill-death ratio of %.2f (%s kills, %s deaths)." % (ratio, player.ratio_kills, player.ratio_deaths)
    info += " %i kills in the last %i seconds." % (player.get_kill_count(), KILL_TIME)
    info += " %i headshot snaps in the last %i seconds." % (player.get_headshot_snap_count(), HEADSHOT_SNAP_TIME)
    return info

add(hackinfo)

def apply_script(protocol, connection, config):
    class Aimbot2Protocol(protocol):
        def start_votekick(self, payload):
            if aimbot_match(payload.reason):
                payload.target.warn_admin('Hack related votekick.')
            return protocol.start_votekick(self, payload)

    class Aimbot2Connection(connection):
        def __init__(self, *arg, **kw):
            connection.__init__(self, *arg, **kw)
            self.rifle_hits = self.smg_hits = self.shotgun_hits = 0
            self.rifle_count = self.smg_count = self.shotgun_count = 0
            self.last_target = None
            self.first_orientation = True
            self.kill_times = []
            self.headshot_snap_times = []
            self.bullet_loop = LoopingCall(self.on_bullet_fire)
            self.shot_time = 0.0
            self.multiple_bullets_count = 0
            self.headshot_snap_warn_time = self.hit_percent_warn_time = 0.0
            self.kills_in_time_warn_time = self.multiple_bullets_warn_time = 0.0

        def warn_admin(self, prefix = 'Possible aimbot detected.'):
            prefix += ' '
            message = hackinfo_player(self)
            for player in self.protocol.players.values():
                if player.admin:
                    player.send_chat(prefix + message)
            irc_relay = self.protocol.irc_relay
            if irc_relay:
                if irc_relay.factory.bot and irc_relay.factory.bot.colors:
                    prefix = '\x0304' + prefix + '\x0f'
                irc_relay.send(prefix + message)

        def on_spawn(self, pos):
            self.first_orientation = True
            return connection.on_spawn(self, pos)

        def bullet_loop_start(self, interval):
            if not self.bullet_loop.running:
                self.bullet_loop.start(interval)

        def bullet_loop_stop(self):
            if self.bullet_loop.running:
                self.bullet_loop.stop()

        def get_headshot_snap_count(self):
            pop_count = 0
            headshot_snap_count = 0
            current_time = reactor.seconds()
            for old_time in self.headshot_snap_times:
                if current_time - old_time <= HEADSHOT_SNAP_TIME:
                    headshot_snap_count += 1
                else:
                    pop_count += 1
            for i in xrange(0, pop_count):
                self.headshot_snap_times.pop(0)
            return headshot_snap_count

        def on_orientation_update(self, x, y, z):
            if not self.first_orientation and self.world_object is not None:
                orient = self.world_object.orientation
                old_orient_v = (orient.x, orient.y, orient.z)
                new_orient_v = (x, y, z)
                theta = dot3d(old_orient_v, new_orient_v)
                if theta <= HEADSHOT_SNAP_ANGLE_COS:
                    self_pos = self.world_object.position
                    for enemy in self.team.other.get_players():
                        enemy_pos = enemy.world_object.position
                        position_v = (enemy_pos.x - self_pos.x, enemy_pos.y - self_pos.y, enemy_pos.z - self_pos.z)
                        c = scale(new_orient_v, dot3d(new_orient_v, position_v))
                        h = magnitude(subtract(position_v, c))
                        if h <= HEAD_RADIUS:
                            current_time = reactor.seconds()
                            self.headshot_snap_times.append(current_time)
                            if self.get_headshot_snap_count() >= HEADSHOT_SNAP_THRESHOLD:
                                if HEADSHOT_SNAP == BAN:
                                    self.ban('Aimbot detected - headshot snap', HEADSHOT_SNAP_BAN_DURATION)
                                    return
                                elif HEADSHOT_SNAP == KICK:
                                    self.kick('Aimbot detected - headshot snap')
                                    return
                                elif HEADSHOT_SNAP == WARN_ADMIN:
                                    if (current_time - self.headshot_snap_warn_time) > WARN_INTERVAL_MINIMUM:
                                        self.headshot_snap_warn_time = current_time
                                        self.warn_admin()
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

        def get_kill_count(self):
            current_time = reactor.seconds()
            kill_count = 0
            pop_count = 0
            for old_time in self.kill_times:
                if current_time - old_time <= KILL_TIME:
                    kill_count += 1
                else:
                    pop_count += 1
            for i in xrange(0, pop_count):
                self.kill_times.pop(0)
            return kill_count

        def on_kill(self, by, type, grenade):
            if by is not None and by is not self:
                if type == WEAPON_KILL or type == HEADSHOT_KILL:
                    by.kill_times.append(reactor.seconds())
                    if by.get_kill_count() >= KILL_THRESHOLD:
                        if KILLS_IN_TIME == BAN:
                            by.ban('Aimbot detected - kills in time window', KILLS_IN_TIME_BAN_DURATION)
                            return
                        elif KILLS_IN_TIME == KICK:
                            by.kick('Aimbot detected - kills in time window')
                            return
                        elif KILLS_IN_TIME == WARN_ADMIN:
                            current_time = reactor.seconds()
                            if (current_time - by.kills_in_time_warn_time) > WARN_INTERVAL_MINIMUM:
                                by.kills_in_time_warn_time = current_time
                                by.warn_admin()
            return connection.on_kill(self, by, type, grenade)

        def multiple_bullets_eject(self):
            if MULTIPLE_BULLETS == BAN:
                self.ban('Aimbot detected - multiple bullets', MULTIPLE_BULLETS_BAN_DURATION)
            elif MULTIPLE_BULLETS == KICK:
                self.kick('Aimbot detected - multiple bullets')
            elif MULTIPLE_BULLETS == WARN_ADMIN:
                current_time = reactor.seconds()
                if (current_time - self.multiple_bullets_warn_time) > WARN_INTERVAL_MINIMUM:
                    self.multiple_bullets_warn_time = current_time
                    self.warn_admin()

        def on_hit(self, hit_amount, hit_player, type, grenade):
            if self.team is not hit_player.team:
                if type == WEAPON_KILL or type == HEADSHOT_KILL:
                    current_time = reactor.seconds()
                    shotgun_use = False
                    if current_time - self.shot_time > (0.5 * hit_player.weapon_object.delay):
                        shotgun_use = True
                        self.multiple_bullets_count = 0
                        self.shot_time = current_time
                    if type == HEADSHOT_KILL:
                        self.multiple_bullets_count += 1
                    if self.weapon == RIFLE_WEAPON:
                        if (not (hit_amount in RIFLE_DAMAGE)) and DETECT_DAMAGE_HACK:
                            return False
                        else:
                            self.rifle_hits += 1
                            if self.multiple_bullets_count >= RIFLE_MULTIPLE_BULLETS_MAX:
                                self.multiple_bullets_eject()
                                return False
                    elif self.weapon == SMG_WEAPON:
                        if (not (hit_amount in SMG_DAMAGE)) and DETECT_DAMAGE_HACK:
                            return False
                        else:
                            self.smg_hits += 1
                            if self.multiple_bullets_count >= SMG_MULTIPLE_BULLETS_MAX:
                                self.multiple_bullets_eject()
                                return False
                    elif self.weapon == SHOTGUN_WEAPON:
                        if (not (hit_amount in SHOTGUN_DAMAGE)) and DETECT_DAMAGE_HACK:
                            return False
                        elif shotgun_use:
                            self.shotgun_hits += 1
            return connection.on_hit(self, hit_amount, hit_player, type, grenade)

        def hit_percent_eject(self, accuracy):
            message = 'Aimbot detected - %i%% %s hit accuracy' %\
                      (100.0 * accuracy, self.weapon_object.name)
            if HIT_PERCENT == BAN:
                self.ban(message, HIT_PERCENT_BAN_DURATION)
            elif HIT_PERCENT == KICK:
                self.kick(message)
            elif HIT_PERCENT == WARN_ADMIN:
                current_time = reactor.seconds()
                if (current_time - self.hit_percent_warn_time) > WARN_INTERVAL_MINIMUM:
                    self.hit_percent_warn_time = current_time
                    self.warn_admin()

        def check_percent(self):
            if self.weapon == RIFLE_WEAPON:
                rifle_perc = float(self.rifle_hits)/float(self.rifle_count)
                if self.rifle_count >= RIFLE_KICK_MINIMUM:
                    if rifle_perc >= RIFLE_KICK_PERC:
                        self.hit_percent_eject(rifle_perc)
            elif self.weapon == SMG_WEAPON:
                smg_perc = float(self.smg_hits)/float(self.smg_count)
                if self.smg_count >= SMG_KICK_MINIMUM:
                    if smg_perc >= SMG_KICK_PERC:
                        self.hit_percent_eject(smg_perc)
            elif self.weapon == SHOTGUN_WEAPON:
                shotgun_perc = float(self.shotgun_hits)/float(self.shotgun_count)
                if self.shotgun_count >= SHOTGUN_KICK_MINIMUM:
                    if shotgun_perc >= SHOTGUN_KICK_PERC:
                        self.hit_percent_eject(shotgun_perc)

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
                position_v_mag = magnitude(position_v)
                if position_v_mag != 0 and (dot3d(orient_v, position_v)/position_v_mag) >= NEAR_MISS_COS:
                    if self.weapon == RIFLE_WEAPON:
                        self.rifle_count += 1
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
                        output += str(self.rifle_hits) + ',' + str(self.rifle_count) + ','
                        output += str(self.smg_hits) + ',' + str(self.smg_count) + ','
                        output += str(self.shotgun_hits) + ',' + str(self.shotgun_count) + '\n'
                        myfile.write(output)
                        myfile.close()
            return connection.on_disconnect(self)

    return Aimbot2Protocol, Aimbot2Connection
