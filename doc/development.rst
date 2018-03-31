Development
============

Testing
--------

Testing in piccolo is performed with ``pytest`` with ``tox`` support.

Tox manages its own virtual environments, so if you have it installed on your
system, testing is as simple as running ``tox``, which will run all tests against
all supported python versions (skipping those not available on your system).


If you already are in your virtual env and wish to test something quickly,
``pytest`` directly may be useful:

.. code:: bash

   # make sure the venv is setup and all deps are installed
   python -m venv venv && source venv/bin/activate
   pip install -r requirements.txt -r dev-requirements.txt

   # build the cython extensions inplace
   # otherwise pytest has issues
   python setup.py build_ext --inplace

   # and test away!
   pytest

   # single file
   pytest tests/piccolo/test_server.py


Code Coverage
-------------

Code coverage is generated with `coverage.py <https://coverage.readthedocs.io/en/latest/>`__ using a ``pytest`` plugin.

.. code:: bash

   # generate coverage data
   pytest --cov=piccolo --cov=pyspades

   # build the report file
   coverage html

   # view at htmlcov/index.html
