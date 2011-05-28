from distutils.core import setup
import py2exe

setup(
    console = ['../feature_server/run.py'],
    options = {
        'py2exe' : {
            'includes' : ['zope.interface', 'twisted.web.resource'],
            'packages' : ['pyspades', 'win32com']
        }}
)