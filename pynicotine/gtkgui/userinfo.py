# COPYRIGHT (C) 2020-2022 Nicotine+ Contributors
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

import time

from gi.repository import Gdk
from gi.repository import GdkPixbuf
from gi.repository import Gio
from gi.repository import GLib
from gi.repository import Gtk

from pynicotine.config import config
from pynicotine.geoip.geoip import GeoIP
from pynicotine.gtkgui.application import GTK_API_VERSION
from pynicotine.gtkgui.widgets.filechooser import FileChooserSave
from pynicotine.gtkgui.widgets.iconnotebook import IconNotebook
from pynicotine.gtkgui.widgets.infobar import InfoBar
from pynicotine.gtkgui.widgets.popupmenu import PopupMenu
from pynicotine.gtkgui.widgets.popupmenu import UserPopupMenu
from pynicotine.gtkgui.widgets.textview import TextView
from pynicotine.gtkgui.widgets.theme import get_flag_icon_name
from pynicotine.gtkgui.widgets.theme import update_widget_visuals
from pynicotine.gtkgui.widgets.treeview import initialise_columns
from pynicotine.gtkgui.widgets.ui import UserInterface
from pynicotine.logfacility import log
from pynicotine.slskmessages import UserStatus
from pynicotine.utils import humanize
from pynicotine.utils import human_speed


class UserInfos(IconNotebook):

    def __init__(self, frame, core):

        super().__init__(
            frame, core,
            widget=frame.userinfo_notebook,
            parent_page=frame.userinfo_page,
            switch_page_callback=self.on_switch_info_page
        )

    def on_switch_info_page(self, _notebook, page, _page_num):

        if self.frame.current_page_id != self.frame.userinfo_page.id:
            return

        for tab in self.pages.values():
            if tab.container == page:
                GLib.idle_add(lambda tab: tab.description_view.textview.grab_focus() == -1, tab)
                break

    def on_get_user_info(self, *_args):

        username = self.frame.userinfo_entry.get_text().strip()

        if not username:
            return

        self.frame.userinfo_entry.set_text("")
        self.core.userinfo.request_user_info(username)

    def show_user(self, user, switch_page=True):

        if user not in self.pages:
            self.pages[user] = page = UserInfo(self, user)
            self.append_page(page.container, user, page.on_close, user=user)
            page.set_label(self.get_tab_label_inner(page.container))

        if switch_page:
            self.set_current_page(self.pages[user].container)
            self.frame.change_main_page(self.frame.userinfo_page)

    def remove_user(self, user):

        page = self.pages.get(user)

        if page is None:
            return

        page.clear()
        self.remove_page(page.container)
        del self.pages[user]

    def show_connection_error(self, user):
        if user in self.pages:
            self.pages[user].show_connection_error()

    def message_progress(self, msg):
        if msg.user in self.pages:
            self.pages[msg.user].message_progress(msg)

    def get_user_stats(self, msg):
        if msg.user in self.pages:
            self.pages[msg.user].get_user_stats(msg)

    def get_user_status(self, msg):

        if msg.user in self.pages:
            page = self.pages[msg.user]
            self.set_user_status(page.container, msg.user, msg.status)

    def set_user_country(self, user, country_code):
        if user in self.pages:
            self.pages[user].set_user_country(country_code)

    def user_interests(self, msg):
        if msg.user in self.pages:
            self.pages[msg.user].user_interests(msg)

    def user_info_reply(self, user, msg):
        if user in self.pages:
            self.pages[user].user_info_reply(msg)

    def update_visuals(self):
        for page in self.pages.values():
            page.update_visuals()

    def server_disconnect(self):
        for user, page in self.pages.items():
            self.set_user_status(page.container, user, UserStatus.OFFLINE)


class UserInfo(UserInterface):

    def __init__(self, userinfos, user):

        super().__init__("ui/userinfo.ui")
        (
            self.container,
            self.country_icon,
            self.country_label,
            self.description_view,
            self.dislikes_list_view,
            self.free_upload_slots_label,
            self.horizontal_paned,
            self.info_bar,
            self.likes_list_view,
            self.picture_container,
            self.picture_view,
            self.placeholder_picture,
            self.progress_bar,
            self.queued_uploads_label,
            self.refresh_button,
            self.retry_button,
            self.shared_files_label,
            self.shared_folders_label,
            self.upload_slots_label,
            self.upload_speed_label,
            self.user_label
        ) = self.widgets

        self.userinfos = userinfos
        self.frame = userinfos.frame
        self.core = userinfos.core

        self.info_bar = InfoBar(self.info_bar, button=self.retry_button)
        self.description_view = TextView(self.description_view)
        self.user_label.set_text(user)

        if GTK_API_VERSION >= 4:
            self.country_icon.set_pixel_size(21)

            self.picture = Gtk.Picture(can_shrink=False, halign=Gtk.Align.CENTER, valign=Gtk.Align.CENTER)
            self.scroll_controller = Gtk.EventControllerScroll(flags=Gtk.EventControllerScrollFlags.VERTICAL)
            self.scroll_controller.connect("scroll", self.on_scroll)
            self.picture_view.add_controller(self.scroll_controller)
        else:
            # Setting a pixel size of 21 results in a misaligned country flag
            self.country_icon.set_pixel_size(0)

            self.picture = Gtk.Image(visible=True)
            self.picture_view.connect("scroll-event", self.on_scroll_event)

        self.picture_view.set_property("child", self.picture)

        self.user = user
        self.picture_data_original = self.picture_data_scaled = None
        self.zoom_factor = 5
        self.actual_zoom = 0
        self.indeterminate_progress = True

        # Set up likes list
        self.likes_store = Gtk.ListStore(str)

        self.like_column_numbers = list(range(self.likes_store.get_n_columns()))
        cols = initialise_columns(
            self.frame, None, self.likes_list_view,
            ["likes", _("Likes"), 0, "text", None]
        )
        cols["likes"].set_sort_column_id(0)

        self.likes_store.set_sort_column_id(0, Gtk.SortType.ASCENDING)
        self.likes_list_view.set_model(self.likes_store)

        # Set up dislikes list
        self.dislikes_store = Gtk.ListStore(str)

        self.hate_column_numbers = list(range(self.dislikes_store.get_n_columns()))
        cols = initialise_columns(
            self.frame, None, self.dislikes_list_view,
            ["dislikes", _("Dislikes"), 0, "text", None]
        )
        cols["dislikes"].set_sort_column_id(0)

        self.dislikes_store.set_sort_column_id(0, Gtk.SortType.ASCENDING)
        self.dislikes_list_view.set_model(self.dislikes_store)

        # Popup menus
        self.user_popup = popup = UserPopupMenu(self.frame, None, self.on_tab_popup)
        popup.setup_user_menu(user, page="userinfo")
        popup.add_items(
            ("", None),
            ("#" + _("Close All Tabs…"), self.on_close_all_tabs),
            ("#" + _("_Close Tab"), self.on_close)
        )

        def get_interest_items(popup):
            return (("$" + _("I _Like This"), self.on_like_recommendation, popup),
                    ("$" + _("I _Dislike This"), self.on_dislike_recommendation, popup),
                    ("", None),
                    ("#" + _("_Search for Item"), self.on_interest_recommend_search, popup))

        popup = PopupMenu(self.frame, self.likes_list_view, self.on_popup_interest_menu)
        popup.add_items(*get_interest_items(popup))

        popup = PopupMenu(self.frame, self.dislikes_list_view, self.on_popup_interest_menu)
        popup.add_items(*get_interest_items(popup))

        popup = PopupMenu(self.frame, self.picture_view)
        popup.add_items(
            ("#" + _("Zoom 1:1"), self.make_zoom_normal),
            ("#" + _("Zoom In"), self.make_zoom_in),
            ("#" + _("Zoom Out"), self.make_zoom_out),
            ("", None),
            ("#" + _("Save Picture"), self.on_save_picture)
        )

        self.update_visuals()
        self.set_in_progress()

    def clear(self):

        self.description_view.clear()
        self.likes_store.clear()
        self.dislikes_store.clear()
        self.load_picture(None)

    def set_label(self, label):
        self.user_popup.set_parent(label)

    def save_columns(self):
        # Unused
        pass

    def update_visuals(self):
        for widget in self.__dict__.values():
            update_widget_visuals(widget)

    """ General """

    def set_pixbuf(self, pixbuf):

        if GTK_API_VERSION >= 4:
            self.picture.set_pixbuf(pixbuf)
        else:
            self.picture.set_from_pixbuf(pixbuf)

        del pixbuf

    def load_picture(self, data):

        if not data:
            if GTK_API_VERSION >= 4:
                self.picture.set_paintable(None)
            else:
                self.picture.clear()

            self.picture_data_original = self.picture_data_scaled = None
            self.placeholder_picture.show()
            return

        try:
            allocation = self.picture_container.get_allocation()
            max_width = allocation.width - 72
            max_height = allocation.height - 72

            # Keep the original picture size for saving to disk
            data_stream = Gio.MemoryInputStream.new_from_data(data, None)
            self.picture_data_original = GdkPixbuf.Pixbuf.new_from_stream(data_stream, cancellable=None)
            picture_width = self.picture_data_original.get_width()
            picture_height = self.picture_data_original.get_height()

            # Scale picture before displaying
            ratio = min(max_width / picture_width, max_height / picture_height)
            self.picture_data_scaled = self.picture_data_original.scale_simple(
                ratio * picture_width, ratio * picture_height, GdkPixbuf.InterpType.BILINEAR)
            self.set_pixbuf(self.picture_data_scaled)

            self.actual_zoom = 0
            self.picture_view.show()

        except Exception as error:
            log.add(_("Failed to load picture for user %(user)s: %(error)s"), {
                "user": self.user,
                "error": error
            })

    def make_zoom_normal(self, *_args):
        self.actual_zoom = 0
        self.set_pixbuf(self.picture_data_scaled)

    def make_zoom_in(self, *_args):

        def calc_zoom_in(w_h):
            return w_h + w_h * self.actual_zoom / 100 + w_h * self.zoom_factor / 100

        if self.picture_data_scaled is None or self.actual_zoom >= 100:
            return

        self.actual_zoom += self.zoom_factor
        width = calc_zoom_in(self.picture_data_scaled.get_width())
        height = calc_zoom_in(self.picture_data_scaled.get_height())

        picture_zoomed = self.picture_data_scaled.scale_simple(width, height, GdkPixbuf.InterpType.NEAREST)
        self.set_pixbuf(picture_zoomed)

    def make_zoom_out(self, *_args):

        def calc_zoom_out(w_h):
            return w_h + w_h * self.actual_zoom / 100 - w_h * self.zoom_factor / 100

        if self.picture_data_scaled is None:
            return

        self.actual_zoom -= self.zoom_factor
        width = calc_zoom_out(self.picture_data_scaled.get_width())
        height = calc_zoom_out(self.picture_data_scaled.get_height())

        if width < 42 or height < 42:
            self.actual_zoom += self.zoom_factor
            return

        picture_zoomed = self.picture_data_scaled.scale_simple(width, height, GdkPixbuf.InterpType.NEAREST)
        self.set_pixbuf(picture_zoomed)

    def show_connection_error(self):

        self.info_bar.show_message(
            _("Unable to request information from user. Either you both have a closed listening "
              "port, the user is offline, or there's a temporary connectivity issue."),
            message_type=Gtk.MessageType.ERROR
        )

        self.set_finished()

    def set_finished(self):

        self.indeterminate_progress = False

        self.userinfos.request_tab_hilite(self.container)
        self.progress_bar.set_fraction(1.0)

        self.refresh_button.set_sensitive(True)

    def pulse_progress(self, repeat=True):

        if not self.indeterminate_progress:
            return False

        self.progress_bar.pulse()
        return repeat

    def set_in_progress(self):

        self.indeterminate_progress = True

        self.progress_bar.pulse()
        GLib.timeout_add(320, self.pulse_progress, False)
        GLib.timeout_add(1000, self.pulse_progress)

        self.info_bar.set_visible(False)
        self.refresh_button.set_sensitive(False)

    def message_progress(self, msg):

        self.indeterminate_progress = False

        if msg.total == 0 or msg.position == 0:
            fraction = 0.0
        elif msg.position >= msg.total:
            fraction = 1.0
        else:
            fraction = float(msg.position) / msg.total

        self.progress_bar.set_fraction(fraction)

    """ Network Messages """

    def user_info_reply(self, msg):

        if msg is None:
            return

        if msg.descr:
            self.description_view.clear()
            self.description_view.append_line(msg.descr)

        self.upload_slots_label.set_text(humanize(msg.totalupl))
        self.queued_uploads_label.set_text(humanize(msg.queuesize))
        self.free_upload_slots_label.set_text(_("Yes") if msg.slotsavail else _("No"))

        self.picture_data_original = self.picture_data_scaled = None
        self.load_picture(msg.pic)

        self.info_bar.set_visible(False)
        self.set_finished()

    def get_user_stats(self, msg):

        if msg.avgspeed > 0:
            self.upload_speed_label.set_text(human_speed(msg.avgspeed))

        self.shared_files_label.set_text(humanize(msg.files))
        self.shared_folders_label.set_text(humanize(msg.dirs))

    def set_user_country(self, country_code):

        if not country_code:
            return

        country = GeoIP.country_code_to_name(country_code)
        country_text = "%s (%s)" % (country, country_code)

        self.country_label.set_text(country_text)

        icon_name = get_flag_icon_name(country_code or "")

        self.country_icon.set_property("icon-name", icon_name)
        self.country_icon.set_visible(bool(icon_name))

    def user_interests(self, msg):

        self.likes_store.clear()
        self.dislikes_store.clear()

        for like in msg.likes:
            self.likes_store.insert_with_valuesv(-1, self.like_column_numbers, [like])

        for hate in msg.hates:
            self.dislikes_store.insert_with_valuesv(-1, self.hate_column_numbers, [hate])

    """ Callbacks """

    def on_tab_popup(self, *_args):
        self.user_popup.toggle_user_items()

    def on_popup_interest_menu(self, menu, widget):

        item = self.frame.interests.get_selected_item(widget, column=0)

        menu.actions[_("I _Like This")].set_state(
            GLib.Variant("b", item in config.sections["interests"]["likes"])
        )
        menu.actions[_("I _Dislike This")].set_state(
            GLib.Variant("b", item in config.sections["interests"]["dislikes"])
        )

    def on_like_recommendation(self, action, state, popup):
        item = self.frame.interests.get_selected_item(popup.parent, column=0)
        self.frame.interests.on_like_recommendation(action, state, item)

    def on_dislike_recommendation(self, action, state, popup):
        item = self.frame.interests.get_selected_item(popup.parent, column=0)
        self.frame.interests.on_dislike_recommendation(action, state, item)

    def on_interest_recommend_search(self, _action, _state, popup):
        item = self.frame.interests.get_selected_item(popup.parent, column=0)
        self.frame.interests.recommend_search(item)

    def on_send_message(self, *_args):
        self.core.privatechats.show_user(self.user)
        self.frame.change_main_page(self.frame.private_page)

    def on_show_ip_address(self, *_args):
        self.core.request_ip_address(self.user)

    def on_browse_user(self, *_args):
        self.core.userbrowse.browse_user(self.user)

    def on_add_to_list(self, *_args):
        self.core.userlist.add_user(self.user)

    def on_ban_user(self, *_args):
        self.core.network_filter.ban_user(self.user)

    def on_ignore_user(self, *_args):
        self.core.network_filter.ignore_user(self.user)

    def on_save_picture_response(self, file_path, *_args):
        _success, picture_bytes = self.picture_data_original.save_to_bufferv(
            type="png", option_keys=[], option_values=[])
        self.core.userinfo.save_user_picture(file_path, picture_bytes)

    def on_save_picture(self, *_args):

        if self.picture_data_original is None:
            return

        FileChooserSave(
            parent=self.frame.window,
            callback=self.on_save_picture_response,
            initial_folder=config.sections["transfers"]["downloaddir"],
            initial_file="%s %s.png" % (self.user, time.strftime("%Y-%m-%d %H_%M_%S"))
        ).show()

    def on_scroll(self, _controller=None, _scroll_x=0, scroll_y=0):

        if scroll_y < 0:
            self.make_zoom_in()
        else:
            self.make_zoom_out()

        return True

    def on_scroll_event(self, _widget, event):

        if event.direction == Gdk.ScrollDirection.SMOOTH:
            return self.on_scroll(scroll_y=event.delta_y)

        if event.direction == Gdk.ScrollDirection.DOWN:
            self.make_zoom_out()

        elif event.direction == Gdk.ScrollDirection.UP:
            self.make_zoom_in()

        return True

    def on_refresh(self, *_args):
        self.set_in_progress()
        self.core.userinfo.request_user_info(self.user)

    def on_close(self, *_args):
        self.core.userinfo.remove_user(self.user)

    def on_close_all_tabs(self, *_args):
        self.userinfos.remove_all_pages()
