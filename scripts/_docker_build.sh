#!/bin/bash

# should be run in the docker container.
# builds the binary wheels

set -e -x


# code from https://github.com/pypa/python-manylinux-demo/blob/master/travis/build-wheels.sh
# Compile wheels
cd /io/
for PYBIN in /opt/python/{cp27-cp27m,cp27-cp27mu,cp34-cp34m,cp35-cp35m,cp36-cp36m}/bin; do
    # clean previous cached stuff
    rm -rf /io/build/
    git clean -fX -- pyspades
    "${PYBIN}/pip" install --only-binary Pillow -r /io/requirements.txt
    "${PYBIN}/python" setup.py bdist_wheel -d /wheelhouse/
done

cd /

# Bundle external shared libraries into the wheels
for whl in /wheelhouse/*.whl; do
    auditwheel show "$whl"
    auditwheel repair "$whl" -w /io/wheelhouse/
done

# fix perms so it's possible to remove without being root
chmod -f go+w -R /io/build /io/wheelhouse /io/piccolo.egg-info/
