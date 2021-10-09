# COPYRIGHT (C) 2020-2021 Nicotine+ Team
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
from pynicotine.gtkgui.widgets.treeview import initialise_columns
from pynicotine.gtkgui.widgets.treeview import show_user_status_tooltip
from pynicotine.gtkgui.widgets.theme import get_status_image
from pynicotine.gtkgui.widgets.theme import update_widget_visuals
from pynicotine.gtkgui.widgets.ui import UserInterface
from pynicotine.utils import humanize
from pynicotine.utils import human_speed


class Interests(UserInterface):

    def __init__(self, frame):

        super().__init__("ui/interests.ui")
        frame.interestsvbox.add(self.Main)

        self.frame = frame
        self.page_id = "interests"
        self.populated_recommends = False

        self.likes = {}
        self.likes_model = Gtk.ListStore(str)
        self.likes_model.set_sort_column_id(0, Gtk.SortType.ASCENDING)

        self.likes_column_numbers = list(range(self.likes_model.get_n_columns()))
        cols = initialise_columns(
            None, self.LikesList,
            ["likes", _("Likes"), -1, "text", None]
        )

        cols["likes"].set_sort_column_id(0)
        self.LikesList.set_model(self.likes_model)

        self.dislikes = {}
        self.dislikes_model = Gtk.ListStore(str)
        self.dislikes_model.set_sort_column_id(0, Gtk.SortType.ASCENDING)

        self.dislikes_column_numbers = list(range(self.dislikes_model.get_n_columns()))
        cols = initialise_columns(
            None, self.DislikesList,
            ["dislikes", _("Dislikes"), -1, "text", None]
        )

        cols["dislikes"].set_sort_column_id(0)
        self.DislikesList.set_model(self.dislikes_model)

        self.recommendations_model = Gtk.ListStore(
            str,  # (0) hrating
            str,  # (1) item
            int   # (2) rating
        )

        self.recommendations_column_numbers = list(range(self.recommendations_model.get_n_columns()))
        cols = initialise_columns(
            None, self.RecommendationsList,
            ["rating", _("Rating"), 0, "number", None],
            ["item", _("Item"), -1, "text", None]
        )

        cols["rating"].set_sort_column_id(2)
        cols["item"].set_sort_column_id(1)

        self.RecommendationsList.set_model(self.recommendations_model)

        self.recommendation_users = {}
        self.recommendation_users_model = Gtk.ListStore(
            GObject.TYPE_OBJECT,  # (0) status icon
            str,                  # (1) user
            str,                  # (2) hspeed
            str,                  # (3) hfiles
            int,                  # (4) status
            GObject.TYPE_UINT64,  # (5) speed
            GObject.TYPE_UINT64   # (6) file count
        )

        self.recommendation_users_column_numbers = list(range(self.recommendation_users_model.get_n_columns()))
        cols = initialise_columns(
            None, self.RecommendationUsersList,
            ["status", _("Status"), 25, "pixbuf", None],
            ["user", _("User"), 100, "text", None],
            ["speed", _("Speed"), 100, "text", None],
            ["files", _("Files"), 100, "text", None],
        )

        cols["status"].set_sort_column_id(4)
        cols["user"].set_sort_column_id(1)
        cols["speed"].set_sort_column_id(5)
        cols["files"].set_sort_column_id(6)

        cols["status"].get_widget().hide()

        self.RecommendationUsersList.set_model(self.recommendation_users_model)
        self.recommendation_users_model.set_sort_column_id(1, Gtk.SortType.ASCENDING)

        for thing in config.sections["interests"]["likes"]:
            if thing and isinstance(thing, str):
                self.likes[thing] = self.likes_model.insert_with_valuesv(-1, self.likes_column_numbers, [thing])

        for thing in config.sections["interests"]["dislikes"]:
            if thing and isinstance(thing, str):
                self.dislikes[thing] = self.dislikes_model.insert_with_valuesv(
                    -1, self.dislikes_column_numbers, [thing])

        """ Popup """

        self.til_popup_menu = popup = PopupMenu(self.frame, self.LikesList, self.on_popup_til_menu)
        popup.setup(
            ("#" + _("_Remove Item"), self.on_remove_thing_i_like),
            ("#" + _("Re_commendations for Item"), self.on_recommend_item),
            ("", None),
            ("#" + _("_Search for Item"), self.on_til_recommend_search)
        )

        self.tidl_popup_menu = popup = PopupMenu(self.frame, self.DislikesList, self.on_popup_til_menu)
        popup.setup(
            ("#" + _("_Remove Item"), self.on_remove_thing_i_dislike),
            ("", None),
            ("#" + _("_Search for Item"), self.on_tidl_recommend_search)
        )

        self.r_popup_menu = popup = PopupMenu(self.frame, self.RecommendationsList, self.on_popup_r_menu)
        popup.setup(
            ("$" + _("I _Like This"), self.on_like_recommendation),
            ("$" + _("I _Dislike This"), self.on_dislike_recommendation),
            ("#" + _("_Recommendations for Item"), self.on_recommend_recommendation),
            ("", None),
            ("#" + _("_Search for Item"), self.on_r_recommend_search)
        )

        self.ru_popup_menu = popup = PopupMenu(self.frame, self.RecommendationUsersList, self.on_popup_ru_menu)
        popup.setup_user_menu()

        self.update_visuals()

    def server_login(self):

        if self.frame.current_page_id != self.page_id:
            # Only populate recommendations if the tab is open on login
            return

        self.populate_recommendations()

    def populate_recommendations(self):
        """ Populates the lists of recommendations and similar users if empty """

        if self.populated_recommends or not self.frame.np.logged_in:
            return

        self.on_recommendations_clicked()
        self.on_similar_users_clicked()

        self.populated_recommends = True

    def recommend_search(self, item):
        self.frame.SearchEntry.set_text(item)
        self.frame.change_main_page("search")

    def on_add_thing_i_like(self, widget, *args):

        thing = widget.get_text().lower()
        widget.set_text("")

        if self.frame.np.interests.add_thing_i_like(thing):
            self.likes[thing] = self.likes_model.insert_with_valuesv(-1, self.likes_column_numbers, [thing])

    def on_add_thing_i_dislike(self, widget, *args):

        thing = widget.get_text().lower()
        widget.set_text("")

        if self.frame.np.interests.add_thing_i_hate(thing):
            self.dislikes[thing] = self.dislikes_model.insert_with_valuesv(-1, self.dislikes_column_numbers, [thing])

    def on_remove_thing_i_like(self, *args):

        thing = self.til_popup_menu.get_user()

        if not self.frame.np.interests.remove_thing_i_like(thing):
            return

        self.likes_model.remove(self.likes[thing])
        del self.likes[thing]

    def on_til_recommend_search(self, *args):
        self.recommend_search(self.til_popup_menu.get_user())

    def on_remove_thing_i_dislike(self, *args):

        thing = self.tidl_popup_menu.get_user()

        if not self.frame.np.interests.remove_thing_i_hate(thing):
            return

        self.dislikes_model.remove(self.dislikes[thing])
        del self.dislikes[thing]

    def on_tidl_recommend_search(self, *args):
        self.recommend_search(self.tidl_popup_menu.get_user())

    def on_like_recommendation(self, action, state, thing=None):

        if thing is None:
            thing = self.r_popup_menu.get_user()

        if state.get_boolean() and self.frame.np.interests.add_thing_i_like(thing):
            self.likes[thing] = self.likes_model.insert_with_valuesv(-1, self.likes_column_numbers, [thing])

        elif not state.get_boolean() and self.frame.np.interests.remove_thing_i_like(thing):
            self.likes_model.remove(self.likes[thing])
            del self.likes[thing]

        action.set_state(state)

    def on_dislike_recommendation(self, action, state, thing=None):

        if thing is None:
            thing = self.r_popup_menu.get_user()

        if state.get_boolean() and thing and self.frame.np.interests.add_thing_i_hate(thing):
            self.dislikes[thing] = self.dislikes_model.insert_with_valuesv(-1, self.dislikes_column_numbers, [thing])

        elif not state.get_boolean() and self.frame.np.interests.remove_thing_i_hate(thing):
            self.dislikes_model.remove(self.dislikes[thing])
            del self.dislikes[thing]

        action.set_state(state)

    def on_recommend_item(self, *args):

        thing = self.til_popup_menu.get_user()
        self.frame.np.interests.request_item_recommendations(thing)
        self.frame.np.interests.request_item_similar_users(thing)

    def on_recommend_recommendation(self, *args):

        thing = self.r_popup_menu.get_user()
        self.frame.np.interests.request_item_recommendations(thing)
        self.frame.np.interests.request_item_similar_users(thing)

    def on_r_recommend_search(self, *args):
        self.recommend_search(self.r_popup_menu.get_user())

    def on_recommendations_clicked(self, *args):

        if not self.likes and not self.dislikes:
            self.frame.np.interests.request_global_recommendations()
            return

        self.frame.np.interests.request_recommendations()

    def on_similar_users_clicked(self, *args):
        self.frame.np.interests.request_similar_users()

    def set_recommendations(self, recom):
        self.recommendations_model.clear()

        for (thing, rating) in recom.items():
            self.recommendations_model.insert_with_valuesv(
                -1, self.recommendations_column_numbers, [humanize(rating), thing, rating]
            )

        self.recommendations_model.set_sort_column_id(2, Gtk.SortType.DESCENDING)

    def global_recommendations(self, msg):
        self.set_recommendations({**msg.recommendations, **msg.unrecommendations})

    def recommendations(self, msg):
        self.set_recommendations({**msg.recommendations, **msg.unrecommendations})

    def item_recommendations(self, msg):
        self.set_recommendations({**msg.recommendations, **msg.unrecommendations})

    def similar_users(self, msg):

        self.recommendation_users_model.clear()
        self.recommendation_users = {}

        for user in msg.users:
            iterator = self.recommendation_users_model.insert_with_valuesv(
                -1, self.recommendation_users_column_numbers,
                [GObject.Value(GObject.TYPE_OBJECT, get_status_image(0)), user, "", "0", 0, 0, 0]
            )
            self.recommendation_users[user] = iterator

            # Request user status, speed and number of shared files
            self.frame.np.watch_user(user, force_update=True)

    def get_user_status(self, msg):

        if msg.user not in self.recommendation_users:
            return

        img = get_status_image(msg.status)
        self.recommendation_users_model.set(self.recommendation_users[msg.user], 0, img, 4, msg.status)

    def get_user_stats(self, msg):

        if msg.user not in self.recommendation_users:
            return

        h_speed = ""
        avgspeed = msg.avgspeed

        if avgspeed > 0:
            h_speed = human_speed(avgspeed)

        files = msg.files
        h_files = humanize(msg.files)

        self.recommendation_users_model.set(
            self.recommendation_users[msg.user], 2, h_speed, 3, h_files, 5, avgspeed, 6, files)

    def get_selected_item(self, treeview, column=0):

        model, iterator = treeview.get_selection().get_selected()

        if iterator is None:
            return None

        return model.get_value(iterator, column)

    def on_popup_til_menu(self, menu, widget):

        item = self.get_selected_item(widget, column=0)
        if item is None:
            return True

        menu.set_user(item)

    def on_popup_r_menu(self, menu, widget):

        item = self.get_selected_item(widget, column=1)
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

    def on_popup_ru_menu(self, menu, widget):

        user = self.get_selected_item(widget, column=1)
        if user is None:
            return True

        menu.set_user(user)
        menu.toggle_user_items()

    def on_ru_row_activated(self, treeview, path, column):

        user = self.get_selected_item(treeview, column=1)

        if user is not None:
            self.frame.np.privatechats.show_user(user)
            self.frame.change_main_page("private")

    def on_tooltip(self, widget, x, y, keyboard_mode, tooltip):
        return show_user_status_tooltip(widget, x, y, tooltip, 4)

    def update_visuals(self):

        for widget in list(self.__dict__.values()):
            update_widget_visuals(widget)
