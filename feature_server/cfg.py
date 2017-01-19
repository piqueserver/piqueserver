
# to have global configuration variables
# similar to http://effbot.org/pyfaq/how-do-i-share-global-variables-across-modules.htm

import os

config = {}
pkg_name = "piqueserver"
config_file = 'config.json'

prefix = os.environ.get('XDG_CONFIG_DIR', '~/.config')
config_path = prefix + "/piqueserver"
config_dir = os.path.expanduser(config_path)
