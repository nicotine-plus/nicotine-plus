# COPYRIGHT (C) 2020-2021 Nicotine+ Team
# COPYRIGHT (C) 2016-2017 Michael Labouebe <gfarmerfr@free.fr>
# COPYRIGHT (C) 2016-2018 Mutnick <mutnick@techie.com>
# COPYRIGHT (C) 2013 eL_vErDe <gandalf@le-vert.net>
# COPYRIGHT (C) 2008-2012 Quinox <quinox@users.sf.net>
# COPYRIGHT (C) 2009 Hedonist <ak@sensi.org>
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
import re

from gi.repository import Gdk
from gi.repository import Gtk

from pynicotine.gtkgui.dialogs import option_dialog
from pynicotine.gtkgui.fileproperties import FileProperties
from pynicotine.gtkgui.transferlist import TransferList
from pynicotine.gtkgui.utils import human_size
from pynicotine.gtkgui.utils import human_speed
from pynicotine.gtkgui.utils import open_file_path
from pynicotine.gtkgui.utils import PopupMenu
from pynicotine.logfacility import log


class Downloads(TransferList):

    def __init__(self, frame, tab_label):

        TransferList.__init__(self, frame, type='download')
        self.tab_label = tab_label

        self.popup_menu_users = PopupMenu(frame, False)
        self.popup_menu_clear = popup2 = PopupMenu(frame, False)
        popup2.setup(
            ("#" + _("Clear Finished/Aborted"), self.on_clear_finished_aborted),
            ("#" + _("Clear Finished"), self.on_clear_finished),
            ("#" + _("Clear Aborted"), self.on_clear_aborted),
            ("#" + _("Clear Paused"), self.on_clear_paused),
            ("#" + _("Clear Filtered"), self.on_clear_filtered),
            ("#" + _("Clear Queued"), self.on_clear_queued)
        )

        self.popup_menu = popup = PopupMenu(frame)
        popup.setup(
            ("#" + "selected_files", None),
            ("", None),
            ("#" + _("Send to _Player"), self.on_play_files),
            ("#" + _("_Open Folder"), self.on_open_directory),
            ("#" + _("File P_roperties"), self.on_file_properties),
            ("", None),
            ("#" + _("Copy _File Path"), self.on_copy_file_path),
            ("#" + _("Copy _URL"), self.on_copy_url),
            ("#" + _("Copy Folder URL"), self.on_copy_dir_url),
            ("", None),
            ("#" + _("_Search"), self.on_file_search),
            (1, _("User(s)"), self.popup_menu_users, self.on_popup_menu_users),
            ("", None),
            ("#" + _("_Retry"), self.on_retry_transfer),
            ("#" + _("Abor_t"), self.on_abort_transfer),
            ("#" + _("_Clear"), self.on_clear_transfer),
            ("", None),
            (1, _("Clear Groups"), self.popup_menu_clear, None)
        )

        self.update_download_filters()

    def on_try_clear_queued(self, widget):
        option_dialog(
            parent=self.frame.MainWindow,
            title=_('Clear Queued Downloads'),
            message=_('Are you sure you wish to clear all queued downloads?'),
            callback=self.on_clear_response
        )

    def download_large_folder(self, username, folder, numfiles, conn, file_list):
        option_dialog(
            parent=self.frame.MainWindow,
            title=_("Download %(num)i files?") % {'num': numfiles},
            message=_("Are you sure you wish to download %(num)i files from %(user)s's folder %(folder)s?") % {'num': numfiles, 'user': username, 'folder': folder},
            callback=self.folder_download_response,
            callback_data=(conn, file_list)
        )

    def folder_download_response(self, dialog, response, data):

        if response == Gtk.ResponseType.OK:
            self.frame.np.transfers.folder_contents_response(data[0], data[1])

        dialog.destroy()

    def update_download_filters(self):

        proccessedfilters = []
        outfilter = "(\\\\("
        failed = {}
        df = sorted(self.frame.np.config.sections["transfers"]["downloadfilters"])
        # Get Filters from config file and check their escaped status
        # Test if they are valid regular expressions and save error messages

        for item in df:
            dfilter, escaped = item
            if escaped:
                dfilter = re.escape(dfilter)
                dfilter = dfilter.replace("\\*", ".*")

            try:
                re.compile("(" + dfilter + ")")
                outfilter += dfilter
                proccessedfilters.append(dfilter)
            except Exception as e:
                failed[dfilter] = e

            proccessedfilters.append(dfilter)

            if item is not df[-1]:
                outfilter += "|"

        # Crop trailing pipes
        while outfilter[-1] == "|":
            outfilter = outfilter[:-1]

        outfilter += ")$)"
        try:
            re.compile(outfilter)
            self.frame.np.config.sections["transfers"]["downloadregexp"] = outfilter
            # Send error messages for each failed filter to log window
            if len(failed) >= 1:
                errors = ""

                for dfilter, error in failed.items():
                    errors += "Filter: %s Error: %s " % (dfilter, error)

                error = _("Error: %(num)d Download filters failed! %(error)s ", {'num': len(failed), 'error': errors})
                log.add(error)

        except Exception as e:
            # Strange that individual filters _and_ the composite filter both fail
            log.add(_("Error: Download Filter failed! Verify your filters. Reason: %s", e))
            self.frame.np.config.sections["transfers"]["downloadregexp"] = ""

    def selected_results_all_data(self, model, path, iterator, data):
        if iterator in self.selected_users:
            return

        user = model.get_value(iterator, 0)
        filename = model.get_value(iterator, 2)
        fullname = model.get_value(iterator, 10)
        size = speed = length = queue = immediate = num = country = bitratestr = ""

        for transfer in self.frame.np.transfers.downloads:
            if transfer.user == user and fullname == transfer.filename:
                size = str(human_size(transfer.size))
                try:
                    if transfer.speed:
                        speed = str(human_speed(transfer.speed))
                except Exception:
                    pass
                bitratestr = str(transfer.bitrate)
                length = str(transfer.length)
                break
        else:
            return

        directory = fullname.rsplit("\\", 1)[0]

        data.append({
            "user": user,
            "fn": fullname,
            "position": num,
            "filename": filename,
            "directory": directory,
            "size": size,
            "speed": speed,
            "queue": queue,
            "immediate": immediate,
            "bitrate": bitratestr,
            "length": length,
            "country": country
        })

    def on_file_properties(self, widget):

        if not self.frame.np.transfers:
            return

        data = []
        self.widget.get_selection().selected_foreach(self.selected_results_all_data, data)

        if data:
            FileProperties(self.frame, data).show()

    def on_open_directory(self, widget):

        downloaddir = self.frame.np.config.sections["transfers"]["downloaddir"]
        incompletedir = self.frame.np.config.sections["transfers"]["incompletedir"]

        if incompletedir == "":
            incompletedir = downloaddir

        transfer = next(iter(self.selected_transfers))

        complete_path = os.path.join(downloaddir, transfer.path)

        if transfer.path == "":
            if transfer.status == "Finished":
                final_path = downloaddir
            else:
                final_path = incompletedir
        elif os.path.exists(complete_path):  # and tranfer.status is "Finished"
            final_path = complete_path
        else:
            final_path = incompletedir

        # Finally, try to open the directory we got...
        command = self.frame.np.config.sections["ui"]["filemanager"]
        open_file_path(final_path, command)

    def on_key_press_event(self, widget, event):

        key = Gdk.keyval_name(event.keyval)

        self.select_transfers()

        if key in ("T", "t"):
            self.on_abort_transfer(widget)
        elif key in ("R", "r"):
            self.on_retry_transfer(widget)
        elif key in ("C", "c") and event.state in (Gdk.ModifierType.CONTROL_MASK, Gdk.ModifierType.LOCK_MASK | Gdk.ModifierType.CONTROL_MASK):
            self.on_copy_file_path(widget)
        elif key == "Delete":
            self.on_abort_transfer(widget, clear=True)
        else:
            # No key match, continue event
            return False

        widget.stop_emission_by_name("key_press_event")
        return True

    def _on_play_files(self, widget, prefix=""):

        downloaddir = self.frame.np.config.sections["transfers"]["downloaddir"]

        for fn in self.selected_transfers:

            playfile = None

            if fn.file is not None and os.path.exists(fn.file.name):
                playfile = fn.file.name
            else:
                # If this file doesn't exist anymore, it may have finished downloading and have been renamed
                # try looking in the download directory and match the original filename.
                basename = str.split(fn.filename, '\\')[-1]
                path = os.sep.join([downloaddir, basename])

                if os.path.exists(path):
                    playfile = path

            if playfile:
                command = self.frame.np.config.sections["players"]["default"]
                open_file_path(playfile, command)

    def double_click(self, event):

        self.select_transfers()
        dc = self.frame.np.config.sections["transfers"]["download_doubleclick"]

        if dc == 1:  # Send to player
            self.on_play_files(None)
        elif dc == 2:  # File manager
            self.on_open_directory(None)
        elif dc == 3:  # Search
            self.on_file_search(None)
        elif dc == 4:  # Abort
            self.on_abort_transfer(None)
        elif dc == 5:  # Clear
            self.on_clear_transfer(None)
        elif dc == 6:  # Retry
            self.on_retry_transfer(None)

    def on_popup_menu(self, widget):

        self.select_transfers()
        num_selected_transfers = len(self.selected_transfers)

        users = len(self.selected_users) > 0
        files = num_selected_transfers > 0

        items = self.popup_menu.get_items()
        items[_("User(s)")].set_sensitive(users)  # Users Menu

        if files:
            act = True
        else:
            # Disable options
            # Send to player, File manager, file properties, Copy File Path, Copy URL, Copy Folder URL, Search filename
            act = False

        for i in (_("Send to _Player"), _("_Open Folder"), _("File P_roperties"),
                  _("Copy _File Path"), _("Copy _URL"), _("Copy Folder URL"), _("_Search")):
            items[i].set_sensitive(act)

        if not users or not files:
            # Disable options
            # Retry, Abort, Clear
            act = False
        else:
            act = True

        for i in (_("_Retry"), _("Abor_t"), _("_Clear")):
            items[i].set_sensitive(act)

        items["selected_files"].set_sensitive(False)
        items["selected_files"].set_label(_("%s File(s) Selected") % num_selected_transfers)

        self.popup_menu.popup()
        return True

    def on_abort_transfer(self, widget, clear=False):
        self.select_transfers()
        self.abort_transfers(clear)

    def on_clear_queued(self, widget):
        self.clear_transfers(["Queued"])

    def on_retry_transfer(self, widget):

        self.select_transfers()

        for transfer in self.selected_transfers:
            self.frame.np.transfers.retry_download(transfer)
