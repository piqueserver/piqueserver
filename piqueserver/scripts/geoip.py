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
from piqueserver.commands import (command, restrict, get_player, target_player)
from piqueserver.config import config

# optional commands
try:
    import geoip2.database
    import geoip2.errors
    database = geoip2.database.Reader(os.path.join(
        config.config_dir, 'data/GeoLite2-City.mmdb'))
except ImportError:
    print("('/from' command disabled. Please install geoip2 to enable.)")
except (IOError, OSError):
    print(
        "('/from' command disabled due to missing GeoIP database. Run 'piqueserver --update-geoip' to install.)"
    )
finally:

    @command('from', admin_only=True)
    @target_player
    def where_from(connection, player):
        # Query database
        try:
            record = database.city(player.address[0])
        except geoip2.errors.GeoIP2Error:
            return 'Player location could not be determined.'

        # Extract info
        raw_items = (record.city, *reversed(record.subdivisions),
                     record.country)

        items = (raw_item.name for raw_item in raw_items if raw_item.name is not None)

        return '%s is from %s (%s)' % (player.name, ', '.join(items),
                                       record.country.iso_code)


def apply_script(protocol, connection, config):
    return protocol, connection
