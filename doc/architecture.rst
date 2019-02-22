Architecture
============

Overview
--------

The piqueserver codebase is made up out of two main packages: `pyspades` and
`piqueserver`. The `piqueserver` module used to be named ``feature_server``.
The original developers wanted to make the pyspades a generic AoS protocol and
server implementation which the ``feature_server`` module then subclassed and
specialized.

However, the unclear division and two locations quickly lead to a large mess,
and it is currently not possible to know for certain which module exactly
contains certain functionality. In general, this is the rule of thumb:

 * `pyspades`: Anything that involves sending and receiving of packets and
   acting on those, keeping game state.

 * `piqueserver`: Anything player-facing, for example commands,
   configuration, etc.

Note however the numerous exceptions to this. For example, parts of the command
logic are in `pyspades`, while a lot of server validation logic is in
`piqueserver`

Classes
-------

There are currently two classes which contain the bulk of the logic.
``Connection``, and ``Protocol``. The ``Connection`` class does not actually
represent a connection, it represents a player connected to the server and is
contained in the ``player.py`` file in the relevant module. The ``Protocol``
object is similar, but represents the server and is in the ``server.py`` file.

Many classes and modules have descriptions you can view in this
documentations or in the files themselves.

Extension Scripts
-----------------

Piqueserver supports extension scripts aka "scripts" that modify it's behaviour.
The mechanism used to implement these is pretty ugly.

Each script defines an ``apply_script(protocol, connection, config)`` function.
This function is called on script initialization with the protocol class, connection
class and the config dict. Scripts are intended to then dynamically subclass the
protocol and connection classes and return those, overriding methods where
needed::

   def apply_script(protocol, connection, config):
       class ScriptNameProtocol(protocol):
           def my_overridden_function(self, arg):
               ...
               return protocol.my_overridden_function(self, arg)
           ...

       class ScriptNameConnection(connection):
           ...

       return ScriptNameProtocol, ScriptNameConnection
       
The application of these scripts is performed in a loop, ``apply_script`` always being 
called with the classes returned by the last invocation. This way, the final class
created inherits from all extension classes.

This is a terrible idea for a number of reasons, but just the way things work currently:

  * Extensions must meddle with the internals of piqueserver. This means that scripts
    are likely to break whenever any internals are changed, making substatial
    changes harder.
  
  * It is impossible to load or unload scripts after starting the server
  
  * There is no clear and defined API for scripts. This makes writing scripts unecessarily
    difficult and also increases breakage.
    
  * Debugging this is very hard
  
Game mode scripts are identical to regular extension scripts in functionality. However,
they are required to define an attribute named ``game_mode`` on the ``Protocol`` class
that describes the base game mode, ``CTF_MODE`` or ``TC_MODE``. This is required because
at a protocol level, AoS currently only supports those two game modes. Any other game
modes must be emulated using the functionality provided by these two game modes.
