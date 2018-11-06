Configuring Piqueserver
=======================

Piqueserver is configured through a config file, usually named
:file:`config.toml`.  Piqueserver uses the configuration language TOML (Tom's
Obvious Markup Language). A detailed description of TOML can be found `in the
TOML readme <https://github.com/toml-lang/toml/blob/master/README.md>`_, but a
short example is provided below.

.. note::
    PySpades, PySnip and versions of piqueserver before 1.0.0 used a JSON file
    for settings. These files will still be read, if no config.toml is
    available. However, the structure piqueserver expects might differ.

TOML Syntax
-----------

TOML files are plaintext files. They can be edited with any plaintext editor of
your choice, such as Notepad++ on windows, editor on mac and, nano or gedit on
Linux.

Configuration is case-sensitive. This means that your settings will not apply
correctly if you use the incorrect case.

The section header is followed by key-value pairs::

    name = "best server ever"

If a # is encountered, the rest of the line will be ignored.

There are a number of types of values::

    text = "text, surrounded by quotes"

    motd = """
    a longer text
    that can stretch
    over more lines
    (useful for the MOTD!)"""

    list = ["a", "list",
            "of", "values"]

    a_number = 123.5
    enable_thing = true  # or false

TOML supports sections similar to the Microsoft :file:`.ini` file format. The
beginning of a section is marked by the name of the section surrounded by
square brackets::

    [general]

Any key-value pairs that follow this are part of that section, until a new section is started.

.. _substitution:

Substitution
------------

Some config options allow data about the server to be substituted. These
options are enclosed in curly braces. This example uses all substitutions that
are available when substitution is available for a config option::

    motd = [
        "Welcome to {server_name}! See /help for commands.",
        "you are playing {game_mode}",
        "Map is {map_name} by {map_author}.",
        "Map description: {map_description}.",
        "(server powered by piqueserver)",
    ]

Individual config options might have additional subsitutions available. This is
noted in the documentation for the relevant option.

.. versionadded:: 1.0.0
    The ``{name}`` format was added. The older, ``%(name)s`` format is deprecated.

Options
-------

.. toctree::
    config-options
