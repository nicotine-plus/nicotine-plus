# COPYRIGHT (C) 2022-2024 Nicotine+ Contributors
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
    "check-latest-version",
    "cli-command",
    "cli-prompt-finished",
    "confirm-quit",
    "enable-message-queue",
    "log-message",
    "queue-network-message",
    "quit",
    "schedule-quit",
    "set-connection-stats",
    "setup",
    "start",
    "thread-callback",

    # Users
    "admin-message",
    "change-password",
    "check-privileges",
    "connect-to-peer",
    "invalid-password",
    "peer-address",
    "privileged-users",
    "server-disconnect",
    "server-login",
    "server-reconnect",
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
    "private-room-operator-added",
    "private-room-operator-removed",
    "private-room-owned",
    "private-room-remove-operator",
    "private-room-remove-user",
    "private-room-removed",
    "private-room-toggle",
    "private-room-users",
    "remove-room",
    "room-completions",
    "room-list",
    "say-chat-room",
    "show-room",
    "ticker-add",
    "ticker-remove",
    "ticker-state",
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
    "private-chat-completions",
    "private-chat-remove-user",
    "private-chat-show-user",

    # Search
    "add-search",
    "add-wish",
    "excluded-search-phrases",
    "file-search-request-distributed",
    "file-search-request-server",
    "file-search-response",
    "remove-search",
    "remove-wish",
    "set-wishlist-interval",
    "show-search",

    # Statistics
    "update-stat",

    # Shares
    "folder-contents-request",
    "shared-file-list-progress",
    "shared-file-list-request",
    "shared-file-list-response",
    "shares-preparing",
    "shares-ready",
    "shares-scanning",
    "shares-unavailable",
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
    "file-connection-closed",
    "file-download-progress",
    "file-transfer-init",
    "file-upload-progress",
    "folder-contents-response",
    "folder-download-finished",
    "peer-connection-closed",
    "peer-connection-error",
    "place-in-queue-request",
    "place-in-queue-response",
    "queue-upload",
    "transfer-request",
    "transfer-response",
    "update-download",
    "update-download-limits",
    "update-upload",
    "update-upload-limits",
    "upload-denied",
    "upload-failed",
    "upload-file-error",

    # User info
    "user-info-progress",
    "user-info-remove-user",
    "user-info-request",
    "user-info-response",
    "user-info-show-user",
    "user-interests",
}


class Events:

    SCHEDULER_MAX_IDLE = 1

    def __init__(self):

        self._callbacks = {}
        self._thread_events = deque()
        self._pending_scheduler_events = deque()
        self._scheduler_events = {}
        self._scheduler_event_id = 0
        self._is_active = False

    def enable(self):

        if self._is_active:
            return

        self._is_active = True

        for event_name, callback in (
            ("quit", self._quit),
            ("thread-callback", self._thread_callback)
        ):
            self.connect(event_name, callback)

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

        callbacks = self._callbacks.get(event_name, [])

        if event_name == "quit":
            # Event and log modules register callbacks first, but need to quit last
            callbacks.reverse()

        for function in callbacks:
            function(*args, **kwargs)

    def emit_main_thread(self, event_name, *args, **kwargs):
        self._thread_events.append((event_name, args, kwargs))

    def invoke_main_thread(self, callback, *args, **kwargs):
        self.emit_main_thread("thread-callback", callback, *args, **kwargs)

    def schedule(self, delay, callback, callback_args=None, repeat=False):

        self._scheduler_event_id += 1
        next_time = (time.monotonic() + delay)

        if callback_args is None:
            callback_args = ()

        self._pending_scheduler_events.append(
            (self._scheduler_event_id, (next_time, delay, repeat, callback, callback_args)))

        return self._scheduler_event_id

    def cancel_scheduled(self, event_id):
        self._pending_scheduler_events.append((event_id, None))

    def process_thread_events(self):
        """Called by the main loop 10 times per second to emit thread events in
        the main thread.

        Return value indicates if the main loop should continue
        processing events.
        """

        if not self._thread_events:
            if not self._is_active:
                return False

            return True

        event_list = []

        while self._thread_events:
            event_list.append(self._thread_events.popleft())

        for event_name, args, kwargs in event_list:
            self.emit(event_name, *args, **kwargs)

        return True

    def _run_scheduler(self):

        while self._is_active:
            # Scheduled events additions/removals from other threads
            while self._pending_scheduler_events:
                event_id, event = self._pending_scheduler_events.popleft()

                if event is not None:
                    self._scheduler_events[event_id] = event
                else:
                    self._scheduler_events.pop(event_id, None)

            # No scheduled events
            if not self._scheduler_events:
                time.sleep(self.SCHEDULER_MAX_IDLE)
                continue

            # Retrieve upcoming event
            event_id, event_data = min(self._scheduler_events.items(), key=lambda x: x[1][0])  # Compare timestamps
            event_time, delay, repeat, callback, callback_args = event_data
            current_time = time.monotonic()
            sleep_time = (event_time - current_time)

            if sleep_time <= 0:
                self.invoke_main_thread(callback, *callback_args)

                if repeat:
                    self._scheduler_events[event_id] = ((event_time + delay), delay, repeat, callback, callback_args)
                else:
                    self._scheduler_events.pop(event_id, None)

                continue

            time.sleep(min(sleep_time, self.SCHEDULER_MAX_IDLE))

    def _thread_callback(self, callback, *args, **kwargs):
        callback(*args, **kwargs)

    def _quit(self):

        # Ensure any remaining events are processed
        self.process_thread_events()

        self._is_active = False
        self._callbacks.clear()
        self._pending_scheduler_events.clear()
        self._scheduler_events.clear()


events = Events()
