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
from gi.repository import GLib
from gi.repository import Gtk

from pynicotine.config import config
from pynicotine.gtkgui.utils import grab_widget_focus
from pynicotine.gtkgui.utils import load_ui_elements
from pynicotine.gtkgui.widgets.filechooser import save_file
from pynicotine.gtkgui.widgets.iconnotebook import IconNotebook
from pynicotine.gtkgui.widgets.infobar import InfoBar
from pynicotine.gtkgui.widgets.popupmenu import PopupMenu
from pynicotine.gtkgui.widgets.textview import append_line
from pynicotine.gtkgui.widgets.theme import update_widget_visuals
from pynicotine.gtkgui.widgets.treeview import initialise_columns
from pynicotine.logfacility import log
from pynicotine.utils import humanize
from pynicotine.utils import human_speed


class UserInfos(IconNotebook):

    def __init__(self, frame):

        self.frame = frame
        self.pages = {}

        IconNotebook.__init__(
            self,
            self.frame.images,
            tabclosers=config.sections["ui"]["tabclosers"],
            show_hilite_image=config.sections["notifications"]["notification_tab_icons"],
            show_status_image=config.sections["ui"]["tab_status_icons"],
            notebookraw=self.frame.UserInfoNotebookRaw
        )

        self.notebook.connect("switch-page", self.on_switch_info_page)

    def on_switch_info_page(self, notebook, page, page_num):

        for tab in self.pages.values():
            if tab.Main == page:
                GLib.idle_add(grab_widget_focus, tab.descr)
                break

    def show_user(self, user):

        if user not in self.pages:
            try:
                status = self.frame.np.users[user].status
            except Exception:
                # Offline
                status = 0

            self.pages[user] = page = UserInfo(self, user)
            self.append_page(page.Main, user, page.on_close, status=status)
            page.set_label(self.get_tab_label_inner(page.Main))

        self.set_current_page(self.page_num(self.pages[user].Main))
        self.frame.change_main_page("userinfo")

    def set_conn(self, user, conn):
        if user in self.pages:
            self.pages[user].conn = conn

    def show_connection_error(self, user):
        if user in self.pages:
            self.pages[user].show_connection_error()

    def get_user_stats(self, msg):
        if msg.user in self.pages:
            self.pages[msg.user].get_user_stats(msg)

    def get_user_status(self, msg):

        if msg.user in self.pages:
            page = self.pages[msg.user]
            self.set_user_status(page.Main, msg.user, msg.status)

    def user_interests(self, msg):
        if msg.user in self.pages:
            self.pages[msg.user].user_interests(msg)

    def user_info_reply(self, user, msg):
        if user in self.pages:
            self.pages[user].user_info_reply(msg)

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


class UserInfo:

    def __init__(self, userinfos, user):

        self.userinfos = userinfos
        self.frame = userinfos.frame

        # Build the window
        load_ui_elements(self, os.path.join(self.frame.gui_dir, "ui", "userinfo.ui"))
        self.info_bar = InfoBar(self.InfoBar, Gtk.MessageType.INFO)

        try:
            if Gtk.get_major_version() == 4:
                args = (Gtk.EventControllerScrollFlags.VERTICAL,)
            else:
                args = (self.ImageViewport, Gtk.EventControllerScrollFlags.VERTICAL)

            self.scroll_controller = Gtk.EventControllerScroll.new(*args)
            self.scroll_controller.connect("scroll", self.on_scroll)

        except AttributeError:
            # GTK <3.24
            self.ImageViewport.connect("scroll-event", self.on_scroll_event)

        if Gtk.get_major_version() == 4:
            self.image = Gtk.Picture()
            self.image.set_can_shrink(False)
            self.image.set_halign(Gtk.Align.CENTER)
            self.image.set_valign(Gtk.Align.CENTER)

            self.ImageViewport.set_child(self.image)
            self.ImageViewport.add_controller(self.scroll_controller)

        else:
            self.image = Gtk.Image()
            self.image.show()

            self.ImageViewport.add(self.image)

        self.user = user
        self.conn = None
        self.image_pixbuf = None
        self.zoom_factor = 5
        self.actual_zoom = 0

        self.hates_store = Gtk.ListStore(str)
        self.Hates.set_model(self.hates_store)

        self.hate_column_numbers = list(range(self.hates_store.get_n_columns()))
        cols = initialise_columns(
            None, self.Hates,
            ["hates", _("Hates"), 0, "text", None]
        )
        cols["hates"].set_sort_column_id(0)

        self.hates_store.set_sort_column_id(0, Gtk.SortType.ASCENDING)

        self.likes_store = Gtk.ListStore(str)
        self.Likes.set_model(self.likes_store)

        self.like_column_numbers = list(range(self.likes_store.get_n_columns()))
        cols = initialise_columns(
            None, self.Likes,
            ["likes", _("Likes"), 0, "text", None]
        )
        cols["likes"].set_sort_column_id(0)

        self.likes_store.set_sort_column_id(0, Gtk.SortType.ASCENDING)

        self.update_visuals()

        self.user_popup = popup = PopupMenu(self.frame, None, self.on_tab_popup)
        popup.setup_user_menu(user, page="userinfo")
        popup.setup(
            ("", None),
            ("#" + _("Close All Tabs..."), self.on_close_all_tabs),
            ("#" + _("_Close Tab"), self.on_close)
        )

        def get_interest_items(popup):
            return (("$" + _("I _Like This"), self.on_like_recommendation, popup),
                    ("$" + _("I _Dislike This"), self.on_dislike_recommendation, popup),
                    ("", None),
                    ("#" + _("_Search for Item"), self.on_interest_recommend_search, popup))

        self.likes_popup_menu = popup = PopupMenu(self.frame, self.Likes, self.on_popup_interest_menu)
        popup.setup(*get_interest_items(popup))

        self.hates_popup_menu = popup = PopupMenu(self.frame, self.Hates, self.on_popup_interest_menu)
        popup.setup(*get_interest_items(popup))

        self.image_menu = popup = PopupMenu(self.frame, self.ImageViewport, self.on_image_popup_menu)
        popup.setup(
            ("#" + _("Zoom 1:1"), self.make_zoom_normal),
            ("#" + _("Zoom In"), self.make_zoom_in),
            ("#" + _("Zoom Out"), self.make_zoom_out),
            ("", None),
            ("#" + _("Save Picture"), self.on_save_picture)
        )

    def set_label(self, label):
        self.user_popup.set_widget(label)

    def update_visuals(self):

        for widget in list(self.__dict__.values()):
            update_widget_visuals(widget)

    def user_interests(self, msg):

        self.likes_store.clear()
        self.hates_store.clear()

        for like in msg.likes:
            self.likes_store.insert_with_valuesv(-1, self.like_column_numbers, [like])

        for hate in msg.hates:
            self.hates_store.insert_with_valuesv(-1, self.hate_column_numbers, [hate])

    def save_columns(self):
        # Unused
        pass

    def load_picture(self, data):

        if data is None:
            self.image.hide()
            return

        try:
            import gc
            import tempfile

            with tempfile.NamedTemporaryFile() as f:
                f.write(data)
                del data

                self.image_pixbuf = pixbuf = GdkPixbuf.Pixbuf.new_from_file(f.name)
                image_width = self.image_pixbuf.get_width()
                image_height = self.image_pixbuf.get_height()

                allocation = self.ImageViewport.get_allocation()
                max_width = allocation.width - 24
                max_height = allocation.height - 24

                # Resize pixbuf to fit container
                ratio = min(max_width / image_width, max_height / image_height)
                pixbuf = self.image_pixbuf.scale_simple(
                    ratio * image_width, ratio * image_height, GdkPixbuf.InterpType.BILINEAR)

                if Gtk.get_major_version() == 4:
                    self.image.set_pixbuf(pixbuf)
                else:
                    self.image.set_from_pixbuf(pixbuf)

            gc.collect()

            self.actual_zoom = 0
            self.SavePicture.set_sensitive(True)

            self.image.show()

        except Exception as e:
            log.add(_("Failed to load picture for user %(user)s: %(error)s"), {
                "user": self.user,
                "error": str(e)
            })

    def get_user_stats(self, msg):

        if msg.avgspeed > 0:
            self.speed.set_text(human_speed(msg.avgspeed))

        self.filesshared.set_text(humanize(msg.files))
        self.dirsshared.set_text(humanize(msg.dirs))

    def show_connection_error(self):

        self.info_bar.show_message(
            _("Unable to request information from user. Either you both have a closed listening "
              "port, the user is offline, or there's a temporary connectivity issue.")
        )

        self.set_finished()

    def set_finished(self):

        # Tab notification
        self.frame.request_tab_icon(self.frame.UserInfoTabLabel)
        self.userinfos.request_changed(self.Main)

        self.progressbar.set_fraction(1.0)

    def user_info_reply(self, msg):

        if msg is None:
            return

        self.descr.get_buffer().set_text("")
        append_line(self.descr, msg.descr, showstamp=False, scroll=False)

        self.uploads.set_text(humanize(msg.totalupl))
        self.queuesize.set_text(humanize(msg.queuesize))
        self.slotsavail.set_text(_("Yes") if msg.slotsavail else _("No"))

        self.image_pixbuf = None
        self.load_picture(msg.pic)

        self.info_bar.set_visible(False)
        self.set_finished()

    def update_gauge(self, msg):

        if msg.total == 0 or msg.bufferlen == 0:
            fraction = 0.0
        elif msg.bufferlen >= msg.total:
            fraction = 1.0
        else:
            fraction = float(msg.bufferlen) / msg.total

        self.progressbar.set_fraction(fraction)

    """ Events """

    def on_tab_popup(self, *args):
        self.user_popup.toggle_user_items()

    def on_popup_interest_menu(self, menu, widget):

        model, iterator = widget.get_selection().get_selected()

        if iterator is None:
            return True

        item = model.get_value(iterator, 0)

        if item is None:
            return True

        menu.set_user(item)

        actions = menu.get_actions()
        actions[_("I _Like This")].set_state(
            GLib.Variant.new_boolean(item in config.sections["interests"]["likes"])
        )
        actions[_("I _Dislike This")].set_state(
            GLib.Variant.new_boolean(item in config.sections["interests"]["dislikes"])
        )

    def on_like_recommendation(self, action, state, popup):
        self.frame.interests.on_like_recommendation(action, state, popup.get_user())

    def on_dislike_recommendation(self, action, state, popup):
        self.frame.interests.on_dislike_recommendation(action, state, popup.get_user())

    def on_interest_recommend_search(self, action, state, popup):
        self.frame.interests.recommend_search(popup.get_user())

    def on_send_message(self, *args):
        self.frame.np.privatechats.show_user(self.user)
        self.frame.change_main_page("private")

    def on_show_ip_address(self, *args):
        self.frame.np.request_ip_address(self.user)

    def on_refresh(self, *args):

        self.info_bar.set_visible(False)
        self.progressbar.set_fraction(0.0)

        self.frame.np.userinfo.request_user_info(self.user)

    def on_browse_user(self, *args):
        self.frame.np.userbrowse.browse_user(self.user)

    def on_add_to_list(self, *args):
        self.frame.np.userlist.add_user(self.user)

    def on_ban_user(self, *args):
        self.frame.np.network_filter.ban_user(self.user)

    def on_ignore_user(self, *args):
        self.frame.np.network_filter.ignore_user(self.user)

    def on_save_picture_response(self, selected, data):

        if not os.path.exists(selected):
            self.image_pixbuf.savev(selected, "jpeg", ["quality"], ["100"])
            log.add(_("Picture saved to %s"), selected)
        else:
            log.add(_("Picture not saved, %s already exists."), selected)

    def on_save_picture(self, *args):

        if self.image is None or self.image_pixbuf is None:
            return

        save_file(
            parent=self.frame.MainWindow,
            callback=self.on_save_picture_response,
            initialdir=config.sections["transfers"]["downloaddir"],
            initialfile="%s %s.jpg" % (self.user, time.strftime("%Y-%m-%d %H_%M_%S")),
            title=_("Save as...")
        )

    def on_image_popup_menu(self, menu, widget):

        act = True

        if self.image is None or self.image_pixbuf is None:
            act = False

        actions = menu.get_actions()
        for (action_id, action) in actions.items():
            action.set_enabled(act)

    def on_scroll(self, controller, x, y):

        if y < 0:
            self.make_zoom_in()
        else:
            self.make_zoom_out()

    def on_scroll_event(self, widget, event):

        if event.get_scroll_deltas().delta_y < 0:
            self.make_zoom_in()
        else:
            self.make_zoom_out()

        return True  # Don't scroll the Gtk.ScrolledWindow

    def make_zoom_normal(self, *args):
        self.make_zoom_in(zoom=True)

    def make_zoom_in(self, *args, zoom=None):

        def calc_zoom_in(a):
            return a + a * self.actual_zoom / 100 + a * self.zoom_factor / 100

        import gc

        if self.image is None or self.image_pixbuf is None or self.actual_zoom > 100:
            return

        x = self.image_pixbuf.get_width()
        y = self.image_pixbuf.get_height()

        if zoom:
            self.actual_zoom = 0
            pixbuf_zoomed = self.image_pixbuf

        else:
            self.actual_zoom += self.zoom_factor
            pixbuf_zoomed = self.image_pixbuf.scale_simple(
                calc_zoom_in(x), calc_zoom_in(y), GdkPixbuf.InterpType.BILINEAR)

        if Gtk.get_major_version() == 4:
            self.image.set_pixbuf(pixbuf_zoomed)
        else:
            self.image.set_from_pixbuf(pixbuf_zoomed)

        del pixbuf_zoomed

        gc.collect()

    def make_zoom_out(self, *args):

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

        pixbuf_zoomed = self.image_pixbuf.scale_simple(
            calc_zoom_out(x), calc_zoom_out(y), GdkPixbuf.InterpType.BILINEAR)

        if Gtk.get_major_version() == 4:
            self.image.set_pixbuf(pixbuf_zoomed)
        else:
            self.image.set_from_pixbuf(pixbuf_zoomed)

        del pixbuf_zoomed

        gc.collect()

    def on_close(self, *args):

        del self.userinfos.pages[self.user]
        self.frame.np.userinfo.remove_user(self.user)
        self.userinfos.remove_page(self.Main)

    def on_close_all_tabs(self, *args):
        self.userinfos.remove_all_pages()
