#!/bin/bash
set -e

LIB_VERSION=1.3.3

rm -f enet-pyspades.pyx
rm -f enet
rm -f enet.so
rm -f "enet-${LIB_VERSION}.tar.gz"
rm -rf "enet-${LIB_VERSION}"

cp enet.pyx enet-pyspades.pyx
git apply pyspades-pyenet.patch

# If dies, use "https://github.com/noway421/enet/archive/${LIB_VERSION}.tar.gz"
# But really only https://github.com/noway421/enet/archive/1.3.3.tar.gz exists
# No other version are supported in pyspades. If their website goes down no
# other versions are fetchable. If you'd like to port to another version and
# bespin.org is dead, use https://github.com/lsalzman/enet, eg
# https://github.com/lsalzman/enet/tree/ee869ab08a
wget "http://enet.bespin.org/download/enet-${LIB_VERSION}.tar.gz"

tar -xzvf "enet-${LIB_VERSION}.tar.gz"
ln -s "enet-${LIB_VERSION}" enet

git apply pyspades-enet.patch
