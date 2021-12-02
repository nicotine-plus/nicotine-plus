# COPYRIGHT (C) 2021 Nicotine+ Team
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

from gi.repository import Gtk

from pynicotine.gtkgui.widgets.dialogs import dialog_hide
from pynicotine.gtkgui.widgets.dialogs import dialog_show
from pynicotine.gtkgui.widgets.dialogs import set_dialog_properties
from pynicotine.gtkgui.widgets.ui import UserInterface


class Shortcuts(UserInterface):

    def __init__(self, frame):

        super().__init__("ui/dialogs/shortcuts.ui")

        self.frame = frame
        set_dialog_properties(self.dialog, frame.MainWindow, quit_callback=self.hide)

        if hasattr(Gtk.Entry.props, "show-emoji-icon"):
            # Emoji picker only available in GTK 3.24+
            self.emoji.show()

        # Workaround for off-centered dialog on first run
        dialog_show(self.dialog)
        dialog_hide(self.dialog)

    def hide(self, *_args):
        dialog_hide(self.dialog)
        return True

    def show(self):
        dialog_show(self.dialog)
