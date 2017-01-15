#!/usr/bin/env python2

### Virtualenv autoload ###
# Not really sure whether it's worth it... Looks like reinveting virtualenv .
# Consider making users to load virtualenv on their own.
from os import path as __p
venv_dirs = [__p.join(__p.dirname(__p.realpath(__file__)), i) for i in ('venv', '.venv')]
activated_venv = None
for venv_dir in venv_dirs:
    try:
        activate_this = __p.join(venv_dir, 'bin', 'activate_this.py')
        execfile(activate_this, dict(__file__=activate_this))
        activated_venv = venv_dir
    except IOError:
        pass
    else:
        break
print "Using virtualenv %s" % activated_venv

import sys
import os

if activated_venv is not None:
    sys.argv[0] = __p.join(activated_venv, 'bin', 'python2')
    sys.executable = sys.argv[0]
    os.environ['_'] = sys.argv[0]
    sys.prefix = activated_venv
    sys.exec_prefix = activated_venv
### Virtualenv autoload end ###

PKG_NAME="piqueserver"
PKG_URL="https://github.com/piqueserver/piqueserver"
PKG_DOWNLOAD_URL="https://github.com/piqueserver/piqueserver/archive/master.tar.gz"

extra_args = sys.argv[2:]

import subprocess
import shutil
from setuptools import setup, find_packages, Extension
from distutils.core import run_setup

def compile_enet():
    previousDir = os.getcwd()
    os.chdir("enet")
    subprocess.Popen(["./prebuild.sh"]).communicate()

    os.chdir("pyenet")

    shutil.move("enet.pyx", "enet-bak.pyx")
    shutil.move("enet-pyspades.pyx", "enet.pyx")
    run_setup(os.path.join(os.getcwd(), "setup.py"), ['build_ext', '--inplace'])
    shutil.move("enet.pyx", "enet-pyspades.pyx")
    shutil.move("enet-bak.pyx", "enet.pyx")

    os.chdir(previousDir)

ext_modules = []

names = [
    'pyspades.vxl',
    'pyspades.bytes',
    'pyspades.packet',
    'pyspades.contained',
    'pyspades.common',
    'pyspades.world',
    'pyspades.loaders',
    'pyspades.mapmaker'
]

static = os.environ.get('STDCPP_STATIC') == "1"

if static:
    print "Linking the build statically."

for name in names:
    if static:
        extra = {'extra_link_args' : ['-static-libstdc++', '-static-libgcc']}
    else:
        extra = {}

    if name in ['pyspades.vxl', 'pyspades.world', 'pyspades.mapmaker']:
        extra["extra_compile_args"] = ['-std=c++11']

    ext_modules.append(Extension(name, ['./%s.pyx' % name.replace('.', '/')],
        language = 'c++', include_dirs=['./pyspades'], **extra))

try:
    from Cython.Distutils import build_ext as _build_ext
    class build_ext(_build_ext):
        def run(self):
            compile_enet()
            _build_ext.run(self)
            run_setup(os.path.join(os.getcwd(), "setup.py"), ['build_py'] + extra_args)
except ImportError as e:
    class build_ext(object):
        pass

    pass


setup(
    name = PKG_NAME,
    packages = [PKG_NAME, '%s.web' % PKG_NAME, 'pyspades', 'pyspades.enet'],
    version = '0.0.1',
    description = 'Open-Source server implementation for Ace of Spades',
    author = 'MatPow2, StackOverflow, piqueserver authors',
    author_email = 'nate.shoffner@gmail.com',
    url = PKG_URL,
    download_url = PKG_DOWNLOAD_URL,
    keywords = ['ace of spades', 'aos', 'server', 'pyspades', 'pysnip', 'piqueserver'],
    classifiers = [],
	setup_requires = ['Cython>=0.25.2,<0.26'],
	install_requires = ['Twisted>=16.6.0,<16.7'],
	extras_require = {
		'from': ['pygeoip>=0.3.2,<0.4'],
		'statusserver': ['Jinja2>=2.8,<2.9', 'Pillow>=3.4.2,<3.5'],
		'ssh': ['pycrypto>=2.6.1,<2.7', 'pyasn1>=0.1.9,<0.2']
	},
    entry_points = {
        'console_scripts': [
            '%s=%s.__main__:main' % (PKG_NAME, PKG_NAME)
    	],
    },
    package_dir = {PKG_NAME: 'feature_server', '%s.web' % PKG_NAME: 'feature_server/web', 'pyspades': 'pyspades', 'pyspades.enet': 'enet/pyenet'}, # some kind of find_packages?
    package_data = {"pyspades.enet": ["enet.so"], "%s.web" % PKG_NAME: ["templates/status.html"]},
    include_package_data=True,

    ext_modules = ext_modules,
    cmdclass = { 'build_ext': build_ext },
)
