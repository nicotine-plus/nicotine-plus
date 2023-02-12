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

import sys

from pynicotine.pluginsystem import BasePlugin

if sys.platform not in ("win32", "darwin"):
    from gi.repository import Gio


class Plugin(BasePlugin):

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        self.settings = {
            "rooms": ["testroom"]
        }
        self.metasettings = {
            "rooms": {
                "description": "Rooms to broadcast in",
                "type": "list string"
            }
        }
        self.commands = {
            "now": {
                "callback": self.now_playing_command,
                "description": _("Announce the song playing now"),
                "group": _("Now Playing"),
                "usage": ["[local|broadcast]"],
                "usage_cli": [""]
            }
        }
        self.bus = None
        self.signal_id = None
        self.stop = False
        self.dbus_mpris_service = ""
        self.last_song_url = ""

    def loaded_notification(self):

        if sys.platform in ("win32", "darwin"):
            # MPRIS is not available on Windows and macOS
            return

        self.bus = Gio.bus_get_sync(bus_type=Gio.BusType.SESSION)
        self.dbus_mpris_service = "org.mpris.MediaPlayer2."

        self.add_mpris_signal_receiver()

    def disable(self):
        self.remove_mpris_signal_receiver()

    def add_mpris_signal_receiver(self):
        """ Receive updates related to MPRIS (Linux only) """

        self.signal_id = self.bus.signal_subscribe(
            sender=None,
            interface_name="org.freedesktop.DBus.Properties",
            member="PropertiesChanged",
            object_path="/org/mpris/MediaPlayer2",
            arg0=None,
            flags=Gio.DBusSignalFlags.NONE,
            callback=self.song_change
        )

    def remove_mpris_signal_receiver(self):
        """ Stop receiving updates related to MPRIS """

        if self.bus and self.signal_id:
            self.bus.signal_unsubscribe(self.signal_id)

    def get_current_mpris_player(self):
        """ Returns the MPRIS client currently selected in Now Playing """

        player = self.config.sections["players"]["npothercommand"]

        if not player:
            dbus_proxy = Gio.DBusProxy.new_sync(
                bus=self.bus,
                flags=Gio.DBusProxyFlags.NONE,
                info=None,
                name="org.freedesktop.DBus",
                object_path="/org/freedesktop/DBus",
                interface_name="org.freedesktop.DBus"
            )
            names = dbus_proxy.ListNames()

            for name in names:
                if name.startswith(self.dbus_mpris_service):
                    player = name[len(self.dbus_mpris_service):]
                    break

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

        self.send_now_playing(broadcast=True)

    def send_now_playing(self, broadcast=False, local=False):
        """ Broadcast Now Playing in selected rooms, or Send in current chat """

        playing = self.core.now_playing.get_np()

        if local or not playing:
            # Display output locally
            self.echo_message(playing)
            return

        if broadcast:
            # Broadcast in selected rooms
            for room in self.settings["rooms"]:
                self.send_public(room, playing)
        else:
            # Send in current chat only
            self.send_message(playing)

    def now_playing_command(self, args, user=None, room=None):
        """ /now command """

        self.send_now_playing(
            broadcast=(args == "broadcast"),
            local=(args == "local" or (user is None and room is None))
        )
