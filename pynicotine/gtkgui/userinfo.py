# COPYRIGHT (C) 2020-2022 Nicotine+ Contributors
# COPYRIGHT (C) 2016-2017 Michael Labouebe <gfarmerfr@free.fr>
# COPYRIGHT (C) 2008-2010 quinox <quinox@users.sf.net>
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

import time

from gi.repository import Gdk
from gi.repository import GdkPixbuf
from gi.repository import Gio
from gi.repository import GLib
from gi.repository import Gtk

from pynicotine.config import config
from pynicotine.core import core
from pynicotine.events import events
from pynicotine.gtkgui.application import GTK_API_VERSION
from pynicotine.gtkgui.widgets.filechooser import FileChooserSave
from pynicotine.gtkgui.widgets.iconnotebook import IconNotebook
from pynicotine.gtkgui.widgets.infobar import InfoBar
from pynicotine.gtkgui.widgets.popupmenu import PopupMenu
from pynicotine.gtkgui.widgets.popupmenu import UserPopupMenu
from pynicotine.gtkgui.widgets.textview import TextView
from pynicotine.gtkgui.widgets.theme import get_flag_icon_name
from pynicotine.gtkgui.widgets.theme import update_widget_visuals
from pynicotine.gtkgui.widgets.treeview import TreeView
from pynicotine.gtkgui.widgets.ui import UserInterface
from pynicotine.logfacility import log
from pynicotine.slskmessages import UserStatus
from pynicotine.utils import humanize
from pynicotine.utils import human_speed


class UserInfos(IconNotebook):

    def __init__(self, window):

        super().__init__(
            window,
            widget=window.userinfo_notebook,
            parent_page=window.userinfo_page
        )

        # Events
        for event_name, callback in (
            ("peer-connection-closed", self.peer_connection_error),
            ("peer-connection-error", self.peer_connection_error),
            ("server-disconnect", self.server_disconnect),
            ("user-country", self.user_country),
            ("user-info-progress", self.user_info_progress),
            ("user-info-remove-user", self.remove_user),
            ("user-info-response", self.user_info_response),
            ("user-info-show-user", self.show_user),
            ("user-interests", self.user_interests),
            ("user-stats", self.user_stats),
            ("user-status", self.user_status)
        ):
            events.connect(event_name, callback)

    def on_get_user_info(self, *_args):

        username = self.window.userinfo_entry.get_text().strip()

        if not username:
            return

        self.window.userinfo_entry.set_text("")
        core.userinfo.show_user(username)

    def show_user(self, user, switch_page=True, **_unused):

        if user not in self.pages:
            self.pages[user] = page = UserInfo(self, user)
            self.append_page(page.container, user, focus_callback=page.on_focus,
                             close_callback=page.on_close, user=user)
            page.set_label(self.get_tab_label_inner(page.container))

        if switch_page:
            self.set_current_page(self.pages[user].container)
            self.window.change_main_page(self.window.userinfo_page)

    def remove_user(self, user):

        page = self.pages.get(user)

        if page is None:
            return

        page.clear()
        self.remove_page(page.container)
        del self.pages[user]

    def peer_connection_error(self, msg):

        page = self.pages.get(msg.user)

        if page is not None:
            page.peer_connection_error()

    def user_stats(self, msg):

        page = self.pages.get(msg.user)

        if page is not None:
            page.user_stats(msg)

    def user_status(self, msg):

        page = self.pages.get(msg.user)

        if page is not None:
            self.set_user_status(page.container, msg.user, msg.status)

    def user_country(self, user, country_code):

        page = self.pages.get(user)

        if page is not None:
            page.user_country(country_code)

    def user_interests(self, msg):

        page = self.pages.get(msg.user)

        if page is not None:
            page.user_interests(msg)

    def user_info_progress(self, msg):

        page = self.pages.get(msg.user)

        if page is not None:
            page.user_info_progress(msg)

    def user_info_response(self, msg):

        page = self.pages.get(msg.init.target_user)

        if page is not None:
            page.user_info_response(msg)

    def update_visuals(self):
        for page in self.pages.values():
            page.update_visuals()

    def server_disconnect(self, _msg):
        for user, page in self.pages.items():
            self.set_user_status(page.container, user, UserStatus.OFFLINE)


class UserInfo:

    def __init__(self, userinfos, user):

        ui_template = UserInterface(scope=self, path="userinfo.ui")
        (
            self.container,
            self.country_icon,
            self.country_label,
            self.description_view,
            self.dislikes_list_container,
            self.free_upload_slots_label,
            self.horizontal_paned,
            self.info_bar,
            self.likes_list_container,
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
        ) = ui_template.widgets

        self.userinfos = userinfos
        self.window = userinfos.window

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
        self.likes_list_view = TreeView(
            self.window, parent=self.likes_list_container,
            columns=[
                {"column_id": "likes", "column_type": "text", "title": _("Likes"), "sort_column": 0,
                 "default_sort_column": "ascending"}
            ]
        )

        # Set up dislikes list
        self.dislikes_list_view = TreeView(
            self.window, parent=self.dislikes_list_container,
            columns=[
                {"column_id": "dislikes", "column_type": "text", "title": _("Dislikes"), "sort_column": 0,
                 "default_sort_column": "ascending"}
            ]
        )

        # Popup menus
        self.user_popup_menu = UserPopupMenu(self.window.application, None, self.on_tab_popup)
        self.user_popup_menu.setup_user_menu(user, page="userinfo")
        self.user_popup_menu.add_items(
            ("", None),
            ("#" + _("Close All Tabs…"), self.on_close_all_tabs),
            ("#" + _("_Close Tab"), self.on_close)
        )

        def get_interest_items(list_view):
            return (("$" + _("I _Like This"), self.window.interests.on_like_recommendation, list_view),
                    ("$" + _("I _Dislike This"), self.window.interests.on_dislike_recommendation, list_view),
                    ("", None),
                    ("#" + _("_Search for Item"), self.window.interests.on_recommend_search, list_view))

        self.likes_popup_menu = PopupMenu(self.window.application, self.likes_list_view.widget,
                                          self.on_popup_likes_menu)
        self.likes_popup_menu.add_items(*get_interest_items(self.likes_list_view))

        self.dislikes_popup_menu = PopupMenu(self.window.application, self.dislikes_list_view.widget,
                                             self.on_popup_dislikes_menu)
        self.dislikes_popup_menu.add_items(*get_interest_items(self.dislikes_list_view))

        self.picture_popup_menu = PopupMenu(self.window.application, self.picture_view)
        self.picture_popup_menu.add_items(
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
        self.likes_list_view.clear()
        self.dislikes_list_view.clear()
        self.load_picture(None)

        for menu in (self.user_popup_menu, self.likes_popup_menu, self.dislikes_popup_menu,
                     self.likes_list_view.column_menu, self.dislikes_list_view.column_menu, self.picture_popup_menu):
            menu.clear()

    def set_label(self, label):
        self.user_popup_menu.set_parent(label)

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

    def peer_connection_error(self):

        if self.refresh_button.get_sensitive():
            return

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

    def user_info_progress(self, msg):

        self.indeterminate_progress = False

        if msg.total == 0 or msg.position == 0:
            fraction = 0.0
        elif msg.position >= msg.total:
            fraction = 1.0
        else:
            fraction = float(msg.position) / msg.total

        self.progress_bar.set_fraction(fraction)

    """ Network Messages """

    def user_info_response(self, msg):

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

    def user_stats(self, msg):

        if msg.avgspeed > 0:
            self.upload_speed_label.set_text(human_speed(msg.avgspeed))

        self.shared_files_label.set_text(humanize(msg.files))
        self.shared_folders_label.set_text(humanize(msg.dirs))

    def user_country(self, country_code):

        if not country_code:
            return

        country = core.geoip.country_code_to_name(country_code)
        country_text = "%s (%s)" % (country, country_code)

        self.country_label.set_text(country_text)

        icon_name = get_flag_icon_name(country_code or "")

        self.country_icon.set_property("icon-name", icon_name)
        self.country_icon.set_visible(bool(icon_name))

    def user_interests(self, msg):

        self.likes_list_view.clear()
        self.dislikes_list_view.clear()

        for like in msg.likes:
            self.likes_list_view.add_row([like], select_row=False)

        for hate in msg.hates:
            self.dislikes_list_view.add_row([hate], select_row=False)

    """ Callbacks """

    def on_tab_popup(self, *_args):
        self.user_popup_menu.toggle_user_items()

    def on_popup_likes_menu(self, menu, *_args):
        self.window.interests.toggle_menu_items(menu, self.likes_list_view, column=0)

    def on_popup_dislikes_menu(self, menu, *_args):
        self.window.interests.toggle_menu_items(menu, self.dislikes_list_view, column=0)

    def on_send_message(self, *_args):
        core.privatechat.show_user(self.user)

    def on_show_ip_address(self, *_args):
        core.request_ip_address(self.user)

    def on_browse_user(self, *_args):
        core.userbrowse.browse_user(self.user)

    def on_add_to_list(self, *_args):
        core.userlist.add_buddy(self.user)

    def on_ban_user(self, *_args):
        core.network_filter.ban_user(self.user)

    def on_ignore_user(self, *_args):
        core.network_filter.ignore_user(self.user)

    def on_save_picture_response(self, file_path, *_args):
        _success, picture_bytes = self.picture_data_original.save_to_bufferv(
            type="png", option_keys=[], option_values=[])
        core.userinfo.save_user_picture(file_path, picture_bytes)

    def on_save_picture(self, *_args):

        if self.picture_data_original is None:
            return

        FileChooserSave(
            parent=self.window,
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
        core.userinfo.show_user(self.user, refresh=True)

    def on_focus(self, *_args):
        self.description_view.textview.grab_focus()

    def on_close(self, *_args):
        core.userinfo.remove_user(self.user)

    def on_close_all_tabs(self, *_args):
        self.userinfos.remove_all_pages()
