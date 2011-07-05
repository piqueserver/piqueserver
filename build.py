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

setup(
    name = 'pyspades extensions',
    ext_modules = cythonize(ext_modules)
)