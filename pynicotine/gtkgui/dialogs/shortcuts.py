# COPYRIGHT (C) 2021-2023 Nicotine+ Contributors
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

from pynicotine.gtkgui.application import GTK_API_VERSION
from pynicotine.gtkgui.widgets import ui
from pynicotine.gtkgui.widgets.dialogs import Dialog


class Shortcuts(Dialog):

    def __init__(self, application):

        self.dialog, self.emoji_shortcut = ui.load(scope=self, path="dialogs/shortcuts.ui")

        super().__init__(
            widget=self.dialog,
            parent=application.window
        )
        application.window.set_help_overlay(self.dialog)

        if GTK_API_VERSION >= 4:
            header_bar = self.dialog.get_titlebar()

            if header_bar is not None:
                try:
                    header_bar.set_use_native_controls(True)  # pylint: disable=no-member

                except AttributeError:
                    # Older GTK version
                    pass

        # Workaround for off-centered dialog on first run
        self.dialog.set_visible(True)
        self.dialog.set_visible(False)
