Example Linux Setup with Systemd
================================

Overview
--------

These instructions will give you a flexible and secure setup for Piqueserver
that starts automatically at boot, restarts on crashes, and collects logs.

It also allows you to run as many instances as you want in parallel.

Instructions
------------

Install latest piqueserver using pip or whatever other method you like.

.. code:: bash

   # pip3 install piqueserver

Create a dedicated directory for piqueserver data. You can put this anywhere
you like. It is a good idea to put some identifier for your server, such as
``ctf`` in the folder name, in case you want to create more server configs in
the future.

.. code:: bash

   # mkdir -p /var/lib/piqueserver/servername/

We want a seperate group to be able to restrict permissions in a more
granular way

.. code:: bash

   # groupadd --system piqueserver

Optionally join your own user to the ``piqueserver`` group to be able to
edit files in the piqueserver directory freely.

.. code:: bash

   # usermod -a -G piqueserver yourusername

We want to copy the default config directory over.

.. code:: bash

   # piqueserver --copy-config -d /var/lib/piqueserver/servername

Edit a new file, ``/etc/systemd/system/piqueserver@.service`` and insert
the following contents.

.. code:: ini

   [Unit]
   Description=Piqueserver

   [Service]
   ExecStart=/usr/local/bin/piqueserver -d /var/lib/piqueserver/%i
   User=piqueserver
   Group=piqueserver
   Restart=always

   # Security Sandbox Settings
   Group=piqueserver
   DynamicUser=true
   # only allow access to the state folder, nothing else
   ProtectHome=true
   TemporaryFileSystem=/var:ro
   PrivateDevices=true
   StateDirectory=piqueserver/%i

   # disallow any unusual syscalls
   SystemCallFilter=@system-service

   [Install]
   WantedBy=network.target

You can now start, stop, and see the status of the process using
systemctl.

.. code:: bash

   # systemctl start piqueserver@servername
   # systemctl stop piqueserver@servername
   # systemctl status piqueserver@servername

You will probably want to start the server at boot. To do this, run:

.. code:: bash

   # systemctl enable piqueserver@servername

To tail the logs, run

.. code:: bash

   # journalctl -f -u piqueserver@servername
