#!/bin/sh

cd "$(dirname "$(readlink -f "$(command -v "$0")")")"
if [ -d "venv/" ] && [ ! "x$(command -v python)" == "x$VIRTUAL_ENV/bin/python" ]; then
	source ./venv/bin/activate
	echo "Using virtualenv"
fi

cd feature_server
exec python2 run.py "$@"
