from piqueserver.map import check_rotation, MapNotFound
from piqueserver.commands import command, parse_maps


@command()
def mapname(connection):
    """
    Tell you what's the name of the current map
    /mapname
    """
    return 'Current map: ' + connection.protocol.map_info.name


@command('showrotation')
def show_rotation(connection):
    """
    Tell you the current map rotation
    /showrotation
    """
    return ", ".join(connection.protocol.get_map_rotation())


@command('map', admin_only=True)
def change_planned_map(connection, *pre_maps):
    """
    Set the next map to be loaded after current game ends and inform everyone of it
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
    """
    Change the current map rotation and informs everyone on the server of it
    /rotation <map1> ... <mapN>
    """
    name = connection.name
    protocol = connection.protocol

    maps, map_list = parse_maps(pre_maps)

    if len(maps) == 0:
        return 'Usage: /rotation <map1> <map2> <map3> ...'
    try:
        protocol.set_map_rotation(maps)
    except MapNotFound as e:
        return 'Invalid map in map rotation (%s)' % e.map
    protocol.send_chat("%s changed map rotation to %s." %
                       (name, map_list), irc=True)


@command('rotationadd', admin_only=True)
def rotation_add(connection, *pre_maps):
    """
    Append a given map to the current map rotation and informs everyone on the server of it
    /rotationadd <map>
    """
    name = connection.name

    protocol = connection.protocol

    new_maps, map_list = parse_maps(pre_maps)

    maps = connection.protocol.get_map_rotation()
    map_list = ", ".join(maps) + map_list
    maps.extend(new_maps)

    try:
        protocol.set_map_rotation(maps)
    except MapNotFound as e:
        return 'Invalid map in map rotation (%s)' % e.map
    protocol.send_chat("%s added %s to map rotation." %
                       (name, " ".join(pre_maps)), irc=True)


@command('revertrotation', admin_only=True)
def revert_rotation(connection):
    """
    Invert the current map rotation
    /revertrotation
    """
    protocol = connection.protocol
    name = connection.name
    maps = protocol.config['maps']
    protocol.set_map_rotation(maps)
    protocol.irc_say("* %s reverted map rotation to %s" % (name, maps))


@command('advancemap', admin_only=True)
def advance(connection):
    """
    Force the next map to be immediately loaded instead of waiting for the time limit to end
    /advancemap
    """
    connection.protocol.advance_rotation('Map advance forced.')
