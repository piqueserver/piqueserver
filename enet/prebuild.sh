#!/bin/bash
set -e
set -x
pwd

LIB_VERSION=1.3.13

rm -f "enet-${LIB_VERSION}.tar.gz"
rm -f pyenet/enet-pyspades.pyx
rm -f pyenet/enet.so
rm -rf pyenet/enet

cp pyenet/enet.pyx pyenet/enet-pyspades.pyx
patch -p1 < pyspades-pyenet.patch

# If dies, use "https://github.com/noway421/enet/archive/${LIB_VERSION}.tar.gz"
# But really only https://github.com/noway421/enet/archive/1.3.3.tar.gz exists
# No other version are supported in pyspades. If their website goes down no
# other versions are fetchable. If you'd like to port to another version and
# bespin.org is dead, use https://github.com/lsalzman/enet, eg
# https://github.com/lsalzman/enet/tree/ee869ab08a
wget "http://enet.bespin.org/download/enet-${LIB_VERSION}.tar.gz"

tar -xzvf "enet-${LIB_VERSION}.tar.gz" -C pyenet "enet-${LIB_VERSION}" && mv pyenet/enet-${LIB_VERSION} pyenet/enet
cp __init__.py-tpl pyenet/__init__.py

# patch -p1 < pyspades-enet.patch
