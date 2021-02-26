# COPYRIGHT (C) 2020-2021 Nicotine+ Team
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

from sys import maxsize

from gi.repository import Gdk
from gi.repository import GObject
from gi.repository import Gtk

from _thread import start_new_thread
from pynicotine import slskmessages
from pynicotine.gtkgui.dialogs import choose_dir
from pynicotine.gtkgui.dialogs import combo_box_dialog
from pynicotine.gtkgui.fileproperties import FileProperties
from pynicotine.gtkgui.utils import human_size
from pynicotine.gtkgui.utils import InfoBar
from pynicotine.gtkgui.utils import initialise_columns
from pynicotine.gtkgui.utils import load_ui_elements
from pynicotine.gtkgui.utils import open_file_path
from pynicotine.gtkgui.utils import PopupMenu
from pynicotine.gtkgui.utils import save_columns
from pynicotine.gtkgui.utils import set_treeview_selected_row
from pynicotine.gtkgui.utils import triggers_context_menu
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

        # Monitor user online status
        if user not in self.frame.np.watchedusers:
            self.frame.np.queue.put(slskmessages.AddUser(user))

        self.user = user
        self.conn = None
        self.local_shares_type = None
        self.refreshing = True

        # selected_folder is the current selected folder
        self.selected_folder = None

        # queued_folder is a folder that should be opened once the share has loaded
        self.queued_folder = None

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

        self.dir_column_numbers = [0, 1]
        cols = initialise_columns(
            None,
            self.FolderTreeView,
            ["folders", _("Folders"), -1, "text", None]  # 0
        )

        cols["folders"].set_sort_column_id(0)

        self.popup_menu_users = PopupMenu(self.frame, False)
        self.popup_menu_users2 = PopupMenu(self.frame, False)
        self.popup_menu_users_tab = PopupMenu(self.frame)

        for menu in (self.popup_menu_users, self.popup_menu_users2, self.popup_menu_users_tab):
            menu.setup_user_menu(user)
            menu.get_items()[_("Brow_se Files")].set_visible(False)

            menu.append_item(("", None))
            menu.append_item(("#" + _("_Save Shares List To Disk"), self.on_save))
            menu.append_item(("#" + _("Close All Tabs"), menu.on_close_all_tabs, self.userbrowses))
            menu.append_item(("#" + _("_Close Tab"), self.on_close))

        self.popup_menu_downloads_folders = PopupMenu(self.frame, False)
        self.popup_menu_downloads_folders.setup(
            ("#" + _("_Download Folder"), self.on_download_directory),
            ("#" + _("Download Folder _To..."), self.on_download_directory_to),
            ("#" + _("Download _Recursive"), self.on_download_directory_recursive),
            ("#" + _("Download R_ecursive To..."), self.on_download_directory_recursive_to)
        )

        self.popup_menu_downloads_files = PopupMenu(self.frame, False)
        self.popup_menu_downloads_files.setup(
            ("#" + _("_Download File(s)"), self.on_download_files),
            ("#" + _("Download _To..."), self.on_download_files_to),
            ("", None),
            ("#" + _("_Download Folder"), self.on_download_directory),
            ("#" + _("Download Folder _To..."), self.on_download_directory_to),
            ("#" + _("Download _Recursive"), self.on_download_directory_recursive),
            ("#" + _("Download R_ecursive To..."), self.on_download_directory_recursive_to)
        )

        self.popup_menu_uploads_folders = PopupMenu(self.frame, False)
        self.popup_menu_uploads_folders.setup(
            ("#" + _("Upload Folder To..."), self.on_upload_directory_to),
            ("#" + _("Upload Folder Recursive To..."), self.on_upload_directory_recursive_to)
        )

        self.popup_menu_uploads_files = PopupMenu(self.frame, False)
        self.popup_menu_uploads_files.setup(
            ("#" + _("Upload Folder To..."), self.on_upload_directory_to),
            ("#" + _("Upload Folder Recursive To..."), self.on_upload_directory_recursive_to),
            ("#" + _("Up_load File(s)"), self.on_upload_files)
        )

        self.folder_popup_menu = PopupMenu(self.frame)

        if user == self.frame.np.config.sections["server"]["login"]:
            self.folder_popup_menu.setup(
                ("#" + _("_Download Folder"), self.on_download_directory),
                ("#" + _("Download Folder _To..."), self.on_download_directory_to),
                ("#" + _("Download _Recursive"), self.on_download_directory_recursive),
                ("#" + _("Download R_ecursive To..."), self.on_download_directory_recursive_to),
                ("", None),
                ("#" + _("Upload Folder To..."), self.on_upload_directory_to),
                ("#" + _("Upload Folder Recursive To..."), self.on_upload_directory_recursive_to),
                ("", None),
                ("#" + _("Open in File _Manager"), self.on_file_manager),
                ("", None),
                ("#" + _("Copy _Folder Path"), self.on_copy_file_path, False),
                ("#" + _("Copy _URL"), self.on_copy_dir_url),
                ("", None),
                (1, _("User"), self.popup_menu_users, self.on_popup_menu_folder_user)
            )
        else:
            self.folder_popup_menu.setup(
                ("#" + _("_Download Folder"), self.on_download_directory),
                ("#" + _("Download Folder _To..."), self.on_download_directory_to),
                ("#" + _("Download _Recursive"), self.on_download_directory_recursive),
                ("#" + _("Download R_ecursive To..."), self.on_download_directory_recursive_to),
                ("", None),
                ("#" + _("Copy _Folder Path"), self.on_copy_file_path, False),
                ("#" + _("Copy _URL"), self.on_copy_dir_url),
                ("", None),
                (1, _("User"), self.popup_menu_users, self.on_popup_menu_folder_user)
            )

        self.FolderTreeView.get_selection().connect("changed", self.on_select_dir)

        self.file_store = Gtk.ListStore(
            str,                  # (0) file name
            str,                  # (1) hsize
            str,                  # (2) hbitrate
            str,                  # (3) hlength
            GObject.TYPE_UINT64,  # (4) size
            GObject.TYPE_UINT64,  # (5) bitrate
            GObject.TYPE_UINT64   # (6) length
        )

        self.FileTreeView.set_model(self.file_store)

        self.file_column_numbers = [0, 1, 2, 3, 4, 5, 6]
        cols = initialise_columns(
            "user_browse",
            self.FileTreeView,
            ["filename", _("Filename"), 600, "text", None],
            ["size", _("Size"), 100, "number", None],
            ["bitrate", _("Bitrate"), 100, "number", None],
            ["length", _("Length"), 100, "number", None]
        )
        cols["filename"].set_sort_column_id(0)
        cols["size"].set_sort_column_id(4)
        cols["bitrate"].set_sort_column_id(5)
        cols["length"].set_sort_column_id(6)
        self.file_store.set_sort_column_id(0, Gtk.SortType.ASCENDING)

        self.file_popup_menu = PopupMenu(self.frame)

        if user == self.frame.np.config.sections["server"]["login"]:
            self.file_popup_menu.setup(
                ("#" + "selected_files", None),
                ("", None),
                (1, _("Download"), self.popup_menu_downloads_files, None),
                (1, _("Upload"), self.popup_menu_uploads_files, None),
                ("", None),
                ("#" + _("Send to _Player"), self.on_play_files),
                ("#" + _("Open in File _Manager"), self.on_file_manager),
                ("#" + _("File _Properties"), self.on_file_properties),
                ("", None),
                ("#" + _("Copy _File Path"), self.on_copy_file_path, True),
                ("#" + _("Copy _URL"), self.on_copy_url),
                ("", None),
                (1, "User", self.popup_menu_users2, self.on_popup_menu_file_user)
            )
        else:
            self.file_popup_menu.setup(
                ("#" + "selected_files", None),
                ("", None),
                (1, _("Download"), self.popup_menu_downloads_files, None),
                ("", None),
                ("#" + _("File _Properties"), self.on_file_properties),
                ("", None),
                ("#" + _("Copy _File Path"), self.on_copy_file_path, True),
                ("#" + _("Copy _URL"), self.on_copy_url),
                ("", None),
                (1, "User", self.popup_menu_users2, self.on_popup_menu_file_user)
            )

        self.update_visuals()

        for name, object in self.__dict__.items():
            if isinstance(object, PopupMenu):
                object.set_user(self.user)

    def on_popup_menu_file_user(self, widget):
        self.on_popup_menu_users(self.popup_menu_users2)

    def on_popup_menu_folder_user(self, widget):
        self.on_popup_menu_users(self.popup_menu_users)

    def on_popup_menu_users(self, menu):
        menu.toggle_user_items()
        return True

    def update_visuals(self):

        for widget in self.__dict__.values():
            update_widget_visuals(widget, list_font_target="browserfont")

    def on_expand(self, widget):

        if self.ExpandButton.get_active():
            self.FolderTreeView.expand_all()
            self.expand.set_from_icon_name("go-up-symbolic", Gtk.IconSize.BUTTON)
        else:
            self.FolderTreeView.collapse_all()
            self.expand.set_from_icon_name("go-down-symbolic", Gtk.IconSize.BUTTON)

            dirs = sorted(self.directories.keys())

            if dirs != []:
                self.set_directory(dirs[0])
            else:
                self.set_directory(None)

    def on_folder_clicked(self, widget, event):

        if triggers_context_menu(event):
            set_treeview_selected_row(widget, event)
            return self.on_folder_popup_menu(widget)

        if event.button == 1 and event.type == Gdk.EventType._2BUTTON_PRESS:
            if self.user != self.frame.np.config.sections["server"]["login"]:
                self.on_download_directory(widget)
                return True

        return False

    def on_folder_popup_menu(self, widget):
        self.folder_popup_menu.popup()
        return True

    def select_files(self):
        self.selected_files = []
        self.FileTreeView.get_selection().selected_foreach(self.selected_files_callback)

    def selected_files_callback(self, model, path, iterator):
        rawfilename = self.file_store.get_value(iterator, 0)
        self.selected_files.append(rawfilename)

    def on_file_clicked(self, widget, event):

        if triggers_context_menu(event):
            set_treeview_selected_row(widget, event)
            return self.on_file_popup_menu(widget)

        if event.button == 1 and event.type == Gdk.EventType._2BUTTON_PRESS:
            self.select_files()

            if self.user == self.frame.np.config.sections["server"]["login"]:
                self.on_play_files(widget)
            else:
                self.on_download_files(widget)
            return True

        return False

    def on_file_popup_menu(self, widget):

        self.select_files()
        num_selected_files = len(self.selected_files)

        if num_selected_files >= 1:
            files = True
        else:
            files = False

        items = self.file_popup_menu.get_items()

        if self.user == self.frame.np.config.sections["server"]["login"]:
            for i in (_("Download"), _("Upload"), _("Send to _Player"), _("File _Properties"),
                      _("Copy _File Path"), _("Copy _URL")):
                items[i].set_sensitive(files)
        else:
            for i in (_("Download"), _("File _Properties"), _("Copy _File Path"), _("Copy _URL")):
                items[i].set_sensitive(files)

        items["selected_files"].set_sensitive(False)
        items["selected_files"].set_label(_("%s File(s) Selected") % num_selected_files)

        self.file_popup_menu.popup()
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

        self.AmountShared.set_text(human_size(self.totalsize))
        self.NumDirectories.set_text(str(len(self.shares)))

        # Generate the directory tree and select first directory
        currentdir = self.browse_get_dirs()

        sel = self.FolderTreeView.get_selection()
        sel.unselect_all()
        if currentdir in self.directories:
            path = self.dir_store.get_path(self.directories[currentdir])
            if path is not None:
                sel.select_path(path)

        if self.ExpandButton.get_active():
            self.FolderTreeView.expand_all()
        else:
            self.FolderTreeView.collapse_all()

        self.set_finished()

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

                self.directories[current_path] = self.dir_store.insert_with_values(
                    parent, -1, self.dir_column_numbers,
                    [subdir, current_path]
                )

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

    def browse_folder(self, folder):
        """ Browse a specific folder in the share """

        try:
            iterator = self.directories[folder]
        except KeyError:
            # Folder not found
            pass

        if folder:
            sel = self.FolderTreeView.get_selection()
            sel.unselect_all()

            path = self.dir_store.get_path(iterator)
            self.FolderTreeView.expand_to_path(path)
            sel.select_path(path)
            self.FolderTreeView.scroll_to_cell(path, None, True, 0.5, 0.5)

            self.queued_folder = None

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
            try:
                size = int(file[2])

                # Some clients send incorrect file sizes
                if size < 0 or size > maxsize:
                    size = 0
            except ValueError:
                size = 0

            f = [file[1], human_size(size)]

            h_bitrate, bitrate, h_length, length = get_result_bitrate_length(size, file[4])
            f += [
                h_bitrate,
                h_length,
                GObject.Value(GObject.TYPE_UINT64, int(size)),
                GObject.Value(GObject.TYPE_UINT64, bitrate),
                GObject.Value(GObject.TYPE_UINT64, length)
            ]

            try:
                self.files[f[0]] = self.file_store.insert_with_valuesv(-1, self.file_column_numbers, f)
            except Exception as msg:
                log.add(_("Error while attempting to display folder '%(folder)s', reported error: %(error)s"), {'folder': directory, 'error': msg})

    def on_save(self, widget):
        sharesdir = os.path.join(self.frame.data_dir, "usershares")

        try:
            if not os.path.exists(sharesdir):
                os.makedirs(sharesdir)

        except Exception as msg:
            log.add(_("Can't create directory '%(folder)s', reported error: %(error)s"), {'folder': sharesdir, 'error': msg})

        try:
            filepath = os.path.join(sharesdir, clean_file(self.user))

            with open(filepath, "w", encoding="utf-8") as sharesfile:
                import json
                json.dump(self.shares, sharesfile, ensure_ascii=False)

            log.add(_("Saved list of shared files for user '%(user)s' to %(dir)s"), {'user': self.user, 'dir': sharesdir})

        except Exception as msg:
            log.add(_("Can't save shares, '%(user)s', reported error: %(error)s"), {'user': self.user, 'error': msg})

    def save_columns(self):
        save_columns("user_browse", self.FileTreeView.get_columns())

    def show_user(self, msg, folder=None, indeterminate_progress=False, local_shares_type=None):

        self.set_in_progress(indeterminate_progress)

        if folder:
            self.queued_folder = folder

        # If this is our own share, remember if it's public or buddy
        # (needed for refresh button)
        if local_shares_type:
            self.local_shares_type = local_shares_type

        """ Update the list model if:
        1. This is a new user browse tab
        2. We're refreshing the file list
        3. This is the list of our own shared files (local_shares_type set)
        """
        if self.refreshing or local_shares_type:
            if msg is None:
                return

            self.make_new_model(msg.list)

        if msg and len(msg.list) == 0:
            self.info_bar.show_message(
                _("User's list of shared files is empty. Either the user is not sharing anything, or they are sharing files privately.")
            )

        else:
            self.info_bar.set_visible(False)
            self.browse_folder(self.queued_folder)

        self.set_finished()

    def show_connection_error(self):

        self.info_bar.show_message(
            _("Unable to request shared files from user. Either the user is offline, you both have a closed listening port, or there's a temporary connectivity issue.")
        )

        self.set_finished()

    def load_shares(self, list):
        self.make_new_model(list)

    def is_refreshing(self):
        return self.refreshing

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

        self.FolderTreeView.set_sensitive(True)
        self.FileTreeView.set_sensitive(True)
        self.RefreshButton.set_sensitive(True)

        self.refreshing = False

    def update_gauge(self, msg):

        if msg.total == 0 or msg.bytes == 0:
            fraction = 0.0
        elif msg.bytes >= msg.total:
            fraction = 1.0
        else:
            fraction = float(msg.bytes) / msg.total

        self.progressbar1.set_fraction(fraction)

    def tab_popup(self, user):
        self.popup_menu_users_tab.toggle_user_items()
        return self.popup_menu_users_tab

    def on_select_dir(self, selection):

        model, iterator = selection.get_selected()

        if iterator is None:
            self.selected_folder = None
            return

        path = model.get_path(iterator)
        directory = model.get_value(iterator, 1)

        self.FolderTreeView.expand_to_path(path)
        self.set_directory(directory)

    def selected_results_all_data(self, model, path, iterator, data):

        filename = model.get_value(iterator, 0)
        fn = "\\".join([self.selected_folder, filename])
        size = model.get_value(iterator, 1)
        bitratestr = model.get_value(iterator, 2)
        length = model.get_value(iterator, 3)

        data.append({
            "user": self.user,
            "fn": fn,
            "filename": filename,
            "directory": self.selected_folder,
            "size": size,
            "bitrate": bitratestr,
            "length": length,
            "immediate": None,
            "speed": None,
            "country": None
        })

    def on_file_properties(self, widget):

        data = []
        self.FileTreeView.get_selection().selected_foreach(self.selected_results_all_data, data)

        if data:
            FileProperties(self.frame, data).show()

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

        if self.frame.np.transfers is None or folder is None:
            return

        ldir = prefix + folder.split("\\")[-1]

        # Check if folder already exists on system
        ldir = self.frame.np.transfers.folder_destination(self.user, ldir)

        for d, files in self.shares:

            # Find the wanted directory
            if d != folder:
                continue

            if self.frame.np.config.sections["transfers"]["reverseorder"]:
                files.sort(key=lambda x: x[1], reverse=True)

            for file in files:

                path = "\\".join([folder, file[1]])
                size = file[2]
                h_bitrate, bitrate, h_length, length = get_result_bitrate_length(size, file[4])

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

        if not self.frame.np.transfers:
            return

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
                h_bitrate, bitrate, h_length, length = get_result_bitrate_length(size, file[4])

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
            title=_("Upload Folder's Contents"),
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

        if not self.frame.np.transfers:
            return

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

        if not self.frame.np.transfers:
            return

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

    def on_key_press_event(self, widget, event):

        key = Gdk.keyval_name(event.keyval)
        self.select_files()

        if key in ("C", "c") and event.state in (Gdk.ModifierType.CONTROL_MASK, Gdk.ModifierType.LOCK_MASK | Gdk.ModifierType.CONTROL_MASK):
            files = (widget == self.FileTreeView)
            self.on_copy_file_path(widget, files)
        else:
            # No key match, continue event
            return False

        widget.stop_emission_by_name("key_press_event")
        return True

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

    def on_refresh(self, widget):

        self.refreshing = True
        self.info_bar.set_visible(False)

        self.FolderTreeView.set_sensitive(False)
        self.FileTreeView.set_sensitive(False)

        self.frame.browse_user(self.user, local_shares_type=self.local_shares_type)

    def on_copy_file_path(self, widget, files=False):

        text = self.selected_folder

        if files and self.selected_files:
            text = "\\".join([self.selected_folder, self.selected_files[0]])

        self.frame.clip.set_text(text, -1)

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
