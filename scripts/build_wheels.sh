#!/bin/bash

# script to fire up the docker image with the build script to produce all the
# binary wheels. Wheels are saved to projectroot/wheelhouse/
# Will have to be run as root or user in the docker group.
# Also should be run with the cwd equal to the project root.

set -e -x

# pull the latest image
docker pull quay.io/pypa/manylinux1_x86_64

# run the build script in the image
docker run --rm -v `pwd`:/io quay.io/pypa/manylinux1_x86_64 /io/scripts/_docker_build.sh
