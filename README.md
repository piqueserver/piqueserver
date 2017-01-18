# :spades: :cloud: piqueserver [![Build Status](https://travis-ci.org/piqueserver/piqueserver.svg?branch=master)](https://travis-ci.org/piqueserver/piqueserver) [![Join the chat at https://gitter.im/piqueserver/piqueserver](https://badges.gitter.im/piqueserver/piqueserver.svg)](https://gitter.im/piqueserver/piqueserver?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge&utm_content=badge)

An Ace of Spades 0.75 server based on [PySnip](https://github.com/NateShoffner/PySnip).

## :rocket: Installation
Clone the repo to get example config files:
```bash
git clone https://github.com/piqueserver/piqueserver
```
Then install using pip:
```bash
pip install piqueserver
```
A-a-and lift off! 
```bash
piqueserver -d ./piqueserver/configs
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

Use virtualenv to install it

```bash
virtualenv -p python2 venv && . venv/bin/activate && pip install -r requirements.txt
./setup.py install
```
-------
Brought to you with :heart: by the [piqueserver team](https://github.com/orgs/piqueserver/people).
