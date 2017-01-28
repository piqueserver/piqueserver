# feature_server/cfg.py
#
#   This file is licensed under the GNU General Public License version 3.
# In accordance to the license, there are instructions for obtaining the
# original source code. Furthermore, the changes made to this file can
# be seem by using diff tools and/or git-compatible software.
#
#   The license full text can be found in the "LICENSE" file, at the root
# of this repository.
#
# (C)2017 piqueserver contributors
#

# to have global configuration variables
# similar to
# http://effbot.org/pyfaq/how-do-i-share-global-variables-across-modules.htm

import os
import sys

server_version = '%s - %s' % (sys.platform, '0.0.1a')
config = {}
pkg_name = "piqueserver"
config_file = 'config.json'

prefix = os.environ.get('XDG_CONFIG_DIR', '~/.config')
config_path = prefix + "/piqueserver"
config_dir = os.path.expanduser(config_path)
