import sys
import os
from distutils.core import setup
from distutils.extension import Extension
from Cython.Distutils import build_ext
from Cython.Build import cythonize

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


setup(
    name = 'pyspades extensions',
    ext_modules = cythonize(ext_modules)
)
