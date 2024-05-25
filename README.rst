piqueserver |Build Status| |Wheel Status| |Coverage Status|
===========================================================

An Ace of Spades 0.75 server based on
`PySnip <https://github.com/NateShoffner/PySnip>`__.

\:point_right: Chat with us!
----------------------------

-  Gitter: |Join the chat at https://gitter.im/piqueserver/piqueserver|
-  Matrix: ``#piqueserver:matrix.org`` (`Riot Webchat
   link <https://riot.im/app/#/room/#piqueserver:matrix.org>`__)
-  Discord: Join with `this invite link <https://discord.gg/w6Te7xC>`__
-  Slack: Join with `this invite link <https://join.slack.com/t/piqueserver/shared_invite/enQtMjg5MDI3MTkwNTgxLTNhMDkyNDRkNzhiNmQyYjRkOTdjNGNkYzNhNTQ4NzZkY2JhZjQxYzIyMTQ0Y2JlYTI2ZGFjMTFmNjAwZTM2OGU>`__

All of these are `bridged <https://matrix.org/docs/guides/faq.html#what-is-matrix>`__ together!

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

Requirements
~~~~~~~~~~~~

Piqueserver requires Python 3.8 and above

We currently provide builds for:
 - Linux x86_64
 - Windows x86 and x86_64
 
If your system is not one of the above, you will also need a recent C++ Compiler.

pip (stable version)
~~~~~~~~~~~~~~~~~~~~

.. code:: bash

    pip3 install piqueserver

Optional features:

- `ssh`: enable ssh manhole server support
- `from`: enable the `from` command to geolocate players by ip

To install with optional features with pip:

.. code:: bash

    pip3 install piqueserver[ssh,from]

git (bleeding edge)
~~~~~~~~~~~~~~~~~~~

.. code:: bash

    git clone https://github.com/piqueserver/piqueserver
    cd piqueserver
    python3 -m venv venv
    source venv/bin/activate

    pip install .

    # now `piqueserver` will be available on the $PATH when venv is active

Arch Linux
~~~~~~~~~~

The `AUR package <https://aur.archlinux.org/packages/piqueserver-git/>`__
(git master) is currently broken. When it gets repaired (you can help!),
you'll be able to install manually or with your favourite AUR helper:

.. code:: bash

    pacaur -S piqueserver-git

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
`Online Documentation <https://piqueserver.readthedocs.io/en/latest/>`__ for more
information (readthedocs.io has replaced our wiki).

Where can i find more scripts?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

You can checkout the `Piqueserver Extras Repository <https://github.com/piqueserver/piqueserver-extras>`__, that contains scripts made by the community and ports from PySnip/PySpades script.
Or in community forums, such as:
`aloha.pk <https://aloha.pk/c/aos-modding/scripts/83>`__ and `BuildAndShoot <https://www.buildandshoot.com/forums/viewforum.php?f=19>`__

\:blush: Contribute
-------------------

Don't be shy and submit us a PR or an issue! Help is always appreciated

\:wrench: Development
---------------------

Use ``python3`` and ``pip`` to setup the development environment:

.. code:: bash

    $ python3 -m venv venv && source venv/bin/activate
    (venv) $ pip install -e '.[dev]' # install in-place
    (venv) $ deactivate # Deactivate virtualenv

--------------

Brought to you with :heart: by the `piqueserver
team <https://github.com/orgs/piqueserver/people>`__.

.. |Build Status| image:: https://github.com/piqueserver/piqueserver/actions/workflows/main.yml/badge.svg?branch=master
   :target: https://github.com/piqueserver/piqueserver/actions/workflows/main.yml
.. |Wheel Status| image:: https://github.com/piqueserver/piqueserver/actions/workflows/wheels.yml/badge.svg?branch=master
   :target: https://github.com/piqueserver/piqueserver/actions/workflows/wheels.yml
.. |Coverage Status| image:: https://coveralls.io/repos/github/piqueserver/piqueserver/badge.svg?branch=master
   :target: https://coveralls.io/github/piqueserver/piqueserver?branch=master
.. |Join the chat at https://gitter.im/piqueserver/piqueserver| image:: https://badges.gitter.im/piqueserver/piqueserver.svg
   :target: https://gitter.im/piqueserver/piqueserver?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge&utm_content=badge
