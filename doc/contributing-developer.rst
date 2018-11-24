Contributing (developer)
========================

This is the developer guide for contributing to piqueserver.

Requirements
------------

Any code which does not follow the requirements below have chances of
**not being accepted** into the ``master`` branch until modified to
comply with them. You may submit code which does not comply with the
requirements and leave for a maintainer to fix them, but it's considered
bad practice.

-  The `EOL <https://en.wikipedia.org/wiki/Newline>`__ (End-of-line)
   character for the file types below must be LF (\\n)

   -  Python and Cython scripts (``.py`` and ``.pyx``)
   -  C and C++ scripts (``.c``, ``.cpp``, ``.h``)
   -  Shell scrips (``.sh``, ``.bash``)

-  The `EOL <https://en.wikipedia.org/wiki/Newline>`__ (End-of-line)
   character for the file types below must be CRLF (\\r\\n)

   -  Windows scripts (``.bat``, ``.ps1``)

-  All files must end with their respective
   `EOL <https://en.wikipedia.org/wiki/Newline>`__ character, as
   mentioned above
-  No trailing whitespaces and/or tabs
-  Blank lines are allowed, but be careful to not use more than 2
   together
-  Indentation rules are not decided yet, use the one of the file you
   are editing
-  In case it's a new file, prefer 4 whitespaces over tabs
-  `NEVER USE BOTH SPACES AND TABS, NEVER <http://imgur.com/VyMu86F>`__

Work-flow recommendations
-------------------------

* Get yourself comfortable with ``git`` from command-line, it allows
  you to do things that some GUIs can't
* Follow the below instructions for commit summaries (a.k.a. the first
  line)
* No more than 70 characters of length
* Describe an action, in imperative form
* **e.g.:** ``implement anti-cheating optimizations``
* See also: `Closing issues via commit
  messages <https://help.github.com/articles/closing-issues-via-commit-messages/>`__

Finding history
---------------

Although piqueserver code is based on PySnip and does contain its
commits, **it's not possible to see them by default** in the GitHub web interface or
`gitk <https://git-scm.com/docs/gitk>`_, due to `a
commit <https://github.com/piqueserver/piqueserver/commit/487515b235cbfcbb87bd774781128c2eea39d2a5>`__
in the early days of piqueserver that made the imported files be treated
as new ones.

To see the true history of a file, you must use an log visualizer that
follows renames, such as:

* ``gitk --follow *FILE*``
* ``git log --follow --pretty=oneline *OPTIONS*``
