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

from pynicotine.gtkgui.dialogs import choose_dir
from pynicotine.gtkgui.dialogs import combo_box_dialog
from pynicotine.gtkgui.utils import FileChooserButton
from pynicotine.gtkgui.utils import initialise_columns
from pynicotine.gtkgui.utils import load_ui_elements
from pynicotine.gtkgui.utils import open_uri


class FastConfigureAssistant(object):

    def __init__(self, frame):

        self.frame = frame
        self.config = frame.np.config

        load_ui_elements(self, os.path.join(self.frame.gui_dir, "ui", "dialogs", "fastconfigure.ui"))
        self.FastConfigureDialog.set_transient_for(self.frame.MainWindow)

        self.downloaddir = FileChooserButton(self.downloaddir, self.FastConfigureDialog, "folder")

        # Page specific, sharepage
        self.sharelist = Gtk.ListStore(
            str,
            str
        )

        initialise_columns(
            None,
            self.shareddirectoriestree,
            ["virtual_folder", _("Virtual Folder"), 0, "text", None],
            ["folder", _("Folder"), 0, "text", None]
        )

        self.shareddirectoriestree.set_model(self.sharelist)

    def show(self):

        # userpasspage
        self.username.set_text(
            self.config.sections["server"]["login"]
        )
        self.password.set_text(
            self.config.sections["server"]["passw"]
        )

        # sharepage
        if self.config.sections['transfers']['downloaddir']:
            self.downloaddir.set_path(
                self.config.sections['transfers']['downloaddir']
            )

        self.sharelist.clear()

        for directory in self.config.sections["transfers"]["shared"]:
            self.add_shared_folder(directory)

        self.FastConfigureDialog.show()

    def store(self):

        # userpasspage
        self.config.sections["server"]["login"] = self.username.get_text()
        self.config.sections["server"]["passw"] = self.password.get_text()

        # sharepage
        self.config.sections['transfers']['downloaddir'] = self.downloaddir.get_path()
        self.config.sections["transfers"]["shared"] = self.get_shared_folders()

    def reset_completeness(self):
        """Turns on the complete flag if everything required is filled in."""

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

    def add_shared_folder(self, directory):

        iterator = self.sharelist.get_iter_first()

        while iterator is not None:

            if directory[1] == self.sharelist.get_value(iterator, 1):
                return

            iterator = self.sharelist.iter_next(iterator)

        self.sharelist.append([
            directory[0],
            directory[1]
        ])

    def on_prepare(self, widget, page):
        self.reset_completeness()

    def on_entry_changed(self, widget, *args):
        self.reset_completeness()

    def on_check_port_status(self, widget):

        open_uri(
            '='.join([
                'http://tools.slsknet.org/porttest.php?port',
                str(self.frame.np.waitport)
            ]),
            self.FastConfigureDialog
        )

    def on_add_share(self, widget):

        selected = choose_dir(
            self.FastConfigureDialog.get_toplevel(),
            title=_("Add a Shared Folder")
        )

        if selected:

            for directory in selected:

                virtual = combo_box_dialog(
                    parent=self.FastConfigureDialog,
                    title=_("Virtual Name"),
                    message=_("Enter virtual name for '%(dir)s':") % {'dir': directory}
                )

                # If the virtual name is empty
                if virtual == '' or virtual is None:

                    dlg = Gtk.MessageDialog(
                        transient_for=self.FastConfigureDialog,
                        flags=0,
                        type=Gtk.MessageType.WARNING,
                        buttons=Gtk.ButtonsType.OK,
                        text=_("Warning")
                    )
                    dlg.format_secondary_text(_("The chosen virtual name is empty"))
                    dlg.run()
                    dlg.destroy()

                else:
                    # Remove slashes from share name to avoid path conflicts
                    virtual = virtual.replace('/', '_').replace('\\', '_')

                    # We get the current defined shares from the treeview
                    model, paths = self.shareddirectoriestree.get_selection().get_selected_rows()

                    iterator = model.get_iter_first()

                    while iterator is not None:

                        # We reject the share if the virtual share name is already used
                        if virtual == model.get_value(iterator, 0):

                            dlg = Gtk.MessageDialog(
                                transient_for=self.FastConfigureDialog,
                                flags=0,
                                type=Gtk.MessageType.WARNING,
                                buttons=Gtk.ButtonsType.OK,
                                text=_("Warning")
                            )
                            dlg.format_secondary_text(_("The chosen virtual name already exists"))
                            dlg.run()
                            dlg.destroy()
                            return

                        # We also reject the share if the directory is already used
                        elif directory == model.get_value(iterator, 1):

                            dlg = Gtk.MessageDialog(
                                transient_for=self.FastConfigureDialog,
                                flags=0,
                                type=Gtk.MessageType.WARNING,
                                buttons=Gtk.ButtonsType.OK,
                                text=_("Warning")
                            )
                            dlg.format_secondary_text(_("The chosen folder is already shared"))
                            dlg.run()
                            dlg.destroy()
                            return

                        else:
                            iterator = model.iter_next(iterator)

                    # The share is unique: we can add it
                    self.add_shared_folder((virtual, directory))

    def on_remove_share(self, widget):

        model, paths = self.shareddirectoriestree.get_selection().get_selected_rows()

        for path in paths:
            self.sharelist.remove(self.sharelist.get_iter(path))

    def on_apply(self, widget):

        self.store()
        self.FastConfigureDialog.hide()

        # Rescan public shares if needed
        if not self.config.sections["transfers"]["friendsonly"]:
            self.frame.on_rescan()

        # Rescan buddy shares if needed
        if self.config.sections["transfers"]["enablebuddyshares"]:
            self.frame.on_buddy_rescan()

        if not self.frame.np.active_server_conn:
            self.frame.on_connect()

    def on_close(self, widget):
        self.FastConfigureDialog.hide()
