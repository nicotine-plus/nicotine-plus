# COPYRIGHT (C) 2020-2021 Nicotine+ Team
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

from gi.repository import Gdk
from gi.repository import GLib
from gi.repository import Gtk

from pynicotine.config import config
from pynicotine.gtkgui.widgets.dialogs import dialog_show
from pynicotine.gtkgui.widgets.dialogs import set_dialog_properties
from pynicotine.gtkgui.widgets.theme import get_icon
from pynicotine.gtkgui.widgets.ui import UserInterface
from pynicotine.utils import open_uri


class About(UserInterface):

    def __init__(self, frame):

        super().__init__("ui/dialogs/about.ui")

        self.frame = frame
        set_dialog_properties(self.dialog, frame.MainWindow)

        # Override link handler with our own
        self.dialog.connect("activate-link", lambda x, url: open_uri(url))

        logo = get_icon("n")

        if logo:
            if Gtk.get_major_version() == 4:
                logo = Gdk.Texture.new_for_pixbuf(logo)

            self.dialog.set_logo(logo)
        else:
            self.dialog.set_logo_icon_name(GLib.get_prgname())

        if Gtk.get_major_version() == 4:
            self.dialog.connect("close-request", lambda x: x.destroy())
        else:
            self.dialog.connect("response", lambda x, y: x.destroy())

        self.dialog.set_version(config.version + "  •  GTK " + config.gtk_version)

    def show(self):
        dialog_show(self.dialog)
