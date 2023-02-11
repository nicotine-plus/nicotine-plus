# COPYRIGHT (C) 2020-2022 Nicotine+ Contributors
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
from pynicotine.gtkgui.widgets.popupmenu import PopupMenu
from pynicotine.gtkgui.widgets.popupmenu import UserPopupMenu
from pynicotine.gtkgui.widgets.treeview import TreeView
from pynicotine.gtkgui.widgets.theme import USER_STATUS_ICON_NAMES
from pynicotine.gtkgui.widgets.ui import UserInterface
from pynicotine.slskmessages import UserStatus
from pynicotine.utils import humanize
from pynicotine.utils import human_speed


class Interests:

    def __init__(self, window):

        ui_template = UserInterface(scope=self, path="interests.ui")
        (
            self.add_dislike_entry,
            self.add_like_entry,
            self.container,
            self.dislikes_list_container,
            self.likes_list_container,
            self.recommendations_button,
            self.recommendations_label,
            self.recommendations_list_container,
            self.similar_users_button,
            self.similar_users_label,
            self.similar_users_list_container
        ) = ui_template.widgets

        if GTK_API_VERSION >= 4:
            window.interests_container.append(self.container)
        else:
            window.interests_container.add(self.container)

        self.window = window
        self.populated_recommends = False

        # Columns
        self.likes_list_view = TreeView(
            window, parent=self.likes_list_container,
            columns={
                "likes": {
                    "column_type": "text",
                    "title": _("Likes"),
                    "default_sort_column": "ascending"
                }
            }
        )

        self.dislikes_list_view = TreeView(
            window, parent=self.dislikes_list_container,
            columns={
                "dislikes": {
                    "column_type": "text",
                    "title": _("Dislikes"),
                    "default_sort_column": "ascending"
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
                    "default_sort_column": "descending"
                },
                "item": {
                    "column_type": "text",
                    "title": _("Item")
                },

                # Hidden data columns
                "rating_data": {"data_type": int}
            }
        )

        self.similar_users_list_view = TreeView(
            window, parent=self.similar_users_list_container,
            activate_row_callback=self.on_ru_row_activated, tooltip_callback=self.on_tooltip,
            columns={
                # Visible columns
                "status": {
                    "column_type": "icon",
                    "title": _("Status"),
                    "width": 25,
                    "sort_column": "status_data",
                    "hide_header": True
                },
                "user": {
                    "column_type": "text",
                    "title": _("User"),
                    "width": 135,
                    "expand_column": True,
                    "iterator_key": True
                },
                "speed": {
                    "column_type": "number",
                    "title": _("Speed"),
                    "width": 60,
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
                "status_data": {"data_type": int},
                "speed_data": {"data_type": GObject.TYPE_UINT},
                "files_data": {"data_type": GObject.TYPE_UINT}
            }
        )

        for item in config.sections["interests"]["likes"]:
            if isinstance(item, str):
                self.add_thing_i_like(item)

        for item in config.sections["interests"]["dislikes"]:
            if isinstance(item, str):
                self.add_thing_i_hate(item)

        # Popup menus
        popup = PopupMenu(self.window.application, self.likes_list_view.widget)
        popup.add_items(
            ("#" + _("Re_commendations for Item"), self.on_recommend_item, self.likes_list_view, "likes"),
            ("#" + _("_Search for Item"), self.on_recommend_search, self.likes_list_view, "likes"),
            ("", None),
            ("#" + _("_Remove Item"), self.on_remove_thing_i_like)
        )

        popup = PopupMenu(self.window.application, self.dislikes_list_view.widget)
        popup.add_items(
            ("#" + _("Re_commendations for Item"), self.on_recommend_item, self.dislikes_list_view, "dislikes"),
            ("#" + _("_Search for Item"), self.on_recommend_search, self.dislikes_list_view, "dislikes"),
            ("", None),
            ("#" + _("_Remove Item"), self.on_remove_thing_i_dislike)
        )

        popup = PopupMenu(self.window.application, self.recommendations_list_view.widget, self.on_popup_r_menu)
        popup.add_items(
            ("$" + _("I _Like This"), self.on_like_recommendation, self.recommendations_list_view, "item"),
            ("$" + _("I _Dislike This"), self.on_dislike_recommendation, self.recommendations_list_view, "item"),
            ("", None),
            ("#" + _("_Recommendations for Item"), self.on_recommend_item, self.recommendations_list_view, "item"),
            ("#" + _("_Search for Item"), self.on_recommend_search, self.recommendations_list_view, "item")
        )

        popup = UserPopupMenu(self.window.application, self.similar_users_list_view.widget, self.on_popup_ru_menu)
        popup.setup_user_menu()

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
            ("user-stats", self.user_stats),
            ("user-status", self.user_status)
        ):
            events.connect(event_name, callback)

    def server_login(self, msg):

        if not msg.success:
            return

        self.recommendations_button.set_sensitive(True)
        self.similar_users_button.set_sensitive(True)

        if self.window.current_page_id != self.window.interests_page.id:
            # Only populate recommendations if the tab is open on login
            return

        self.populate_recommendations()

    def server_disconnect(self, *_args):
        self.recommendations_button.set_sensitive(False)
        self.similar_users_button.set_sensitive(False)

    def populate_recommendations(self):
        """ Populates the lists of recommendations and similar users if empty """

        if self.populated_recommends or core.user_status == UserStatus.OFFLINE:
            return

        self.on_recommendations_clicked()
        self.on_similar_users_clicked()

        self.populated_recommends = True

    def add_thing_i_like(self, item):

        item = item.strip().lower()

        if not item:
            return

        iterator = self.likes_list_view.iterators.get(item)

        if iterator is None:
            self.likes_list_view.add_row([item])

    def add_thing_i_hate(self, item):

        item = item.strip().lower()

        if not item:
            return

        iterator = self.dislikes_list_view.iterators.get(item)

        if iterator is None:
            self.dislikes_list_view.add_row([item])

    def remove_thing_i_like(self, item):

        iterator = self.likes_list_view.iterators.get(item)

        if iterator is not None:
            self.likes_list_view.remove_row(iterator)

    def remove_thing_i_hate(self, item):

        iterator = self.dislikes_list_view.iterators.get(item)

        if iterator is not None:
            self.dislikes_list_view.remove_row(iterator)

    def recommend_search(self, item):
        core.search.do_search(item, mode="global")

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

        for iterator in list_view.get_selected_rows():
            item = list_view.get_row_value(iterator, column_id)

            core.interests.request_item_recommendations(item)
            core.interests.request_item_similar_users(item)
            return

    def on_recommend_search(self, _action, _state, list_view, column_id):

        for iterator in list_view.get_selected_rows():
            item = list_view.get_row_value(iterator, column_id)

            self.recommend_search(item)
            return

    def on_recommendations_clicked(self, *_args):

        if not self.likes_list_view.iterators and not self.dislikes_list_view.iterators:
            core.interests.request_global_recommendations()
            return

        core.interests.request_recommendations()

    def on_similar_users_clicked(self, *_args):
        core.interests.request_similar_users()

    def set_recommendations(self, recommendations, item=None):

        if item:
            self.recommendations_label.set_label(_("Recommendations (%s)") % item)
        else:
            self.recommendations_label.set_label(_("Recommendations"))

        self.recommendations_list_view.clear()

        for thing, rating in recommendations:
            self.recommendations_list_view.add_row([humanize(rating), thing, rating], select_row=False)

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

        for user in users:
            self.similar_users_list_view.add_row([
                USER_STATUS_ICON_NAMES[UserStatus.OFFLINE],
                user,
                "", "0", 0, 0, 0
            ], select_row=False)

    def similar_users(self, msg):
        # Sort users by rating (largest number of identical likes)
        self.set_similar_users(sorted(msg.users, key=msg.users.get, reverse=True))

    def item_similar_users(self, msg):
        self.set_similar_users(msg.users, msg.thing)

    def user_status(self, msg):

        iterator = self.similar_users_list_view.iterators.get(msg.user)

        if iterator is None:
            return

        status = msg.status
        status_icon_name = USER_STATUS_ICON_NAMES.get(status)

        if not status_icon_name:
            return

        self.similar_users_list_view.set_row_value(iterator, "status", status_icon_name)
        self.similar_users_list_view.set_row_value(iterator, "status_data", status)

    def user_stats(self, msg):

        iterator = self.similar_users_list_view.iterators.get(msg.user)

        if iterator is None:
            return

        h_speed = ""
        avgspeed = msg.avgspeed

        if avgspeed > 0:
            h_speed = human_speed(avgspeed)

        files = msg.files
        h_files = humanize(msg.files)

        self.similar_users_list_view.set_row_value(iterator, "speed", h_speed)
        self.similar_users_list_view.set_row_value(iterator, "files", h_files)
        self.similar_users_list_view.set_row_value(iterator, "speed_data", GObject.Value(GObject.TYPE_UINT, avgspeed))
        self.similar_users_list_view.set_row_value(iterator, "files_data", GObject.Value(GObject.TYPE_UINT, files))

    @staticmethod
    def toggle_menu_items(menu, list_view, column_id):

        for iterator in list_view.get_selected_rows():
            item = list_view.get_row_value(iterator, column_id)

            menu.actions[_("I _Like This")].set_state(
                GLib.Variant("b", item in config.sections["interests"]["likes"])
            )
            menu.actions[_("I _Dislike This")].set_state(
                GLib.Variant("b", item in config.sections["interests"]["dislikes"])
            )
            return

    def on_popup_r_menu(self, menu, *_args):
        self.toggle_menu_items(menu, self.recommendations_list_view, column_id="item")

    def on_r_row_activated(self, *_args):

        for iterator in self.recommendations_list_view.get_selected_rows():
            item = self.recommendations_list_view.get_row_value(iterator, "item")

            core.interests.request_item_recommendations(item)
            core.interests.request_item_similar_users(item)
            return

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

    @staticmethod
    def on_tooltip(list_view, pos_x, pos_y, _keyboard_mode, tooltip):
        return list_view.show_user_status_tooltip(pos_x, pos_y, tooltip, column_id="status_data")
