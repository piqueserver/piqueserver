Architecture
============

Overview
--------

The piccolo codebase is made up out of two main modules: `pyspades` and
`piccolo`. The `piccolo` module used to be named ``feature_server``.
The original developers wanted to make the pyspades a generic AoS protocol and
server implementation which the ``feature_server`` module then subclassed and
specialized.

However, the unclear division and two locations quickly lead to a large mess,
and it is currently not possible to know for certain which module exactly
certains certain functionality. In general, this is the rule of thumb:

 * `pyspades`: Anything that involves sending and recieving of packets and
   acting on those, keeping game state.

 * `piccolo`: Anything player-facing, for example commands,
   configuration, etc.

Note however the numerous exceptions to this. For example, parts of the command
logic are in `pyspades`, while a lot of server validation logic is in
`piccolo`

Classes
-------

There are currently two classes which contain the bulk of the logic.
``Connection``, and ``Protocol``. The ``Connection`` class does not actually
represent a connection, it represents a player connected to the server and is
contained in the ``player.py`` file in the relevant module. The ``Protocol``
object is similar, but represents the server and is in the ``server.py`` file.

Many classes and modules have descriptions you can view in this
documentations or in the files, but there is one more k
