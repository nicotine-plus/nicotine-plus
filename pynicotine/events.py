# COPYRIGHT (C) 2022 Nicotine+ Contributors
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


EVENT_NAMES = set([
    # General
    "add-privileged-user",
    "admin-message",
    "change-password",
    "check-privileges",
    "cli-command",
    "confirm-quit",
    "connect-to-peer",
    "enable-message-queue",
    "hide-scan-progress",
    "invalid-password",
    "log-message",
    "show-text-notification",
    "peer-address",
    "peer-connection-closed",
    "peer-connection-error",
    "privileged-users",
    "quit",
    "remove-privileged-user",
    "scheduler-callback",
    "server-login",
    "server-disconnect",
    "server-timeout",
    "set-away-mode",
    "set-connection-stats",
    "set-scan-indeterminate",
    "set-scan-progress",
    "setup",
    "show-scan-progress",
    "shares-unavailable",
    "start",
    "thread-callback",
    "user-country",
    "user-stats",
    "user-status",
    "watch-user",

    # Buddy list
    "add-buddy",
    "buddy-note",
    "buddy-notify",
    "buddy-last-seen",
    "buddy-prioritized",
    "buddy-trusted",
    "remove-buddy",

    # Chatrooms
    "clear-room-messages",
    "echo-room-message",
    "join-room",
    "leave-room",
    "private-room-add-operator",
    "private-room-add-user",
    "private-room-added",
    "private-room-disown",
    "private-room-operator-added",
    "private-room-operator-removed",
    "private-room-owned",
    "private-room-remove-operator",
    "private-room-remove-user",
    "private-room-removed",
    "private-room-toggle",
    "private-room-users",
    "public-room-message",
    "remove-room",
    "room-completion-list",
    "room-list",
    "say-chat-room",
    "show-room",
    "ticker-add",
    "ticker-remove",
    "ticker-set",
    "user-joined-room",
    "user-left-room",

    # Interests
    "add-dislike",
    "add-interest",
    "global-recommendations",
    "item-recommendations",
    "item-similar-users",
    "recommendations",
    "remove-dislike",
    "remove-interest",
    "similar-users",

    # Private chat
    "clear-private-messages",
    "echo-private-message",
    "message-user",
    "private-chat-completion-list",
    "private-chat-show-user",
    "private-chat-remove-user",
    "send-private-message",

    # Search
    "add-wish",
    "distributed-search-request",
    "do-search",
    "file-search-response",
    "remove-search",
    "remove-wish",
    "server-search-request",
    "set-wishlist-interval",

    # Statistics
    "update-stat-value",

    # Shares
    "folder-contents-request",
    "shared-file-list-progress",
    "shared-file-list-request",
    "shared-file-list-response",
    "user-browse-remove-user",
    "user-browse-show-user",

    # Transfers
    "abort-download",
    "abort-downloads",
    "abort-upload",
    "abort-uploads",
    "clear-download",
    "clear-downloads",
    "clear-upload",
    "clear-uploads",
    "download-connection-closed",
    "download-file-error",
    "download-large-folder",
    "download-notification",
    "file-download-init",
    "file-upload-init",
    "file-download-progress",
    "file-upload-progress",
    "folder-contents-response",
    "place-in-queue-request",
    "place-in-queue-response",
    "queue-upload",
    "transfer-request",
    "transfer-response",
    "update-download",
    "update-downloads",
    "update-upload",
    "update-uploads",
    "upload-connection-closed",
    "upload-denied",
    "upload-failed",
    "upload-file-error",
    "upload-notification",

    # User info
    "user-info-progress",
    "user-info-remove-user",
    "user-info-request",
    "user-info-response",
    "user-info-show-user",
    "user-interests",
])


class Events:

    def __init__(self):
        self._callbacks = {}

    def connect(self, event_name, function):

        if event_name not in EVENT_NAMES:
            raise ValueError("Unknown event %s" % event_name)

        if event_name not in self._callbacks:
            self._callbacks[event_name] = []

        self._callbacks[event_name].append(function)

    def disconnect(self, event_name, function):
        self._callbacks[event_name].remove(function)

    def emit(self, event_name, *args, **kwargs):
        for function in self._callbacks.get(event_name, []):
            function(*args, **kwargs)


events = Events()
