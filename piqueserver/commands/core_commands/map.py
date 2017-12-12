from piqueserver.map import check_rotation, MapNotFound
from ..command import command, parse_maps


@command()
def mapname(connection):
    return 'Current map: ' + connection.protocol.map_info.name


@command('showrotation')
def show_rotation(connection):
    return ", ".join(connection.protocol.get_map_rotation())


@command('map', admin_only=True)
def change_planned_map(connection, *pre_maps):
    """
    set the next map
    /map <mapname>
    """
    name = connection.name
    protocol = connection.protocol

    # parse seed numbering
    maps, _map_list = parse_maps(pre_maps)
    if not maps:
        return 'Invalid map name'

    planned_map = maps[0]
    try:
        protocol.planned_map = check_rotation([planned_map])[0]
        protocol.send_chat('%s changed next map to %s' %
                           (name, planned_map), irc=True)
    except MapNotFound:
        return 'Map %s not found' % (maps[0])


@command('rotation', admin_only=True)
def change_rotation(connection, *pre_maps):
    name = connection.name
    protocol = connection.protocol

    maps, map_list = parse_maps(pre_maps)

    if len(maps) == 0:
        return 'Usage: /rotation <map1> <map2> <map3>...'
    ret = protocol.set_map_rotation(maps, False)
    if not ret:
        return 'Invalid map in map rotation (%s)' % ret.map
    protocol.send_chat("%s changed map rotation to %s." %
                       (name, map_list), irc=True)


@command('rotationadd', admin_only=True)
def rotation_add(connection, *pre_maps):
    name = connection.name
    protocol = connection.protocol

    new_maps, map_list = parse_maps(pre_maps)

    maps = connection.protocol.get_map_rotation()
    map_list = ", ".join(maps) + map_list
    maps.extend(new_maps)

    ret = protocol.set_map_rotation(maps, False)
    if not ret:
        return 'Invalid map in map rotation (%s)' % ret.map
    protocol.send_chat("%s added %s to map rotation." %
                       (name, " ".join(pre_maps)), irc=True)


@command('revertrotation', admin_only=True)
def revert_rotation(connection):
    protocol = connection.protocol
    name = connection.name
    maps = protocol.config['maps']
    protocol.set_map_rotation(maps, False)
    protocol.irc_say("* %s reverted map rotation to %s" % (name, maps))


@command('advancemap', admin_only=True)
def advance(connection):
    connection.protocol.advance_rotation('Map advance forced.')
