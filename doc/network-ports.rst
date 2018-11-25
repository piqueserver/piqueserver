Network ports
=============

Piqueserver needs a few firewall ports open for various things.

The game server
---------------

The port the actual gameplay is on - this needs to be allowed at the bare minimum for players to connect to the game.

- Default: 32887
- Config variable: ``port``
- Protocol: udp

Status server
-------------

This is for the webpage which displays info about the server.

- Default: 32886
- Config variable: ``status_server.port``
- Protocol: tcp

Banpublish
----------
For making the banlist public.

- Default: 32885
- Config variable: ``banpublish.port``
- Protocol: tcp

SSH
---
Some ssh server for remotely connecting to the server.

- Default: 32887
- Config variable: ``ssh.port``
- Protocol: tcp
