# COPYRIGHT (C) 2020-2022 Nicotine+ Team
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

from gi.repository import GLib
from gi.repository import GObject
from gi.repository import Gtk

from pynicotine.config import config
from pynicotine.gtkgui.dialogs.fileproperties import FileProperties
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
from pynicotine.gtkgui.widgets.treeview import show_file_path_tooltip
from pynicotine.gtkgui.widgets.ui import UserInterface
from pynicotine.logfacility import log
from pynicotine.utils import get_result_bitrate_length
from pynicotine.utils import human_size
from pynicotine.utils import open_file_path


class UserBrowses(IconNotebook):

    def __init__(self, frame):

        IconNotebook.__init__(self, frame, frame.userbrowse_notebook, "userbrowse")
        self.notebook.connect("switch-page", self.on_switch_browse_page)

    def on_switch_browse_page(self, _notebook, page, _page_num):

        if self.frame.current_page_id != self.page_id:
            return

        for tab in self.pages.values():
            if tab.Main == page:

                # Remember folder or file selection
                if tab.num_selected_files >= 1:
                    GLib.idle_add(lambda: tab.FileTreeView.grab_focus() == -1)  # pylint:disable=cell-var-from-loop
                else:
                    GLib.idle_add(lambda: tab.FolderTreeView.grab_focus() == -1)  # pylint:disable=cell-var-from-loop

                break

    def show_user(self, user, folder=None, local_shares_type=None, indeterminate_progress=False, switch_page=True):

        if user not in self.pages:
            self.pages[user] = page = UserBrowse(self, user)
            page.set_in_progress(indeterminate_progress)

            self.append_page(page.Main, user, page.on_close, user=user)
            page.set_label(self.get_tab_label_inner(page.Main))

            if self.get_n_pages() > 0:
                self.frame.userbrowse_status_page.hide()

        page = self.pages[user]

        page.indeterminate_progress = indeterminate_progress
        page.local_shares_type = local_shares_type
        page.queued_folder = folder
        page.browse_queued_folder()

        if switch_page:
            self.set_current_page(self.page_num(page.Main))
            self.frame.change_main_page("userbrowse")

    def show_connection_error(self, user):
        if user in self.pages:
            self.pages[user].show_connection_error()

    def message_progress(self, msg):
        if msg.user in self.pages:
            self.pages[msg.user].message_progress(msg)

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

    def update_visuals(self):
        for page in self.pages.values():
            page.update_visuals()

    def server_disconnect(self):
        for user, page in self.pages.items():
            self.set_user_status(page.Main, user, 0)


class UserBrowse(UserInterface):

    def __init__(self, userbrowses, user):

        super().__init__("ui/userbrowse.ui")

        self.userbrowses = userbrowses
        self.frame = userbrowses.frame
        self.user = user
        self.local_shares_type = None
        self.queued_folder = None

        self.shares = {}
        self.dir_iters = {}
        self.dir_user_data = {}
        self.file_iters = {}

        self.selected_folder = None
        self.selected_files = {}
        self.num_selected_files = 0

        self.search_list = []
        self.query = None
        self.search_position = 0

        self.info_bar = InfoBar(self.InfoBar, Gtk.MessageType.INFO)

        # Setup FolderTreeView
        self.dir_store = Gtk.TreeStore(str)
        self.dir_column_numbers = list(range(self.dir_store.get_n_columns()))
        cols = initialise_columns(
            self.frame, None, self.FolderTreeView,
            ["folder", _("Folder"), -1, "text", None]
        )

        self.FolderTreeView.get_selection().connect("changed", self.on_select_dir)
        self.FolderTreeView.set_model(self.dir_store)

        # Popup Menu (FolderTreeView)
        self.user_popup = popup = PopupMenu(self.frame, None, self.on_tab_popup)
        popup.setup_user_menu(user, page="userbrowse")
        popup.add_items(
            ("", None),
            ("#" + _("_Save Shares List to Disk"), self.on_save),
            ("#" + _("Close All Tabs…"), self.on_close_all_tabs),
            ("#" + _("_Close Tab"), self.on_close)
        )

        self.folder_popup_menu = PopupMenu(self.frame, self.FolderTreeView, self.on_folder_popup_menu)

        if user == config.sections["server"]["login"]:
            self.folder_popup_menu.add_items(
                ("#" + _("Upload Folder…"), self.on_upload_directory_to),
                ("#" + _("Upload Folder & Subfolder(s)…"), self.on_upload_directory_recursive_to),
                ("", None),
                ("#" + _("Open in File _Manager"), self.on_file_manager),
                ("", None),
                ("#" + _("Copy _Folder Path"), self.on_copy_folder_path),
                ("#" + _("Copy _URL"), self.on_copy_dir_url),
                ("", None),
                (">" + _("User"), self.user_popup)
            )
        else:
            self.folder_popup_menu.add_items(
                ("#" + _("_Download Folder"), self.on_download_directory),
                ("#" + _("Download Folder _To…"), self.on_download_directory_to),
                ("#" + _("Download Folder & Subfolder(s)"), self.on_download_directory_recursive),
                ("#" + _("Download Folder & Subfolder(s) To…"), self.on_download_directory_recursive_to),
                ("", None),
                ("#" + _("Copy _Folder Path"), self.on_copy_folder_path),
                ("#" + _("Copy _URL"), self.on_copy_dir_url),
                ("", None),
                (">" + _("User"), self.user_popup)
            )

        # Setup FileTreeView
        self.treeview_name = "user_browse"
        self.file_store = Gtk.ListStore(
            str,                  # (0) file name
            str,                  # (1) hsize
            str,                  # (2) hbitrate
            str,                  # (3) hlength
            GObject.TYPE_UINT64,  # (4) size
            GObject.TYPE_UINT64,  # (5) bitrate
            GObject.TYPE_UINT64   # (6) length
        )

        self.file_column_offsets = {}
        self.file_column_numbers = list(range(self.file_store.get_n_columns()))
        cols = initialise_columns(
            self.frame, "user_browse", self.FileTreeView,
            ["filename", _("Filename"), 600, "text", None],
            ["size", _("Size"), 100, "number", None],
            ["bitrate", _("Bitrate"), 100, "number", None],
            ["length", _("Length"), 100, "number", None]
        )
        cols["filename"].set_sort_column_id(0)
        cols["size"].set_sort_column_id(4)
        cols["bitrate"].set_sort_column_id(5)
        cols["length"].set_sort_column_id(6)

        self.FileTreeView.get_selection().connect("changed", self.on_select_file)
        self.FileTreeView.set_model(self.file_store)

        for column in self.FileTreeView.get_columns():
            self.file_column_offsets[column.get_title()] = 0
            column.connect("notify::x-offset", self.on_column_position_changed)

        # Popup Menu (FileTreeView)
        self.file_popup_menu = PopupMenu(self.frame, self.FileTreeView, self.on_file_popup_menu)

        if user == config.sections["server"]["login"]:
            self.file_popup_menu.add_items(
                ("#" + "selected_files", None),
                ("", None),
                ("#" + _("Up_load File(s)…"), self.on_upload_files),
                ("#" + _("Upload Folder…"), self.on_upload_directory_to),
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
            self.file_popup_menu.add_items(
                ("#" + "selected_files", None),
                ("", None),
                ("#" + _("_Download File(s)"), self.on_download_files),
                ("#" + _("Download File(s) _To…"), self.on_download_files_to),
                ("", None),
                ("#" + _("_Download Folder"), self.on_download_directory),
                ("#" + _("Download Folder _To…"), self.on_download_directory_to),
                ("", None),
                ("#" + _("F_ile Properties"), self.on_file_properties),
                ("", None),
                ("#" + _("Copy _File Path"), self.on_copy_file_path),
                ("#" + _("Copy _URL"), self.on_copy_url),
                ("", None),
                (">" + _("User"), self.user_popup)
            )

        # Key Bindings (FolderTreeView)
        setup_accelerator("Left", self.FolderTreeView, self.on_folder_collapse_accelerator)
        setup_accelerator("minus", self.FolderTreeView, self.on_folder_collapse_accelerator)  # "-"
        setup_accelerator("backslash", self.FolderTreeView, self.on_folder_collapse_sub_accelerator)  # "\"
        setup_accelerator("equal", self.FolderTreeView, self.on_folder_expand_sub_accelerator)  # "=" (for US/UK laptop)
        setup_accelerator("Right", self.FolderTreeView, self.on_folder_expand_accelerator)

        setup_accelerator("<Shift>Return", self.FolderTreeView, self.on_folder_focus_filetree_accelerator)  # brwse into
        setup_accelerator("<Primary>Return", self.FolderTreeView, self.on_folder_transfer_to_accelerator)  # w/to prompt
        setup_accelerator("<Shift><Primary>Return", self.FolderTreeView, self.on_folder_transfer_accelerator)  # no prmt
        setup_accelerator("<Primary><Alt>Return", self.FolderTreeView, self.on_folder_open_manager_accelerator)

        # Key Bindings (FileTreeView)
        for accelerator in ("<Shift>Tab", "BackSpace", "backslash"):  # Avoid header, navigate up, "\"
            setup_accelerator(accelerator, self.FileTreeView, self.on_focus_folder_accelerator)

        setup_accelerator("Left", self.FileTreeView, self.on_focus_folder_left_accelerator)

        setup_accelerator("<Shift>Return", self.FileTreeView, self.on_file_transfer_multi_accelerator)  # multi activate
        setup_accelerator("<Primary>Return", self.FileTreeView, self.on_file_transfer_to_accelerator)  # with to prompt
        setup_accelerator("<Shift><Primary>Return", self.FileTreeView, self.on_file_transfer_accelerator)  # no prompt
        setup_accelerator("<Primary><Alt>Return", self.FileTreeView, self.on_file_open_manager_accelerator)
        setup_accelerator("<Alt>Return", self.FileTreeView, self.on_file_properties_accelerator)

        # Key Bindings (General)
        for widget in (self.Main, self.FolderTreeView, self.FileTreeView):
            setup_accelerator("<Primary>f", widget, self.on_search_accelerator)  # Find focus

        for widget in (self.Main, self.SearchEntry):
            setup_accelerator("<Primary>g", widget, self.on_search_next_accelerator)  # Next search match
            setup_accelerator("<Shift><Primary>g", widget, self.on_search_previous_accelerator)

        setup_accelerator("Escape", self.SearchEntry, self.on_search_escape_accelerator)
        setup_accelerator("F3", self.Main, self.on_search_next_accelerator)
        setup_accelerator("<Shift>F3", self.Main, self.on_search_previous_accelerator)

        setup_accelerator("<Primary>backslash", self.Main, self.on_expand_accelerator)  # expand / collapse all (button)
        setup_accelerator("F5", self.Main, self.on_refresh_accelerator)
        setup_accelerator("<Primary>r", self.Main, self.on_refresh_accelerator)  # Refresh
        setup_accelerator("<Primary>s", self.Main, self.on_save_accelerator)  # Save Shares List

        self.ExpandButton.set_active(True)
        self.update_visuals()

    def set_label(self, label):
        self.user_popup.set_parent(label)

    def update_visuals(self):

        for widget in list(self.__dict__.values()):
            update_widget_visuals(widget, list_font_target="browserfont")

    """ Folder/File Views """

    def clear_model(self):

        self.query = None
        self.search_list.clear()

        self.selected_folder = None
        self.selected_files.clear()

        self.shares.clear()

        self.dir_iters.clear()
        self.dir_user_data.clear()
        self.dir_store.clear()

        self.file_iters.clear()
        self.file_store.clear()

    def make_new_model(self, shares, private_shares=None):

        self.clear_model()
        private_size = num_private_folders = 0

        # Generate the directory tree and select first directory
        size, num_folders = self.create_folder_tree(shares)

        if private_shares:
            shares = shares + private_shares
            private_size, num_private_folders = self.create_folder_tree(private_shares, private=True)

        # Sort files
        for _folder, files in shares:
            files.sort()

        self.shares = dict(shares)

        self.AmountShared.set_text(human_size(size + private_size))
        self.NumDirectories.set_text(str(num_folders + num_private_folders))

        if self.ExpandButton.get_active():
            self.FolderTreeView.expand_all()
        else:
            self.FolderTreeView.collapse_all()

        iterator = self.dir_store.get_iter_first()
        sel = self.FolderTreeView.get_selection()
        sel.unselect_all()

        if iterator:
            path = self.dir_store.get_path(iterator)
            sel.select_path(path)

        self.set_finished()

    def create_folder_tree(self, shares, private=False):

        total_size = 0

        if not shares:
            num_folders = 0
            return total_size, num_folders

        # Sort folders
        shares.sort()

        for folder, files in shares:
            current_path = None
            root_processed = False

            for subfolder in folder.split('\\'):
                parent = self.dir_iters.get(current_path)

                if not root_processed:
                    current_path = subfolder
                    root_processed = True
                else:
                    current_path = '\\'.join([current_path, subfolder])

                if current_path in self.dir_iters:
                    # Folder was already added to tree
                    continue

                if not subfolder:
                    # Most likely a root folder
                    subfolder = '\\'

                if private:
                    subfolder = "[PRIVATE FOLDER]  " + subfolder

                self.dir_iters[current_path] = iterator = self.dir_store.insert_with_values(
                    parent, -1, self.dir_column_numbers, [subfolder]
                )
                self.dir_user_data[iterator.user_data] = current_path

            for filedata in files:
                total_size += filedata[2]

        return total_size, len(shares)

    def browse_queued_folder(self):

        iterator = self.dir_iters.get(self.queued_folder)

        if not iterator:
            return

        self.queued_folder = None
        sel = self.FolderTreeView.get_selection()
        path = self.dir_store.get_path(iterator)

        self.FolderTreeView.expand_to_path(path)
        sel.select_path(path)
        self.FolderTreeView.scroll_to_cell(path, None, True, 0.5, 0.5)

    def shared_file_list(self, msg):

        self.make_new_model(msg.list, msg.privatelist)
        self.info_bar.set_visible(False)

        if msg.list or msg.privatelist:
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

    def message_progress(self, msg):

        if msg.total == 0 or msg.position == 0:
            fraction = 0.0
        elif msg.position >= msg.total:
            fraction = 1.0
        else:
            fraction = float(msg.position) / msg.total

        self.progressbar1.set_fraction(fraction)

    def set_finished(self):

        self.userbrowses.request_tab_hilite(self.Main)
        self.progressbar1.set_fraction(1.0)
        self.RefreshButton.set_sensitive(True)

    def set_directory(self, iter_user_data):

        directory = self.dir_user_data.get(iter_user_data)

        if directory is None:
            return

        self.selected_folder = directory
        self.file_store.clear()
        self.file_iters.clear()

        files = self.shares.get(directory)

        if not files:
            return

        # Temporarily disable sorting for increased performance
        sort_column, sort_type = self.file_store.get_sort_column_id()
        self.file_store.set_default_sort_func(lambda *_args: 0)
        self.file_store.set_sort_column_id(-1, Gtk.SortType.ASCENDING)

        for file in files:
            # Filename, HSize, Bitrate, HLength, Size, Length
            filename = file[1]
            size = file[2]
            h_bitrate, bitrate, h_length, length = get_result_bitrate_length(size, file[4])

            file_row = [filename, human_size(size), h_bitrate, h_length,
                        GObject.Value(GObject.TYPE_UINT64, size),
                        GObject.Value(GObject.TYPE_UINT64, bitrate),
                        GObject.Value(GObject.TYPE_UINT64, length)]

            self.file_iters[filename] = self.file_store.insert_with_valuesv(-1, self.file_column_numbers, file_row)

        if sort_column is not None and sort_type is not None:
            self.file_store.set_sort_column_id(sort_column, sort_type)

    def select_files(self):

        self.selected_files.clear()
        model, paths = self.FileTreeView.get_selection().get_selected_rows()

        for path in paths:
            iterator = model.get_iter(path)
            rawfilename = model.get_value(iterator, 0)
            filesize = model.get_value(iterator, 4)

            self.selected_files[rawfilename] = filesize

    """ Download/Upload """

    def download_directory(self, folder, prefix="", recurse=False):

        if folder is None:
            return

        # Remember custom download location
        self.frame.np.transfers.requested_folders[self.user][folder] = prefix

        # Get final download destination
        destination = self.frame.np.transfers.get_folder_destination(self.user, folder)

        files = self.shares.get(folder)

        if files:
            if config.sections["transfers"]["reverseorder"]:
                files.sort(key=lambda x: x[1], reverse=True)

            for file_data in files:
                virtualpath = "\\".join([folder, file_data[1]])
                size = file_data[2]
                h_bitrate, _bitrate, h_length, _length = get_result_bitrate_length(size, file_data[4])

                self.frame.np.transfers.get_file(
                    self.user, virtualpath, destination,
                    size=size, bitrate=h_bitrate, length=h_length)

        if not recurse:
            return

        for subdir, _subf in self.shares.items():
            if folder in subdir and folder != subdir:
                self.download_directory(subdir, prefix=os.path.join(destination, ""))

    def upload_directory_to(self, user, folder, recurse=False):

        if not folder or not user:
            return

        ldir = folder.split("\\")[-1]
        files = self.shares.get(folder)

        if files:
            locally_queued = False

            for file_data in files:
                filename = "\\".join([folder, file_data[1]])
                size = file_data[2]
                self.frame.np.transfers.push_file(user, filename, size, ldir, locally_queued=locally_queued)
                locally_queued = True

        if not recurse:
            return

        for subdir, _subf in self.shares.items():
            if folder in subdir and folder != subdir:
                self.upload_directory_to(user, subdir, recurse)

    """ Search """

    def rebuild_search_matches(self):

        self.search_list.clear()

        for directory, files in self.shares.items():

            if self.query in directory.lower() and directory not in self.search_list:
                self.search_list.append(directory)
                continue

            for file_data in files:
                if self.query in file_data[1].lower() and directory not in self.search_list:
                    self.search_list.append(directory)

        self.search_list.sort()

    def select_search_match_folder(self):

        directory = self.search_list[self.search_position]
        path = self.dir_store.get_path(self.dir_iters[directory])

        self.FolderTreeView.expand_to_path(path)
        self.FolderTreeView.set_cursor(path)

    def select_search_match_files(self):

        result_files = []
        found_first_match = False

        for filepath in self.file_iters:
            if self.query in filepath.lower():
                result_files.append(filepath)

        result_files.sort()

        selection = self.FileTreeView.get_selection()
        selection.unselect_all()

        for filepath in result_files:
            # Select each matching file in folder
            path = self.file_store.get_path(self.file_iters[filepath])
            selection.select_path(path)

            if found_first_match:
                continue

            # Position cursor at first match
            self.FileTreeView.scroll_to_cell(path, None, True, 0.5, 0.5)
            found_first_match = True

    def find_search_matches(self, reverse=False):

        query = self.SearchEntry.get_text().lower()

        if not query:
            return False

        if self.query != query:
            # New search query, rebuild result list
            self.search_position = 0
            self.query = query

            self.rebuild_search_matches()
        else:
            # Increment/decrement search position
            self.search_position += -1 if reverse else 1

        if not self.search_list:
            return False

        if self.search_position < 0:
            self.search_position = len(self.search_list) - 1

        elif self.search_position >= len(self.search_list):
            self.search_position = 0

        # Set active folder
        self.select_search_match_folder()

        # Get matching files in the current folder
        self.select_search_match_files()
        return True

    """ Callbacks (FolderTreeView) """

    def on_select_dir(self, selection):

        _model, iterator = selection.get_selected()

        if iterator is None:
            return

        self.set_directory(iterator.user_data)

    def on_folder_popup_menu(self, *_args):
        self.user_popup.toggle_user_items()

    def on_download_directory(self, *_args):

        if self.selected_folder is not None:
            self.download_directory(self.selected_folder)

    def on_download_directory_recursive(self, *_args):
        self.download_directory(self.selected_folder, prefix="", recurse=True)

    def on_download_directory_to_selected(self, selected, recurse):

        try:
            self.download_directory(self.selected_folder, prefix=os.path.join(selected, ""), recurse=recurse)
        except OSError:  # failed to open
            log.add('Failed to open %r for reading', selected)  # notify user

    def on_download_directory_to(self, *_args, recurse=False):

        if recurse:
            str_title = _("Select Destination for Downloading Multiple Folders")
        else:
            str_title = _("Select Destination Folder")

        choose_dir(
            parent=self.frame.MainWindow,
            title=str_title,
            callback=self.on_download_directory_to_selected,
            callback_data=recurse,
            initialdir=config.sections["transfers"]["downloaddir"],
            multichoice=False
        )

    def on_download_directory_recursive_to(self, *_args):
        self.on_download_directory_to(recurse=True)

    def on_upload_directory_to_response(self, dialog, response_id, recurse):

        user = dialog.get_response_value()
        folder = self.selected_folder
        dialog.destroy()

        if response_id != Gtk.ResponseType.OK:
            return

        if not user or folder is None:
            return

        self.frame.np.userbrowse.send_upload_attempt_notification(user)
        self.upload_directory_to(user, folder, recurse)

    def on_upload_directory_to(self, *_args, recurse=False):

        folder = self.selected_folder

        if folder is None:
            return

        users = []
        for row in config.sections["server"]["userlist"]:
            if row and isinstance(row, list):
                user = str(row[0])
                users.append(user)

        users.sort()

        if recurse:
            str_title = _("Upload Folder (with Subfolders) To User")
        else:
            str_title = _("Upload Folder To User")

        entry_dialog(
            parent=self.frame.MainWindow,
            title=str_title,
            message=_('Enter the name of the user you want to upload to:'),
            callback=self.on_upload_directory_to_response,
            callback_data=recurse,
            droplist=users
        )

    def on_upload_directory_recursive_to(self, *_args):
        self.on_upload_directory_to(recurse=True)

    def on_copy_folder_path(self, *_args):

        if self.selected_folder is None:
            return

        copy_text(self.selected_folder)

    def on_copy_dir_url(self, *_args):

        if self.selected_folder is None:
            return

        path = self.selected_folder + '\\'
        copy_file_url(self.user, path)

    """ Key Bindings (FolderTreeView) """

    def on_folder_row_activated(self, _treeview, path, _column):

        if path is None:
            return

        # Keyboard accessibility support for <Return> key behaviour
        if self.FolderTreeView.row_expanded(path):
            expandable = self.FolderTreeView.collapse_row(path)
        else:
            expandable = self.FolderTreeView.expand_row(path, False)

        if not expandable and len(self.file_store) > 0:
            # This is the deepest level, so move focus over to Files if there are any
            self.FileTreeView.grab_focus()

        # Note: Other Folder actions are handled by setup_accelerator functions [Shift/Ctrl/Alt+Return]
        # ToDo: Mouse double-click actions will need *_args for keycode state & mods [Ctrl/Alt+DblClick]

    def on_folder_collapse_accelerator(self, *_args):
        """ Left: collapse row
            Shift+Left (Gtk) | "-" | "/" (Gtk) | """

        path, _focus_column = self.FolderTreeView.get_cursor()

        if path is None:
            return False

        self.FolderTreeView.collapse_row(path)
        return True

    def on_folder_expand_accelerator(self, *_args):
        """ Right: expand row
            Shift+Right (Gtk) | "+" (Gtk) |    """

        path, _focus_column = self.FolderTreeView.get_cursor()

        if path is None:
            return False

        expandable = self.FolderTreeView.expand_row(path, False)

        if not expandable and len(self.file_store) > 0:
            self.FileTreeView.grab_focus()

        return True

    def on_folder_collapse_sub_accelerator(self, *_args):
        """ \backslash: collapse or expand to show subs """

        path, _focus_column = self.FolderTreeView.get_cursor()

        if path is None:
            return False

        self.FolderTreeView.collapse_row(path)  # show 2nd level
        self.FolderTreeView.expand_row(path, False)
        return True

    def on_folder_expand_sub_accelerator(self, *_args):
        """ =equal: expand only (dont move focus)   """

        path, _focus_column = self.FolderTreeView.get_cursor()

        if path is None:
            return False

        self.FolderTreeView.expand_row(path, False)
        return True

    def on_folder_focus_filetree_accelerator(self, *_args):
        """ Shift+Enter: focus selection over FileTree  """

        if len(self.file_store) >= 1:
            self.FileTreeView.grab_focus()
            return True

        self.on_folder_expand_sub_accelerator()
        return True

    def on_folder_transfer_to_accelerator(self, *_args):
        """ Ctrl+Enter: Upload Folder To...
                        Download Folder Into...         """

        if self.user == config.sections["server"]["login"]:
            if len(self.file_store) >= 1:
                self.on_upload_directory_to()
            else:
                self.on_upload_directory_recursive_to()

        elif len(self.file_store) >= 1:
            self.on_download_directory_to()

        return True

    def on_folder_transfer_accelerator(self, *_args):
        """ Shift+Ctrl+Enter: Upload Folder Recursive To...
            (without prompt)  Download Folder           """

        if self.user == config.sections["server"]["login"]:
            self.on_folder_expand_sub_accelerator()
            self.on_upload_directory_recursive_to()
            return True

        if len(self.file_store) <= 0:
            # don't risk accidental recursive download
            self.on_folder_expand_sub_accelerator()
            return True

        self.on_download_directory()  # without prompt
        return True

    def on_folder_open_manager_accelerator(self, *_args):
        """ Ctrl+Alt+Enter: Open folder in File Manager... """

        if self.user != config.sections["server"]["login"]:
            return False

        self.on_file_manager()
        return True

    """ Callbacks (FileTreeView) """

    def on_column_position_changed(self, column, _param):
        """ Save column position and width to config """

        col_title = column.get_title()
        offset = column.get_x_offset()

        if self.file_column_offsets[col_title] == offset:
            return

        self.file_column_offsets[col_title] = offset
        save_columns(self.treeview_name, self.FileTreeView.get_columns())

    def on_select_file(self, selection):
        self.num_selected_files = selection.count_selected_rows()

    def on_file_popup_menu(self, menu, _widget):

        self.select_files()
        self.num_selected_files = len(self.selected_files)
        menu.set_num_selected_files(self.num_selected_files)

        self.user_popup.toggle_user_items()

    def on_download_files(self, *_args, prefix=""):

        folder = self.selected_folder
        files = self.shares.get(folder)

        if not files:
            return

        for file_data in files:
            # Find the wanted file
            if file_data[1] not in self.selected_files:
                continue

            virtualpath = "\\".join([folder, file_data[1]])
            size = file_data[2]
            h_bitrate, _bitrate, h_length, _length = get_result_bitrate_length(size, file_data[4])

            # Get the file
            self.frame.np.transfers.get_file(
                self.user, virtualpath, prefix,
                size=size, bitrate=h_bitrate, length=h_length)

    def on_download_files_to_selected(self, selected, _data):

        try:
            self.on_download_files(prefix=selected)
        except OSError:  # failed to open
            log.add('failed to open %r for reading', selected)  # notify user

    def on_download_files_to(self, *_args):

        try:
            _path_start, folder = self.selected_folder.rsplit("\\", 1)
        except ValueError:
            folder = self.selected_folder

        download_folder = config.sections["transfers"]["downloaddir"]
        path = os.path.join(download_folder, folder)

        if not os.path.exists(path) or not os.path.isdir(path):
            path = download_folder

        choose_dir(
            parent=self.frame.MainWindow,
            title=_("Select Destination Folder for File(s)"),
            callback=self.on_download_files_to_selected,
            initialdir=path,
            multichoice=False
        )

    def on_upload_files_response(self, dialog, response_id, _data):

        user = dialog.get_response_value()
        folder = self.selected_folder
        dialog.destroy()

        if response_id != Gtk.ResponseType.OK:
            return

        if not user or folder is None:
            return

        self.frame.np.userbrowse.send_upload_attempt_notification(user)

        locally_queued = False
        prefix = ""

        for basename, size in self.selected_files.items():
            self.frame.np.transfers.push_file(
                user, "\\".join([folder, basename]), size, prefix, locally_queued=locally_queued)
            locally_queued = True

    def on_upload_files(self, *_args):

        users = []

        for row in config.sections["server"]["userlist"]:
            if row and isinstance(row, list):
                user = str(row[0])
                users.append(user)

        users.sort()
        entry_dialog(
            parent=self.frame.MainWindow,
            title=_('Upload File(s) To User'),
            message=_('Enter the name of the user you want to upload to:'),
            callback=self.on_upload_files_response,
            droplist=users
        )

    def on_play_files(self, *_args):

        path = self.frame.np.shares.virtual2real(self.selected_folder)

        for basename in self.selected_files:
            playfile = os.sep.join([path, basename])

            if os.path.exists(playfile):
                command = config.sections["players"]["default"]
                open_file_path(playfile, command)

    def on_file_manager(self, *_args):

        if self.selected_folder is None:
            return

        path = self.frame.np.shares.virtual2real(self.selected_folder)
        command = config.sections["ui"]["filemanager"]

        open_file_path(path, command)

    def on_file_properties(self, *_args):

        data = []
        model, paths = self.FileTreeView.get_selection().get_selected_rows()

        for path in paths:
            iterator = model.get_iter(path)
            filename = model.get_value(iterator, 0)
            virtual_path = "\\".join([self.selected_folder, filename])
            size = model.get_value(iterator, 1)
            bitratestr = model.get_value(iterator, 2)
            length = model.get_value(iterator, 3)

            data.append({
                "user": self.user,
                "fn": virtual_path,
                "filename": filename,
                "directory": self.selected_folder,
                "size": size,
                "bitrate": bitratestr,
                "length": length
            })

        if data:
            FileProperties(self.frame, data).show()

    def on_copy_file_path(self, *_args):

        if self.selected_folder is None or not self.selected_files:
            return

        text = "\\".join([self.selected_folder, next(iter(self.selected_files))])
        copy_text(text)

    def on_copy_url(self, *_args):

        if not self.selected_files:
            return

        path = "\\".join([self.selected_folder, next(iter(self.selected_files))])
        copy_file_url(self.user, path)

    """ Key Bindings (FileTreeView) """

    def on_file_row_activated(self, _treeview, _path, _column):

        self.select_files()

        if self.user == config.sections["server"]["login"]:
            self.on_play_files()
        else:
            self.on_download_files()

    def on_focus_folder_left_accelerator(self, *_args):
        """ Left: focus back parent folder (left arrow) """

        if self.FileScrolledWindow.get_hadjustment().get_value() > 0.0:
            return False  # allow horizontal scrolling

        self.FolderTreeView.grab_focus()
        return True

    def on_focus_folder_accelerator(self, *_args):
        """ Shift+Tab: focus selection back parent folder
            BackSpace | \backslash |                  """

        self.FolderTreeView.grab_focus()
        return True

    def on_file_transfer_to_accelerator(self, *_args):
        """ Ctrl+Enter: Upload File(s) To...
                        Download File(s) Into...  """

        if len(self.file_store) <= 0:  # avoid navigation trap
            self.FolderTreeView.grab_focus()
            return True

        if self.num_selected_files <= 0:  # do folder instead
            self.on_folder_transfer_to_accelerator()
            return True

        self.select_files()

        if self.user == config.sections["server"]["login"]:
            self.on_upload_files()
            return True

        self.on_download_files_to()  # (with prompt, Single or Multi-selection)
        return True

    def on_file_transfer_accelerator(self, *_args):
        """ Shift+Ctrl+Enter: Upload File(s) To...
            (without prompt)  Download File(s) """

        if len(self.file_store) <= 0:
            self.FolderTreeView.grab_focus()  # avoid nav trap
            return True

        self.select_files()

        if self.user == config.sections["server"]["login"]:
            if self.num_selected_files >= 1:
                self.on_upload_files()

            elif self.num_selected_files <= 0:
                self.on_upload_directory_to()

        else:  # [user is not self]
            if self.num_selected_files >= 1:
                self.on_download_files()  # (no prompt, Single or Multi-selection)

            elif self.num_selected_files <= 0:
                self.on_download_directory()  # (without prompt, No-selection=All)

        return True

    def on_file_transfer_multi_accelerator(self, *_args):
        """ Shift+Enter: Send to Player (multiple files)
                         Download Files (multiple)   """

        if len(self.file_store) <= 0:
            self.FolderTreeView.grab_focus()  # avoid nav trap
            return True

        self.select_files()  # support multi-select with Up/Dn keys

        if self.user == config.sections["server"]["login"]:
            self.on_play_files()
        else:
            self.on_download_files()

        return True

    def on_file_open_manager_accelerator(self, *_args):
        """ Ctrl+Alt+Enter: Open in File Manager """

        if self.user == config.sections["server"]["login"]:
            self.on_file_manager()

        else:  # [user is not self]
            self.on_file_properties_accelerator()  # same as Alt+Enter

        return True

    def on_file_properties_accelerator(self, *_args):
        """ Alt+Enter: show file properties dialog """

        if len(self.file_store) <= 0:
            self.FolderTreeView.grab_focus()  # avoid nav trap

        if self.num_selected_files >= 1:
            self.on_file_properties()

        return True

    """ Callbacks (General) """

    @staticmethod
    def on_tooltip(widget, pos_x, pos_y, _keyboard_mode, tooltip):

        file_path_tooltip = show_file_path_tooltip(widget, pos_x, pos_y, tooltip, 0)

        if file_path_tooltip:
            return file_path_tooltip

        return False

    def on_expand(self, *_args):

        if self.ExpandButton.get_active():
            self.FolderTreeView.expand_all()
            self.expand.set_property("icon-name", "go-up-symbolic")
        else:
            self.FolderTreeView.collapse_all()
            self.expand.set_property("icon-name", "go-down-symbolic")

    def on_tab_popup(self, *_args):
        self.user_popup.toggle_user_items()

    def on_search(self, *_args):
        self.find_search_matches()

    def on_save(self, *_args):
        self.frame.np.userbrowse.save_shares_list_to_disk(self.user, list(self.shares.items()))

    def on_refresh(self, *_args):

        self.clear_model()
        self.FolderTreeView.grab_focus()
        self.info_bar.set_visible(False)

        self.set_in_progress(self.indeterminate_progress)
        self.frame.np.userbrowse.browse_user(self.user, local_shares_type=self.local_shares_type, new_request=True)

    def on_close(self, *_args):

        del self.userbrowses.pages[self.user]
        self.frame.np.userbrowse.remove_user(self.user)
        self.userbrowses.remove_page(self.Main)

        if self.userbrowses.get_n_pages() == 0:
            self.frame.userbrowse_status_page.show()

    def on_close_all_tabs(self, *_args):
        self.userbrowses.remove_all_pages()

    """ Key Bindings (General) """

    def on_expand_accelerator(self, *_args):
        """ Ctrl+\backslash: Expand / Collapse All """

        self.ExpandButton.set_active(not self.ExpandButton.get_active())
        return True

    def on_save_accelerator(self, *_args):
        """ Ctrl+S: Save Shares List """

        self.on_save()
        return True

    def on_refresh_accelerator(self, *_args):
        """ Ctrl+R or F5: Refresh """

        self.on_refresh()
        return True

    def on_search_accelerator(self, *_args):
        """ Ctrl+F: Find """

        self.SearchEntry.grab_focus()
        return True

    def on_search_next_accelerator(self, *_args):
        """ Ctrl+G or F3: Find Next """

        if not self.find_search_matches():
            self.SearchEntry.grab_focus()

        return True

    def on_search_previous_accelerator(self, *_args):
        """ Shift+Ctrl+G or Shift+F3: Find Previous """

        if not self.find_search_matches(reverse=True):
            self.SearchEntry.grab_focus()

        return True

    def on_search_escape_accelerator(self, *_args):
        """ Escape: navigate out of SearchEntry """

        if self.num_selected_files >= 1:
            self.FileTreeView.grab_focus()
        else:
            self.FolderTreeView.grab_focus()

        return True
