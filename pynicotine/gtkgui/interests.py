# COPYRIGHT (C) 2020 Nicotine+ Team
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

from gettext import gettext as _

from gi.repository import Gdk
from gi.repository import Gtk
from gi.repository import GObject

from pynicotine import slskmessages
from pynicotine.gtkgui.utils import humanize
from pynicotine.gtkgui.utils import human_speed
from pynicotine.gtkgui.utils import initialise_columns
from pynicotine.gtkgui.utils import load_ui_elements
from pynicotine.gtkgui.utils import PopupMenu
from pynicotine.gtkgui.utils import update_widget_visuals


class Interests:

    def __init__(self, frame, np):

        self.frame = frame
        self.np = np

        load_ui_elements(self, os.path.join(self.frame.gui_dir, "ui", "interests.ui"))

        self.likes = {}
        self.likes_model = Gtk.ListStore(str)
        self.likes_model.set_sort_column_id(0, Gtk.SortType.ASCENDING)

        cols = initialise_columns(
            self.LikesList,
            [_("I like") + ":", 0, "text"]
        )

        cols[0].set_sort_column_id(0)
        self.LikesList.set_model(self.likes_model)

        self.til_popup_menu = popup = PopupMenu(self.frame)

        popup.setup(
            ("#" + _("_Remove this item"), self.on_remove_thing_i_like),
            ("#" + _("Re_commendations for this item"), self.on_recommend_item),
            ("", None),
            ("#" + _("_Search for this item"), self.on_recommend_search)
        )

        self.LikesList.connect("button_press_event", self.on_popup_til_menu)

        self.dislikes = {}
        self.dislikes_model = Gtk.ListStore(str)
        self.dislikes_model.set_sort_column_id(0, Gtk.SortType.ASCENDING)

        cols = initialise_columns(
            self.DislikesList,
            [_("I dislike") + ":", 0, "text"]
        )

        cols[0].set_sort_column_id(0)
        self.DislikesList.set_model(self.dislikes_model)

        self.tidl_popup_menu = popup = PopupMenu(self.frame)

        popup.setup(
            ("#" + _("_Remove this item"), self.on_remove_thing_i_dislike),
            ("", None),
            ("#" + _("_Search for this item"), self.on_recommend_search)
        )

        self.DislikesList.connect("button_press_event", self.on_popup_tidl_menu)

        cols = initialise_columns(
            self.RecommendationsList,
            [_("Rating"), 0, "text"],
            [_("Item"), -1, "text"]
        )

        cols[0].set_sort_column_id(2)
        cols[1].set_sort_column_id(1)

        self.recommendations_model = Gtk.ListStore(
            str,  # (0) hrating
            str,  # (1) item
            int   # (2) rating
        )
        self.RecommendationsList.set_model(self.recommendations_model)

        self.r_popup_menu = popup = PopupMenu(self.frame)

        popup.setup(
            ("$" + _("I _like this"), self.on_like_recommendation),
            ("$" + _("I _don't like this"), self.on_dislike_recommendation),
            ("#" + _("_Recommendations for this item"), self.on_recommend_recommendation),
            ("", None),
            ("#" + _("_Search for this item"), self.on_recommend_search)
        )

        self.RecommendationsList.connect("button_press_event", self.on_popup_r_menu)

        cols = initialise_columns(
            self.UnrecommendationsList,
            [_("Rating"), 0, "text"],
            [_("Item"), -1, "text"]
        )

        cols[0].set_sort_column_id(2)
        cols[1].set_sort_column_id(1)

        self.unrecommendations_model = Gtk.ListStore(
            str,  # (0) hrating
            str,  # (1) item
            int   # (2) rating
        )
        self.UnrecommendationsList.set_model(self.unrecommendations_model)

        self.ur_popup_menu = popup = PopupMenu(self.frame)

        popup.setup(
            ("$" + _("I _like this"), self.on_like_recommendation),
            ("$" + _("I _don't like this"), self.on_dislike_recommendation),
            ("#" + _("_Recommendations for this item"), self.on_recommend_recommendation),
            ("", None),
            ("#" + _("_Search for this item"), self.on_recommend_search)
        )

        self.UnrecommendationsList.connect("button_press_event", self.on_popup_un_rec_menu)

        cols = initialise_columns(
            self.RecommendationUsersList,
            ["", 25, "pixbuf"],
            [_("User"), 100, "text"],
            [_("Speed"), 0, "text"],
            [_("Files"), 0, "text"],
        )

        cols[0].set_sort_column_id(4)
        cols[1].set_sort_column_id(1)
        cols[2].set_sort_column_id(5)
        cols[3].set_sort_column_id(6)

        self.recommendation_users = {}
        self.recommendation_users_model = Gtk.ListStore(
            GObject.TYPE_OBJECT,  # (0) status icon
            str,                  # (1) user
            str,                  # (2) hspeed
            str,                  # (3) hfiles
            GObject.TYPE_INT64,   # (4) status
            GObject.TYPE_UINT64,  # (5) speed
            GObject.TYPE_UINT64   # (6) file count
        )
        self.RecommendationUsersList.set_model(self.recommendation_users_model)
        self.recommendation_users_model.set_sort_column_id(1, Gtk.SortType.ASCENDING)

        self.ru_popup_menu = popup = PopupMenu(self.frame)
        popup.setup(
            ("#" + _("Send _message"), popup.on_send_message),
            ("", None),
            ("#" + _("Show IP a_ddress"), popup.on_show_ip_address),
            ("#" + _("Get user i_nfo"), popup.on_get_user_info),
            ("#" + _("Brow_se files"), popup.on_browse_user),
            ("#" + _("Gi_ve privileges"), popup.on_give_privileges),
            ("", None),
            ("$" + _("_Add user to list"), popup.on_add_to_list),
            ("$" + _("_Ban this user"), popup.on_ban_user),
            ("$" + _("_Ignore this user"), popup.on_ignore_user)
        )

        self.RecommendationUsersList.connect("button_press_event", self.on_popup_ru_menu)

        for thing in self.np.config.sections["interests"]["likes"]:
            self.likes[thing] = self.likes_model.append([thing])

        for thing in self.np.config.sections["interests"]["dislikes"]:
            self.dislikes[thing] = self.dislikes_model.append([thing])

        self.update_visuals()

    def on_add_thing_i_like(self, widget):
        thing = self.AddLikeEntry.get_text()
        self.AddLikeEntry.set_text("")

        if thing and thing.lower() not in self.np.config.sections["interests"]["likes"]:
            thing = thing.lower()
            self.np.config.sections["interests"]["likes"].append(thing)
            self.likes[thing] = self.likes_model.append([thing])
            self.np.config.write_configuration()
            self.np.queue.put(slskmessages.AddThingILike(thing))

    def on_add_thing_i_dislike(self, widget):
        thing = self.AddDislikeEntry.get_text()
        self.AddDislikeEntry.set_text("")

        if thing and thing.lower() not in self.np.config.sections["interests"]["dislikes"]:
            thing = thing.lower()
            self.np.config.sections["interests"]["dislikes"].append(thing)
            self.dislikes[thing] = self.dislikes_model.append([thing])
            self.np.config.write_configuration()
            self.np.queue.put(slskmessages.AddThingIHate(thing))

    def on_remove_thing_i_like(self, widget):
        thing = self.til_popup_menu.get_user()

        if thing not in self.np.config.sections["interests"]["likes"]:
            return

        self.likes_model.remove(self.likes[thing])
        del self.likes[thing]
        self.np.config.sections["interests"]["likes"].remove(thing)

        self.np.config.write_configuration()
        self.np.queue.put(slskmessages.RemoveThingILike(thing))

    def on_remove_thing_i_dislike(self, widget):
        thing = self.tidl_popup_menu.get_user()

        if thing not in self.np.config.sections["interests"]["dislikes"]:
            return

        self.dislikes_model.remove(self.dislikes[thing])
        del self.dislikes[thing]
        self.np.config.sections["interests"]["dislikes"].remove(thing)

        self.np.config.write_configuration()
        self.np.queue.put(slskmessages.RemoveThingIHate(thing))

    def on_like_recommendation(self, widget):
        thing = widget.get_parent().get_user()

        if widget.get_active() and thing not in self.np.config.sections["interests"]["likes"]:
            self.np.config.sections["interests"]["likes"].append(thing)
            self.likes[thing] = self.likes_model.append([thing])

            self.np.config.write_configuration()
            self.np.queue.put(slskmessages.AddThingILike(thing))

        elif not widget.get_active() and thing in self.np.config.sections["interests"]["likes"]:
            self.likes_model.remove(self.likes[thing])
            del self.likes[thing]
            self.np.config.sections["interests"]["likes"].remove(thing)

            self.np.config.write_configuration()
            self.np.queue.put(slskmessages.RemoveThingILike(thing))

    def on_dislike_recommendation(self, widget):
        thing = widget.get_parent().get_user()

        if widget.get_active() and thing not in self.np.config.sections["interests"]["dislikes"]:
            self.np.config.sections["interests"]["dislikes"].append(thing)
            self.dislikes[thing] = self.dislikes_model.append([thing])

            self.np.config.write_configuration()
            self.np.queue.put(slskmessages.AddThingIHate(thing))

        elif not widget.get_active() and thing in self.np.config.sections["interests"]["dislikes"]:
            self.dislikes_model.remove(self.dislikes[thing])
            del self.dislikes[thing]
            self.np.config.sections["interests"]["dislikes"].remove(thing)

            self.np.config.write_configuration()
            self.np.queue.put(slskmessages.RemoveThingIHate(thing))

    def on_recommend_item(self, widget):
        thing = self.til_popup_menu.get_user()
        self.np.queue.put(slskmessages.ItemRecommendations(thing))
        self.np.queue.put(slskmessages.ItemSimilarUsers(thing))

    def on_recommend_recommendation(self, widget):
        thing = self.r_popup_menu.get_user()
        self.np.queue.put(slskmessages.ItemRecommendations(thing))
        self.np.queue.put(slskmessages.ItemSimilarUsers(thing))

    def on_recommend_search(self, widget):
        thing = widget.get_parent().get_user()
        self.frame.search_entry.set_text(thing)
        self.frame.change_main_page("search")

    def on_global_recommendations_clicked(self, widget):
        self.np.queue.put(slskmessages.GlobalRecommendations())

    def on_recommendations_clicked(self, widget):
        self.np.queue.put(slskmessages.Recommendations())

    def on_similar_users_clicked(self, widget):
        self.np.queue.put(slskmessages.SimilarUsers())

    def set_recommendations(self, title, recom):
        self.recommendations_model.clear()

        for (thing, rating) in recom.items():
            self.recommendations_model.append([humanize(rating), thing, rating])

        self.recommendations_model.set_sort_column_id(2, Gtk.SortType.DESCENDING)

    def set_unrecommendations(self, title, recom):
        self.unrecommendations_model.clear()

        for (thing, rating) in recom.items():
            self.unrecommendations_model.append([humanize(rating), thing, rating])

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
            iterator = self.recommendation_users_model.append([self.frame.images["offline"], user, "0", "0", 0, 0, 0])
            self.recommendation_users[user] = iterator
            self.np.queue.put(slskmessages.AddUser(user))

    def get_user_status(self, msg):
        if msg.user not in self.recommendation_users:
            return

        img = self.frame.get_status_image(msg.status)
        self.recommendation_users_model.set(self.recommendation_users[msg.user], 0, img, 4, msg.status)

    def get_user_stats(self, msg):
        if msg.user not in self.recommendation_users:
            return

        self.recommendation_users_model.set(self.recommendation_users[msg.user], 2, human_speed(msg.avgspeed), 3, humanize(msg.files), 5, msg.avgspeed, 6, msg.files)

    def on_popup_ru_menu(self, widget, event):
        items = self.ru_popup_menu.get_children()
        d = self.RecommendationUsersList.get_path_at_pos(int(event.x), int(event.y))

        if not d:
            return

        path, column, x, y = d
        user = self.recommendation_users_model.get_value(self.recommendation_users_model.get_iter(path), 1)

        if event.button != 3:
            if event.type == Gdk.EventType._2BUTTON_PRESS:
                self.privatechats.send_message(user)
                self.change_main_page("private")
            return

        self.ru_popup_menu.set_user(user)
        items[7].set_active(user in (i[0] for i in self.np.config.sections["server"]["userlist"]))
        items[8].set_active(user in self.np.config.sections["server"]["banlist"])
        items[9].set_active(user in self.np.config.sections["server"]["ignorelist"])

        self.ru_popup_menu.popup(None, None, None, None, event.button, event.time)

    def on_popup_til_menu(self, widget, event):
        if event.button != 3:
            return

        d = self.LikesList.get_path_at_pos(int(event.x), int(event.y))

        if not d:
            return

        path, column, x, y = d
        iterator = self.likes_model.get_iter(path)
        thing = self.likes_model.get_value(iterator, 0)

        self.til_popup_menu.set_user(thing)
        self.til_popup_menu.popup(None, None, None, None, event.button, event.time)

    def on_popup_tidl_menu(self, widget, event):
        if event.button != 3:
            return

        d = self.DislikesList.get_path_at_pos(int(event.x), int(event.y))

        if not d:
            return

        path, column, x, y = d
        iterator = self.dislikes_model.get_iter(path)
        thing = self.dislikes_model.get_value(iterator, 0)

        self.tidl_popup_menu.set_user(thing)
        self.tidl_popup_menu.popup(None, None, None, None, event.button, event.time)

    def on_popup_r_menu(self, widget, event):
        if event.button != 3:
            return

        d = self.RecommendationsList.get_path_at_pos(int(event.x), int(event.y))

        if not d:
            return

        path, column, x, y = d
        iterator = self.recommendations_model.get_iter(path)
        thing = self.recommendations_model.get_value(iterator, 0)
        items = self.r_popup_menu.get_children()

        self.r_popup_menu.set_user(thing)
        items[0].set_active(thing in self.np.config.sections["interests"]["likes"])
        items[1].set_active(thing in self.np.config.sections["interests"]["dislikes"])

        self.r_popup_menu.popup(None, None, None, None, event.button, event.time)

    def on_popup_un_rec_menu(self, widget, event):
        if event.button != 3:
            return

        d = self.UnrecommendationsList.get_path_at_pos(int(event.x), int(event.y))

        if not d:
            return

        path, column, x, y = d
        iterator = self.unrecommendations_model.get_iter(path)
        thing = self.unrecommendations_model.get_value(iterator, 0)
        items = self.ur_popup_menu.get_children()

        self.ur_popup_menu.set_user(thing)
        items[0].set_active(thing in self.np.config.sections["interests"]["likes"])
        items[1].set_active(thing in self.np.config.sections["interests"]["dislikes"])

        self.ur_popup_menu.popup(None, None, None, None, event.button, event.time)

    def update_visuals(self):

        for widget in self.__dict__.values():
            update_widget_visuals(widget)
