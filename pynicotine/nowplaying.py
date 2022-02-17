# COPYRIGHT (C) 2020-2022 Nicotine+ Team
# COPYRIGHT (C) 2016-2017 Michael Labouebe <gfarmerfr@free.fr>
# COPYRIGHT (C) 2008-2011 Quinox <quinox@users.sf.net>
# COPYRIGHT (C) 2008 Gallows <g4ll0ws@gmail.com>
# COPYRIGHT (C) 2006-2009 Daelstorm <daelstorm@gmail.com>
#
# GNU GENERAL PUBLIC LICENSE
#    Version 3, 29 June 2007
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import json

from pynicotine.logfacility import log
from pynicotine.utils import execute_command
from pynicotine.utils import http_request
from pynicotine.utils import human_length


class NowPlaying:
    """ This class contains code for retrieving information about the song currently
    playing in a media player """

    def __init__(self, config):

        self.config = config
        self.bus = None
        self.title_clear()

    def title_clear(self):
        self.title = {
            "title": "",
            "artist": "",
            "comment": "",
            "year": "",
            "album": "",
            "track": "",
            "length": "",
            "nowplaying": "",
            "bitrate": "",
            "filename": ""
        }

    def display_now_playing(self, _obj=None, callback=None, get_player=None, get_command=None, get_format=None):

        self.get_np(callback, get_player, get_command, get_format)

    def get_np(self, callback=None, get_player=None, get_command=None, get_format=None):

        self.title_clear()

        if get_player is None:
            player = self.config.sections["players"]["npplayer"]
        else:
            player = get_player()

        if get_command is None:
            command = self.config.sections["players"]["npothercommand"]
        else:
            command = get_command()

        result = None

        if player == "lastfm":
            result = self.lastfm(command)

        elif player == "listenbrainz":
            result = self.listenbrainz(command)

        elif player == "other":
            result = self.other(command)

        elif player == "mpris":
            result = self.mpris(command)

        if not result:
            return None

        # Since we need unicode instead of bytes we'll try to force such a
        # conversion. Individual player commands should have done this already
        # - this is a failsafe.

        for key, value in self.title.items():
            try:
                self.title[key] = str(value, "utf-8", "replace")
            except TypeError:
                self.title[key] = value  # already unicode

        if get_format is None:
            title = self.config.sections["players"]["npformat"]
        else:
            title = get_format()

        title = title.replace("%", "%%")  # Escaping user supplied % symbols
        title = title.replace("$t", "%(title)s")
        title = title.replace("$a", "%(artist)s")
        title = title.replace("$b", "%(album)s")
        title = title.replace("$c", "%(comment)s")
        title = title.replace("$n", "%(nowplaying)s")
        title = title.replace("$k", "%(track)s")
        title = title.replace("$l", "%(length)s")
        title = title.replace("$y", "%(year)s")
        title = title.replace("$r", "%(bitrate)s")
        title = title.replace("$f", "%(filename)s")
        title = title.replace("$p", "%(program)s")

        title = title % self.title
        title = ' '.join(x for x in title.replace('\r', '\n').split('\n') if x)

        if title:
            if callback:
                callback(title)

            return title

        return None

    def lastfm(self, user):
        """ Function to get the last song played via Last.fm API """

        try:
            user, apikey = user.split(';')

        except ValueError:
            log.add_important_error(_("Last.fm: Please provide both your Last.fm username and API key"))
            return None

        try:
            response = http_request(
                "https", "ws.audioscrobbler.com",
                "/2.0/?method=user.getrecenttracks&user=" + user + "&api_key=" + apikey + "&limit=1&format=json",
                headers={"User-Agent": self.config.application_name})

        except Exception as error:
            log.add_important_error(_("Last.fm: Could not connect to Audioscrobbler: %(error)s"), {"error": error})
            return None

        try:
            json_api = json.loads(response)
            lastplayed = json_api["recenttracks"]["track"]

            try:
                # In most cases, a list containing a single track dictionary is sent
                lastplayed = lastplayed[0]

            except KeyError:
                # On rare occasions, the track dictionary is not wrapped in a list
                pass

            self.title["artist"] = lastplayed["artist"]["#text"]
            self.title["title"] = lastplayed["name"]
            self.title["album"] = lastplayed["album"]["#text"]
            self.title["nowplaying"] = "%s: %s - %s - %s" % (
                _("Last played"), self.title["artist"], self.title["album"], self.title["title"])

        except Exception:
            log.add_important_error(_("Last.fm: Could not get recent track from Audioscrobbler: %(error)s"),
                                    {"error": response})
            return None

        return True

    def mpris(self, player):
        """ Function to get the currently playing song via DBus MPRIS v2 interface """

        # https://media.readthedocs.org/pdf/mpris2/latest/mpris2.pdf

        from gi.repository import Gio  # pylint: disable=import-error
        self.bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)

        dbus_mpris_service = 'org.mpris.MediaPlayer2.'
        dbus_mpris_player_service = 'org.mpris.MediaPlayer2.Player'
        dbus_mpris_path = '/org/mpris/MediaPlayer2'
        dbus_property = 'org.freedesktop.DBus.Properties'

        if not player:
            dbus_proxy = Gio.DBusProxy.new_sync(
                self.bus, Gio.DBusProxyFlags.NONE, None,
                'org.freedesktop.DBus', '/org/freedesktop/DBus', 'org.freedesktop.DBus', None
            )

            names = dbus_proxy.ListNames()
            players = []

            for name in names:
                if name.startswith(dbus_mpris_service):
                    players.append(name[len(dbus_mpris_service):])

            if not players:
                log.add_important_error(_("MPRIS: Could not find a suitable MPRIS player"))
                return None

            player = players[0]
            if len(players) > 1:
                log.add(_("Found multiple MPRIS players: %(players)s. Using: %(player)s"),
                        {'players': players, 'player': player})
            else:
                log.add(_("Auto-detected MPRIS player: %s"), player)

        try:
            dbus_proxy = Gio.DBusProxy.new_sync(
                self.bus, Gio.DBusProxyFlags.NONE, None,
                dbus_mpris_service + player, dbus_mpris_path, dbus_property, None
            )

            metadata = dbus_proxy.Get('(ss)', dbus_mpris_player_service, 'Metadata')

        except Exception as error:
            log.add_important_error(_("MPRIS: Something went wrong while querying %(player)s: %(exception)s"),
                                    {'player': player, 'exception': error})
            return None

        self.title['program'] = player
        list_mapping = [('xesam:artist', 'artist')]

        for source, dest in list_mapping:
            try:
                self.title[dest] = '+'.join(metadata[source])
            except KeyError:
                self.title[dest] = '?'

        mapping = [
            ('xesam:title', 'title'),
            ('xesam:album', 'album'),
            ('xesam:contentCreated', 'year'),
            ('xesam:comment', 'comment'),
            ('xesam:audioBitrate', 'bitrate'),
            ('xesam:url', 'filename'),
            ('xesak:trackNumber', 'track')
        ]

        for source, dest in mapping:
            try:
                self.title[dest] = str(metadata[source])
            except KeyError:
                self.title[dest] = '?'

        # The length is in microseconds, and be represented as a signed 64-bit integer.
        try:
            self.title['length'] = human_length(metadata['mpris:length'] // 1000000)
        except KeyError:
            self.title['length'] = '?'

        if self.title['artist'] != "":
            self.title['nowplaying'] += self.title['artist']

        if self.title['title'] != "":
            self.title['nowplaying'] += " - " + self.title['title']

        return True

    def listenbrainz(self, username):
        """ Function to get the currently playing song via ListenBrainz API """

        if not username:
            log.add_important_error(_("ListenBrainz: Please provide your ListenBrainz username"))
            return None

        try:
            response = http_request('https', 'api.listenbrainz.org',
                                    '/1/user/{}/playing-now'.format(username),
                                    headers={'User-Agent': self.config.application_name})

        except Exception as error:
            log.add_important_error(_("ListenBrainz: Could not connect to ListenBrainz: %(error)s"), {'error': error})
            return None

        try:
            json_api = json.loads(response)['payload']

            if not json_api['playing_now']:
                log.add_important_error(_("ListenBrainz: You don\'t seem to be listening to anything right now"))
                return None

            track = json_api['listens'][0]['track_metadata']

            self.title['artist'] = track['artist_name']
            self.title['title'] = track['track_name']
            self.title['album'] = track['release_name']
            self.title['nowplaying'] = '%s: %s - %s - %s' % (
                _('Playing now'), self.title['artist'], self.title['album'], self.title['title'])

            return True

        except Exception:
            log.add_important_error(_("ListenBrainz: Could not get current track from ListenBrainz: %(error)s"),
                                    {'error': str(response)})
        return None

    def other(self, command):

        if not command:
            return None

        try:
            output = execute_command(command, returnoutput=True)
            self.title["nowplaying"] = output
            return True

        except Exception as error:
            log.add_important_error(_("Executing '%(command)s' failed: %(error)s"),
                                    {"command": command, "error": error})
            return None
