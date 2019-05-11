"""
Detects and reacts to possible aimbot users.

Commands
^^^^^^^^

* ``/accuracy <player>`` shows player's accuracy per weapon
* ``/hackinfo <player>`` shows player's accuracy, K/D ratio and how often their cross-hair snaps onto another players head *admin only*

Options
^^^^^^^

.. code-block:: guess

   [aimbot]
   collect_data = true # saves hits and shots of each weapon to a csv file

.. codeauthor:: ?
"""
import os
import csv
import re
from math import sqrt, cos, pi

from twisted.internet.task import LoopingCall
from twisted.internet import reactor

from pyspades.constants import (
    WEAPON_TOOL, WEAPON_KILL, HEADSHOT_KILL,
    RIFLE_WEAPON, SMG_WEAPON, SHOTGUN_WEAPON,
)
from piqueserver.commands import command, admin, get_player
from piqueserver.config import config
from piqueserver.utils import parse

DISABLED, KICK, BAN, WARN_ADMIN = range(4)

# This controls which detection methods are enabled. If a player is detected
# using one of these methods, the player is kicked.
HEADSHOT_SNAP = WARN_ADMIN
HIT_PERCENT = WARN_ADMIN
KILLS_IN_TIME = WARN_ADMIN
MULTIPLE_BULLETS = WARN_ADMIN

# Minimum amount of time that must pass between admin warnings that are
# triggered by the same detection method. Time is in seconds.
WARN_INTERVAL_MINIMUM = 300

# These controls are only used if banning is enabled
# Time is given in minutes. Set to 0 for a permaban
HEADSHOT_SNAP_BAN_DURATION = parse("23hours")
HIT_PERCENT_BAN_DURATION = parse("1day")
KILLS_IN_TIME_BAN_DURATION = parse("2day")
MULTIPLE_BULLETS_BAN_DURATION = parse("1week")

# If more than or equal to this number of weapon hit packets are received
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

# Approximate size of player's heads in blocks
HEAD_RADIUS = 0.7

# 128 is the approximate fog distance, but bump it up a little
# just in case
FOG_DISTANCE = 135.0

# Don't touch any of this stuff
FOG_DISTANCE2 = FOG_DISTANCE**2
NEAR_MISS_COS = cos(NEAR_MISS_ANGLE * (pi / 180.0))
HEADSHOT_SNAP_ANGLE_COS = cos(HEADSHOT_SNAP_ANGLE * (pi / 180.0))

aimbot_pattern = re.compile(".*(aim|bot|ha(ck|x)|cheat).*", re.IGNORECASE)
aimbot_config = config.section("aimbot")
collect_data = aimbot_config.option("collect_data", False)
config_dir = config.config_dir
def point_distance2(c1, c2):
    if c1.world_object is not None and c2.world_object is not None:
        p1 = c1.world_object.position
        p2 = c2.world_object.position
        return (p1.x - p2.x)**2 + (p1.y - p2.y)**2 + (p1.z - p2.z)**2


def dot3d(v1, v2):
    return v1[0] * v2[0] + v1[1] * v2[1] + v1[2] * v2[2]


def magnitude(v):
    return sqrt(v[0]**2 + v[1]**2 + v[2]**2)


def scale(v, factor):
    return (v[0] * factor, v[1] * factor, v[2] * factor)


def subtract(v1, v2):
    return (v1[0] - v2[0], v1[1] - v2[1], v1[2] - v2[2])


@command()
def accuracy(connection, name=None):
    if name is None:
        player = connection
    else:
        player = get_player(connection.protocol, name)
    return accuracy_player(player)


def accuracy_player(player, name_info=True):
    if player.rifle_count != 0:
        rifle_percent = "{0:.1f}%".format(
            (player.rifle_hits / player.rifle_count) * 100)
    else:
        rifle_percent = 'None'
    if player.smg_count != 0:
        smg_percent = "{0:.1f}%".format(
            (player.smg_hits / player.smg_count) * 100)
    else:
        smg_percent = 'None'
    if player.shotgun_count != 0:
        shotgun_percent = "{0:.1f}%".format(
            (player.shotgun_hits / player.shotgun_count) * 100)
    else:
        shotgun_percent = 'None'

    s = ''
    if name_info:
        s += player.name + ' has an accuracy of: '
    s += 'Rifle: %s SMG: %s Shotgun: %s.' % (
        rifle_percent, smg_percent, shotgun_percent)
    return s


@command(admin_only=True)
def hackinfo(connection, name):
    player = get_player(connection.protocol, name)
    return hackinfo_player(player)


def hackinfo_player(player):
    info = "%s #%s (%s) has an accuracy of: " % (
        player.name, player.player_id, player.address[0])
    info += accuracy_player(player, False)
    ratio = player.ratio_kills / float(max(1, player.ratio_deaths))
    info += " Kill-death ratio of %.2f (%s kills, %s deaths)." % (
        ratio, player.ratio_kills, player.ratio_deaths)
    info += " %i kills in the last %i seconds." % (
        player.get_kill_count(), KILL_TIME)
    info += " %i headshot snaps in the last %i seconds." % (
        player.get_headshot_snap_count(), HEADSHOT_SNAP_TIME)
    return info


def apply_script(protocol, connection, config):
    class Aimbot2Protocol(protocol):

        def start_votekick(self, payload):
            if not aimbot_pattern.match(payload.reason) is None:
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

        def warn_admin(self, prefix='Possible aimbot detected.'):
            prefix += ' '
            message = hackinfo_player(self)
            for player in list(self.protocol.players.values()):
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

            self.headshot_snap_times = self.headshot_snap_times[pop_count:]
            return headshot_snap_count

        def on_orientation_update(self, x, y, z):
            if self.first_orientation or self.world_object is None:
                # we have no orientation data yet
                self.first_orientation = False
                return connection.on_orientation_update(self, x, y, z)

            orient = self.world_object.orientation
            old_orient_v = (orient.x, orient.y, orient.z)
            new_orient_v = (x, y, z)
            theta = dot3d(old_orient_v, new_orient_v)

            if theta > HEADSHOT_SNAP_ANGLE_COS:
                # The angle didn't change enough
                return connection.on_orientation_update(self, x, y, z)

            self_pos = self.world_object.position
            for enemy in self.team.other.get_players():
                enemy_pos = enemy.world_object.position
                position_v = (enemy_pos.x - self_pos.x, enemy_pos.y -
                              self_pos.y, enemy_pos.z - self_pos.z)
                c = scale(new_orient_v, dot3d(new_orient_v, position_v))
                h = magnitude(subtract(position_v, c))

                if h > HEAD_RADIUS:
                    # Didn't snap near a head
                    continue

                current_time = reactor.seconds()
                self.headshot_snap_times.append(current_time)

                if self.get_headshot_snap_count() < HEADSHOT_SNAP_THRESHOLD:
                    # Not enough headshots yet
                    continue

                if HEADSHOT_SNAP == BAN:
                    self.ban('Aimbot detected - headshot snap',
                             HEADSHOT_SNAP_BAN_DURATION)
                    return
                elif HEADSHOT_SNAP == KICK:
                    self.kick(
                        'Aimbot detected - headshot snap')
                    return
                elif HEADSHOT_SNAP == WARN_ADMIN:
                    if (current_time -
                            self.headshot_snap_warn_time) > WARN_INTERVAL_MINIMUM:
                        self.headshot_snap_warn_time = current_time
                        self.warn_admin()

            return connection.on_orientation_update(self, x, y, z)

        def on_shoot_set(self, shoot):
            if self.tool != WEAPON_TOOL:
                return connection.on_shoot_set(self, shoot)

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

            self.kill_times = self.kill_times[pop_count:]
            return kill_count

        def on_kill(self, by, kill_type, grenade):
            if by is None or by is self:
                return connection.on_kill(self, by, kill_type, grenade)

            if kill_type != WEAPON_KILL and kill_type != HEADSHOT_KILL:
                return connection.on_kill(self, by, kill_type, grenade)

            by.kill_times.append(reactor.seconds())
            if by.get_kill_count() >= KILL_THRESHOLD:
                if KILLS_IN_TIME == BAN:
                    by.ban('Aimbot detected - kills in time window',
                           KILLS_IN_TIME_BAN_DURATION)
                    return
                elif KILLS_IN_TIME == KICK:
                    by.kick('Aimbot detected - kills in time window')
                    return
                elif KILLS_IN_TIME == WARN_ADMIN:
                    current_time = reactor.seconds()
                    if ((current_time - by.kills_in_time_warn_time)
                            > WARN_INTERVAL_MINIMUM):
                        by.kills_in_time_warn_time = current_time
                        by.warn_admin()

            return connection.on_kill(self, by, kill_type, grenade)

        def multiple_bullets_eject(self):
            if MULTIPLE_BULLETS == BAN:
                self.ban('Aimbot detected - multiple bullets',
                         MULTIPLE_BULLETS_BAN_DURATION)
            elif MULTIPLE_BULLETS == KICK:
                self.kick('Aimbot detected - multiple bullets')
            elif MULTIPLE_BULLETS == WARN_ADMIN:
                current_time = reactor.seconds()
                if ((current_time - self.multiple_bullets_warn_time)
                        > WARN_INTERVAL_MINIMUM):
                    self.multiple_bullets_warn_time = current_time
                    self.warn_admin()

        def on_hit(self, hit_amount, hit_player, hit_type, grenade):
            if self.team is hit_player.team or hit_type not in (
                    WEAPON_KILL, HEADSHOT_KILL):
                return connection.on_hit(
                    self, hit_amount, hit_player, hit_type, grenade)

            current_time = reactor.seconds()
            shotgun_use = False
            if current_time - \
                    self.shot_time > (0.5 * hit_player.weapon_object.delay):
                shotgun_use = True
                self.multiple_bullets_count = 0
                self.shot_time = current_time
            if hit_type == HEADSHOT_KILL:
                self.multiple_bullets_count += 1
            if self.weapon == RIFLE_WEAPON:
                self.rifle_hits += 1
                if self.multiple_bullets_count >= RIFLE_MULTIPLE_BULLETS_MAX:
                    self.multiple_bullets_eject()
                    return False
            elif self.weapon == SMG_WEAPON:
                self.smg_hits += 1
                if self.multiple_bullets_count >= SMG_MULTIPLE_BULLETS_MAX:
                    self.multiple_bullets_eject()
                    return False
            elif self.weapon == SHOTGUN_WEAPON:
                self.shotgun_hits += 1

            return connection.on_hit(
                self, hit_amount, hit_player, hit_type, grenade)

        def hit_percent_eject(self, hit_accuracy):
            message = 'Aimbot detected - %i%% %s hit accuracy' %\
                      (100.0 * hit_accuracy, self.weapon_object.name)
            if HIT_PERCENT == BAN:
                self.ban(message, HIT_PERCENT_BAN_DURATION)
            elif HIT_PERCENT == KICK:
                self.kick(message)
            elif HIT_PERCENT == WARN_ADMIN:
                current_time = reactor.seconds()
                if (current_time -
                        self.hit_percent_warn_time) > WARN_INTERVAL_MINIMUM:
                    self.hit_percent_warn_time = current_time
                    self.warn_admin()

        def check_percent(self):
            if self.weapon == RIFLE_WEAPON:
                rifle_perc = float(self.rifle_hits) / float(self.rifle_count)
                if self.rifle_count >= RIFLE_KICK_MINIMUM:
                    if rifle_perc >= RIFLE_KICK_PERC:
                        self.hit_percent_eject(rifle_perc)
            elif self.weapon == SMG_WEAPON:
                smg_perc = float(self.smg_hits) / float(self.smg_count)
                if self.smg_count >= SMG_KICK_MINIMUM:
                    if smg_perc >= SMG_KICK_PERC:
                        self.hit_percent_eject(smg_perc)
            elif self.weapon == SHOTGUN_WEAPON:
                shotgun_perc = float(self.shotgun_hits) / \
                    float(self.shotgun_count)
                if self.shotgun_count >= SHOTGUN_KICK_MINIMUM:
                    if shotgun_perc >= SHOTGUN_KICK_PERC:
                        self.hit_percent_eject(shotgun_perc)

        def on_bullet_fire(self):
            # Remembering the past offers a performance boost, particularly
            # with the SMG
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
                position_v = (p_targ.x - p_self.x, p_targ.y -
                              p_self.y, p_targ.z - p_self.z)
                orient = self.world_object.orientation
                orient_v = (orient.x, orient.y, orient.z)
                position_v_mag = magnitude(position_v)
                if position_v_mag != 0 and (
                    dot3d(
                        orient_v,
                        position_v) /
                        position_v_mag) >= NEAR_MISS_COS:
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
            if collect_data.get():
                if self.name is not None:
                    with open(os.path.join(config_dir,'aimbot2log.csv'), 'a+') as csvfile:
                        csvfile.seek(0)
                        fieldnames = ['name', 'rifle_hits', 'rifle_count', 'smg_hits', 'smg_count', 'shotgun_hits', 'shotgun_count']
                        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                        try:
                            has_header = csv.Sniffer().has_header(csvfile.readline())
                        except csv.Error:
                            # Empty file causes this error
                            has_header = False
                        if not has_header:
                            writer.writeheader()
                        writer.writerow({
                            'name': self.name,
                            'rifle_hits': self.rifle_hits,
                            'rifle_count': self.rifle_count,
                            'smg_hits': self.smg_hits,
                            'smg_count': self.smg_count,
                            'shotgun_hits': self.shotgun_hits,
                            'shotgun_count': self.shotgun_count
                        })
                        csvfile.close()
            return connection.on_disconnect(self)

    return Aimbot2Protocol, Aimbot2Connection
