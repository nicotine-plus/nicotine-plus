# COPYRIGHT (C) 2020-2021 Nicotine+ Team
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

from gi.repository import Gdk
from gi.repository import Gtk

from pynicotine.config import config
from pynicotine.gtkgui.widgets.filechooser import choose_dir
from pynicotine.gtkgui.widgets.filechooser import FileChooserButton
from pynicotine.gtkgui.widgets.dialogs import dialog_hide
from pynicotine.gtkgui.widgets.dialogs import entry_dialog
from pynicotine.gtkgui.widgets.dialogs import message_dialog
from pynicotine.gtkgui.widgets.dialogs import set_dialog_properties
from pynicotine.gtkgui.widgets.treeview import initialise_columns
from pynicotine.gtkgui.widgets.ui import UserInterface
from pynicotine.utils import open_uri


class FastConfigureAssistant(UserInterface):

    def __init__(self, frame):

        super().__init__("ui/dialogs/fastconfigure.ui")

        self.frame = frame
        set_dialog_properties(self.FastConfigureDialog, frame.MainWindow)

        for page in (self.welcomepage, self.userpasspage, self.portpage, self.sharepage, self.summarypage):
            self.FastConfigureDialog.append_page(page)

            if Gtk.get_major_version() == 3:
                self.FastConfigureDialog.child_set_property(page, "has-padding", False)

        self.FastConfigureDialog.set_page_type(self.welcomepage, Gtk.AssistantPageType.CUSTOM)
        self.FastConfigureDialog.set_page_type(self.summarypage, Gtk.AssistantPageType.SUMMARY)

        # Page specific, sharepage
        self.downloaddir = FileChooserButton(self.downloaddir, self.FastConfigureDialog, "folder")

        self.sharelist = Gtk.ListStore(
            str,
            str
        )

        self.column_numbers = list(range(self.sharelist.get_n_columns()))
        initialise_columns(
            None, self.shareddirectoriestree,
            ["virtual_folder", _("Virtual Folder"), 0, "text", None],
            ["folder", _("Folder"), 0, "text", None]
        )

        self.shareddirectoriestree.set_model(self.sharelist)

    def show(self):

        if config.need_config():
            self.cancel_button.hide()

        # userpasspage
        self.username.set_text(
            config.sections["server"]["login"]
        )
        self.password.set_text(
            config.sections["server"]["passw"]
        )

        # portpage
        url = config.portchecker_url % str(self.frame.np.protothread.listenport)
        text = "<a href='" + url + "' title='" + url + "'>" + _("Check Port Status") + "</a>"
        self.checkmyport.set_markup(text)
        self.checkmyport.connect("activate-link", lambda x, url: open_uri(url))

        # sharepage
        if config.sections['transfers']['downloaddir']:
            self.downloaddir.set_path(
                config.sections['transfers']['downloaddir']
            )

        self.sharelist.clear()

        for entry in config.sections["transfers"]["shared"]:
            virtual_name, path = entry

            if isinstance(virtual_name, str) and isinstance(path, str):
                self.add_shared_folder(virtual_name, path)

        # completepage
        import urllib.parse

        login = urllib.parse.quote(config.sections["server"]["login"])
        url = config.privileges_url % login
        text = "<a href='" + url + "' title='" + url + "'>" + _("Get Soulseek Privileges…") + "</a>"
        self.privileges.set_markup(text)
        self.privileges.connect("activate-link", lambda x, url: open_uri(url))

        self.FastConfigureDialog.present_with_time(Gdk.CURRENT_TIME)

    def reset_completeness(self):
        """ Turns on the complete flag if everything required is filled in. """

        complete = False
        pageid = self.FastConfigureDialog.get_current_page()
        page = self.FastConfigureDialog.get_nth_page(pageid)

        if not page:
            return

        name = Gtk.Buildable.get_name(page)

        if name == 'welcomepage':
            complete = True

        elif name == 'userpasspage':
            if (len(self.username.get_text()) > 0 and len(self.password.get_text()) > 0):
                complete = True

        elif name == 'portpage':
            complete = True

        elif name == 'sharepage':
            if self.downloaddir.get_path():
                complete = True

        elif name == 'summarypage':
            complete = True

        self.FastConfigureDialog.set_page_complete(page, complete)

    def get_shared_folders(self):

        iterator = self.sharelist.get_iter_first()
        dirs = []

        while iterator is not None:
            dirs.append(
                (
                    self.sharelist.get_value(iterator, 0),
                    self.sharelist.get_value(iterator, 1)
                )
            )
            iterator = self.sharelist.iter_next(iterator)

        return dirs

    def add_shared_folder(self, virtual_name, path):

        iterator = self.sharelist.get_iter_first()

        while iterator is not None:

            if path == self.sharelist.get_value(iterator, 1):
                return

            iterator = self.sharelist.iter_next(iterator)

        self.sharelist.insert_with_valuesv(-1, self.column_numbers, [virtual_name, path])

    def on_entry_changed(self, *args):
        self.reset_completeness()

    def on_add_share_response(self, dialog, response_id, directory):

        virtual = dialog.get_response_value()
        dialog.destroy()

        if response_id != Gtk.ResponseType.OK:
            return

        # If the virtual name is empty
        if not virtual:
            message_dialog(
                parent=self.FastConfigureDialog,
                title=_("Unable to Share Folder"),
                message=_("The chosen virtual name is empty")
            )
            return

        # Remove slashes from share name to avoid path conflicts
        virtual = virtual.replace('/', '_').replace('\\', '_')

        # We get the current defined shares from the treeview
        model, paths = self.shareddirectoriestree.get_selection().get_selected_rows()

        iterator = model.get_iter_first()

        while iterator is not None:

            # We reject the share if the virtual share name is already used
            if virtual == model.get_value(iterator, 0):
                message_dialog(
                    parent=self.FastConfigureDialog,
                    title=_("Unable to Share Folder"),
                    message=_("The chosen virtual name already exists")
                )
                return

            # We also reject the share if the directory is already used
            if directory == model.get_value(iterator, 1):
                message_dialog(
                    parent=self.FastConfigureDialog,
                    title=_("Unable to Share Folder"),
                    message=_("The chosen folder is already shared")
                )
                return

            iterator = model.iter_next(iterator)

        # The share is unique: we can add it
        self.add_shared_folder(virtual, directory)

    def on_add_share_selected(self, selected, data):

        for folder in selected:

            entry_dialog(
                parent=self.FastConfigureDialog,
                title=_("Virtual Name"),
                message=_("Enter virtual name for '%(dir)s':") % {'dir': folder},
                callback=self.on_add_share_response,
                callback_data=folder
            )

    def on_add_share(self, *args):

        choose_dir(
            parent=self.FastConfigureDialog,
            title=_("Add a Shared Folder"),
            callback=self.on_add_share_selected
        )

    def on_remove_share(self, *args):

        model, paths = self.shareddirectoriestree.get_selection().get_selected_rows()

        for path in reversed(paths):
            model.remove(model.get_iter(path))

    def on_set_up(self, *args):
        self.FastConfigureDialog.next_page()

    def on_prepare(self, *args):
        self.reset_completeness()

    def on_close(self, *args):

        # userpasspage
        config.sections["server"]["login"] = self.username.get_text()
        config.sections["server"]["passw"] = self.password.get_text()

        # sharepage
        config.sections['transfers']['downloaddir'] = self.downloaddir.get_path()
        config.sections["transfers"]["shared"] = self.get_shared_folders()

        dialog_hide(self.FastConfigureDialog)

        # Rescan public shares
        self.frame.np.shares.rescan_public_shares()

        # Rescan buddy shares if needed
        if config.sections["transfers"]["enablebuddyshares"]:
            self.frame.np.shares.rescan_buddy_shares()

        self.frame.np.connect()

    def on_cancel(self, *args):
        dialog_hide(self.FastConfigureDialog)
        return True
