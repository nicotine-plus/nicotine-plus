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

import time

from collections import deque
from threading import Thread


EVENT_NAMES = {
    # General
    "add-privileged-user",
    "admin-message",
    "change-password",
    "check-privileges",
    "cli-command",
    "cli-prompt-finished",
    "confirm-quit",
    "connect-to-peer",
    "enable-message-queue",
    "hide-scan-progress",
    "invalid-password",
    "log-message",
    "peer-address",
    "peer-connection-closed",
    "peer-connection-error",
    "privileged-users",
    "quit",
    "remove-privileged-user",
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

    # Notification messages
    "show-notification",
    "show-chatroom-notification",
    "show-download-notification",
    "show-private-chat-notification",
    "show-search-notification",

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
    "global-room-message",
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

    # Network filter
    "ban-user",
    "ignore-user",
    "unban-user",
    "unignore-user",

    # Private chat
    "clear-private-messages",
    "echo-private-message",
    "message-user",
    "private-chat-completion-list",
    "private-chat-remove-user",
    "private-chat-show-user",
    "send-private-message",

    # Search
    "add-wish",
    "do-search",
    "file-search-request-distributed",
    "file-search-request-server",
    "file-search-response",
    "remove-search",
    "remove-wish",
    "set-wishlist-interval",
    "show-search",

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
    "update-download-limits",
    "update-downloads",
    "update-upload",
    "update-upload-limits",
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
}


class Events:

    def __init__(self):

        self._callbacks = {}
        self._thread_events = deque()
        self._scheduler_events = {}
        self._scheduler_event_id = 0

        Thread(target=self._run_scheduler, name="SchedulerThread", daemon=True).start()

    def connect(self, event_name, function):

        if event_name not in EVENT_NAMES:
            raise ValueError(f"Unknown event {event_name}")

        if event_name not in self._callbacks:
            self._callbacks[event_name] = []

        self._callbacks[event_name].append(function)

    def disconnect(self, event_name, function):
        self._callbacks[event_name].remove(function)

    def emit(self, event_name, *args, **kwargs):
        for function in self._callbacks.get(event_name, []):
            function(*args, **kwargs)

    def emit_main_thread(self, event_name, *args, **kwargs):
        self._thread_events.append((event_name, args, kwargs))

    def invoke_main_thread(self, callback, *args, **kwargs):
        self.emit_main_thread("thread-callback", callback, *args, **kwargs)

    def schedule(self, delay, callback, repeat=False):

        self._scheduler_event_id += 1
        self._scheduler_events[self._scheduler_event_id] = ((time.time() + delay), delay, repeat, callback)

        return self._scheduler_event_id

    def cancel_scheduled(self, event_id):
        self._scheduler_events.pop(event_id, None)

    def process_thread_events(self):
        """ Called by the main loop 20 times per second to emit thread events in the main thread """

        if not self._thread_events:
            return

        event_list = []

        while self._thread_events:
            event_list.append(self._thread_events.popleft())

        for event_name, args, kwargs in event_list:
            self.emit(event_name, *args, **kwargs)

    def _run_scheduler(self):

        while True:
            if not self._scheduler_events:
                time.sleep(1)
                continue

            event_id, event_data = min(self._scheduler_events.items(), key=lambda x: x[1][0])  # Compare timestamps
            event_time, delay, repeat, callback = event_data
            current_time = time.time()
            sleep_time = (event_time - current_time)

            if sleep_time <= 0:
                self.invoke_main_thread(callback)

                if repeat:
                    self._scheduler_events[event_id] = ((event_time + delay), delay, repeat, callback)
                else:
                    self._scheduler_events.pop(event_id, None)

                continue

            time.sleep(min(sleep_time, 1))


events = Events()
