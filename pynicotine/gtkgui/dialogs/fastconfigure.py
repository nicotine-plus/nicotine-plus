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

import os

from gi.repository import Gtk

from pynicotine.config import config
from pynicotine.gtkgui.widgets.filechooser import choose_dir
from pynicotine.gtkgui.widgets.filechooser import FileChooserButton
from pynicotine.gtkgui.widgets.dialogs import dialog_show
from pynicotine.gtkgui.widgets.dialogs import set_dialog_properties
from pynicotine.gtkgui.widgets.theme import get_icon
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

        logo = get_icon("n")

        if logo:
            self.icon.set_from_pixbuf(logo)
        else:
            self.icon.set_property("icon-name", config.application_id)

        # Page specific, sharepage
        self.downloaddir = FileChooserButton(self.downloaddir, self.FastConfigureDialog, "folder")

        self.shared_folders = None
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
        self.shared_folders = config.sections["transfers"]["shared"][:]

        if config.sections['transfers']['downloaddir']:
            self.downloaddir.set_path(
                config.sections['transfers']['downloaddir']
            )

        self.sharelist.clear()

        for entry in self.shared_folders:
            virtual_name, path = entry
            self.sharelist.insert_with_valuesv(-1, self.column_numbers, [str(virtual_name), str(path)])

        # completepage
        import urllib.parse

        login = urllib.parse.quote(config.sections["server"]["login"])
        url = config.privileges_url % login
        text = "<a href='" + url + "' title='" + url + "'>" + _("Get Soulseek Privileges…") + "</a>"
        self.privileges.set_markup(text)
        self.privileges.connect("activate-link", lambda x, url: open_uri(url))

        dialog_show(self.FastConfigureDialog)

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
            if len(self.username.get_text()) > 0 and len(self.password.get_text()) > 0:
                complete = True

        elif name == 'portpage':
            complete = True

        elif name == 'sharepage':
            if self.downloaddir.get_path():
                complete = True

        elif name == 'summarypage':
            complete = True

        self.FastConfigureDialog.set_page_complete(page, complete)

    def on_entry_changed(self, *args):
        self.reset_completeness()

    def on_add_share_selected(self, selected, data):

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
            self.shared_folders.append((virtual, folder))

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
        self.username.grab_focus()

    def on_prepare(self, *args):
        self.reset_completeness()

    def on_close(self, *args):

        # userpasspage
        config.sections["server"]["login"] = self.username.get_text()
        config.sections["server"]["passw"] = self.password.get_text()

        # sharepage
        config.sections['transfers']['downloaddir'] = self.downloaddir.get_path()
        config.sections["transfers"]["shared"] = self.shared_folders

        # Rescan shares
        self.frame.np.shares.rescan_shares()
        self.frame.np.connect()

        self.FastConfigureDialog.destroy()

    def on_cancel(self, *args):
        self.FastConfigureDialog.destroy()
