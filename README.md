Supybot - Warzone 2100 Lobby plugin
============

A Plugin for Supybot to query wzlobbyserver-ng

TODO
-----------
* Docs

Requirements
-----------
* Twisted >=10.1
* socketrpc >=0.0.2
* pymongo (for bson)

Installation
-----------
* clone this repository into your plugins directory

    cd <supybot>/plugins
    git git://github.com/pcdummy/supybot-wzlobby.git WZLobby

* enable it.

    irc: <yourbot>: load WZLobby

Configuration:
-----------
* enable/disable notification with:

    <yourbot>: notifications <on|off>
