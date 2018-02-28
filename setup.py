#!/usr/bin/env python3

from __future__ import print_function

import sys
import os
from distutils.core import run_setup
# build_ext is subclassed, so we import it with a _ to avoid a collision
from distutils.command.build_ext import build_ext as _build_ext
from setuptools import setup, Extension


PKG_NAME = "piqueserver"
PKG_URL = "https://github.com/piqueserver/piqueserver"

extra_args = sys.argv[2:]

with open('README.rst') as f:
    long_description = f.read()

# load version info from the piqueserver module manually
here = os.path.abspath(os.path.dirname(__file__))
version = {}
with open(os.path.join(here, 'piqueserver/version.py')) as f:
    exec(f.read(), version)

ext_modules = []

ext_names = [
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

linetrace = os.environ.get('CYTHON_TRACE') == '1'

for name in ext_names:
    if static:
        extra = {'extra_link_args': ['-static-libstdc++', '-static-libgcc']}
    else:
        extra = {}

    if name in ['pyspades.vxl', 'pyspades.world', 'pyspades.mapmaker']:
        extra["extra_compile_args"] = ['-std=c++11']

        if sys.platform == "win32":
            # Python aparently redifines hypot to _hypot. This fixes that.
            extra["extra_compile_args"].extend(['-include', 'cmath'])

    extra['define_macros'] = []

    if sys.platform == "win32":
        # nobody is using 32-bit in 2017. right? right? please
        extra["define_macros"].append(("MS_WIN64", None))

    if linetrace:
        extra['define_macros'].append(('CYTHON_TRACE', '1'))

    ext_modules.append(Extension(name, ['./%s.pyx' % name.replace('.', '/')],
                                 language='c++', include_dirs=['./pyspades'], **extra))


class build_ext(_build_ext):

    def run(self):

        from Cython.Build import cythonize

        compiler_directives = {}
        if linetrace:
            compiler_directives['linetrace'] = True

        self.extensions = cythonize(self.extensions, compiler_directives=compiler_directives)

        _build_ext.run(self)

        run_setup(os.path.join(os.getcwd(), "setup.py"),
                  ['build_py'] + extra_args)


setup(
    name=PKG_NAME,
    packages=[PKG_NAME, '%s.web' % PKG_NAME,
        '%s.scripts' % PKG_NAME, '%s.game_modes' % PKG_NAME,
        '%s.core_commands' % PKG_NAME, 'pyspades'],
    version=version['__version__'],
    description='Open-Source server implementation for Ace of Spades ',
    author=('Originally MatPow2 and PySnip contributors,'
            'now, StackOverflow and piqueserver authors'),
    author_email='nate.shoffner@gmail.com',
    maintainer='noway421',
    maintainer_email='noway@2ch.hk',
    license='GNU General Public License v3',
    long_description=long_description,
    url=PKG_URL,
    keywords=['ace of spades', 'aos', 'server',
              'pyspades', 'pysnip', 'piqueserver'],
    classifiers=[
        'Intended Audience :: System Administrators',
        'Development Status :: 5 - Production/Stable',
        'Operating System :: MacOS :: MacOS X',
        'Operating System :: Unix',
        'Operating System :: Microsoft :: Windows',
        'Environment :: Console',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Programming Language :: Python',
        'Programming Language :: Cython',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 3',
        'Framework :: Twisted',
        'Topic :: Games/Entertainment',
        'Topic :: Games/Entertainment :: First Person Shooters',
    ],
    platforms="Darwin, Unix, Win32",

    setup_requires=['Cython>=0.27,<1'],
    install_requires=[
        'Cython>=0.27,<1',
        'Twisted[tls]>=17,<18',
        'Jinja2>=2,<3',  # status server is part of our 'vanilla' package
        'Pillow>=4.3.0,<5',
        'pyenet',
        'ipaddress',
        'toml',
        'six'
    ],
    extras_require={
        'from': ['pygeoip>=0.3.2,<0.4'],
        # 'statusserver': ['Jinja2>=2.8,<2.9', 'Pillow>=3.4.2,<3.5'],
        'ssh': [
            'cryptography>=2.1.4,<2.2',
            'pyasn1>=0.4.2,<0.5'
        ]
    },
    entry_points={
        'console_scripts': [
            '%s=%s.run:main' % (PKG_NAME, PKG_NAME)
        ],
    },
    package_dir={
        PKG_NAME: 'piqueserver',
        '%s.core_commands' % PKG_NAME: 'piqueserver/core_commands',
        '%s.web' % PKG_NAME: 'piqueserver/web',
        '%s.scripts' % PKG_NAME: 'piqueserver/scripts',
        '%s.game_modes' % PKG_NAME: 'piqueserver/game_modes',
        'pyspades': 'pyspades',
    },  # some kind of find_packages?
    package_data={"%s.web" % PKG_NAME: ["templates/status.html"]},
    include_package_data=True,

    ext_modules=ext_modules,
    cmdclass={'build_ext': build_ext},
)
