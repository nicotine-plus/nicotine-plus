# SPDX-FileCopyrightText: 2024-2025 Nicotine+ Contributors
# SPDX-License-Identifier: GPL-3.0-or-later

import os

from locale import strxfrm

from gi.repository import GLib
from gi.repository import GObject
from gi.repository import Gtk

from pynicotine.config import config
from pynicotine.core import core
from pynicotine.events import events
from pynicotine.gtkgui.application import GTK_API_VERSION
from pynicotine.gtkgui.widgets import ui
from pynicotine.gtkgui.widgets.dialogs import Dialog
from pynicotine.gtkgui.widgets.dialogs import EntryDialog
from pynicotine.gtkgui.widgets.filechooser import FileChooserButton
from pynicotine.gtkgui.widgets.infobar import InfoBar
from pynicotine.gtkgui.widgets.treeview import TreeView
from pynicotine.utils import human_size
from pynicotine.utils import humanize


class Download(Dialog):

    def __init__(self, application):

        (
            self.cancel_button,
            self.container,
            self.download_button,
            self.download_folder_default_button,
            self.download_folder_label,
            self.download_paused_button,
            self.enable_subfolders_toggle,
            self.expand_button,
            self.expand_icon,
            self.info_bar_container,
            self.list_container,
            self.progress_bar,
            self.rename_button,
            self.retry_button,
            self.select_initial_button,
            self.unselect_all_button
        ) = ui.load(scope=self, path="dialogs/download.ui")

        super().__init__(
            parent=application.window,
            content_box=self.container,
            buttons_start=(self.cancel_button,),
            buttons_end=(self.download_paused_button, self.download_button),
            default_button=self.download_button,
            close_callback=self.on_close,
            title=_("Download Files"),
            width=650,
            height=650,
            show_title_buttons=False
        )
        application.add_window(self.widget)
        self.application = application
        self.parent_iterators = {}
        self.initial_selected_iterators = set()
        self.folder_names = {}
        self.pending_folders = {}
        self.num_files = {}
        self.num_selected_files = {}
        self.indeterminate_progress = False
        self.select_all = False
        self.total_selected_size = 0

        self.download_folder_button = FileChooserButton(
            self.download_folder_label.get_parent(), window=self,
            label=self.download_folder_label, end_button=self.download_folder_default_button,
            chooser_type="folder"
        )
        self.info_bar = InfoBar(parent=self.info_bar_container, button=self.retry_button)

        self.tree_view = TreeView(
            application.window, parent=self.list_container, has_tree=True,
            activate_row_callback=self.on_row_activated,
            select_row_callback=self.on_row_selected,
            columns={
                # Visible columns
                "name": {
                    "column_type": "text",
                    "title": _("Folder / File"),
                    "width": 150,
                    "expand_column": True,
                    "default_sort_type": "ascending"
                },
                "size": {
                    "column_type": "number",
                    "title": _("Size"),
                    "width": 100,
                    "sort_column": "size_data"
                },
                "selected": {
                    "column_type": "toggle",
                    "title": _("Selected"),
                    "width": 0,
                    "toggle_callback": self.on_select_file,
                    "inconsistent_column": "inconsistent_data",
                    "hide_header": True
                },

                # Hidden data columns
                "user_data": {"data_type": str},
                "folder_path_data": {"data_type": str},
                "size_data": {"data_type": GObject.TYPE_UINT64},
                "file_attributes_data": {"data_type": GObject.TYPE_PYOBJECT},
                "inconsistent_data": {"data_type": bool},
                "id_data": {
                    "data_type": str,
                    "iterator_key": True
                }
            }
        )

        self.expand_button.connect("toggled", self.on_expand_tree)

        for event_name, callback in (
            ("folder-contents-response", self.folder_contents_response),
            ("folder-contents-timeout", self.folder_contents_timeout),
            ("server-disconnect", self.server_disconnect),
        ):
            events.connect(event_name, callback)

    def destroy(self):

        self.clear()

        self.download_folder_button.destroy()
        self.info_bar.destroy()
        self.tree_view.destroy()
        super().destroy()

        self.indeterminate_progress = False

    def clear(self):

        self.folder_names.clear()
        self.parent_iterators.clear()
        self.initial_selected_iterators.clear()
        self.pending_folders.clear()
        self.num_files.clear()
        self.num_selected_files.clear()
        self.tree_view.clear()

        self.total_selected_size = 0

        self.set_finished()

    def update_files(self, data, partial_files=True, select_all=False):

        self.tree_view.freeze()

        self.rename_button.set_sensitive(False)
        self.expand_button.set_active(True)
        self.enable_subfolders_toggle.set_active(True)
        self.enable_subfolders_toggle.get_parent().set_visible(partial_files)
        self.download_folder_button.set_path(config.sections["transfers"]["downloaddir"])

        self.select_all = select_all
        has_unselected_files = False

        for username, file_path, size, file_attributes, selected, root_folder_path in sorted(
            data, key=lambda x: len(x[0])
        ):
            if username + file_path in self.tree_view.iterators:
                continue

            folder_path, _separator, file_name = file_path.rpartition("\\")
            folder_path_parent, _separator, folder_name = folder_path.rpartition("\\")
            parent_iterator = self.parent_iterators.get(username + folder_path)

            if root_folder_path is not None:
                common_path, separator, _unused = root_folder_path.rpartition("\\")
                folder_name = folder_path[len(common_path) + len(separator):]

            elif folder_path_parent in self.folder_names:
                common_path, separator, _unused = folder_path_parent.rpartition("\\")
                folder_name = folder_path[len(common_path) + len(separator):]

            elif len(folder_name) < 12:
                folder_name = os.path.join(*folder_path.split("\\")[-2:])

            folder_name = folder_name.replace("\\", os.sep)
            self.folder_names[folder_path] = folder_name

            if parent_iterator is None:
                if partial_files:
                    core.downloads.request_folder(username, folder_path)

                    if username not in self.pending_folders:
                        self.pending_folders[username] = set()

                    self.pending_folders[username].add(folder_path)

                if username not in self.num_files:
                    self.num_files[username] = {}
                    self.num_selected_files[username] = {}

                self.num_files[username][folder_path] = 0
                self.num_selected_files[username][folder_path] = 0

                if not selected:
                    has_unselected_files = True
                    inconsistent = True
                else:
                    inconsistent = False

                parent_iterator = self.parent_iterators[username + folder_path] = self.tree_view.add_row(
                    [
                        folder_name,
                        "",
                        select_all or selected,
                        username,
                        folder_path,
                        0,
                        {},
                        inconsistent,
                        username + folder_path
                    ],
                    select_row=False
                )
                self.initial_selected_iterators.add(parent_iterator)

            iterator = self.tree_view.add_row(
                [
                    file_name,
                    human_size(size),
                    select_all or selected,
                    username,
                    folder_path,
                    size,
                    file_attributes,
                    False,
                    username + file_path
                ],
                select_row=False, parent_iterator=parent_iterator
            )
            self.num_files[username][folder_path] += 1

            if selected:
                self.initial_selected_iterators.add(iterator)
            else:
                self.initial_selected_iterators.discard(parent_iterator)

            if select_all or selected:
                self.total_selected_size += size
                self.num_selected_files[username][folder_path] += 1

        self.update_title()
        self.tree_view.expand_all_rows()

        if partial_files:
            self.set_in_progress()

        self.tree_view.unfreeze()

        if has_unselected_files:
            return

        self.unselect_all_button.set_visible(True)

        if not partial_files:
            self.select_initial_button.set_visible(False)

    def update_title(self):

        num_selected_files = 0

        for folders in self.num_selected_files.values():
            for count in folders.values():
                num_selected_files += count

        self.set_title(_("Download %(num_files)s file(s)  /  %(total_size)s") % {
            "num_files": humanize(num_selected_files),
            "total_size": human_size(self.total_selected_size)
        })

    def download(self, paused=False):

        files = []

        for iterator in self.tree_view.iterators.values():
            selected = self.tree_view.get_row_value(iterator, "selected")

            if not selected:
                continue

            row_id = self.tree_view.get_row_value(iterator, "id_data")

            if row_id in self.parent_iterators:
                continue

            username = self.tree_view.get_row_value(iterator, "user_data")
            folder_path = self.tree_view.get_row_value(iterator, "folder_path_data")
            file_name = self.tree_view.get_row_value(iterator, "name")
            file_path = "\\".join([folder_path, file_name])
            size = self.tree_view.get_row_value(iterator, "size_data")
            file_attributes = self.tree_view.get_row_value(iterator, "file_attributes_data")
            destination_folder_path = None

            if self.enable_subfolders_toggle.get_active():
                download_folder_path = self.download_folder_button.get_path()

                if download_folder_path == config.sections["transfers"]["downloaddir"]:
                    download_folder_path = core.downloads.get_default_download_folder(username)

                destination_folder_name = self.folder_names[folder_path]
                destination_folder_path = os.path.join(download_folder_path, destination_folder_name)

            files.append((username, file_path, destination_folder_path, size, file_attributes))

        files.sort(key=lambda x: strxfrm(x[1]))

        for username, file_path, destination_folder_path, size, file_attributes in files:
            core.downloads.enqueue_download(
                username, file_path, folder_path=destination_folder_path, size=size,
                file_attributes=file_attributes, paused=paused
            )

        self.close()

    def pulse_progress(self, repeat=True):

        if not self.indeterminate_progress:
            return False

        self.progress_bar.pulse()
        return repeat

    def set_in_progress(self):

        self.indeterminate_progress = True

        self.progress_bar.get_parent().set_reveal_child(True)
        self.progress_bar.pulse()
        GLib.timeout_add(320, self.pulse_progress, False)
        GLib.timeout_add(1000, self.pulse_progress)

        self.info_bar.set_visible(False)

    def set_finished(self):

        self.indeterminate_progress = False

        self.progress_bar.set_fraction(1.0)
        self.progress_bar.get_parent().set_reveal_child(False)

        self.info_bar.set_visible(False)

    def set_failed(self):

        if not self.indeterminate_progress:
            return

        self.set_finished()
        self.info_bar.show_error_message(
            _("Failed to request folder contents.")
        )
        self.info_bar.set_visible(True)

    def reset_selected_count(self):

        self.total_selected_size = 0

        for folders in self.num_selected_files.values():
            for folder_path in folders:
                folders[folder_path] = 0

    def folder_contents_response(self, msg):

        self.tree_view.freeze()

        username = msg.username
        selected = self.select_all
        has_added_file = False

        for folder_path, files in msg.list.items():
            if username not in self.pending_folders:
                continue

            if folder_path not in self.pending_folders[username]:
                continue

            parent_iterator = self.parent_iterators[username + folder_path]
            unselected_parent = False

            for _code, file_name, size, _ext, file_attributes, *_unused in files:
                file_path = "\\".join([folder_path, file_name])

                if username + file_path in self.tree_view.iterators:
                    continue

                self.tree_view.add_row(
                    [
                        file_name,
                        human_size(size),
                        selected,
                        username,
                        folder_path,
                        size,
                        file_attributes,
                        False,
                        username + file_path
                    ],
                    select_row=False, parent_iterator=parent_iterator
                )
                self.num_files[username][folder_path] += 1
                has_added_file = True

                if selected:
                    self.total_selected_size += size
                    self.num_selected_files[username][folder_path] += 1

                if not unselected_parent:
                    if not selected:
                        self.tree_view.set_row_value(parent_iterator, "selected", False)

                    self.initial_selected_iterators.discard(parent_iterator)
                    unselected_parent = True

            if not files:
                self.set_failed()

            self.pending_folders[username].remove(folder_path)

            if not self.pending_folders[username]:
                del self.pending_folders[username]

        if selected:
            self.update_title()

        elif has_added_file:
            self.unselect_all_button.set_visible(False)

        if not self.pending_folders:
            self.set_finished()

        elif not msg.list:
            self.set_failed()

        self.tree_view.unfreeze()

    def folder_contents_timeout(self, username, folder_path):

        if username not in self.pending_folders:
            return

        if folder_path not in self.pending_folders[username]:
            return

        self.set_failed()

    def server_disconnect(self, *_args):
        if self.indeterminate_progress:
            self.set_failed()

    def on_retry(self, *_args):

        self.set_in_progress()

        for username, folders in self.pending_folders.items():
            for folder_path in folders:
                core.downloads.request_folder(username, folder_path)

    def on_rename_response(self, dialog, _response_id, iterator):

        folder_name = dialog.get_entry_value().strip()

        if not folder_name:
            return

        folder_path = self.tree_view.get_row_value(iterator, "folder_path_data")
        self.folder_names[folder_path] = folder_name

        self.tree_view.set_row_value(iterator, "name", folder_name)

    def on_rename(self, *_args):

        for iterator in self.tree_view.get_selected_rows():
            username = self.tree_view.get_row_value(iterator, "user_data")
            folder_path = self.tree_view.get_row_value(iterator, "folder_path_data")
            folder_name = self.folder_names[folder_path]
            parent_iterator = self.parent_iterators[username + folder_path]

            EntryDialog(
                parent=self,
                title=_("Rename Folder"),
                message=_("Enter new folder name for '%s':") % folder_name,
                default=folder_name,
                action_button_label=_("_Rename"),
                callback=self.on_rename_response,
                callback_data=parent_iterator
            ).present()
            return

    def on_select_all(self, *_args):

        self.reset_selected_count()

        for iterator in self.tree_view.iterators.values():
            row_id = self.tree_view.get_row_value(iterator, "id_data")
            self.tree_view.set_row_value(iterator, "selected", True)

            if row_id in self.parent_iterators:
                self.tree_view.set_row_value(iterator, "inconsistent_data", False)
                continue

            username = self.tree_view.get_row_value(iterator, "user_data")
            folder_path = self.tree_view.get_row_value(iterator, "folder_path_data")

            self.total_selected_size += self.tree_view.get_row_value(iterator, "size_data")
            self.num_selected_files[username][folder_path] += 1

        self.unselect_all_button.set_visible(True)
        self.update_title()

    def on_unselect_all(self, *_args):

        self.reset_selected_count()

        for iterator in self.tree_view.iterators.values():
            self.tree_view.set_row_value(iterator, "selected", False)

        self.unselect_all_button.set_visible(False)
        self.update_title()

    def on_select_initial(self, *_args):

        self.reset_selected_count()

        for iterator in self.tree_view.iterators.values():
            selected = iterator in self.initial_selected_iterators
            self.tree_view.set_row_value(iterator, "selected", selected)

            if not selected:
                continue

            username = self.tree_view.get_row_value(iterator, "user_data")
            folder_path = self.tree_view.get_row_value(iterator, "folder_path_data")
            row_id = self.tree_view.get_row_value(iterator, "id_data")

            if row_id in self.parent_iterators:
                self.tree_view.set_row_value(iterator, "inconsistent_data", True)
                continue

            self.total_selected_size += self.tree_view.get_row_value(iterator, "size_data")
            self.num_selected_files[username][folder_path] += 1
            parent_iterator = self.parent_iterators[username + folder_path]

            self.tree_view.set_row_value(
                parent_iterator, "inconsistent_data",
                self.num_selected_files[username][folder_path] != self.num_files[username][folder_path]
            )
            self.tree_view.set_row_value(parent_iterator, "selected", True)

        self.unselect_all_button.set_visible(False)
        self.update_title()

    def on_expand_tree(self, *_args):

        if not self.expand_button.get_visible():
            return

        expanded = self.expand_button.get_active()

        if expanded:
            icon_name = "view-restore-symbolic"
            tooltip_text = _("Collapse All")
            self.tree_view.expand_all_rows()
        else:
            icon_name = "view-fullscreen-symbolic"
            tooltip_text = _("Expand All")
            self.tree_view.collapse_all_rows()

        icon_args = (Gtk.IconSize.BUTTON,) if GTK_API_VERSION == 3 else ()  # pylint: disable=no-member
        self.expand_icon.set_from_icon_name(icon_name, *icon_args)
        self.expand_button.set_tooltip_text(tooltip_text)

    def on_select_file(self, tree_view, iterator):

        selected = not tree_view.get_row_value(iterator, "selected")
        username = tree_view.get_row_value(iterator, "user_data")
        folder_path = tree_view.get_row_value(iterator, "folder_path_data")
        row_id = tree_view.get_row_value(iterator, "id_data")

        tree_view.set_row_value(iterator, "selected", selected)
        tree_view.set_row_value(iterator, "inconsistent_data", False)

        if row_id in self.parent_iterators:
            for i_iterator in tree_view.iterators.values():
                i_folder_path = tree_view.get_row_value(i_iterator, "folder_path_data")

                if i_folder_path != folder_path:
                    continue

                i_selected = tree_view.get_row_value(i_iterator, "selected")

                if selected and not i_selected:
                    self.total_selected_size += self.tree_view.get_row_value(i_iterator, "size_data")
                    self.num_selected_files[username][i_folder_path] += 1

                elif not selected and i_selected:
                    self.total_selected_size -= self.tree_view.get_row_value(i_iterator, "size_data")
                    self.num_selected_files[username][i_folder_path] -= 1

                tree_view.set_row_value(i_iterator, "selected", selected)
        else:
            parent_iterator = self.parent_iterators[username + folder_path]

            if selected:
                self.total_selected_size += tree_view.get_row_value(iterator, "size_data")
                self.num_selected_files[username][folder_path] += 1

                tree_view.set_row_value(parent_iterator, "selected", True)
                tree_view.set_row_value(
                    parent_iterator, "inconsistent_data",
                    self.num_selected_files[username][folder_path] != self.num_files[username][folder_path]
                )
            else:
                self.total_selected_size -= tree_view.get_row_value(iterator, "size_data")
                self.num_selected_files[username][folder_path] -= 1
                has_selected_files = self.num_selected_files[username][folder_path] > 0

                tree_view.set_row_value(parent_iterator, "selected", has_selected_files)
                tree_view.set_row_value(parent_iterator, "inconsistent_data", has_selected_files)

        self.update_title()

    def on_toggle_enable_subfolders(self, *_args):
        self.rename_button.set_visible(self.enable_subfolders_toggle.get_active())

    def on_default_download_folder(self, *_args):
        self.download_folder_button.set_path(config.sections["transfers"]["downloaddir"])

    def on_row_activated(self, tree_view, iterator, column_id):

        if column_id == "selected":
            return

        is_file = tree_view.get_row_value(iterator, "id_data") not in self.parent_iterators

        if is_file:
            self.on_select_file(tree_view, iterator)
            return

        if tree_view.is_row_expanded(iterator):
            tree_view.collapse_row(iterator)
        else:
            tree_view.expand_row(iterator)

    def on_row_selected(self, tree_view, iterator):

        if iterator is None:
            return

        is_folder = tree_view.get_row_value(iterator, "id_data") in self.parent_iterators
        self.rename_button.set_sensitive(is_folder)

    def on_cancel(self, *_args):
        self.close()

    def on_download(self, *_args):
        self.download()

    def on_download_paused(self, *_args):
        self.download(paused=True)

    def on_close(self, *_args):
        self.clear()
