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
from pynicotine.geoip.geoip import GeoIP
from pynicotine.gtkgui.widgets.filechooser import save_file
from pynicotine.gtkgui.widgets.iconnotebook import IconNotebook
from pynicotine.gtkgui.widgets.infobar import InfoBar
from pynicotine.gtkgui.widgets.popupmenu import PopupMenu
from pynicotine.gtkgui.widgets.textentry import CompletionEntry
from pynicotine.gtkgui.widgets.textview import TextView
from pynicotine.gtkgui.widgets.theme import update_widget_visuals
from pynicotine.gtkgui.widgets.treeview import initialise_columns
from pynicotine.gtkgui.widgets.ui import UserInterface
from pynicotine.logfacility import log
from pynicotine.utils import humanize
from pynicotine.utils import human_speed


class UserInfos(IconNotebook):

    def __init__(self, frame):

        IconNotebook.__init__(self, frame, frame.userinfo_notebook, "userinfo")
        self.notebook.connect("switch-page", self.on_switch_info_page)

        CompletionEntry(frame.UserInfoEntry, frame.UserInfoCombo.get_model())

    def on_switch_info_page(self, _notebook, page, _page_num):

        if self.frame.current_page_id != self.page_id:
            return

        for tab in self.pages.values():
            if tab.Main == page:
                GLib.idle_add(lambda: tab.descr.grab_focus() == -1)  # pylint:disable=cell-var-from-loop
                break

    def show_user(self, user, switch_page=True):

        if user not in self.pages:
            self.pages[user] = page = UserInfo(self, user)
            self.append_page(page.Main, user, page.on_close, user=user)
            page.set_label(self.get_tab_label_inner(page.Main))

            if self.get_n_pages() > 0:
                self.frame.userinfo_status_page.hide()

        if switch_page:
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

    def set_user_country(self, user, country_code):
        if user in self.pages:
            self.pages[user].set_user_country(country_code)

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


class UserInfo(UserInterface):

    def __init__(self, userinfos, user):

        super().__init__("ui/userinfo.ui")

        self.userinfos = userinfos
        self.frame = userinfos.frame

        self.info_bar = InfoBar(self.InfoBar, Gtk.MessageType.INFO)
        self.descr_textview = TextView(self.descr)

        if Gtk.get_major_version() == 4:
            self.picture = Gtk.Picture()
            self.picture.set_can_shrink(False)
            self.picture.set_halign(Gtk.Align.CENTER)
            self.picture.set_valign(Gtk.Align.CENTER)

            self.picture_view.set_child(self.picture)

            self.scroll_controller = Gtk.EventControllerScroll.new(Gtk.EventControllerScrollFlags.VERTICAL)
            self.scroll_controller.connect("scroll", self.on_scroll)
            self.picture_view.add_controller(self.scroll_controller)

        else:
            self.picture = Gtk.Image()
            self.picture.show()

            self.picture_view.add(self.picture)
            self.picture_view.connect("scroll-event", self.on_scroll_event)

        self.user = user
        self.conn = None
        self.picture_data = None
        self.zoom_factor = 5
        self.actual_zoom = 0

        # Set up likes list
        self.likes_store = Gtk.ListStore(str)

        self.like_column_numbers = list(range(self.likes_store.get_n_columns()))
        cols = initialise_columns(
            self.frame, None, self.Likes,
            ["likes", _("Likes"), 0, "text", None]
        )
        cols["likes"].set_sort_column_id(0)

        self.likes_store.set_sort_column_id(0, Gtk.SortType.ASCENDING)
        self.Likes.set_model(self.likes_store)

        # Set up dislikes list
        self.hates_store = Gtk.ListStore(str)

        self.hate_column_numbers = list(range(self.hates_store.get_n_columns()))
        cols = initialise_columns(
            self.frame, None, self.Hates,
            ["dislikes", _("Dislikes"), 0, "text", None]
        )
        cols["dislikes"].set_sort_column_id(0)

        self.hates_store.set_sort_column_id(0, Gtk.SortType.ASCENDING)
        self.Hates.set_model(self.hates_store)

        # Popup menus
        self.user_popup = popup = PopupMenu(self.frame, None, self.on_tab_popup)
        popup.setup_user_menu(user, page="userinfo")
        popup.setup(
            ("", None),
            ("#" + _("Close All Tabs…"), self.on_close_all_tabs),
            ("#" + _("_Close Tab"), self.on_close)
        )

        def get_interest_items(popup):
            return (("$" + _("I _Like This"), self.on_like_recommendation, popup),
                    ("$" + _("I _Dislike This"), self.on_dislike_recommendation, popup),
                    ("", None),
                    ("#" + _("_Search for Item"), self.on_interest_recommend_search, popup))

        popup = PopupMenu(self.frame, self.Likes, self.on_popup_interest_menu)
        popup.setup(*get_interest_items(popup))

        popup = PopupMenu(self.frame, self.Hates, self.on_popup_interest_menu)
        popup.setup(*get_interest_items(popup))

        popup = PopupMenu(self.frame, self.picture_view, self.on_picture_popup_menu)
        popup.setup(
            ("#" + _("Zoom 1:1"), self.make_zoom_normal),
            ("#" + _("Zoom In"), self.make_zoom_in),
            ("#" + _("Zoom Out"), self.make_zoom_out),
            ("", None),
            ("#" + _("Save Picture"), self.on_save_picture)
        )

        self.update_visuals()

    def set_label(self, label):
        self.user_popup.set_parent(label)

    def save_columns(self):
        # Unused
        pass

    def update_visuals(self):

        for widget in list(self.__dict__.values()):
            update_widget_visuals(widget)

    """ General """

    def load_picture(self, data):

        if not data:
            self.picture.hide()
            return

        try:
            import gc
            import tempfile

            with tempfile.NamedTemporaryFile() as file_handle:
                file_handle.write(data)
                del data

                self.picture_data = GdkPixbuf.Pixbuf.new_from_file(file_handle.name)
                picture_width = self.picture_data.get_width()
                picture_height = self.picture_data.get_height()

                allocation = self.picture_view.get_allocation()
                max_width = allocation.width - 24
                max_height = allocation.height - 24

                # Resize picture to fit container
                ratio = min(max_width / picture_width, max_height / picture_height)
                self.picture_data = self.picture_data.scale_simple(
                    ratio * picture_width, ratio * picture_height, GdkPixbuf.InterpType.BILINEAR)

                if Gtk.get_major_version() == 4:
                    self.picture.set_pixbuf(self.picture_data)
                else:
                    self.picture.set_from_pixbuf(self.picture_data)

            gc.collect()

            self.actual_zoom = 0
            self.SavePicture.set_sensitive(True)

            self.picture.show()

        except Exception as error:
            log.add(_("Failed to load picture for user %(user)s: %(error)s"), {
                "user": self.user,
                "error": error
            })

    def make_zoom_normal(self, *_args):
        self.make_zoom_in(zoom=True)

    def make_zoom_in(self, *_args, zoom=None):

        def calc_zoom_in(w_h):
            return w_h + w_h * self.actual_zoom / 100 + w_h * self.zoom_factor / 100

        import gc

        if self.picture is None or self.picture_data is None or self.actual_zoom > 100:
            return

        width = self.picture_data.get_width()
        height = self.picture_data.get_height()

        if zoom:
            self.actual_zoom = 0
            picture_zoomed = self.picture_data

        else:
            self.actual_zoom += self.zoom_factor
            picture_zoomed = self.picture_data.scale_simple(
                calc_zoom_in(width), calc_zoom_in(height), GdkPixbuf.InterpType.BILINEAR)

        if Gtk.get_major_version() == 4:
            self.picture.set_pixbuf(picture_zoomed)
        else:
            self.picture.set_from_pixbuf(picture_zoomed)

        del picture_zoomed
        gc.collect()

    def make_zoom_out(self, *_args):

        def calc_zoom_out(w_h):
            return w_h + w_h * self.actual_zoom / 100 - w_h * self.zoom_factor / 100

        import gc

        if self.picture is None or self.picture_data is None:
            return

        width = self.picture_data.get_width()
        height = self.picture_data.get_height()

        self.actual_zoom -= self.zoom_factor

        if calc_zoom_out(width) < 10 or calc_zoom_out(height) < 10:
            self.actual_zoom += self.zoom_factor
            return

        picture_zoomed = self.picture_data.scale_simple(
            calc_zoom_out(width), calc_zoom_out(height), GdkPixbuf.InterpType.BILINEAR)

        if Gtk.get_major_version() == 4:
            self.picture.set_pixbuf(picture_zoomed)
        else:
            self.picture.set_from_pixbuf(picture_zoomed)

        del picture_zoomed
        gc.collect()

    def show_connection_error(self):

        self.info_bar.show_message(
            _("Unable to request information from user. Either you both have a closed listening "
              "port, the user is offline, or there's a temporary connectivity issue.")
        )

        self.set_finished()

    def set_finished(self):
        self.userinfos.request_tab_hilite(self.Main)
        self.progressbar.set_fraction(1.0)

    def update_gauge(self, msg):

        if msg.total == 0 or msg.bufferlen == 0:
            fraction = 0.0
        elif msg.bufferlen >= msg.total:
            fraction = 1.0
        else:
            fraction = float(msg.bufferlen) / msg.total

        self.progressbar.set_fraction(fraction)

    """ Network Messages """

    def user_info_reply(self, msg):

        if msg is None:
            return

        self.descr_textview.clear()
        self.descr_textview.append_line(msg.descr, showstamp=False, scroll=False)

        self.uploads.set_text(humanize(msg.totalupl))
        self.queuesize.set_text(humanize(msg.queuesize))
        self.slotsavail.set_text(_("Yes") if msg.slotsavail else _("No"))

        self.picture_data = None
        self.load_picture(msg.pic)

        self.info_bar.set_visible(False)
        self.set_finished()

    def get_user_stats(self, msg):

        if msg.avgspeed > 0:
            self.speed.set_text(human_speed(msg.avgspeed))

        self.filesshared.set_text(humanize(msg.files))
        self.dirsshared.set_text(humanize(msg.dirs))

    def set_user_country(self, country_code):

        if country_code:
            country = GeoIP.country_code_to_name(country_code)
            country_text = "%s (%s)" % (country, country_code)
        else:
            country_text = _("Unknown")

        self.country.set_text(country_text)

    def user_interests(self, msg):

        self.likes_store.clear()
        self.hates_store.clear()

        for like in msg.likes:
            self.likes_store.insert_with_valuesv(-1, self.like_column_numbers, [like])

        for hate in msg.hates:
            self.hates_store.insert_with_valuesv(-1, self.hate_column_numbers, [hate])

    """ Callbacks """

    def on_tab_popup(self, *_args):
        self.user_popup.toggle_user_items()

    @staticmethod
    def on_popup_interest_menu(menu, widget):

        model, iterator = widget.get_selection().get_selected()
        item = model.get_value(iterator, 0)
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

    def on_interest_recommend_search(self, _action, _state, popup):
        self.frame.interests.recommend_search(popup.get_user())

    def on_send_message(self, *_args):
        self.frame.np.privatechats.show_user(self.user)
        self.frame.change_main_page("private")

    def on_show_ip_address(self, *_args):
        self.frame.np.request_ip_address(self.user)

    def on_browse_user(self, *_args):
        self.frame.np.userbrowse.browse_user(self.user)

    def on_add_to_list(self, *_args):
        self.frame.np.userlist.add_user(self.user)

    def on_ban_user(self, *_args):
        self.frame.np.network_filter.ban_user(self.user)

    def on_ignore_user(self, *_args):
        self.frame.np.network_filter.ignore_user(self.user)

    def on_save_picture_response(self, selected, _data):

        if not os.path.exists(selected):
            self.picture_data.savev(selected, "jpeg", ["quality"], ["100"])
            log.add(_("Picture saved to %s"), selected)
        else:
            log.add(_("Picture not saved, %s already exists."), selected)

    def on_save_picture(self, *_args):

        if self.picture is None or self.picture_data is None:
            return

        save_file(
            parent=self.frame.MainWindow,
            callback=self.on_save_picture_response,
            initialdir=config.sections["transfers"]["downloaddir"],
            initialfile="%s %s.jpg" % (self.user, time.strftime("%Y-%m-%d %H_%M_%S")),
            title=_("Save as…")
        )

    def on_picture_popup_menu(self, menu, _widget):
        for action in menu.get_actions().values():
            action.set_enabled(self.picture is not None and self.picture_data is not None)

    def on_scroll(self, _controller, _scroll_x, scroll_y):

        if scroll_y < 0:
            self.make_zoom_in()
        else:
            self.make_zoom_out()

        return True

    def on_scroll_event(self, _widget, event):

        if event.get_scroll_deltas().delta_y < 0:
            self.make_zoom_in()
        else:
            self.make_zoom_out()

        return True

    def on_refresh(self, *_args):

        self.info_bar.set_visible(False)
        self.progressbar.set_fraction(0.0)

        self.frame.np.userinfo.request_user_info(self.user)

    def on_close(self, *_args):

        del self.userinfos.pages[self.user]
        self.frame.np.userinfo.remove_user(self.user)
        self.userinfos.remove_page(self.Main)

        if self.userinfos.get_n_pages() == 0:
            self.frame.userinfo_status_page.show()

    def on_close_all_tabs(self, *_args):
        self.userinfos.remove_all_pages()
