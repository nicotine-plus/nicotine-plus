# COPYRIGHT (C) 2020 Nicotine+ Team
# COPYRIGHT (C) 2016-2017 Michael Labouebe <gfarmerfr@free.fr>
# COPYRIGHT (C) 2013 SeeSchloss <see@seos.fr>
# COPYRIGHT (C) 2009-2010 Quinox <quinox@users.sf.net>
# COPYRIGHT (C) 2006-2009 Daelstorm <daelstorm@gmail.com>
# COPYRIGHT (C) 2003-2004 Hyriand <hyriand@thegraveyard.org>
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
from gettext import gettext as _
from sys import maxsize

from gi.repository import Gdk
from gi.repository import GObject
from gi.repository import Gtk

from _thread import start_new_thread
from pynicotine import slskmessages
from pynicotine.gtkgui.dialogs import choose_dir
from pynicotine.gtkgui.dialogs import combo_box_dialog
from pynicotine.gtkgui.utils import hide_columns
from pynicotine.gtkgui.utils import human_size
from pynicotine.gtkgui.utils import InfoBar
from pynicotine.gtkgui.utils import initialise_columns
from pynicotine.gtkgui.utils import load_ui_elements
from pynicotine.gtkgui.utils import open_file_path
from pynicotine.gtkgui.utils import PopupMenu
from pynicotine.gtkgui.utils import set_treeview_selected_row
from pynicotine.gtkgui.utils import update_widget_visuals
from pynicotine.logfacility import log
from pynicotine.utils import clean_file
from pynicotine.utils import get_result_bitrate_length


class UserBrowse:

    def __init__(self, userbrowses, user):

        self.userbrowses = userbrowses
        self.frame = userbrowses.frame

        # Build the window
        load_ui_elements(self, os.path.join(self.frame.gui_dir, "ui", "userbrowse.ui"))
        self.info_bar = InfoBar(self.InfoBar, Gtk.MessageType.INFO)

        self.user = user
        self.conn = None

        # selected_folder is the current selected folder
        self.selected_folder = None
        self.search_list = []
        self.query = None
        self.search_position = 0
        self.selected_files = []

        self.shares = []

        # Iters for current DirStore
        self.directories = {}

        # Iters for current FileStore
        self.files = {}
        self.totalsize = 0

        self.dir_store = Gtk.TreeStore(str, str)

        self.FolderTreeView.set_headers_visible(True)
        self.FolderTreeView.set_enable_tree_lines(True)

        cols = initialise_columns(
            self.FolderTreeView,
            [_("Directories"), -1, "text"]  # 0
        )
        cols[0].set_sort_column_id(0)

        self.popup_menu_users = PopupMenu(self.frame, False)
        self.popup_menu_users2 = PopupMenu(self.frame, False)
        for menu in [self.popup_menu_users, self.popup_menu_users2]:
            menu.setup(
                ("#" + _("Send _message"), menu.on_send_message),
                ("#" + _("Show IP a_ddress"), menu.on_show_ip_address),
                ("#" + _("Get user i_nfo"), menu.on_get_user_info),
                ("#" + _("Gi_ve privileges"), menu.on_give_privileges),
                ("", None),
                ("#" + _("_Save shares list to disk"), self.on_save),
                ("", None),
                ("$" + _("_Add user to list"), menu.on_add_to_list),
                ("$" + _("_Ban this user"), menu.on_ban_user),
                ("$" + _("_Ignore this user"), menu.on_ignore_user)
            )

        self.popup_menu_downloads_folders = PopupMenu(self.frame, False)
        self.popup_menu_downloads_folders.setup(
            ("#" + _("_Download directory"), self.on_download_directory),
            ("#" + _("Download directory _to..."), self.on_download_directory_to),
            ("#" + _("Download _recursive"), self.on_download_directory_recursive),
            ("#" + _("Download r_ecursive to..."), self.on_download_directory_recursive_to)
        )

        self.popup_menu_downloads_files = PopupMenu(self.frame, False)
        self.popup_menu_downloads_files.setup(
            ("#" + _("_Download file(s)"), self.on_download_files),
            ("#" + _("Download _to..."), self.on_download_files_to),
            ("", None),
            ("#" + _("_Download directory"), self.on_download_directory),
            ("#" + _("Download directory _to..."), self.on_download_directory_to),
            ("#" + _("Download _recursive"), self.on_download_directory_recursive),
            ("#" + _("Download r_ecursive to..."), self.on_download_directory_recursive_to)
        )

        self.popup_menu_uploads_folders = PopupMenu(self.frame, False)
        self.popup_menu_uploads_folders.setup(
            ("#" + _("Upload Directory to..."), self.on_upload_directory_to),
            ("#" + _("Upload Directory recursive to..."), self.on_upload_directory_recursive_to)
        )

        self.popup_menu_uploads_files = PopupMenu(self.frame, False)
        self.popup_menu_uploads_files.setup(
            ("#" + _("Upload Directory to..."), self.on_upload_directory_to),
            ("#" + _("Upload Directory recursive to..."), self.on_upload_directory_recursive_to),
            ("#" + _("Up_load file(s)"), self.on_upload_files)
        )

        self.folder_popup_menu = PopupMenu(self.frame)
        self.folder_popup_menu.set_user(user)

        if user == self.frame.np.config.sections["server"]["login"]:
            self.folder_popup_menu.setup(
                ("USERMENU", _("User"), self.popup_menu_users, self.on_popup_menu_folder_user),
                ("", None),
                (1, _("Download"), self.popup_menu_downloads_folders, None),
                (1, _("Upload"), self.popup_menu_uploads_folders, None),
                ("", None),
                ("#" + _("Copy _URL"), self.on_copy_dir_url),
                ("#" + _("Open in File Manager"), self.on_file_manager)
            )
        else:
            self.folder_popup_menu.setup(
                ("USERMENU", _("User"), self.popup_menu_users, self.on_popup_menu_folder_user),
                ("", None),
                (1, _("Download"), self.popup_menu_downloads_folders, None),
                ("", None),
                ("#" + _("Copy _URL"), self.on_copy_dir_url)
            )

        self.FolderTreeView.connect("button_press_event", self.on_folder_clicked)
        self.FolderTreeView.get_selection().connect("changed", self.on_select_dir)

        # Filename, HSize, Bitrate, HLength, Size, Length, RawFilename
        self.file_store = Gtk.ListStore(str, str, str, str, GObject.TYPE_INT64, int, str)

        self.FileTreeView.set_model(self.file_store)
        widths = self.frame.np.config.sections["columns"]["userbrowse_widths"]
        cols = initialise_columns(
            self.FileTreeView,
            [_("Filename"), widths[0], "text"],
            [_("Size"), widths[1], "number"],
            [_("Bitrate"), widths[2], "number"],
            [_("Length"), widths[3], "number"]
        )
        cols[0].set_sort_column_id(0)
        cols[1].set_sort_column_id(4)
        cols[2].set_sort_column_id(2)
        cols[3].set_sort_column_id(5)
        self.file_store.set_sort_column_id(0, Gtk.SortType.ASCENDING)

        hide_columns(cols, self.frame.np.config.sections["columns"]["userbrowse"])

        self.FileTreeView.get_selection().set_mode(Gtk.SelectionMode.MULTIPLE)
        self.FileTreeView.set_headers_clickable(True)
        self.FileTreeView.set_rubber_banding(True)

        self.file_popup_menu = PopupMenu(self.frame)

        if user == self.frame.np.config.sections["server"]["login"]:
            self.file_popup_menu.setup(
                ("USERMENU", "User", self.popup_menu_users2, self.on_popup_menu_file_user),
                ("", None),
                (1, _("Download"), self.popup_menu_downloads_files, None),
                (1, _("Upload"), self.popup_menu_uploads_files, None),
                ("", None),
                ("#" + _("Copy _URL"), self.on_copy_url),
                ("#" + _("Send to _player"), self.on_play_files),
                ("#" + _("Open in File Manager"), self.on_file_manager)
            )
        else:
            self.file_popup_menu.setup(
                ("USERMENU", "User", self.popup_menu_users2, self.on_popup_menu_file_user),
                ("", None),
                (1, _("Download"), self.popup_menu_downloads_files, None),
                ("", None),
                ("#" + _("Copy _URL"), self.on_copy_url)
            )

        self.FileTreeView.connect("button_press_event", self.on_file_clicked)

        self.update_visuals()

        for name, object in self.__dict__.items():
            if isinstance(object, PopupMenu):
                object.set_user(self.user)

    def on_popup_menu_file_user(self, widget):
        self.on_popup_menu_users(self.popup_menu_users2)

    def on_popup_menu_folder_user(self, widget):
        self.on_popup_menu_users(self.popup_menu_users)

    def on_popup_menu_users(self, menu):

        items = menu.get_children()

        act = True
        items[0].set_sensitive(act)
        items[1].set_sensitive(act)
        items[2].set_sensitive(act)

        items[7].set_active(self.user in (i[0] for i in self.frame.np.config.sections["server"]["userlist"]))
        items[8].set_active(self.user in self.frame.np.config.sections["server"]["banlist"])
        items[9].set_active(self.user in self.frame.np.config.sections["server"]["ignorelist"])

        for i in range(3, 10):
            items[i].set_sensitive(act)

        return True

    def update_visuals(self):

        for widget in self.__dict__.values():
            update_widget_visuals(widget, list_font_target="browserfont")

    def on_expand(self, widget):

        if self.ExpandButton.get_active():
            self.FolderTreeView.expand_all()
            self.expand.set_from_icon_name("list-remove-symbolic", Gtk.IconSize.BUTTON)
        else:
            self.FolderTreeView.collapse_all()
            self.expand.set_from_icon_name("list-add-symbolic", Gtk.IconSize.BUTTON)

            dirs = sorted(self.directories.keys())

            if dirs != []:
                self.set_directory(dirs[0])
            else:
                self.set_directory(None)

    def on_folder_clicked(self, widget, event):

        pathinfo = widget.get_path_at_pos(event.x, event.y)

        if pathinfo is not None:

            if event.button == 1 and event.type == Gdk.EventType._2BUTTON_PRESS:
                self.on_download_directory(widget)
                return True

            elif event.button == 3:
                return self.on_folder_popup_menu(widget, event)

        return False

    def on_folder_popup_menu(self, widget, event):

        act = True
        if self.selected_folder is None:
            act = False

        items = self.folder_popup_menu.get_children()
        for item in items[1:]:
            item.set_sensitive(act)

        self.folder_popup_menu.popup(None, None, None, None, event.button, event.time)

    def selected_files_callback(self, model, path, iterator):
        rawfilename = self.file_store.get_value(iterator, 6)
        self.selected_files.append(rawfilename)

    def on_file_clicked(self, widget, event):

        if event.button == 3:
            return self.on_file_popup_menu(widget, event)

        else:
            pathinfo = widget.get_path_at_pos(event.x, event.y)

            if pathinfo is None:
                widget.get_selection().unselect_all()

            elif event.button == 1 and event.type == Gdk.EventType._2BUTTON_PRESS:
                self.selected_files = []
                self.FileTreeView.get_selection().selected_foreach(self.selected_files_callback)
                self.on_download_files(widget)
                self.FileTreeView.get_selection().unselect_all()
                return True

        return False

    def on_file_popup_menu(self, widget, event):

        set_treeview_selected_row(widget, event)

        self.selected_files = []
        self.FileTreeView.get_selection().selected_foreach(self.selected_files_callback)

        files = True
        multiple = False

        if len(self.selected_files) > 1:
            multiple = True

        if len(self.selected_files) >= 1:
            files = True
        else:
            files = False

        items = self.file_popup_menu.get_children()

        if self.user == self.frame.np.config.sections["server"]["login"]:
            items[2].set_sensitive(files)  # Downloads
            items[3].set_sensitive(files)  # Uploads
            items[5].set_sensitive(not multiple and files)  # Copy URL
            items[6].set_sensitive(files)  # Send to player
        else:
            items[2].set_sensitive(files)  # Downloads
            items[4].set_sensitive(not multiple and files)  # Copy URL

        self.FileTreeView.stop_emission_by_name("button_press_event")
        self.file_popup_menu.popup(None, None, None, None, event.button, event.time)

        return True

    def make_new_model(self, list):

        self.shares = list
        self.selected_folder = None
        self.selected_files = []
        self.directories.clear()
        self.files.clear()
        self.dir_store.clear()

        # Compute the number of shared dirs and total size
        self.totalsize = 0
        for dir, files in self.shares:
            for filedata in files:
                if filedata[2] < maxsize:
                    self.totalsize += filedata[2]

        self.AmountShared.set_markup("<b>%s</b>" % human_size(self.totalsize))
        self.NumDirectories.set_markup("<b>%d</b>" % len(self.shares))

        # Generate the directory tree and select first directory
        currentdir = self.browse_get_dirs()

        sel = self.FolderTreeView.get_selection()
        sel.unselect_all()
        if currentdir in self.directories:
            path = self.dir_store.get_path(self.directories[currentdir])
            if path is not None:
                sel.select_path(path)

        self.FolderTreeView.set_sensitive(True)
        self.FileTreeView.set_sensitive(True)

        if self.ExpandButton.get_active():
            self.FolderTreeView.expand_all()
        else:
            self.FolderTreeView.collapse_all()

    def browse_get_dirs(self):

        directory = ""
        dirseparator = '\\'

        # If there is no share

        if self.shares == []:

            # Set the model of the treeviex
            self.FolderTreeView.set_model(self.dir_store)

            # Sort the DirStore
            self.dir_store.set_sort_column_id(0, Gtk.SortType.ASCENDING)

            return directory

        def builddicttree(p, s):
            """
                Build recursively a hierarchical dict containing raw subdir
                'p' is a reference to the parent
                's' a list of the subdir of a path

                ex of 's': ['music', 'rock', 'doors']
            """

            if s:
                subdir = s.pop(0)

                if subdir not in p:
                    p[subdir] = {}

                builddicttree(p[subdir], s)

        def buildgtktree(dictdir, parent, path):
            """
                Build recursively self.directories with iters pointing to directories
                'dictdir' is a hierarchical dict containing raw subdir
                'parent' is the iter pointing to the parent
                'path' is the current raw path
            """

            # Foreach subdir
            for subdir in dictdir:

                if parent is None:
                    # The first sudirs are attached to the root (None)
                    current_path = subdir
                else:
                    # Other sudirs futher down the path are attached to their parent
                    current_path = dirseparator.join([path, subdir])

                self.directories[current_path] = self.dir_store.append(parent, [subdir, current_path])

                # If there are subdirs futher down the path: recurse
                if len(dictdir[subdir]):
                    buildgtktree(dictdir[subdir], self.directories[current_path], current_path)

        # For each shared dir we will complete the dictionnary
        dictdir = {}

        for dirshares, f in self.shares:

            # Split the path
            s = dirshares.split(dirseparator)

            # and build a hierarchical dictionnary containing raw subdir
            if len(s) >= 1:
                builddicttree(dictdir, s)

        # Append data to the DirStore
        buildgtktree(dictdir, None, None)

        # Select the first directory
        sortlist = sorted(self.directories.keys())

        directory = sortlist[0]

        # Sort the DirStore
        self.dir_store.set_sort_column_id(0, Gtk.SortType.ASCENDING)

        # Set the model of the treeviex
        self.FolderTreeView.set_model(self.dir_store)

        return directory

    def set_directory(self, directory):

        self.selected_folder = directory
        self.file_store.clear()
        self.files.clear()

        found_dir = False

        for d, f in self.shares:
            if d == directory:
                found_dir = True
                files = f
                break

        if not found_dir:
            return

        for file in files:
            # Filename, HSize, Bitrate, HLength, Size, Length, RawFilename
            rl = 0

            try:
                size = int(file[2])

                # Some clients send incorrect file sizes
                if size < 0 or size > maxsize:
                    size = 0
            except ValueError:
                size = 0

            f = [file[1], human_size(size)]

            h_bitrate, bitrate, h_length = get_result_bitrate_length(size, file[4])
            f += [h_bitrate, h_length]

            f += [int(size), rl, file[1]]

            try:
                self.files[f[0]] = self.file_store.append(f)
            except Exception as msg:
                log.add(_("Error while attempting to display folder '%(folder)s', reported error: %(error)s"), {'folder': directory, 'error': msg})

    def on_save(self, widget):
        sharesdir = os.path.join(self.frame.data_dir, "usershares")

        try:
            if not os.path.exists(sharesdir):
                os.mkdir(sharesdir)
        except Exception as msg:
            log.add(_("Can't create directory '%(folder)s', reported error: %(error)s"), {'folder': sharesdir, 'error': msg})

        try:
            import pickle as mypickle
            import bz2
            sharesfile = bz2.BZ2File(os.path.join(sharesdir, clean_file(self.user)), 'w')
            mypickle.dump(self.shares, sharesfile, protocol=mypickle.HIGHEST_PROTOCOL)
            sharesfile.close()
            log.add(_("Saved list of shared files for user '%(user)s' to %(dir)s"), {'user': self.user, 'dir': sharesdir})

        except Exception as msg:
            log.add(_("Can't save shares, '%(user)s', reported error: %(error)s"), {'user': self.user, 'error': msg})

    def save_columns(self):

        columns = []
        widths = []

        for column in self.FileTreeView.get_columns():
            columns.append(column.get_visible())
            widths.append(column.get_width())

        self.frame.np.config.sections["columns"]["userbrowse"] = columns
        self.frame.np.config.sections["columns"]["userbrowse_widths"] = widths

    def show_user(self, msg, indeterminate_progress=False):

        self.set_in_progress(indeterminate_progress)

        if msg is None:
            return

        self.conn = None
        self.make_new_model(msg.list)

        if len(msg.list) == 0:
            self.info_bar.show_message(
                _("User's list of shared files is empty. Either the user is not sharing anything, or they are sharing files privately.")
            )

        else:
            self.info_bar.set_visible(False)

        self.set_finished()

    def show_connection_error(self):

        self.info_bar.show_message(
            _("Unable to request shared files from user. Either the user is offline, you both have a closed listening port, or there's a temporary connectivity issue.")
        )

        self.set_finished()

    def load_shares(self, list):
        self.make_new_model(list)

    def set_in_progress(self, indeterminate_progress):

        if not indeterminate_progress:
            self.progressbar1.set_fraction(0.0)
        else:
            self.progressbar1.set_fraction(0.5)

        self.RefreshButton.set_sensitive(False)

    def set_finished(self):

        # Tab notification
        self.frame.request_tab_icon(self.frame.UserBrowseTabLabel)
        self.userbrowses.request_changed(self.Main)

        self.progressbar1.set_fraction(1.0)
        self.RefreshButton.set_sensitive(True)

    def update_gauge(self, msg):

        if msg.total == 0 or msg.bytes == 0:
            fraction = 0.0
        elif msg.bytes >= msg.total:
            fraction = 1.0
        else:
            fraction = float(msg.bytes) / msg.total

        self.progressbar1.set_fraction(fraction)

    def on_select_dir(self, selection):

        model, iterator = selection.get_selected()

        if iterator is None:
            self.selected_folder = None
            return

        path = model.get_path(iterator)
        directory = model.get_value(iterator, 1)

        self.FolderTreeView.expand_to_path(path)
        self.set_directory(directory)

    def on_resort(self, column, column_id):

        model = self.FileTreeView.get_model()

        if model.sort_col == column_id:
            order = model.sort_order

            if order == Gtk.SortType.ASCENDING:
                order = Gtk.SortType.DESCENDING
            else:
                order = Gtk.SortType.ASCENDING

            column.set_sort_order(order)
            model.sort_order = order
            self.FileTreeView.set_model(None)
            model.sort()
            self.FileTreeView.set_model(model)
            return

        cols = self.FileTreeView.get_columns()
        cols[model.sort_col].set_sort_indicator(False)
        cols[column_id].set_sort_indicator(True)
        model.sort_col = column_id

        self.on_resort(column, column_id)

    def on_download_directory(self, widget):

        if self.selected_folder is not None:
            self.download_directory(self.selected_folder)

    def on_download_directory_recursive(self, widget):

        self.download_directory(self.selected_folder, "", 1)

    def on_download_directory_to(self, widget):

        folder = choose_dir(self.frame.MainWindow, self.frame.np.config.sections["transfers"]["downloaddir"], multichoice=False)

        if folder is None:
            return

        try:
            self.download_directory(self.selected_folder, os.path.join(folder[0], ""))
        except IOError:  # failed to open
            log.add('Failed to open %r for reading', folder[0])  # notify user

    def on_download_directory_recursive_to(self, widget):

        folder = choose_dir(self.frame.MainWindow, self.frame.np.config.sections["transfers"]["downloaddir"], multichoice=False)

        if folder is None:
            return

        try:
            self.download_directory(self.selected_folder, os.path.join(folder[0], ""), 1)
        except IOError:  # failed to open
            log.add('Failed to open %r for reading', folder[0])  # notify user

    def download_directory(self, folder, prefix="", recurse=0):

        if folder is None:
            return

        ldir = prefix + folder.split("\\")[-1]

        # Check if folder already exists on system
        ldir = self.frame.np.transfers.folder_destination(self.user, ldir)

        for d, f in self.shares:

            # Find the wanted directory
            if d != folder:
                continue

            priorityfiles = []
            normalfiles = []

            if self.frame.np.config.sections["transfers"]["prioritize"]:

                for file in f:

                    parts = file[1].rsplit('.', 1)

                    if len(parts) == 2 and parts[1] in ['sfv', 'md5', 'nfo']:
                        priorityfiles.append(file)
                    else:
                        normalfiles.append(file)
            else:
                normalfiles = f

            if self.frame.np.config.sections["transfers"]["reverseorder"]:
                deco = [(x[1], x) for x in normalfiles]
                deco.sort(reverse=True)
                normalfiles = [x for junk, x in deco]

            for file in priorityfiles + normalfiles:

                path = "\\".join([folder, file[1]])
                size = file[2]
                h_bitrate, bitrate, h_length = get_result_bitrate_length(size, file[4])

                self.frame.np.transfers.get_file(
                    self.user,
                    path,
                    ldir,
                    size=size,
                    bitrate=h_bitrate,
                    length=h_length,
                    checkduplicate=True
                )

        if not recurse:
            return

        for subdir, subf in self.shares:
            if folder in subdir and folder != subdir:
                self.download_directory(subdir, os.path.join(ldir, ""))

    def on_download_files(self, widget, prefix=""):

        folder = self.selected_folder

        for d, f in self.shares:

            # Find the wanted directory
            if d != folder:
                continue

            for file in f:

                # Find the wanted file
                if file[1] not in self.selected_files:
                    continue

                path = "\\".join([folder, file[1]])
                size = file[2]
                h_bitrate, bitrate, h_length = get_result_bitrate_length(size, file[4])

                # Get the file
                self.frame.np.transfers.get_file(self.user, path, prefix, size=size, bitrate=h_bitrate, length=h_length, checkduplicate=True)

            # We have found the wanted directory: we can break out of the loop
            break

    def on_download_files_to(self, widget):

        try:
            _, folder = self.selected_folder.rsplit("\\", 1)
        except ValueError:
            folder = self.selected_folder

        path = os.path.join(self.frame.np.config.sections["transfers"]["downloaddir"], folder)

        if os.path.exists(path) and os.path.isdir(path):
            ldir = choose_dir(self.frame.MainWindow, path, multichoice=False)
        else:
            ldir = choose_dir(self.frame.MainWindow, self.frame.np.config.sections["transfers"]["downloaddir"], multichoice=False)

        if ldir is None:
            return

        try:
            self.on_download_files(widget, ldir[0])
        except IOError:  # failed to open
            log.add('failed to open %r for reading', ldir[0])  # notify user

    def on_upload_directory_to(self, widget, recurse=0):

        folder = self.selected_folder

        if folder is None:
            return

        users = []
        for entry in self.frame.np.config.sections["server"]["userlist"]:
            users.append(entry[0])

        users.sort()
        user = combo_box_dialog(
            parent=self.frame.MainWindow,
            title=_("Upload Directory's Contents"),
            message=_('Enter the User you wish to upload to:'),
            droplist=users
        )

        if user is None or user == "":
            return

        self.frame.np.send_message_to_peer(user, slskmessages.UploadQueueNotification(None))

        self.upload_directory_to(user, folder, recurse)

    def on_upload_directory_recursive_to(self, widget):
        self.on_upload_directory_to(widget, recurse=1)

    def upload_directory_to(self, user, folder, recurse=0):

        if folder == "" or folder is None or user is None or user == "":
            return

        realpath = self.frame.np.shares.virtual2real(folder)
        ldir = folder.split("\\")[-1]

        for d, f in self.shares:

            # Find the wanted directory
            if d != folder:
                continue

            for file in f:
                filename = "\\".join([folder, file[1]])
                realfilename = "\\".join([realpath, file[1]])
                size = file[2]
                self.frame.np.transfers.push_file(user, filename, realfilename, ldir, size=size)
                self.frame.np.transfers.check_upload_queue()

        if not recurse:
            return

        for subdir, subf in self.shares:
            if folder in subdir and folder != subdir:
                self.upload_directory_to(user, subdir, recurse)

    def on_upload_files(self, widget, prefix=""):

        folder = self.selected_folder
        realpath = self.frame.np.shares.virtual2real(folder)

        users = []

        for entry in self.frame.np.config.sections["server"]["userlist"]:
            users.append(entry[0])

        users.sort()
        user = combo_box_dialog(
            parent=self.frame.MainWindow,
            title=_('Upload File(s)'),
            message=_('Enter the User you wish to upload to:'),
            droplist=users
        )

        if user is None or user == "":
            return

        self.frame.np.send_message_to_peer(user, slskmessages.UploadQueueNotification(None))

        for fn in self.selected_files:
            self.frame.np.transfers.push_file(user, "\\".join([folder, fn]), "\\".join([realpath, fn]), prefix)
            self.frame.np.transfers.check_upload_queue()

    def on_play_files(self, widget, prefix=""):
        start_new_thread(self._on_play_files, (widget, prefix))

    def _on_play_files(self, widget, prefix=""):

        path = self.frame.np.shares.virtual2real(self.selected_folder)

        for fn in self.selected_files:
            playfile = os.sep.join([path, fn])

            if os.path.exists(playfile):
                command = self.frame.np.config.sections["players"]["default"]
                open_file_path(playfile, command)

    def find_matches(self):

        self.search_list = []

        for directory, files in self.shares:

            if self.query in directory.lower():
                if directory not in self.search_list:
                    self.search_list.append(directory)

            for file in files:
                if self.query in file[1].lower():
                    if directory not in self.search_list:
                        self.search_list.append(directory)

    def on_search(self, widget):

        query = self.SearchEntry.get_text().lower()

        if self.query == query:
            self.search_position += 1
        else:
            self.search_position = 0
            self.query = query
            if self.query == "":
                return
            self.find_matches()

        if self.search_list != []:

            if self.search_position not in list(range(len(self.search_list))):
                self.search_position = 0

            self.search_list.sort()
            directory = self.search_list[self.search_position]

            path = self.dir_store.get_path(self.directories[directory])
            self.FolderTreeView.expand_to_path(path)
            self.FolderTreeView.set_cursor(path)

            # Get matching files in the current directory
            resultfiles = []
            for file in self.files:
                if query in file.lower():
                    resultfiles.append(file)

            sel = self.FileTreeView.get_selection()
            sel.unselect_all()
            not_selected = 1
            resultfiles.sort()

            for fn in resultfiles:
                path = self.file_store.get_path(self.files[fn])

                # Select each matching file in directory
                sel.select_path(path)

                if not_selected:
                    # Position cursor at first match
                    self.FileTreeView.scroll_to_cell(path, None, True, 0.5, 0.5)
                    not_selected = 0
        else:
            self.search_position = 0

    def on_close(self, widget):

        del self.userbrowses.users[self.user]

        self.userbrowses.remove_page(self.Main)
        self.Main.destroy()

    def on_refresh(self, widget):
        self.info_bar.set_visible(False)
        self.FolderTreeView.set_sensitive(False)
        self.FileTreeView.set_sensitive(False)
        self.frame.browse_user(self.user)

    def on_copy_url(self, widget):

        if self.selected_files != [] and self.selected_files is not None:
            path = "\\".join([self.selected_folder, self.selected_files[0]])
            self.frame.set_clipboard_url(self.user, path)

    def on_copy_dir_url(self, widget):

        if self.selected_folder is None:
            return

        path = self.selected_folder
        if path[:-1] != "/":
            path += "/"

        self.frame.set_clipboard_url(self.user, path)

    def on_file_manager(self, widget):

        if self.selected_folder is None:
            return

        path = self.frame.np.shares.virtual2real(self.selected_folder)
        command = self.frame.np.config.sections["ui"]["filemanager"]

        open_file_path(path, command)
