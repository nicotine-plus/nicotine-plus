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
            "help": {
                "aliases": ["?"],
                "callback": self.help_command,
                "description": _("List available commands"),
                "usage": ["[query]"]
            },
            "quit": {
                "aliases": ["q", "exit"],
                "callback": self.quit_command,
                "description": _("Quit Nicotine+"),
                "usage": ["[-force]"]
            },
            "clear": {
                "aliases": ["cl"],
                "callback": self.clear_command,
                "description": _("Clear chat window"),
                "disable": ["cli"],
                "group": _("Chat"),
            },
            "me": {
                "callback": self.me_command,
                "description": _("Say something in the third-person"),
                "disable": ["cli"],
                "group": _("Chat"),
                "usage": ["<something..>"]
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
            "join": {
                "aliases": ["j"],
                "callback": self.join_command,
                "description": _("Join chat room"),
                "disable": ["cli"],
                "group": _("Chat Rooms"),
                "usage": ["<room>"]
            },
            "leave": {
                "aliases": ["l"],
                "callback": self.leave_command,
                "description": _("Leave chat room"),
                "disable": ["cli"],
                "group": _("Chat Rooms"),
                "usage": ["<room>"],
                "usage_chatroom": ["[room]"]
            },
            "say": {
                "callback": self.say_command,
                "description": _("Say message in specified chat room"),
                "disable": ["cli"],
                "group": _("Chat Rooms"),
                "usage": ["<room>", "<message..>"]
            },
            "pm": {
                "callback": self.pm_command,
                "description": _("Open private chat"),
                "disable": ["cli"],
                "group": _("Private Chat"),
                "usage": ["<user>"]
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
            "msg": {
                "aliases": ["m"],
                "callback": self.msg_command,
                "description": _("Send private message to user"),
                "disable": ["cli"],
                "group": _("Private Chat"),
                "usage": ["<user>", "<message..>"]
            },
            "add": {
                "aliases": ["buddy"],
                "callback": self.add_buddy_command,
                "description": _("Add user to buddy list"),
                "group": _("Users"),
                "usage": ["<user>"],
                "usage_private_chat": ["[user]"]
            },
            "rem": {
                "aliases": ["unbuddy"],
                "callback": self.remove_buddy_command,
                "description": _("Remove buddy from buddy list"),
                "group": _("Users"),
                "usage": ["<buddy>"],
                "usage_private_chat": ["[buddy]"]
            },
            "browse": {
                "aliases": ["b"],
                "callback": self.browse_user_command,
                "description": _("Browse files of user"),
                "disable": ["cli"],
                "group": _("Users"),
                "usage": ["<user>"],
                "usage_private_chat": ["[user]"]
            },
            "whois": {
                "aliases": ["info", "w"],
                "callback": self.whois_command,
                "description": _("Show user profile information"),
                "disable": ["cli"],
                "group": _("Users"),
                "usage": ["<user>"],
                "usage_private_chat": ["[user]"]
            },
            "ip": {
                "callback": self.ip_address_command,
                "description": _("Show IP address or username"),
                "group": _("Network Filters"),
                "usage": ["<user or ip>"],
                "usage_private_chat": ["[user]", "[ip]"]
            },
            "ban": {
                "callback": self.ban_command,
                "description": _("Block connections from user or IP address"),
                "group": _("Network Filters"),
                "usage": ["<user or ip>"],
                "usage_private_chat": ["[user]", "[ip]"]
            },
            "unban": {
                "callback": self.unban_command,
                "description": _("Remove user or IP address from ban lists"),
                "group": _("Network Filters"),
                "usage": ["<user or ip>"],
                "usage_private_chat": ["[user]", "[ip]"]
            },
            "ignore": {
                "callback": self.ignore_command,
                "description": _("Silence messages from user or IP address"),
                "disable": ["cli"],
                "group": _("Network Filters"),
                "usage": ["<user or ip>"],
                "usage_private_chat": ["[user]", "[ip]"]
            },
            "unignore": {
                "callback": self.unignore_command,
                "description": _("Remove user or IP address from ignore lists"),
                "disable": ["cli"],
                "group": _("Network Filters"),
                "usage": ["<user or ip>"],
                "usage_private_chat": ["[user]", "[ip]"]
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
            },
            "search": {
                "aliases": ["s"],
                "callback": self.search_command,
                "description": _("Start global file search"),
                "disable": ["cli"],
                "group": _("Search Files"),
                "usage": ["<query>"]
            },
            "rsearch": {
                "aliases": ["rs"],
                "callback": self.search_rooms_command,
                "description": _("Search files in joined rooms"),
                "disable": ["cli"],
                "group": _("Search Files"),
                "usage": ["<query>"]
            },
            "bsearch": {
                "aliases": ["bs"],
                "callback": self.search_buddies_command,
                "description": _("Search files of all buddies"),
                "disable": ["cli"],
                "group": _("Search Files"),
                "usage": ["<query>"]
            },
            "usearch": {
                "aliases": ["us"],
                "callback": self.search_user_command,
                "description": _("Search a user's shared files"),
                "disable": ["cli"],
                "group": _("Search Files"),
                "usage": ["<user>", "<query>"]
            }
        }

    """ Application Commands """

    def help_command(self, args, user=None, room=None):

        if user is not None:
            command_interface = "private_chat"

        elif room is not None:
            command_interface = "chatroom"

        else:
            command_interface = "cli"

        search_query = " ".join(args.lower().split(" ", maxsplit=1))
        command_groups = self.parent.get_command_descriptions(  # pylint: disable=no-member
            command_interface, search_query=search_query
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
                output_text += f"\n\t{command_usage}  -  {description}"

        if not search_query:
            output_text += "\n\n" + _("Type %(command)s to list similar commands") % {"command": "/help [query]"}
        elif not num_commands:
            output_text += "\n" + _("Type %(command)s to list available commands") % {"command": "/help"}

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

    def sample_command(self, _args, **_unused):
        self.output("Hello")

    """ Chat """

    def clear_command(self, args, user=None, room=None):

        if args:
            return False

        if room is not None:
            self.core.chatrooms.clear_room_messages(room)

        elif user is not None:
            self.core.privatechat.clear_private_messages(user)

        return True

    def me_command(self, args, **_unused):
        self.send_message("/me " + args)  # /me is sent as plain text

    """ Chat Rooms """

    def join_command(self, args, **_unused):
        self.core.chatrooms.show_room(args)

    def leave_command(self, args, room=None, **_unused):

        if args:
            room = args

        if room not in self.core.chatrooms.joined_rooms:
            self.output(_("Not joined in room %s") % room)
            return False

        self.core.chatrooms.remove_room(room)
        return True

    def say_command(self, args, **_unused):

        args_split = args.split(maxsplit=1)
        room, text = args_split[0], args_split[1]

        if room not in self.core.chatrooms.joined_rooms:
            self.output(_("Not joined in room %s") % room)
            return False

        self.send_public(room, text)
        return True

    """ Private Chat """

    def pm_command(self, args, **_unused):
        self.core.privatechat.show_user(args)

    def close_command(self, args, user=None, **_unused):

        if args:
            user = args

        if user not in self.core.privatechat.users:
            self.output(f"Not messaging with user {user}")
            return False

        self.output(f"Closing private chat of user {user}")
        self.core.privatechat.remove_user(user)
        return True

    def msg_command(self, args, **_unused):

        args_split = args.split(maxsplit=1)
        user, text = args_split[0], args_split[1]

        self.send_private(user, text, show_ui=True, switch_page=False)

    """ Users """

    def add_buddy_command(self, args, user=None, **_unused):

        if args:
            user = args

        self.core.userlist.add_buddy(user)

    def remove_buddy_command(self, args, user=None, **_unused):

        if args:
            user = args

        self.core.userlist.remove_buddy(user)

    def browse_user_command(self, args, user=None, **_unused):

        if args:
            user = args

        self.core.userbrowse.browse_user(user)

    def whois_command(self, args, user=None, **_unused):

        if args:
            user = args

        self.core.userinfo.show_user(user)

    """ Network Filters """

    def ip_address_command(self, args, user=None, **_unused):

        if self.core.network_filter.is_ip_address(args):
            self.output(self.core.network_filter.get_online_username(args))
            return

        if args:
            user = args

        online_ip_address = self.core.network_filter.get_online_user_ip_address(user)

        if not online_ip_address:
            self.core.request_ip_address(user)
            return

        self.output(online_ip_address)

    def ban_command(self, args, user=None, **_unused):

        if self.core.network_filter.is_ip_address(args):
            banned_ip_address = self.core.network_filter.ban_user_ip(ip_address=args)
        else:
            if args:
                user = args

            banned_ip_address = None
            self.core.network_filter.ban_user(user)

        self.output(_("Banned %s") % (banned_ip_address or user))

    def unban_command(self, args, user=None, **_unused):

        if self.core.network_filter.is_ip_address(args):
            unbanned_ip_addresses = self.core.network_filter.unban_user_ip(ip_address=args)
            self.core.network_filter.unban_user(self.core.network_filter.get_online_username(args))
        else:
            if args:
                user = args

            unbanned_ip_addresses = self.core.network_filter.unban_user_ip(user)
            self.core.network_filter.unban_user(user)

        self.output(_("Unbanned %s") % (" & ".join(unbanned_ip_addresses) or user))

    def ignore_command(self, args, user=None, **_unused):

        if self.core.network_filter.is_ip_address(args):
            ignored_ip_address = self.core.network_filter.ignore_user_ip(ip_address=args)
        else:
            if args:
                user = args

            ignored_ip_address = None
            self.core.network_filter.ignore_user(user)

        self.output(_("Ignored %s") % (ignored_ip_address or user))

    def unignore_command(self, args, user=None, **_unused):

        if self.core.network_filter.is_ip_address(args):
            unignored_ip_addresses = self.core.network_filter.unignore_user_ip(ip_address=args)
            self.core.network_filter.unignore_user(self.core.network_filter.get_online_username(args))
        else:
            if args:
                user = args

            unignored_ip_addresses = self.core.network_filter.unignore_user_ip(user)
            self.core.network_filter.unignore_user(user)

        self.output(_("Unignored %s") % (" & ".join(unignored_ip_addresses) or user))

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

            for virtual_name, folder_path, *_ignored in share_group:
                self.output(f'• "{virtual_name}" {folder_path}')

            num_listed += num_shares

        self.output("\n" + f"{num_listed} shares listed ({num_total} configured)")

    """ Search Files """

    def search_command(self, args, **_unused):
        self.core.search.do_search(args, "global")

    def search_rooms_command(self, args, **_unused):
        self.core.search.do_search(args, "rooms")

    def search_buddies_command(self, args, **_unused):
        self.core.search.do_search(args, "buddies")

    def search_user_command(self, args, **_unused):

        args_split = args.split(maxsplit=1)
        user, query = args_split[0], args_split[1]

        self.core.search.do_search(query, "user", user=user)
