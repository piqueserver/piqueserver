from commands import add, admin, name, get_player
from twisted.internet import reactor

@name('griefcheck')
@admin
def grief_check(connection, player, time = None):
    player = get_player(connection.protocol, player)
    minutes = float(time or 2)
    if minutes < 0.0:
        raise ValueError()
    time = reactor.seconds() - minutes * 60.0
    blocks = [b[1] for b in player.blocks_removed if b[0] >= time]
    message = '%s removed %s block%s in the last ' % (player.name,
        len(blocks) or 'no', '' if len(blocks) == 1 else 's')
    if minutes == 1.0:
        message += 'minute.'
    else:
        message += '%s minutes.' % ('%f' % minutes).rstrip('0').rstrip('.')
    if len(blocks):
        names = set(blocks)
        names.discard(None)
        if len(names) > 0:
            message += ' Some of them were placed by %s.' % (', '.join(names))
        else:
            message += ' All of them were map blocks.'
        last = player.blocks_removed[-1]
        message += ' Last one was destroyed %s seconds ago' % (
            int(reactor.seconds() - last[0]))
        whom = last[1]
        if whom is None and len(names) > 0:
            message += ', and was part of the map'
        elif whom is not None:
            message += ', and belonged to %s' % whom
        message += '.'
    if connection.protocol.votekick_player is player:
        dist = distance_3d_vector(player.world_object.position,
            connection.protocol.voting_player.world_object.position)
        message += ' %s is %d tiles away from the votekick starter.' % (
            player.name, int(dist))
    return message

add(grief_check)

def apply_script(protocol, connection, config):
    class BlockInfoConnection(connection):
        blocks_removed = None
        
        def on_block_build(self, x, y, z):
            if self.protocol.block_info is None:
                self.protocol.block_info = {}
            self.protocol.block_info[(x, y, z)] = self.name
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