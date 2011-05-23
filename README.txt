=========================================================
PYSPADES - ACE OF SPADES NETWORK PROTOCOL IMPLEMENTATIONS
=========================================================
http://code.google.com/p/pyspades

What is 'pyspades'?
---------------------
pyspades is a package which includes Twisted protocol implementations for
Ace of Spades' client and server. 

How do I install pyspades?
----------------------------
pyspades doesn't have a setup.py file at the moment (but will have one, once I
can be bothered). 

Dependencies include:
    * The Twisted framework (http://twistedmatrix.com) for networking
      Remember, Twisted depends on zope.interface:
      http://pypi.python.org/pypi/zope.interface
    
    * Cython (http://cython.org) for compiled and accelerated extension modules
      You will also need a compiler in case you are building from source.

If you are installing from source, build using build.bat on Windows or
build.sh on Linux/Mac/whatever.

How do I use pyspades?
------------------------
Wiki:
http://code.google.com/p/pyspades/w/list

API documentation is in the works.