from distutils.core import setup
import py2exe

# just so we always get commands.py first, not the stdlib commands.py
import sys
sys.path.append('..')

setup(
    console = ['../tools/editor/run.py'],
    zipfile = None,
    options = {
        'py2exe' : {
            'compressed' : 1,
            'optimize' : 2,
            'bundle_files' : 1,
            'packages' : ['pyspades', 'win32com']
        }}
)