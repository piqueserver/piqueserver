#!/usr/bin/env python2

from __future__ import print_function

# ### Virtualenv autoload ###
# # Not really sure whether it's worth it... Looks like reinveting virtualenv .
# # Consider making users to load virtualenv on their own.
# from os import path as __p
# venv_dirs = [__p.join(__p.dirname(__p.realpath(__file__)), i) for i in ('venv', '.venv')]
# activated_venv = None
# for venv_dir in venv_dirs:
#     try:
#         activate_this = __p.join(venv_dir, 'bin', 'activate_this.py')
#         execfile(activate_this, dict(__file__=activate_this))
#         activated_venv = venv_dir
#     except IOError:
#         pass
#     else:
#         break
# print("Using virtualenv %s" % activated_venv)

# import sys
# import os

# if activated_venv is not None:
#     sys.argv[0] = __p.join(activated_venv, 'bin', 'python2')
#     sys.executable = sys.argv[0]
#     os.environ['_'] = sys.argv[0]
#     sys.prefix = activated_venv
#     sys.exec_prefix = activated_venv
# ### Virtualenv autoload end ###


import sys
import os

PKG_NAME="piqueserver"
PKG_URL="https://github.com/piqueserver/piqueserver"
PKG_DOWNLOAD_URL="https://github.com/piqueserver/piqueserver/archive/master.tar.gz"

extra_args = sys.argv[2:]

import subprocess
import shutil
from setuptools import setup, find_packages, Extension, dist
from distutils.core import run_setup

try:
   import pypandoc
   import re
   long_description = pypandoc.convert_text(
        re.sub(r'[^\x00-\x7F]+',' ',
            pypandoc.convert('README.md', 'markdown', format="markdown_github")), 'rst', format="markdown")
except (IOError, ImportError):
    long_description = ''


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
    print("Linking the build statically.")

for name in names:
    if static:
        extra = {'extra_link_args' : ['-static-libstdc++', '-static-libgcc']}
    else:
        extra = {}

    if name in ['pyspades.vxl', 'pyspades.world', 'pyspades.mapmaker']:
        extra["extra_compile_args"] = ['-std=c++11']

    ext_modules.append(Extension(name, ['./%s.pyx' % name.replace('.', '/')],
        language = 'c++', include_dirs=['./pyspades'], **extra))


from distutils.command.build_ext import build_ext as _build_ext
class build_ext(_build_ext):
    def run(self):

        from Cython.Build import cythonize
        self.extensions = cythonize(self.extensions)

        _build_ext.run(self)

        run_setup(os.path.join(os.getcwd(), "setup.py"), ['build_py'] + extra_args)

setup(
    name = PKG_NAME,
    packages = [PKG_NAME, '%s.web' % PKG_NAME, 'pyspades'],
    version = '0.0.1',
    description = 'Open-Source server implementation for Ace of Spades',
    author = 'MatPow2, StackOverflow, piqueserver authors',
    author_email = 'nate.shoffner@gmail.com',
    maintainer = 'noway421',
    maintainer_email = 'noway@2ch.hk',
    license = 'GNU General Public License v3',
    long_description = long_description,
    url = PKG_URL,
    download_url = PKG_DOWNLOAD_URL,
    keywords = ['ace of spades', 'aos', 'server', 'pyspades', 'pysnip', 'piqueserver'],
    classifiers = [
        'Intended Audience :: System Administrators',
        'Development Status :: 3 - Alpha',
        'Operating System :: MacOS :: MacOS X',
        'Operating System :: Unix',
        'Environment :: Console',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Programming Language :: Python',
        'Programming Language :: Cython',
        'Programming Language :: Python :: 2 :: Only',
        'Framework :: Twisted',
    ],
    platforms = "Darwin, Unix",
    setup_requires = ['Cython>=0,<1'], # at least for now when we have to cythonize enet
    install_requires = ['Cython>=0,<1', 'Twisted>=17', 'Jinja2>=2,<3', 'Pillow>=3,<5', 'pyenet'], # status server is part of our 'vanila' package
    extras_require = {
        'from': ['pygeoip>=0.3.2,<0.4'],
        # 'statusserver': ['Jinja2>=2.8,<2.9', 'Pillow>=3.4.2,<3.5'],
        'ssh': ['pycrypto>=2.6.1,<2.7', 'cryptography>=2.0.0,<3.0', 'pyasn1>=0.1.9,<0.2']
    },
    entry_points = {
        'console_scripts': [
            '%s=%s.run:main' % (PKG_NAME, PKG_NAME)
        ],
    },
    package_dir = {PKG_NAME: 'piqueserver', '%s.web' % PKG_NAME: 'piqueserver/web', 'pyspades': 'pyspades'}, # some kind of find_packages?
    package_data = {"%s.web" % PKG_NAME: ["templates/status.html"]},
    include_package_data=True,

    ext_modules = ext_modules,
    cmdclass = { 'build_ext': build_ext },
)
