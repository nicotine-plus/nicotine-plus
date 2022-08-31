# COPYRIGHT (C) 2021-2022 Nicotine+ Contributors
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

from pynicotine.gtkgui.widgets.dialogs import Dialog
from pynicotine.gtkgui.widgets.ui import UserInterface


class Shortcuts(UserInterface, Dialog):

    def __init__(self, frame):

        UserInterface.__init__(self, "ui/dialogs/shortcuts.ui")
        self.dialog, self.emoji_shortcut = self.widgets

        Dialog.__init__(
            self,
            dialog=self.dialog,
            parent=frame.window,
            close_destroy=False
        )
        frame.window.set_help_overlay(self.dialog)

        # Workaround for off-centered dialog on first run
        self.dialog.show()
        self.dialog.hide()
