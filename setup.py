import sys
from setuptools import setup, find_packages, Extension
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

for name in names:
    extra = {'extra_compile_args' : ['-std=c++11']} if name in ['pyspades.vxl', 'pyspades.world', 'pyspades.mapmaker'] else {}

    ext_modules.append(Extension(name, ['%s.pyx' % name.replace('.', '/')],
        language = 'c++', include_dirs=['pyspades'], **extra))


setup(
    name = 'pysnip',
    packages = ['pysnip', 'pyspades', 'pysnip.feature_server'],
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
        	'pysnip=pysnip.feature_server.run:main'
    	],
    },
    package_dir = {'pysnip': '', 'pyspades': 'pyspades'},
    ext_modules = cythonize(ext_modules)
)
