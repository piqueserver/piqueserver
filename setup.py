from os import path as __p
venv_dirs = [__p.join(__p.dirname(__p.realpath(__file__)), i) for i in ('venv', '.venv')]
for venv_dir in venv_dirs:
    try:
        activate_venv = __p.join(venv_dir, 'bin/activate_this.py')
        execfile(activate_venv, dict(__file__=activate_venv))
    except IOError:
        pass
    else:
        break
print "Using virtualenv from %s" % venv_dir

import sys
import os
import distutils
import subprocess
import shutil
from setuptools import setup, find_packages, Extension
from distutils.core import run_setup
from Cython.Distutils import build_ext as _build_ext

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


class build_ext(_build_ext):
    def run(self):
        compile_enet()
        _build_ext.run(self)

setup(
    name = 'pysnip',
    packages = ['pysnip', 'pysnip.web', 'pyspades', 'pyspades.enet'],
    version = '0.0.0',
    description = 'Open-source server implementation for Ace of Spades',
    author = 'Matpow2, Stackoverflow',
    author_email = 'nate.shoffner@gmail.com',
    url = 'https://github.com/NateShoffner/PySnip',
    download_url = 'https://github.com/NateShoffner/PySnip/archive/master.tar.gz',
    keywords = ['ace of spades', 'aos', 'server'],
    classifiers = [],
	setup_requires = ['cython'],
	install_requires = ['twisted'],
	extras_require = {
		'from': ['pygeoip'],
		'statusserver': ['jinja2', 'pillow'],
		'ssh': ['pycrypto', 'pyasn1']
	},
    entry_points = {
        'console_scripts': [
            'pysnip=pysnip.__main__:main'
    	],
    },
    package_dir = {'pysnip': 'feature_server', 'pysnip.web': 'feature_server/web', 'pyspades': 'pyspades', 'pyspades.enet': 'enet/pyenet'}, # some kind of find_packages?
    package_data = {"pyspades.enet": ["enet.so"], "pysnip.web": ["templates/status.html"]},

    ext_modules = ext_modules,
    cmdclass = {'build_ext': build_ext},
)
