from random import choice
from twisted.internet import reactor
from pyspades.contained import KillAction, InputData, SetColor, WeaponInput
from pyspades.player import create_player, set_tool
from pyspades.constants import (GRENADE_KILL, FALL_KILL, NETWORK_FPS)
from pyspades.common import (
    prettify_timespan,
    make_color)
from piqueserver.commands import command, CommandError, get_player, join_arguments


# aparently, we need to send packets in this file. For now, I give in.
kill_action = KillAction()
input_data = InputData()
set_color = SetColor()
weapon_input = WeaponInput()


def get_ban_arguments(connection, arg):
    duration = None
    if len(arg):
        try:
            duration = int(arg[0])
            arg = arg[1:]
        except (IndexError, ValueError):
            pass
    if duration is None:
        if len(arg) > 0 and arg[0] == "perma":
            arg = arg[1:]
        else:
            duration = connection.protocol.default_ban_time
    reason = join_arguments(arg)
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
    Ban a given player forever or for a limited amount of time
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
    duration = 60
    reason = join_arguments(arg)
    player = get_player(connection.protocol, value)
    player.ban(reason, duration)


@command(admin_only=True)
def dban(connection, value, *arg):
    """
    Ban a given player for one day
    /dban <player> [reason]
    """
    duration = 1440
    reason = join_arguments(arg)
    player = get_player(connection.protocol, value)
    player.ban(reason, duration)


@command(admin_only=True)
def wban(connection, value, *arg):
    """
    Ban a given player for one week
    /wban <player> [reason]
    """
    duration = 10080
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
    /banip <ip> [reason]
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
            ip, prettify_timespan(duration * 60), reason)


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
def ip(connection, value=None):
    """
    Get the IP of a user
    /ip [player]
    """
    if value is None:
        if connection not in connection.protocol.players:
            raise ValueError()
        player = connection
    else:
        player = get_player(connection.protocol, value)
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
def invisible(connection, player=None):
    """
    Turn invisible
    /invisible [player]
    """
    protocol = connection.protocol
    if player is not None:
        player = get_player(protocol, player)
    elif connection in protocol.players:
        player = connection
    else:
        raise ValueError()
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
        reactor.callLater(1.0 / NETWORK_FPS, protocol.send_contained,
                          kill_action, sender=player)
    else:
        player.send_chat("You return to visibility")
        protocol.irc_say('* %s became visible' % player.name)
        x, y, z = player.world_object.position.get()
        create_player.player_id = player.player_id
        create_player.name = player.name
        create_player.x = x
        create_player.y = y
        create_player.z = z
        create_player.weapon = player.weapon
        create_player.team = player.team.id
        world_object = player.world_object
        input_data.player_id = player.player_id
        input_data.up = world_object.up
        input_data.down = world_object.down
        input_data.left = world_object.left
        input_data.right = world_object.right
        input_data.jump = world_object.jump
        input_data.crouch = world_object.crouch
        input_data.sneak = world_object.sneak
        input_data.sprint = world_object.sprint
        set_tool.player_id = player.player_id
        set_tool.value = player.tool
        set_color.player_id = player.player_id
        set_color.value = make_color(*player.color)
        weapon_input.primary = world_object.primary_fire
        weapon_input.secondary = world_object.secondary_fire
        protocol.send_contained(create_player, sender=player, save=True)
        protocol.send_contained(set_tool, sender=player)
        protocol.send_contained(set_color, sender=player, save=True)
        protocol.send_contained(input_data, sender=player)
        protocol.send_contained(weapon_input, sender=player)
    if connection is not player and connection in protocol.players:
        if player.invisible:
            return '%s is now invisible' % player.name
        else:
            return '%s is now visible' % player.name
