from pyspades.server import player_data, chat_message
from pyspades.server import create_player, position_data, kill_action
from commands import add, rights

def spectators(connection):
    names = [p.name for p in connection.protocol.players.values()
        if p.spectator]
    if len(names):
        return '%s %s spectating.' % (', '.join(names), 'is' if len(names) == 1
            else 'are')
    else:
        return 'There are no spectators.'

add(spectators)

rights['spectator'] = ['tp', 'goto']

def apply_script(protocol, connection, config):
    class SpectatorConnection(connection):
        spectator = False
        
        def on_user_login(self, user_type):
            if user_type != 'spectator':
                return connection.on_user_login(self, user_type)
            self.spectator = True
            self.filter_visibility_data = True
            self.god = True
            self.invisible = True
            self.killing = False
            self.building = False
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
            return connection.on_user_login(self, user_type)
        
        def on_chat(self, value, global_message):
            if not self.spectator:
                return connection.on_chat(self, value, global_message)
            chat_message.global_message = global_message
            chat_message.value = value
            chat_message.player_id = self.player_id
            for player in self.protocol.connections.values():
                if player.spectator:
                    player.send_contained(chat_message)
            self.protocol.irc_say('(%s) %s' % (self.name, value))
            print message.encode('ascii', 'replace')
            return False
        
    return protocol, SpectatorConnection