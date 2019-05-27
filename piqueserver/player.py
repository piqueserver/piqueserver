import math
from typing import List, Tuple, Optional, Union

from twisted.internet import reactor
from twisted.logger import Logger

from piqueserver import commands
from piqueserver.release import format_release
import pyspades
from pyspades.constants import (ERROR_BANNED, DESTROY_BLOCK, SPADE_DESTROY,
                                GRENADE_DESTROY, ERROR_KICKED, BLOCK_TOOL)
from pyspades.server import ServerConnection
from pyspades.common import encode, escape_control_codes, prettify_timespan, Vertex3
from pyspades.world import Character
from pyspades.types import AttributeSet

# TODO: move these where they belong
from pyspades.team import Team
from pyspades.world import Grenade
CHAT_WINDOW_SIZE = 5
CHAT_PER_SECOND = 0.5

HookValue = Optional[bool]

log = Logger()


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

    def on_connect(self) -> None:
        protocol = self.protocol
        client_ip = self.address[0]

        if client_ip in self.protocol.bans:
            name, reason, timestamp = self.protocol.bans[client_ip]

            if timestamp is not None and reactor.seconds() >= timestamp:
                protocol.remove_ban(client_ip)
                protocol.save_bans()
            else:
                log.info('banned user {} ({}) attempted to join'.format(name,
                                                                        client_ip))
                self.disconnect(ERROR_BANNED)
                return

        manager = self.protocol.ban_manager

        if manager is not None:
            reason = manager.get_ban(client_ip)
            if reason is not None:
                log.info(('federated banned user (%s) attempted to join, '
                          'banned for %r') % (client_ip, reason))
                self.disconnect(ERROR_BANNED)
                return

        ServerConnection.on_connect(self)

    def on_join(self) -> None:
        if self.protocol.motd is not None:
            self.send_lines(self.protocol.motd)

    def on_login(self, name: str) -> None:
        self.printable_name = escape_control_codes(name)
        if len(self.printable_name) > 15:
            self.kick(silent=True)
        log.info('{name} (IP {ip}, ID {pid}) entered the game!',
                 name=self.printable_name,
                 ip=self.address[0], pid=self.player_id)
        self.protocol.irc_say('* %s (IP %s, ID %s) entered the game!' %
                              (self.name, self.address[0], self.player_id))
        if self.user_types is None:
            self.user_types = AttributeSet()
            self.rights = AttributeSet()
            if self.protocol.everyone_is_admin:
                self.on_user_login('admin', False)

    def get_spawn_location(self) -> Tuple[int, int, int]:
        get_location = self.protocol.map_info.get_spawn_location
        if get_location is not None:
            result = get_location(self)
            if result is not None:
                return result
        return ServerConnection.get_spawn_location(self)

    def on_disconnect(self) -> None:
        if self.name is not None:
            log.info('{name} disconnected!', name=self.printable_name)
            self.protocol.irc_say('* %s (IP %s) disconnected' %
                                  (self.name, self.address[0]))
            self.protocol.player_memory.append((self.name, self.address[0]))
        else:
            log.info('{ip} disconnected', ip=self.address[0])
        ServerConnection.on_disconnect(self)

    def on_command(self, command: str, parameters: List[str]) -> None:
        result = commands.handle_command(self, command, parameters)

        if result:
            for i in reversed(result.split("\n")):
                self.send_chat(i)

    def _can_build(self) -> bool:
        if not self.building:
            return False
        if not self.god and not self.protocol.building:
            return False

        return True

    def on_block_build_attempt(self, x: int, y: int, z: int) -> bool:
        return self._can_build()

    def on_line_build_attempt(self, points) -> bool:
        return self._can_build()

    def on_line_build(self, points) -> None:
        if self.god:
            self.refill()
        if self.god_build:
            if self.protocol.god_blocks is None:
                self.protocol.god_blocks = set()
            self.protocol.god_blocks.update(points)
        elif self.protocol.user_blocks is not None:
            self.protocol.user_blocks.update(points)

    def on_block_build(self, x: int, y: int, z: int) -> None:
        if self.god:
            self.refill()
        if self.god_build:
            if self.protocol.god_blocks is None:
                self.protocol.god_blocks = set()
            self.protocol.god_blocks.add((x, y, z))
        elif self.protocol.user_blocks is not None:
            self.protocol.user_blocks.add((x, y, z))

    def on_block_destroy(self, x: int, y: int, z: int, mode: int) -> bool:
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

    def on_block_removed(self, x: int, y: int, z: int) -> None:
        if self.protocol.user_blocks is not None:
            self.protocol.user_blocks.discard((x, y, z))
        if self.protocol.god_blocks is not None:
            self.protocol.god_blocks.discard((x, y, z))

    def on_hit(self, hit_amount: float, player: 'FeatureConnection',
               _type: int, grenade: Grenade) -> HookValue:
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

    def on_kill(self, killer: Optional['FeatureConnection'], _type: int,
                grenade: None) -> None:
        self.streak = 0
        if killer is None or self.team is killer.team:
            return
        if not grenade or grenade.name == 'grenade':
            # doesn't give streak kills on airstrikes (or other types of
            # explosions)
            killer.streak += 1
            killer.best_streak = max(killer.streak, killer.best_streak)
        killer.team.kills += 1

    def on_reset(self) -> None:
        self.streak = 0
        self.best_streak = 0

    def on_animation_update(self, jump: bool, crouch: bool, sneak: bool,
                            sprint: bool) -> Tuple[bool, bool, bool, bool]:
        if self.fly and crouch and self.world_object.velocity.z != 0.0:
            jump = True
        return jump, crouch, sneak, sprint

    def on_fall(self, damage: int) -> HookValue:
        if self.god:
            return False
        if not self.protocol.fall_damage:
            return False

    def on_grenade(self, time_left: float) -> None:
        if self.god:
            self.refill()

    def on_team_join(self, team: 'FeatureTeam') -> HookValue:
        if self.team is not None:
            if self.protocol.teamswitch_interval:
                teamswitch_interval = self.protocol.teamswitch_interval
                teamswitch_allowed = self.protocol.teamswitch_allowed
                if not teamswitch_allowed:
                    self.send_chat('Switching teams is not allowed')
                    return False
                if (self.last_switch is not None and
                        reactor.seconds() - self.last_switch < teamswitch_interval):
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

    def on_chat(self, value: str, global_message: bool) -> Union[str, bool]:
        """
        notifies when the server receives a chat message

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

        log.info("<{name}> {message}", name=escape_control_codes(
            self.name), message=escape_control_codes(value))

        return value

    def kick(self, reason=None, silent=False):
        if not silent:
            if reason is not None:
                message = '{} was kicked: {}'.format(self.name, reason)
            else:
                message = '%s was kicked' % self.name
            self.protocol.send_chat(message, irc=True)
            log.info(message)
        # FIXME: Client should handle disconnect events the same way in both
        # main and initial loading network loops
        self.disconnect(ERROR_KICKED)

    def ban(self, reason=None, duration=None):
        reason = ': ' + reason if reason is not None else ''
        duration = duration or None
        if duration is None:
            message = '{} permabanned{}'.format(self.name, reason)
        else:
            message = '{} banned for {}{}'.format(self.name,
                                                  prettify_timespan(duration), reason)
        if self.protocol.on_ban_attempt(self, reason, duration):
            self.protocol.send_chat(message, irc=True)
            self.protocol.on_ban(self, reason, duration)
            if self.address[0] == "127.0.0.1":
                self.protocol.send_chat("Ban ignored: localhost")
            else:
                self.protocol.add_ban(self.address[0], reason, duration,
                                      self.name)

    def send_lines(self, lines: List[str]) -> None:
        current_time = 0
        for line in lines:
            reactor.callLater(current_time, self.send_chat, line)
            current_time += 2

    def on_hack_attempt(self, reason):
        log.warn('Hack attempt detected from {}: {}'.format(self.printable_name,
                                                            reason))
        self.kick(reason)

    def on_user_login(self, user_type, verbose=True):
        log.info("'{username}' logged in as {user_type}", username=self.name,
                 user_type=user_type)

        if user_type == 'admin':
            self.admin = True
            self.speedhack_detect = False

        # notify of new release to admin on /login
        new_release = self.protocol.new_release
        if user_type == 'admin' and new_release:
            self.send_chat("!" * 30)
            self.send_chat(format_release(new_release))
            self.send_chat("!" * 30)

        self.user_types.add(user_type)
        rights = set(commands.get_rights(user_type))
        self.rights.update(rights)
        if verbose:
            message = ' logged in as %s' % (user_type)
            self.send_chat('You' + message)
            self.protocol.irc_say("* " + self.name + message)

    def timed_out(self):
        if self.name is not None:
            log.info('%s timed out' % self.printable_name)
        ServerConnection.timed_out(self)
