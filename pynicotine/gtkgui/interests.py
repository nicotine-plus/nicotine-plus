# COPYRIGHT (C) 2020-2022 Nicotine+ Contributors
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

from gi.repository import GLib
from gi.repository import GObject
from gi.repository import Gtk

from pynicotine.config import config
from pynicotine.gtkgui.widgets.popupmenu import PopupMenu
from pynicotine.gtkgui.widgets.popupmenu import UserPopupMenu
from pynicotine.gtkgui.widgets.treeview import TreeView
from pynicotine.gtkgui.widgets.theme import get_status_icon
from pynicotine.gtkgui.widgets.theme import update_widget_visuals
from pynicotine.gtkgui.widgets.ui import UserInterface
from pynicotine.utils import humanize
from pynicotine.utils import human_speed


class Interests(UserInterface):

    def __init__(self, frame, core):

        super().__init__("ui/interests.ui")
        (
            self.container,
            self.dislikes_list_container,
            self.likes_list_container,
            self.recommendations_button,
            self.recommendations_label,
            self.recommendations_list_container,
            self.similar_users_button,
            self.similar_users_label,
            self.similar_users_list_container
        ) = self.widgets

        if Gtk.get_major_version() >= 4:
            frame.interests_container.append(self.container)
        else:
            frame.interests_container.add(self.container)

        self.frame = frame
        self.core = core

        self.populated_recommends = False

        # Columns
        self.likes_iters = {}
        self.likes_list_view = TreeView(
            frame, parent=self.likes_list_container,
            columns=[
                {"column_id": "likes", "column_type": "text", "title": _("Likes"), "width": -1,
                 "sort_column": 0, "default_sort_column": "ascending"}
            ]
        )

        self.dislikes_iters = {}
        self.dislikes_list_view = TreeView(
            frame, parent=self.dislikes_list_container,
            columns=[
                {"column_id": "dislikes", "column_type": "text", "title": _("Dislikes"), "width": -1,
                 "sort_column": 0, "default_sort_column": "ascending"}
            ]
        )

        self.recommendations_list_view = TreeView(
            frame, parent=self.recommendations_list_container,
            search_column=1, activate_row_callback=self.on_r_row_activated,
            columns=[
                # Visible columns
                {"column_id": "rating", "column_type": "number", "title": _("Rating"), "width": 0,
                 "sort_column": 2, "default_sort_column": "descending"},
                {"column_id": "item", "column_type": "text", "title": _("Item"), "width": -1,
                 "sort_column": 1},

                # Hidden data columns
                {"column_id": "rating_hidden", "data_type": int}
            ]
        )

        self.similar_users_iters = {}
        self.similar_users_list_view = TreeView(
            frame, parent=self.similar_users_list_container,
            search_column=1, activate_row_callback=self.on_ru_row_activated, tooltip_callback=self.on_tooltip,
            columns=[
                # Visible columns
                {"column_id": "status", "title": _("Status"), "width": 25,
                 "column_type": "icon", "sort_column": 4, "hide_header": True},
                {"column_id": "user", "title": _("User"), "width": 135,
                 "column_type": "text", "sort_column": 1, "expand_header": True},
                {"column_id": "speed", "title": _("Speed"), "width": 60,
                 "column_type": "number", "sort_column": 5, "expand_header": True},
                {"column_id": "files", "title": _("Files"), "width": -1,
                 "column_type": "number", "sort_column": 6, "expand_header": True},

                # Hidden data columns
                {"column_id": "status_hidden", "data_type": int},
                {"column_id": "speed_hidden", "data_type": GObject.TYPE_UINT},
                {"column_id": "files_hidden", "data_type": GObject.TYPE_UINT}
            ]
        )

        for thing in config.sections["interests"]["likes"]:
            if thing and isinstance(thing, str):
                self.likes_iters[thing] = self.likes_list_view.add_row([thing])

        for thing in config.sections["interests"]["dislikes"]:
            if thing and isinstance(thing, str):
                self.dislikes_iters[thing] = self.dislikes_list_view.add_row([thing])

        # Popup menus
        self.til_popup_menu = popup = PopupMenu(self.frame, self.likes_list_view.widget)
        popup.add_items(
            ("#" + _("Re_commendations for Item"), self.on_recommend_item, self.likes_list_view),
            ("#" + _("_Search for Item"), self.on_recommend_search, self.likes_list_view),
            ("", None),
            ("#" + _("_Remove Item"), self.on_remove_thing_i_like)
        )

        self.tidl_popup_menu = popup = PopupMenu(self.frame, self.dislikes_list_view.widget)
        popup.add_items(
            ("#" + _("Re_commendations for Item"), self.on_recommend_item, self.dislikes_list_view),
            ("#" + _("_Search for Item"), self.on_recommend_search, self.dislikes_list_view),
            ("", None),
            ("#" + _("_Remove Item"), self.on_remove_thing_i_dislike)
        )

        self.r_popup_menu = popup = PopupMenu(self.frame, self.recommendations_list_view.widget, self.on_popup_r_menu)
        popup.add_items(
            ("$" + _("I _Like This"), self.on_like_recommendation),
            ("$" + _("I _Dislike This"), self.on_dislike_recommendation),
            ("", None),
            ("#" + _("_Recommendations for Item"), self.on_recommend_item, self.recommendations_list_view),
            ("#" + _("_Search for Item"), self.on_recommend_search, self.recommendations_list_view)
        )

        popup = UserPopupMenu(self.frame, self.similar_users_list_view.widget, self.on_popup_ru_menu)
        popup.setup_user_menu()

        self.update_visuals()

    def server_login(self):

        self.recommendations_button.set_sensitive(True)
        self.similar_users_button.set_sensitive(True)

        if self.frame.current_page_id != self.frame.interests_page.id:
            # Only populate recommendations if the tab is open on login
            return

        self.populate_recommendations()

    def server_disconnect(self):
        self.recommendations_button.set_sensitive(False)
        self.similar_users_button.set_sensitive(False)

    def populate_recommendations(self):
        """ Populates the lists of recommendations and similar users if empty """

        if self.populated_recommends or not self.core.logged_in:
            return

        self.on_recommendations_clicked()
        self.on_similar_users_clicked()

        self.populated_recommends = True

    def recommend_search(self, item):
        self.frame.search_entry.set_text(item)
        self.frame.change_main_page(self.frame.search_page)

    def on_add_thing_i_like(self, widget, *_args):

        thing = widget.get_text().lower()
        widget.set_text("")

        if self.core.interests.add_thing_i_like(thing):
            self.likes_iters[thing] = self.likes_list_view.add_row([thing])

    def on_add_thing_i_dislike(self, widget, *_args):

        thing = widget.get_text().lower()
        widget.set_text("")

        if self.core.interests.add_thing_i_hate(thing):
            self.dislikes_iters[thing] = self.dislikes_list_view.add_row([thing])

    def on_remove_thing_i_like(self, *_args):

        thing = self.get_selected_item(self.likes_list_view, column=0)

        if not self.core.interests.remove_thing_i_like(thing):
            return

        self.likes_list_view.remove_row(self.likes_iters[thing])
        del self.likes_iters[thing]

    def on_remove_thing_i_dislike(self, *_args):

        thing = self.get_selected_item(self.dislikes_list_view, column=0)

        if not self.core.interests.remove_thing_i_hate(thing):
            return

        self.dislikes_list_view.remove_row(self.dislikes_iters[thing])
        del self.dislikes_iters[thing]

    def on_like_recommendation(self, action, state, thing=None):

        if thing is None:
            thing = self.get_selected_item(self.recommendations_list_view, column=1)

        if state.get_boolean() and self.core.interests.add_thing_i_like(thing):
            self.likes_iters[thing] = self.likes_list_view.add_row([thing])

        elif not state.get_boolean() and self.core.interests.remove_thing_i_like(thing):
            self.likes_list_view.remove_row(self.likes_iters[thing])
            del self.likes_iters[thing]

        action.set_state(state)

    def on_dislike_recommendation(self, action, state, thing=None):

        if thing is None:
            thing = self.get_selected_item(self.recommendations_list_view, column=1)

        if state.get_boolean() and thing and self.core.interests.add_thing_i_hate(thing):
            self.dislikes_iters[thing] = self.dislikes_list_view.add_row([thing])

        elif not state.get_boolean() and self.core.interests.remove_thing_i_hate(thing):
            self.dislikes_list_view.remove_row(self.dislikes_iters[thing])
            del self.dislikes_iters[thing]

        action.set_state(state)

    def on_recommend_item(self, _action, _state, list_view):

        column = 1 if list_view == self.recommendations_list_view else 0
        item = self.get_selected_item(list_view, column)
        self.core.interests.request_item_recommendations(item)
        self.core.interests.request_item_similar_users(item)

    def on_recommend_search(self, _action, _state, list_view):

        column = 1 if list_view == self.recommendations_list_view else 0
        item = self.get_selected_item(list_view, column)
        self.recommend_search(item)

    def on_recommendations_clicked(self, *_args):

        if not self.likes_iters and not self.dislikes_iters:
            self.core.interests.request_global_recommendations()
            return

        self.core.interests.request_recommendations()

    def on_similar_users_clicked(self, *_args):
        self.core.interests.request_similar_users()

    def set_recommendations(self, recommendations, item=None):

        if item:
            self.recommendations_label.set_label(_("Recommendations (%s)") % item)
        else:
            self.recommendations_label.set_label(_("Recommendations"))

        self.recommendations_list_view.clear()

        for thing, rating in recommendations:
            self.recommendations_list_view.add_row([humanize(rating), thing, rating])

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
        self.similar_users_iters.clear()

        for user in users:
            iterator = self.similar_users_list_view.add_row([get_status_icon(0), user, "", "0", 0, 0, 0])
            self.similar_users_iters[user] = iterator

            # Request user status, speed and number of shared files
            self.core.watch_user(user, force_update=True)

    def similar_users(self, msg):
        self.set_similar_users(msg.users)

    def item_similar_users(self, msg):
        self.set_similar_users(msg.users, msg.thing)

    def get_user_status(self, msg):

        iterator = self.similar_users_iters.get(msg.user)

        if iterator is None:
            return

        status_icon = get_status_icon(msg.status)

        if status_icon is None:
            return

        self.similar_users_list_view.set_row_value(iterator, 0, status_icon)
        self.similar_users_list_view.set_row_value(iterator, 4, msg.status)

    def get_user_stats(self, msg):

        iterator = self.similar_users_iters.get(msg.user)

        if iterator is None:
            return

        h_speed = ""
        avgspeed = msg.avgspeed

        if avgspeed > 0:
            h_speed = human_speed(avgspeed)

        files = msg.files
        h_files = humanize(msg.files)

        self.similar_users_list_view.set_row_value(iterator, 2, h_speed)
        self.similar_users_list_view.set_row_value(iterator, 3, h_files)
        self.similar_users_list_view.set_row_value(iterator, 5, GObject.Value(GObject.TYPE_UINT, avgspeed))
        self.similar_users_list_view.set_row_value(iterator, 6, GObject.Value(GObject.TYPE_UINT, files))

    @staticmethod
    def get_selected_item(treeview, column=0):

        iterators = treeview.get_selected_rows()

        if not iterators:
            return None

        return treeview.get_row_value(iterators[0], column)

    def on_popup_r_menu(self, menu, *_args):

        item = self.get_selected_item(self.recommendations_list_view, column=1)

        menu.actions[_("I _Like This")].set_state(
            GLib.Variant("b", item in config.sections["interests"]["likes"])
        )
        menu.actions[_("I _Dislike This")].set_state(
            GLib.Variant("b", item in config.sections["interests"]["dislikes"])
        )

    def on_r_row_activated(self, *_args):

        item = self.get_selected_item(self.recommendations_list_view, column=1)

        if item is not None:
            self.core.interests.request_item_recommendations(item)
            self.core.interests.request_item_similar_users(item)

    def on_popup_ru_menu(self, menu, *_args):

        user = self.get_selected_item(self.similar_users_list_view, column=1)
        menu.set_user(user)
        menu.toggle_user_items()

    def on_ru_row_activated(self, *_args):

        user = self.get_selected_item(self.similar_users_list_view, column=1)

        if user is not None:
            self.core.privatechats.show_user(user)
            self.frame.change_main_page(self.frame.private_page)

    @staticmethod
    def on_tooltip(list_view, pos_x, pos_y, _keyboard_mode, tooltip):
        return list_view.show_user_status_tooltip(pos_x, pos_y, tooltip, column=4)

    def update_visuals(self):

        for widget in list(self.__dict__.values()):
            update_widget_visuals(widget)
