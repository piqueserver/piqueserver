from pyspades.server import player_data, chat_message
from pyspades.server import create_player, position_data, kill_action
from commands import add, rights, admin, name, get_player
import commands

@admin
def god(connection, value = None):
    irc = connection not in connection.protocol.players
    if not irc and value is None and connection.spectator:
        return "You're spectating"
    elif value is not None:
        player = get_player(connection.protocol, value)
        if player.spectator:
            return '%s is a spectator.' % player.name
    return commands.god(connection, value)

@admin
def invisible(connection, value = None):
    irc = connection not in connection.protocol.players
    if not irc and value is None and connection.spectator:
        return "You're spectating"
    elif value is not None:
        player = get_player(connection.protocol, value)
        if player.spectator:
            return '%s is a spectator.' % player.name
    return commands.invisible(connection, value)

@name('togglekill')
@admin
def toggle_kill(connection, value = None):
    if value is not None:
        player = get_player(connection.protocol, value)
        if player.spectator:
            return '%s is a spectator.' % player.name
    return commands.toggle_kill(connection, value)

@name('togglebuild')
@admin
def toggle_build(connection, value = None):
    if value is not None:
        player = get_player(connection.protocol, value)
        if player.spectator:
            return '%s is a spectator.' % player.name
    return commands.toggle_build(connection, value)

def pm(connection, value, *arg):
    irc = connection not in connection.protocol.players
    if not irc and connection.spectator:
        return "You're spectating."
    return commands.pm(connection, value, *arg)

def spectators(connection):
    names = [p.name for p in connection.protocol.players.values()
        if p.spectator]
    if len(names):
        return '%s %s spectating.' % (', '.join(names), 'is' if len(names) == 1
            else 'are')
    else:
        return 'There are no spectators.'

@admin
def spectator(connection, value):
    player = get_player(connection.protocol, value)
    player.start_spectating()
    player.send_chat("You're now a spectator.")
    connection.protocol.irc_say('* %s is now a spectator' % player.name)
    if connection is not player and connection not in connection.protocol.players:
        return '%s is now a spectator.' % player.name

for func in (god, invisible, toggle_build, toggle_kill, no_follow, pm,
    spectators, spectator):
    add(func)

rights['spectator'] = ['teleport', 'tp', 'goto']

def apply_script(protocol, connection, config):
    class SpectatorConnection(connection):
        spectator = False
        
        def start_spectating(self):
            self.spectator = True
            self.filter_visibility_data = True
            self.god = True
            self.invisible = True
            self.fly = True
            self.killing = False
            self.building = False
            self.drop_flag()
            self.leave_squad()
            self.respawn_time = self.protocol.respawn_time
            player_data.player_left = self.player_id
            for player in self.protocol.connections.values():
                if player is self:
                    continue
                if not player.spectator:
                    player.send_contained(player_data)
                else:
                    pos = player.team.get_random_location(True)
                    x, y, z = pos
                    create_player.player_id = player.player_id
                    create_player.name = player.name
                    create_player.x = x
                    create_player.y = y - 128
                    create_player.weapon = player.weapon
                    position_data.set((0, 0, 0), player.player_id)
                    kill_action.not_fall = True
                    kill_action.player1 = kill_action.player2 = player.player_id
                    self.send_contained(create_player)
                    self.send_contained(position_data)
                    self.send_contained(kill_action)
                    position_data.player_id = self.player_id
                    kill_action.player1 = kill_action.player2 = self.player_id
                    player.send_contained(position_data)
                    player.send_contained(kill_action)
        
        def on_join(self):
            for player in self.protocol.connections.values():
                if player.spectator:
                    player_data.player_left = player.player_id
                    self.send_contained(player_data)
            connection.on_join(self)
        
        def on_user_login(self, user_type):
            if user_type != 'spectator':
                return connection.on_user_login(self, user_type)
            self.start_spectating()
            return connection.on_user_login(self, user_type)
        
        def on_color_set_attempt(self, color):
            if self.spectator:
                return False
            return connection.on_color_set_attempt(self, color)
        
        def on_chat(self, value, global_message):
            if not self.spectator:
                return connection.on_chat(self, value, global_message)
            chat_message.global_message = global_message
            chat_message.value = value
            chat_message.player_id = self.player_id
            for player in self.protocol.connections.values():
                if player is not self and player.spectator:
                    player.send_contained(chat_message)
            message = '(%s) %s' % (self.name, value)
            self.protocol.irc_say(message)
            print message.encode('ascii', 'replace')
            return False

        def join_squad(self, squad, squad_pref):
            if self.spectator:
                return "You can't join a squad while spectating!"
            else:
                return connection.join_squad(squad, squad_pref)
        
    return protocol, SpectatorConnection
