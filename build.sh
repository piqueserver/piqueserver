#!/bin/sh

cd "$(dirname "$(readlink -f "$(command -v "$0")")")"
if [ -d "venv/" ] && [ ! "x$(command -v python)" == "x$VIRTUAL_ENV/bin/python" ]; then
	source ./venv/bin/activate
	echo "Using virtualenv"
fi

python2 build.py build_ext --inplace
cd enet
python2 setup.py build_ext --inplace
