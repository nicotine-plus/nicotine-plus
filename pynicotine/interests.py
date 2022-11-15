# COPYRIGHT (C) 2021-2022 Nicotine+ Contributors
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
from pynicotine.config import config
from pynicotine.core import core
from pynicotine.events import events


class Interests:

    def __init__(self):

        for event_name, callback in (
            ("item-similar-users", self._item_similar_users),
            ("server-login", self._server_login),
            ("similar-users", self._similar_users)
        ):
            events.connect(event_name, callback)

    def _server_login(self, msg):

        if not msg.success:
            return

        for item in config.sections["interests"]["likes"]:
            if not isinstance(item, str):
                continue

            item = item.strip().lower()

            if item:
                core.queue.append(slskmessages.AddThingILike(item))

        for item in config.sections["interests"]["dislikes"]:
            if not isinstance(item, str):
                continue

            item = item.strip().lower()

            if item:
                core.queue.append(slskmessages.AddThingIHate(item))

    def add_thing_i_like(self, item):

        item = item.strip().lower()

        if not item:
            return

        if item in config.sections["interests"]["likes"]:
            return

        config.sections["interests"]["likes"].append(item)
        config.write_configuration()
        core.queue.append(slskmessages.AddThingILike(item))

        events.emit("add-interest", item)

    def add_thing_i_hate(self, item):

        item = item.strip().lower()

        if not item:
            return

        if item in config.sections["interests"]["dislikes"]:
            return

        config.sections["interests"]["dislikes"].append(item)
        config.write_configuration()
        core.queue.append(slskmessages.AddThingIHate(item))

        events.emit("add-dislike", item)

    def remove_thing_i_like(self, item):

        if not item and not isinstance(item, str):
            return

        if item not in config.sections["interests"]["likes"]:
            return

        config.sections["interests"]["likes"].remove(item)
        config.write_configuration()
        core.queue.append(slskmessages.RemoveThingILike(item))

        events.emit("remove-interest", item)

    def remove_thing_i_hate(self, item):

        if not item and not isinstance(item, str):
            return

        if item not in config.sections["interests"]["dislikes"]:
            return

        config.sections["interests"]["dislikes"].remove(item)
        config.write_configuration()
        core.queue.append(slskmessages.RemoveThingIHate(item))

        events.emit("remove-dislike", item)

    def request_global_recommendations(self):
        core.queue.append(slskmessages.GlobalRecommendations())

    def request_item_recommendations(self, item):
        core.queue.append(slskmessages.ItemRecommendations(item))

    def request_item_similar_users(self, item):
        core.queue.append(slskmessages.ItemSimilarUsers(item))

    def request_recommendations(self):
        core.queue.append(slskmessages.Recommendations())

    def request_similar_users(self):
        core.queue.append(slskmessages.SimilarUsers())

    def _similar_users(self, msg):
        """ Server code: 110 """

        for user in msg.users:
            # Request user status, speed and number of shared files
            core.watch_user(user, force_update=True)

    def _item_similar_users(self, msg):
        """ Server code: 112 """

        for user in msg.users:
            # Request user status, speed and number of shared files
            core.watch_user(user, force_update=True)
