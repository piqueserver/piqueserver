import sys
from distutils.core import setup
from distutils.extension import Extension
from Cython.Distutils import build_ext
from Cython.Build import cythonize

ext_modules = []

names = [
    'pyspades.compression',
    'pyspades.load',
    'pyspades.compressedvxl',
    'pyspades.bytes',
    'pyspades.packet',
    'pyspades.loaders',
    'pyspades.serverloaders',
    'pyspades.clientloaders'
]

for name in names:
    ext_modules.append(Extension(name, ['./%s.pyx' % name.replace('.', '/')],
        language = 'c++'))

if False:
    extra_link_args = []
    opengl_libraries = []
    if sys.platform == 'win32':
        opengl_libraries.append('opengl32')
    elif sys.platform == 'linux2':
        opengl_libraries.append('GL')
    elif sys.platform == 'darwin':
        extra_link_args.extend(['-framework', 'OpenGL'])

    ext_modules.append(Extension('experimental.render', 
        ['./experimental/render.pyx'], language = 'c++', 
        extra_link_args = extra_link_args, libraries = opengl_libraries,
        include_dirs = ['./pyspades', './experimental']))

setup(
    name = 'pyspades extensions',
    ext_modules = cythonize(ext_modules)
)