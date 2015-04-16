![PySnip](http://i.imgur.com/QFgqcRM.png)

PySnip is an robust, open-source and cross-platform server implementation for [Ace of Spades](http://buildandshoot.com). It is fully customizable with extensions and scripts.

### Features ###

* Many administrator features
* A lot of epic commands
* A remote console (using SSH)
* Map rotation
* Map metadata (name, version, author, and map configuration)
* Map extensions (water damage, etc.)
* A map generator
* An IRC client for managing your server
* A JSON query webserver
* A status server with map overview
* Server/map scripts
* Airstrikes
* Melee attacks with the pickaxe
* New gamemodes (deathmatch / runningman)
* Rollback feature (rolling back to the original map)
* Spectator mode
* Dirt grenades
* Platforms with buttons
* Ban subscribe service
* A ton of other features 

### Installing ###
#### For windows ####
Go to [releases](https://github.com/NateShoffner/PySnip/releases) and download desired version.

#### For linux ####
Grab it from repo.
```bash
git clone https://github.com/NateShoffner/PySnip
cd PySnip
```
Create virtualenv
```bash
virtualenv -p python2 venv
source ./venv/bin/activate
```
Install dependencies
```bash
pip install cython twisted jinja2 pillow pygeoip pycrypto pyasn1
```
Compile
```bash
./build.sh
```
Run
```bash
./run_server.sh
```

### Support ###

Feel free to post a question on the [forums](http://buildandshoot.com/viewforum.php?f=19) if you need any help or hop onto [IRC](http://webchat.quakenet.org/?channels=%23buildandshoot) to to chat.
