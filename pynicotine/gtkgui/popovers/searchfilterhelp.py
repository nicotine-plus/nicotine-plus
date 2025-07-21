# SPDX-FileCopyrightText: 2022-2023 Nicotine+ Contributors
# SPDX-License-Identifier: GPL-3.0-or-later

from pynicotine.gtkgui.widgets import ui
from pynicotine.gtkgui.widgets.popover import Popover


class SearchFilterHelp(Popover):

    def __init__(self, window):

        (self.container,) = ui.load(scope=self, path="popovers/searchfilterhelp.ui")

        super().__init__(
            window=window,
            content_box=self.container,
            width=500,
            height=375
        )
