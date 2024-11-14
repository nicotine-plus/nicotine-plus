# COPYRIGHT (C) 2020-2024 Nicotine+ Contributors
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

from gi.repository import GLib
from gi.repository import GObject

from pynicotine.config import config
from pynicotine.core import core
from pynicotine.events import events
from pynicotine.gtkgui.application import GTK_API_VERSION
from pynicotine.gtkgui.widgets import ui
from pynicotine.gtkgui.widgets.popupmenu import PopupMenu
from pynicotine.gtkgui.widgets.popupmenu import UserPopupMenu
from pynicotine.gtkgui.widgets.treeview import TreeView
from pynicotine.gtkgui.widgets.theme import USER_STATUS_ICON_NAMES
from pynicotine.gtkgui.widgets.theme import get_flag_icon_name
from pynicotine.slskmessages import UserStatus
from pynicotine.utils import humanize
from pynicotine.utils import human_speed


class Interests:

    def __init__(self, window):

        (
            self.add_dislike_entry,
            self.add_like_entry,
            self.container,
            self.dislikes_list_container,
            self.likes_list_container,
            self.recommendations_button,
            self.recommendations_label,
            self.recommendations_list_container,
            self.similar_users_label,
            self.similar_users_list_container
        ) = ui.load(scope=self, path="interests.ui")

        if GTK_API_VERSION >= 4:
            window.interests_container.append(self.container)
        else:
            window.interests_container.add(self.container)

        self.window = window
        self.page = window.interests_page
        self.page.id = "interests"
        self.toolbar = window.interests_toolbar
        self.toolbar_start_content = window.interests_title
        self.toolbar_end_content = window.interests_end
        self.toolbar_default_widget = None
        self.popup_menus = []

        self.populated_recommends = False

        # Columns
        self.likes_list_view = TreeView(
            window, parent=self.likes_list_container,
            delete_accelerator_callback=self.on_remove_thing_i_like,
            columns={
                "likes": {
                    "column_type": "text",
                    "title": _("Likes"),
                    "default_sort_type": "ascending"
                }
            }
        )

        self.dislikes_list_view = TreeView(
            window, parent=self.dislikes_list_container,
            delete_accelerator_callback=self.on_remove_thing_i_dislike,
            columns={
                "dislikes": {
                    "column_type": "text",
                    "title": _("Dislikes"),
                    "default_sort_type": "ascending"
                }
            }
        )

        self.recommendations_list_view = TreeView(
            window, parent=self.recommendations_list_container,
            activate_row_callback=self.on_r_row_activated,
            columns={
                # Visible columns
                "rating": {
                    "column_type": "number",
                    "title": _("Rating"),
                    "width": 0,
                    "sort_column": "rating_data",
                    "default_sort_type": "descending"
                },
                "item": {
                    "column_type": "text",
                    "title": _("Item"),
                    "iterator_key": True
                },

                # Hidden data columns
                "rating_data": {"data_type": GObject.TYPE_INT}
            }
        )

        self.similar_users_list_view = TreeView(
            window, parent=self.similar_users_list_container,
            activate_row_callback=self.on_ru_row_activated,
            columns={
                # Visible columns
                "status": {
                    "column_type": "icon",
                    "title": _("Status"),
                    "width": 25,
                    "hide_header": True
                },
                "country": {
                    "column_type": "icon",
                    "title": _("Country"),
                    "width": 30,
                    "hide_header": True
                },
                "user": {
                    "column_type": "text",
                    "title": _("User"),
                    "width": 120,
                    "expand_column": True,
                    "iterator_key": True
                },
                "speed": {
                    "column_type": "number",
                    "title": _("Speed"),
                    "width": 90,
                    "sort_column": "speed_data",
                    "expand_column": True
                },
                "files": {
                    "column_type": "number",
                    "title": _("Files"),
                    "sort_column": "files_data",
                    "expand_column": True
                },

                # Hidden data columns
                "speed_data": {"data_type": GObject.TYPE_UINT},
                "files_data": {"data_type": GObject.TYPE_UINT},
                "rating_data": {
                    "data_type": GObject.TYPE_UINT,
                    "default_sort_type": "descending"
                }
            }
        )

        self.likes_list_view.freeze()
        self.dislikes_list_view.freeze()

        for item in config.sections["interests"]["likes"]:
            if isinstance(item, str):
                self.add_thing_i_like(item, select_row=False)

        for item in config.sections["interests"]["dislikes"]:
            if isinstance(item, str):
                self.add_thing_i_hate(item, select_row=False)

        self.likes_list_view.unfreeze()
        self.dislikes_list_view.unfreeze()

        # Popup menus
        popup = PopupMenu(self.window.application, self.likes_list_view.widget)
        popup.add_items(
            ("#" + _("_Recommendations for Item"), self.on_recommend_item, self.likes_list_view, "likes"),
            ("#" + _("_Search for Item"), self.on_recommend_search, self.likes_list_view, "likes"),
            ("", None),
            ("#" + _("Remove"), self.on_remove_thing_i_like)
        )
        self.popup_menus.append(popup)

        popup = PopupMenu(self.window.application, self.dislikes_list_view.widget)
        popup.add_items(
            ("#" + _("_Recommendations for Item"), self.on_recommend_item, self.dislikes_list_view, "dislikes"),
            ("#" + _("_Search for Item"), self.on_recommend_search, self.dislikes_list_view, "dislikes"),
            ("", None),
            ("#" + _("Remove"), self.on_remove_thing_i_dislike)
        )
        self.popup_menus.append(popup)

        popup = PopupMenu(self.window.application, self.recommendations_list_view.widget, self.on_popup_r_menu)
        popup.add_items(
            ("$" + _("I _Like This"), self.on_like_recommendation, self.recommendations_list_view, "item"),
            ("$" + _("I _Dislike This"), self.on_dislike_recommendation, self.recommendations_list_view, "item"),
            ("", None),
            ("#" + _("_Recommendations for Item"), self.on_recommend_item, self.recommendations_list_view, "item"),
            ("#" + _("_Search for Item"), self.on_recommend_search, self.recommendations_list_view, "item")
        )
        self.popup_menus.append(popup)

        popup = UserPopupMenu(
            self.window.application, parent=self.similar_users_list_view.widget, callback=self.on_popup_ru_menu,
            tab_name="interests"
        )
        self.popup_menus.append(popup)

        for event_name, callback in (
            ("add-dislike", self.add_thing_i_hate),
            ("add-interest", self.add_thing_i_like),
            ("global-recommendations", self.global_recommendations),
            ("item-recommendations", self.item_recommendations),
            ("item-similar-users", self.item_similar_users),
            ("recommendations", self.recommendations),
            ("remove-dislike", self.remove_thing_i_hate),
            ("remove-interest", self.remove_thing_i_like),
            ("server-login", self.server_login),
            ("server-disconnect", self.server_disconnect),
            ("similar-users", self.similar_users),
            ("user-country", self.user_country),
            ("user-stats", self.user_stats),
            ("user-status", self.user_status)
        ):
            events.connect(event_name, callback)

    def destroy(self):

        for menu in self.popup_menus:
            menu.destroy()

        self.likes_list_view.destroy()
        self.dislikes_list_view.destroy()
        self.recommendations_list_view.destroy()
        self.similar_users_list_view.destroy()

        self.__dict__.clear()

    def on_focus(self, *_args):

        self.populate_recommendations()
        self.recommendations_list_view.grab_focus()
        return True

    def server_login(self, msg):

        if not msg.success:
            return

        self.recommendations_button.set_sensitive(True)

        if self.window.current_page_id != self.window.interests_page.id:
            # Only populate recommendations if the tab is open on login
            return

        self.populate_recommendations()

    def server_disconnect(self, *_args):

        self.recommendations_button.set_sensitive(False)

        for iterator in self.similar_users_list_view.iterators.values():
            self.similar_users_list_view.set_row_value(iterator, "status", USER_STATUS_ICON_NAMES[UserStatus.OFFLINE])

        self.populated_recommends = False

    def populate_recommendations(self):
        """Populates the lists of recommendations and similar users if
        empty."""

        if self.populated_recommends or core.users.login_status == UserStatus.OFFLINE:
            return

        self.show_recommendations()

    def show_recommendations(self):

        self.recommendations_label.set_label(_("Recommendations"))
        self.similar_users_label.set_label(_("Similar Users"))

        if not self.likes_list_view.iterators and not self.dislikes_list_view.iterators:
            core.interests.request_global_recommendations()
        else:
            core.interests.request_recommendations()

        core.interests.request_similar_users()
        self.populated_recommends = True

    def show_item_recommendations(self, list_view, column_id):

        for iterator in list_view.get_selected_rows():
            item = list_view.get_row_value(iterator, column_id)

            core.interests.request_item_recommendations(item)
            core.interests.request_item_similar_users(item)
            self.populated_recommends = True

            if self.window.current_page_id != self.window.interests_page.id:
                self.window.change_main_page(self.window.interests_page)
            return

    def add_thing_i_like(self, item, select_row=True):

        item = item.strip().lower()

        if not item:
            return

        iterator = self.likes_list_view.iterators.get(item)

        if iterator is None:
            self.likes_list_view.add_row([item], select_row=select_row)

    def add_thing_i_hate(self, item, select_row=True):

        item = item.strip().lower()

        if not item:
            return

        iterator = self.dislikes_list_view.iterators.get(item)

        if iterator is None:
            self.dislikes_list_view.add_row([item], select_row=select_row)

    def remove_thing_i_like(self, item):

        iterator = self.likes_list_view.iterators.get(item)

        if iterator is not None:
            self.likes_list_view.remove_row(iterator)

    def remove_thing_i_hate(self, item):

        iterator = self.dislikes_list_view.iterators.get(item)

        if iterator is not None:
            self.dislikes_list_view.remove_row(iterator)

    def on_add_thing_i_like(self, *_args):

        item = self.add_like_entry.get_text().strip()

        if not item:
            return

        self.add_like_entry.set_text("")
        core.interests.add_thing_i_like(item)

    def on_add_thing_i_dislike(self, *_args):

        item = self.add_dislike_entry.get_text().strip()

        if not item:
            return

        self.add_dislike_entry.set_text("")
        core.interests.add_thing_i_hate(item)

    def on_remove_thing_i_like(self, *_args):

        for iterator in self.likes_list_view.get_selected_rows():
            item = self.likes_list_view.get_row_value(iterator, "likes")

            core.interests.remove_thing_i_like(item)
            return

    def on_remove_thing_i_dislike(self, *_args):

        for iterator in self.dislikes_list_view.get_selected_rows():
            item = self.dislikes_list_view.get_row_value(iterator, "dislikes")

            core.interests.remove_thing_i_hate(item)
            return

    def on_like_recommendation(self, action, state, list_view, column_id):

        for iterator in list_view.get_selected_rows():
            item = list_view.get_row_value(iterator, column_id)

            if state.get_boolean():
                core.interests.add_thing_i_like(item)
            else:
                core.interests.remove_thing_i_like(item)

            action.set_state(state)
            return

    def on_dislike_recommendation(self, action, state, list_view, column_id):

        for iterator in list_view.get_selected_rows():
            item = list_view.get_row_value(iterator, column_id)

            if state.get_boolean():
                core.interests.add_thing_i_hate(item)
            else:
                core.interests.remove_thing_i_hate(item)

            action.set_state(state)
            return

    def on_recommend_item(self, _action, _state, list_view, column_id):
        self.show_item_recommendations(list_view, column_id)

    def on_recommend_search(self, _action, _state, list_view, column_id):

        for iterator in list_view.get_selected_rows():
            item = list_view.get_row_value(iterator, column_id)

            core.search.do_search(item, mode="global")
            return

    def on_refresh_recommendations(self, *_args):
        self.show_recommendations()

    def set_recommendations(self, recommendations, item=None):

        if item:
            self.recommendations_label.set_label(_("Recommendations (%s)") % item)
        else:
            self.recommendations_label.set_label(_("Recommendations"))

        self.recommendations_list_view.clear()
        self.recommendations_list_view.freeze()

        for thing, rating in recommendations:
            self.recommendations_list_view.add_row([humanize(rating), thing, rating], select_row=False)

        self.recommendations_list_view.unfreeze()

    def global_recommendations(self, msg):
        self.set_recommendations(msg.recommendations + msg.unrecommendations)

    def recommendations(self, msg):
        self.set_recommendations(msg.recommendations + msg.unrecommendations)

    def item_recommendations(self, msg):
        self.set_recommendations(msg.recommendations + msg.unrecommendations, msg.thing)

    def set_similar_users(self, users, item=None):

        if item:
            self.similar_users_label.set_label(_("Similar Users (%s)") % item)
        else:
            self.similar_users_label.set_label(_("Similar Users"))

        self.similar_users_list_view.clear()
        self.similar_users_list_view.freeze()

        for index, (user, rating) in enumerate(reversed(list(users.items()))):
            status = core.users.statuses.get(user, UserStatus.OFFLINE)
            country_code = core.users.countries.get(user, "")
            stats = core.users.watched.get(user)
            rating = index + (1000 * rating)  # Preserve default sort order

            if stats is not None:
                speed = stats.upload_speed or 0
                files = stats.files
            else:
                speed = 0
                files = None

            h_files = humanize(files) if files is not None else ""
            h_speed = human_speed(speed) if speed > 0 else ""

            self.similar_users_list_view.add_row([
                USER_STATUS_ICON_NAMES[status],
                get_flag_icon_name(country_code),
                user,
                h_speed,
                h_files,
                speed,
                files or 0,
                rating
            ], select_row=False)

        self.similar_users_list_view.unfreeze()

    def similar_users(self, msg):
        self.set_similar_users(msg.users)

    def item_similar_users(self, msg):
        rating = 0
        self.set_similar_users({user: rating for user in msg.users}, msg.thing)

    def user_country(self, user, country_code):

        iterator = self.similar_users_list_view.iterators.get(user)

        if iterator is None:
            return

        flag_icon_name = get_flag_icon_name(country_code)

        if flag_icon_name and flag_icon_name != self.similar_users_list_view.get_row_value(iterator, "country"):
            self.similar_users_list_view.set_row_value(iterator, "country", flag_icon_name)

    def user_status(self, msg):

        iterator = self.similar_users_list_view.iterators.get(msg.user)

        if iterator is None:
            return

        status_icon_name = USER_STATUS_ICON_NAMES.get(msg.status)

        if status_icon_name and status_icon_name != self.similar_users_list_view.get_row_value(iterator, "status"):
            self.similar_users_list_view.set_row_value(iterator, "status", status_icon_name)

    def user_stats(self, msg):

        iterator = self.similar_users_list_view.iterators.get(msg.user)

        if iterator is None:
            return

        speed = msg.avgspeed or 0
        num_files = msg.files or 0
        column_ids = []
        column_values = []

        if speed != self.similar_users_list_view.get_row_value(iterator, "speed_data"):
            h_speed = human_speed(speed) if speed > 0 else ""

            column_ids.extend(("speed", "speed_data"))
            column_values.extend((h_speed, speed))

        if num_files != self.similar_users_list_view.get_row_value(iterator, "files_data"):
            h_num_files = humanize(num_files)

            column_ids.extend(("files", "files_data"))
            column_values.extend((h_num_files, num_files))

        if column_ids:
            self.similar_users_list_view.set_row_values(iterator, column_ids, column_values)

    @staticmethod
    def toggle_menu_items(menu, list_view, column_id):

        for iterator in list_view.get_selected_rows():
            item = list_view.get_row_value(iterator, column_id)

            menu.actions[_("I _Like This")].set_state(
                GLib.Variant.new_boolean(item in config.sections["interests"]["likes"])
            )
            menu.actions[_("I _Dislike This")].set_state(
                GLib.Variant.new_boolean(item in config.sections["interests"]["dislikes"])
            )
            return

    def on_popup_r_menu(self, menu, *_args):
        self.toggle_menu_items(menu, self.recommendations_list_view, column_id="item")

    def on_r_row_activated(self, *_args):
        self.show_item_recommendations(self.recommendations_list_view, column_id="item")

    def on_popup_ru_menu(self, menu, *_args):

        for iterator in self.similar_users_list_view.get_selected_rows():
            user = self.similar_users_list_view.get_row_value(iterator, "user")

            menu.set_user(user)
            menu.toggle_user_items()
            return

    def on_ru_row_activated(self, *_args):

        for iterator in self.similar_users_list_view.get_selected_rows():
            user = self.similar_users_list_view.get_row_value(iterator, "user")

            core.userinfo.show_user(user)
            return
