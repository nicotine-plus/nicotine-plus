# COPYRIGHT (C) 2020-2023 Nicotine+ Contributors
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
from pynicotine.gtkgui.widgets import clipboard
from pynicotine.gtkgui.widgets import ui
from pynicotine.gtkgui.widgets.filechooser import FileChooserSave
from pynicotine.gtkgui.widgets.iconnotebook import IconNotebook
from pynicotine.gtkgui.widgets.popupmenu import PopupMenu
from pynicotine.gtkgui.widgets.popupmenu import UserPopupMenu
from pynicotine.gtkgui.widgets.textentry import ComboBox
from pynicotine.gtkgui.widgets.textview import TextView
from pynicotine.gtkgui.widgets.theme import get_flag_icon_name
from pynicotine.gtkgui.widgets.treeview import TreeView
from pynicotine.logfacility import log
from pynicotine.slskmessages import UserStatus
from pynicotine.utils import humanize
from pynicotine.utils import human_speed


class UserInfos(IconNotebook):

    def __init__(self, window):

        super().__init__(
            window,
            parent=window.userinfo_content,
            parent_page=window.userinfo_page
        )

        self.userinfo_combobox = ComboBox(
            container=self.window.userinfo_title, has_entry=True, has_entry_completion=True,
            entry=self.window.userinfo_entry
        )

        # Events
        for event_name, callback in (
            ("add-buddy", self.add_remove_buddy),
            ("ban-user", self.ban_unban_user),
            ("ignore-user", self.ignore_unignore_user),
            ("peer-connection-closed", self.peer_connection_error),
            ("peer-connection-error", self.peer_connection_error),
            ("remove-buddy", self.add_remove_buddy),
            ("server-disconnect", self.server_disconnect),
            ("unban-user", self.ban_unban_user),
            ("unignore-user", self.ignore_unignore_user),
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

    def on_remove_all_pages(self, *_args):
        core.userinfo.remove_all_users()

    def on_restore_removed_page(self, page_args):
        username, = page_args
        core.userinfo.show_user(username)

    def on_show_user_profile(self, *_args):

        username = self.window.userinfo_entry.get_text().strip()

        if not username:
            return

        self.window.userinfo_entry.set_text("")
        core.userinfo.show_user(username)

    def show_user(self, user, refresh=False, switch_page=True):

        page = self.pages.get(user)

        if page is None:
            refresh = True
            self.pages[user] = page = UserInfo(self, user)

            self.append_page(page.container, user, focus_callback=page.on_focus,
                             close_callback=page.on_close, user=user)
            page.set_label(self.get_tab_label_inner(page.container))

        if refresh:
            page.update_button_states()
            page.set_in_progress()

        if switch_page:
            self.set_current_page(page.container)
            self.window.change_main_page(self.window.userinfo_page)

    def remove_user(self, user):

        page = self.pages.get(user)

        if page is None:
            return

        page.clear()
        self.remove_page(page.container, page_args=(user,))
        del self.pages[user]

    def ban_unban_user(self, user):

        page = self.pages.get(user)

        if page is not None:
            page.update_ban_button_state()

    def ignore_unignore_user(self, user):

        page = self.pages.get(user)

        if page is not None:
            page.update_ignore_button_state()

    def add_remove_buddy(self, user, *_args):

        page = self.pages.get(user)

        if page is not None:
            page.update_buddy_button_state()

    def peer_connection_error(self, user, *_args, **_kwargs):

        page = self.pages.get(user)

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

    def user_info_progress(self, user, position, total):

        page = self.pages.get(user)

        if page is not None:
            page.user_info_progress(position, total)

    def user_info_response(self, msg):

        page = self.pages.get(msg.init.target_user)

        if page is not None:
            page.user_info_response(msg)

    def server_disconnect(self, *_args):
        for user, page in self.pages.items():
            self.set_user_status(page.container, user, UserStatus.OFFLINE)


class UserInfo:

    def __init__(self, userinfos, user):

        (
            self.add_remove_buddy_label,
            self.ban_unban_user_label,
            self.container,
            self.country_icon,
            self.country_label,
            self.description_view_container,
            self.dislikes_list_container,
            self.edit_interests_button,
            self.edit_profile_button,
            self.free_upload_slots_label,
            self.horizontal_paned,
            self.ignore_unignore_user_label,
            self.info_bar,
            self.info_bar_label,
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
        ) = ui.load(scope=self, path="userinfo.ui")

        self.userinfos = userinfos
        self.window = userinfos.window

        self.description_view = TextView(self.description_view_container, editable=False, vertical_margin=5)
        self.user_label.set_text(user)

        if GTK_API_VERSION >= 4:
            self.country_icon.set_pixel_size(21)
            self.picture = Gtk.Picture(can_shrink=True, content_fit=Gtk.ContentFit.CONTAIN, hexpand=True, vexpand=True)
            self.picture_view.append(self.picture)  # pylint: disable=no-member
        else:
            # Setting a pixel size of 21 results in a misaligned country flag
            self.country_icon.set_pixel_size(0)

            self.picture = Gtk.EventBox(hexpand=True, vexpand=True, visible=True)
            self.picture.connect("draw", self.on_draw_picture)

            self.picture_view.add(self.picture)    # pylint: disable=no-member

        self.user = user
        self.picture_data = None
        self.picture_surface = None
        self.indeterminate_progress = True

        # Set up likes list
        self.likes_list_view = TreeView(
            self.window, parent=self.likes_list_container,
            columns={
                "likes": {
                    "column_type": "text",
                    "title": _("Likes"),
                    "default_sort_type": "ascending"
                }
            }
        )

        # Set up dislikes list
        self.dislikes_list_view = TreeView(
            self.window, parent=self.dislikes_list_container,
            columns={
                "dislikes": {
                    "column_type": "text",
                    "title": _("Dislikes"),
                    "default_sort_type": "ascending"
                }
            }
        )

        # Popup menus
        self.user_popup_menu = UserPopupMenu(
            self.window.application, callback=self.on_tab_popup, username=user, tab_name="userinfo"
        )
        self.user_popup_menu.add_items(
            ("", None),
            ("#" + _("Close All Tabs…"), self.on_close_all_tabs),
            ("#" + _("_Close Tab"), self.on_close)
        )

        def get_interest_items(list_view, column_id):
            return (("$" + _("I _Like This"), self.window.interests.on_like_recommendation, list_view, column_id),
                    ("$" + _("I _Dislike This"), self.window.interests.on_dislike_recommendation, list_view, column_id),
                    ("", None),
                    ("#" + _("_Search for Item"), self.window.interests.on_recommend_search, list_view, column_id))

        self.likes_popup_menu = PopupMenu(self.window.application, self.likes_list_view.widget,
                                          self.on_popup_likes_menu)
        self.likes_popup_menu.add_items(*get_interest_items(self.likes_list_view, "likes"))

        self.dislikes_popup_menu = PopupMenu(self.window.application, self.dislikes_list_view.widget,
                                             self.on_popup_dislikes_menu)
        self.dislikes_popup_menu.add_items(*get_interest_items(self.dislikes_list_view, "dislikes"))

        self.picture_popup_menu = PopupMenu(self.window.application, self.picture)
        self.picture_popup_menu.add_items(
            ("#" + _("Copy Picture"), self.on_copy_picture),
            ("#" + _("Save Picture"), self.on_save_picture)
        )

        self.populate_stats()

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

    """ General """

    def populate_stats(self):

        user_stats = core.watched_users.get(self.user, {})
        speed = user_stats.get("upload_speed", 0)
        files = user_stats.get("files")
        folders = user_stats.get("folders")
        country_code = core.user_countries.get(self.user)

        if speed > 0:
            self.upload_speed_label.set_text(human_speed(speed))

        if files is not None:
            self.shared_files_label.set_text(humanize(files))

        if folders is not None:
            self.shared_folders_label.set_text(humanize(folders))

        if country_code:
            self.user_country(country_code)

    def load_picture(self, data):

        if not data:
            if GTK_API_VERSION >= 4:
                self.picture.set_paintable(None)

            self.picture_data = None
            self.placeholder_picture.set_visible(True)
            return

        try:
            if GTK_API_VERSION >= 4:
                self.picture_data = Gdk.Texture.new_from_bytes(GLib.Bytes(data))
                self.picture.set_paintable(self.picture_data)
            else:
                data_stream = Gio.MemoryInputStream.new_from_bytes(GLib.Bytes(data))
                self.picture_data = GdkPixbuf.Pixbuf.new_from_stream(data_stream, cancellable=None)
                self.picture_surface = Gdk.cairo_surface_create_from_pixbuf(self.picture_data, scale=1, for_window=None)

            self.picture_view.set_visible(True)

        except Exception as error:
            log.add(_("Failed to load picture for user %(user)s: %(error)s"), {
                "user": self.user,
                "error": error
            })

    def peer_connection_error(self):

        if self.refresh_button.get_sensitive():
            return

        self.info_bar_label.set_label(
            _("Unable to request information from user. Either you both have a closed listening "
              "port, the user is offline, or there's a temporary connectivity issue.")
        )
        self.info_bar.set_visible(True)
        self.info_bar.set_reveal_child(True)

        self.set_finished()

    def set_finished(self):

        self.indeterminate_progress = False

        self.userinfos.request_tab_changed(self.container)
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
        self.info_bar.set_reveal_child(False)
        self.refresh_button.set_sensitive(False)

    def user_info_progress(self, position, total):

        self.indeterminate_progress = False

        if total == 0 or position == 0:
            fraction = 0.0
        elif position >= total:
            fraction = 1.0
        else:
            fraction = float(position) / total

        self.progress_bar.set_fraction(fraction)

    """ Button States """

    def update_edit_button_state(self):

        is_personal_profile = (self.user == core.login_username)

        for widget in (self.edit_interests_button, self.edit_profile_button):
            widget.set_visible(is_personal_profile)

    def update_buddy_button_state(self):
        label = _("Remove _Buddy") if self.user in core.userlist.buddies else _("Add _Buddy")
        self.add_remove_buddy_label.set_text_with_mnemonic(label)

    def update_ban_button_state(self):
        label = _("Unban User") if core.network_filter.is_user_banned(self.user) else _("Ban User")
        self.ban_unban_user_label.set_text(label)

    def update_ignore_button_state(self):
        label = _("Unignore User") if core.network_filter.is_user_ignored(self.user) else _("Ignore User")
        self.ignore_unignore_user_label.set_text(label)

    def update_button_states(self):

        self.update_edit_button_state()
        self.update_buddy_button_state()
        self.update_ban_button_state()
        self.update_ignore_button_state()

    """ Network Messages """

    def user_info_response(self, msg):

        if msg is None:
            return

        if msg.descr is not None:
            self.description_view.clear()
            self.description_view.append_line(msg.descr)

        self.upload_slots_label.set_text(humanize(msg.totalupl))
        self.queued_uploads_label.set_text(humanize(msg.queuesize))
        self.free_upload_slots_label.set_text(_("Yes") if msg.slotsavail else _("No"))

        self.picture_data = None
        self.load_picture(msg.pic)

        self.info_bar.set_visible(False)
        self.info_bar.set_reveal_child(False)
        self.set_finished()

    def user_stats(self, msg):

        if msg.avgspeed > 0:
            self.upload_speed_label.set_text(human_speed(msg.avgspeed))

        self.shared_files_label.set_text(humanize(msg.files))
        self.shared_folders_label.set_text(humanize(msg.dirs))

    def user_country(self, country_code):

        if not country_code:
            return

        country_name = core.network_filter.COUNTRIES.get(country_code, _("Unknown"))
        country_text = f"{country_name} ({country_code})"

        self.country_label.set_text(country_text)

        icon_name = get_flag_icon_name(country_code)

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

    def on_draw_picture(self, area, context):
        """ Draws a centered picture that fills the drawing area """

        area_width = area.get_allocated_width()
        area_height = area.get_allocated_height()
        picture_width = self.picture_surface.get_width()
        picture_height = self.picture_surface.get_height()

        scale_factor = min(area_width / picture_width, area_height / picture_height)
        translate_x = (area_width - (picture_width * scale_factor)) / 2
        translate_y = (area_height - (picture_height * scale_factor)) / 2

        context.translate(translate_x, translate_y)
        context.scale(scale_factor, scale_factor)
        context.set_source_surface(self.picture_surface, 0, 0)
        context.paint()

    def on_tab_popup(self, *_args):
        self.user_popup_menu.toggle_user_items()

    def on_popup_likes_menu(self, menu, *_args):
        self.window.interests.toggle_menu_items(menu, self.likes_list_view, column_id="likes")

    def on_popup_dislikes_menu(self, menu, *_args):
        self.window.interests.toggle_menu_items(menu, self.dislikes_list_view, column_id="dislikes")

    def on_edit_profile(self, *_args):
        self.window.application.on_preferences(page_id="user-profile")

    def on_edit_interests(self, *_args):
        self.window.change_main_page(self.window.interests_page)

    def on_send_message(self, *_args):
        core.privatechat.show_user(self.user)

    def on_show_ip_address(self, *_args):
        core.request_ip_address(self.user, notify=True)

    def on_browse_user(self, *_args):
        core.userbrowse.browse_user(self.user)

    def on_add_remove_buddy(self, *_args):

        if self.user in core.userlist.buddies:
            core.userlist.remove_buddy(self.user)
            return

        core.userlist.add_buddy(self.user)

    def on_ban_unban_user(self, *_args):

        if core.network_filter.is_user_banned(self.user):
            core.network_filter.unban_user(self.user)
            return

        core.network_filter.ban_user(self.user)

    def on_ignore_unignore_user(self, *_args):

        if core.network_filter.is_user_ignored(self.user):
            core.network_filter.unignore_user(self.user)
            return

        core.network_filter.ignore_user(self.user)

    def on_copy_picture(self, *_args):

        if self.picture_data is None:
            return

        clipboard.copy_image(self.picture_data)

    def on_save_picture_response(self, file_path, *_args):

        if GTK_API_VERSION >= 4:
            picture_bytes = self.picture_data.save_to_png_bytes().get_data()
        else:
            _success, picture_bytes = self.picture_data.save_to_bufferv(
                type="png", option_keys=[], option_values=[])

        core.userinfo.save_user_picture(file_path, picture_bytes)

    def on_save_picture(self, *_args):

        if self.picture_data is None:
            return

        current_date_time = time.strftime("%Y-%m-%d_%H-%M-%S")

        FileChooserSave(
            parent=self.window,
            callback=self.on_save_picture_response,
            initial_folder=config.sections["transfers"]["downloaddir"],
            initial_file=f"{self.user}_{current_date_time}.png"
        ).show()

    def on_refresh(self, *_args):
        core.userinfo.show_user(self.user, refresh=True)

    def on_focus(self, *_args):
        self.description_view.widget.grab_focus()

    def on_close(self, *_args):
        core.userinfo.remove_user(self.user)

    def on_close_all_tabs(self, *_args):
        self.userinfos.remove_all_pages()
