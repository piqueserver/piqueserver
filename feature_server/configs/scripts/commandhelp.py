"""
Command helper.
Copyright (c) 2013 learn_more
See the file license.txt or http://opensource.org/licenses/MIT for copying permission.

Lists all commands available to you (permission based).
"""

from commands import add, admin, commands as cmdlist, aliases as aliaslist
import fnmatch

def commands(connection, value = None):
	names = []
	for command in cmdlist:
		command_func = cmdlist[command]
		if (hasattr(command_func, 'user_types') and command not in connection.rights):
			continue
		include = False
		if (value is None or fnmatch.fnmatch(command, value)):
			include = True
		aliases = []
		for a in aliaslist:
			if aliaslist[a] == command:
				if (value is None or fnmatch.fnmatch(a, value)):
					include = True
				aliases.append(a)
		cmd = command if len(aliases) == 0 else ('%s (%s)' % (command, ', '.join(aliases)))
		if include:
			names.append(cmd)
	return 'Commands: %s' % (', '.join(names))

add(commands)

def apply_script(protocol, connection, config):
	return protocol, connection
