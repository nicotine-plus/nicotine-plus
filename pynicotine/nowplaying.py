# SPDX-FileCopyrightText: 2020-2025 Nicotine+ Contributors
# SPDX-FileCopyrightText: 2016-2017 Michael Labouebe <gfarmerfr@free.fr>
# SPDX-FileCopyrightText: 2008-2011 quinox <quinox@users.sf.net>
# SPDX-FileCopyrightText: 2008 gallows <g4ll0ws@gmail.com>
# SPDX-FileCopyrightText: 2006-2009 daelstorm <daelstorm@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later

import json
import os
import sys

from pynicotine.config import config
from pynicotine.logfacility import log
from pynicotine.utils import execute_command
from pynicotine.utils import human_length


class AudioscrobblerError(Exception):
    pass


class NowPlaying:
    """This class contains code for retrieving information about the song
    currently playing in a media player."""

    __slots__ = ("title",)

    def __init__(self):
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
            player = config.sections["players"]["npplayer"]

            if player == "mpris" and (sys.platform in {"win32", "darwin"} or "SNAP_NAME" in os.environ):
                player = "lastfm"
        else:
            player = get_player()

        if get_command is None:
            command = config.sections["players"]["npothercommand"]
        else:
            command = get_command()

        result = None

        if player == "lastfm":
            result = self._lastfm(command)

        elif player == "librefm":
            result = self._librefm(command)

        elif player == "listenbrainz":
            result = self._listenbrainz(command)

        elif player == "other":
            result = self._other(command)

        elif player == "mpris":
            result = self._mpris(command)

        if not result:
            return None

        if get_format is None:
            title = config.sections["players"]["npformat"]
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

        title %= self.title
        title = " ".join(x for x in title.replace("\r", "\n").split("\n") if x)

        if title:
            if callback:
                callback(title)

            return title

        return None

    def _parse_audioscrobbler_response(self, response_body):

        json_response = json.loads(response_body)

        if "error" in json_response:
            code = json_response["error"].get("code")
            message = json_response["error"].get("#text")

            raise AudioscrobblerError(f"{message} (error code {code})")

        last_played = json_response["recenttracks"]["track"]

        try:
            # In most cases, a list containing a single track dictionary is sent
            last_played = last_played[0]

        except KeyError:
            # On rare occasions, the track dictionary is not wrapped in a list
            pass

        self.title["artist"] = artist = last_played.get("artist", {}).get("#text") or "?"
        self.title["title"] = title = last_played.get("name") or "?"
        self.title["album"] = last_played.get("album", {}).get("#text") or "?"
        self.title["nowplaying"] = f"{artist} - {title}"

    def _lastfm(self, username):
        """Function to get the last song played via Last.fm API."""

        try:
            username, apikey = username.split(";")

        except ValueError:
            log.add(_("Last.fm: Please provide both your Last.fm username and API key"), title=_("Now Playing Error"))
            return None

        try:
            from urllib.request import urlopen
            with urlopen((f"https://ws.audioscrobbler.com/2.0/?method=user.getrecenttracks&user={username}"
                          f"&api_key={apikey}&limit=1&format=json"), timeout=10) as response:
                response_body = response.read().decode("utf-8", "replace")

        except Exception as error:
            log.add(_("Last.fm: Could not connect to Audioscrobbler: %(error)s"), {"error": error},
                    title=_("Now Playing Error"))
            return None

        try:
            self._parse_audioscrobbler_response(response_body)

        except Exception as error:
            log.add(_("Last.fm: Could not get recent track from Audioscrobbler: %(error)s"),
                    {"error": error}, title=_("Now Playing Error"))
            return None

        return True

    def _librefm(self, username):
        """Function to get the last song played via Libre.fm API."""

        try:
            from urllib.request import urlopen
            with urlopen((f"https://libre.fm/2.0/?method=user.getrecenttracks&user={username}"
                          f"&limit=1&format=json"), timeout=10) as response:
                response_body = response.read().decode("utf-8", "replace")

        except Exception as error:
            log.add(_("Libre.fm: Could not connect to Libre.fm: %(error)s"), {"error": error},
                    title=_("Now Playing Error"))
            return None

        try:
            self._parse_audioscrobbler_response(response_body)

        except Exception as error:
            log.add(_("Libre.fm: Could not get recent track: %(error)s"),
                    {"error": error}, title=_("Now Playing Error"))
            return None

        return True

    def _mpris(self, player):
        """Function to get the currently playing song via DBus MPRIS v2
        interface."""

        # https://media.readthedocs.org/pdf/mpris2/latest/mpris2.pdf

        from gi.repository import Gio  # pylint: disable=import-error

        dbus_mpris_service = "org.mpris.MediaPlayer2."

        if not player:
            dbus_proxy = Gio.DBusProxy.new_for_bus_sync(
                bus_type=Gio.BusType.SESSION,
                flags=0,
                info=None,
                name="org.freedesktop.DBus",
                object_path="/org/freedesktop/DBus",
                interface_name="org.freedesktop.DBus",
                cancellable=None
            )
            names = dbus_proxy.ListNames()
            players = []

            for name in names:
                if name.startswith(dbus_mpris_service):
                    players.append(name[len(dbus_mpris_service):])

            if not players:
                log.add(_("MPRIS: Could not find a suitable MPRIS player"), title=_("Now Playing Error"))
                return None

            player = players[0]
            if len(players) > 1:
                log.add(_("Found multiple MPRIS players: %(players)s. Using: %(player)s"),
                        {"players": players, "player": player})
            else:
                log.add(_("Auto-detected MPRIS player: %s"), player)

        try:
            dbus_proxy = Gio.DBusProxy.new_for_bus_sync(
                bus_type=Gio.BusType.SESSION,
                flags=0,
                info=None,
                name=dbus_mpris_service + player,
                object_path="/org/mpris/MediaPlayer2",
                interface_name="org.freedesktop.DBus.Properties",
                cancellable=None
            )
            metadata = dbus_proxy.Get("(ss)", "org.mpris.MediaPlayer2.Player", "Metadata")

        except Exception as error:
            log.add(_("MPRIS: Something went wrong while querying %(player)s: %(exception)s"),
                    {"player": player, "exception": error}, title=_("Now Playing Error"))
            return None

        self.title["program"] = player
        list_mapping = [("xesam:artist", "artist")]

        for source, dest in list_mapping:
            try:
                self.title[dest] = "+".join(metadata[source])
            except KeyError:
                self.title[dest] = "?"

        mapping = [
            ("xesam:title", "title"),
            ("xesam:album", "album"),
            ("xesam:contentCreated", "year"),
            ("xesam:comment", "comment"),
            ("xesam:audioBitrate", "bitrate"),
            ("xesam:url", "filename"),
            ("xesak:trackNumber", "track")
        ]

        for source, dest in mapping:
            try:
                self.title[dest] = str(metadata[source])
            except KeyError:
                self.title[dest] = "?"

        # The length is in microseconds, and be represented as a signed 64-bit integer.
        try:
            self.title["length"] = human_length(metadata["mpris:length"] // 1000000)
        except KeyError:
            self.title["length"] = "?"

        if self.title["artist"]:
            self.title["nowplaying"] += self.title["artist"]

        if self.title["title"]:
            self.title["nowplaying"] += " - " + self.title["title"]

        return True

    def _listenbrainz(self, username):
        """Function to get the currently playing song via ListenBrainz API."""

        if not username:
            log.add(_("ListenBrainz: Please provide your ListenBrainz username"), title=_("Now Playing Error"))
            return None

        try:
            from urllib.request import urlopen
            with urlopen(f"https://api.listenbrainz.org/1/user/{username}/playing-now", timeout=10) as response:
                response_body = response.read().decode("utf-8", "replace")

        except Exception as error:
            log.add(_("ListenBrainz: Could not connect to ListenBrainz: %(error)s"), {"error": error},
                    title=_("Now Playing Error"))
            return None

        try:
            json_response = json.loads(response_body)["payload"]

            if not json_response["playing_now"]:
                log.add(_("ListenBrainz: You don't seem to be listening to anything right now"),
                        title=_("Now Playing Error"))
                return None

            track = json_response["listens"][0]["track_metadata"]

            self.title["artist"] = artist = track.get("artist_name", "?")
            self.title["title"] = title = track.get("track_name", "?")
            self.title["album"] = track.get("release_name", "?")
            self.title["nowplaying"] = f"{artist} - {title}"

            return True

        except Exception as error:
            log.add(_("ListenBrainz: Could not get current track from ListenBrainz: %(error)s"),
                    {"error": error}, title=_("Now Playing Error"))
        return None

    def _other(self, command):

        if not command:
            return None

        try:
            output = execute_command(command, returnoutput=True, hidden=True)
            self.title["nowplaying"] = output.decode("utf-8", "replace")
            return True

        except Exception as error:
            log.add(_("Executing '%(command)s' failed: %(error)s"),
                    {"command": command, "error": error}, title=_("Now Playing Error"))
            return None
