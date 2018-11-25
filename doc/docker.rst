Running Piqueserver with Docker
===============================

Image
-----

You can either use the published image on Docker Hub or build it locally.

.. code:: bash

    # using published image
    docker pull piqueserver/piqueserver:master
    # build it locally
    git clone https://github.com/piqueserver/piqueserver
    cd piqueserver
    docker build -t piqueserver/piqueserver:master .


Running
-------

Get your config ready. It should have the following structure:

.. code:: bash

    config/
    ├── config.toml
    ├── game_modes
    │   └── README.md
    ├── logs
    ├── maps
    │   ├── classicgen.txt
    │   └── random.txt
    ├── README.md
    └── scripts
        └── README.md

If you don’t have it you can grab it from the repository `here <https://github.com/piqueserver/piqueserver/tree/master/piqueserver/config>`_.
After setting up the config directory you can run piqueserver using the following command.

.. code:: bash

    # running
    docker run -d \
               -rm \
               -v /path/to/config:/config \
               -p 32887:32887/udp -p 32886:32886/tcp \
               --name mypiqueserver \
               piqueserver/piqueserver:master
    # viewing logs
    docker logs mypiqueserver
    # killing the server
    docker kill mypiqueserver

.. note::

    | ``-v`` flag only accepts absolute paths.
    | Ports 32887 and 32886 are for the game and status server respectively.
    | ``-p`` flag's syntax is as follows `host_port:container_port`
    | If you want it to run on a different port change the host_port.


Docker Compose
--------------
Sample docker-compose file. You can find the full example `here <https://github.com/piqueserver/arena>`_.

.. code:: yaml

    version: '3'
    services:
    arena:
        image: piqueserver/piqueserver:master
        volumes:
        - .:/config
        ports:
        - "8001:32887/udp" # game server
        - "8002:32886" # status server

