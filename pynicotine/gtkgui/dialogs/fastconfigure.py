# COPYRIGHT (C) 2020-2022 Nicotine+ Contributors
# COPYRIGHT (C) 2016-2017 Michael Labouebe <gfarmerfr@free.fr>
# COPYRIGHT (C) 2009-2011 Quinox <quinox@users.sf.net>
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

import os

from gi.repository import Gtk

from pynicotine.config import config
from pynicotine.gtkgui.widgets.filechooser import FileChooserButton
from pynicotine.gtkgui.widgets.filechooser import FolderChooser
from pynicotine.gtkgui.widgets.dialogs import Dialog
from pynicotine.gtkgui.widgets.dialogs import EntryDialog
from pynicotine.gtkgui.widgets.treeview import initialise_columns
from pynicotine.gtkgui.widgets.ui import UserInterface
from pynicotine.utils import open_uri


class FastConfigure(UserInterface, Dialog):

    def __init__(self, frame, core):

        self.core = core
        self.rescan_required = False
        self.finished = False

        UserInterface.__init__(self, "ui/dialogs/fastconfigure.ui")
        (
            self.account_page,
            self.check_port_label,
            self.download_folder_button,
            self.main_icon,
            self.next_button,
            self.password_entry,
            self.port_page,
            self.previous_button,
            self.share_page,
            self.shares_list_view,
            self.stack,
            self.summary_page,
            self.username_entry,
            self.welcome_page
        ) = self.widgets

        self.pages = [self.welcome_page, self.account_page, self.port_page, self.share_page, self.summary_page]

        Dialog.__init__(
            self,
            parent=frame.window,
            content_box=self.stack,
            buttons=[(self.previous_button, Gtk.ResponseType.HELP),
                     (self.next_button, Gtk.ResponseType.APPLY)],
            default_response=Gtk.ResponseType.APPLY,
            show_callback=self.on_show,
            close_callback=self.on_close,
            width=720,
            height=450,
            resizable=False,
            close_destroy=False
        )

        self.main_icon.set_property("icon-name", config.application_id)

        # Page specific, share_page
        self.download_folder_button = FileChooserButton(
            self.download_folder_button, self.dialog, "folder", selected_function=self.on_download_folder_selected)

        self.shared_folders = None
        self.sharelist = Gtk.ListStore(
            str,
            str
        )

        self.column_numbers = list(range(self.sharelist.get_n_columns()))
        cols = initialise_columns(
            frame, None, self.shares_list_view,
            ["virtual_folder", _("Virtual Folder"), 1, "text", None],
            ["folder", _("Folder"), 125, "text", None]
        )

        cols["virtual_folder"].set_expand(True)
        cols["folder"].set_expand(True)

        self.shares_list_view.set_model(self.sharelist)
        self.reset_completeness()

    def reset_completeness(self):
        """ Turns on the complete flag if everything required is filled in. """

        page = self.stack.get_visible_child()
        page_complete = (
            (page in (self.welcome_page, self.port_page, self.summary_page))
            or (page == self.account_page and self.username_entry.get_text() and self.password_entry.get_text())
            or (page == self.share_page and self.download_folder_button.get_path())
        )
        self.finished = (page == self.summary_page)
        next_label = _("_Finish") if page == self.summary_page else _("_Next")

        if self.next_button.get_label() != next_label:
            self.next_button.set_label(next_label)

        self.next_button.set_sensitive(page_complete)

        for button in (self.previous_button, self.next_button):
            button.set_visible(page != self.welcome_page)

    def on_entry_changed(self, *_args):
        self.reset_completeness()

    def on_download_folder_selected(self):
        config.sections['transfers']['downloaddir'] = self.download_folder_button.get_path()

    def on_add_share_selected(self, selected, _data):

        shared = config.sections["transfers"]["shared"]
        buddy_shared = config.sections["transfers"]["buddyshared"]

        for folder in selected:

            # If the folder is already shared
            if folder in (x[1] for x in shared + buddy_shared):
                return

            virtual = os.path.basename(os.path.normpath(folder))

            # Remove slashes from share name to avoid path conflicts
            virtual = virtual.replace('/', '_').replace('\\', '_')
            virtual_final = virtual

            counter = 1
            while virtual_final in (x[0] for x in shared + buddy_shared):
                virtual_final = virtual + str(counter)
                counter += 1

            # The share is unique: we can add it
            self.sharelist.insert_with_valuesv(-1, self.column_numbers, [virtual, folder])
            config.sections["transfers"]["shared"].append((virtual, folder))

            self.rescan_required = True

    def on_add_share(self, *_args):

        FolderChooser(
            parent=self.dialog,
            title=_("Add a Shared Folder"),
            callback=self.on_add_share_selected,
            multiple=True
        ).show()

    def on_edit_share_response(self, dialog, _response_id, iterator):

        virtual = dialog.get_entry_value()

        if not virtual:
            return

        shared = config.sections["transfers"]["shared"]
        buddy_shared = config.sections["transfers"]["buddyshared"]

        virtual = self.core.shares.get_normalized_virtual_name(virtual, shared_folders=(shared + buddy_shared))
        folder = self.sharelist.get_value(iterator, 1)
        old_virtual = self.sharelist.get_value(iterator, 0)
        old_mapping = (old_virtual, folder)
        new_mapping = (virtual, folder)

        shared.remove(old_mapping)
        shared.append(new_mapping)

        self.sharelist.set_value(iterator, 0, virtual)
        self.rescan_required = True

    def on_edit_share(self, *_args):

        for iterator in self.shares_list_view.get_selected_rows():
            virtual_name = self.shares_list_view.get_row_value(iterator, 0)
            folder = self.shares_list_view.get_row_value(iterator, 1)

            EntryDialog(
                parent=self.dialog,
                title=_("Edit Shared Folder"),
                message=_("Enter new virtual name for '%(dir)s':") % {'dir': folder},
                default=virtual_name,
                callback=self.on_edit_share_response,
                callback_data=iterator
            ).show()
            return

    def on_remove_share(self, *_args):

        model, paths = self.shares_list_view.get_selection().get_selected_rows()

        for path in reversed(paths):
            iterator = model.get_iter(path)
            virtual = model.get_value(iterator, 0)
            folder = model.get_value(iterator, 1)

            config.sections["transfers"]["shared"].remove((virtual, folder))
            model.remove(iterator)
            self.rescan_required = True

    def on_page_change(self, *_args):

        page = self.stack.get_visible_child()

        if page == self.account_page:
            self.username_entry.grab_focus()

        self.reset_completeness()

    def on_next(self, *_args):

        if self.finished:
            self.close()
            return

        start_page_index = self.pages.index(self.stack.get_visible_child()) + 1

        for page in self.pages[start_page_index:]:
            if page.get_visible():
                self.next_button.grab_focus()
                self.stack.set_visible_child(page)
                return

    def on_previous(self, *_args):

        start_page_index = self.pages.index(self.stack.get_visible_child())

        for page in reversed(self.pages[:start_page_index]):
            if page.get_visible():
                self.previous_button.grab_focus()
                self.stack.set_visible_child(page)
                return

    def on_close(self, *_args):

        if self.rescan_required:
            self.core.shares.rescan_shares()

        if not self.finished:
            return True

        # account_page
        if config.need_config():
            config.sections["server"]["login"] = self.username_entry.get_text()
            config.sections["server"]["passw"] = self.password_entry.get_text()

        self.core.connect()
        return True

    def on_show(self, *_args):

        self.rescan_required = False
        self.stack.set_visible_child(self.welcome_page)

        # account_page
        self.account_page.set_visible(config.need_config())

        self.username_entry.set_text(config.sections["server"]["login"])
        self.password_entry.set_text(config.sections["server"]["passw"])

        # port_page
        url = config.portchecker_url % str(self.core.protothread.listenport)
        text = "<a href='" + url + "' title='" + url + "'>" + _("Check Port Status") + "</a>"
        self.check_port_label.set_markup(text)
        self.check_port_label.connect("activate-link", lambda x, url: open_uri(url))

        # share_page
        if config.sections['transfers']['downloaddir']:
            self.download_folder_button.set_path(
                config.sections['transfers']['downloaddir']
            )

        self.sharelist.clear()

        for entry in config.sections["transfers"]["shared"]:
            virtual_name, path = entry
            self.sharelist.insert_with_valuesv(-1, self.column_numbers, [str(virtual_name), str(path)])
