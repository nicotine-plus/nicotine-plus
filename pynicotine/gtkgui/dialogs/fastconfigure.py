# COPYRIGHT (C) 2020-2024 Nicotine+ Contributors
# COPYRIGHT (C) 2016-2017 Michael Labouebe <gfarmerfr@free.fr>
# COPYRIGHT (C) 2009-2011 quinox <quinox@users.sf.net>
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

import pynicotine
from pynicotine.config import config
from pynicotine.core import core
from pynicotine.gtkgui.application import GTK_API_VERSION
from pynicotine.gtkgui.widgets import ui
from pynicotine.gtkgui.widgets.filechooser import FileChooserButton
from pynicotine.gtkgui.widgets.filechooser import FolderChooser
from pynicotine.gtkgui.widgets.dialogs import Dialog
from pynicotine.gtkgui.widgets.dialogs import EntryDialog
from pynicotine.gtkgui.widgets.treeview import TreeView
from pynicotine.slskmessages import UserStatus


class FastConfigure(Dialog):

    def __init__(self, application):

        self.invalid_password = False
        self.rescan_required = False
        self.finished = False

        (
            self.account_page,
            self.download_folder_container,
            self.invalid_password_label,
            self.listen_port_entry,
            self.main_icon,
            self.next_button,
            self.next_label,
            self.password_entry,
            self.port_page,
            self.previous_button,
            self.previous_label,
            self.set_up_button,
            self.share_page,
            self.shares_list_container,
            self.stack,
            self.summary_page,
            self.username_entry,
            self.welcome_page
        ) = ui.load(scope=self, path="dialogs/fastconfigure.ui")

        self.pages = [self.welcome_page, self.account_page, self.port_page, self.share_page, self.summary_page]

        super().__init__(
            parent=application.window,
            content_box=self.stack,
            buttons_start=(self.previous_button,),
            buttons_end=(self.next_button,),
            default_button=self.next_button,
            show_callback=self.on_show,
            close_callback=self.on_close,
            title=_("Setup Assistant"),
            width=720,
            height=450,
            show_title=False
        )

        icon_name = pynicotine.__application_id__
        icon_args = (Gtk.IconSize.BUTTON,) if GTK_API_VERSION == 3 else ()  # pylint: disable=no-member

        self.main_icon.set_from_icon_name(icon_name, *icon_args)
        self.username_entry.set_max_length(core.users.USERNAME_MAX_LENGTH)

        self.download_folder_button = FileChooserButton(
            self.download_folder_container, window=self, chooser_type="folder",
            selected_function=self.on_download_folder_selected,
            show_open_external_button=not application.isolated_mode
        )

        self.shares_list_view = TreeView(
            application.window, parent=self.shares_list_container, multi_select=True,
            activate_row_callback=self.on_edit_shared_folder,
            delete_accelerator_callback=self.on_remove_shared_folder,
            columns={
                "virtual_name": {
                    "column_type": "text",
                    "title": _("Virtual Folder"),
                    "width": 1,
                    "expand_column": True,
                    "default_sort_type": "ascending"
                },
                "folder": {
                    "column_type": "text",
                    "title": _("Folder"),
                    "width": 125,
                    "expand_column": True
                }
            }
        )

        self.reset_completeness()

    def destroy(self):

        self.download_folder_button.destroy()
        self.shares_list_view.destroy()

        super().destroy()

    def reset_completeness(self):
        """Turns on the complete flag if everything required is filled in."""

        page = self.stack.get_visible_child()
        page_complete = (
            (page in (self.welcome_page, self.port_page, self.summary_page))
            or (page == self.account_page and self.username_entry.get_text() and self.password_entry.get_text())
            or (page == self.share_page and self.download_folder_button.get_path())
        )
        self.finished = (page == self.account_page if self.invalid_password else page == self.summary_page)
        previous_label = _("_Cancel") if self.invalid_password else _("_Previous")
        next_label = _("_Finish") if self.finished else _("_Next")
        show_buttons = (page != self.welcome_page)

        self.set_show_title_buttons(not show_buttons)

        if self.previous_label.get_label() != previous_label:
            self.previous_label.set_label(previous_label)

        if self.next_label.get_label() != next_label:
            self.next_label.set_label(next_label)

        self.previous_button.set_visible(show_buttons)
        self.next_button.set_visible(show_buttons)
        self.next_button.set_sensitive(page_complete)

    def on_entry_changed(self, *_args):
        self.reset_completeness()

    def on_user_entry_activate(self, *_args):

        if not self.username_entry.get_text():
            self.username_entry.grab_focus()
            return

        if not self.password_entry.get_text():
            self.password_entry.grab_focus()
            return

        self.on_next()

    def on_download_folder_selected(self):
        config.sections["transfers"]["downloaddir"] = self.download_folder_button.get_path()

    def on_add_shared_folder_selected(self, selected, _data):

        for folder_path in selected:
            virtual_name = core.shares.add_share(folder_path)

            if virtual_name:
                self.shares_list_view.add_row([virtual_name, folder_path])
                self.rescan_required = True

    def on_add_shared_folder(self, *_args):

        FolderChooser(
            parent=self,
            title=_("Add a Shared Folder"),
            callback=self.on_add_shared_folder_selected,
            select_multiple=True
        ).present()

    def on_edit_shared_folder_response(self, dialog, _response_id, iterator):

        new_virtual_name = dialog.get_entry_value()
        old_virtual_name = self.shares_list_view.get_row_value(iterator, "virtual_name")

        if new_virtual_name == old_virtual_name:
            return

        self.rescan_required = True
        folder_path = self.shares_list_view.get_row_value(iterator, "folder")
        orig_iterator = self.shares_list_view.iterators[old_virtual_name]

        self.shares_list_view.remove_row(orig_iterator)
        core.shares.remove_share(old_virtual_name)
        new_virtual_name = core.shares.add_share(
            folder_path, virtual_name=new_virtual_name, validate_path=False
        )

        self.shares_list_view.add_row([new_virtual_name, folder_path])

    def on_edit_shared_folder(self, *_args):

        for iterator in self.shares_list_view.get_selected_rows():
            virtual_name = self.shares_list_view.get_row_value(iterator, "virtual_name")
            folder_path = self.shares_list_view.get_row_value(iterator, "folder")

            EntryDialog(
                parent=self,
                title=_("Edit Shared Folder"),
                message=_("Enter new virtual name for '%(dir)s':") % {"dir": folder_path},
                default=virtual_name,
                action_button_label=_("_Edit"),
                callback=self.on_edit_shared_folder_response,
                callback_data=iterator
            ).present()
            return

    def on_remove_shared_folder(self, *_args):

        for iterator in reversed(list(self.shares_list_view.get_selected_rows())):
            virtual_name = self.shares_list_view.get_row_value(iterator, "virtual_name")
            orig_iterator = self.shares_list_view.iterators[virtual_name]

            core.shares.remove_share(virtual_name)
            self.shares_list_view.remove_row(orig_iterator)

            self.rescan_required = True

    def on_page_change(self, *_args):

        page = self.stack.get_visible_child()

        if page == self.welcome_page:
            self.set_up_button.grab_focus()

        elif page == self.account_page:
            self.username_entry.grab_focus_without_selecting()

        self.reset_completeness()

    def on_next(self, *_args):

        if self.finished:
            self.on_finished()
            return

        start_page_index = self.pages.index(self.stack.get_visible_child()) + 1

        for page in self.pages[start_page_index:]:
            if page.get_visible():
                self.next_button.grab_focus()
                self.stack.set_visible_child(page)
                return

    def on_previous(self, *_args):

        if self.invalid_password:
            self.close()
            return

        start_page_index = self.pages.index(self.stack.get_visible_child())

        for page in reversed(self.pages[:start_page_index]):
            if page.get_visible():
                self.previous_button.grab_focus()
                self.stack.set_visible_child(page)
                return

    def on_finished(self, *_args):

        if self.rescan_required:
            core.shares.rescan_shares()

        # port_page
        listen_port = self.listen_port_entry.get_value_as_int()
        config.sections["server"]["portrange"] = (listen_port, listen_port)

        # account_page
        if self.invalid_password or config.need_config():
            config.sections["server"]["login"] = self.username_entry.get_text()
            config.sections["server"]["passw"] = self.password_entry.get_text()

        if core.users.login_status == UserStatus.OFFLINE:
            core.connect()

        self.close()

    def on_close(self, *_args):
        self.invalid_password = False
        self.rescan_required = False

    def on_show(self, *_args):

        transition_type = self.stack.get_transition_type()
        self.stack.set_transition_type(Gtk.StackTransitionType.NONE)

        self.account_page.set_visible(self.invalid_password or config.need_config())
        self.stack.set_visible_child(self.account_page if self.invalid_password else self.welcome_page)

        self.stack.set_transition_type(transition_type)
        self.on_page_change()

        # account_page
        if self.invalid_password:
            self.invalid_password_label.set_label(
                _("User %s already exists, and the password you entered is invalid. Please choose another username "
                  "if this is your first time logging in.") % config.sections["server"]["login"])

        self.invalid_password_label.set_visible(self.invalid_password)

        self.username_entry.set_text(config.sections["server"]["login"])
        self.password_entry.set_text(config.sections["server"]["passw"])

        # port_page
        listen_port, _unused_port = config.sections["server"]["portrange"]
        self.listen_port_entry.set_value(listen_port)

        # share_page
        self.download_folder_button.set_path(core.downloads.get_default_download_folder())

        self.shares_list_view.clear()
        self.shares_list_view.freeze()

        for virtual_name, folder_path, *_unused in config.sections["transfers"]["shared"]:
            self.shares_list_view.add_row([virtual_name, folder_path], select_row=False)

        self.shares_list_view.unfreeze()
