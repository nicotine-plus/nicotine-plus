# COPYRIGHT (C) 2021-2024 Nicotine+ Contributors
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

from pynicotine.config import config
from pynicotine.core import core
from pynicotine.events import events
from pynicotine.slskmessages import AddThingIHate
from pynicotine.slskmessages import AddThingILike
from pynicotine.slskmessages import GlobalRecommendations
from pynicotine.slskmessages import ItemRecommendations
from pynicotine.slskmessages import ItemSimilarUsers
from pynicotine.slskmessages import Recommendations
from pynicotine.slskmessages import RemoveThingILike
from pynicotine.slskmessages import RemoveThingIHate
from pynicotine.slskmessages import SimilarUsers


class SimilarUser:
    __slots__ = ("username", "rating")

    def __init__(self, username, rating=None):
        self.username = username
        self.rating = rating


class Interests:
    __slots__ = ("similar_users",)

    def __init__(self):

        self.similar_users = {}

        for event_name, callback in (
            ("item-similar-users", self._item_similar_users),
            ("quit", self._quit),
            ("server-login", self._server_login),
            ("similar-users", self._similar_users)
        ):
            events.connect(event_name, callback)

    def _quit(self):
        self.similar_users.clear()

    def _server_login(self, msg):

        if not msg.success:
            return

        for item in config.sections["interests"]["likes"]:
            if not isinstance(item, str):
                continue

            item = item.strip().lower()

            if item:
                core.send_message_to_server(AddThingILike(item))

        for item in config.sections["interests"]["dislikes"]:
            if not isinstance(item, str):
                continue

            item = item.strip().lower()

            if item:
                core.send_message_to_server(AddThingIHate(item))

    def add_thing_i_like(self, item):

        item = item.strip().lower()

        if not item:
            return

        if item in config.sections["interests"]["likes"]:
            return

        config.sections["interests"]["likes"].append(item)
        config.write_configuration()
        core.send_message_to_server(AddThingILike(item))

        events.emit("add-interest", item)

    def add_thing_i_hate(self, item):

        item = item.strip().lower()

        if not item:
            return

        if item in config.sections["interests"]["dislikes"]:
            return

        config.sections["interests"]["dislikes"].append(item)
        config.write_configuration()
        core.send_message_to_server(AddThingIHate(item))

        events.emit("add-dislike", item)

    def remove_thing_i_like(self, item):

        if not item and not isinstance(item, str):
            return

        if item not in config.sections["interests"]["likes"]:
            return

        config.sections["interests"]["likes"].remove(item)
        config.write_configuration()
        core.send_message_to_server(RemoveThingILike(item))

        events.emit("remove-interest", item)

    def remove_thing_i_hate(self, item):

        if not item and not isinstance(item, str):
            return

        if item not in config.sections["interests"]["dislikes"]:
            return

        config.sections["interests"]["dislikes"].remove(item)
        config.write_configuration()
        core.send_message_to_server(RemoveThingIHate(item))

        events.emit("remove-dislike", item)

    def request_global_recommendations(self):
        core.send_message_to_server(GlobalRecommendations())

    def request_item_recommendations(self, item):
        core.send_message_to_server(ItemRecommendations(item))

    def request_item_similar_users(self, item):
        core.send_message_to_server(ItemSimilarUsers(item))

    def request_recommendations(self):
        core.send_message_to_server(Recommendations())

    def request_similar_users(self):
        core.send_message_to_server(SimilarUsers())

    def _similar_users(self, msg, has_ratings=True):
        """Server code 110."""

        new_users = set(msg.users)

        # Unwatch and remove old users
        for username in self.similar_users:
            if username not in new_users:
                core.users.unwatch_user(username, context="interests")

        self.similar_users.clear()

        # Add new users
        for username in msg.users:
            rating = msg.users[username] if has_ratings else None
            self.similar_users[username] = SimilarUser(username, rating)

            # Request user status, speed and number of shared files
            core.users.watch_user(username, context="interests")

    def _item_similar_users(self, msg):
        """Server code 112."""

        self._similar_users(msg, has_ratings=False)
