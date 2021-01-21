from gi.repository import Gio
from pynicotine.pluginsystem import BasePlugin


def enable(plugins):
    global PLUGIN
    PLUGIN = Plugin(plugins)
    PLUGIN.add_mpris_signal_receiver()


def disable(plugins):
    global PLUGIN
    PLUGIN.remove_mpris_signal_receiver()
    PLUGIN = None


class Plugin(BasePlugin):
    __name__ = "Now Playing Sender"
    settings = {
        'rooms': ['testroom'],
    }
    metasettings = {
        'rooms': {'description': 'Rooms to broadcast in', 'type': 'list string'},
    }

    def init(self):

        self.last_song_url = ""
        self.stop = False

        self.bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
        self.signal_id = None

        self.dbus_mpris_service = 'org.mpris.MediaPlayer2.'
        self.dbus_mpris_player_service = 'org.mpris.MediaPlayer2.Player'
        self.dbus_mpris_path = '/org/mpris/MediaPlayer2'
        self.dbus_property = 'org.freedesktop.DBus.Properties'

    def add_mpris_signal_receiver(self):
        """ Receive updates related to MPRIS """

        self.signal_id = self.bus.signal_subscribe(None,
                                                   self.dbus_property,
                                                   "PropertiesChanged",
                                                   self.dbus_mpris_path,
                                                   None,
                                                   Gio.DBusSignalFlags.NONE,
                                                   self.song_change)

    def remove_mpris_signal_receiver(self):
        """ Stop receiving updates related to MPRIS """

        self.bus.signal_unsubscribe(self.signal_id)

    def get_current_mpris_player(self):
        """ Returns the MPRIS client currently selected in Now Playing """

        player = self.frame.np.config.sections["players"]["npothercommand"]

        if not player:
            dbus_proxy = Gio.DBusProxy.new_sync(self.bus,
                                                Gio.DBusProxyFlags.NONE,
                                                None,
                                                'org.freedesktop.DBus',
                                                '/org/freedesktop/DBus',
                                                'org.freedesktop.DBus',
                                                None)

            names = dbus_proxy.ListNames()

            for name in names:
                if name.startswith(self.dbus_mpris_service):
                    player = name[len(self.dbus_mpris_service):]
                    break

        return player

    def get_current_mpris_song_url(self, player):
        """ Returns the current song url for the selected MPRIS client """

        dbus_proxy = Gio.DBusProxy.new_sync(self.bus,
                                            Gio.DBusProxyFlags.NONE,
                                            None,
                                            self.dbus_mpris_service + player,
                                            self.dbus_mpris_path,
                                            self.dbus_property,
                                            None)

        metadata = dbus_proxy.Get('(ss)', self.dbus_mpris_player_service, 'Metadata')
        song_url = metadata.get("xesam:url")

        return song_url

    def send_now_playing(self):
        """ Broadcast Now Playing in selected rooms """

        for room in self.settings['rooms']:
            playing = self.frame.np.now_playing.get_np()

            if playing:
                self.saypublic(room, playing)

    def song_change(self, connection, sender_name, object_path, interface_name, signal_name, parameters):

        if self.frame.np.config.sections["players"]["npplayer"] != "mpris":
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
