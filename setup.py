#!/usr/bin/env python2

from __future__ import print_function

import sys
import os
from distutils.core import run_setup
# build_ext is subclassed, so we import it with a _ to avoid a collision
from distutils.command.build_ext import build_ext as _build_ext
from setuptools import setup, Extension


PKG_NAME = "piqueserver"
PKG_URL = "https://github.com/piqueserver/piqueserver"
PKG_DOWNLOAD_URL = "https://github.com/piqueserver/piqueserver/archive/0.1.0.zip"

extra_args = sys.argv[2:]

try:
    import pypandoc
    import re
    long_description = pypandoc.convert_text(
        re.sub(r'[^\x00-\x7F]+', ' ',
               pypandoc.convert('README.md', 'markdown', format="markdown_github")), 'rst', format="markdown")
except (IOError, ImportError):
    long_description = ''


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
    version='0.1.0_post2',
    description='Open-Source server implementation for Ace of Spades ',
    author=('Originally MatPow2 and PySnip contributors,'
            'now, StackOverflow and piqueserver authors'),
    author_email='nate.shoffner@gmail.com',
    maintainer='noway421',
    maintainer_email='noway@2ch.hk',
    license='GNU General Public License v3',
    long_description=long_description,
    url=PKG_URL,
    download_url=PKG_DOWNLOAD_URL,
    keywords=['ace of spades', 'aos', 'server',
              'pyspades', 'pysnip', 'piqueserver'],
    classifiers=[
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
    platforms="Darwin, Unix",

    setup_requires=['Cython>=0,<1'],
    install_requires=[
        'Cython>=0,<1',
        'Twisted>=17',
        'Jinja2>=2,<3',  # status server is part of our 'vanilla' package
        'Pillow>=3,<5',
        'pyenet',
        'ipaddress'
    ],
    extras_require={
        'from': ['pygeoip>=0.3.2,<0.4'],
        # 'statusserver': ['Jinja2>=2.8,<2.9', 'Pillow>=3.4.2,<3.5'],
        'ssh': [
            'pycrypto>=2.6.1,<2.7',
            'cryptography>=2.0.0,<3.0',
            'pyasn1>=0.1.9,<0.2'
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
