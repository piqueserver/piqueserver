
# to have global configuration variables
# similar to http://effbot.org/pyfaq/how-do-i-share-global-variables-across-modules.htm

import os

config = {}
config_dir = os.path.join(os.path.expanduser("~"), ".pysnip")
config_file = 'config.json'

