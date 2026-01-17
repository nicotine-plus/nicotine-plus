# SPDX-FileCopyrightText: 2021-2025 Nicotine+ Contributors
# SPDX-License-Identifier: GPL-3.0-or-later

from gi.repository import Gtk

from pynicotine.gtkgui.application import GTK_API_VERSION
from pynicotine.gtkgui.widgets.dialogs import Dialog
from pynicotine.gtkgui.widgets.theme import add_css_class


class Shortcuts(Dialog):

    def __init__(self, application):

        self.scrollable = Gtk.ScrolledWindow(
            hscrollbar_policy=Gtk.PolicyType.NEVER, propagate_natural_height=True, propagate_natural_width=True,
            width_request=360, visible=True
        )
        self.container = Gtk.FlowBox(
            margin_start=24, margin_end=24, margin_top=14, margin_bottom=18, max_children_per_line=2,
            column_spacing=36, row_spacing=36, visible=True
        )

        super().__init__(
            application=application,
            content_box=self.scrollable,
            title=_("Keyboard Shortcuts"),
            width=800,
            height=600,
            resizable=False
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
                _("Next Widget"): "accel.focus-next-widget",
                _("Previous Widget"): "accel.focus-previous-widget",
                _("Main Menu"): "win.main-menu",
                _("Context Menu"): "win.context-menu",
                _("Change Main Tab"): ("accel.change-main-tab-start", "accel.change-main-tab-end"),
                _("Focus Top Bar"): "win.focus-top-bar",
                _("Focus Next View"): "win.change-focus-view",
                _("Show Log Pane"): "win.show-log-pane"
            },
            _("Secondary Tabs"): {
                _("Previous Tab"): "win.cycle-tabs-reverse",
                _("Next Tab"): "win.cycle-tabs",
                _("Reopen Tab"): "win.reopen-closed-tab",
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
                _("Next Match"): "accel.find-next-match",
                _("Previous Match"): "accel.find-previous-match"
            },
            _("Browse Shares"): {
                _("Transfer To"): "accel.download-to",
                _("File Properties"): "accel.file-properties",
                _("Save List to Disk"): "accel.save",
                _("Refresh"): "accel.refresh",
                _("Find"): "accel.find",
                _("Next Match"): "accel.find-next-match",
                _("Previous Match"): "accel.find-previous-match",
                _("Expand All"): "accel.toggle-row-expand"
            },
            _("File Search"): {
                _("Result Filters"): "accel.find",
                _("File Properties"): "accel.file-properties",
                _("Wishlist"): "app.wishlist"
            },
            _("File Transfers"): {
                _("Resume Transfer"): "accel.retry-transfer",
                _("Abort Transfer"): "accel.abort-transfer",
                _("File Properties"): "accel.file-properties"
            }
        }
        group_icons = {
            _("General"): "input-keyboard-symbolic",
            _("View"): "view-grid-symbolic",
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
        flowbox_child = Gtk.FlowBoxChild(child=section_container, visible=True)
        section_icon = Gtk.Image(icon_name=icon_name, visible=True)
        section_label = Gtk.Label(label=group_name, selectable=True, xalign=0, visible=True)
        section_label_container = Gtk.Box(margin_bottom=6, spacing=6, visible=True)

        add_css_class(section_label, "heading")

        if GTK_API_VERSION >= 4:
            flowbox_child.set_focusable(False)                  # pylint: disable=no-member
            section_label_container.append(section_icon)        # pylint: disable=no-member
            section_label_container.append(section_label)       # pylint: disable=no-member
            section_container.append(section_label_container)   # pylint: disable=no-member
            self.container.append(flowbox_child)                # pylint: disable=no-member
        else:
            flowbox_child.set_can_focus(False)
            section_label_container.add(section_icon)           # pylint: disable=no-member
            section_label_container.add(section_label)          # pylint: disable=no-member
            section_container.add(section_label_container)      # pylint: disable=no-member
            self.container.add(flowbox_child)                   # pylint: disable=no-member

        return section_container

    def _get_accelerator_label(self, action_name):

        accelerators = self.application.get_accels_for_action(action_name)
        *_args, key, mods = Gtk.accelerator_parse(accelerators[0])

        return Gtk.accelerator_get_label(key, mods)

    def _create_shortcut_row(self, parent, description, action_name):

        if isinstance(action_name, tuple):
            action_name_start, action_name_end, *_unused = action_name
            accelerator_start = self._get_accelerator_label(action_name_start)
            accelerator_end = self._get_accelerator_label(action_name_end)
            accelerator = f"{accelerator_start} … {accelerator_end}"
        else:
            accelerator = self._get_accelerator_label(action_name)

        row = Gtk.Box(spacing=12, visible=True)
        accelerator_label = Gtk.Label(
            label=accelerator, selectable=True, xalign=1, yalign=0, visible=True
        )
        description_label = Gtk.Label(
            label=description, mnemonic_widget=accelerator_label, hexpand=True, xalign=0, yalign=0,
            visible=True
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
