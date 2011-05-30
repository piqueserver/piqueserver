from distutils.core import setup
import py2exe

# just so we always get commands.py first, not the stdlib commands.py
import sys
sys.path.insert(0, '../feature_server')

setup(
    console = ['../feature_server/run.py'],
    options = {
        'py2exe' : {
            'includes' : ['zope.interface', 'twisted.web.resource'],
            'packages' : ['pyspades', 'win32com']
        }}
)