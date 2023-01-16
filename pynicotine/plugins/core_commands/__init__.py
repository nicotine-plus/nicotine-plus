# COPYRIGHT (C) 2023 Nicotine+ Contributors
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

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        self.commands = {
            "close": {
                "description": "Close private chat",
                "aliases": ["c"],
                "disable": ["cli"],
                "group": "Private Chat",
                "callback": self.close_command,
                "usage_chatroom": ["<user>"],
                "usage_private_chat": ["[user]"]
            },
            "sample": {
                "description": "Sample command description",
                "aliases": ["demo"],
                "disable": ["private_chat"],
                "callback": self.sample_command,
                "callback_private_chat": self.sample_command,
                "usage": ["<choice1|choice2>", "<something..>"],
                "usage_chatroom": ["<choice55|choice2>"]
            },
            "rescan": {
                "callback": self.rescan_command,
                "description": _("Rescan shares"),
                "group": _("Configure Shares"),
                "usage": ["[-force]"]
            },
            "shares": {
                "aliases": ["ls"],
                "callback": self.list_shares_command,
                "description": _("List shares"),
                "group": _("Configure Shares"),
                "usage": ["[public]", "[buddy]"]
            }
        }

    def close_command(self, args, user=None, **_unused):

        if args:
            user = args

        if user not in self.core.privatechat.users:
            self.output(f"Not messaging with user {user}")
            return False

        self.output(f"Closing private chat of user {user}")
        self.core.privatechat.remove_user(user)
        return True

    def sample_command(self, _args, **_unused):
        self.output("Hello")
        return True

    """ Configure Shares """

    def rescan_command(self, args, **_unused):

        force = (args.lstrip("- ") in ("force", "f"))

        if args and not force:
            self.output("Invalid option")
            return False

        self.core.shares.rescan_shares(force=force)
        return True

    def list_shares_command(self, args, **_unused):

        share_groups = self.core.shares.get_shared_folders()
        num_total = num_listed = 0

        for share_index, share_group in enumerate(share_groups):
            group_name = "buddy" if share_index == 1 else "public"
            num_shares = len(share_group)
            num_total += num_shares

            if not num_shares or args and group_name not in args.lower():
                continue

            self.output("\n" + f"{num_shares} {group_name} shares:")

            for virtual_name, folder_path, *_unused in share_group:
                self.output(f'• "{virtual_name}" {folder_path}')

            num_listed += num_shares

        self.output("\n" + f"{num_listed} shares listed ({num_total} configured)")
