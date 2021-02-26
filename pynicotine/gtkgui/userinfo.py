# COPYRIGHT (C) 2020-2021 Nicotine+ Team
# COPYRIGHT (C) 2016-2017 Michael Labouebe <gfarmerfr@free.fr>
# COPYRIGHT (C) 2008-2010 Quinox <quinox@users.sf.net>
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
import time

from gi.repository import GdkPixbuf
from gi.repository import Gtk

from pynicotine import slskmessages
from pynicotine.gtkgui.dialogs import save_file
from pynicotine.gtkgui.utils import append_line
from pynicotine.gtkgui.utils import humanize
from pynicotine.gtkgui.utils import human_speed
from pynicotine.gtkgui.utils import IconNotebook
from pynicotine.gtkgui.utils import InfoBar
from pynicotine.gtkgui.utils import initialise_columns
from pynicotine.gtkgui.utils import load_ui_elements
from pynicotine.gtkgui.utils import PopupMenu
from pynicotine.gtkgui.utils import set_treeview_selected_row
from pynicotine.gtkgui.utils import triggers_context_menu
from pynicotine.gtkgui.utils import update_widget_visuals
from pynicotine.logfacility import log


# User Info and User Browse Notebooks
class UserTabs(IconNotebook):

    def __init__(self, frame, subwindow, notebookraw, tab_label, tab_name):

        self.frame = frame

        ui = frame.np.config.sections["ui"]

        IconNotebook.__init__(
            self,
            self.frame.images,
            angle=ui["labelinfo"],
            tabclosers=ui["tabclosers"],
            show_hilite_image=self.frame.np.config.sections["notifications"]["notification_tab_icons"],
            reorderable=ui["tab_reorderable"],
            show_status_image=ui["tab_status_icons"],
            notebookraw=notebookraw
        )

        self.popup_enable()

        self.subwindow = subwindow

        self.users = {}
        self.tab_label = tab_label
        self.tab_name = tab_name

    def init_window(self, user):

        try:
            status = self.frame.np.users[user].status
        except Exception:
            # Offline
            status = 0

        w = self.users[user] = self.subwindow(self, user)
        self.append_page(w.Main, user, w.on_close, status=status)

    def show_user(self, user, conn=None, msg=None, indeterminate_progress=False, change_page=True, folder=None, local_shares_type=None):

        self.save_columns()

        if user in self.users:
            self.users[user].conn = conn
        else:
            self.init_window(user)

        self.users[user].show_user(msg, folder, indeterminate_progress, local_shares_type)

        if change_page:
            self.set_current_page(self.page_num(self.users[user].Main))
            self.frame.change_main_page(self.tab_name)

    def show_connection_error(self, user):
        if user in self.users:
            self.users[user].show_connection_error()

    def save_columns(self):
        for user in self.users:
            self.users[user].save_columns()

    def get_user_stats(self, msg):

        if msg.user in self.users:
            tab = self.users[msg.user]
            tab.speed.set_text(_("Speed: %s") % human_speed(msg.avgspeed))
            tab.filesshared.set_text(_("Files: %s") % humanize(msg.files))
            tab.dirsshared.set_text(_("Directories: %s") % humanize(msg.dirs))

    def get_user_status(self, msg):

        if msg.user in self.users:

            tab = self.users[msg.user]
            tab.status = msg.status

            self.set_user_status(tab.Main, msg.user, msg.status)

    def is_new_request(self, user):

        if user in self.users:
            return self.users[user].is_refreshing()

        return True

    def show_interests(self, msg):

        if msg.user in self.users:
            self.users[msg.user].show_interests(msg.likes, msg.hates)

    def update_gauge(self, msg):

        for i in self.users.values():
            if i.conn == msg.conn.conn:
                i.update_gauge(msg)

    def update_visuals(self):

        for i in self.users.values():
            i.update_visuals()

    def tab_popup(self, user):

        if user in self.users:
            return self.users[user].tab_popup(user)

    def on_tab_popup(self, widget, page):

        username = self.get_page_owner(page, self.users)
        menu = self.tab_popup(username)

        if menu is None:
            return False

        menu.popup()
        return True

    def on_tab_click(self, widget, event, page):

        if triggers_context_menu(event):
            return self.on_tab_popup(widget, page)

        if event.button == 2:
            username = self.get_page_owner(page, self.users)
            self.users[username].on_close(widget)
            return True

        return False

    def close_all_tabs(self, dialog, response, data):

        if response == Gtk.ResponseType.OK:
            for user in self.users.copy():
                self.users[user].on_close(dialog)

        dialog.destroy()

    def conn_close(self):

        self.connected = 0

        for user in self.users:
            tab = self.users[user]
            tab.status = 0

            self.set_user_status(tab.Main, user, tab.status)


class UserInfo:

    def __init__(self, userinfos, user):

        self.userinfos = userinfos
        self.frame = userinfos.frame

        # Build the window
        load_ui_elements(self, os.path.join(self.frame.gui_dir, "ui", "userinfo.ui"))
        self.info_bar = InfoBar(self.InfoBar, Gtk.MessageType.INFO)

        # Request user status, speed and number of shared files
        self.frame.np.queue.put(slskmessages.AddUser(user))

        # Request user interests
        self.frame.np.queue.put(slskmessages.UserInterests(user))

        self.user = user
        self.conn = None
        self._descr = ""
        self.image_pixbuf = None
        self.zoom_factor = 5
        self.actual_zoom = 0
        self.status = 0

        self.hates_store = Gtk.ListStore(str)
        self.Hates.set_model(self.hates_store)

        cols = initialise_columns(
            None,
            self.Hates,
            ["hates", _("Hates"), 0, "text", None]
        )
        cols["hates"].set_sort_column_id(0)

        self.hates_store.set_sort_column_id(0, Gtk.SortType.ASCENDING)

        self.likes_store = Gtk.ListStore(str)
        self.Likes.set_model(self.likes_store)

        cols = initialise_columns(
            None,
            self.Likes,
            ["likes", _("Likes"), 0, "text", None]
        )
        cols["likes"].set_sort_column_id(0)

        self.likes_store.set_sort_column_id(0, Gtk.SortType.ASCENDING)

        self.tag_local = self.descr.get_buffer().create_tag()

        self.update_visuals()

        self.user_popup = popup = PopupMenu(self.frame)
        popup.setup_user_menu(user)
        popup.get_items()[_("Show User I_nfo")].set_visible(False)

        popup.append_item(("", None))
        popup.append_item(("#" + _("Close All Tabs"), popup.on_close_all_tabs, self.userinfos))
        popup.append_item(("#" + _("_Close Tab"), self.on_close))

        self.likes_popup_menu = popup = PopupMenu(self.frame)
        popup.setup(
            ("$" + _("I _Like This"), self.frame.interests.on_like_recommendation),
            ("$" + _("I _Dislike This"), self.frame.interests.on_dislike_recommendation),
            ("", None),
            ("#" + _("_Search For Item"), self.frame.interests.on_recommend_search)
        )

        self.hates_popup_menu = popup = PopupMenu(self.frame)
        popup.setup(
            ("$" + _("I _Like This"), self.frame.interests.on_like_recommendation),
            ("$" + _("I _Dislike This"), self.frame.interests.on_dislike_recommendation),
            ("", None),
            ("#" + _("_Search For Item"), self.frame.interests.on_recommend_search)
        )

        self.image_menu = popup = PopupMenu(self.frame)
        popup.setup(
            ("#" + _("Zoom 1:1"), self.make_zoom_normal),
            ("#" + _("Zoom In"), self.make_zoom_in),
            ("#" + _("Zoom Out"), self.make_zoom_out),
            ("", None),
            ("#" + _("Save Picture"), self.on_save_picture)
        )

    def get_selected_like_item(self, treeview):

        model, iterator = treeview.get_selection().get_selected()

        if iterator is None:
            return None

        return model.get_value(iterator, 0)

    def on_likes_list_clicked(self, widget, event):

        if triggers_context_menu(event):
            set_treeview_selected_row(widget, event)
            return self.on_popup_likes_menu(widget)

        return False

    def on_popup_likes_menu(self, widget):

        item = self.get_selected_like_item(widget)
        if item is None:
            return False

        self.likes_popup_menu.set_user(item)

        items = self.likes_popup_menu.get_items()
        items[_("I _Like This")].set_active(item in self.frame.np.config.sections["interests"]["likes"])
        items[_("I _Dislike This")].set_active(item in self.frame.np.config.sections["interests"]["dislikes"])

        self.likes_popup_menu.popup()
        return True

    def on_hates_list_clicked(self, widget, event):

        if triggers_context_menu(event):
            set_treeview_selected_row(widget, event)
            return self.on_popup_hates_menu(widget)

        return False

    def on_popup_hates_menu(self, widget):

        item = self.get_selected_like_item(widget)
        if item is None:
            return False

        self.hates_popup_menu.set_user(item)

        items = self.hates_popup_menu.get_items()
        items[_("I _Like This")].set_active(item in self.frame.np.config.sections["interests"]["likes"])
        items[_("I _Dislike This")].set_active(item in self.frame.np.config.sections["interests"]["dislikes"])

        self.hates_popup_menu.popup()
        return True

    def update_visuals(self):

        for widget in self.__dict__.values():
            update_widget_visuals(widget)

    def show_interests(self, likes, hates):

        self.likes_store.clear()
        self.hates_store.clear()

        for like in likes:
            self.likes_store.append([like])

        for hate in hates:
            self.hates_store.append([hate])

    def save_columns(self):
        # Unused
        pass

    def load_picture(self, data):

        try:
            import gc
            import tempfile

            with tempfile.NamedTemporaryFile() as f:
                f.write(data)
                del data

                self.image_pixbuf = GdkPixbuf.Pixbuf.new_from_file(f.name)
                self.image.set_from_pixbuf(self.image_pixbuf)

            gc.collect()

            self.actual_zoom = 0
            self.SavePicture.set_sensitive(True)

        except Exception as e:
            log.add(_("Failed to load picture for user %(user)s: %(error)s") % {
                "user": self.user,
                "error": str(e)
            })

    def show_user(self, msg, *args):

        if msg is None:
            return

        self._descr = msg.descr
        self.image_pixbuf = None
        self.descr.get_buffer().set_text("")

        append_line(self.descr, msg.descr, self.tag_local, showstamp=False, scroll=False)

        self.uploads.set_text(_("Total uploads allowed: %i") % msg.totalupl)
        self.queuesize.set_text(_("Queue size: %i") % msg.queuesize)

        if msg.slotsavail:
            slots = _("Yes")
        else:
            slots = _("No")

        self.slotsavail.set_text(_("Slots free: %s") % slots)

        if msg.uploadallowed == 0:
            allowed = _("No one")
        elif msg.uploadallowed == 1:
            allowed = _("Everyone")
        elif msg.uploadallowed == 2:
            allowed = _("Users in list")
        elif msg.uploadallowed == 3:
            allowed = _("Trusted Users")
        else:
            allowed = _("unknown")

        self.AcceptUploads.set_text(_("%s") % allowed)

        if msg.has_pic and msg.pic is not None:
            self.load_picture(msg.pic)

        self.info_bar.set_visible(False)
        self.set_finished()

    def show_connection_error(self):

        self.info_bar.show_message(
            _("Unable to request information from user. Either you both have a closed listening port, the user is offline, or there's a temporary connectivity issue.")
        )

        self.set_finished()

    def set_finished(self):

        # Tab notification
        self.frame.request_tab_icon(self.frame.UserInfoTabLabel)
        self.userinfos.request_changed(self.Main)

        self.progressbar.set_fraction(1.0)

    def update_gauge(self, msg):

        if msg.total == 0 or msg.bytes == 0:
            fraction = 0.0
        elif msg.bytes >= msg.total:
            fraction = 1.0
        else:
            fraction = float(msg.bytes) / msg.total

        self.progressbar.set_fraction(fraction)

    def tab_popup(self, user):
        self.user_popup.toggle_user_items()
        return self.user_popup

    """ Events """

    def on_send_message(self, widget):
        self.frame.privatechats.send_message(self.user, show_user=True)
        self.frame.change_main_page("private")

    def on_show_ip_address(self, widget):

        self.frame.np.ip_requested.add(self.user)
        self.frame.np.queue.put(slskmessages.GetPeerAddress(self.user))

    def on_refresh(self, widget):
        self.info_bar.set_visible(False)
        self.progressbar.set_fraction(0.0)
        self.frame.local_user_info_request(self.user)

    def on_browse_user(self, widget):
        self.frame.browse_user(self.user)

    def on_add_to_list(self, widget):
        self.frame.np.userlist.add_to_list(self.user)

    def on_ban_user(self, widget):
        self.frame.ban_user(self.user)

    def on_ignore_user(self, widget):
        self.frame.ignore_user(self.user)

    def on_close(self, widget):
        del self.userinfos.users[self.user]
        self.userinfos.remove_page(self.Main)

    def on_save_picture(self, widget):

        if self.image is None or self.image_pixbuf is None:
            return

        response = save_file(
            self.frame.MainWindow,
            self.frame.np.config.sections["transfers"]["downloaddir"],
            "%s %s.jpg" % (self.user, time.strftime("%Y-%m-%d %H_%M_%S")),
            title="Save as..."
        )

        if not response:
            return

        pathname = response[0]

        if not os.path.exists(pathname):
            self.image_pixbuf.savev(pathname, "jpeg", ["quality"], ["100"])
            log.add(_("Picture saved to %s"), pathname)
        else:
            log.add(_("Picture not saved, %s already exists."), pathname)

    def on_image_click(self, widget, event):

        if triggers_context_menu(event):
            return self.on_image_popup_menu(widget)

        return False

    def on_image_popup_menu(self, widget):

        act = True

        if self.image is None or self.image_pixbuf is None:
            act = False

        items = self.image_menu.get_items()
        for (item_id, item) in items.items():
            item.set_sensitive(act)

        self.image_menu.popup()
        return True

    def on_scroll_event(self, widget, event):

        if event.get_scroll_deltas().delta_y < 0:
            self.make_zoom_in()
        else:
            self.make_zoom_out()

        return True  # Don't scroll the Gtk.ScrolledWindow

    def make_zoom_normal(self, widget):
        self.make_zoom_in(zoom=True)

    def make_zoom_in(self, widget=None, zoom=None):

        def calc_zoom_in(a):
            return a + a * self.actual_zoom / 100 + a * self.zoom_factor / 100

        import gc

        if self.image is None or self.image_pixbuf is None or self.actual_zoom > 100:
            return

        x = self.image_pixbuf.get_width()
        y = self.image_pixbuf.get_height()

        if zoom:
            self.actual_zoom = 0
        else:
            self.actual_zoom += self.zoom_factor

        pixbuf_zoomed = self.image_pixbuf.scale_simple(calc_zoom_in(x), calc_zoom_in(y), GdkPixbuf.InterpType.TILES)
        self.image.set_from_pixbuf(pixbuf_zoomed)

        del pixbuf_zoomed

        gc.collect()

    def make_zoom_out(self, widget=None):

        def calc_zoom_out(a):
            return a + a * self.actual_zoom / 100 - a * self.zoom_factor / 100

        import gc

        if self.image is None or self.image_pixbuf is None:
            return

        x = self.image_pixbuf.get_width()
        y = self.image_pixbuf.get_height()

        self.actual_zoom -= self.zoom_factor

        if calc_zoom_out(x) < 10 or calc_zoom_out(y) < 10:
            self.actual_zoom += self.zoom_factor
            return

        pixbuf_zoomed = self.image_pixbuf.scale_simple(calc_zoom_out(x), calc_zoom_out(y), GdkPixbuf.InterpType.TILES)
        self.image.set_from_pixbuf(pixbuf_zoomed)

        del pixbuf_zoomed

        gc.collect()
