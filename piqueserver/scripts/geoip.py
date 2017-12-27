from __future__ import print_function, unicode_literals
import os
from piqueserver import cfg
from piqueserver.commands import command, get_player

# optional commands
try:
    import pygeoip
    database = pygeoip.GeoIP(os.path.join(
        cfg.config_dir, 'data/GeoLiteCity.dat'))
except ImportError:
    print("('/from' command disabled. Please install pygeoip to enable.)")
except (IOError, OSError):
    print("('/from' command disabled due to missing GeoIP database. Run 'piqueserver --update-geoip' to install.)")
finally:
    @command('from')
    def where_from(connection, value=None):
        if value is None:
            if connection not in connection.protocol.players:
                raise ValueError()
            player = connection
        else:
            player = get_player(connection.protocol, value)
        record = database.record_by_addr(player.address[0])
        if record is None:
            return 'Player location could not be determined.'
        items = []
        for entry in ('country_name', 'city', 'region_name'):
            # sometimes, the record entries are numbers or nonexistent
            try:
                value = record[entry]
                int(value)
                # if this raises a ValueError, it's not a number
                continue
            except KeyError:
                continue
            except ValueError:
                pass

            if not isinstance(value, str):
                continue
            items.append(value)
        return '%s is from %s' % (player.name, ', '.join(items))

def apply_script(protocol, connection, config):
    return protocol, connection
