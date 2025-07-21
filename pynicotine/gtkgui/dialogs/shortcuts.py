# SPDX-FileCopyrightText: 2021-2023 Nicotine+ Contributors
# SPDX-License-Identifier: GPL-3.0-or-later

from gi.repository import Gtk

from pynicotine.gtkgui.application import GTK_API_VERSION
from pynicotine.gtkgui.widgets.dialogs import Dialog
from pynicotine.gtkgui.widgets.theme import add_css_class


class Shortcuts(Dialog):

    def __init__(self, application):

        self.application = application
        self.scrollable = Gtk.ScrolledWindow(
            hscrollbar_policy=Gtk.PolicyType.NEVER, propagate_natural_height=True, propagate_natural_width=True,
            visible=True
        )
        self.container = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL, margin_start=18, margin_end=18, margin_top=14, margin_bottom=18,
            spacing=36, visible=True
        )

        super().__init__(
            parent=application.window,
            content_box=self.scrollable,
            title=_("Keyboard Shortcuts"),
            width=425,
            height=525
        )

        shortcut_groups = {
            _("General"): {
                _("Connect"): "app.connect",
                _("Disconnect"): "app.disconnect",
                _("Away"): "app.away-accel",
                _("Rescan Shares"): "app.rescan-shares",
                _("Keyboard Shortcuts"): "app.keyboard-shortcuts",
                _("Preferences"): "app.preferences",
                _("Confirm Quit"): "app.confirm-quit",
                _("Quit"): "app.force-quit"
            },
            _("View"): {
                _("Open Main Menu"): "win.main-menu",
                _("Open Context Menu"): "win.context-menu",
                _("Focus Next View"): "win.change-focus-view",
                _("Show Log Pane"): "win.show-log-pane"
            },
            _("Main Tabs"): {
                _("Change Active Tab"): "Alt+1...9",
            },
            _("Secondary Tabs"): {
                _("Go to Previous Tab"): "win.cycle-tabs-reverse",
                _("Go to Next Tab"): "win.cycle-tabs",
                _("Reopen Closed Tab"): "win.reopen-closed-tab",
                _("Close Tab"): "win.close-tab"
            },
            _("Lists"): {
                _("Copy Cell"): "accel.copy-clipboard",
                _("Select All"): "accel.select-all",
                _("Find"): "accel.find",
                _("Remove Row"): "accel.remove"
            },
            _("Editing"): {
                _("Cut"): "accel.cut-clipboard",
                _("Copy"): "accel.copy-clipboard",
                _("Paste"): "accel.paste-clipboard",
                _("Insert Emoji"): "accel.insert-emoji",
                _("Select All"): "accel.select-all",
                _("Find"): "accel.find",
                _("Find Next Match"): "accel.find-next-match",
                _("Find Previous Match"): "accel.find-previous-match"
            },
            _("File Transfers"): {
                _("Resume / Retry Transfer"): "accel.retry-transfer",
                _("Pause / Abort Transfer"): "accel.abort-transfer",
                _("File Properties"): "accel.file-properties"
            },
            _("Browse Shares"): {
                _("Download / Upload To"): "accel.download-to",
                _("File Properties"): "accel.file-properties",
                _("Save List to Disk"): "accel.save",
                _("Refresh"): "accel.refresh",
                _("Find"): "accel.find",
                _("Find Next Match"): "accel.find-next-match",
                _("Find Previous Match"): "accel.find-previous-match",
                _("Expand / Collapse All"): "accel.toggle-row-expand",
                _("Go to Parent Folder"): "accel.back"
            },
            _("File Search"): {
                _("Result Filters"): "accel.find",
                _("File Properties"): "accel.file-properties",
                _("Wishlist"): "app.wishlist"
            }
        }
        group_icons = {
            _("General"): "input-keyboard-symbolic",
            _("View"): "open-menu-symbolic",
            _("Main Tabs"): "view-grid-symbolic",
            _("Secondary Tabs"): "tab-new-symbolic",
            _("Lists"): "view-list-symbolic",
            _("Editing"): "document-edit-symbolic",
            _("File Transfers"): "folder-download-symbolic",
            _("Browse Shares"): "folder-symbolic",
            _("File Search"): "system-search-symbolic"
        }

        for group_name, shortcuts in shortcut_groups.items():
            icon_name = group_icons.get(group_name)
            section_container = self._create_shortcut_section(group_name, icon_name)

            for description, action_name in shortcuts.items():
                self._create_shortcut_row(section_container, description, action_name)

        if GTK_API_VERSION >= 4:
            self.scrollable.set_child(self.container)  # pylint: disable=no-member
        else:
            self.scrollable.add(self.container)        # pylint: disable=no-member

    def _create_shortcut_section(self, group_name, icon_name):

        section_container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12, visible=True)
        section_icon = Gtk.Image(icon_name=icon_name, visible=True)
        section_label = Gtk.Label(label=group_name, selectable=True, xalign=0, visible=True)
        section_label_container = Gtk.Box(margin_bottom=6, spacing=6, visible=True)

        add_css_class(section_label, "heading")

        if GTK_API_VERSION >= 4:
            section_label_container.append(section_icon)        # pylint: disable=no-member
            section_label_container.append(section_label)       # pylint: disable=no-member
            section_container.append(section_label_container)   # pylint: disable=no-member
            self.container.append(section_container)            # pylint: disable=no-member
        else:
            section_label_container.add(section_icon)           # pylint: disable=no-member
            section_label_container.add(section_label)          # pylint: disable=no-member
            section_container.add(section_label_container)      # pylint: disable=no-member
            self.container.add(section_container)               # pylint: disable=no-member

        return section_container

    def _create_shortcut_row(self, parent, description, action_name):

        accelerators = self.application.get_accels_for_action(action_name)

        if accelerators:
            *_args, key, mods = Gtk.accelerator_parse(accelerators[0])
            accelerator = Gtk.accelerator_get_label(key, mods)
        else:
            accelerator = action_name

        row = Gtk.Box(homogeneous=True, spacing=12, visible=True)
        accelerator_label = Gtk.Label(
            label=accelerator, selectable=True, xalign=0, yalign=0,
            visible=True
        )
        description_label = Gtk.Label(
            label=description, justify=Gtk.Justification.RIGHT, mnemonic_widget=accelerator_label,
            xalign=1, yalign=0, visible=True
        )

        add_css_class(description_label, "dim-label")

        if GTK_API_VERSION >= 4:
            row.append(description_label)  # pylint: disable=no-member
            row.append(accelerator_label)  # pylint: disable=no-member

            parent.append(row)             # pylint: disable=no-member
        else:
            row.add(description_label)     # pylint: disable=no-member
            row.add(accelerator_label)     # pylint: disable=no-member

            parent.add(row)                # pylint: disable=no-member

        return row
