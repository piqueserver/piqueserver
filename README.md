
<img src="doc/logo.png" align="right" width="200px" alt="logo">

# piqueserver [![Build Status](https://travis-ci.org/piqueserver/piqueserver.svg?branch=master)](https://travis-ci.org/piqueserver/piqueserver) [![Join the chat at https://gitter.im/piqueserver/piqueserver](https://badges.gitter.im/piqueserver/piqueserver.svg)](https://gitter.im/piqueserver/piqueserver?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge&utm_content=badge)

An Ace of Spades 0.75 server based on [PySnip](https://github.com/NateShoffner/PySnip).

## :rocket: Installation

Install with pip:

```bash
pip install piqueserver
```

or from git:

```bash
git clone https://github.com/piqueserver/piqueserver
virtualenv2 venv
source venv/bin/activate
pip install -r requirements.txt
python setup.py install
```

Then copy the default configuration as a base to work off

```bash
piqueserver --copy-config
```

A-a-and lift off!

```bash
piqueserver
```

### Custom config location

If you wish to use a different location to `~/.config/piqueserver/` for config files, specify a directory with the `-d`
flag:

```bash
piqueserver --copy-config -d custom_dir
piqueserver -d custom_dir
```


## :speech_balloon: FAQ

#### What's the purpose?


 The purpose of this repo is to be a continuation of PySnip.


#### What if PySnip development returns?

Then they would merge our changes and development would be continued
there, I guess. The important thing is to keep AoS servers alive.


#### How long will it take for the first release?

March 2017 probably.


#### Why should I use piqueserver instead of PySnip/PySpades?

 * Multi config installation
 * Docker support
 * Bug fixes
 * Improvements
 * Better anti-hacking
 * New scripts

#### What about 0.76 support

 Working with multiple versions is a pain. 0.76 will be suported in the
 future only.

#### Is that everything?

 Please see also the [original README](https://github.com/piqueserver/piqueserver/blob/master/OLD_README.md) from PySnip and
 the [Wiki](https://github.com/piqueserver/piqueserver/wiki) for more information.

## :blush: Contribute

Don't be shy and submit us a PR or an issue! Help is always appreciated

## :wrench: Development

Use `pip` and `virtualenv` to setup the development environment:

```bash
$ virtualenv -p python2 venv && . ./venv/bin/activate
(venv) $ pip install -r requirements.txt
(venv) $ ./setup.py install
(venv) $ deactivate # Deactivate virtualenv
```
-------
Brought to you with :heart: by the [piqueserver team](https://github.com/orgs/piqueserver/people).
