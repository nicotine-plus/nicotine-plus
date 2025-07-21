# SPDX-FileCopyrightText: 2020-2025 Nicotine+ Contributors
# SPDX-FileCopyrightText: 2009 quinox <quinox@users.sf.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from inspect import currentframe

from pynicotine.pluginsystem import BasePlugin


class Plugin(BasePlugin):

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        self.settings = {}
        self.metasettings = {}

        # These are too noisy, don't enable them by default
        verbose_events = {"public_room_message_notification", "distrib_search_notification"}

        for function_name in Plugin.__dict__:
            if function_name.startswith("_"):
                continue

            self.settings[function_name] = (function_name not in verbose_events)
            self.metasettings[function_name] = {
                "description": f"{function_name}()",
                "type": "bool"
            }

        self.log("__init__()")

    def _trigger_log(self, parameter_arguments=""):

        function_name = currentframe().f_back.f_code.co_name

        if not self.settings[function_name]:
            return

        self.log(f"{function_name}({parameter_arguments})")

    def init(self):
        self._trigger_log()

    def disable(self):
        self._trigger_log()

    def loaded_notification(self):
        self._trigger_log()

    def unloaded_notification(self):
        self._trigger_log()

    def shutdown_notification(self):
        self._trigger_log()

    def public_room_message_notification(self, room, user, line):
        self._trigger_log(f"room={room}, user={user}, line={line}")

    def search_request_notification(self, searchterm, user, token):
        self._trigger_log(f"searchterm={searchterm}, user={user}, token={token}")

    def distrib_search_notification(self, searchterm, user, token):
        self._trigger_log(f"searchterm={searchterm}, user={user}, token={token}")

    def incoming_private_chat_event(self, user, line):
        self._trigger_log(f"user={user}, line={line}")

    def incoming_private_chat_notification(self, user, line):
        self._trigger_log(f"user={user}, line={line}")

    def incoming_public_chat_event(self, room, user, line):
        self._trigger_log(f"room={room}, user={user}, line={line}")

    def incoming_public_chat_notification(self, room, user, line):
        self._trigger_log(f"room={room}, user={user}, line={line}")

    def outgoing_private_chat_event(self, user, line):
        self._trigger_log(f"user={user}, line={line}")

    def outgoing_private_chat_notification(self, user, line):
        self._trigger_log(f"user={user}, line={line}")

    def outgoing_public_chat_event(self, room, line):
        self._trigger_log(f"room={room}, line={line}")

    def outgoing_public_chat_notification(self, room, line):
        self._trigger_log(f"user={room}, line={line}")

    def outgoing_global_search_event(self, text):
        self._trigger_log(f"text={text}")

    def outgoing_room_search_event(self, rooms, text):
        self._trigger_log(f"rooms={rooms}, text={text}")

    def outgoing_buddy_search_event(self, text):
        self._trigger_log(f"text={text}")

    def outgoing_user_search_event(self, users, text):
        self._trigger_log(f"users={users}, text={text}")

    def user_resolve_notification(self, user, ip_address, port, country):
        self._trigger_log(f"user={user}, ip_address={ip_address}, port={port}, country={country}")

    def server_connect_notification(self):
        self._trigger_log()

    def server_disconnect_notification(self, userchoice):
        self._trigger_log(f"userchoice={userchoice}")

    def join_chatroom_notification(self, room):
        self._trigger_log(f"room={room}")

    def leave_chatroom_notification(self, room):
        self._trigger_log(f"room={room}")

    def user_join_chatroom_notification(self, room, user):
        self._trigger_log(f"room={room}, user={user}")

    def user_leave_chatroom_notification(self, room, user):
        self._trigger_log(f"room={room}, user={user}")

    def user_stats_notification(self, user, stats):
        self._trigger_log(f"user={user}, stats={stats}")

    def user_status_notification(self, user, status, privileged):
        self._trigger_log(f"user={user}, status={status}, privileged={privileged}")

    def upload_queued_notification(self, user, virtual_path, real_path):
        self._trigger_log(f"user={user}, virtual_path={virtual_path}, real_path={real_path}")

    def upload_started_notification(self, user, virtual_path, real_path):
        self._trigger_log(f"user={user}, virtual_path={virtual_path}, real_path={real_path}")

    def upload_finished_notification(self, user, virtual_path, real_path):
        self._trigger_log(f"user={user}, virtual_path={virtual_path}, real_path={real_path}")

    def download_started_notification(self, user, virtual_path, real_path):
        self._trigger_log(f"user={user}, virtual_path={virtual_path}, real_path={real_path}")

    def download_finished_notification(self, user, virtual_path, real_path):
        self._trigger_log(f"user={user}, virtual_path={virtual_path}, real_path={real_path}")
