# COPYRIGHT (C) 2020 Nicotine+ Team
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

import copy
import os
from gettext import gettext as _

from gi.repository import GObject
from gi.repository import Gtk

from pynicotine.logfacility import log
from pynicotine.utils import execute_command


class NowPlaying:

    def __init__(self, frame):
        """ Create NowPlayer interface """

        # Build the window
        self.frame = frame

        builder = Gtk.Builder()

        builder.set_translation_domain('nicotine')
        builder.add_from_file(os.path.join(os.path.dirname(os.path.realpath(__file__)), "ui", "nowplaying.ui"))

        self.now_playing_dialog = builder.get_object("NowPlayingDialog")

        builder.connect_signals(self)

        for i in builder.get_objects():
            try:
                self.__dict__[Gtk.Buildable.get_name(i)] = i
            except TypeError:
                pass

        self.now_playing_dialog.set_transient_for(self.frame.MainWindow)

        self.now_playing_dialog.connect("destroy", self.quit)
        self.now_playing_dialog.connect("destroy-event", self.quit)
        self.now_playing_dialog.connect("delete-event", self.quit)

        self.title_clear()

        # Set the active radio button
        config = self.frame.np.config.sections

        self.player_replacers = []

        self.on_np_player(None)
        self.set_player(config["players"]["npplayer"])

        # Default format list
        self.np_format_model = Gtk.ListStore(GObject.TYPE_STRING)

        self.defaultlist = [
            "$n",
            "$n ($f)",
            "$a - $t",
            "[$a] $t",
            "$a - $b - $t",
            "$a - $b - $t ($l/$r KBps) from $y $c"
        ]

        for item in self.defaultlist:
            self.np_format_model.append([str(item)])

        # Add custom formats
        if config["players"]["npformatlist"] != []:
            for item in config["players"]["npformatlist"]:
                self.np_format_model.append([str(item)])

        # Set the NPFormat model
        self.NPFormat.set_entry_text_column(0)
        self.NPFormat.set_model(self.np_format_model)

        if config["players"]["npformat"] == "":
            # If there's no default format in the config: set the first of the list
            self.NPFormat.set_active(0)
        else:
            # If there's is a default format in the config: select the right item
            for (i, v) in enumerate(self.np_format_model):
                if v[0] == config["players"]["npformat"]:
                    self.NPFormat.set_active(i)

        # Set the command from the config
        self.NPCommand.set_text(config["players"]["npothercommand"])

    def title_clear(self):
        self.Example.set_text("")
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

    def set_player(self, player):

        if player == "lastfm":
            self.NP_lastfm.set_active(1)
        elif player == "mpris":
            self.NP_mpris.set_active(1)
        elif player == "other":
            self.NP_other.set_active(1)
            self.player_replacers = ["$n"]
        else:
            self.NP_other.set_active(1)

    def on_np_player(self, widget):

        isset = False

        if self.NP_lastfm.get_active():
            self.player_replacers = ["$n", "$t", "$a", "$b"]
            self.player_input.set_text(_("Username;APIKEY :"))
            isset = True
        elif self.NP_mpris.get_active():
            self.player_replacers = ["$n", "$p", "$a", "$b", "$t", "$y", "$c", "$r", "$k", "$l", "$f"]
            self.player_input.set_text(_("Client name (e.g. amarok, audacious, exaile) or empty for auto:"))
            isset = True
        elif self.NP_other.get_active():
            self.player_replacers = ["$n"]
            self.player_input.set_text(_("Command :"))
            isset = True

        self.NPCommand.set_sensitive(
            self.NP_lastfm.get_active() or
            self.NP_other.get_active() or
            self.NP_mpris.get_active()
        )

        legend = ""
        for item in self.player_replacers:
            legend += item + "\t"
            if item == "$t":
                legend += _("Title")
            elif item == "$n":
                legend += _("Now Playing (typically \"%(artist)s - %(title)s\")") % {'artist': _("Artist"), 'title': _("Title")}
            elif item == "$l":
                legend += _("Length")
            elif item == "$r":
                legend += _("Bitrate")
            elif item == "$c":
                legend += _("Comment")
            elif item == "$a":
                legend += _("Artist")
            elif item == "$b":
                legend += _("Album")
            elif item == "$k":
                legend += _("Track Number")
            elif item == "$y":
                legend += _("Year")
            elif item == "$f":
                legend += _("Filename (URI)")
            elif item == "$p":
                legend += _("Program")

            legend += "\n"

        self.Legend.set_text(legend)

        if not isset:
            self.Legend.set_text("")

    def on_np_cancel(self, widget):
        self.quit(None)

    def show(self):
        self.now_playing_dialog.show()

    def quit(self, widget, s=None):

        # Save new defined formats in npformatlist before exiting
        config = self.frame.np.config.sections

        text = self.NPFormat.get_child().get_text()

        if text is not None and not text.isspace() and text != "":
            if text not in config["players"]["npformatlist"] and text not in self.defaultlist:
                config["players"]["npformatlist"].append(text)

        self.frame.np.config.write_configuration()

        # Hide the NowPlaying window
        self.now_playing_dialog.hide()
        return True

    def on_np_test(self, widget):
        self.display_now_playing(None, 1)

    def display_now_playing(self, widget, test=0, callback=None):

        self.get_np(None, test, callback)

    def get_np(self, widget, test=None, callback=None):

        self.title_clear()

        result = None

        try:

            if self.NP_lastfm.get_active():
                result = self.lastfm()
            elif self.NP_other.get_active():
                result = self.other()
            elif self.NP_mpris.get_active():
                result = self.mpris()

        except RuntimeError:
            log.add_warning(_("ERROR: Could not execute now playing code. Are you sure you picked the right player?"))
            result = None

        if not result:
            return None

        # Since we need unicode instead of bytes we'll try to force such a
        # conversion. Individual player commands should have done this already
        # - this is a failsafe.
        oldtitle = copy.copy(self.title)
        self.title_clear()
        for key, value in oldtitle.items():
            try:
                self.title[key] = str(value, "UTF-8", "replace")
            except TypeError:
                self.title[key] = value  # already unicode

        title = self.NPFormat.get_child().get_text()
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
        title = ' '.join([x for x in title.replace('\r', '\n').split('\n') if x])

        if test:
            self.Example.set_text(title)
            return None

        if title:
            if callback:
                callback(title)
            return title

        return None

    def on_np_save(self, widget):

        if self.NP_lastfm.get_active():
            player = "lastfm"
        elif self.NP_mpris.get_active():
            player = "mpris"
        elif self.NP_other.get_active():
            player = "other"

        self.frame.np.config.sections["players"]["npplayer"] = player
        self.frame.np.config.sections["players"]["npothercommand"] = self.NPCommand.get_text()
        self.frame.np.config.sections["players"]["npformat"] = self.NPFormat.get_child().get_text()
        self.frame.np.config.write_configuration()

        self.quit(None)

    def lastfm(self):
        """ Function to get the last song played via lastfm api """

        import http.client
        import json

        try:
            conn = http.client.HTTPSConnection("ws.audioscrobbler.com")
        except Exception as error:
            log.add_warning(_("ERROR: lastfm: Could not connect to audioscrobbler: %(error)s"), {"error": error})
            return None

        try:
            (user, apikey) = self.NPCommand.get_text().split(';')
        except ValueError:
            log.add_warning(_("ERROR: lastfm: Please provide both your lastfm username and API key"))
            return None

        conn.request("GET", "/2.0/?method=user.getrecenttracks&user=" + user + "&api_key=" + apikey + "&format=json", headers={"User-Agent": "Nicotine+"})
        resp = conn.getresponse()
        data = resp.read().decode("utf-8")

        if resp.status != 200 or resp.reason != "OK":
            log.add_warning(_("ERROR: lastfm: Could not get recent track from audioscrobbler: %(error)s"), {"error": str(data)})
            return None

        json_api = json.loads(data)
        lastplayed = json_api["recenttracks"]["track"][0]

        self.title["artist"] = lastplayed["artist"]["#text"]
        self.title["title"] = lastplayed["name"]
        self.title["album"] = lastplayed["album"]["#text"]
        self.title["nowplaying"] = "%s: %s - %s - %s" % (_("Last played"), self.title["artist"], self.title["album"], self.title["title"])

        return True

    def mpris(self):
        """ Function to get the currently playing song via dbus mpris v2 interface """

        # https://media.readthedocs.org/pdf/mpris2/latest/mpris2.pdf
        try:
            import dbus
            import dbus.glib
        except ImportError as error:
            log.add_warning(_("ERROR: MPRIS: failed to load dbus module: %(error)s"), {"error": error})
            return None

        self.bus = dbus.SessionBus()

        player = self.NPCommand.get_text()

        dbus_mpris_service = 'org.mpris.MediaPlayer2.'
        dbus_mpris_player_service = 'org.mpris.MediaPlayer2.Player'
        dbus_mpris_path = '/org/mpris/MediaPlayer2'
        dbus_property = 'org.freedesktop.DBus.Properties'

        if not player:

            names = self.bus.list_names()
            players = []

            for name in names:
                if name.startswith(dbus_mpris_service):
                    players.append(name[len(dbus_mpris_service):])

            if not players:
                log.add_warning(_("ERROR: MPRIS: Could not find a suitable MPRIS player."))
                return None

            player = players[0]
            if len(players) > 1:
                log.add_warning(_("Found multiple MPRIS players: %(players)s. Using: %(player)s"), {'players': players, 'player': player})
            else:
                log.add_warning(_("Auto-detected MPRIS player: %s."), player)

        try:
            player_obj = self.bus.get_object(dbus_mpris_service + player, dbus_mpris_path)
            player_property_obj = dbus.Interface(player_obj, dbus_interface=dbus_property)
            metadata = player_property_obj.Get(dbus_mpris_player_service, "Metadata")
        except Exception as exception:
            log.add_warning(_("ERROR: MPRIS: Something went wrong while querying %(player)s: %(exception)s"), {'player': player, 'exception': exception})
            return None

        self.title['program'] = player
        list_mapping = [('xesam:artist', 'artist')]

        for (source, dest) in list_mapping:
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

        for (source, dest) in mapping:
            try:
                self.title[dest] = str(metadata[source])
            except KeyError:
                self.title[dest] = '?'

        # The length is in microseconds, and be represented as a signed 64-bit integer.
        try:
            self.title['length'] = self.get_length_time(metadata['mpris:length'] // 1000000)
        except KeyError:
            self.title['length'] = '?'

        if self.title['artist'] != "":
            self.title['nowplaying'] += self.title['artist']

        if self.title['title'] != "":
            self.title['nowplaying'] += " - " + self.title['title']

        return True

    def get_length_time(self, length):
        """ Function used to normalize tracks duration """

        if length != '' and length is not None:

            minutes = int(length) // 60
            seconds = str(int(length) - (60 * minutes))

            if len(seconds) < 2:
                seconds = '0' + seconds

            length = str(minutes) + ":" + str(seconds)
        else:
            length = "0:00"

        return length

    def other(self):
        try:
            othercommand = self.NPCommand.get_text()
            if othercommand == "":
                return None

            output = execute_command(othercommand, returnoutput=True)
            self.title["nowplaying"] = output
            return True
        except Exception as error:
            log.add_warning(_("ERROR: Executing '%(command)s' failed: %(error)s"), {"command": othercommand, "error": error})
            return None
