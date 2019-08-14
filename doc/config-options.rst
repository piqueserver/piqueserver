Base Configuration Options
==========================

These are the base configuration options available in piqueserver.

General
-------

This section contains general information and configuration for the server

name
++++

The Name of the server, as displayed on the master server list::

    name = "piqueserver instance"

This config option supports :ref:`substitution`.

motd
++++

A list of lines which should be sent when the player joins::

    motd = [
       "Welcome to the server",
       "Have fun! <3",
    ]

This config option supports :ref:`substitution`.

help
++++

This is the text shown by the /help command. If not defined, /help will
just display a list of the available commands.

This config option supports :ref:`substitution`.

rules
+++++

This is the text shown by the /rules command.

This config option supports :ref:`substitution`.

tips
++++

A line picked at random from this text will be shown every :ref:`tip_frequency` minutes.

This config option supports :ref:`substitution`.

.. _tip_frequency:

tip_frequency
+++++++++++++

How often the tip will be shown, in minutes. 0 means no tips. Default 5.

max_players
+++++++++++

The maximum number of players on the server. Going over 32 players will break
the vanilla AoS client, as is not designed to support more. Default 32.

game_mode
+++++++++

The ``ctf`` for "Capture the Flag", ``tc`` for "Territory Control". or a script
name for a custom game mode.

cap_limit
+++++++++

The number of captures that are required to end the game.

.. _rotation:

rotation
++++++++

A list of maps to use

default_time_limit
++++++++++++++++++

The default time limit to set per map. When the time limit runs out, the map rotation is advanced.

advance_on_win
++++++++++++++

If true, advance the map rotation when the game ends.

random_rotation
+++++++++++++++

``false`` if the order should be as in :ref:`rotation`, ``true`` if the order
should be shuffled. Default false.

max_connections_per_ip
++++++++++++++++++++++

Limits how many players can connect from the same IP address. 0 disables this limit. Default 0.

team1/team2
+++++++++++

This section configures the teams::

    [team1]
    # name of the team to be displayed in-game
    name = "Blue"
    # color of the players in RGB, 0-255
    color = [ 0, 0, 255]

    [team2]
    name = "Green"
    color = [ 0, 255, 0]

bans
++++

This section defines the behaviour when admins ban players::

    [bans]
    # default duration a banned player will be banned for
    default_duration = "1day"

    # location the bans are saved and loaded from
    file = "bans.txt"

    # Ban publish allows you to synchronize bans between servers. When enabled,
    # the server listens on the given port and responds to any requests with a list
    # of bans
    publish = false
    publish_port = 32885

    # Bansubscribe allows you to inherit bans from another server with banpublish enabled.
    # `url` is the URL returning the json list, `whitelist` is a list of names which should
    # be exempt from the filter
    bansubscribe = [
        { url = "http://www.blacklist.spadille.net/subscribe.json", whitelist = []},
    ]

    # how often the subscribed servers are frequented to update bans
    bansubscribe_interval = "5min"

.. _respawn_waves:

respawn_waves
+++++++++++++

When true, respawn all dead players every :ref:`respawn_time` seconds. When
false, respawn a player :ref:`respawn_time` seconds after their death. Spawning
in groups decreases the effectiveness of spawnkilling. Default true.

.. _respawn_time:

respawn_time
++++++++++++

see :ref:`respawn_waves`

cap_limit
+++++++++

The number of intel captures before the game is won. Default 10.


respawn_time
++++++++++++

The number of seconds before a player respawns. Default 5.

master
++++++

'true' shows server on the master serverlist. 'false' disables this, for
private games want a private game. Default false.

friendly_fire
+++++++++++++

``true``: enables friendly fire.
``false``: disables friendly fire.

.. _friendly_fire_on_grief:

friendly_fire_on_grief
++++++++++++++++++++++
if true, friendly fire is enabled temporarily if a player destroys a block.

spade_teamkills_on_grief
++++++++++++++++++++++++
If friendly fire should be enabled for the spade too. This is disabled by
default, because it often causes accidental teamkills in tunnels.

grief_friendly_fire_time
++++++++++++++++++++++++

The number of seconds a player is vulnerable to friendly fire after destroying
a block when :ref:`friendly_fire_on_grief` is enabled.

teamswitch_interval
+++++++++++++++++++

Forces players to wait a set duration before being able to switch back
again after they switched teams.

"0sec" disables the cooldown.

teamswitch_allowed
++++++++++++++++++

If ``true`` you only get to pick a team when you join.

detect_speedhack
++++++++++++++++

If ``true``, attempt to detect if users are speedhacking. This is not 100%
accurate, so it might be a good idea to disable it for servers where the users
are trusted.

rubberband_distance
+++++++++++++++++++

Distance the server tolerates between the place it thinks the client is to where the client actually is.
Default 10.

melee_damage
++++++++++++

The amount of damage dealt by the spade. Default 80.

fall_damage
+++++++++++

controls whether players receive damage by falling from height

passwords
+++++++++

This section contains roles and their associated passwords. When playing, a
player may gain that role by typing::

    /login <password>

Any name may be used for a role, but there are two special roles:
``admin`` and ``trusted``. Users with the ``admin`` role have the maximum rights
available, while ``trusted`` users are not affected by votekicks and similar.

Each account can have a list of passwords. It is usually a good idea to give
out one password per person::

    [passwords]
    admin = ["password","sesame","watermelon"],
    trusted = ["semi","coolness"]
    custom = ["mypass"]

rights
++++++

This section contains the commands each role can execute.

scripts
+++++++

.. TODO Document this on a separate page

Piqueserver ships with a set of scripts you can use to customize the features
of your server. They are loaded in order, "on top of" each other.

Scripts can either be absolute python import paths
(``piqueserver.scripts.aimbot2``) or the name of scripts in the scripts folder,
excluding the file extension (``mycustomscript`` for a script at
``scripts/mycustomscript.py``)::

    scripts = [
        "piqueserver.scripts.rollback",
        "piqueserver.scripts.protect",
        "myscript",
    ]

Logging
+++++++

Piqueserver can log events that happen to a text file::

    [logging]
    # set log level
    # log levels in decending order: debug, info, warn, error, critical
    loglevel = "info"
    # the logfile to log to
    # relative paths are resolved relative to the config directory; parent
    # directories are created as necessary
    # empty string disables logging
    logfile = "./logs/log.txt"

    # Write a new log file each day
    rotate_daily = true

    # enable profiling
    profile = false

ssh
+++

This section controls `SSH`_ "manhole" access to the server. This allows you
access to a python shell. This is mainly useful for debugging. If you don't know
what you are doing, you should leave it disabled::

    [ssh]
    enabled = false
    port = 32887

    [ssh.users]
    # user = password
    # pairs for credentials allowed to login to the ssh server
    # WARNING: keep these credentials secure since this gives console access to the server
    # on which piqueserver is running!
    user1 = "ssh_pass_change_this"

.. _ssh: http://en.wikipedia.org/wiki/Secure_Shell

status_server
+++++++++++++

The status server is a built-in web server that displays information about the
server and connected players::

    [status_server]
    enabled = true
    # the port to listen on
    port = 32886
    # write an access log
    logging = false

server_prefix
+++++++++++++

When the server sends messages to users, the message is prefixed with the characters in server_prefix.

user_blocks_only
++++++++++++++++

Controls whether users can affect the map's initial blocks.

logfile
+++++++

The file where the server log is recorded. Relative paths are resolved relative
to the configuration directory. For example if the logfile is `./logs/log.txt`,
this will be in the `logs` subdirectory of the config directory.

balanced_teams
++++++++++++++

If 0, any permutation of teams is allowed. If 1 or greater, players are not
allowed to join a team if that would mean the difference in players count
between the two teams is more than the ``balanced_teams`` value. Default 2.

login_retries
+++++++++++++

The number of /login attempts allowed before users are auto-kicked. Default 3.

irc
+++

This section configures an IRC chatbot that reports server events in the given channel::

    [irc]
    enabled = false
    # IRC login details
    nickname = "piqueserver"
    username = "piqueserver"
    realname = "piqueserver"
    server = "irc.quakenet.org"
    port = 6667

    # channel to join into
    channel = "#piquserver-bots"
    # password for the channel
    password = ""

    # prefixes irc users must use for bot to process as command or to send to game chat
    commandprefix = "!"
    chatprefix = "."

set_god_build
+++++++++++++

Put the player into god build mode automatically when entering god mode

time_announcements
++++++++++++++++++

Configure the times that announcements about the remaining time should be made.
This value is a list of times remaining in seconds.

ip_getter
+++++++++

Optionally override the service used to fetch the server's public ip address.
Eg. `"https://api.ipify.org"`. If this is set to an empty string,
IP getting is disabled.

Note: this url must return solely the ip address in the response body.

release_notifications
+++++++++++++++++++++

Check github for new releases and notify admins if new releases are found. Default True.

everyone_is_admin
+++++++++++++++++

Set `everyone_is_admin` to true to automatically log all players in as admin on
join.  Possibly useful for testing purposes.
