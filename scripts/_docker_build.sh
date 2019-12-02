#!/bin/bash

# WARNING: do not run manually; this is run in the docker container by ./scripts/build_wheels.sh

# builds the binary wheels for supported python versions

set -e -x


# code from https://github.com/pypa/python-manylinux-demo/blob/master/travis/build-wheels.sh
# Compile wheels
cd /io/
for PYBIN in /opt/python/{cp35-cp35m,cp36-cp36m,cp37-cp37m,cp38-cp38}/bin; do
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
chmod -f go+w -R /io/build /io/wheelhouse /io/piqueserver.egg-info/
