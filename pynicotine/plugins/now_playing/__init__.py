# COPYRIGHT (C) 2020-2022 Nicotine+ Contributors
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
from urllib.request import urlopen

from pynicotine.logfacility import log
from pynicotine.pluginsystem import BasePlugin
from pynicotine.utils import execute_command
from pynicotine.utils import human_length


class Plugin(BasePlugin):

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        self.settings = {
            "format": "%artist% - %title%",
            "lastfm_username_api_key": "",
            "listenbrainz_username": ""
        }
        self.metasettings = {
            "source": {
                "description": "Media source:",
                "type": "dropdown",
                "options": [
                    "Last.fm",
                    "ListenBrainz"
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
            self.metasettings["mpris_player"] = {
                "description": "MPRIS player (e.g. amarok, audacious, exaile); leave empty to autodetect:",
                "type": "string"
            }
            self.metasettings["rooms"] = {
                "description": "Rooms to broadcast in (MPRIS only)",
                "type": "list string"
            }

        else:
            self.settings["source"] = "Last.fm"

        self.__publiccommands__ = self.__privatecommands__ = [("now", self.now_command)]

        self.bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
        self.signal_id = None
        self.last_song_url = ""

        self.dbus_mpris_service = "org.mpris.MediaPlayer2."
        self.dbus_mpris_player_service = "org.mpris.MediaPlayer2.Player"
        self.dbus_mpris_path = "/org/mpris/MediaPlayer2"
        self.dbus_property = "org.freedesktop.DBus.Properties"

        self.add_mpris_signal_receiver()

    def disable(self):
        self.remove_mpris_signal_receiver()

    def now_command(self, _args, *_unused):
        self.send_message(self.get_np())

    def outgoing_global_search_event(self, text):
        return (self.get_np(format=text),)

    def outgoing_room_search_event(self, rooms, text):
        return rooms, self.get_np(format=text)

    def outgoing_buddy_search_event(self, text):
        return (self.get_np(format=text),)

    def outgoing_user_search_event(self, users, text):
        return users, self.get_np(format=text)

    def get_np(self, format_message=None):

        player = self.settings["source"]
        track_info = None

        if player == "Last.fm":
            track_info = self.lastfm("")

        elif player == "ListenBrainz":
            track_info = self.listenbrainz()

        elif player == "MPRIS":
            track_info = self.mpris()

        if not track_info:
            return None

        if not format_message:
            format_message = self.settings["format"]

        for placeholder, value in track_info.items():
            format_message = format_message.replace(placeholder, value)

        format_message = " ".join(x for x in format_message.replace("\r", "\n").split("\n") if x)
        return format_message

    def send_now_playing(self):
        """ Broadcast Now Playing in selected rooms """

        for room in self.settings["rooms"]:
            playing = self.get_np()

            if playing:
                self.send_public(room, playing)

    """ Last.fm """

    def lastfm(self, user):
        """ Function to get the last song played via Last.fm API """

        try:
            user, apikey = user.split(";")

        except ValueError:
            log.add_important(_("Last.fm: Please provide both your Last.fm username and API key"))
            return None

        try:
            with urlopen((f"https://ws.audioscrobbler.com/2.0/?method=user.getrecenttracks&user={user}&api_key={apikey}"
                          f"&limit=1&format=json"), timeout=10) as response:
                response_body = response.read().decode("utf-8")

        except Exception as error:
            log.add_important(_("Last.fm: Could not connect to Audioscrobbler: %(error)s"), {"error": error})
            return None

        try:
            track_info = {}
            json_api = json.loads(response_body)
            lastplayed = json_api["recenttracks"]["track"]

            try:
                # In most cases, a list containing a single track dictionary is sent
                lastplayed = lastplayed[0]

            except KeyError:
                # On rare occasions, the track dictionary is not wrapped in a list
                pass

            track_info["%artist%"] = lastplayed["artist"]["#text"]
            track_info["%title%"] = lastplayed["name"]
            track_info["%album%"] = lastplayed["album"]["#text"]

        except Exception:
            log.add_important(_("Last.fm: Could not get recent track from Audioscrobbler: %(error)s"),
                              {"error": response_body}, title=_("Now Playing Error"))
            return None

        return track_info

    """ MPRIS """

    def mpris(self):
        """ Function to get the currently playing song via DBus MPRIS v2 interface """

        player = self.settings["mpris_player"]

        if not player:
            dbus_proxy = Gio.DBusProxy.new_sync(
                self.bus, Gio.DBusProxyFlags.NONE, None,
                "org.freedesktop.DBus", "/org/freedesktop/DBus", "org.freedesktop.DBus", None
            )

            names = dbus_proxy.ListNames()
            players = []

            for name in names:
                if name.startswith(self.dbus_mpris_service):
                    players.append(name[len(self.dbus_mpris_service):])

            if not players:
                log.add_important(_("MPRIS: Could not find a suitable MPRIS player"), title=_("Now Playing Error"))
                return None

            player = players[0]
            if len(players) > 1:
                log.add(_("Found multiple MPRIS players: %(players)s. Using: %(player)s"),
                        {"players": players, "player": player})
            else:
                log.add(_("Auto-detected MPRIS player: %s"), player)

        try:
            dbus_proxy = Gio.DBusProxy.new_sync(
                self.bus, Gio.DBusProxyFlags.NONE, None,
                self.dbus_mpris_service + player, self.dbus_mpris_path, self.dbus_property, None
            )

            metadata = dbus_proxy.Get("(ss)", self.dbus_mpris_player_service, "Metadata")

        except Exception as error:
            log.add_important(_("MPRIS: Something went wrong while querying %(player)s: %(exception)s"),
                              {"player": player, "exception": error}, title=_("Now Playing Error"))
            return None

        track_info = {}
        track_info["%program%"] = player
        list_mapping = [("xesam:artist", "artist")]

        for source, dest in list_mapping:
            try:
                track_info[dest] = "+".join(metadata[source])
            except KeyError:
                track_info[dest] = "?"

        mapping = [
            ("xesam:title", "%title%"),
            ("xesam:album", "%album%"),
            ("xesam:contentCreated", "%year%"),
            ("xesam:comment", "%comment%"),
            ("xesam:audioBitrate", "%bitrate%"),
            ("xesam:url", "%filename%"),
            ("xesak:trackNumber", "%track%")
        ]

        for source, dest in mapping:
            try:
                track_info[dest] = str(metadata[source])
            except KeyError:
                track_info[dest] = "?"

        # The length is in microseconds, and be represented as a signed 64-bit integer.
        try:
            track_info["%duration%"] = human_length(metadata["mpris:length"] // 1000000)
        except KeyError:
            track_info["%duration%"] = "?"

        return track_info

    def add_mpris_signal_receiver(self):
        """ Receive updates related to MPRIS """

        self.signal_id = self.bus.signal_subscribe(
            None, self.dbus_property, "PropertiesChanged", self.dbus_mpris_path,
            None, Gio.DBusSignalFlags.NONE, self.song_change)

    def remove_mpris_signal_receiver(self):
        """ Stop receiving updates related to MPRIS """

        self.bus.signal_unsubscribe(self.signal_id)

    def get_current_mpris_player(self):
        """ Returns the MPRIS client currently selected in Now Playing """

        player = self.config.sections["players"]["npothercommand"]

        if not player:
            dbus_proxy = Gio.DBusProxy.new_sync(
                self.bus, Gio.DBusProxyFlags.NONE, None,
                "org.freedesktop.DBus", "/org/freedesktop/DBus", "org.freedesktop.DBus", None)

            names = dbus_proxy.ListNames()

            for name in names:
                if name.startswith(self.dbus_mpris_service):
                    player = name[len(self.dbus_mpris_service):]
                    break

        return player

    def get_current_mpris_song_url(self, player):
        """ Returns the current song url for the selected MPRIS client """

        dbus_proxy = Gio.DBusProxy.new_sync(
            self.bus, Gio.DBusProxyFlags.NONE, None,
            self.dbus_mpris_service + player, self.dbus_mpris_path, self.dbus_property, None)

        metadata = dbus_proxy.Get("(ss)", self.dbus_mpris_player_service, "Metadata")
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

        except Exception:
            # Selected player is invalid
            return

        if selected_client_song_url != changed_song_url:
            # Song change was from another MPRIS client than the selected one, exit
            return

        # Keep track of which song is playing
        self.last_song_url = changed_song_url

        self.send_now_playing()

    """ ListenBrainz """

    def listenbrainz(self):
        """ Function to get the currently playing song via ListenBrainz API """

        username = self.settings["listenbrainz_username"]

        if not username:
            log.add(_("ListenBrainz: Please provide your ListenBrainz username"))
            return None

        try:
            with urlopen(f"https://api.listenbrainz.org/1/user/{username}/playing-now", timeout=10) as response:
                response_body = response.read().decode("utf-8")

        except Exception as error:
            log.add(_("ListenBrainz: Could not connect to ListenBrainz: %(error)s"), {"error": error})
            return None

        try:
            track_info = {}
            json_api = json.loads(response_body)["payload"]

            if not json_api["playing_now"]:
                log.add(_("ListenBrainz: You don't seem to be listening to anything right now"))
                return None

            track = json_api["listens"][0]["track_metadata"]

            track_info["%artist%"] = track["artist_name"]
            track_info["%title%"] = track["track_name"]
            track_info["%album%"] = track["release_name"]

            return track_info

        except Exception:
            log.add(_("ListenBrainz: Could not get current track from ListenBrainz: %(error)s"),
                    {"error": str(response_body)})
        return None
