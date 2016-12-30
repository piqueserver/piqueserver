from distutils.core import setup
import py2exe

# just so we always get commands.py first, not the stdlib commands.py
import sys
sys.path.insert(0, '../feature_server')
sys.path.append('..')

setup(
    console = ['../feature_server/run.py'],
    zipfile = None,
    options = {
        'py2exe' : {
            'compressed' : 1,
            'optimize' : 2,
            'bundle_files' : 1,
            'dll_excludes' : ['mswsock.dll', 'powrprof.dll'],
            'includes' : ['zope.interface', 'twisted.web.resource', 'six'],
            'packages' : ['pyspades', 'win32com', 'pygeoip', 'pyasn1', 'jinja2', 'PIL']
        }}
)
