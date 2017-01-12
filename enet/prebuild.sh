#!/bin/sh
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

# If dies, use https://github.com/lsalzman/enet
# Search for commits with release preparation (they're not into tags)
wget "http://enet.bespin.org/download/enet-${LIB_VERSION}.tar.gz"

tar -xzvf "enet-${LIB_VERSION}.tar.gz" -C pyenet "enet-${LIB_VERSION}" && mv pyenet/enet-${LIB_VERSION} pyenet/enet
cp __init__.py-tpl pyenet/__init__.py

