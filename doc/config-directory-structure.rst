Config directory structure
==========================

The configuration directory follows a strict structure.

By default the configuration directory lives at ``$XDG_CONFIG_HOME/piqueserver/`` with a fallback to ``$HOME/.config/piqueserver/``, as specified by the `XDG Base Directory Specification <https://standards.freedesktop.org/basedir-spec/basedir-spec-latest.html>`_.

This can be overridden by the `-d` command line option.

What follows is an explanation of each file or subdirectory:

- ``config.json``: The main configuration file. By default piqueserver will look for ``config.json`` in the config directory. This can be overridden by the `-c command line option <https://github.com/piqueserver/piqueserver/wiki/Command-line-arguments#-c-or---config-file>`_.
- ``README.md``: A markdown formatted (plain text) file with a short explanation of the layout of the config directory. Not required, but may contain some useful information for quick reference. This is copied here by default by ``piqueserver --copy-config``.
- ``logs/``: This directory contains logs output by the server. Currently the main server logfile is ``logs/log.txt``.
- ``maps/``: Any map files should be stored in here. Where a map is specified by name in ``config.json``, the server will look for  a ``txt`` or ``vxl`` file with that name.
- ``scripts/``: All scripts should be stored in this directory. The server will load any scripts listed in ``config.json`` by name from here. For example, if ``"votekick"`` is listed in the ``"scripts"`` array, then ``scripts/votekick.py`` will be loaded. There will be a lot of scripts included by default with piqueserver (and copied into that directory if you run ``piqueserver --copy-config``), and you can add whatever new scripts you want there too.
- ``game_modes/``: Scripts that are specifically game modes will be stored here.
- ``data/``: Various other data files are stored here. Currently it's only used for the geoip data file required by the ``/from`` command in-game.
