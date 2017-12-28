piqueserver |Build Status| |Build status| |Coverage Status| |Join the chat at https://gitter.im/piqueserver/piqueserver|
========================================================================================================================

An Ace of Spades 0.75 server based on
`PySnip <https://github.com/NateShoffner/PySnip>`__.

\:point_right: Chat with us!
----------------------------

-  Gitter: |Join the chat at https://gitter.im/piqueserver/piqueserver|
-  Matrix: ``#piqueserver:matrix.org`` (`Riot Webchat
   link <https://riot.im/app/#/room/#piqueserver:matrix.org>`__)
-  Slack: Message us for an invite!
-  IRC: ``#piqueserver`` on freenode.net
   (`web <http://webchat.freenode.net/?channels=%23piqueserver>`__)

All of these are bridged together!

\:tada: Features
----------------

-  Many administrator features
-  A lot of epic commands
-  A remote console (using SSH)
-  Map rotation
-  Map metadata (name, version, author, and map configuration)
-  Map extensions (water damage, etc.)
-  A map generator
-  An IRC client for managing your server
-  A JSON query webserver
-  A status server with map overview
-  Server/map scripts
-  Airstrikes
-  Melee attacks with the pickaxe
-  New gamemodes (deathmatch / runningman)
-  Rollback feature (rolling back to the original map)
-  Spectator mode
-  Dirt grenades
-  Platforms with buttons
-  Ban subscribe service
-  A ton of other features

\:rocket: Installation
----------------------

pip (stable version)
~~~~~~~~~~~~~~~~~~~~

.. code:: bash

    pip install piqueserver

to install with the optional ssh server

.. code:: bash

    pip install piqueserver[ssh]

git (bleeding edge)
~~~~~~~~~~~~~~~~~~~

.. code:: bash

    git clone https://github.com/piqueserver/piqueserver
    virtualenv2 venv
    source venv/bin/activate
    pip install -r requirements.txt
    python setup.py install

Archlinux
~~~~~~~~~

An `AUR package <https://aur.archlinux.org/packages/piqueserver-git/>`__
(git master) is available. Install manually or with your favourite AUR
helper:

.. code:: bash

    pacaur -y piqueserver-git

\:rocket: Running
-----------------

Then copy the default configuration as a base to work off

.. code:: bash

    piqueserver --copy-config

A-a-and lift off!

.. code:: bash

    piqueserver

Custom config location
~~~~~~~~~~~~~~~~~~~~~~

If you wish to use a different location to ``~/.config/piqueserver/``
for config files, specify a directory with the ``-d`` flag:

.. code:: bash

    piqueserver --copy-config -d custom_dir
    piqueserver -d custom_dir

\:speech_balloon: FAQ
---------------------

What's the purpose?
~~~~~~~~~~~~~~~~~~~

The purpose of this repo is to be a continuation of PySnip.

What if PySnip development returns?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Then they would merge our changes and development would be continued
there, I guess. The important thing is to keep AoS servers alive.

Why should I use piqueserver instead of PySnip/PySpades?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

-  Multi config installation
-  Docker support
-  Bug fixes
-  Improvements
-  Better anti-hacking
-  New scripts

What about 0.76 support
~~~~~~~~~~~~~~~~~~~~~~~

Working with multiple versions is a pain. 0.76 will be suported in the
future only.

Is that everything?
~~~~~~~~~~~~~~~~~~~

Please see also the
`Wiki <https://github.com/piqueserver/piqueserver/wiki>`__ for more
information.

\:blush: Contribute
-------------------

Don't be shy and submit us a PR or an issue! Help is always appreciated

\:wrench: Development
---------------------

Use ``pip`` and ``virtualenv`` to setup the development environment:

.. code:: bash

    $ virtualenv -p python2 venv && . ./venv/bin/activate
    (venv) $ pip install -r requirements.txt
    (venv) $ ./setup.py install
    (venv) $ deactivate # Deactivate virtualenv

--------------

Brought to you with :heart: by the `piqueserver
team <https://github.com/orgs/piqueserver/people>`__.

.. |Build Status| image:: https://travis-ci.org/piqueserver/piqueserver.svg?branch=master
   :target: https://travis-ci.org/piqueserver/piqueserver
.. |Build status| image:: https://ci.appveyor.com/api/projects/status/3mayprg9le4lejmm/branch/master?svg=true
   :target: https://ci.appveyor.com/project/piqueserver/piqueserver/branch/master
.. |Coverage Status| image:: https://coveralls.io/repos/github/piqueserver/piqueserver/badge.svg?branch=master
   :target: https://coveralls.io/github/piqueserver/piqueserver?branch=master
.. |Join the chat at https://gitter.im/piqueserver/piqueserver| image:: https://badges.gitter.im/piqueserver/piqueserver.svg
   :target: https://gitter.im/piqueserver/piqueserver?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge&utm_content=badge
