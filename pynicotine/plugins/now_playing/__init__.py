# COPYRIGHT (C) 2020-2023 Nicotine+ Contributors
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
import sys

from gi.repository import Gio

from pynicotine.logfacility import log
from pynicotine.pluginsystem import BasePlugin
from pynicotine.utils import human_length


class Plugin(BasePlugin):

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        self.commands = {
            "now": {
                "callback": self.now_command,
                "description": _("Announce the song playing now"),
            }
        }
        self.settings = {
            "format": "np: $n",
            "lastfm_username_api_key": "",
            "listenbrainz_username": "",
            "other_command": ""
        }
        self.metasettings = {
            "source": {
                "description": "Media source:",
                "type": "dropdown",
                "options": [
                    "Last.fm",
                    "ListenBrainz",
                    "Other"
                ]
            },
            "format": {
                "description": "Now Playing message format:",
                "type": "string"
            },
            "lastfm_username_api_key": {
                "description": "Last.fm username;APIKEY:",
                "type": "string"
            },
            "listenbrainz_username": {
                "description": "ListenBrainz username:",
                "type": "string"
            },
            "mpris_player": {
                "description": "MPRIS player (e.g. amarok, audacious, exaile); leave empty to autodetect:",
                "type": "string"
            },
            "other_command": {
                "description": "Other command:",
                "type": "string"
            }
        }

        if sys.platform not in ("win32", "darwin"):
            for option_key, value in (
                ("source", "MPRIS"),
                ("mpris_player", ""),
                ("rooms", ["testroom"])
            ):
                self.settings[option_key] = value

            self.metasettings["source"]["options"].append("MPRIS")
            self.metasettings["source"]["options"].sort()

            self.metasettings["rooms"] = {
                "description": "Rooms to broadcast in (MPRIS only)",
                "type": "list string"
            }

            self.bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
            self.dbus_mpris_service = "org.mpris.MediaPlayer2."
            self.signal_id = None
            self.last_song_url = ""

            self.add_mpris_signal_receiver()

        else:
            # MPRIS is not available on Windows and macOS
            self.settings["source"] = "Last.fm"
            del self.metasettings["mpris_player"]
            self.bus = None

    def disable(self):
        self.remove_mpris_signal_receiver()

    def now_command(self, _args, user=None, room=None):

        playing = self.get_np()

        if not playing or (not user and not room):
            self.echo_message(playing)
            return

        self.send_message(playing)

    def outgoing_global_search_event(self, text):
        return (self.get_np(format_message=text),)

    def outgoing_room_search_event(self, rooms, text):
        return rooms, self.get_np(format_message=text)

    def outgoing_buddy_search_event(self, text):
        return (self.get_np(format_message=text),)

    def outgoing_user_search_event(self, users, text):
        return users, self.get_np(format_message=text)

    def get_np(self, format_message=None):

        player = self.settings["source"]
        playing = None

        if player == "Last.fm":
            playing = self.lastfm()

        elif player == "ListenBrainz":
            playing = self.listenbrainz()

        elif player == "MPRIS":
            playing = self.mpris()

        elif player == "Other":
            playing = self.other()

        if not playing:
            return "" if format_message else None

        if not format_message:
            format_message = self.settings["format"]

        for placeholder, value in playing.items():
            format_message = format_message.replace(f"%{placeholder}%", value)

        format_message = format_message.replace("%", "%%")  # Escaping user supplied % symbols
        format_message = format_message.replace("$t", "%(title)s")
        format_message = format_message.replace("$a", "%(artist)s")
        format_message = format_message.replace("$b", "%(album)s")
        format_message = format_message.replace("$c", "%(comment)s")
        format_message = format_message.replace("$n", "%(nowplaying)s")
        format_message = format_message.replace("$k", "%(track)s")
        format_message = format_message.replace("$l", "%(length)s")
        format_message = format_message.replace("$y", "%(year)s")
        format_message = format_message.replace("$r", "%(bitrate)s")
        format_message = format_message.replace("$f", "%(filename)s")
        format_message = format_message.replace("$p", "%(program)s")

        playing = format_message % playing
        playing = " ".join(x for x in playing.replace("\r", "\n").split("\n") if x)

        return playing

    def broadcast_now_playing(self):
        """ Broadcast Now Playing in selected rooms """

        playing = self.get_np()

        for room in self.settings["rooms"]:
            if playing:
                self.send_public(room, playing)

    """ Last.fm """

    def lastfm(self):
        """ Function to get the last song played via Last.fm API """

        try:
            user, api_key = self.settings["lastfm_username_api_key"].split(";")

        except ValueError:
            log.add(_("Last.fm: Please provide both your Last.fm username and API key"), title=_("Now Playing Error"))
            return None

        audioscrobbler_url = (
            "https://ws.audioscrobbler.com/2.0/"
            "?method=user.getrecenttracks"
            f"&user={user}"
            f"&api_key={api_key}"
            "&limit=1"
            "&format=json"
        )

        try:
            from urllib.request import urlopen

            with urlopen(audioscrobbler_url, timeout=10) as response:
                response_body = response.read().decode("utf-8")

        except Exception as error:
            log.add(_("Last.fm: Could not connect to Audioscrobbler: %(error)s"), {"error": error},
                    title=_("Now Playing Error"))
            return None

        try:
            playing = {}
            json_api = json.loads(response_body)
            lastplayed = json_api["recenttracks"]["track"]

            try:
                # In most cases, a list containing a single dictionary is sent
                lastplayed = lastplayed[0]

            except KeyError:
                # On rare occasions, the track dictionary is not wrapped in a list
                pass

            playing["artist"] = artist = lastplayed["artist"]["#text"]
            playing["title"] = title = lastplayed["name"]
            playing["album"] = album = lastplayed["album"]["#text"]
            playing["nowplaying"] = f"{artist} - {album} - {title}"

        except Exception:
            log.add(_("Last.fm: Could not get recent track from Audioscrobbler: %(error)s"), {"error": response_body},
                    title=_("Now Playing Error"))
            return None

        return playing

    """ MPRIS """

    def mpris(self):
        """ Function to get the currently playing song via DBus MPRIS v2 interface """

        # https://media.readthedocs.org/pdf/mpris2/latest/mpris2.pdf

        player = self.get_current_mpris_player()

        try:
            dbus_proxy = Gio.DBusProxy.new_for_bus_sync(
                bus_type=Gio.BusType.SESSION,
                flags=Gio.DBusProxyFlags.NONE,
                info=None,
                name=self.dbus_mpris_service + player,
                object_path="/org/mpris/MediaPlayer2",
                interface_name="org.freedesktop.DBus.Properties"
            )
            metadata = dbus_proxy.Get("(ss)", "org.mpris.MediaPlayer2.Player", "Metadata")

        except Exception as error:
            log.add(_("MPRIS: Something went wrong while querying %(player)s: %(exception)s"),
                    {"player": player, "exception": error}, title=_("Now Playing Error"))
            return None

        playing = {}
        playing["program"] = player
        list_mapping = [("xesam:artist", "artist")]

        for source, dest in list_mapping:
            try:
                playing[dest] = "+".join(metadata[source])
            except KeyError:
                playing[dest] = "?"

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
                playing[dest] = str(metadata[source])
            except KeyError:
                playing[dest] = "?"

        # The length is in microseconds, and be represented as a signed 64-bit integer.
        try:
            playing["duration"] = human_length(metadata["mpris:length"] // 1000000)
        except KeyError:
            playing["duration"] = "?"

        if playing["artist"] != "":
            playing["nowplaying"] += playing["artist"]

        if playing["title"] != "":
            playing["nowplaying"] += " - " + playing["title"]

        return playing

    def add_mpris_signal_receiver(self):
        """ Receive updates related to MPRIS """

        if not self.bus:
            # MPRIS is not available on Windows and macOS
            return

        self.signal_id = self.bus.signal_subscribe(
            sender=None,
            interface_name="org.freedesktop.DBus",
            member="PropertiesChanged",
            object_path="/org/freedesktop/DBus",
            arg0=None,
            flags=Gio.DBusSignalFlags.NONE,
            callback=self.song_change
        )

    def remove_mpris_signal_receiver(self):
        """ Stop receiving updates related to MPRIS """

        if self.bus:
            self.bus.signal_unsubscribe(self.signal_id)

    def get_current_mpris_player(self):
        """ Returns the MPRIS client currently selected in plugin settings """

        player = self.settings["mpris_player"]

        if not player:
            dbus_proxy = Gio.DBusProxy.new_for_bus_sync(
                bus_type=Gio.BusType.SESSION,
                flags=Gio.DBusProxyFlags.NONE,
                info=None,
                name="org.freedesktop.DBus",
                object_path="/org/freedesktop/DBus",
                interface_name="org.freedesktop.DBus"
            )
            names = dbus_proxy.ListNames()
            players = []

            for name in names:
                if name.startswith(self.dbus_mpris_service):
                    players.append(name[len(self.dbus_mpris_service):])

            if not players:
                log.add(_("MPRIS: Could not find a suitable MPRIS player"), title=_("Now Playing Error"))
                return None

            player = players[0]
            if len(players) > 1:
                log.add(_("Found multiple MPRIS players: %(players)s. Using: %(player)s"),
                        {"players": players, "player": player})
            else:
                log.add(_("Auto-detected MPRIS player: %s"), player)

        return player

    def get_current_mpris_song_url(self, player):
        """ Returns the current song url for the selected MPRIS client """

        dbus_proxy = Gio.DBusProxy.new_sync(
            bus=self.bus,
            flags=Gio.DBusProxyFlags.NONE,
            info=None,
            name=self.dbus_mpris_service + player,
            object_path="/org/mpris/MediaPlayer2",
            interface_name="org.freedesktop.DBus.Properties"
        )
        metadata = dbus_proxy.Get("(ss)", "org.mpris.MediaPlayer2.Player", "Metadata")
        song_url = metadata.get("xesam:url")

        return song_url

    def song_change(self, _connection, _sender_name, _object_path, _interface_name, _signal_name, parameters):

        if self.config.sections["players"]["npplayer"] != "mpris":
            # MPRIS is not active, exit
            return

        # Get the changed song url received from the the signal
        try:
            changed_song_url = parameters[1].get("Metadata").get("xesam:url")

        except AttributeError:
            return

        if not changed_song_url:
            # Song url empty, the player most likely stopped playing
            self.last_song_url = ""
            return

        if changed_song_url == self.last_song_url:
            # A new song didn't start playing, exit
            return

        try:
            player = self.get_current_mpris_player()
            selected_client_song_url = self.get_current_mpris_song_url(player)

        except Exception as error:
            self.log(f"Selected MPRIS player is invalid. Error: {error}")
            return

        if selected_client_song_url != changed_song_url:
            # Song change was from another MPRIS client than the selected one, exit
            return

        # Keep track of which song is playing
        self.last_song_url = changed_song_url

        self.broadcast_now_playing()

    """ ListenBrainz """

    def listenbrainz(self):
        """ Function to get the currently playing song via ListenBrainz API """

        username = self.settings["listenbrainz_username"]

        if not username:
            log.add(_("ListenBrainz: Please provide your ListenBrainz username"), title=_("Now Playing Error"))
            return None

        listenbrainz_url = f"https://api.listenbrainz.org/1/user/{username}/playing-now"

        try:
            from urllib.request import urlopen

            with urlopen(listenbrainz_url, timeout=10) as response:
                response_body = response.read().decode("utf-8")

        except Exception as error:
            log.add(_("ListenBrainz: Could not connect to ListenBrainz: %(error)s"),
                    {"error": error}, title=_("Now Playing Error"))
            return None

        try:
            playing = {}
            json_api = json.loads(response_body)["payload"]

            if not json_api["playing_now"]:
                log.add(_("ListenBrainz: You don't seem to be listening to anything right now"))
                return None

            track = json_api["listens"][0]["track_metadata"]

            playing["artist"] = artist = track["artist_name"]
            playing["title"] = title = track["track_name"]
            playing["album"] = album = track["release_name"]
            playing["nowplaying"] = f"{artist} - {album} - {title}"

        except Exception:
            log.add(_("ListenBrainz: Could not get current track from ListenBrainz: %(error)s"),
                    {"error": str(response_body)}, title=_("Now Playing Error"))
            return None

        return playing

    def other(self):

        command = self.settings["other_command"]

        if not command:
            return None

        playing = {}

        try:
            from pynicotine.utils import execute_command

            output = execute_command(command, returnoutput=True)
            playing["nowplaying"] = output

        except Exception as error:
            log.add(_("Executing '%(command)s' failed: %(error)s"),
                    {"command": command, "error": error}, title=_("Now Playing Error"))
            return None

        return playing
