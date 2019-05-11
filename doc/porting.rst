Porting scripts
===============

Piqueserver still supports scripting just as PySnip did! However, since Piqueserver has had much 
refactoring and improvements since forking from PySnip, some scripts that work with PySnip, may 
not work immediately with Piqueserver. Never fear! The piqueserver team has avoided breaking 
changes regarding scripts as much as possible, and here are some details on some points that 
could be breaking changes.

.. tip:: Do `reach out to the piqueserver team <https://github.com/piqueserver/piqueserver#point_right-chat-with-us>`_ we can help you out!

Automated port to Python 3
--------------------------

Since Piqueserver doesn't support Python 2 anymore we have to port the scripts to Python 3.
Most of the porting can be automated with tools like `2to3 <https://docs.python.org/3.0/library/2to3.html>`_.
We can later fix issues related to py2->py3 as they arise.


Fix feature_server module imports
---------------------------------

.. code:: python

    # OLD
    from map import ...
    from commands import ...
    from scheduler import ...
    # NEW
    from piqueserver.map import ...
    from piqueserver.commands import ...
    from piqueserver.scheduler import ...
    from piqueserver.map import ...

``map.DEFAULT_LOAD_DIR`` and other constants
--------------------------------------------
This constant in `feature_server/map.py` is no longer, along with potentially others. Now, if you wish to get the map directory, you can use something like:

.. code:: python

    import os
    from piqueserver.config import config
    map_dir = os.path.join(config.config_dir, 'maps')


Fix player related imports
---------------------------

Most of the player related stuff from `pyspades.server` has been moved to `pyspades.player`.

.. code:: python

    # OLD
    from pyspades.server import create_player, player_left, intel_capture
    from pyspades.server import set_tool, weapon_reload
    # NEW
    from pyspades.player import create_player, player_left, intel_capture
    from pyspades.player import set_tool, weapon_reload


Fix packet imports
------------------

pyspades (and PySnip) have `various packet instances <https://github.com/infogulch/pyspades/blob/protocol075/pyspades/server.py#L43-L74>`_ in `pyspades.server` and those instances were used/shared by multiple scripts.
Which can get messy and cause bugs. In piqueserver those instances are no longer present and scripts have to create those instances themselves.

.. code:: python

    # OLD
    from pyspades.server import grenade_packet, block_action, set_color
    # NEW
    from pyspades.contained import GrenadePacket, BlockAction, SetColor
    # lazy fix: package level global like below
    grenade_packet, block_action, set_color = GrenadePacket(), BlockAction(), SetColor()
    # proper fix: create them wherever they get used

Debugging import errors
---------------------------
Import errors in scripts causes piqueserver to throw `NotImplementedError` which is vague(sorry!). 
For debugging those import errors use python(shell) or ipython they'll point you to which exact import is causing issues.

.. code:: python

    In [1]: import buildandsplat                                                                       
    ---------------------------------------------------------------------------
    ImportError                               Traceback (most recent call last)
    <ipython-input-1-01d8c693f582> in <module>
    ----> 1 import buildandsplat

    ~/piqueserver/piqueserver/game_modes/buildandsplat.py in <module>
        25 from pyspades.common import Vertex3, make_color, get_color
        26 from pyspades.constants import *
    ---> 27 from subprocess import add, admin, get_player, name
        28 from pyspades import contained as loaders
        29 from pyspades.weapon import WEAPONS

    ImportError: cannot import name 'add' from 'subprocess' (/usr/local/lib/python3.7/subprocess.py)



Final
------
Try out the script and see if anything breaks.
If the errors seem py2->py3 related refer to `this cheatsheet <http://python-future.org/compatible_idioms.html>`_.
Piqueserver team has done a `giant port of scripts <https://github.com/piqueserver/piqueserver/pull/181>`_ in v0.1.1 it can be used as a reference.
If you get stuck please `reach out to the piqueserver team <https://github.com/piqueserver/piqueserver#point_right-chat-with-us>`_ we are happy to help!


