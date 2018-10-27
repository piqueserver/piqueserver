
.PHONY: all help fixme install pylint clean develop

all: help

install:
	python setup.py install

help:
	@echo "Available commands:"
	@echo "make install: run setup.py install"
	@echo "make pylint:  run pylint"
	@echo "make fixme:   find FIXME, TODO, NOTE, and XXX in the code"
	@echo "make clean:   remove all build artifacts after building inplace"
	@echo "make develop: run setup.py develop to build inplace for development"

pylint:
	pylint piqueserver

fixme:
	pylint piqueserver pyspades --disable=all --enable=fixme

clean:
	rm -f "pyspades/*.so"  # built c extensions
	rm -f pyspades/{bytes,common,contained,loaders,mapmaker,packet,vxl,world}.cpp
	rm -rf build/ piqueserver.egg-info/

develop:
	python setup.py develop
