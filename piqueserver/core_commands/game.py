import math
import re
from twisted.internet import reactor
from piqueserver.commands import command, CommandError, get_player, get_team, get_truthy


@command('time')
def get_time_limit(connection):
    """
    Tell you the current time limit
    /time
    """
    advance_call = connection.protocol.advance_call
    if advance_call is None:
        return 'No time limit set'
    left = int(
        math.ceil((advance_call.getTime() - reactor.seconds()) / 60.0))
    return 'There are %s minutes left' % left


@command("resetgame", admin_only=True)
def reset_game(connection):
    """
    Reset the game
    /resetgame
    """
    resetting_player = connection
    # irc compatibility
    if resetting_player not in connection.protocol.players:
        for player in connection.protocol.players.values():
            resetting_player = player
            if player.admin:
                break
        if resetting_player is connection:
            return
    connection.protocol.reset_game(resetting_player)
    connection.protocol.on_game_end()
    connection.protocol.send_chat(
        'Game has been reset by %s' % connection.name,
        irc=True)


@command(admin_only=True)
def lock(connection, value):
    """
    Make a specified team no longer joinable until it's unlocked
    /lock <blue|green|spectator>
    New players will be placed in the spectator team even if it's locked
    """
    team = get_team(connection, value)
    team.locked = True
    connection.protocol.send_chat('%s team is now locked' % team.name)
    connection.protocol.irc_say('* %s locked %s team' % (connection.name,
                                                         team.name))


@command(admin_only=True)
def unlock(connection, value):
    """
    Unlock a team
    /unlock <blue|green|spectator>
    """
    team = get_team(connection, value)
    team.locked = False
    connection.protocol.send_chat('%s team is now unlocked' % team.name)
    connection.protocol.irc_say('* %s unlocked %s team' % (connection.name,
                                                           team.name))


@command(admin_only=True)
def switch(connection, player=None, team=None):
    """
    Switch teams either for yourself or for a given player
    /switch [player]
    """
    protocol = connection.protocol
    if player is not None:
        player = get_player(protocol, player)
    elif connection in protocol.players:
        player = connection
    else:
        raise ValueError()
    if player.team.spectator:
        player.send_chat(
            "The switch command can't be used on a spectating player.")
        return
    if team is None:
        new_team = player.team.other
    else:
        new_team = get_team(connection, team)
    if player.invisible:
        old_team = player.team
        player.team = new_team
        player.on_team_changed(old_team)
        player.spawn(player.world_object.position.get())
        player.send_chat('Switched to %s team' % player.team.name)
        if connection is not player and connection in protocol.players:
            connection.send_chat('Switched %s to %s team' % (player.name,
                                                             player.team.name))
        protocol.irc_say('* %s silently switched teams' % player.name)
    else:
        player.respawn_time = protocol.respawn_time
        player.set_team(new_team)
        protocol.send_chat('%s switched teams' % player.name, irc=True)


@command('setbalance', admin_only=True)
def set_balance(connection, value):
    """
    Turn automatic balancing on or off
    /setbalance <on|off>
    """
    should_balance = get_truthy(value)
    if should_balance is None:
        raise CommandError()

    protocol = connection.protocol
    protocol.balanced_teams = should_balance

    if should_balance:
        protocol.send_chat('now balancing teams')
        connection.protocol.irc_say(
            '* %s turned on balanced teams' % connection.name)
    else:
        protocol.send_chat('now no longer balancing teams')
        connection.protocol.irc_say(
            '* %s turned off balanced teams' % connection.name)


@command('togglebuild', 'tb', admin_only=True)
def toggle_build(connection, player=None):
    """
    Toggle building for everyone in the server or for a given player
    /togglebuild [player]
    """
    if player is not None:
        player = get_player(connection.protocol, player)
        value = not player.building
        player.building = value
        msg = '%s can build again' if value else '%s is disabled from building'
        connection.protocol.send_chat(msg % player.name)
        connection.protocol.irc_say('* %s %s building for %s' %
                                    (connection.name,
                                     ['disabled', 'enabled'][int(value)],
                                     player.name))
    else:
        value = not connection.protocol.building
        connection.protocol.building = value
        on_off = ['OFF', 'ON'][int(value)]
        connection.protocol.send_chat('Building has been toggled %s!' % on_off)
        connection.protocol.irc_say(
            '* %s toggled building %s' % (connection.name,
                                          on_off))


@command('togglekill', 'tk', admin_only=True)
def toggle_kill(connection, player=None):
    """
    Toggle killing for everyone in the server or for a given player
    /togglekill [player]
    """
    if player is not None:
        player = get_player(connection.protocol, player)
        value = not player.killing
        player.killing = value
        msg = '%s can kill again' if value else '%s is disabled from killing'
        connection.protocol.send_chat(msg % player.name)
        connection.protocol.irc_say('* %s %s killing for %s' %
                                    (connection.name,
                                     ['disabled', 'enabled'][int(value)], player.name))
    else:
        value = not connection.protocol.killing
        connection.protocol.killing = value
        on_off = ['OFF', 'ON'][int(value)]
        connection.protocol.send_chat('Killing has been toggled %s!' % on_off)
        connection.protocol.irc_say(
            '* %s toggled killing %s' % (connection.name,
                                         on_off))


@command('toggleteamkill', 'ttk', admin_only=True)
def toggle_teamkill(connection):
    """
    Toggle friendly fire
    /toggleteamkill
    """
    value = not connection.protocol.friendly_fire
    connection.protocol.friendly_fire = value
    on_off = ['OFF', 'ON'][int(value)]
    connection.protocol.send_chat(
        'Friendly fire has been toggled %s!' % on_off)
    connection.protocol.irc_say('* %s toggled friendly fire %s' % (
        connection.name, on_off))


@command('globalchat', admin_only=True)
def global_chat(connection, value=None):
    """
    Enable or disable global chat
    /globalchat [on|off]
    Toggles if no arguments are given
    """
    enabled = get_truthy(value)
    if enabled is True:
        connection.protocol.global_chat = True
    elif enabled is False:
        connection.protocol.global_chat = False
    else:
        connection.protocol.global_chat = not connection.protocol.global_chat

    connection.protocol.send_chat(
        'Global chat %s' % (
            'enabled' if connection.protocol.global_chat else 'disabled'),
        irc=True)


@command('timelimit', admin_only=True)
def set_time_limit(connection, value):
    """
    Set this game time limit
    /timelimit <duration>
    """
    value = float(value)
    protocol = connection.protocol
    protocol.set_time_limit(value)
    protocol.send_chat('Time limit set to %s' % value, irc=True)


@command(admin_only=True)
def fog(connection, *args):
    """
    Set the fog color
    /fog red green blue (all values 0-255)
    /fog #aabbcc        (hex representation of rgb)
    /fog #abc           (short hex representation of rgb)
    """
    if(len(args) == 3):
        r = int(args[0])
        g = int(args[1])
        b = int(args[2])
    elif(len(args) == 1 and args[0][0] == '#'):
        hex_code = args[0][1:]

        if (len(hex_code) != 3) and (len(hex_code) != 6):
            raise ValueError()

        if len(hex_code) == 3: # it's a short hex code, turn it into a full one
            hex_code = (hex_code[0]*2) + (hex_code[1]*2) + (hex_code[2]*2)

        valid_characters = re.compile('[a-fA-F0-9]')
        for char in hex_code:
            if valid_characters.match(char) == None:
                raise ValueError()

        r = int(hex_code[0:2], base=16)
        g = int(hex_code[2:4], base=16)
        b = int(hex_code[4:6], base=16)
    else:
        raise ValueError()

    connection.protocol.set_fog_color((r, g, b))
    # TODO: Warn when the fog was set to the same color as before
    return 'Fog color changed successfully'
