from random import choice
from twisted.internet import reactor
# aparently, we need to send packets in this file. For now, I give in.
from pyspades.contained import CreatePlayer, SetTool, KillAction, InputData, SetColor, WeaponInput
from pyspades.constants import (GRENADE_KILL, FALL_KILL, NETWORK_FPS)
from pyspades.common import (
    prettify_timespan,
    make_color)
from piqueserver.commands import (
    command, CommandError, get_player, join_arguments, target_player)
from piqueserver.utils import timeparse


def has_digits(s: str) -> bool:
    return any(char.isdigit() for char in s)


def get_ban_arguments(connection, args):
    """
    Parses duration and reason from arguments.
    It handles duration in two ways: interger mintues and human-friendly duration.
    It also handles cases where duration or reason are none.
    Note: It returns duration in seconds.
    """
    default_duration = connection.protocol.default_ban_time
    reason = None
    if len(args) < 1:
        return default_duration, reason
    if len(args) > 1:
        reason = join_arguments(args[1:])
    if args[0] == "perma":
        return None, reason

    if args[0].isdigit():  # all digits == duration in minutes
        duration = int(args[0]) * 60
    elif has_digits(args[0]):  # if it contains some digits maybe duration?
        duration = timeparse(args[0])
        if not duration:
            raise ValueError("Invalid duration")
    else:  # maybe just one long reason
        duration = default_duration
        reason = join_arguments(args[:])
    return duration, reason


@command(admin_only=True)
def kick(connection, value, *arg):
    """
    Kick a given player
    /kick <player>
    Player is the #ID of the player, or an unique part of their name
    """
    reason = join_arguments(arg)
    player = get_player(connection.protocol, value)
    player.kick(reason)


@command(admin_only=True)
def ban(connection, value, *arg):
    """
    Ban a given player forever or for a limited amount of time.
    /ban <player> [duration] [reason]
    """
    duration, reason = get_ban_arguments(connection, arg)
    player = get_player(connection.protocol, value)
    player.ban(reason, duration)


@command(admin_only=True)
def hban(connection, value, *arg):
    """
    Ban a given player for an hour
    /hban <player> [reason]
    """
    duration = timeparse("1hour")
    reason = join_arguments(arg)
    player = get_player(connection.protocol, value)
    player.ban(reason, duration)


@command(admin_only=True)
def dban(connection, value, *arg):
    """
    Ban a given player for one day
    /dban <player> [reason]
    """
    duration = timeparse("1day")
    reason = join_arguments(arg)
    player = get_player(connection.protocol, value)
    player.ban(reason, duration)


@command(admin_only=True)
def wban(connection, value, *arg):
    """
    Ban a given player for one week
    /wban <player> [reason]
    """
    duration = timeparse("1week")
    reason = join_arguments(arg)
    player = get_player(connection.protocol, value)
    player.ban(reason, duration)


@command(admin_only=True)
def pban(connection, value, *arg):
    """
    Ban a given player permanently
    /pban <player> [reason]
    """
    duration = 0
    reason = join_arguments(arg)
    player = get_player(connection.protocol, value)
    player.ban(reason, duration)


@command(admin_only=True)
def banip(connection, ip, *arg):
    """
    Ban an ip
    /banip <ip> [duration] [reason]
    """
    duration, reason = get_ban_arguments(connection, arg)
    try:
        connection.protocol.add_ban(ip, reason, duration)
    except ValueError:
        return 'Invalid IP address/network'
    reason = ': ' + reason if reason is not None else ''
    duration = duration or None
    if duration is None:
        return 'IP/network %s permabanned%s' % (ip, reason)
    else:
        return 'IP/network %s banned for %s%s' % (
            ip, prettify_timespan(duration), reason)


@command(admin_only=True)
def unban(connection, ip):
    """
    Unban an ip
    /unban <ip>
    """
    try:
        connection.protocol.remove_ban(ip)
        return 'IP unbanned'
    except KeyError:
        return 'IP not found in ban list'


@command('undoban', admin_only=True)
def undo_ban(connection, *arg):
    """
    Undo last ban
    /undoban
    """
    if len(connection.protocol.bans) > 0:
        result = connection.protocol.undo_last_ban()
        return 'Ban for %s undone' % result[0]
    else:
        return 'No bans to undo!'


@command(admin_only=True)
def say(connection, *arg):
    """
    Say something in chat as server message
    /say <text>
    """
    value = ' '.join(arg)
    connection.protocol.send_chat(value)
    connection.protocol.irc_say(value)


@command(admin_only=True)
def mute(connection, value):
    """
    Mute a player
    /mute <player>
    """
    player = get_player(connection.protocol, value)
    if player.mute:
        return '%s is already muted' % player.name
    player.mute = True
    message = '%s has been muted by %s' % (player.name, connection.name)
    connection.protocol.send_chat(message, irc=True)


@command(admin_only=True)
def unmute(connection, value):
    """
    Unmute a player
    /unmute <player>
    """
    player = get_player(connection.protocol, value)
    if not player.mute:
        return '%s is not muted' % player.name
    player.mute = False
    message = '%s has been unmuted by %s' % (player.name, connection.name)
    connection.protocol.send_chat(message, irc=True)


@command(admin_only=True)
@target_player
def ip(connection, player):
    """
    Get the IP of a user
    /ip [player]
    """
    return 'The IP of %s is %s' % (player.name, player.address[0])


@command("whowas", admin_only=True)
def who_was(connection, value):
    """
    Get the IP of a user who has left
    /whowas <player>
    """
    value = value.lower()
    ret = None
    exact_match = False
    for name, ip in connection.protocol.player_memory:
        name_lower = name.lower()
        if name_lower == value:
            ret = (name, ip)
            exact_match = True
        elif not exact_match and name_lower.count(value):
            ret = (name, ip)
    if ret is None:
        raise CommandError("Invalid Player")
    return "%s's most recent IP was %s" % ret


@command('invisible', 'invis', 'inv', admin_only=True)
@target_player
def invisible(connection, player):
    """
    Turn invisible
    /invisible [player]
    """
    protocol = connection.protocol
    # TODO: move this logic to a more suitable place
    player.invisible = not player.invisible
    player.filter_visibility_data = player.invisible
    player.god = player.invisible
    player.god_build = False
    player.killing = not player.invisible
    if player.invisible:
        player.send_chat("You're now invisible")
        protocol.irc_say('* %s became invisible' % player.name)
        kill_action = KillAction()
        kill_action.kill_type = choice([GRENADE_KILL, FALL_KILL])
        kill_action.player_id = kill_action.killer_id = player.player_id
        reactor.callLater(1.0 / NETWORK_FPS, protocol.broadcast_contained,
                          kill_action, sender=player)
    else:
        player.send_chat("You return to visibility")
        protocol.irc_say('* %s became visible' % player.name)
        x, y, z = player.world_object.position.get()
        create_player = CreatePlayer()
        create_player.player_id = player.player_id
        create_player.name = player.name
        create_player.x = x
        create_player.y = y
        create_player.z = z
        create_player.weapon = player.weapon
        create_player.team = player.team.id
        world_object = player.world_object
        input_data = InputData()
        input_data.player_id = player.player_id
        input_data.up = world_object.up
        input_data.down = world_object.down
        input_data.left = world_object.left
        input_data.right = world_object.right
        input_data.jump = world_object.jump
        input_data.crouch = world_object.crouch
        input_data.sneak = world_object.sneak
        input_data.sprint = world_object.sprint
        set_tool = SetTool()
        set_tool.player_id = player.player_id
        set_tool.value = player.tool
        set_color = SetColor()
        set_color.player_id = player.player_id
        set_color.value = make_color(*player.color)
        weapon_input = WeaponInput()
        weapon_input.primary = world_object.primary_fire
        weapon_input.secondary = world_object.secondary_fire
        protocol.broadcast_contained(create_player, sender=player, save=True)
        protocol.broadcast_contained(set_tool, sender=player)
        protocol.broadcast_contained(set_color, sender=player, save=True)
        protocol.broadcast_contained(input_data, sender=player)
        protocol.broadcast_contained(weapon_input, sender=player)
    if connection is not player and connection in protocol.players.values():
        if player.invisible:
            return '%s is now invisible' % player.name
        else:
            return '%s is now visible' % player.name


@command('godsilent', 'gods', admin_only=True)
def godsilent(connection, player=None):
    """
    Silently go into god mode
    /godsilent [player]
    """
    if player is not None:
        connection = get_player(connection.protocol, player)
    elif connection not in connection.protocol.players.values():
        return 'Unknown player: ' + player

    connection.god = not connection.god  # toggle godmode

    if connection.protocol.set_god_build:
        connection.god_build = connection.god
    else:
        connection.god_build = False

    if connection.god:
        if player is None:
            return 'You have silently entered god mode'
        else:
            # TODO: Do not send this if the specified player is the one who called the command
            connection.send_chat(
                'Someone has made you silently enter godmode!')
            return 'You made ' + connection.name + ' silently enter god mode'
    else:
        if player is None:
            return 'You have silently returned to being a mere human'
        else:
            # TODO: Do not send this if the specified player is the one who called the command
            connection.send_chat(
                'Someone has made you silently return to being a mere human')
            return 'You made ' + connection.name + ' silently return to being a mere human'


@command(admin_only=True)
def god(connection, player=None):
    """
    Go into god mode and inform everyone on the server of it
    /god [player]
    """
    if player:
        connection = get_player(connection.protocol, player)
    elif connection not in connection.protocol.players.values():
        return 'Unknown player'

    connection.god = not connection.god  # toggle godmode

    if connection.god:
        message = '%s entered GOD MODE!' % connection.name
    else:
        message = '%s returned to being a mere human' % connection.name
    connection.protocol.send_chat(message, irc=True)


@command('godbuild', admin_only=True)
@target_player
def god_build(connection, player):
    """
    Place blocks that can be destroyed only by players with godmode activated
    /godbuild [player]
    """
    protocol = connection.protocol

    player.god_build = not player.god_build

    message = ('now placing god blocks' if player.god_build else
               'no longer placing god blocks')
    player.send_chat("You're %s" % message)
    if connection is not player and connection in protocol.players.values():
        connection.send_chat('%s is %s' % (player.name, message))
    protocol.irc_say('* %s is %s' % (player.name, message))
