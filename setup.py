import os
from typing import Dict, List, NamedTuple
from setuptools import setup, Extension, find_packages
from Cython.Build import cythonize
from Cython.Compiler import Options

class Descriptor(NamedTuple):
    extension_name: str
    sources: List[str]
    compile_flags: List[str] = []
    link_flags: List[str] = []
    macros: Dict[str, str] = {}

use_static = (os.environ.get('STDCPP_STATIC') == '1')
use_asan = (os.environ.get('USE_ASAN') == '1')
use_ubsan = (os.environ.get('USE_UBSAN') == '1')
use_linetrace = (os.environ.get('CYTHON_TRACE') == '1')

compile_flags: List[str] = []
link_flags: List[str] = []
macros: Dict[str, str] = {}

if use_static:
    link_flags += ['-static-libstdc++', '-static-libgcc']

# Compile the server with AddressSanitizer
if use_asan:
    link_flags += ['-lasan']
    compile_flags += ['-fsanitize=address']

# Compile the server with UndefinedBehaviourSanitizer
if use_ubsan:
    link_flags += ['-lubsan']
    compile_flags += ['-fsanitize=undefined']

if use_linetrace:
    macros['CYTHON_TRACE'] = '1'
    Options.generate_cleanup_code = True

extension_descriptors = [
    Descriptor('pyspades.world',
               sources=['pyspades/world.pyx'],
               compile_flags=['-std=c++11']),

    Descriptor('pyspades.mapmaker',
               sources=['pyspades/mapmaker.pyx'],
               compile_flags=['-std=c++11']),

    Descriptor('pyspades.bytes',
               sources=['pyspades/bytes.pyx']),

    Descriptor('pyspades.common',
               sources=['pyspades/common.pyx']),

    Descriptor('pyspades.contained',
               sources=['pyspades/contained.pyx']),

    Descriptor('pyspades.loaders',
               sources=['pyspades/loaders.pyx']),

    Descriptor('pyspades.packet',
               sources=['pyspades/packet.pyx']),

    Descriptor('pyspades.vxl',
               sources=['pyspades/vxl.pyx']),
]

extensions: List[Extension] = []
for descriptor in extension_descriptors:
    extension = Extension(
        name=descriptor.extension_name,
        sources=descriptor.sources,
        language='c++',
        include_dirs=['pyspades/'],
        define_macros=list({**macros, **descriptor.macros}.items()),
        extra_link_args=[*link_flags, *descriptor.link_flags],
        extra_compile_args=[*compile_flags, *descriptor.compile_flags],
    )

    extensions += [extension]

setup(
    packages=find_packages(exclude=('tests', 'tests.*')),
    ext_modules=cythonize(
        extensions,
        compiler_directives={
            'language_level': 3,
            'embedsignature': True,
        }
    ),
)
