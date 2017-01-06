import sys
sys.path.append('..')

import os
import shutil
import subprocess

def copy(src, dst):
    if os.path.isfile(src):
        shutil.copyfile(src, dst)
    else:
        shutil.copytree(src, dst)

def get_git_rev():
    import subprocess
    pipe = subprocess.Popen(
        ["git", "rev-parse", "HEAD"],
        stdout=subprocess.PIPE, stderr = subprocess.PIPE)
    ret = pipe.stdout.read()[:40]
    if not ret:
        return '?'
    return ret

git_rev = get_git_rev()

SERVER_FILES = ['maps', 'scripts', 'web', 'data']
COPY_FILES = {'config.txt.default' : 'config.txt'}
REMOVE_EXTENSIONS = ['txtc', 'pyc', 'saved.vxl', 'txto', 'pyo']
REMOVE_FILES = ['w9xpopen.exe', 'dummy']
PKG_NAME="piqueserver"

open('./dist/run.bat', 'wb').write('run.exe\npause\n')
open('./dist/version', 'wb').write(git_rev)

if not os.path.isfile('../feature_server/data/GeoLiteCity.dat'):
    print '(missing GeoLiteCity.dat in data folder)'

for name in SERVER_FILES:
    copy('../feature_server/%s' % name, './dist/%s' % name)

for src, dst in COPY_FILES.iteritems():
    copy('../feature_server/%s' % src, './dist/%s' % dst)

for root, sub, files in os.walk('./dist'):
    for file in files:
        path = os.path.join(root, file)
        if file in REMOVE_FILES:
            os.remove(path)
        else:
            for ext in REMOVE_EXTENSIONS:
                if file.endswith(ext):
                    os.remove(path)
                    break

filename = '%s-feature_server-%s.zip' % (PKG_NAME, git_rev)

try:
    os.remove(filename)
except OSError:
    pass

try:
    subprocess.check_call(['7z', 'a', filename, 'dist'])
except WindowsError:
    print '7zip failed - do you have the 7zip directory in PATH?'
