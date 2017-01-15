#!/usr/bin/env python
import subprocess
import tarfile
import shutil
import os
try:
  import urllib as urllib_request
except ImportError:
  import urllib.request as urllib_request

lib_version = "1.3.13"
enet_dir = "enet-%s" % lib_version
enet_file = "%s.tar.gz" % enet_dir
enet_url = "http://enet.bespin.org/download/%s" % enet_file

if os.path.isfile("pyenet/enet-pyspades.pyx"):
	os.remove("pyenet/enet-pyspades.pyx")
if os.path.isfile("pyenet/enet.so"):
	os.remove("pyenet/enet.so")
if os.path.isdir("pyenet/enet"):
	shutil.rmtree("pyenet/enet")

shutil.copyfile("pyenet/enet.pyx", "pyenet/enet-pyspades.pyx")
subprocess.Popen(['patch', '-p1', 'pyenet/enet-pyspades.pyx', 'pyspades-pyenet.patch']).communicate()

urllib_request.urlretrieve(enet_url, enet_file)

tar = tarfile.open(enet_file)
tar.extractall()
tar.close()

shutil.move(enet_dir, "pyenet/enet")
shutil.copyfile("__init__.py-tpl", "pyenet/__init__.py")
