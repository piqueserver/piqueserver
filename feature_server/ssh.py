# Copyright (c) Mathias Kaerlev 2011-2012.

# This file is part of pyspades.

# pyspades is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# pyspades is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with pyspades.  If not, see <http://www.gnu.org/licenses/>.

from twisted.cred import portal, checkers
from twisted.conch import manhole, manhole_ssh
from twisted.internet import reactor
 
def create_remote_factory(namespace, users):
    realm = manhole_ssh.TerminalRealm()
    def create_remote_protocol(_): 
        return manhole.Manhole(namespace)
    realm.chainedProtocolFactory.protocolFactory = create_remote_protocol
    p = portal.Portal(realm)
    p.registerChecker(
        checkers.InMemoryUsernamePasswordDatabaseDontUse(**users))
    f = manhole_ssh.ConchFactory(p)
    return f

class RemoteConsole(object):
    def __init__(self, server, config):
        users = config.get('users', {})
        factory = create_remote_factory(locals(), users)
        server.listenTCP(config.get('port', 38827), factory)