from map import Map
from commands import add, admin
from pyspades.common import coordinates
from pyspades.serverloaders import BlockAction, SetColor
from twisted.internet import reactor
from pyspades.constants import *
import time
import operator

@admin
def rollmap(connection, filename = None, value = None):
    start_x, start_y, end_x, end_y = 0, 0, 512, 512
    if value is not None:
        start_x, start_y = coordinates(value)
        end_x, end_y = start_x + 64, start_y + 64
    return connection.protocol.start_rollback(connection, filename,
        start_x, start_y, end_x, end_y)

@admin
def rollback(connection, value = None):
    return rollmap(connection, value = value)

@admin
def rollbackcancel(connection):
    return connection.protocol.cancel_rollback(connection)

for func in (rollmap, rollback, rollbackcancel):
    add(func)

def apply_script(protocol, connection, config):
    rollback_on_game_end = config.get('rollback_on_game_end', False)
    rollback_map = Map(config['map']).data
    
    class RollbackConnection(connection):
        def on_color_set(self, (r, g, b)):
            if (self.protocol.rollback_in_progress and
                self.protocol.rollbacking_player is self):
                return False
            
    class RollbackProtocol(protocol):
        rollback_in_progress = False
        rollback_max_rows = 10 # per 'cycle', intended to cap cpu usage
        rollback_max_packets = 180 # per 'cycle' cap for (unique packets * players)
        rollback_max_unique_packets = 12 # per 'cycle', each block op is at least 1
        rollback_time_between_cycles = 0.06
        rollback_time_between_progress_updates = 10.0
        rollbacking_player = None
        rollback_start_time = None
        rollback_last_chat = None
        rollback_rows = None
        rollback_total_rows = None
        
        # rollback
        
        def start_rollback(self, connection, filename,
                           start_x, start_y, end_x, end_y, z_offset):
            if self.rollback_in_progress:
                return 'Rollback in progress.'
            map = rollback_map if filename is None else Map(filename).data
            message = ('%s commenced a rollback...' %
                (connection.name if connection is not None else 'Map'))
            if connection is None or connection not in self.players:
                for player in self.players.values():
                    connection = player
                    if player.admin:
                        break
            if connection is None:
                return ('There must be at least one player in the server '
                    'to perform a rollback')
            self.send_chat(message, irc = True)
            packet_generator = self.create_rollback_generator(connection,
                self.map, map, start_x, start_y, end_x, end_y, z_offset)
            self.rollbacking_player = connection
            self.rollback_in_progress = True
            self.rollback_start_time = time.time()
            self.rollback_last_chat = self.rollback_start_time
            self.rollback_rows = 0
            self.rollback_total_rows = end_x - start_x
            self.rollback_cycle(packet_generator)
        
        def cancel_rollback(self, connection):
            if not self.rollback_in_progress:
                return 'No rollback in progress.'
            self.end_rollback('Cancelled by %s' % connection.name)
        
        def end_rollback(self, result):
            self.rollback_in_progress = False
            self.update_entities()
            self.send_chat('Rollback ended. %s' % result, irc = True)
        
        def rollback_cycle(self, packet_generator):
            if not self.rollback_in_progress:
                return
            try:
                sent_unique = sent_total = rows = 0
                while (True):
                    if rows > self.rollback_max_rows:
                        break
                    if sent_unique > self.rollback_max_unique_packets:
                        break
                    if sent_total > self.rollback_max_packets:
                        break
                    
                    sent = packet_generator.next()
                    sent_unique += sent
                    sent_total += sent * len(self.connections)
                    rows += (sent == 0)
                self.rollback_rows += rows
                if (time.time() - self.rollback_last_chat >
                    self.rollback_time_between_progress_updates):
                    self.rollback_last_chat = time.time()
                    progress = int(float(self.rollback_rows) /
                        self.rollback_total_rows * 100.0)
                    if progress < 100:
                        self.send_chat('Rollback progress %s%%' % progress)
                    else
                        self.send_chat('Rollback doing color pass...')
            except (StopIteration):
                self.end_rollback('Time taken: %.2fs' % 
                    float(time.time() - self.rollback_start_time))
                return
            reactor.callLater(self.rollback_time_between_cycles,
                self.rollback_cycle, packet_generator)
        
        def create_rollback_generator(self, connection, old, new,
                                      start_x, start_y, end_x, end_y):
            surface = {}
            block_action = BlockAction()
            block_action.player_id = connection.player_id
            set_color = SetColor()
            set_color.value = 0x000000
            set_color.player_id = connection.player_id
            self.send_contained(set_color, save = True)
            
            for x in xrange(start_x, end_x):
                block_action.x = x
                for y in xrange(start_y, end_y):
                    block_action.y = y
                    for z in xrange(64):
                        block_action.z = z
                        block_action.value = None
                        old_solid = old.get_solid(x, y, z)
                        new_solid = new.get_solid(x, y, z)
                        if old_solid and not new_solid:
                            block_action.value = DESTROY_BLOCK
                            old.remove_point_unsafe(x, y, z)
                        elif new_solid:
                            new_color = new.get_color(x, y, z)
                            new_is_surface = (new_color != 0)
                            if not old_solid and new_is_surface:
                                surface[(x, y, z)] = new_color
                            elif not old_solid and not new_is_surface:
                                block_action.value = BUILD_BLOCK
                                old.set_point_unsafe_int(x, y, z, 0)
                            elif old_solid and new_is_surface:
                                old_color = old.get_color(x, y, z)
                                if old_color != new_color:
                                    surface[(x, y, z)] = new_color
                                    block_action.value = DESTROY_BLOCK
                                    old.remove_point_unsafe(x, y, z)
                        if block_action.value is not None:
                            self.send_contained(block_action, save = True)
                            yield 1
                yield 0
            last_color = None
            block_action.value = BUILD_BLOCK
            for pos, color in sorted(surface.iteritems(),
                key = operator.itemgetter(1)):
                packets_sent = 0
                if color != last_color:
                    set_color.value = color & 0xFFFFFF
                    self.send_contained(set_color, sender = connection,
                        save = True)
                    packets_sent += 1
                    last_color = color
                connection.send_contained(set_color)
                x, y, z = pos
                old.set_point_unsafe_int(x, y, z, color)
                block_action.x = x
                block_action.y = y
                block_action.z = z
                self.send_contained(block_action, save = True)
                packets_sent += 1
                yield packets_sent
        
        def on_game_end(self, player):
            if rollback_on_game_end:
                self.start_rollback(None, None, 0, 0, 512, 512, 0)
        
    return RollbackProtocol, RollbackConnection