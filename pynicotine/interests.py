# COPYRIGHT (C) 2021 Nicotine+ Team
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

from pynicotine import slskmessages


class Interests:

    def __init__(self, core, config, queue, ui_callback=None):

        self.core = core
        self.config = config
        self.queue = queue
        self.ui_callback = None

        if hasattr(ui_callback, "interests"):
            self.ui_callback = ui_callback.interests

    def server_login(self):

        for thing in self.config.sections["interests"]["likes"]:
            if thing and isinstance(thing, str):
                self.queue.append(slskmessages.AddThingILike(thing))

        for thing in self.config.sections["interests"]["dislikes"]:
            if thing and isinstance(thing, str):
                self.queue.append(slskmessages.AddThingIHate(thing))

        if self.ui_callback:
            self.ui_callback.server_login()

    def server_disconnect(self):
        if self.ui_callback:
            self.ui_callback.server_disconnect()

    def add_thing_i_like(self, item):

        if not item and not isinstance(item, str):
            return False

        if item in self.config.sections["interests"]["likes"]:
            return False

        self.config.sections["interests"]["likes"].append(item)
        self.config.write_configuration()

        self.queue.append(slskmessages.AddThingILike(item))
        return True

    def add_thing_i_hate(self, item):

        if not item and not isinstance(item, str):
            return False

        if item in self.config.sections["interests"]["dislikes"]:
            return False

        self.config.sections["interests"]["dislikes"].append(item)
        self.config.write_configuration()

        self.queue.append(slskmessages.AddThingIHate(item))
        return True

    def remove_thing_i_like(self, item):

        if not item and not isinstance(item, str):
            return False

        if item not in self.config.sections["interests"]["likes"]:
            return False

        self.config.sections["interests"]["likes"].remove(item)
        self.config.write_configuration()
        self.queue.append(slskmessages.RemoveThingILike(item))
        return True

    def remove_thing_i_hate(self, item):

        if not item and not isinstance(item, str):
            return False

        if item not in self.config.sections["interests"]["dislikes"]:
            return False

        self.config.sections["interests"]["dislikes"].remove(item)
        self.config.write_configuration()
        self.queue.append(slskmessages.RemoveThingIHate(item))
        return True

    def request_global_recommendations(self):
        self.queue.append(slskmessages.GlobalRecommendations())

    def request_item_recommendations(self, item):
        self.queue.append(slskmessages.ItemRecommendations(item))

    def request_item_similar_users(self, item):
        self.queue.append(slskmessages.ItemSimilarUsers(item))

    def request_recommendations(self):
        self.queue.append(slskmessages.Recommendations())

    def request_similar_users(self):
        self.queue.append(slskmessages.SimilarUsers())

    def global_recommendations(self, msg):
        if self.ui_callback:
            self.ui_callback.global_recommendations(msg)

    def item_recommendations(self, msg):
        if self.ui_callback:
            self.ui_callback.item_recommendations(msg)

    def recommendations(self, msg):
        if self.ui_callback:
            self.ui_callback.recommendations(msg)

    def similar_users(self, msg):
        if self.ui_callback:
            self.ui_callback.similar_users(msg)

    def get_user_status(self, msg):
        if self.ui_callback:
            self.ui_callback.get_user_status(msg)

    def get_user_stats(self, msg):
        if self.ui_callback:
            self.ui_callback.get_user_stats(msg)
