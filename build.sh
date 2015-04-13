#!/bin/sh

python2 build.py build_ext --inplace
cd enet
python2 setup.py build_ext --inplace
