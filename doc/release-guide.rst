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
    python -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt -r dev-requirements.txt

    # build and install
    python setup.py install
    python setup.py build_ext --inplace

    # run the tests
    tox

    # ensure the server is runnable
    piqueserver -d piqueserver/config


Notes before continuing
-----------------------

These next steps involve pushing the packages to pypi as we go. Probably
a safer workflow would be to build the packages first, then update Git
with the version changes, and finally push to pypi. There is also the
test pypi instance to experiment with uploading packages if required.

Most important to remember is the step where we edit some files to bump
the version info.

Build the sdist
---------------

Prerequisites: Linux computer, ``python3.7`` (or greater), ``pip`` (same
version as the python you’re using), ``twine``

The source distribution is OS agnostic, so this is the easiest to start
with.

-  deactivate any venvs and ensure we’re back in a clean state on the
   correct branch:

::

    git checkout master # or release branch if this is a bug fix on old supported version
    git clean -xffd
    python -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt -r dev-requirements.txt


-  IMPORTANT: update ``piqueserver/version.py`` with the new version numbers (this should be the
   single source of version info for piqueserver).

-  build and upload the source distribution:

::

    python setup.py sdist
    twine upload dist/*

Build Linux binary wheels
-------------------------

Prerequisites: same as for sdist, plus ``docker``

-  make sure docker is running and you have a recent version of the pypa
   manylinux1 docker image

::

    sudo docker pull quay.io/pypa/manylinux1_x86_64

-  build and upload the linux binary wheels:

::

    ./scripts/build_wheels.sh
    twine upload wheelhouse/*

Build Windows binary wheels
---------------------------

Use the download-wheels tool to fetch the wheels from github actions.

::

    python download_wheels.py --ghtoken <your github token> -d winbuilds/

Update git
----------

Technically this can happen once we’re sure this will be a release, but
if done after building the packages, at least we know it’s all fine.

-  add, commit, tag, and push the version changes:

::

    git add -A
    git commit -m "release version X"
    git tag -a "v0.1.2"
    git push
    git push --tags

-  merge master across to the release branch if required:

::

    git checkout v0.1.x
    git merge master
    git push

-  create and publish release notes on the pushed tag on GitHub

Celebrate!
----------

🎉
