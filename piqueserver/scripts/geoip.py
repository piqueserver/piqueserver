'''
Gets a player's location info using a geoip database.
Location is formatted as a list of regions ordered by hierarchy (i.e. City, Region, Country)

.. note::
  This script depends on `geoip2` package and `piqueserver --update-geoip` needs to be executed after installing the package.

Commands
^^^^^^^^
* ``/from ``         get active player's location
* ``/from <player>`` get player's location info

.. codeauthor:: ?
'''

import os
from piqueserver.commands import command, restrict, get_player
from piqueserver.config import config

# optional commands
try:
    import geoip2.database
    import geoip2.errors
    database = geoip2.database.Reader(os.path.join(
        config.config_dir, 'data/GeoLite2-City/GeoLite2-City.mmdb'))
except ImportError:
    print("('/from' command disabled. Please install geoip2 to enable.)")
except (IOError, OSError):
    print(
        "('/from' command disabled due to missing GeoIP database. Run 'piqueserver --update-geoip' to install.)"
    )
finally:

    @restrict('admin')
    @command('from')
    def where_from(connection, value=None):
        # Get player IP address
        if value is None:
            if connection not in connection.protocol.players:
                raise ValueError()
            player = connection
        else:
            player = get_player(connection.protocol, value)

        # Query database
        try:
            record = database.city(player.address[0])
        except geoip2.errors.GeoIP2Error:
            return 'Player location could not be determined.'

        # Extract info
        raw_items = []
        raw_items.append(record.country)
        raw_items.extend(record.subdivisions)
        raw_items.append(record.city)

        items = (raw_item.name for raw_item in reversed(raw_items))

        return '%s is from %s (%s)' % (player.name, ', '.join(items),
                                       record.country.iso_code)


def apply_script(protocol, connection, config):
    return protocol, connection
