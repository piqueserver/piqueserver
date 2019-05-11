Supported Python environments
=============================

Piqueserver 0.1.0 supports the following Versions of CPython: 3.5, 3.6 and 3.7

Migration from Python 2 to Python 3
-----------------------------------
To Migrate an existing installations over, follow the following steps:

 1. Make sure Python3.5+ is installed on your system: ``python3 --version``
 2. Make sure the Python3 version of pip is installed on your system:  ``pip3 --version``
 3. ``pip uninstall piqueserver``
 4. ``pip3 install --upgrade piqueserver``
 5. Start up your server again and verify no errors are shown in the console

Possible issues with the migration
----------------------------------
Python3 has changed many internals of the python language. Because of that, some subtle bugs might occur.

Old pyspades scripts will likely be broken by this change too. If this happens, just open an issue or chat with us and we will work with you to get it ported to the new version!

.. seealso::

   :doc:`porting`
