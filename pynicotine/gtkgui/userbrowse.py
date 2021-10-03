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

import json
import os

from gi.repository import GLib
from gi.repository import GObject
from gi.repository import Gtk

from pynicotine import slskmessages
from pynicotine.config import config
from pynicotine.gtkgui.fileproperties import FileProperties
from pynicotine.gtkgui.utils import copy_file_url
from pynicotine.gtkgui.utils import copy_text
from pynicotine.gtkgui.utils import setup_accelerator
from pynicotine.gtkgui.widgets.filechooser import choose_dir
from pynicotine.gtkgui.widgets.iconnotebook import IconNotebook
from pynicotine.gtkgui.widgets.infobar import InfoBar
from pynicotine.gtkgui.widgets.dialogs import entry_dialog
from pynicotine.gtkgui.widgets.popupmenu import PopupMenu
from pynicotine.gtkgui.widgets.theme import update_widget_visuals
from pynicotine.gtkgui.widgets.treeview import initialise_columns
from pynicotine.gtkgui.widgets.treeview import save_columns
from pynicotine.gtkgui.widgets.ui import UserInterface
from pynicotine.logfacility import log
from pynicotine.utils import get_path
from pynicotine.utils import get_result_bitrate_length
from pynicotine.utils import human_size
from pynicotine.utils import open_file_path


class UserBrowses(IconNotebook):

    def __init__(self, frame):

        self.frame = frame
        self.pages = {}

        IconNotebook.__init__(
            self,
            self.frame,
            tabclosers=config.sections["ui"]["tabclosers"],
            show_hilite_image=config.sections["notifications"]["notification_tab_icons"],
            show_status_image=config.sections["ui"]["tab_status_icons"],
            notebookraw=self.frame.UserBrowseNotebookRaw
        )

        self.notebook.connect("switch-page", self.on_switch_browse_page)

    def on_switch_browse_page(self, notebook, page, page_num):

        if not self.unread_pages:
            self.frame.clear_tab_hilite(self.frame.UserBrowseTabLabel)

        for tab in self.pages.values():
            if tab.Main == page:
                GLib.idle_add(lambda: tab.FolderTreeView.grab_focus() == -1)
                break

    def show_user(self, user, folder=None, local_shares_type=None, indeterminate_progress=False):

        if user not in self.pages:
            self.save_columns()

            try:
                status = self.frame.np.users[user].status
            except Exception:
                # Offline
                status = 0

            self.pages[user] = page = UserBrowse(self, user)
            page.set_in_progress(indeterminate_progress)

            self.append_page(page.Main, user, page.on_close, status=status)
            page.set_label(self.get_tab_label_inner(page.Main))

            if self.get_n_pages() > 0:
                self.frame.UserBrowseStatusPage.hide()

        page = self.pages[user]

        page.indeterminate_progress = indeterminate_progress
        page.local_shares_type = local_shares_type
        page.queued_folder = folder
        page.browse_queued_folder()

        self.set_current_page(self.page_num(page.Main))
        self.frame.change_main_page("userbrowse")

    def set_conn(self, user, conn):
        if user in self.pages:
            self.pages[user].conn = conn

    def show_connection_error(self, user):
        if user in self.pages:
            self.pages[user].show_connection_error()

    def get_user_status(self, msg):

        if msg.user in self.pages:
            page = self.pages[msg.user]
            self.set_user_status(page.Main, msg.user, msg.status)

    def _shared_file_list(self, user, msg):
        if user in self.pages:
            self.pages[user].shared_file_list(msg)

    def shared_file_list(self, user, msg):
        # We can potentially arrive here from a different thread. Run in main thread.
        GLib.idle_add(self._shared_file_list, user, msg)

    def update_gauge(self, msg):

        for page in self.pages.values():
            if page.conn == msg.conn.conn:
                page.update_gauge(msg)

    def update_visuals(self):
        for page in self.pages.values():
            page.update_visuals()

    def server_disconnect(self):
        for user, page in self.pages.items():
            self.set_user_status(page.Main, user, 0)

    def save_columns(self):
        """ Save the treeview state of the currently selected tab """

        current_page = self.get_nth_page(self.get_current_page())

        for page in self.pages.values():
            if page.Main == current_page:
                page.save_columns()
                break


class UserBrowse(UserInterface):

    def __init__(self, userbrowses, user):

        super().__init__("ui/userbrowse.ui")

        self.userbrowses = userbrowses
        self.frame = userbrowses.frame

        self.info_bar = InfoBar(self.InfoBar, Gtk.MessageType.INFO)

        self.user = user
        self.conn = None
        self.local_shares_type = None

        # selected_folder is the current selected folder
        self.selected_folder = None

        # queued_folder is a folder that should be opened once the share has loaded
        self.queued_folder = None

        self.search_list = []
        self.query = None
        self.search_position = 0
        self.selected_files = {}

        self.shares = []

        # Iters for current DirStore
        self.directories = {}

        # Iters for current FileStore
        self.files = {}
        self.totalsize = 0

        self.dir_store = Gtk.TreeStore(str)
        self.FolderTreeView.set_model(self.dir_store)
        setup_accelerator("Left", self.FolderTreeView, self.on_collapse_row_accelerator)
        setup_accelerator("Right", self.FolderTreeView, self.on_expand_row_accelerator)

        self.dir_column_numbers = list(range(self.dir_store.get_n_columns()))
        cols = initialise_columns(
            None, self.FolderTreeView,
            ["folders", _("Folders"), -1, "text", None]  # 0
        )

        cols["folders"].set_sort_column_id(0)

        self.user_popup = popup = PopupMenu(self.frame, None, self.on_tab_popup)
        popup.setup_user_menu(user, page="userbrowse")
        popup.setup(
            ("", None),
            ("#" + _("_Save Shares List to Disk"), self.on_save),
            ("#" + _("Close All Tabs..."), self.on_close_all_tabs),
            ("#" + _("_Close Tab"), self.on_close)
        )

        self.popup_menu_downloads_folders = PopupMenu(self.frame)
        self.popup_menu_downloads_folders.setup(
            ("#" + _("_Download Folder"), self.on_download_directory),
            ("#" + _("Download Folder _To..."), self.on_download_directory_to),
            ("#" + _("Download _Recursive"), self.on_download_directory_recursive),
            ("#" + _("Download R_ecursive To..."), self.on_download_directory_recursive_to)
        )

        self.popup_menu_downloads_files = PopupMenu(self.frame)
        self.popup_menu_downloads_files.setup(
            ("#" + _("_Download File(s)"), self.on_download_files),
            ("#" + _("Download _To..."), self.on_download_files_to),
            ("", None),
            ("#" + _("_Download Folder"), self.on_download_directory),
            ("#" + _("Download Folder _To..."), self.on_download_directory_to),
            ("#" + _("Download _Recursive"), self.on_download_directory_recursive),
            ("#" + _("Download R_ecursive To..."), self.on_download_directory_recursive_to)
        )

        self.popup_menu_uploads_folders = PopupMenu(self.frame)
        self.popup_menu_uploads_folders.setup(
            ("#" + _("Upload Folder To..."), self.on_upload_directory_to),
            ("#" + _("Upload Folder Recursive To..."), self.on_upload_directory_recursive_to)
        )

        self.popup_menu_uploads_files = PopupMenu(self.frame)
        self.popup_menu_uploads_files.setup(
            ("#" + _("Upload Folder To..."), self.on_upload_directory_to),
            ("#" + _("Upload Folder Recursive To..."), self.on_upload_directory_recursive_to),
            ("#" + _("Up_load File(s)"), self.on_upload_files)
        )

        self.folder_popup_menu = PopupMenu(self.frame, self.FolderTreeView, self.on_folder_popup_menu)

        if user == config.sections["server"]["login"]:
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
                ("#" + _("Copy _Folder Path"), self.on_copy_folder_path),
                ("#" + _("Copy _URL"), self.on_copy_dir_url),
                ("", None),
                (">" + _("User"), self.user_popup)
            )
        else:
            self.folder_popup_menu.setup(
                ("#" + _("_Download Folder"), self.on_download_directory),
                ("#" + _("Download Folder _To..."), self.on_download_directory_to),
                ("#" + _("Download _Recursive"), self.on_download_directory_recursive),
                ("#" + _("Download R_ecursive To..."), self.on_download_directory_recursive_to),
                ("", None),
                ("#" + _("Copy _Folder Path"), self.on_copy_folder_path),
                ("#" + _("Copy _URL"), self.on_copy_dir_url),
                ("", None),
                (">" + _("User"), self.user_popup)
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
        setup_accelerator("<Alt>Return", self.FileTreeView, self.on_file_properties_accelerator)

        self.file_column_numbers = [i for i in range(self.file_store.get_n_columns())]
        cols = initialise_columns(
            "user_browse", self.FileTreeView,
            ["filename", _("Filename"), 600, "text", None],
            ["size", _("Size"), 100, "number", None],
            ["bitrate", _("Bitrate"), 100, "number", None],
            ["length", _("Length"), 100, "number", None]
        )
        cols["filename"].set_sort_column_id(0)
        cols["size"].set_sort_column_id(4)
        cols["bitrate"].set_sort_column_id(5)
        cols["length"].set_sort_column_id(6)

        self.file_popup_menu = PopupMenu(self.frame, self.FileTreeView, self.on_file_popup_menu)

        if user == config.sections["server"]["login"]:
            self.file_popup_menu.setup(
                ("#" + "selected_files", None),
                ("", None),
                (">" + _("Download"), self.popup_menu_downloads_files),
                (">" + _("Upload"), self.popup_menu_uploads_files),
                ("", None),
                ("#" + _("Send to _Player"), self.on_play_files),
                ("#" + _("Open in File _Manager"), self.on_file_manager),
                ("#" + _("F_ile Properties"), self.on_file_properties),
                ("", None),
                ("#" + _("Copy _File Path"), self.on_copy_file_path),
                ("#" + _("Copy _URL"), self.on_copy_url),
                ("", None),
                (">" + _("User"), self.user_popup)
            )
        else:
            self.file_popup_menu.setup(
                ("#" + "selected_files", None),
                ("", None),
                (">" + _("Download"), self.popup_menu_downloads_files),
                ("", None),
                ("#" + _("F_ile Properties"), self.on_file_properties),
                ("", None),
                ("#" + _("Copy _File Path"), self.on_copy_file_path),
                ("#" + _("Copy _URL"), self.on_copy_url),
                ("", None),
                (">" + _("User"), self.user_popup)
            )

        self.ExpandButton.set_active(True)
        self.update_visuals()

    def set_label(self, label):
        self.user_popup.set_widget(label)

    def update_visuals(self):

        for widget in list(self.__dict__.values()):
            update_widget_visuals(widget, list_font_target="browserfont")

    def on_expand(self, widget):

        if self.ExpandButton.get_active():
            self.FolderTreeView.expand_all()
            self.expand.set_property("icon-name", "go-up-symbolic")
        else:
            self.FolderTreeView.collapse_all()
            self.expand.set_property("icon-name", "go-down-symbolic")

    def on_folder_row_activated(self, treeview, path, column):
        if self.user != config.sections["server"]["login"]:
            self.on_download_directory()

    def on_folder_popup_menu(self, menu, widget):

        actions = menu.get_actions()

        if self.user == config.sections["server"]["login"]:
            for i in (_("_Download Folder"), _("Download Folder _To..."), _("Download _Recursive"),
                      _("Download R_ecursive To..."), _("Upload Folder To..."), _("Upload Folder Recursive To..."),
                      _("Open in File _Manager"), _("Copy _Folder Path"), _("Copy _URL")):
                actions[i].set_enabled(self.selected_folder)
        else:
            for i in (_("_Download Folder"), _("Download Folder _To..."), _("Download _Recursive"),
                      _("Download R_ecursive To..."), _("Copy _Folder Path"), _("Copy _URL")):
                actions[i].set_enabled(self.selected_folder)

        self.user_popup.toggle_user_items()

    def select_files(self):

        self.selected_files.clear()
        model, paths = self.FileTreeView.get_selection().get_selected_rows()

        for path in paths:
            iterator = model.get_iter(path)
            rawfilename = model.get_value(iterator, 0)
            filesize = model.get_value(iterator, 4)

            self.selected_files[rawfilename] = filesize

    def on_file_row_activated(self, treeview, path, column):

        self.select_files()

        if self.user == config.sections["server"]["login"]:
            self.on_play_files()
        else:
            self.on_download_files()

    def on_file_popup_menu(self, menu, widget):

        self.select_files()
        num_selected_files = len(self.selected_files)

        actions = menu.get_actions()

        if self.user == config.sections["server"]["login"]:
            for i in (_("Download"), _("Upload"), _("Send to _Player"), _("F_ile Properties"),
                      _("Copy _File Path"), _("Copy _URL")):
                actions[i].set_enabled(num_selected_files)

            actions[_("Open in File _Manager")].set_enabled(self.selected_folder)
        else:
            for i in (_("Download"), _("F_ile Properties"), _("Copy _File Path"), _("Copy _URL")):
                actions[i].set_enabled(num_selected_files)

        menu.set_num_selected_files(num_selected_files)
        self.user_popup.toggle_user_items()

    def clear_model(self):

        self.query = None
        self.selected_folder = None
        self.shares.clear()
        self.selected_files.clear()
        self.directories.clear()
        self.files.clear()
        self.dir_store.clear()
        self.file_store.clear()
        self.search_list.clear()

    def make_new_model(self, shares, private_shares=None):

        # Temporarily disable sorting for improved performance
        self.dir_store.set_default_sort_func(lambda *args: 0)
        self.dir_store.set_sort_column_id(-1, Gtk.SortType.ASCENDING)

        self.clear_model()
        self.shares = shares
        private_size = num_private_folders = 0

        # Generate the directory tree and select first directory
        size, num_folders = self.create_folder_tree(shares)

        if private_shares:
            self.shares = shares + private_shares
            private_size, num_private_folders = self.create_folder_tree(private_shares, private=True)

        self.AmountShared.set_text(human_size(size + private_size))
        self.NumDirectories.set_text(str(num_folders + num_private_folders))

        if self.ExpandButton.get_active():
            self.FolderTreeView.expand_all()
        else:
            self.FolderTreeView.collapse_all()

        self.dir_store.set_sort_column_id(0, Gtk.SortType.ASCENDING)

        iterator = self.dir_store.get_iter_first()
        sel = self.FolderTreeView.get_selection()
        sel.unselect_all()

        if iterator:
            path = self.dir_store.get_path(iterator)
            sel.select_path(path)

        self.set_finished()

    def create_folder_tree(self, shares, private=False):

        size = 0

        if not shares:
            num_folders = 0
            return size, num_folders

        for folder, files in shares:
            current_path = ""
            root_processed = False

            for subfolder in folder.split('\\'):
                parent = self.directories.get(current_path)

                if not root_processed:
                    current_path = subfolder
                    root_processed = True
                else:
                    current_path = '\\'.join([current_path, subfolder])

                if current_path in self.directories:
                    # Folder was already added to tree
                    continue

                if not subfolder:
                    # Most likely a root folder
                    subfolder = '\\'

                if private:
                    subfolder = "[PRIVATE FOLDER]  " + subfolder

                self.directories[current_path] = self.dir_store.insert_with_values(
                    parent, -1, self.dir_column_numbers, [subfolder]
                )

            for filedata in files:
                size += filedata[2]

        return size, len(shares)

    def browse_queued_folder(self):
        """ Browse a queued folder in the share """

        try:
            iterator = self.directories[self.queued_folder]
        except KeyError:
            # Folder not found
            return

        if self.queued_folder:
            sel = self.FolderTreeView.get_selection()
            sel.unselect_all()

            path = self.dir_store.get_path(iterator)
            self.FolderTreeView.expand_to_path(path)
            sel.select_path(path)
            self.FolderTreeView.scroll_to_cell(path, None, True, 0.5, 0.5)

            self.queued_folder = None

    def set_directory(self, iter_data):

        directory = None

        for d, i in self.directories.items():
            if i.user_data == iter_data:
                directory = d
                break

        if not directory:
            return

        # Temporarily disable sorting for improved performance
        self.file_store.set_default_sort_func(lambda *args: 0)
        self.file_store.set_sort_column_id(-1, Gtk.SortType.ASCENDING)

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
                log.add(_("Error while attempting to display folder '%(folder)s', reported error: %(error)s"),
                        {'folder': directory, 'error': msg})

        self.file_store.set_sort_column_id(0, Gtk.SortType.ASCENDING)

    def on_save(self, *args):

        sharesdir = os.path.join(config.data_dir, "usershares")

        try:
            if not os.path.exists(sharesdir):
                os.makedirs(sharesdir)

        except Exception as msg:
            log.add(_("Can't create directory '%(folder)s', reported error: %(error)s"),
                    {'folder': sharesdir, 'error': msg})

        try:
            get_path(sharesdir, self.user, self.dump_shares_to_file)
            log.add(_("Saved list of shared files for user '%(user)s' to %(dir)s"),
                    {'user': self.user, 'dir': sharesdir})

        except Exception as msg:
            log.add(_("Can't save shares, '%(user)s', reported error: %(error)s"), {'user': self.user, 'error': msg})

    def dump_shares_to_file(self, path, data):

        with open(path, "w", encoding="utf-8") as sharesfile:
            json.dump(self.shares, sharesfile, ensure_ascii=False)

    def save_columns(self):
        save_columns("user_browse", self.FileTreeView.get_columns())

    def shared_file_list(self, msg):

        self.make_new_model(msg.list, msg.privatelist)
        self.info_bar.set_visible(False)

        if msg.list or (config.sections["ui"]["private_shares"] and msg.privatelist):
            self.browse_queued_folder()

        else:
            self.info_bar.show_message(
                _("User's list of shared files is empty. Either the user is not sharing anything, "
                  "or they are sharing files privately.")
            )

        self.set_finished()

    def show_connection_error(self):

        self.info_bar.show_message(
            _("Unable to request shared files from user. Either the user is offline, you both have "
              "a closed listening port, or there's a temporary connectivity issue.")
        )

        self.set_finished()

    def set_in_progress(self, indeterminate_progress):

        if not indeterminate_progress:
            self.progressbar1.set_fraction(0.0)
        else:
            self.progressbar1.set_fraction(0.5)

        self.RefreshButton.set_sensitive(False)

    def set_finished(self):

        self.frame.request_tab_hilite(self.frame.UserBrowseTabLabel)
        self.userbrowses.request_changed(self.Main)

        self.progressbar1.set_fraction(1.0)
        self.RefreshButton.set_sensitive(True)

    def update_gauge(self, msg):

        if msg.total == 0 or msg.bufferlen == 0:
            fraction = 0.0
        elif msg.bufferlen >= msg.total:
            fraction = 1.0
        else:
            fraction = float(msg.bufferlen) / msg.total

        self.progressbar1.set_fraction(fraction)

    def copy_selected_path(self, is_file=False):

        if self.selected_folder is None:
            return

        text = self.selected_folder

        if is_file and self.selected_files:
            text = "\\".join([self.selected_folder, next(iter(self.selected_files))])

        copy_text(text)

    def on_select_dir(self, selection):

        model, iterator = selection.get_selected()

        if iterator is None:
            return

        self.set_directory(iterator.user_data)

    def on_expand_row_accelerator(self, *args):
        """ Right: expand row """

        path, _focus_column = self.FolderTreeView.get_cursor()
        self.FolderTreeView.expand_row(path, False)
        return True

    def on_collapse_row_accelerator(self, *args):
        """ Left: expand row """

        path, _focus_column = self.FolderTreeView.get_cursor()
        self.FolderTreeView.collapse_row(path)
        return True

    def on_file_properties_accelerator(self, *args):
        """ Alt+Return: show file properties dialog """

        self.on_file_properties()
        return True

    def on_file_properties(self, *args):

        data = []
        model, paths = self.FileTreeView.get_selection().get_selected_rows()

        for path in paths:
            iterator = model.get_iter(path)
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
                "queue": None,
                "speed": None,
                "country": None
            })

        if data:
            FileProperties(self.frame, data).show()

    def on_download_directory(self, *args):

        if self.selected_folder is not None:
            self.download_directory(self.selected_folder)

    def on_download_directory_recursive(self, *args):
        self.download_directory(self.selected_folder, prefix="", recurse=True)

    def on_download_directory_to_selected(self, selected, recurse):

        try:
            self.download_directory(self.selected_folder, prefix=os.path.join(selected, ""), recurse=recurse)
        except IOError:  # failed to open
            log.add('Failed to open %r for reading', selected)  # notify user

    def on_download_directory_to(self, *args, recurse=False):

        choose_dir(
            parent=self.frame.MainWindow,
            callback=self.on_download_directory_to_selected,
            callback_data=recurse,
            initialdir=config.sections["transfers"]["downloaddir"],
            multichoice=False
        )

    def on_download_directory_recursive_to(self, *args):
        self.on_download_directory_to(recurse=True)

    def download_directory(self, folder, prefix="", recurse=False):

        if folder is None:
            return

        # Remember custom download location
        self.frame.np.transfers.requested_folders[self.user][folder] = prefix

        # Get final download destination
        destination = self.frame.np.transfers.get_folder_destination(self.user, folder)

        for d, files in self.shares:
            # Find the wanted directory
            if d != folder:
                continue

            if config.sections["transfers"]["reverseorder"]:
                files.sort(key=lambda x: x[1], reverse=True)

            for file in files:
                virtualpath = "\\".join([folder, file[1]])
                size = file[2]
                h_bitrate, bitrate, h_length, length = get_result_bitrate_length(size, file[4])

                self.frame.np.transfers.get_file(
                    self.user, virtualpath, destination,
                    size=size, bitrate=h_bitrate, length=h_length)

        if not recurse:
            return

        for subdir, subf in self.shares:
            if folder in subdir and folder != subdir:
                self.download_directory(subdir, prefix=os.path.join(destination, ""))

    def on_download_files(self, *args, prefix=""):

        folder = self.selected_folder

        for d, f in self.shares:
            # Find the wanted directory
            if d != folder:
                continue

            for file in f:
                # Find the wanted file
                if file[1] not in self.selected_files:
                    continue

                virtualpath = "\\".join([folder, file[1]])
                size = file[2]
                h_bitrate, bitrate, h_length, length = get_result_bitrate_length(size, file[4])

                # Get the file
                self.frame.np.transfers.get_file(
                    self.user, virtualpath, prefix,
                    size=size, bitrate=h_bitrate, length=h_length)

            # We have found the wanted directory: we can break out of the loop
            break

    def on_download_files_to_selected(self, selected, data):

        try:
            self.on_download_files(prefix=selected)
        except IOError:  # failed to open
            log.add('failed to open %r for reading', selected)  # notify user

    def on_download_files_to(self, *args):

        try:
            _, folder = self.selected_folder.rsplit("\\", 1)
        except ValueError:
            folder = self.selected_folder

        download_folder = config.sections["transfers"]["downloaddir"]
        path = os.path.join(download_folder, folder)

        if not os.path.exists(path) or not os.path.isdir(path):
            path = download_folder

        choose_dir(
            parent=self.frame.MainWindow,
            callback=self.on_download_files_to_selected,
            initialdir=path,
            multichoice=False
        )

    def on_upload_directory_to_response(self, dialog, response_id, recurse):

        user = dialog.get_response_value()
        folder = self.selected_folder
        dialog.destroy()

        if response_id != Gtk.ResponseType.OK:
            return

        if not user or folder is None:
            return

        self.frame.np.send_message_to_peer(user, slskmessages.UploadQueueNotification(None))
        self.upload_directory_to(user, folder, recurse)

    def on_upload_directory_to(self, *args, recurse=False):

        folder = self.selected_folder

        if folder is None:
            return

        users = []
        for row in config.sections["server"]["userlist"]:
            if row and isinstance(row, list):
                user = str(row[0])
                users.append(user)

        users.sort()
        entry_dialog(
            parent=self.frame.MainWindow,
            title=_("Upload Folder's Contents"),
            message=_('Enter the name of a user you wish to upload to:'),
            callback=self.on_upload_directory_to_response,
            callback_data=recurse,
            droplist=users
        )

    def on_upload_directory_recursive_to(self, *args):
        self.on_upload_directory_to(recurse=True)

    def upload_directory_to(self, user, folder, recurse=False):

        if folder == "" or folder is None or user is None or user == "":
            return

        ldir = folder.split("\\")[-1]

        locally_queued = False
        for d, f in self.shares:

            # Find the wanted directory
            if d != folder:
                continue

            for file in f:
                filename = "\\".join([folder, file[1]])
                size = file[2]
                self.frame.np.transfers.push_file(user, filename, ldir, size=size, locally_queued=locally_queued)
                locally_queued = True

        if not recurse:
            return

        for subdir, subf in self.shares:
            if folder in subdir and folder != subdir:
                self.upload_directory_to(user, subdir, recurse)

    def on_upload_files_response(self, dialog, response_id, data):

        user = dialog.get_response_value()
        folder = self.selected_folder
        dialog.destroy()

        if response_id != Gtk.ResponseType.OK:
            return

        if not user or folder is None:
            return

        self.frame.np.send_message_to_peer(user, slskmessages.UploadQueueNotification(None))

        locally_queued = False
        prefix = ""

        for fn, size in self.selected_files.items():
            self.frame.np.transfers.push_file(
                user, "\\".join([folder, fn]), prefix, size=size, locally_queued=locally_queued)
            locally_queued = True

    def on_upload_files(self, *args):

        users = []

        for row in config.sections["server"]["userlist"]:
            if row and isinstance(row, list):
                user = str(row[0])
                users.append(user)

        users.sort()
        entry_dialog(
            parent=self.frame.MainWindow,
            title=_('Upload File(s)'),
            message=_('Enter the name of a user you wish to upload to:'),
            callback=self.on_upload_files_response,
            droplist=users
        )

    def on_play_files(self, *args):

        path = self.frame.np.shares.virtual2real(self.selected_folder)

        for fn in self.selected_files:
            playfile = os.sep.join([path, fn])

            if os.path.exists(playfile):
                command = config.sections["players"]["default"]
                open_file_path(playfile, command)

    def find_matches(self):

        self.search_list.clear()

        for directory, files in self.shares:

            if self.query in directory.lower() and directory not in self.search_list:
                self.search_list.append(directory)
                continue

            for file in files:
                if self.query in file[1].lower() and directory not in self.search_list:
                    self.search_list.append(directory)

    def on_search(self, *args):

        query = self.SearchEntry.get_text().lower()

        if not query:
            return

        if self.query == query:
            self.search_position += 1
        else:
            self.search_position = 0
            self.query = query

            self.find_matches()

        if not self.search_list:
            return

        if self.search_position >= len(self.search_list):
            self.search_position = 0

        self.search_list = sorted(self.search_list, key=str.casefold)
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

    def on_refresh(self, *args):

        self.clear_model()
        self.FolderTreeView.grab_focus()
        self.info_bar.set_visible(False)

        self.set_in_progress(self.indeterminate_progress)
        self.frame.np.userbrowse.browse_user(self.user, local_shares_type=self.local_shares_type, new_request=True)

    def on_copy_folder_path(self, *args):
        self.copy_selected_path()

    def on_copy_file_path(self, *args):
        self.copy_selected_path(is_file=True)

    def on_copy_url(self, *args):

        if self.selected_files:
            path = "\\".join([self.selected_folder, next(iter(self.selected_files))])
            copy_file_url(self.user, path)

    def on_copy_dir_url(self, *args):

        if self.selected_folder is None:
            return

        path = self.selected_folder + '\\'
        copy_file_url(self.user, path)

    def on_file_manager(self, *args):

        if self.selected_folder is None:
            return

        path = self.frame.np.shares.virtual2real(self.selected_folder)
        command = config.sections["ui"]["filemanager"]

        open_file_path(path, command)

    def on_tab_popup(self, *args):
        self.user_popup.toggle_user_items()

    def on_close(self, *args):

        del self.userbrowses.pages[self.user]
        self.frame.np.userbrowse.remove_user(self.user)
        self.userbrowses.remove_page(self.Main)

        if self.userbrowses.get_n_pages() == 0:
            self.frame.UserBrowseStatusPage.show()

    def on_close_all_tabs(self, *args):
        self.userbrowses.remove_all_pages()
