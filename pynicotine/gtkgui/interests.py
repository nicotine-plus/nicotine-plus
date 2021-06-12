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

import os

from gi.repository import GLib
from gi.repository import GObject
from gi.repository import Gtk

from pynicotine import slskmessages
from pynicotine.config import config
from pynicotine.gtkgui.utils import load_ui_elements
from pynicotine.gtkgui.widgets.popupmenu import PopupMenu
from pynicotine.gtkgui.widgets.treeview import initialise_columns
from pynicotine.gtkgui.widgets.treeview import show_user_status_tooltip
from pynicotine.gtkgui.widgets.theme import update_widget_visuals
from pynicotine.utils import humanize
from pynicotine.utils import human_speed


class Interests:

    def __init__(self, frame):

        self.frame = frame

        load_ui_elements(self, os.path.join(self.frame.gui_dir, "ui", "interests.ui"))
        self.frame.interestsvbox.add(self.Main)

        if Gtk.get_major_version() == 4:
            self.InterestsPanedSecond.set_resize_start_child(True)
            self.InterestsPanedSecond.set_resize_end_child(False)

        else:
            self.InterestsPanedSecond.child_set_property(self.RecommendationsVbox, "resize", True)
            self.InterestsPanedSecond.child_set_property(self.SimilarUsers, "resize", False)

        self.likes = {}
        self.likes_model = Gtk.ListStore(str)
        self.likes_model.set_sort_column_id(0, Gtk.SortType.ASCENDING)

        self.likes_column_numbers = list(range(self.likes_model.get_n_columns()))
        cols = initialise_columns(
            None, self.LikesList,
            ["i_like", _("I Like"), -1, "text", None]
        )

        cols["i_like"].set_sort_column_id(0)
        self.LikesList.set_model(self.likes_model)

        self.dislikes = {}
        self.dislikes_model = Gtk.ListStore(str)
        self.dislikes_model.set_sort_column_id(0, Gtk.SortType.ASCENDING)

        self.dislikes_column_numbers = list(range(self.dislikes_model.get_n_columns()))
        cols = initialise_columns(
            None, self.DislikesList,
            ["i_dislike", _("I Dislike"), -1, "text", None]
        )

        cols["i_dislike"].set_sort_column_id(0)
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

        self.unrecommendations_model = Gtk.ListStore(
            str,  # (0) hrating
            str,  # (1) item
            int   # (2) rating
        )

        self.unrecommendations_column_numbers = list(range(self.unrecommendations_model.get_n_columns()))
        cols = initialise_columns(
            None, self.UnrecommendationsList,
            ["rating", _("Rating"), 0, "number", None],
            ["item", _("Item"), -1, "text", None]
        )

        cols["rating"].set_sort_column_id(2)
        cols["item"].set_sort_column_id(1)

        self.UnrecommendationsList.set_model(self.unrecommendations_model)

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

        self.tidl_popup_menu = popup = PopupMenu(self.frame, self.DislikesList, self.on_popup_tidl_menu)
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

    def recommend_search(self, item):
        self.frame.SearchEntry.set_text(item)
        self.frame.change_main_page("search")

    def on_add_thing_i_like(self, widget, *args):

        thing = widget.get_text()
        widget.set_text("")

        if thing and thing.lower() not in config.sections["interests"]["likes"]:
            thing = thing.lower()
            config.sections["interests"]["likes"].append(thing)
            self.likes[thing] = self.likes_model.insert_with_valuesv(-1, self.likes_column_numbers, [thing])
            config.write_configuration()
            self.frame.np.queue.append(slskmessages.AddThingILike(thing))

    def on_add_thing_i_dislike(self, widget, *args):

        thing = widget.get_text()
        widget.set_text("")

        if thing and thing.lower() not in config.sections["interests"]["dislikes"]:
            thing = thing.lower()
            config.sections["interests"]["dislikes"].append(thing)
            self.dislikes[thing] = self.dislikes_model.insert_with_valuesv(-1, self.dislikes_column_numbers, [thing])
            config.write_configuration()
            self.frame.np.queue.append(slskmessages.AddThingIHate(thing))

    def on_remove_thing_i_like(self, *args):

        thing = self.til_popup_menu.get_user()

        if thing not in config.sections["interests"]["likes"]:
            return

        self.likes_model.remove(self.likes[thing])
        del self.likes[thing]
        config.sections["interests"]["likes"].remove(thing)

        config.write_configuration()
        self.frame.np.queue.append(slskmessages.RemoveThingILike(thing))

    def on_til_recommend_search(self, *args):
        self.recommend_search(self.til_popup_menu.get_user())

    def on_remove_thing_i_dislike(self, *args):

        thing = self.tidl_popup_menu.get_user()

        if thing not in config.sections["interests"]["dislikes"]:
            return

        self.dislikes_model.remove(self.dislikes[thing])
        del self.dislikes[thing]
        config.sections["interests"]["dislikes"].remove(thing)

        config.write_configuration()
        self.frame.np.queue.append(slskmessages.RemoveThingIHate(thing))

    def on_tidl_recommend_search(self, *args):
        self.recommend_search(self.tidl_popup_menu.get_user())

    def on_like_recommendation(self, action, state, thing=None):

        if thing is None:
            thing = self.r_popup_menu.get_user()

        if state.get_boolean() and \
                thing and thing not in config.sections["interests"]["likes"]:
            config.sections["interests"]["likes"].append(thing)
            self.likes[thing] = self.likes_model.insert_with_valuesv(-1, self.likes_column_numbers, [thing])

            config.write_configuration()
            self.frame.np.queue.append(slskmessages.AddThingILike(thing))

        elif not state and \
                thing and thing in config.sections["interests"]["likes"]:
            self.likes_model.remove(self.likes[thing])
            del self.likes[thing]
            config.sections["interests"]["likes"].remove(thing)

            config.write_configuration()
            self.frame.np.queue.append(slskmessages.RemoveThingILike(thing))

        action.set_state(state)

    def on_dislike_recommendation(self, action, state, thing=None):

        if thing is None:
            thing = self.r_popup_menu.get_user()

        if state.get_boolean() and \
                thing and thing not in config.sections["interests"]["dislikes"]:
            config.sections["interests"]["dislikes"].append(thing)
            self.dislikes[thing] = self.dislikes_model.insert_with_valuesv(-1, self.dislikes_column_numbers, [thing])

            config.write_configuration()
            self.frame.np.queue.append(slskmessages.AddThingIHate(thing))

        elif not state and \
                thing and thing in config.sections["interests"]["dislikes"]:
            self.dislikes_model.remove(self.dislikes[thing])
            del self.dislikes[thing]
            config.sections["interests"]["dislikes"].remove(thing)

            config.write_configuration()
            self.frame.np.queue.append(slskmessages.RemoveThingIHate(thing))

        action.set_state(state)

    def on_recommend_item(self, *args):

        thing = self.til_popup_menu.get_user()
        self.frame.np.queue.append(slskmessages.ItemRecommendations(thing))
        self.frame.np.queue.append(slskmessages.ItemSimilarUsers(thing))

    def on_recommend_recommendation(self, *args):

        thing = self.r_popup_menu.get_user()
        self.frame.np.queue.append(slskmessages.ItemRecommendations(thing))
        self.frame.np.queue.append(slskmessages.ItemSimilarUsers(thing))

    def on_r_recommend_search(self, *args):
        self.recommend_search(self.r_popup_menu.get_user())

    def on_global_recommendations_clicked(self, *args):
        self.frame.np.queue.append(slskmessages.GlobalRecommendations())

    def on_recommendations_clicked(self, *args):
        self.frame.np.queue.append(slskmessages.Recommendations())

    def on_similar_users_clicked(self, *args):
        self.frame.np.queue.append(slskmessages.SimilarUsers())

    def set_recommendations(self, title, recom):
        self.recommendations_model.clear()

        for (thing, rating) in recom.items():
            self.recommendations_model.insert_with_valuesv(
                -1, self.recommendations_column_numbers, [humanize(rating), thing, rating]
            )

        self.recommendations_model.set_sort_column_id(2, Gtk.SortType.DESCENDING)

    def set_unrecommendations(self, title, recom):
        self.unrecommendations_model.clear()

        for (thing, rating) in recom.items():
            self.unrecommendations_model.insert_with_valuesv(
                -1, self.unrecommendations_column_numbers, [humanize(rating), thing, rating]
            )

        self.unrecommendations_model.set_sort_column_id(2, Gtk.SortType.ASCENDING)

    def global_recommendations(self, msg):
        self.set_recommendations("Global recommendations", msg.recommendations)
        self.set_unrecommendations("Unrecommendations", msg.unrecommendations)

    def recommendations(self, msg):
        self.set_recommendations("Recommendations", msg.recommendations)
        self.set_unrecommendations("Unrecommendations", msg.unrecommendations)

    def item_recommendations(self, msg):
        self.set_recommendations(_("Recommendations for %s") % msg.thing, msg.recommendations)
        self.set_unrecommendations("Unrecommendations", msg.unrecommendations)

    def similar_users(self, msg):
        self.recommendation_users_model.clear()
        self.recommendation_users = {}

        for user in msg.users:
            iterator = self.recommendation_users_model.insert_with_valuesv(
                -1, self.recommendation_users_column_numbers,
                [GObject.Value(GObject.TYPE_OBJECT, self.frame.images["offline"]), user, "0", "0", 0, 0, 0]
            )
            self.recommendation_users[user] = iterator

            # Request user status, speed and number of shared files
            self.frame.np.watch_user(user, force_update=True)

    def get_user_status(self, msg):
        if msg.user not in self.recommendation_users:
            return

        img = self.frame.get_status_image(msg.status)
        self.recommendation_users_model.set(self.recommendation_users[msg.user], 0, img, 4, msg.status)

    def get_user_stats(self, msg):
        if msg.user not in self.recommendation_users:
            return

        self.recommendation_users_model.set(
            self.recommendation_users[msg.user],
            2, human_speed(msg.avgspeed), 3, humanize(msg.files), 5, msg.avgspeed, 6, msg.files)

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

    def on_popup_tidl_menu(self, menu, widget):

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

        user = self.get_selected_item(treeview)

        if user is not None:
            self.frame.privatechats.send_message(user)
            self.frame.change_main_page("private")

    def on_tooltip(self, widget, x, y, keyboard_mode, tooltip):
        return show_user_status_tooltip(widget, x, y, tooltip, 4)

    def update_visuals(self):

        for widget in list(self.__dict__.values()):
            update_widget_visuals(widget)
