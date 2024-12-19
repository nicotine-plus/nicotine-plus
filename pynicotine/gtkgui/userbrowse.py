# COPYRIGHT (C) 2020-2024 Nicotine+ Contributors
# COPYRIGHT (C) 2016-2017 Michael Labouebe <gfarmerfr@free.fr>
# COPYRIGHT (C) 2013 SeeSchloss <see@seos.fr>
# COPYRIGHT (C) 2009-2010 quinox <quinox@users.sf.net>
# COPYRIGHT (C) 2006-2009 daelstorm <daelstorm@gmail.com>
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
from gi.repository import Pango

from pynicotine.config import config
from pynicotine.core import core
from pynicotine.events import events
from pynicotine.gtkgui.application import GTK_API_VERSION
from pynicotine.gtkgui.dialogs.fileproperties import FileProperties
from pynicotine.gtkgui.widgets import clipboard
from pynicotine.gtkgui.widgets import ui
from pynicotine.gtkgui.widgets.accelerator import Accelerator
from pynicotine.gtkgui.widgets.combobox import ComboBox
from pynicotine.gtkgui.widgets.dialogs import EntryDialog
from pynicotine.gtkgui.widgets.filechooser import FolderChooser
from pynicotine.gtkgui.widgets.iconnotebook import IconNotebook
from pynicotine.gtkgui.widgets.infobar import InfoBar
from pynicotine.gtkgui.widgets.popupmenu import PopupMenu
from pynicotine.gtkgui.widgets.popupmenu import FilePopupMenu
from pynicotine.gtkgui.widgets.popupmenu import UserPopupMenu
from pynicotine.gtkgui.widgets.theme import add_css_class
from pynicotine.gtkgui.widgets.theme import get_file_type_icon_name
from pynicotine.gtkgui.widgets.theme import remove_css_class
from pynicotine.gtkgui.widgets.treeview import TreeView
from pynicotine.slskmessages import ConnectionType
from pynicotine.slskmessages import FileListMessage
from pynicotine.slskmessages import UserStatus
from pynicotine.utils import human_size
from pynicotine.utils import humanize
from pynicotine.utils import open_file_path
from pynicotine.utils import open_folder_path


class UserBrowses(IconNotebook):

    def __init__(self, window):

        super().__init__(
            window,
            parent=window.userbrowse_content,
            parent_page=window.userbrowse_page
        )

        self.page = window.userbrowse_page
        self.page.id = "userbrowse"
        self.toolbar = window.userbrowse_toolbar
        self.toolbar_start_content = window.userbrowse_title
        self.toolbar_end_content = window.userbrowse_end
        self.toolbar_default_widget = window.userbrowse_entry

        self.file_properties = None

        self.userbrowse_combobox = ComboBox(
            container=self.window.userbrowse_title, has_entry=True, has_entry_completion=True,
            entry=self.window.userbrowse_entry, item_selected_callback=self.on_get_shares
        )

        # Events
        for event_name, callback in (
            ("peer-connection-closed", self.peer_connection_error),
            ("peer-connection-error", self.peer_connection_error),
            ("quit", self.quit),
            ("server-disconnect", self.server_disconnect),
            ("shared-file-list-progress", self.shared_file_list_progress),
            ("shared-file-list-response", self.shared_file_list),
            ("user-browse-remove-user", self.remove_user),
            ("user-browse-show-user", self.show_user),
            ("user-status", self.user_status)
        ):
            events.connect(event_name, callback)

    def quit(self):
        self.freeze()

    def destroy(self):

        self.userbrowse_combobox.destroy()

        if self.file_properties is not None:
            self.file_properties.destroy()

        super().destroy()

    def on_focus(self, *_args):

        if self.window.current_page_id != self.window.userbrowse_page.id:
            return True

        if self.get_n_pages():
            return True

        if self.window.userbrowse_entry.is_sensitive():
            self.window.userbrowse_entry.grab_focus()
            return True

        return False

    def on_remove_all_pages(self, *_args):
        core.userbrowse.remove_all_users()

    def on_restore_removed_page(self, page_args):
        username, = page_args
        core.userbrowse.browse_user(username)

    def on_get_shares(self, *_args):

        entry_text = self.window.userbrowse_entry.get_text().strip()

        if not entry_text:
            return

        self.window.userbrowse_entry.set_text("")

        if entry_text.startswith("slsk://"):
            core.userbrowse.open_soulseek_url(entry_text)
        else:
            core.userbrowse.browse_user(entry_text)

    def show_user(self, user, path=None, switch_page=True):

        page = self.pages.get(user)

        if page is None:
            self.pages[user] = page = UserBrowse(self, user)

            self.append_page(page.container, user, focus_callback=page.on_focus,
                             close_callback=page.on_close, user=user)
            page.set_label(self.get_tab_label_inner(page.container))

        page.queued_path = path
        page.browse_queued_path()

        if switch_page:
            self.set_current_page(page.container)
            self.window.change_main_page(self.window.userbrowse_page)

    def remove_user(self, user):

        page = self.pages.get(user)

        if page is None:
            return

        page.clear()
        self.remove_page(page.container, page_args=(user,))
        del self.pages[user]
        page.destroy()

    def peer_connection_error(self, username, conn_type, **_unused):

        page = self.pages.get(username)

        if page is None:
            return

        if conn_type == ConnectionType.PEER:
            page.peer_connection_error()

    def user_status(self, msg):

        page = self.pages.get(msg.user)

        if page is not None:
            self.set_user_status(page.container, msg.user, msg.status)

    def shared_file_list_progress(self, user, _sock, position, total):

        page = self.pages.get(user)

        if page is not None:
            page.shared_file_list_progress(position, total)

    def shared_file_list(self, msg):

        page = self.pages.get(msg.username)

        if page is not None:
            page.shared_file_list(msg)

    def server_disconnect(self, *_args):
        for user, page in self.pages.items():
            self.set_user_status(page.container, user, UserStatus.OFFLINE)


class UserBrowse:

    def __init__(self, userbrowses, user):

        (
            self.container,
            self.expand_button,
            self.expand_icon,
            self.file_list_container,
            self.folder_tree_container,
            self.info_bar_container,
            self.num_folders_label,
            self.path_bar,
            self.path_bar_container,
            self.progress_bar,
            self.refresh_button,
            self.retry_button,
            self.save_button,
            self.search_button,
            self.search_entry,
            self.search_entry_revealer,
            self.share_size_label
        ) = ui.load(scope=self, path="userbrowse.ui")

        self.userbrowses = userbrowses
        self.window = userbrowses.window
        self.user = user
        self.indeterminate_progress = False
        self.local_permission_level = None
        self.queued_path = None

        self.active_folder_path = None
        self.selected_files = {}

        self.search_folder_paths = []
        self.query = None
        self.search_position = 0

        self.info_bar = InfoBar(parent=self.info_bar_container, button=self.retry_button)
        self.path_bar_container.get_hadjustment().connect("changed", self.on_path_bar_scroll)

        # Setup folder_tree_view
        self.folder_tree_view = TreeView(
            self.window, parent=self.folder_tree_container, has_tree=True,
            multi_select=True, activate_row_callback=self.on_folder_row_activated,
            select_row_callback=self.on_select_folder,
            columns={
                # Visible columns
                "folder": {
                    "column_type": "text",
                    "title": _("Folder"),
                    "hide_header": True,
                    "tooltip_callback": self.on_folder_path_tooltip
                },

                # Hidden data columns
                "folder_path_data": {"iterator_key": True}
            }
        )

        # Popup Menu (folder_tree_view)
        self.user_popup_menu = UserPopupMenu(
            self.window.application, callback=self.on_tab_popup, username=user, tab_name="userbrowse"
        )
        self.user_popup_menu.add_items(
            ("", None),
            ("#" + _("_Save Shares List to Disk"), self.on_save),
            ("#" + _("Close All Tabs…"), self.on_close_all_tabs),
            ("#" + _("_Close Tab"), self.on_close)
        )

        self.folder_popup_menu = PopupMenu(self.window.application, self.folder_tree_view.widget,
                                           self.on_folder_popup_menu)

        if user == config.sections["server"]["login"]:
            self.folder_popup_menu.add_items(
                ("#" + _("Upload Folder & Subfolders…"), self.on_upload_folder_recursive_to),
                ("", None)
            )
            if not self.window.application.isolated_mode:
                self.folder_popup_menu.add_items(
                    ("#" + _("Open in File _Manager"), self.on_file_manager)
                )
            self.folder_popup_menu.add_items(
                ("#" + _("F_ile Properties"), self.on_file_properties, True),
                ("", None),
                ("#" + _("Copy _Folder Path"), self.on_copy_folder_path),
                ("#" + _("Copy Folder U_RL"), self.on_copy_folder_url),
                ("", None),
                (">" + _("User Actions"), self.user_popup_menu)
            )
        else:
            self.folder_popup_menu.add_items(
                ("#" + _("_Download Folder & Subfolders"), self.on_download_folder_recursive),
                ("#" + _("Download Folder & Subfolders _To…"), self.on_download_folder_recursive_to),
                ("", None),
                ("#" + _("F_ile Properties"), self.on_file_properties, True),
                ("", None),
                ("#" + _("Copy _Folder Path"), self.on_copy_folder_path),
                ("#" + _("Copy Folder U_RL"), self.on_copy_folder_url),
                ("", None),
                (">" + _("User Actions"), self.user_popup_menu)
            )

        # Setup file_list_view
        self.file_list_view = TreeView(
            self.window, parent=self.file_list_container, name="user_browse",
            multi_select=True, activate_row_callback=self.on_file_row_activated,
            columns={
                # Visible columns
                "file_type": {
                    "column_type": "icon",
                    "title": _("File Type"),
                    "width": 30,
                    "hide_header": True
                },
                "filename": {
                    "column_type": "text",
                    "title": _("File Name"),
                    "width": 150,
                    "expand_column": True,
                    "default_sort_type": "ascending",
                    "iterator_key": True
                },
                "size": {
                    "column_type": "number",
                    "title": _("Size"),
                    "width": 100,
                    "sort_column": "size_data"
                },
                "quality": {
                    "column_type": "number",
                    "title": _("Quality"),
                    "width": 150,
                    "sort_column": "bitrate_data"
                },
                "length": {
                    "column_type": "number",
                    "title": _("Duration"),
                    "width": 100,
                    "sort_column": "length_data"
                },

                # Hidden data columns
                "size_data": {"data_type": GObject.TYPE_UINT64},
                "bitrate_data": {"data_type": GObject.TYPE_UINT},
                "length_data": {"data_type": GObject.TYPE_UINT},
                "file_attributes_data": {"data_type": GObject.TYPE_PYOBJECT}
            }
        )

        # Popup Menu (file_list_view)
        self.file_popup_menu = FilePopupMenu(
            self.window.application, parent=self.file_list_view.widget, callback=self.on_file_popup_menu
        )
        if user == config.sections["server"]["login"]:
            self.file_popup_menu.add_items(
                ("#" + _("Up_load File(s)…"), self.on_upload_files_to),
                ("#" + _("Upload Folder…"), self.on_upload_folder_to),
                ("", None)
            )
            if not self.window.application.isolated_mode:
                self.file_popup_menu.add_items(
                    ("#" + _("_Open File"), self.on_open_file),
                    ("#" + _("Open in File _Manager"), self.on_file_manager)
                )
            self.file_popup_menu.add_items(
                ("#" + _("F_ile Properties"), self.on_file_properties),
                ("", None),
                ("#" + _("Copy _File Path"), self.on_copy_file_path),
                ("#" + _("Copy _URL"), self.on_copy_url),
                ("", None),
                (">" + _("User Actions"), self.user_popup_menu)
            )
        else:
            self.file_popup_menu.add_items(
                ("#" + _("_Download File(s)"), self.on_download_files),
                ("#" + _("Download File(s) _To…"), self.on_download_files_to),
                ("", None),
                ("#" + _("_Download Folder"), self.on_download_folder),
                ("#" + _("Download Folder _To…"), self.on_download_folder_to),
                ("", None),
                ("#" + _("F_ile Properties"), self.on_file_properties),
                ("", None),
                ("#" + _("Copy _File Path"), self.on_copy_file_path),
                ("#" + _("Copy _URL"), self.on_copy_url),
                ("", None),
                (">" + _("User Actions"), self.user_popup_menu)
            )

        # Key Bindings (folder_tree_view)
        Accelerator("Right", self.folder_tree_view.widget, self.on_folder_expand_accelerator)

        Accelerator("<Shift>Return", self.folder_tree_view.widget, self.on_folder_focus_filetree_accelerator)
        Accelerator("<Primary>Return", self.folder_tree_view.widget, self.on_folder_transfer_to_accelerator)
        Accelerator("<Shift><Primary>Return", self.folder_tree_view.widget, self.on_folder_transfer_accelerator)
        Accelerator("<Primary><Alt>Return", self.folder_tree_view.widget, self.on_folder_open_manager_accelerator)
        Accelerator("<Alt>Return", self.folder_tree_view.widget, self.on_file_properties_accelerator, True)

        # Key Bindings (file_list_view)
        for accelerator in ("BackSpace", "backslash"):  # Navigate up, "\"
            Accelerator(accelerator, self.file_list_view.widget, self.on_focus_folder_accelerator)

        Accelerator("Left", self.file_list_view.widget, self.on_focus_folder_left_accelerator)

        Accelerator("<Shift>Return", self.file_list_view.widget, self.on_file_transfer_multi_accelerator)
        Accelerator("<Primary>Return", self.file_list_view.widget, self.on_file_transfer_to_accelerator)
        Accelerator("<Shift><Primary>Return", self.file_list_view.widget, self.on_file_transfer_accelerator)
        Accelerator("<Primary><Alt>Return", self.file_list_view.widget, self.on_file_open_manager_accelerator)
        Accelerator("<Alt>Return", self.file_list_view.widget, self.on_file_properties_accelerator)

        # Key Bindings (General)
        for widget in (self.container, self.folder_tree_view.widget, self.file_list_view.widget):
            Accelerator("<Primary>f", widget, self.on_search_accelerator)  # Find focus

        Accelerator("Escape", self.search_entry, self.on_search_escape_accelerator)
        Accelerator("F3", self.container, self.on_search_next_accelerator)
        Accelerator("<Shift>F3", self.container, self.on_search_previous_accelerator)
        Accelerator("<Primary>g", self.container, self.on_search_next_accelerator)  # Next search match
        Accelerator("<Shift><Primary>g", self.container, self.on_search_previous_accelerator)
        Accelerator("Up", self.search_entry, self.on_search_previous_accelerator)
        Accelerator("Down", self.search_entry, self.on_search_next_accelerator)

        Accelerator("<Primary>backslash", self.container, self.on_expand_accelerator)  # expand / collapse all (button)
        Accelerator("F5", self.container, self.on_refresh_accelerator)
        Accelerator("<Primary>r", self.container, self.on_refresh_accelerator)  # Refresh
        Accelerator("<Primary>s", self.container, self.on_save_accelerator)  # Save Shares List

        self.popup_menus = (
            self.folder_popup_menu, self.file_popup_menu, self.user_popup_menu
        )

        self.expand_button.set_active(config.sections["userbrowse"]["expand_folders"])

    def clear(self):
        self.clear_model()

    def destroy(self):

        for menu in self.popup_menus:
            menu.destroy()

        self.info_bar.destroy()
        self.folder_tree_view.destroy()
        self.file_list_view.destroy()
        self.__dict__.clear()

        self.indeterminate_progress = False  # Stop progress bar timer

    def set_label(self, label):
        self.user_popup_menu.set_parent(label)

    # Folder/File Views #

    def clear_model(self):

        self.search_position = 0
        self.search_folder_paths.clear()

        self.active_folder_path = None
        self.populate_path_bar()
        self.selected_files.clear()

        self.folder_tree_view.clear()
        self.file_list_view.clear()

    def rebuild_model(self):

        self.clear_model()
        browsed_user = core.userbrowse.users[self.user]

        if browsed_user.num_folders is None or browsed_user.shared_size is None:
            return

        # Generate the folder tree and select first folder
        self.create_folder_tree(browsed_user.public_folders)

        if browsed_user.private_folders:
            self.create_folder_tree(browsed_user.private_folders, private=True)

        self.num_folders_label.set_text(humanize(browsed_user.num_folders))
        self.share_size_label.set_text(human_size(browsed_user.shared_size))

        if self.expand_button.get_active():
            self.folder_tree_view.expand_all_rows()
        else:
            self.folder_tree_view.expand_root_rows()

        self.select_search_match_folder()

    def create_folder_tree(self, folders, private=False):

        if not folders:
            return

        iterators = self.folder_tree_view.iterators
        add_row = self.folder_tree_view.add_row
        query = self.query
        private_template = _("[PRIVATE]  %s")

        for folder_path, files in reversed(list(folders.items())):
            current_path = parent = None
            root_processed = False
            skip_folder = (query and query not in folder_path.lower())

            if skip_folder:
                for file_info in files:
                    if query in file_info[1].lower():
                        skip_folder = False

            if skip_folder:
                continue

            for subfolder in folder_path.split("\\"):
                if not root_processed:
                    current_path = subfolder
                    root_processed = True
                else:
                    current_path += f"\\{subfolder}"

                if current_path in iterators:
                    # Folder was already added to tree
                    parent = iterators[current_path]
                    continue

                if not subfolder:
                    # Most likely a root folder
                    subfolder = "\\"

                if private:
                    subfolder = private_template % subfolder

                parent = add_row(
                    [subfolder, current_path], select_row=False, parent_iterator=parent
                )

            if query:
                self.search_folder_paths.append(folder_path)

        self.search_folder_paths.reverse()

    def browse_queued_path(self):

        if not self.queued_path:
            return

        # Reset search to show all folders
        self.search_entry.set_text("")
        self.search_button.set_active(False)

        folder_path, _separator, basename = self.queued_path.rpartition("\\")
        iterator = self.folder_tree_view.iterators.get(folder_path)

        if not iterator:
            return

        self.queued_path = None

        # Scroll to the requested folder
        self.folder_tree_view.select_row(iterator)

        iterator = self.file_list_view.iterators.get(basename)

        if not iterator:
            self.folder_tree_view.grab_focus()
            return

        # Scroll to the requested file
        self.file_list_view.select_row(iterator)
        self.file_list_view.grab_focus()

    def shared_file_list(self, msg):

        is_empty = (not msg.list and not msg.privatelist)
        self.local_permission_level = msg.permission_level

        self.rebuild_model()
        self.info_bar.set_visible(False)

        if is_empty:
            self.info_bar.show_info_message(
                _("User's list of shared files is empty. Either the user is not sharing anything, "
                  "or they are sharing files privately.")
            )
            self.retry_button.set_visible(False)
        else:
            self.browse_queued_path()

        self.set_finished()

    def peer_connection_error(self):

        if self.refresh_button.get_sensitive():
            return

        self.info_bar.show_error_message(
            _("Unable to request shared files from user. Either the user is offline, the listening ports "
              "are closed on both sides, or there is a temporary connectivity issue.")
        )
        self.retry_button.set_visible(True)
        self.set_finished()

    def pulse_progress(self, repeat=True):

        if not self.indeterminate_progress:
            return False

        self.progress_bar.pulse()
        return repeat

    def shared_file_list_progress(self, position, total):

        self.indeterminate_progress = False

        if total <= 0 or position <= 0:
            fraction = 0.0

        elif position < total:
            fraction = float(position) / total

        else:
            fraction = 1.0
            GLib.timeout_add(1000, self.set_finishing)

        self.progress_bar.set_fraction(fraction)

    def set_indeterminate_progress(self):

        self.indeterminate_progress = True

        self.progress_bar.get_parent().set_reveal_child(True)
        self.progress_bar.pulse()
        GLib.timeout_add(320, self.pulse_progress, False)
        GLib.timeout_add(1000, self.pulse_progress)

        self.info_bar.set_visible(False)

        self.refresh_button.set_sensitive(False)
        self.save_button.set_sensitive(False)

    def set_finishing(self):

        if hasattr(self, "refresh_button") and not self.refresh_button.get_sensitive():
            self.set_indeterminate_progress()

        return False

    def set_finished(self):

        self.indeterminate_progress = False

        self.userbrowses.request_tab_changed(self.container)
        self.progress_bar.set_fraction(1.0)
        self.progress_bar.get_parent().set_reveal_child(False)

        self.refresh_button.set_sensitive(True)
        self.save_button.set_sensitive(not self.folder_tree_view.is_empty())

    def populate_path_bar(self, folder_path=""):

        for widget in list(self.path_bar):
            self.path_bar.remove(widget)

        if not folder_path:
            return

        folder_path_split = folder_path.split("\\")

        for index, folder in enumerate(folder_path_split):
            i_folder_path = "\\".join(folder_path_split[:index + 1])

            if index:
                label = Gtk.Label(label="\\", visible=True)

                add_css_class(label, "dim-label")
                add_css_class(label, "heading")

                if GTK_API_VERSION >= 4:
                    self.path_bar.append(label)  # pylint: disable=no-member
                else:
                    self.path_bar.add(label)     # pylint: disable=no-member

            if len(folder) > 10:
                width_chars = 10
                ellipsize = Pango.EllipsizeMode.END
            else:
                width_chars = -1
                ellipsize = Pango.EllipsizeMode.NONE

            button_label = Gtk.Label(label=folder, ellipsize=ellipsize, width_chars=width_chars, visible=True)

            if index == len(folder_path_split) - 1:
                button = Gtk.MenuButton(visible=True)
                self.folder_popup_menu.set_menu_button(button)
                add_css_class(button_label, "heading")

                if GTK_API_VERSION >= 4:
                    button.set_child(button_label)                              # pylint: disable=no-member
                    button.set_always_show_arrow(True)                          # pylint: disable=no-member
                    button.set_has_frame(False)                                 # pylint: disable=no-member
                    button.set_create_popup_func(self.on_folder_popup_menu)     # pylint: disable=no-member

                    inner_button = next(iter(button))
                    button_label.set_mnemonic_widget(inner_button)
                else:
                    box = Gtk.Box(spacing=6, visible=True)
                    arrow_icon = Gtk.Image(icon_name="pan-down-symbolic", visible=True)
                    box.add(button_label)                                       # pylint: disable=no-member
                    box.add(arrow_icon)                                         # pylint: disable=no-member

                    button.add(box)                                             # pylint: disable=no-member
                    button.connect("clicked", self.on_folder_popup_menu)

                    button_label.set_mnemonic_widget(button)
            else:
                button = Gtk.Button(child=button_label, visible=True)
                button.connect("clicked", self.on_path_bar_clicked, i_folder_path)
                add_css_class(button_label, "normal")

                button_label.set_mnemonic_widget(button)

            add_css_class(button, "flat")
            remove_css_class(button, "text-button")

            if GTK_API_VERSION >= 4:
                self.path_bar.append(button)  # pylint: disable=no-member
            else:
                self.path_bar.add(button)     # pylint: disable=no-member

    def set_active_folder(self, folder_path):

        if self.active_folder_path == folder_path:
            return

        browsed_user = core.userbrowse.users.get(self.user)

        if browsed_user is None:
            # Redundant row selection event when closing tab, prevent crash
            return

        self.populate_path_bar(folder_path)
        self.file_list_view.clear()

        self.active_folder_path = folder_path

        if not folder_path:
            return

        files = browsed_user.public_folders.get(folder_path)

        if not files:
            files = browsed_user.private_folders.get(folder_path)

            if not files:
                return

        # Temporarily disable sorting for increased performance
        self.file_list_view.freeze()

        for _code, basename, size, _ext, file_attributes, *_unused in files:
            h_size = human_size(size, config.sections["ui"]["file_size_unit"])
            h_quality, bitrate, h_length, length = FileListMessage.parse_audio_quality_length(size, file_attributes)

            self.file_list_view.add_row([
                get_file_type_icon_name(basename),
                basename,
                h_size,
                h_quality,
                h_length,
                size,
                bitrate,
                length,
                file_attributes
            ], select_row=False)

        self.file_list_view.unfreeze()
        self.select_search_match_files()

    def select_files(self):

        self.selected_files.clear()

        for iterator in self.file_list_view.get_selected_rows():
            basename = self.file_list_view.get_row_value(iterator, "filename")
            filesize = self.file_list_view.get_row_value(iterator, "size_data")

            self.selected_files[basename] = filesize

    def get_selected_folder_path(self):

        for iterator in self.folder_tree_view.get_selected_rows():
            folder_path = self.folder_tree_view.get_row_value(iterator, "folder_path_data")
            return f'{folder_path or ""}\\'

        return None

    def get_selected_file_path(self):
        selected_folder = self.get_selected_folder_path()
        selected_file = next(iter(self.selected_files), "")
        return f"{selected_folder}{selected_file}"

    # Search #

    def select_search_match_folder(self):

        iterator = None

        if self.search_folder_paths:
            folder_path = self.search_folder_paths[self.search_position]
            iterator = self.folder_tree_view.iterators[folder_path]

        self.folder_tree_view.select_row(iterator)

    def select_search_match_files(self):

        if not self.query:
            return

        result_files = []
        found_first_match = False

        for filepath, iterator in self.file_list_view.iterators.items():
            if self.query in filepath.lower():
                result_files.append(iterator)

        self.file_list_view.unselect_all_rows()

        for iterator in result_files:
            # Select each matching file in folder
            self.file_list_view.select_row(iterator, should_scroll=(not found_first_match))
            found_first_match = True

    def find_search_matches(self, reverse=False):

        query = self.search_entry.get_text().lower() or None

        if self.query != query:
            # New search query, rebuild result list
            active_folder_path = self.active_folder_path

            self.query = query
            self.rebuild_model()

            if not self.search_folder_paths:
                iterator = self.folder_tree_view.iterators.get(active_folder_path)

                if iterator:
                    self.folder_tree_view.select_row(iterator)

                return False

        elif query:
            # Increment/decrement search position
            self.search_position += -1 if reverse else 1

        else:
            return False

        if self.search_position < 0:
            self.search_position = len(self.search_folder_paths) - 1

        elif self.search_position >= len(self.search_folder_paths):
            self.search_position = 0

        # Set active folder
        self.select_search_match_folder()

        # Get matching files in the current folder
        self.select_search_match_files()
        return True

    # Callbacks (folder_tree_view) #

    def on_select_folder(self, tree_view, iterator):

        if iterator is None:
            return

        selected_iterators = tree_view.get_selected_rows()
        folder_path = None

        # Skip first folder
        next(selected_iterators)

        if next(selected_iterators, None):
            # Multiple folders selected. Avoid any confusion by clearing the path bar and file list view.
            folder_path = None
        else:
            folder_path = tree_view.get_row_value(iterator, "folder_path_data")

        self.set_active_folder(folder_path)

    def on_folder_path_tooltip(self, treeview, iterator):
        return treeview.get_row_value(iterator, "folder_path_data")

    def on_folder_popup_menu(self, *_args):
        self.folder_popup_menu.update_model()
        self.user_popup_menu.toggle_user_items()

    def on_download_folder(self, *_args, download_folder_path=None, recurse=False):

        prev_folder_path = None

        for iterator in self.folder_tree_view.get_selected_rows():
            folder_path = self.folder_tree_view.get_row_value(iterator, "folder_path_data")

            if recurse and prev_folder_path and prev_folder_path in folder_path:
                # Already recursing, avoid redundant request for subfolder
                continue

            core.userbrowse.download_folder(
                self.user, folder_path, download_folder_path=download_folder_path, recurse=recurse)

            prev_folder_path = folder_path

    def on_download_folder_recursive(self, *_args):
        self.on_download_folder(recurse=True)

    def on_download_folder_to_selected(self, selected_download_folder_paths, recurse):
        self.on_download_folder(
            download_folder_path=next(iter(selected_download_folder_paths), None), recurse=recurse)

    def on_download_folder_to(self, *_args, recurse=False):

        if recurse:
            str_title = _("Select Destination for Downloading Multiple Folders")
        else:
            str_title = _("Select Destination Folder")

        FolderChooser(
            parent=self.window,
            title=str_title,
            callback=self.on_download_folder_to_selected,
            callback_data=recurse,
            initial_folder=core.downloads.get_default_download_folder()
        ).present()

    def on_download_folder_recursive_to(self, *_args):
        self.on_download_folder_to(recurse=True)

    def on_upload_folder_to_response(self, dialog, _response_id, recurse):

        user = dialog.get_entry_value()

        if not user:
            return

        prev_folder_path = None
        sent_upload_notification = False

        for iterator in self.folder_tree_view.get_selected_rows():
            folder_path = self.folder_tree_view.get_row_value(iterator, "folder_path_data")

            if recurse and prev_folder_path and prev_folder_path in folder_path:
                # Already recursing, avoid redundant request for subfolder
                continue

            if not sent_upload_notification:
                core.userbrowse.send_upload_attempt_notification(user)
                sent_upload_notification = True

            core.userbrowse.upload_folder(
                user, folder_path, local_browsed_user=core.userbrowse.users[self.user], recurse=recurse)

            prev_folder_path = folder_path

    def on_upload_folder_to(self, *_args, recurse=False):

        if recurse:
            str_title = _("Upload Folder (with Subfolders) To User")
        else:
            str_title = _("Upload Folder To User")

        EntryDialog(
            parent=self.window,
            title=str_title,
            message=_("Enter the name of the user you want to upload to:"),
            action_button_label=_("_Upload"),
            callback=self.on_upload_folder_to_response,
            callback_data=recurse,
            droplist=sorted(core.buddies.users)
        ).present()

    def on_upload_folder_recursive_to(self, *_args):
        self.on_upload_folder_to(recurse=True)

    def on_copy_folder_path(self, *_args):
        folder_path = self.get_selected_folder_path()
        clipboard.copy_text(folder_path)

    def on_copy_folder_url(self, *_args):
        folder_path = self.get_selected_folder_path()
        folder_url = core.userbrowse.get_soulseek_url(self.user, folder_path)
        clipboard.copy_text(folder_url)

    # Key Bindings (folder_tree_view) #

    def on_folder_row_activated(self, tree_view, iterator, _column_id):

        if iterator is None:
            return

        # Keyboard accessibility support for <Return> key behaviour
        if tree_view.is_row_expanded(iterator):
            expandable = tree_view.collapse_row(iterator)
        else:
            expandable = tree_view.expand_row(iterator)

        if not expandable and not self.file_list_view.is_empty():
            # This is the deepest level, so move focus over to Files if there are any
            self.file_list_view.grab_focus()

        # Note: Other Folder actions are handled by Accelerator functions [Shift/Ctrl/Alt+Return]
        # TODO: Mouse double-click actions will need keycode state & mods [Shift/Ctrl+DblClick]

    def on_folder_expand_accelerator(self, *_args):
        """Right, Shift+Right (Gtk), "+" (Gtk) - expand row."""

        iterator = self.folder_tree_view.get_focused_row()

        if iterator is None:
            return False

        if not self.file_list_view.is_empty():
            self.file_list_view.grab_focus()

        return True

    def on_folder_focus_filetree_accelerator(self, *_args):
        """Shift+Enter - focus selection over FileTree."""

        if not self.file_list_view.is_empty():
            self.file_list_view.grab_focus()
            return True

        iterator = self.folder_tree_view.get_focused_row()

        if iterator is None:
            return False

        self.folder_tree_view.expand_row(iterator)
        return True

    def on_folder_transfer_to_accelerator(self, *_args):
        """Ctrl+Enter - Upload Folder To, Download Folder Into."""

        if self.user == config.sections["server"]["login"]:
            self.on_upload_folder_recursive_to()
        else:
            self.on_download_folder_recursive_to()

        return True

    def on_folder_transfer_accelerator(self, *_args):
        """Shift+Ctrl+Enter - Upload Folder Recursive To, Download Folder (without prompt)."""

        if self.user == config.sections["server"]["login"]:
            self.on_upload_folder_recursive_to()
        else:
            self.on_download_folder_recursive()  # without prompt

        return True

    def on_folder_open_manager_accelerator(self, *_args):
        """Ctrl+Alt+Enter - Open folder in File Manager."""

        if self.user != config.sections["server"]["login"]:
            return False

        self.on_file_manager()
        return True

    # Callbacks (file_list_view) #

    def on_file_popup_menu(self, menu, _widget):

        self.select_files()
        menu.set_num_selected_files(len(self.selected_files))

        self.user_popup_menu.toggle_user_items()

    def on_download_files(self, *_args, download_folder_path=None):

        folder_path = self.active_folder_path
        browsed_user = core.userbrowse.users[self.user]

        files = browsed_user.public_folders.get(folder_path)

        if not files:
            files = browsed_user.private_folders.get(folder_path)

            if not files:
                return

        for file_data in files:
            _code, basename, *_unused = file_data

            # Find the wanted file
            if basename not in self.selected_files:
                continue

            core.userbrowse.download_file(
                self.user, folder_path, file_data, download_folder_path=download_folder_path)

    def on_download_files_to_selected(self, selected_download_folder_paths, _data):
        self.on_download_files(download_folder_path=next(iter(selected_download_folder_paths), None))

    def on_download_files_to(self, *_args):

        FolderChooser(
            parent=self.window,
            title=_("Select Destination Folder for Files"),
            callback=self.on_download_files_to_selected,
            initial_folder=core.downloads.get_default_download_folder()
        ).present()

    def on_upload_files_to_response(self, dialog, _response_id, _data):

        user = dialog.get_entry_value()
        folder_path = self.active_folder_path

        if not user or folder_path is None:
            return

        core.userbrowse.send_upload_attempt_notification(user)

        for basename, size in self.selected_files.items():
            core.userbrowse.upload_file(user, folder_path, (None, basename, size))

    def on_upload_files_to(self, *_args):

        EntryDialog(
            parent=self.window,
            title=_("Upload File(s) To User"),
            message=_("Enter the name of the user you want to upload to:"),
            action_button_label=_("_Upload"),
            callback=self.on_upload_files_to_response,
            droplist=sorted(core.buddies.users)
        ).present()

    def on_open_file(self, *_args):

        folder_path = core.shares.virtual2real(self.active_folder_path)

        for basename in self.selected_files:
            open_file_path(os.path.join(folder_path, basename))

    def on_file_manager(self, *_args):

        for iterator in self.folder_tree_view.get_selected_rows():
            folder_path = self.folder_tree_view.get_row_value(iterator, "folder_path_data")
            open_folder_path(core.shares.virtual2real(folder_path))
            return

    def on_file_properties(self, _action, _state, all_files=False):

        data = []
        selected_size = 0
        selected_length = 0
        watched_user = core.users.watched.get(self.user)
        speed = 0

        if watched_user is not None:
            speed = watched_user.upload_speed or 0

        if all_files:
            prev_folder_path = None

            for iterator in self.folder_tree_view.get_selected_rows():
                selected_folder_path = self.folder_tree_view.get_row_value(iterator, "folder_path_data")

                if prev_folder_path and prev_folder_path in selected_folder_path:
                    # Already recursing, avoid duplicates
                    continue

                for folder_path, files in core.userbrowse.iter_matching_folders(
                    selected_folder_path, browsed_user=core.userbrowse.users[self.user], recurse=True
                ):
                    for file_data in files:
                        _code, basename, file_size, _ext, file_attributes, *_unused = file_data
                        _bitrate, length, *_unused = FileListMessage.parse_file_attributes(file_attributes)
                        file_path = "\\".join([folder_path, basename])
                        selected_size += file_size

                        if length:
                            selected_length += length

                        data.append({
                            "user": self.user,
                            "file_path": file_path,
                            "basename": basename,
                            "virtual_folder_path": folder_path,
                            "speed": speed,
                            "size": file_size,
                            "file_attributes": file_attributes
                        })

                prev_folder_path = selected_folder_path

        else:
            selected_folder_path = self.active_folder_path

            for iterator in self.file_list_view.get_selected_rows():
                basename = self.file_list_view.get_row_value(iterator, "filename")
                file_path = "\\".join([selected_folder_path, basename])
                file_size = self.file_list_view.get_row_value(iterator, "size_data")
                selected_size += file_size
                selected_length += self.file_list_view.get_row_value(iterator, "length_data")

                data.append({
                    "user": self.user,
                    "file_path": file_path,
                    "basename": basename,
                    "virtual_folder_path": selected_folder_path,
                    "speed": speed,
                    "size": file_size,
                    "file_attributes": self.file_list_view.get_row_value(iterator, "file_attributes_data"),
                    "country_code": core.users.countries.get(self.user)
                })

        if data:
            if self.userbrowses.file_properties is None:
                self.userbrowses.file_properties = FileProperties(self.window.application)

            self.userbrowses.file_properties.update_properties(data, selected_size, selected_length)
            self.userbrowses.file_properties.present()

    def on_copy_file_path(self, *_args):
        file_path = self.get_selected_file_path()
        clipboard.copy_text(file_path)

    def on_copy_url(self, *_args):
        file_path = self.get_selected_file_path()
        file_url = core.userbrowse.get_soulseek_url(self.user, file_path)
        clipboard.copy_text(file_url)

    # Key Bindings (file_list_view) #

    def on_file_row_activated(self, _tree_view, _iterator, _column_id):

        self.select_files()

        if self.user == config.sections["server"]["login"]:
            self.on_open_file()
        else:
            self.on_download_files()

    def on_focus_folder_left_accelerator(self, *_args):
        """Left - focus back parent folder (left arrow)."""

        column_id = self.file_list_view.get_focused_column()

        if next(self.file_list_view.get_visible_columns(), None) != column_id:
            return False  # allow horizontal scrolling

        self.folder_tree_view.grab_focus()
        return True

    def on_focus_folder_accelerator(self, *_args):
        """BackSpace, \backslash - focus selection back parent folder"""

        self.folder_tree_view.grab_focus()
        return True

    def on_file_transfer_to_accelerator(self, *_args):
        """Ctrl+Enter - Upload File(s) To, Download File(s) Into."""

        if self.file_list_view.is_empty():  # avoid navigation trap
            self.folder_tree_view.grab_focus()
            return True

        self.select_files()

        if self.user == config.sections["server"]["login"]:
            if self.file_list_view.is_selection_empty():
                self.on_upload_folder_to()
            else:
                self.on_upload_files_to()

            return True

        if self.file_list_view.is_selection_empty():
            self.on_download_folder_to()
        else:
            self.on_download_files_to()  # (with prompt, Single or Multi-selection)

        return True

    def on_file_transfer_accelerator(self, *_args):
        """Shift+Ctrl+Enter - Upload File(s) To, Download File(s) (without prompt)."""

        if self.file_list_view.is_empty():
            self.folder_tree_view.grab_focus()  # avoid nav trap
            return True

        self.select_files()

        if self.user == config.sections["server"]["login"]:
            if self.file_list_view.is_selection_empty():
                self.on_upload_folder_to()
            else:
                self.on_upload_files_to()

            return True

        if self.file_list_view.is_selection_empty():
            self.on_download_folder()  # (without prompt, No-selection=All)
        else:
            self.on_download_files()  # (no prompt, Single or Multi-selection)

        return True

    def on_file_transfer_multi_accelerator(self, *_args):
        """Shift+Enter - Open File, Download Files (multiple)."""

        if self.file_list_view.is_empty():
            self.folder_tree_view.grab_focus()  # avoid nav trap
            return True

        self.select_files()  # support multi-select with Up/Dn keys

        if self.user == config.sections["server"]["login"]:
            self.on_open_file()
        else:
            self.on_download_files()

        return True

    def on_file_open_manager_accelerator(self, *_args):
        """Ctrl+Alt+Enter - Open in File Manager."""

        if self.user == config.sections["server"]["login"]:
            self.on_file_manager()

        else:  # [user is not self]
            self.on_file_properties_accelerator()  # same as Alt+Enter

        return True

    def on_file_properties_accelerator(self, *_args):
        """Alt+Enter - show file properties dialog."""

        if self.file_list_view.is_empty():
            self.folder_tree_view.grab_focus()  # avoid nav trap

        self.on_file_properties(*_args)
        return True

    # Callbacks (General) #

    def on_show_progress_bar(self, progress_bar):
        """Enables indeterminate progress bar mode when tab is active."""

        if not self.indeterminate_progress and progress_bar.get_fraction() <= 0.0:
            self.set_indeterminate_progress()

        if core.users.login_status == UserStatus.OFFLINE:
            self.peer_connection_error()

    def on_hide_progress_bar(self, progress_bar):
        """Disables indeterminate progress bar mode when switching to another tab."""

        if self.indeterminate_progress:
            self.indeterminate_progress = False
            progress_bar.set_fraction(0.0)

    def on_path_bar_clicked(self, _button, folder_path):

        iterator = self.folder_tree_view.iterators.get(folder_path)

        if iterator:
            self.folder_tree_view.select_row(iterator)
            self.folder_tree_view.grab_focus()

    def on_path_bar_scroll(self, adjustment, *_args):

        adjustment_end = (adjustment.get_upper() - adjustment.get_page_size())

        if adjustment.get_value() < adjustment_end:
            self.path_bar_container.emit("scroll-child", Gtk.ScrollType.END, True)

    def on_expand(self, *_args):

        active = self.expand_button.get_active()

        if active:
            icon_name = "view-restore-symbolic"
            self.folder_tree_view.expand_all_rows()
        else:
            icon_name = "view-fullscreen-symbolic"
            self.folder_tree_view.collapse_all_rows()

        icon_args = (Gtk.IconSize.BUTTON,) if GTK_API_VERSION == 3 else ()  # pylint: disable=no-member
        self.expand_icon.set_from_icon_name(icon_name, *icon_args)

        config.sections["userbrowse"]["expand_folders"] = active

    def on_tab_popup(self, *_args):
        self.user_popup_menu.toggle_user_items()

    def on_search_enabled(self, *_args):
        self.search_button.set_active(self.search_entry_revealer.get_reveal_child())

    def on_show_search(self, *_args):

        active = self.search_button.get_active()

        if active:
            self.search_entry.grab_focus()

        elif not self.file_list_view.is_selection_empty():
            self.file_list_view.grab_focus()

        else:
            self.folder_tree_view.grab_focus()

        self.search_entry_revealer.set_reveal_child(active)

    def on_search(self, *_args):
        self.find_search_matches()

    def on_search_entry_changed(self, *_args):
        if len(self.search_entry.get_text()) <= 0:
            self.find_search_matches()

    def on_save(self, *_args):
        core.userbrowse.save_shares_list_to_disk(self.user)

    def on_refresh(self, *_args):

        if not self.refresh_button.get_sensitive():
            # Refresh is already in progress
            return

        # Remember selection after refresh
        self.select_files()
        file_path = self.get_selected_file_path()

        self.clear_model()
        self.set_indeterminate_progress()

        if self.local_permission_level:
            core.userbrowse.browse_local_shares(
                path=file_path, permission_level=self.local_permission_level, new_request=True)
        else:
            core.userbrowse.browse_user(self.user, path=file_path, new_request=True)

    def on_focus(self):

        if self.file_list_view.is_selection_empty():
            self.folder_tree_view.grab_focus()
        else:
            self.file_list_view.grab_focus()

        return True

    def on_close(self, *_args):
        core.userbrowse.remove_user(self.user)

    def on_close_all_tabs(self, *_args):
        self.userbrowses.remove_all_pages()

    # Key Bindings (General) #

    def on_expand_accelerator(self, *_args):
        """Ctrl+\backslash - Expand / Collapse All."""

        self.expand_button.set_active(not self.expand_button.get_active())
        return True

    def on_save_accelerator(self, *_args):
        """Ctrl+S - Save Shares List."""

        if not self.save_button.get_sensitive():
            return False

        self.on_save()
        return True

    def on_refresh_accelerator(self, *_args):
        """Ctrl+R or F5 - Refresh."""

        self.on_refresh()
        return True

    def on_search_accelerator(self, *_args):
        """Ctrl+F - Find."""

        if self.search_button.get_sensitive():
            self.search_button.set_active(True)
            self.search_entry.grab_focus()

        return True

    def on_search_next_accelerator(self, *_args):
        """Ctrl+G or F3 - Find Next."""

        if not self.find_search_matches():
            self.search_entry.grab_focus()

        return True

    def on_search_previous_accelerator(self, *_args):
        """Shift+Ctrl+G or Shift+F3 - Find Previous."""

        if not self.find_search_matches(reverse=True):
            self.search_entry.grab_focus()

        return True

    def on_search_escape_accelerator(self, *_args):
        """Escape - navigate out of search_entry."""

        self.search_button.set_active(False)
        return True
