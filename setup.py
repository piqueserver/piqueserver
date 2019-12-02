#!/usr/bin/env python3

import sys
import os
from distutils.core import run_setup
# build_ext is subclassed, so we import it with a _ to avoid a collision
from distutils.command.build_ext import build_ext as _build_ext
from setuptools import setup, Extension, find_packages


PKG_NAME = "piqueserver"

extra_args = sys.argv[2:]

with open('README.rst') as f:
    long_description = f.read()

# load version info from the piqueserver module manually
here = os.path.abspath(os.path.dirname(__file__))
version = {}
with open(os.path.join(here, 'piqueserver/version.py')) as f:
    exec(f.read(), version)

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

# Compile the server with support for
# AddressSanitizer/UndefinedBehaviourSanitizer
USE_ASAN = os.environ.get('USE_ASAN') == '1'
USE_UBSAN = os.environ.get('USE_UBSAN') == '1'

ext_modules = []

for name in ext_names:
    extra = {
        "define_macros": [],
        "extra_link_args": [],
        "extra_compile_args": [],
    }  # type: dict

    if static:
        extra['extra_link_args'].extend(
            ['-static-libstdc++', '-static-libgcc'])

    if USE_ASAN:
        extra["extra_link_args"].append("-lasan")
        extra["extra_compile_args"].append("-fsanitize=address")

    if USE_UBSAN:
        extra["extra_link_args"].append("-lubsan")
        extra["extra_compile_args"].append("-fsanitize=undefined")

    if name in ['pyspades.vxl', 'pyspades.world', 'pyspades.mapmaker']:
        extra["extra_compile_args"].append('-std=c++11')

    if linetrace:
        extra['define_macros'].append(('CYTHON_TRACE', '1'))

    ext_modules.append(Extension(name, ['./%s.pyx' % name.replace('.', '/')],
                                 language='c++', include_dirs=['./pyspades'],
                                 **extra))


class build_ext(_build_ext):

    def run(self):

        from Cython.Build import cythonize

        if USE_ASAN:
            from Cython.Compiler import Options
            # make asan/valgrind's memory leak results better
            Options.generate_cleanup_code = True

        compiler_directives = {'language_level': 3, 'embedsignature': True}
        if linetrace:
            compiler_directives['linetrace'] = True

        self.extensions = cythonize(self.extensions, compiler_directives=compiler_directives)

        _build_ext.run(self)

        run_setup(os.path.join(os.getcwd(), "setup.py"),
                  ['build_py'] + extra_args)


setup(
    name=PKG_NAME,
    packages=find_packages(exclude=("tests", "tests.*")),
    version=version['__version__'],
    description='Open-Source server implementation for Ace of Spades ',
    author=('Originally MatPow2 and PySnip contributors,'
            'now, StackOverflow and piqueserver authors'),
    author_email='nate.shoffner@gmail.com',
    maintainer='noway421',
    maintainer_email='noway@2ch.hk',
    license='GNU General Public License v3',
    long_description=long_description,
    long_description_content_type="text/x-rst",
    url="https://github.com/piqueserver/piqueserver",
    keywords=['ace of spades', 'aos', 'server',
              'pyspades', 'pysnip', 'piqueserver'],
    python_requires=">=3.5.3",
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
        'Programming Language :: Python :: 3',
        'Framework :: Twisted',
        'Topic :: Games/Entertainment',
        'Topic :: Games/Entertainment :: First Person Shooters',
    ],
    platforms="Darwin, Unix, Win32",

    setup_requires=['Cython>=0.27,<1'],
    install_requires=[
        'pypiwin32;platform_system=="Windows"',
        'Cython>=0.27,<1',
        'Twisted[tls]',
        'Jinja2>=2,<3',
        'Pillow>=5.1.0,<7',
        'aiohttp>=3.3.0,<3.7.0',
        'pyenet',
        'toml',
        'packaging>=19.0'
    ],
    extras_require={
        'from': ['geoip2>=2.9,<3.0'],
        'ssh': ['Twisted[tls,conch]'],
    },
    entry_points={
        'console_scripts': [
            '%s=%s.run:main' % (PKG_NAME, PKG_NAME)
        ],
    },
    package_data={"%s.web" % PKG_NAME: ["templates/status.html"]},
    include_package_data=True,

    ext_modules=ext_modules,
    cmdclass={'build_ext': build_ext},
)
