Release Guide
=========================

Ensure we’re ready for release
------------------------------

-  branch should be up to date
-  github action builds should be passing
-  test with a clean install on local machine if possible
-  all the following should run without error (assuming Linux machine):

::

    # make sure we're clean and up to date
    git checkout master
    git pull
    git clean -xffd

    # clean install
    pip install -e .

    # do isolated build
    python -m build

    # run the tests
    tox

    # ensure the server is runnable
    piqueserver -d piqueserver/config

Build the sdist
---------------

Prerequisites: Linux computer, supported python version, ``pip`` (same
version as the python you’re using), ``twine``, ``build``, ``gh``

The source distribution is OS agnostic, so this is the easiest to start
with.

-  deactivate any venvs and ensure we’re back in a clean state on the
   correct branch
-  build and upload the source distribution:

::

    python -b build --sdist
    twine upload dist/*

Download binary wheels
----------------------

Use the download-wheels tool to fetch the wheels from github actions.

::

    cd dist/
    gh release dowload <git tag>

Update Github release
---------------------

Set the release as latest

Celebrate!
----------

🎉
