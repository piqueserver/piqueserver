Startup and Initialization
==========================

Startup and initialization of the server is currently poorly defined. The
phases are roughly as follows:

Server Initialization
---------------------

Config loading
^^^^^^^^^^^^^^

The config and command-line arguments are loaded first, because they are
required to proceed further.

Module initialization
^^^^^^^^^^^^^^^^^^^^^

The asyncio and twisted reactors are initialized. The files defining the game
logic in ``piqueserver/`` and ``pyspades/`` are imported via
`piqueserver.server`.

Script Loading
^^^^^^^^^^^^^^

The way the script extension system works means that scripts can only be loaded
before the two main classes, ``Connection`` and ``Protocol``, are instantiated.

In this phase, the scripts defined in the config are loaded. This consists of
four sub-phases:

1. All scripts defined under ``scripts`` in the config are loaded, either from
   the config directory, or from `sys.path`.

2. ``apply_script`` is called on all scripts, in the order that they are
   declared in the config.

3. If the game mode is not ``"ctf"`` or ``"tc"`` for which the logic is
   built-in, the game mode is imported as a script.

4. ``apply_script`` is called on the game mode script


Protocol Initialization
^^^^^^^^^^^^^^^^^^^^^^^

The ``Protocol`` class created in the previous step is instantiated, calling
it's ``__init__`` method. This does the following:

- Configure logging
- Read configuration such as map rotation, team names, time limits, win
  conditions
- Load the ban list
- Import and initialize auxilliary functionality like SSH, status server,
  banpublish/bansubscribe, command console.
- Initialize user configuration
- Resolve the filenames of the map rotation
- Create the ``enet.Host`` object, listening on the socket.
- Create the ``Team`` and ``World`` objects.
- Call ``protocol.on_advance(map_name)`` with the name of the map that is about
  to be loaded.
- Schedule future tasks such as the update check, ban vaccum, map loading,
  annoucements, game end, update loop and master server connection.

Config Validation
^^^^^^^^^^^^^^^^^

The configuration is validated for any errors or unused keys.

Event Loop Startup
^^^^^^^^^^^^^^^^^^

Control is passed to the Twisted/AsyncIO event loop, which drives everything
from here on out.

Map Loading
^^^^^^^^^^^

The map is loaded or generated in a background thread. This is done to prevent
connections from timing out on slow hardware.

Once complete, ``protocol.on_map_change``, and ``Team.initialize()`` are
called.

Map Change
----------

Map change is triggered by ``protocol.advance_rotation``

This:

1. Calls ``protocol.on_advance`` with the next map.
2. If a message was specified, print it and wait 10 seconds.
3. Load or generate the next map.
4. Call ``protocol.on_map_leave``
5. Call ``map_info.on_map_leave``
6. Replace the loaded map with the new one.
7. Call ``Team.initialize``

Game Mode Initialization
------------------------

Games are defined by the game mode. They usually represent a period of time
where two teams compete for points and end with one team winning or losing, or
some other condition such as a time limit being hit.

There is currently no hook for when the game starts. However, existing modes
assume it starts with the ``on_map_change`` call.

When a game ends, the game mode will call ``on_game_end`` to notify any other
scripts and possibly trigger a map change.

Player Lifecycle
----------------

Players join and play the game in a number of phases and states:

Connection Start
^^^^^^^^^^^^^^^^

An ENet connection handshake is performed. ``protocol.on_connect`` is called
once complete.

This creates a new ``Connection`` object, on which ``connection.on_connect`` is
called. This decides if the player should be allowed to join based on
information such as the player count, IP or protocol version.

Map Transfer
^^^^^^^^^^^^

The map is generated and sent to the player. A snapshot of current player state
is saved, on top of which changes occurring during map transfer will be
layered. A handshake is started to identify the client version and available
protocol extensions.

On map transfer completion, ``connection.on_join`` will be called.

Limbo
^^^^^

After map transfer, players are in the "Limbo" state. They are in this state
until the client sends an `ExistingPlayer` packet containing the chosen name
and team ID.

Joined
^^^^^^

Once a team is selected, ``connection.on_team_join`` is called to validate the
team choice. ``connection.on_login`` is then called to validate the chosen
name.

Spawned
^^^^^^^

When a player is about to be spawned, ``connection.on_spawn_location`` is
called to allow overriding the position. ``connection.on_spawn`` is called when
the spawn is performed.

Dead
^^^^

When a player dies, `connection.on_kill` is called.
