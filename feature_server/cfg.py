
# to have global configuration variables
# similar to http://effbot.org/pyfaq/how-do-i-share-global-variables-across-modules.htm

import os
import sys

server_version = '%s - %s' % (sys.platform, '0.0.1a')
config = {}
pkg_name = "piqueserver"
config_file = 'config.json'

prefix = os.environ.get('XDG_CONFIG_HOME', '~/.config')
config_path = prefix + "/piqueserver"
config_dir = os.path.expanduser(config_path)
