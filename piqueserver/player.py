from __future__ import print_function, unicode_literals

import math

from twisted.internet import reactor

from piqueserver import commands

import pyspades
from pyspades.constants import (ERROR_BANNED, DESTROY_BLOCK, SPADE_DESTROY,
                                GRENADE_DESTROY, ERROR_KICKED, BLOCK_TOOL)
from pyspades.server import ServerConnection
from pyspades.common import encode, escape_control_codes, prettify_timespan, Vertex3
from pyspades.world import Character

# TODO: move these where they belong
CHAT_WINDOW_SIZE = 5
CHAT_PER_SECOND = 0.5

class FeatureConnection(ServerConnection):
    printable_name = None
    admin = False
    last_switch = None
    mute = False
    deaf = False
    login_retries = None
    god = False
    god_build = False
    fly = False
    invisible = False
    building = True
    killing = True
    streak = 0
    best_streak = 0
    last_chat = None
    chat_time = 0
    chat_count = 0
    user_types = None
    rights = None
    can_complete_line_build = True

    def on_connect(self):
        protocol = self.protocol
        client_ip = self.address[0]

        if client_ip in self.protocol.bans:
            name, reason, timestamp = self.protocol.bans[client_ip]

            if timestamp is not None and reactor.seconds() >= timestamp:
                protocol.remove_ban(client_ip)
                protocol.save_bans()
            else:
                print('banned user %s (%s) attempted to join' % (name,
                                                                 client_ip))
                self.disconnect(ERROR_BANNED)
                return

        manager = self.protocol.ban_manager

        if manager is not None:
            reason = manager.get_ban(client_ip)
            if reason is not None:
                print(('federated banned user (%s) attempted to join, '
                       'banned for %r') % (client_ip, reason))
                self.disconnect(ERROR_BANNED)
                return

        ServerConnection.on_connect(self)

    def on_join(self):
        if self.protocol.motd is not None:
            self.send_lines(self.protocol.motd)

    def on_login(self, name):
        self.printable_name = escape_control_codes(name)
        if len(self.printable_name) > 15:
            self.kick(silent=True)
        print('%s (IP %s, ID %s) entered the game!' % (self.printable_name,
                                                       self.address[0], self.player_id))
        self.protocol.irc_say('* %s (IP %s, ID %s) entered the game!' %
                              (self.name, self.address[0], self.player_id))
        if self.user_types is None:
            self.user_types = pyspades.types.AttributeSet()
            self.rights = pyspades.types.AttributeSet()
            if self.protocol.everyone_is_admin:
                self.on_user_login('admin', False)

    def get_spawn_location(self):
        get_location = self.protocol.map_info.get_spawn_location
        if get_location is not None:
            result = get_location(self)
            if result is not None:
                return result
        return ServerConnection.get_spawn_location(self)

    def on_disconnect(self):
        if self.name is not None:
            print(self.printable_name, 'disconnected!')
            self.protocol.irc_say('* %s (IP %s) disconnected' %
                                  (self.name, self.address[0]))
            self.protocol.player_memory.append((self.name, self.address[0]))
        else:
            print('%s disconnected' % self.address[0])
        ServerConnection.on_disconnect(self)

    def on_command(self, command, parameters):
        result = commands.handle_command(self, command, parameters)
        if result == False:
            parameters = ['***'] * len(parameters)
        log_message = '<%s> /%s %s' % (self.name, command,
                                       ' '.join(parameters))
        if result:
            log_message += ' -> %s' % result
            for i in reversed(result.split("\n")):
                self.send_chat(i)
        print(escape_control_codes(log_message))

    def _can_build(self):
        if not self.can_complete_line_build:
            return False
        if not self.building:
            return False
        if not self.god and not self.protocol.building:
            return False

    def on_block_build_attempt(self, x, y, z):
        return self._can_build()

    def on_secondary_fire_set(self, secondary):

        # Inlined from fbpatch.py
        # Author: Nick Christensen AKA a_girl
        # Distant Drag Build Client Bug Patch for (0.75) and possibly (0.76)
        #
        # if right mouse button has been clicked to initiate drag building;
        # distinguishes from the right click release that marks the end point.
        if secondary:
            if self.tool == BLOCK_TOOL:  # 1 refers to block tool; if the tool in hand is a block
                # grab player current position at drag build start
                position = self.world_object.position
                # grab player current orientation at drag build start
                vector = self.world_object.orientation
                # probably unnecessary, but makes sure vector values are
                # between 0 and 1 inclusive
                vector.normalize()
                # creates a line object starting at player and following
                # their point of view.
                c = Character(self.world_object.world, position, vector)
                # finds coordinates of the first block this line strikes.
                line_start = c.cast_ray()
                if line_start:  # if player is pointing at a valid point.  Distant solid blocks will return False
                    distance = (Vertex3(*line_start) - Vertex3(position.x, position.y, position.z)).length()
                    if distance > 6:
                        self.can_complete_line_build = False
                    else:
                        self.can_complete_line_build = True
                else:
                    self.can_complete_line_build = False

    def on_line_build_attempt(self, points):
        if self._can_build() == False:
            return False

        # originally from the bugfix.py script
        # prevent "unlimited tower" crash, fix by Danko
        for point in points:
            x, y, z = point
            if x < 0 or x > 511 or y < 0 or y > 511 or z < 0 or z > 61:
                return False
        return True

    def on_line_build(self, points):
        if self.god:
            self.refill()
        if self.god_build:
            if self.protocol.god_blocks is None:
                self.protocol.god_blocks = set()
            self.protocol.god_blocks.update(points)
        elif self.protocol.user_blocks is not None:
            self.protocol.user_blocks.update(points)

    def on_block_build(self, x, y, z):
        if self.god:
            self.refill()
        if self.god_build:
            if self.protocol.god_blocks is None:
                self.protocol.god_blocks = set()
            self.protocol.god_blocks.add((x, y, z))
        elif self.protocol.user_blocks is not None:
            self.protocol.user_blocks.add((x, y, z))

    def on_block_destroy(self, x, y, z, mode):
        map_on_block_destroy = self.protocol.map_info.on_block_destroy
        if map_on_block_destroy is not None:
            result = map_on_block_destroy(self, x, y, z, mode)
            if result == False:
                return result
        if not self.building:
            return False
        if not self.god:
            if not self.protocol.building:
                return False
            is_indestructable = self.protocol.is_indestructable
            if mode == DESTROY_BLOCK:
                if is_indestructable(x, y, z):
                    return False
            elif mode == SPADE_DESTROY:
                if (is_indestructable(x, y, z) or
                        is_indestructable(x, y, z + 1) or
                        is_indestructable(x, y, z - 1)):
                    return False
            elif mode == GRENADE_DESTROY:
                for nade_x in range(x - 1, x + 2):
                    for nade_y in range(y - 1, y + 2):
                        for nade_z in range(z - 1, z + 2):
                            if is_indestructable(nade_x, nade_y, nade_z):
                                return False

    def on_block_removed(self, x, y, z):
        if self.protocol.user_blocks is not None:
            self.protocol.user_blocks.discard((x, y, z))
        if self.protocol.god_blocks is not None:
            self.protocol.god_blocks.discard((x, y, z))

    def on_hit(self, hit_amount, player, _type, grenade):
        if not self.protocol.killing:
            self.send_chat(
                "You can't kill anyone right now! Damage is turned OFF")
            return False
        if not self.killing:
            self.send_chat("%s. You can't kill anyone." % player.name)
            return False
        elif player.god:
            if not player.invisible:
                self.send_chat("You can't hurt %s! That player is in "
                               "*god mode*" % player.name)
            return False
        if self.god:
            self.protocol.send_chat('%s, killing in god mode is forbidden!' %
                                    self.name, irc=True)
            self.protocol.send_chat('%s returned to being a mere human.' %
                                    self.name, irc=True)
            self.god = False
            self.god_build = False

    def on_kill(self, killer, _type, grenade):
        self.streak = 0
        if killer is None or self.team is killer.team:
            return
        if not grenade or grenade.name == 'grenade':
            # doesn't give streak kills on airstrikes (or other types of
            # explosions)
            killer.streak += 1
            killer.best_streak = max(killer.streak, killer.best_streak)
        killer.team.kills += 1

    def on_reset(self):
        self.streak = 0
        self.best_streak = 0

    def on_animation_update(self, jump, crouch, sneak, sprint):
        if self.fly and crouch and self.world_object.velocity.z != 0.0:
            jump = True
        return jump, crouch, sneak, sprint

    def on_fall(self, damage):
        if self.god:
            return False
        if not self.protocol.fall_damage:
            return False

    def on_grenade(self, time_left):
        if self.god:
            self.refill()

    def on_team_join(self, team):
        if self.team is not None:
            if self.protocol.teamswitch_interval:
                teamswitch_interval = self.protocol.teamswitch_interval
                if teamswitch_interval == 'never':
                    self.send_chat('Switching teams is not allowed')
                    return False
                if (self.last_switch is not None and
                        reactor.seconds() - self.last_switch < teamswitch_interval * 60):
                    self.send_chat(
                        'You must wait before switching teams again')
                    return False
        if team.locked:
            self.send_chat('Team is locked')
            if not team.spectator and not team.other.locked:
                return team.other
            return False
        balanced_teams = self.protocol.balanced_teams
        if balanced_teams and not team.spectator:
            other_team = team.other
            if other_team.count() < team.count() + 1 - balanced_teams:
                if other_team.locked:
                    return False
                self.send_chat('Team is full, moved to %s' % other_team.name)
                return other_team
        self.last_switch = reactor.seconds()

    def on_chat(self, value, global_message):
        """
        notifies when the server recieves a chat message

        return False to block sending the message
        """
        message = '<{}> {}'.format(self.name, value)

        if self.mute:
            message = '(MUTED) {}'.format(message)
            self.send_chat('(Chat not sent - you are muted)')
            return False

        if global_message:
            if self.protocol.global_chat:
                # forward message to IRC
                self.protocol.irc_say(message)
            else:
                self.send_chat('(Chat not sent - global chat disabled)')
                return False

        # antispam:
        current_time = reactor.seconds()
        if self.last_chat is None:
            self.last_chat = current_time

        else:
            self.chat_time += current_time - self.last_chat

            if self.chat_count > CHAT_WINDOW_SIZE:
                if self.chat_count / self.chat_time > CHAT_PER_SECOND:
                    self.mute = True
                    self.protocol.send_chat(
                        '%s has been muted for excessive spam' % (
                            self.name),
                        irc=True)

                # reset if CHAT_WINDOW_SIZE messages were sent and not
                # determined to be spam
                self.chat_time = 0
                self.chat_count = 0
            else:
                self.chat_count += 1
            self.last_chat = current_time

        # TODO: replace with logging
        print(escape_control_codes(message))

        return value

    def kick(self, reason=None, silent=False):
        if not silent:
            if reason is not None:
                message = '%s was kicked: %s' % (self.name, reason)
            else:
                message = '%s was kicked' % self.name
            self.protocol.send_chat(message, irc=True)
        # FIXME: Client should handle disconnect events the same way in both
        # main and initial loading network loops
        self.disconnect(ERROR_KICKED)

    def ban(self, reason=None, duration=None):
        reason = ': ' + reason if reason is not None else ''
        duration = duration or None
        if duration is None:
            message = '%s permabanned%s' % (self.name, reason)
        else:
            message = '%s banned for %s%s' % (self.name,
                                              prettify_timespan(duration * 60), reason)
        if self.protocol.on_ban_attempt(self, reason, duration):
            self.protocol.send_chat(message, irc=True)
            self.protocol.on_ban(self, reason, duration)
            if self.address[0] == "127.0.0.1":
                self.protocol.send_chat("Ban ignored: localhost")
            else:
                self.protocol.add_ban(self.address[0], reason, duration,
                                      self.name)

    def send_lines(self, lines):
        current_time = 0
        for line in lines:
            reactor.callLater(current_time, self.send_chat, line)
            current_time += 2

    def on_hack_attempt(self, reason):
        print('Hack attempt detected from %s: %s' % (self.printable_name,
                                                     reason))
        self.kick(reason)

    def on_user_login(self, user_type, verbose=True):
        if user_type == 'admin':
            self.admin = True
            self.speedhack_detect = False
        self.user_types.add(user_type)
        rights = set(commands.get_rights(user_type))
        self.rights.update(rights)
        if verbose:
            message = ' logged in as %s' % (user_type)
            self.send_chat('You' + message)
            self.protocol.irc_say("* " + self.name + message)

    def timed_out(self):
        if self.name is not None:
            print('%s timed out' % self.printable_name)
        ServerConnection.timed_out(self)


def encode_lines(value):
    if value is not None:
        return [encode(line) for line in value]
