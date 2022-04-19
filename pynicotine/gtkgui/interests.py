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

from gi.repository import Gio
from gi.repository import GLib
from gi.repository import GObject
from gi.repository import Gtk

from pynicotine.config import config
from pynicotine.gtkgui.widgets.popupmenu import PopupMenu
from pynicotine.gtkgui.widgets.popupmenu import UserPopupMenu
from pynicotine.gtkgui.widgets.treeview import initialise_columns
from pynicotine.gtkgui.widgets.treeview import show_user_status_tooltip
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
            self.dislikes_list_view,
            self.likes_list_view,
            self.recommendations_button,
            self.recommendations_label,
            self.recommendations_list_view,
            self.similar_users_button,
            self.similar_users_label,
            self.similar_users_list_view
        ) = self.widgets

        if Gtk.get_major_version() == 4:
            frame.interests_container.append(self.container)
        else:
            frame.interests_container.add(self.container)

        self.frame = frame
        self.core = core

        self.populated_recommends = False

        # Columns
        self.likes = {}
        self.likes_model = Gtk.ListStore(str)
        self.likes_model.set_sort_column_id(0, Gtk.SortType.ASCENDING)

        self.likes_column_numbers = list(range(self.likes_model.get_n_columns()))
        cols = initialise_columns(
            frame, None, self.likes_list_view,
            ["likes", _("Likes"), -1, "text", None]
        )

        cols["likes"].set_sort_column_id(0)
        self.likes_list_view.set_model(self.likes_model)

        self.dislikes = {}
        self.dislikes_model = Gtk.ListStore(str)
        self.dislikes_model.set_sort_column_id(0, Gtk.SortType.ASCENDING)

        self.dislikes_column_numbers = list(range(self.dislikes_model.get_n_columns()))
        cols = initialise_columns(
            frame, None, self.dislikes_list_view,
            ["dislikes", _("Dislikes"), -1, "text", None]
        )

        cols["dislikes"].set_sort_column_id(0)
        self.dislikes_list_view.set_model(self.dislikes_model)

        self.recommendations_model = Gtk.ListStore(
            str,  # (0) hrating
            str,  # (1) item
            int   # (2) rating
        )

        self.recommendations_column_numbers = list(range(self.recommendations_model.get_n_columns()))
        cols = initialise_columns(
            frame, None, self.recommendations_list_view,
            ["rating", _("Rating"), 0, "number", None],
            ["item", _("Item"), -1, "text", None]
        )

        cols["rating"].set_sort_column_id(2)
        cols["item"].set_sort_column_id(1)

        self.recommendations_list_view.set_model(self.recommendations_model)
        self.recommendations_model.set_sort_column_id(2, Gtk.SortType.DESCENDING)

        self.recommendation_users = {}
        self.recommendation_users_model = Gtk.ListStore(
            Gio.Icon,             # (0) status icon
            str,                  # (1) user
            str,                  # (2) hspeed
            str,                  # (3) hfiles
            int,                  # (4) status
            GObject.TYPE_UINT,    # (5) speed
            GObject.TYPE_UINT     # (6) file count
        )

        self.recommendation_users_column_numbers = list(range(self.recommendation_users_model.get_n_columns()))
        cols = initialise_columns(
            frame, None, self.similar_users_list_view,
            ["status", _("Status"), 25, "icon", None],
            ["user", _("User"), 135, "text", None],
            ["speed", _("Speed"), 60, "number", None],
            ["files", _("Files"), -1, "number", None],
        )

        cols["status"].set_sort_column_id(4)
        cols["user"].set_sort_column_id(1)
        cols["speed"].set_sort_column_id(5)
        cols["files"].set_sort_column_id(6)

        cols["user"].set_expand(True)
        cols["speed"].set_expand(True)
        cols["files"].set_expand(True)

        cols["status"].get_widget().hide()

        self.similar_users_list_view.set_model(self.recommendation_users_model)
        self.recommendation_users_model.set_sort_column_id(1, Gtk.SortType.ASCENDING)

        for thing in config.sections["interests"]["likes"]:
            if thing and isinstance(thing, str):
                self.likes[thing] = self.likes_model.insert_with_valuesv(-1, self.likes_column_numbers, [thing])

        for thing in config.sections["interests"]["dislikes"]:
            if thing and isinstance(thing, str):
                self.dislikes[thing] = self.dislikes_model.insert_with_valuesv(
                    -1, self.dislikes_column_numbers, [thing])

        # Popup menus
        self.til_popup_menu = popup = PopupMenu(self.frame, self.likes_list_view)
        popup.add_items(
            ("#" + _("Re_commendations for Item"), self.on_recommend_item, popup),
            ("#" + _("_Search for Item"), self.on_recommend_search, popup),
            ("", None),
            ("#" + _("_Remove Item"), self.on_remove_thing_i_like)
        )

        self.tidl_popup_menu = popup = PopupMenu(self.frame, self.dislikes_list_view)
        popup.add_items(
            ("#" + _("Re_commendations for Item"), self.on_recommend_item, popup),
            ("#" + _("_Search for Item"), self.on_recommend_search, popup),
            ("", None),
            ("#" + _("_Remove Item"), self.on_remove_thing_i_dislike)
        )

        self.r_popup_menu = popup = PopupMenu(self.frame, self.recommendations_list_view, self.on_popup_r_menu)
        popup.add_items(
            ("$" + _("I _Like This"), self.on_like_recommendation),
            ("$" + _("I _Dislike This"), self.on_dislike_recommendation),
            ("", None),
            ("#" + _("_Recommendations for Item"), self.on_recommend_item, popup),
            ("#" + _("_Search for Item"), self.on_recommend_search, popup)
        )

        popup = UserPopupMenu(self.frame, self.similar_users_list_view, self.on_popup_ru_menu)
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
            self.likes[thing] = self.likes_model.insert_with_valuesv(-1, self.likes_column_numbers, [thing])

    def on_add_thing_i_dislike(self, widget, *_args):

        thing = widget.get_text().lower()
        widget.set_text("")

        if self.core.interests.add_thing_i_hate(thing):
            self.dislikes[thing] = self.dislikes_model.insert_with_valuesv(-1, self.dislikes_column_numbers, [thing])

    def on_remove_thing_i_like(self, *_args):

        thing = self.get_selected_item(self.likes_list_view, column=0)

        if not self.core.interests.remove_thing_i_like(thing):
            return

        self.likes_model.remove(self.likes[thing])
        del self.likes[thing]

    def on_remove_thing_i_dislike(self, *_args):

        thing = self.get_selected_item(self.dislikes_list_view, column=0)

        if not self.core.interests.remove_thing_i_hate(thing):
            return

        self.dislikes_model.remove(self.dislikes[thing])
        del self.dislikes[thing]

    def on_like_recommendation(self, action, state, thing=None):

        if thing is None:
            thing = self.get_selected_item(self.recommendations_list_view, column=1)

        if state.get_boolean() and self.core.interests.add_thing_i_like(thing):
            self.likes[thing] = self.likes_model.insert_with_valuesv(-1, self.likes_column_numbers, [thing])

        elif not state.get_boolean() and self.core.interests.remove_thing_i_like(thing):
            self.likes_model.remove(self.likes[thing])
            del self.likes[thing]

        action.set_state(state)

    def on_dislike_recommendation(self, action, state, thing=None):

        if thing is None:
            thing = self.get_selected_item(self.recommendations_list_view, column=1)

        if state.get_boolean() and thing and self.core.interests.add_thing_i_hate(thing):
            self.dislikes[thing] = self.dislikes_model.insert_with_valuesv(-1, self.dislikes_column_numbers, [thing])

        elif not state.get_boolean() and self.core.interests.remove_thing_i_hate(thing):
            self.dislikes_model.remove(self.dislikes[thing])
            del self.dislikes[thing]

        action.set_state(state)

    def on_recommend_item(self, _action, _state, menu):

        column = 1 if menu.parent == self.recommendations_list_view else 0
        item = self.get_selected_item(menu.parent, column)
        self.core.interests.request_item_recommendations(item)
        self.core.interests.request_item_similar_users(item)

    def on_recommend_search(self, _action, _state, menu):

        column = 1 if menu.parent == self.recommendations_list_view else 0
        item = self.get_selected_item(menu.parent, column)
        self.recommend_search(item)

    def on_recommendations_clicked(self, *_args):

        if not self.likes and not self.dislikes:
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

        self.recommendations_model.clear()

        for thing, rating in recommendations:
            self.recommendations_model.insert_with_valuesv(
                -1, self.recommendations_column_numbers, [humanize(rating), thing, rating]
            )

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

        self.recommendation_users_model.clear()
        self.recommendation_users = {}

        for user in users:
            iterator = self.recommendation_users_model.insert_with_valuesv(
                -1, self.recommendation_users_column_numbers,
                [get_status_icon(0), user, "", "0", 0, 0, 0]
            )
            self.recommendation_users[user] = iterator

            # Request user status, speed and number of shared files
            self.core.watch_user(user, force_update=True)

    def similar_users(self, msg):
        self.set_similar_users(msg.users)

    def item_similar_users(self, msg):
        self.set_similar_users(msg.users, msg.thing)

    def get_user_status(self, msg):

        iterator = self.recommendation_users.get(msg.user)

        if iterator is None:
            return

        status_icon = get_status_icon(msg.status)

        if status_icon is None:
            return

        self.recommendation_users_model.set_value(iterator, 0, status_icon)
        self.recommendation_users_model.set_value(iterator, 4, msg.status)

    def get_user_stats(self, msg):

        iterator = self.recommendation_users.get(msg.user)

        if iterator is None:
            return

        h_speed = ""
        avgspeed = msg.avgspeed

        if avgspeed > 0:
            h_speed = human_speed(avgspeed)

        files = msg.files
        h_files = humanize(msg.files)

        self.recommendation_users_model.set_value(iterator, 2, h_speed)
        self.recommendation_users_model.set_value(iterator, 3, h_files)
        self.recommendation_users_model.set_value(iterator, 5, GObject.Value(GObject.TYPE_UINT, avgspeed))
        self.recommendation_users_model.set_value(iterator, 6, GObject.Value(GObject.TYPE_UINT, files))

    @staticmethod
    def get_selected_item(treeview, column=0):

        model, iterator = treeview.get_selection().get_selected()

        if iterator is None:
            return None

        return model.get_value(iterator, column)

    def on_popup_r_menu(self, menu, widget):

        item = self.get_selected_item(widget, column=1)

        menu.actions[_("I _Like This")].set_state(
            GLib.Variant("b", item in config.sections["interests"]["likes"])
        )
        menu.actions[_("I _Dislike This")].set_state(
            GLib.Variant("b", item in config.sections["interests"]["dislikes"])
        )

    def on_r_row_activated(self, treeview, _path, _column):

        item = self.get_selected_item(treeview, column=1)

        if item is not None:
            self.core.interests.request_item_recommendations(item)
            self.core.interests.request_item_similar_users(item)

    def on_popup_ru_menu(self, menu, widget):

        user = self.get_selected_item(widget, column=1)
        menu.set_user(user)
        menu.toggle_user_items()

    def on_ru_row_activated(self, treeview, _path, _column):

        user = self.get_selected_item(treeview, column=1)

        if user is not None:
            self.core.privatechats.show_user(user)
            self.frame.change_main_page(self.frame.private_page)

    @staticmethod
    def on_tooltip(widget, pos_x, pos_y, _keyboard_mode, tooltip):
        return show_user_status_tooltip(widget, pos_x, pos_y, tooltip, 4)

    def update_visuals(self):

        for widget in list(self.__dict__.values()):
            update_widget_visuals(widget)
