from distutils.core import setup
from distutils.extension import Extension
from Cython.Distutils import build_ext
from Cython.Build import cythonize

ext_modules = []

names = [
    'pyspades.compression',
    'pyspades.load'
]

for name in names:
    ext_modules.append(Extension(name, ['./%s.pyx' % name.replace('.', '/')],
        language = 'c++'))

setup(
    name = 'pyspade extensions',
    ext_modules = cythonize(ext_modules)
)