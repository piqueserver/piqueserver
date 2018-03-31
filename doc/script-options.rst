Script Options
==============

piccolo\.scripts\.afk
--------------------------------
Auto-kicks players after they were afk for set time_limit.

.. code-block:: guess

   [afk]
   time_limit = 15 # in minutes

piccolo\.scripts\.aimbot2
------------------------------------
Detects and react to possible aimbot users.

.. code-block:: guess

   [aimbot]
   collect_data = true # saves hits and shots of each weapon to a csv file

piccolo\.scripts\.antijerk
-------------------------------------
Kicks jerks for 'PRESS ALT-F4 FOR AIRSTRIKES' and so on.

.. code-block:: guess

   [antijerk]
   ban_duration = 15 # in minutes

piccolo\.scripts\.blockinfo
-----------------------------------
A tool for identifying griefers. Provides /griefcheck command.

.. code-block:: guess

   [blockinfo]
   griefcheck_on_votekick = true
   irc_only = false

piccolo\.scripts\.medkit
--------------------------------------
Gives a specified amount of medkits on spawn.

.. code-block:: guess

   [medkit]
   medkits = 1 # no. of medkits
   medkit_heal_amount = 40 # how much hp. it gives

piccolo\.scripts\.rangedamage
--------------------------------------
Changes the damage values depending on distance.

.. code-block:: guess

   [rangedamange.rifle]
   pct_per_block = 0 # percentage per block?
   multiplier = 1

   [rangedamange.smg]
   pct_per_block = 0
   multiplier = 1

   [rangedamange.shotgun]
   pct_per_block = 0
   multiplier = 1

piccolo\.scripts\.spawn_protect
--------------------------------------
Protects spawned players for a specified amount of seconds.

.. code-block:: guess

   [spawn_protect]
   protection_time = 3 # in seconds

piccolo\.scripts\.spectatorcontrol
--------------------------------------
Lets you set restrictions on spectators.

.. code-block:: guess

   [spectator_control]
   no_chat = false # determines whether spectators can chat or not in your server
   kick = false # determines whether spectators will be kicked after remaining for so long
   kick_time = 300 # how long a spectator may remain before they are kicked; time in seconds

