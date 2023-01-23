Installation
============

.. note:: piqueserver only supports python 3.7 and above


All platforms
--------------

Installing with pip
~~~~~~~~~~~~~~~~~~~
.. code:: bash

    pip3 install piqueserver # vanilla install
    pip3 install piqueserver[ssh] # if you also want ssh server


Unix-like
---------

Installing from source
~~~~~~~~~~~~~~~~~~~~~~
.. code:: bash

    # required for https, pillow, map compression etc.
    # these are for ubuntu 16.04, find similar packages for your own distro/OSs
    sudo apt-get install python3-dev libssl-dev libffi-dev libjpeg-dev zlib1g-dev
    # get the source
    git clone https://github.com/piqueserver/piqueserver
    cd piqueserver
    # we make git tags for every version so you can checkout out to specific version if you want
    # git checkout v0.1.3
    # create a new python3 venv
    virtualenv -p python3 venv
    source venv/bin/activate
    # install deps.
    pip install -r requirements.txt
    # install piqueserver
    python setup.py install

    # don't forget to deactivate the venv when finished!
    deactivate

Windows
-------

Installation from source
~~~~~~~~~~~~~~~~~~~~~~~~

.. note:: 

    Most of the piqueserver team uses Linux and we aren't experienced with Cython on windows. 
    If you can help us improve windows support we'd greatly appreciate it.

Tricky bit for windows is to get Cython working. 

* Install Visual C++ compiler please follow `this guide <https://wiki.python.org/moin/WindowsCompilers>`_.
* Don't forget to upgrade `setuptools`
* Install git or download sources from github and unzip
* If you decided to use git: `git clone https://github.com/piqueserver/piqueserver`

.. tip:: If you see errors like "unable to find vcvarsall.bat" refer to `this article <https://blogs.msdn.microsoft.com/pythonengineering/2016/04/11/unable-to-find-vcvarsall-bat/>`_.

.. code:: bash

    cd piqueserver
    pip3 install -r requirements.txt
    python setup.py install

