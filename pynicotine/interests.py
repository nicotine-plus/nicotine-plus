# SPDX-FileCopyrightText: 2021-2025 Nicotine+ Contributors
# SPDX-License-Identifier: GPL-3.0-or-later
from __future__ import annotations

from typing import TYPE_CHECKING

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

if TYPE_CHECKING:
    from pynicotine.slskmessages import Login


class Interests:
    __slots__ = ("similar_users",)

    MAX_SIMILAR_USERS = 200

    def __init__(self):

        self.similar_users = {}

        for event_name, callback in (
            ("item-similar-users", self._item_similar_users),
            ("quit", self._quit),
            ("server-login", self._server_login),
            ("similar-users", self._similar_users)
        ):
            events.connect(event_name, callback)

    def _quit(self) -> None:
        self.similar_users.clear()

    def _server_login(self, msg: Login) -> None:

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

    def add_thing_i_like(self, item) -> None:

        item = item.strip().lower()

        if not item:
            return

        if item in config.sections["interests"]["likes"]:
            return

        config.sections["interests"]["likes"].append(item)
        config.write_configuration()
        core.send_message_to_server(AddThingILike(item))

        events.emit("add-interest", item)

    def add_thing_i_hate(self, item) -> None:

        item = item.strip().lower()

        if not item:
            return

        if item in config.sections["interests"]["dislikes"]:
            return

        config.sections["interests"]["dislikes"].append(item)
        config.write_configuration()
        core.send_message_to_server(AddThingIHate(item))

        events.emit("add-dislike", item)

    def remove_thing_i_like(self, item) -> None:

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

    def request_global_recommendations(self) -> None:
        core.send_message_to_server(GlobalRecommendations())

    def request_item_recommendations(self, item: str) -> None:
        core.send_message_to_server(ItemRecommendations(item))

    def request_item_similar_users(self, item: str) -> None:
        core.send_message_to_server(ItemSimilarUsers(item))

    def request_recommendations(self) -> None:
        core.send_message_to_server(Recommendations())

    def request_similar_users(self) -> None:
        core.send_message_to_server(SimilarUsers())

    def _similar_users(self, msg: SimilarUsers) -> None:
        """Server code 110."""

        # Limit number of users to prevent excessive status requests
        msg.users = msg.users[:self.MAX_SIMILAR_USERS]
        new_usernames = {x.username for x in msg.users}

        # Unwatch and remove old users
        for username, similar_user in self.similar_users.items():
            if similar_user.username not in new_usernames:
                core.users.unwatch_user(username, context="interests")

        self.similar_users.clear()

        # Add new users
        for user in msg.users:
            self.similar_users[user.username] = user

            # Request user status, speed and number of shared files
            core.users.watch_user(user.username, context="interests")

    def _item_similar_users(self, msg: ItemSimilarUsers) -> None:
        """Server code 112."""

        self._similar_users(msg)
