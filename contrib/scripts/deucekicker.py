from commands import add, admin

KICK_DEUCE_ON_JOIN = False
KICK_DEUCE_WHEN_FULL = True
DEUCES_CAN_BUILD = True

@admin
def deuceskick(connection):
    for player in connection.protocol.players.values():
        if player.is_deuce == True:
            player.kick(connection.name + ' kicked all the deuces.')

@admin
def deucesjoin(connection):
    global KICK_DEUCE_ON_JOIN
    KICK_DEUCE_ON_JOIN = not KICK_DEUCE_ON_JOIN
    if KICK_DEUCE_ON_JOIN == True:
        connection.send_chat('Deuces will now be kicked when they join.')
    else:
        connection.send_chat('Deuces will no longer be kicked when they join.')

@admin
def deucesfull(connection):
    global KICK_DEUCE_WHEN_FULL
    KICK_DEUCE_WHEN_FULL = not KICK_DEUCE_WHEN_FULL
    if KICK_DEUCE_WHEN_FULL == True:
        connection.send_chat('Deuces now be kicked when the server is full.')
    else:
        connection.send_chat('Deuces will no longer be kicked when the server is full.')

@admin
def deucesbuild(connection):
    global DEUCES_CAN_BUILD
    DEUCES_CAN_BUILD = not DEUCES_CAN_BUILD
    if DEUCES_CAN_BUILD == True:
        connection.send_chat('Deuces can now build.')
    else:
        connection.send_chat('Deuces can no longer build.')
    for player in connection.protocol.players.values():
        if player.is_deuce == True:
            player.building = DEUCES_CAN_BUILD

add(deuceskick)
add(deucesjoin)
add(deucesfull)
add(deucesbuild)

def apply_script(protocol, connection, config):
    class DeuceKickerConnection(connection):
        def on_join(self):
            self.is_deuce = False
            return connection.on_join(self)

        def on_spawn(self, location):
            if self.name == 'Deuce' + str(self.player_id):
                self.is_deuce = True
                self.building = DEUCES_CAN_BUILD
                if KICK_DEUCE_ON_JOIN == True:
                    self.kick('This server does not allow deuces to join.')
            if KICK_DEUCE_WHEN_FULL == True:
                if len(self.protocol.players.values()) == config.get('max_players'):
                    for player in self.protocol.players.values():
                        if player.is_deuce == True:
                            player.kick('A deuce is automatically kicked when the server is full.')
                            break
            return connection.on_spawn(self, location)
    
    return protocol, DeuceKickerConnection