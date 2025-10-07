# SPDX-FileCopyrightText: 2025 Nicotine+ Contributors
# SPDX-License-Identifier: GPL-3.0-or-later

from gi.repository import Gtk

from pynicotine.core import core
from pynicotine.events import events
from pynicotine.gtkgui.application import GTK_API_VERSION
from pynicotine.gtkgui.widgets import ui
from pynicotine.gtkgui.widgets.popover import Popover
from pynicotine.gtkgui.widgets.theme import add_css_class
from pynicotine.gtkgui.widgets.theme import remove_css_class


class PortChecker(Popover):

    def __init__(self, window):

        (
            self.container,
            self.description_label,
            self.status_container,
            self.status_icon,
            self.status_label,
            self.status_spinner
        ) = ui.load(scope=self, path="popovers/portchecker.ui")

        super().__init__(
            window=window,
            content_box=self.container,
            show_callback=self.on_show,
            close_callback=self.on_close
        )

        self.port = None

        for event_name, callback in (
            ("check-port-status", self.on_check_port_status),
            ("server-disconnect", self.on_show),
            ("server-login", self.on_show)
        ):
            events.connect(event_name, callback)

    def check_status(self):

        for css_class in ("error", "warning", "success"):
            remove_css_class(self.status_container, css_class)

        if self.port is None:
            icon_args = (Gtk.IconSize.BUTTON,) if GTK_API_VERSION == 3 else ()  # pylint: disable=no-member

            self.status_icon.set_from_icon_name("emblem-important-symbolic", *icon_args)
            self.status_label.set_label(_("You are offline"))
            self.description_label.set_label(_("Connect to the server to check port status."))

            add_css_class(self.status_container, "error")
            return

        self.status_label.set_label(_("Checking connection status…"))
        self.description_label.set_label(_("Waiting for response from port checker."))

        self.status_spinner.set_visible(True)
        self.status_spinner.start()

        core.port_checker.check_status(self.port)

    def on_check_port_status(self, port, is_successful):

        if port != self.port:
            return

        if is_successful is None:
            icon_name = "dialog-question-symbolic"
            css_class = None
            status = _("Port %i (TCP) status unknown") % port
            description = _("Cannot check connection status.")

        elif is_successful:
            icon_name = "object-select-symbolic"
            css_class = "success"
            status = _("Port %i (TCP) is open") % port
            description = _("Most users can connect to you.")

        else:
            icon_name = "dialog-warning-symbolic"
            css_class = "warning"
            status = _("Port %i (TCP) is closed") % port
            description = _("You can only connect to a few users. Ensure the port is forwarded "
                            "and your device's firewall is not blocking it.")

        icon_args = (Gtk.IconSize.BUTTON,) if GTK_API_VERSION == 3 else ()  # pylint: disable=no-member

        self.status_label.set_label(status)
        self.description_label.set_label(description)

        self.status_icon.set_from_icon_name(icon_name, *icon_args)
        self.status_spinner.set_visible(False)
        self.status_spinner.stop()

        if css_class:
            add_css_class(self.status_container, css_class)

    def on_show(self, *_args):

        if not self.is_visible():
            return

        self.status_spinner.stop()
        self.status_spinner.set_visible(False)

        self.check_status()

    def on_close(self, *_args):
        self.status_spinner.stop()
        self.status_spinner.set_visible(False)
