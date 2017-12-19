#!/bin/bash

# script to fire up the docker image with the build script to produce all the
# binary wheels.
# Will have to be run as root or user in the docker group.
# Also should be run with the cwd equal to the project root.

set -e -x

docker run --rm -v `pwd`:/io quay.io/pypa/manylinux1_x86_64 /io/scripts/_docker_build.sh
