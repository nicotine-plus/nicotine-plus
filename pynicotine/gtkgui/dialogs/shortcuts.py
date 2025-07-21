# SPDX-FileCopyrightText: 2021-2023 Nicotine+ Contributors
# SPDX-License-Identifier: GPL-3.0-or-later

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
