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

        import dbus
        from dbus.mainloop.glib import DBusGMainLoop

        self.last_song_url = ""
        self.stop = False

        DBusGMainLoop(set_as_default=True)
        self.bus = dbus.SessionBus()

        self.dbus_mpris_service = 'org.mpris.MediaPlayer2.'
        self.dbus_mpris_player_service = 'org.mpris.MediaPlayer2.Player'
        self.dbus_mpris_path = '/org/mpris/MediaPlayer2'
        self.dbus_property = 'org.freedesktop.DBus.Properties'

    def add_mpris_signal_receiver(self):
        """ Receive updates related to MPRIS """

        self.bus.add_signal_receiver(
            self.song_change,
            "PropertiesChanged",
            path=self.dbus_mpris_path,
            dbus_interface=self.dbus_property
        )

    def remove_mpris_signal_receiver(self):
        """ Stop receiving updates related to MPRIS """

        self.bus.remove_signal_receiver(
            self.song_change,
            "PropertiesChanged",
            path=self.dbus_mpris_path,
            dbus_interface=self.dbus_property
        )

    def get_current_mpris_player(self):
        """ Returns the MPRIS client currently selected in Now Playing """

        player = self.frame.np.config.sections["players"]["npothercommand"]

        if not player:
            names = self.bus.list_names()

            for name in names:
                if name.startswith(self.dbus_mpris_service):
                    player = name[len(self.dbus_mpris_service):]
                    break

        return player

    def get_current_mpris_song_url(self, player):
        """ Returns the current song url for the selected MPRIS client """

        import dbus

        player_obj = self.bus.get_object(self.dbus_mpris_service + player, self.dbus_mpris_path)
        player_property_obj = dbus.Interface(player_obj, dbus_interface=self.dbus_property)

        metadata = player_property_obj.Get(self.dbus_mpris_player_service, "Metadata")
        song_url = metadata.get("xesam:url")

        return song_url

    def send_now_playing(self):
        """ Broadcast Now Playing in selected rooms """

        for room in self.settings['rooms']:
            try:
                playing = self.frame.now_playing.get_np()

            except AttributeError:
                # Legacy support

                if not hasattr(self.frame, "NowPlaying"):
                    from pynicotine.gtkgui.nowplaying import NowPlaying
                    self.frame.NowPlaying = NowPlaying(self.frame)

                playing = self.frame.NowPlaying.GetNP(None)

            if playing:
                self.saypublic(room, playing)

    def song_change(self, interface_name, changed_properties, invalidated_properties):

        if self.frame.np.config.sections["players"]["npplayer"] != "mpris":
            # MPRIS is not active, exit
            return

        # Get the changed song url received from the the signal
        try:
            changed_song_url = changed_properties.get("Metadata").get("xesam:url")

        except AttributeError:
            return

        if not changed_song_url:
            # Song url empty, the player most likely stopped playing
            self.last_song_url = ""
            return

        if changed_song_url == self.last_song_url:
            # A new song didn't start playing, exit
            return

        player = self.get_current_mpris_player()
        selected_client_song_url = self.get_current_mpris_song_url(player)

        if selected_client_song_url != changed_song_url:
            # Song change was from another MPRIS client than the selected one, exit
            return

        # Keep track of which song is playing
        self.last_song_url = changed_song_url

        self.send_now_playing()
