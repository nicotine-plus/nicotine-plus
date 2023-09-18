# COPYRIGHT (C) 2020-2023 Nicotine+ Contributors
# COPYRIGHT (C) 2011 quinox <quinox@users.sf.net>
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

from pynicotine.pluginsystem import BasePlugin


class Plugin(BasePlugin):

    PLACEHOLDERS = {
        "%files%": "num_files",
        "%folders%": "num_folders"
    }

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        self.settings = {
            "message": "Please consider sharing more files if you would like to download from me again. Thanks :)",
            "num_files": 1,
            "num_folders": 1,
            "open_private_chat": True,
            "detected_leechers": []
        }
        self.metasettings = {
            "message": {
                "description": ("Private chat message to send to leechers. Each line is sent as a separate message, "
                                "too many message lines may get you temporarily banned for spam!"),
                "type": "textview"
            },
            "num_files": {
                "description": "Require users to have a minimum number of shared files:",
                "type": "int", "minimum": 0
            },
            "num_folders": {
                "description": "Require users to have a minimum number of shared folders:",
                "type": "int", "minimum": 1
            },
            "open_private_chat": {
                "description": "Open chat tabs when sending private messages to leechers",
                "type": "bool"
            },
            "detected_leechers": {
                "description": "Detected leechers",
                "type": "list string"
            }
        }

        self.probed_users = {}
        self.detected_leechers = set()

    def loaded_notification(self):

        min_num_files = self.metasettings["num_files"]["minimum"]
        min_num_folders = self.metasettings["num_folders"]["minimum"]

        if self.settings["num_files"] < min_num_files:
            self.settings["num_files"] = min_num_files

        if self.settings["num_folders"] < min_num_folders:
            self.settings["num_folders"] = min_num_folders

        # Separate leechers set for faster membership checks
        self.detected_leechers = set(self.settings["detected_leechers"])

        self.log(
            "Require users have a minimum of %d files in %d shared public folders.",
            (self.settings["num_files"], self.settings["num_folders"])
        )

    def upload_queued_notification(self, user, virtual_path, real_path):

        if user in self.probed_users:
            # We already have stats for this user.
            return

        self.probed_users[user] = "requesting"
        self.core.request_user_stats(user)

        self.log("Getting statistics from the server for new user %s…", user)

    def user_stats_notification(self, user, stats):

        if user not in self.probed_users:
            # We did not trigger this notification
            return

        if self.probed_users[user] != "requesting":
            # We already dealt with this user.
            return

        num_files = stats["files"]
        num_folders = stats["dirs"]
        is_previous_leecher = (user in self.detected_leechers)

        if num_files >= self.settings["num_files"] and num_folders >= self.settings["num_folders"]:
            if is_previous_leecher:
                self.detected_leechers.remove(user)
                self.settings["detected_leechers"].remove(user)

            self.probed_users[user] = "okay"
            self.log("User %s is okay, sharing %s files in %s folders.", (user, num_files, num_folders))
            return

        if is_previous_leecher:
            # Still leeching, but we already messaged the user previously
            self.probed_users[user] = "processed"
            return

        if user in self.core.userlist.buddies:
            self.probed_users[user] = "buddy"
            self.log("Buddy %s is only sharing %s files in %s folders. Not complaining.",
                     (user, num_files, num_folders))
            return

        if num_files <= 0 and num_folders >= self.settings["num_folders"]:
            # SoulseekQt seems to only send the number of folders to the server in at least some cases
            self.log(
                "User %s seems to have zero files but does have %s shared folders, the remote client could be wrong.",
                (user, num_folders)
            )
            # TODO: Implement alternative fallback method (num_files | num_folders) from a Browse Shares request

        if num_files <= 0 and num_folders <= 0:
            # SoulseekQt only sends the number of shared files/folders to the server once on startup (see Issue #1565)
            self.log("User %s seems to have zero files and no public shared folder, the server could be wrong.", user)

        if self.settings["message"]:
            log_message = ("Leecher detected, %s is only sharing %s files in %s folders. Going to message "
                           "leecher after transfer…")
        else:
            log_message = ("Leecher detected, %s is only sharing %s files in %s folders. Going to log "
                           "leecher after transfer…")

        self.probed_users[user] = "leecher"
        self.log(log_message, (user, num_files, num_folders))

    def upload_finished_notification(self, user, *_):

        if user not in self.probed_users:
            return

        if self.probed_users[user] != "leecher":
            return

        self.probed_users[user] = "processed"

        if not self.settings["message"]:
            self.log("Leecher %s doesn't share enough files. No message is specified in plugin settings.", user)
            return

        for line in self.settings["message"].splitlines():
            for placeholder, option_key in self.PLACEHOLDERS.items():
                # Replace message placeholders with actual values specified in the plugin settings
                line = line.replace(placeholder, str(self.settings[option_key]))

            self.send_private(user, line, show_ui=self.settings["open_private_chat"], switch_page=False)

        self.detected_leechers.add(user)
        self.settings["detected_leechers"].append(user)

        self.log("Leecher %s doesn't share enough files. Message sent.", user)
