
.PHONY: all help fixme install pylint

all: help

install:
	python setup.py install

help:
	@echo "Available commands:"
	@echo "make install: run setup.py install"
	@echo "make pylint:  run pylint"
	@echo "make fixme:   find FIXME, TODO, NOTE, and XXX in the code"

pylint:
	pylint piqueserver pyspades

fixme:
	pylint piqueserver pyspades --disable=all --enable=fixme
