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

        self.main_group_name = _("%s Commands") % self.config.application_name
        self.commands = {
            "help": {
                "aliases": ["?"],
                "callback": self.help_command,
                "description": _("List available commands"),
                "group": self.main_group_name,
                "usage": ["[query]"]
            },
            "quit": {
                "aliases": ["q", "exit"],
                "callback": self.quit_command,
                "description": _("Quit Nicotine+"),
                "group": self.main_group_name,
                "usage": ["[-force]"]
            },
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
                "group": self.main_group_name,
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

    """ Application Commands """

    def help_command(self, args, user=None, room=None):

        if user is not None:
            interface = "private_chat"

        elif room is not None:
            interface = "chatroom"

        else:
            interface = "cli"

        search_query = " ".join(args.lower().split(" ", maxsplit=1))
        command_groups = self.parent.get_command_descriptions(  # pylint: disable=no-member
            interface, search_query=search_query
        )
        num_commands = sum(len(command_groups[x]) for x in command_groups)
        output_text = ""

        if not search_query:
            output_text += _("Listing %(num)i available commands:") % {"num": num_commands}
        else:
            output_text += _('Listing %(num)i available commands matching "%(query)s":') % {
                "num": num_commands,
                "query": search_query
            }

        for group_name, commands in command_groups.items():
            output_text += f"\n\n{group_name}:"

            for command_usage, description in commands:
                output_text += f"\n	{command_usage}  -  {description}"

        if not search_query:
            output_text += "\n\n" + _("Type %(command)s to list similar commands") % {"command": "/help [query]"}

        self.output(output_text)
        return True

    def quit_command(self, args, **_unused):

        force = (args.lstrip("- ") in ("force", "f"))

        if args and not force:
            self.output("Invalid option")
            return False

        if force:
            self.core.quit()
        else:
            self.core.confirm_quit()

        return True

    """ Private Chats """

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
