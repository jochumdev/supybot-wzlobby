###
# Copyright (C) 2011  Warzone 2100 Project
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

import supybot.utils as utils
from supybot.commands import *
import supybot.conf as conf
import supybot.plugins as plugins
import supybot.ircdb as ircdb
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks

# To notify all channels.
import supybot.world as world
import supybot.ircmsgs as ircmsgs

import struct
from supybot.drivers.Twisted import reactor
from twisted.internet.task import LoopingCall

from socketrpc.twisted_srpc import SocketRPCClient, set_serializer

set_serializer("jsonlib")

class LobbyClient(SocketRPCClient):
    def __init__(self, user, password):
        self._user = user
        self._password = password
        
    def clientConnectionMade(self, factory):
        SocketRPCClient.clientConnectionMade(self, factory)

        # Send the version command first.
        self.remote.transport.write(struct.pack("!8sI", "version", 4))
        
        # now login
        self.call("login", username=self._user, password=self._password)

class WZLobby(callbacks.Plugin):
    def __init__(self, irc):
        callbacks.Plugin.__init__(self, irc)

        host = self.registryValue('lobby_address')
        port = self.registryValue('lobby_port')

        self._client = LobbyClient(self.registryValue('lobby_user'), self.registryValue('lobby_password'))
        self._connector = reactor.connectTCP(host, port, self._client)

        self._lCall = LoopingCall(self._update)
        self._lCall.start(int(self.registryValue('lobby_interval')))

        self._lastnotified = set()
        self._games = []

    def _update(self):
        def checkAndNotify(games):
            newKeys = set(["%s&%s&%s" % (game['description'], game['mapname'], game['hostplayer']) for game in games])

            if self._lastnotified ^ newKeys:
                self._lastnotified = newKeys
                self._games = games

                text = self._format_games(self._games)
                # Iterator over all networks
                for irc in world.ircs:
                    # Now over all its channels we are in.
                    for channel in irc.state.channels:
                        if not self.registryValue('notify', channel):
                            continue

                        msg = ircmsgs.privmsg(channel, text)
                        if channel in irc.state.channels:
                            irc.queueMsg(msg)

        self._client.call("list").addCallback(checkAndNotify)

    def games(self, irc, msg, args):
        irc.reply(self._format_games(self._games))

    def notifications(self, irc, msg, args, channel, state):
        if not ircdb.checkCapability(msg.prefix, "admin"):
            irc.reply("Sorry, you'r not allowed to do so.")
            return

        if state:
            self.setRegistryValue('notify', True, channel)
            irc.reply("Will send notifications to %s in the future" % channel)
        else:
            self.setRegistryValue('notify', False, channel)
            irc.reply("Will not send notifications to %s in the future" % channel)

    notifications = wrap(notifications, ['inChannel', optional('boolean')])

    def _format_games(self, games):
        if not games:
            return "No games in the lobby"

        games = [self._format_game(game) for game in games]

        if len(games) == 1:
            return unicode("1 game: %s" % games[0]).encode('utf-8')
        else:
            return unicode("%i games: %s" % (len(games), ", ".join(games))).encode('utf-8')

    def _format_game(self, game):
        private = ''
        if game["isPrivate"]:
            private = 'private, '

        detail = ''
        if game["mapname"]:
            if game["mapname"][3:].lower() == "sk-":
                detail = ' (%s by %s)' % (game["mapname"][3:], game["hostplayer"])
            else:
                detail = ' (%s by %s)' % (game["mapname"], game["hostplayer"])

        return "\x02%s\x02%s [%i/%i] (%sversion: %s)" % (game["description"],
                                               detail,
                                               game["currentPlayers"],
                                               game["maxPlayers"],
                                               private,
                                               game["multiVer"])

    def die(self):
        self._connector.disconnect()
        self._lCall.stop()


Class = WZLobby


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
