from pyspades.collision import distance_3d_vector
from pyspades.common import prettify_timespan
from commands import add, admin, name, get_player
from twisted.internet import reactor

@name('griefcheck')
@admin
def grief_check(connection, player, time = None):
    player = get_player(connection.protocol, player)
    color = connection not in connection.protocol.players and connection.colors
    minutes = float(time or 2)
    if minutes < 0.0:
        raise ValueError()
    time = reactor.seconds() - minutes * 60.0
    blocks_removed = player.blocks_removed or []
    blocks = [b[1] for b in blocks_removed if b[0] >= time]
    player_name = player.name
    if color:
        player_name = (('\x0303' if player.team.id else '\x0302') +
            player_name + '\x0f')
    message = '%s removed %s block%s in the last ' % (player_name,
        len(blocks) or 'no', '' if len(blocks) == 1 else 's')
    if minutes == 1.0:
        message += 'minute.'
    else:
        message += '%s minutes.' % ('%f' % minutes).rstrip('0').rstrip('.')
    if len(blocks):
        infos = set(blocks)
        infos.discard(None)
        if color:
            names = [('\x0303' if team else '\x0302') + name for name, team in
                infos]
        else:
            names = set([name for name, team in infos])
        if len(names) > 0:
            message += (' Some of them were placed by ' +
                ('\x0f, ' if color else ', ').join(names))
            message += '\x0f.' if color else '.'
        else:
            message += ' All of them were map blocks.'
        last = blocks_removed[-1]
        message += ' Last one was destroyed %s ago' % (
            prettify_timespan(reactor.seconds() - last[0], get_seconds = True))
        whom = last[1]
        if whom is None and len(names) > 0:
            message += ', and was part of the map'
        elif whom is not None:
            name, team = whom
            if color:
                name = ('\x0303' if team else '\x0302') + name + '\x0f'
            message += ', and belonged to %s' % name
        message += '.'
    if connection.protocol.votekick_player is player:
        dist = distance_3d_vector(player.world_object.position,
            connection.protocol.voting_player.world_object.position)
        message += ' %s is %d tiles away from the votekick starter.' % (
            player_name, int(dist))
    return message

add(grief_check)

def apply_script(protocol, connection, config):
    class BlockInfoConnection(connection):
        blocks_removed = None
        
        def on_block_build(self, x, y, z):
            if self.protocol.block_info is None:
                self.protocol.block_info = {}
            self.protocol.block_info[(x, y, z)] = (self.name, self.team.id)
            connection.on_block_build(self, x, y, z)
        
        def on_block_removed(self, x, y, z):
            if self.protocol.block_info is None:
                self.protocol.block_info = {}
            if self.blocks_removed is None:
                self.blocks_removed = []
            pos = (x, y, z)
            info = (reactor.seconds(),
                self.protocol.block_info.pop(pos, None))
            self.blocks_removed.append(info)
            connection.on_block_removed(self, x, y, z)
    
    class BlockInfoProtocol(protocol):
        block_info = None
    
    return BlockInfoProtocol, BlockInfoConnection