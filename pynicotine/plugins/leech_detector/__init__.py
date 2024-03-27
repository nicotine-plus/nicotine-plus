# COPYRIGHT (C) 2020-2024 Nicotine+ Contributors
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
        "%folders%": "num_folders",
        "%shared_percentage%": "share_percentage_config"
    }

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        self.settings = {
            "autoban": True,
            "message": "Please consider sharing more files if you would like to download from me again. Thanks :)",
            "open_private_chat": True,
            "num_files": 1,
            "num_folders": 1,
            "share_percentage_config": 75,
            "detected_leechers": []
        }
        self.metasettings = {
            "autoban": {
                "description": "Auto bans detected leechers",
                "type": "bool"
            },
            "message": {
                "description": ("Private chat message to send to leechers. Each line is sent as a separate message, "
                                "too many message lines may get you temporarily banned for spam!"),
                "type": "textview"
            },
            "open_private_chat": {
                "description": "Open chat tabs when sending private messages to leechers",
                "type": "bool"
            },
            "num_files": {
                "description": "Require users to have a minimum number of shared files:",
                "type": "int", "minimum": 0
            },
            "num_folders": {
                "description": "Require users to have a minimum number of shared folders:",
                "type": "int", "minimum": 1
            },
            "share_percentage_config": {
                "description": "Require this percentage of share vs private to avoid leech detection",
                "type": "int", "minimum": 1, "maximum": 100
            },
            "detected_leechers": {
                "description": "Detected leechers",
                "type": "list string"
            }
        }

        self.probed_users = {}

    def loaded_notification(self):

        min_num_files = self.metasettings["num_files"]["minimum"]
        min_num_folders = self.metasettings["num_folders"]["minimum"]


        if self.settings["num_files"] < min_num_files:
            self.settings["num_files"] = min_num_files

        if self.settings["num_folders"] < min_num_folders:
            self.settings["num_folders"] = min_num_folders

        self.log(
            "Require users have a minimum of %d files in %d shared public folders which totals more than %d percent shared.",
            (self.settings["num_files"], self.settings["num_folders"], self.settings["share_percentage_config"])
        )
    
    def check_user(self, user, num_files, num_folders, num_pfolders, share_percent):

        if user not in self.probed_users:
            # We are not watching this user
            return

        if self.probed_users[user] == "okay":
            # User was already accepted previously, nothing to do
            return
            
        # conditions to be met to avoid ban
        is_user_accepted = (
            num_files >= self.settings["num_files"] and 
            num_folders >= self.settings["num_folders"] and
            share_percent >= self.settings["share_percentage_config"]
        )
        
        if is_user_accepted or user in self.core.buddies.users:
            if user in self.settings["detected_leechers"]:
                self.settings["detected_leechers"].remove(user)

            self.probed_users[user] = "okay"

            if is_user_accepted:
                self.log("User %s is okay, sharing %s files in %s folders with %s private. Percent: %s", (user, num_files, num_folders, num_pfolders, share_percent))
            else:
                self.log("Buddy %s is sharing %s files in %s folders and %s private. Percent: %s",
                         (user, num_files, num_folders, num_folders, share_percent))
            return

        if not self.probed_users[user].startswith("requesting"):
            # We already dealt with the user this session
            return

        if user in self.settings["detected_leechers"]:
            # We already messaged the user in a previous session
            self.probed_users[user] = "processed_leecher"
            return

        if (num_files <= 0 or num_folders <= 0) and self.probed_users[user] != "requesting_shares":
            # SoulseekQt only sends the number of shared files/folders to the server once on startup.
            # Verify user's actual number of files/folders.
            self.log("User %s has no shared files according to the server, requesting shares to verify…", user)
            self.probed_users[user] = "requesting_shares"
            self.core.userbrowse.request_user_shares(user)
            return

        if self.settings["message"]:
            for line in self.settings["message"].splitlines():
                for placeholder, option_key in self.PLACEHOLDERS.items():
                    # Replace message placeholders with actual values specified in the plugin settings
                    line = line.replace(placeholder, str(self.settings[option_key]))

                self.send_private(user, line, show_ui=self.settings["open_private_chat"], switch_page=False)
                log_message = ("Leecher detected, %s is only sharing %s files in %s folders and %s private. %s Percent shared. Message sent.")
        else:
            log_message = ("Leecher detected, %s is only sharing %s files in %s folders and %s private. %s Percent shared. No messsage to send…")


        if self.settings["autoban"] != False: self.core.network_filter.ban_user(user)
            
        self.probed_users[user] = "processed_leecher"
        if user not in self.settings["detected_leechers"]:
            self.settings["detected_leechers"].append(user)
        self.log(log_message, (user, num_files, num_folders, num_pfolders, share_percent))

    def upload_queued_notification(self, user, virtual_path, real_path):

        if user in self.probed_users:
            return

        self.probed_users[user] = "requesting_stats"
        stats = self.core.users.watched.get(user)
        # browse Downloaders
        self.core.userbrowse.browse_user(user, switch_page=False)

        if stats is None:
            # Transfer manager will request the stats from the server shortly
            return

        if stats.files is not None and stats.folders is not None:
            total = num_folders=stats.folders + num_pfolders=stats.pfolders
            percentage = round((num_pfolders=stats.pfolders / total) * 100)
            self.check_user(user, num_files=stats.files, num_folders=stats.folders, num_pfolders=stats.pfolders, share_percent=percentage)

    def user_stats_notification(self, user, stats):
        total = num_folders=stats["dirs"] + num_pfolders=stats["pdirs"]
        percentage = round((num_pfolders=stats["pdirs"] / total) * 100)
        self.check_user(user, num_files=stats["files"], num_folders=stats["dirs"], num_pfolders=stats["pdirs"], percentage)

    def user_stats_notification_login(self, user, stats):
        return
