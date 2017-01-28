# feature_server/ssh.py
#
#   This file is licensed under the GNU General Public License version 3.
# In accordance to the license, there are instructions for obtaining the
# original source code. Furthermore, the changes made to this file can
# be seem by using diff tools and/or git-compatible software.
#
#   The license full text can be found in the "LICENSE" file, at the root
# of this repository. The original PySpades code can be found in this URL:
# https://github.com/infogulch/pyspades/releases/tag/v0.75.01.
#
# The original copyright holders are Mathias Kaerlev and PySpades contributors
#

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
