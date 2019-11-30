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

import sys
from os import path

try:
    from twisted.cred import portal, checkers
    from twisted.conch import manhole, manhole_ssh
    from twisted.conch.ssh import keys
except ImportError as e:
    print("ERROR: piqueserver was not installed with the [ssh] option")
    print("but SSH was enabled in the settings")
    print(e)
    sys.exit(1)

from piqueserver.config import config


def create_remote_factory(namespace, users):
    realm = manhole_ssh.TerminalRealm()

    def create_remote_protocol(_):
        return manhole.ColoredManhole(namespace)

    realm.chainedProtocolFactory.protocolFactory = create_remote_protocol
    p = portal.Portal(realm)

    users = {key: value.encode() for key, value in users.items()}

    p.registerChecker(
        checkers.InMemoryUsernamePasswordDatabaseDontUse(**users))
    f = manhole_ssh.ConchFactory(p)
    ssh_key_base_path = path.join(config.config_dir, "ssh-keys")
    ssh_pubkey_path = path.join(ssh_key_base_path,
                                "ssh_host_rsa_key.pub")
    ssh_privkey_path = path.join(ssh_key_base_path,
                                 "ssh_host_rsa_key")
    try:
        f.publicKeys[b"ssh-rsa"] = keys.Key.fromFile(ssh_pubkey_path)
        f.privateKeys[b"ssh-rsa"] = keys.Key.fromFile(ssh_privkey_path)
    except FileNotFoundError:
        print("ERROR: You don't have any keys in the host key location")
        print("Generate one with:")
        print("  mkdir {}".format(ssh_key_base_path))
        print("  ssh-keygen -f {} -t rsa".format(ssh_privkey_path))
        print("make sure to specify no password")
        sys.exit(1)
    return f


ssh_config = config.section("ssh")
class RemoteConsole:

    def __init__(self, server):
        users = ssh_config.option("users", {})
        port = ssh_config.option("port", 38827)
        factory = create_remote_factory(locals(), users.get())
        server.listenTCP(port.get(), factory)
