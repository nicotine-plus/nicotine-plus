# SPDX-FileCopyrightText: 2022-2023 Nicotine+ Contributors
# SPDX-License-Identifier: GPL-3.0-or-later

from pynicotine.config import config
from pynicotine.gtkgui.application import GTK_API_VERSION
from pynicotine.gtkgui.widgets import ui
from pynicotine.gtkgui.widgets.popover import Popover
from pynicotine.gtkgui.widgets.theme import add_css_class


class TransferSpeeds(Popover):

    def __init__(self, window, transfer_type):

        self.transfer_type = transfer_type

        (
            self.alt_speed_spinner,
            self.container,
            self.speed_spinner,
            self.use_alt_limit_radio,
            self.use_limit_radio,
            self.use_unlimited_speed_radio
        ) = ui.load(scope=self, path=f"popovers/{transfer_type}speeds.ui")

        super().__init__(
            window=window,
            content_box=self.container,
            show_callback=self.on_show
        )

    def set_menu_button(self, menu_button):

        super().set_menu_button(menu_button)

        if menu_button is not None and GTK_API_VERSION >= 4:
            inner_button = next(iter(menu_button))
            add_css_class(widget=inner_button, css_class="flat")

    @staticmethod
    def update_transfer_limits():
        raise NotImplementedError

    def on_active_limit_toggled(self, *_args):

        use_limit_config_key = f"use_{self.transfer_type}_speed_limit"
        prev_active_limit = config.sections["transfers"][use_limit_config_key]

        if self.use_limit_radio.get_active():
            config.sections["transfers"][use_limit_config_key] = "primary"

        elif self.use_alt_limit_radio.get_active():
            config.sections["transfers"][use_limit_config_key] = "alternative"

        else:
            config.sections["transfers"][use_limit_config_key] = "unlimited"

        if prev_active_limit != config.sections["transfers"][use_limit_config_key]:
            self.update_transfer_limits()

    def on_limit_changed(self, *_args):

        speed_limit = self.speed_spinner.get_value_as_int()

        if speed_limit == config.sections["transfers"][f"{self.transfer_type}limit"]:
            return

        config.sections["transfers"][f"{self.transfer_type}limit"] = speed_limit
        self.update_transfer_limits()

    def on_alt_limit_changed(self, *_args):

        alt_speed_limit = self.alt_speed_spinner.get_value_as_int()

        if alt_speed_limit == config.sections["transfers"][f"{self.transfer_type}limitalt"]:
            return

        config.sections["transfers"][f"{self.transfer_type}limitalt"] = alt_speed_limit
        self.update_transfer_limits()

    def on_show(self, *_args):

        self.alt_speed_spinner.set_value(config.sections["transfers"][f"{self.transfer_type}limitalt"])
        self.speed_spinner.set_value(config.sections["transfers"][f"{self.transfer_type}limit"])

        use_speed_limit = config.sections["transfers"][f"use_{self.transfer_type}_speed_limit"]

        if use_speed_limit == "primary":
            self.use_limit_radio.set_active(True)

        elif use_speed_limit == "alternative":
            self.use_alt_limit_radio.set_active(True)

        else:
            self.use_unlimited_speed_radio.set_active(True)
