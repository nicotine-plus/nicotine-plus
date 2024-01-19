# COPYRIGHT (C) 2020-2024 Nicotine+ Contributors
# COPYRIGHT (C) 2008-2011 quinox <quinox@users.sf.net>
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

import socket
import threading

from pynicotine.pluginsystem import BasePlugin, ResponseThrottle


class Plugin(BasePlugin):

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        self.settings = {
            "keyword_enabled": False,
            "socket_timeout": 10
        }
        self.metasettings = {
            "keyword_enabled": {
                "description": 'Enable "portscan" keyword trigger',
                "type": "bool"
            },
            "socket_timeout": {
                "description": "Socket timeout (in seconds)",
                "type": "int"
            }
        }
        self.commands = {
            "port": {
                "callback": self.port_checker_command,
                "description": "Check firewall state of user",
                "parameters": ["<user>"],
                "parameters_private_chat": ["[user]"]
            }
        }
        self.throttle = ResponseThrottle(self.core, self.human_name)
        self.checkroom = "nicotine"

    def incoming_public_chat_notification(self, room, user, line):

        if room != self.checkroom or not self.settings["keyword_enabled"] or self.core.users.login_username == user:
            return

        if not self.throttle.ok_to_respond(room, user, line, 10):
            return

        if "portscan" in line.lower():
            self.log("%s requested a port scan", user)
            self.resolve(user, True)

    def resolve(self, user, announce):

        user_address = self.core.users.addresses.get(user)

        if user_address is not None:
            ip_address, port = user_address
            threading.Thread(target=self.check_port, args=(user, ip_address, port, announce)).start()

    def check_port(self, user, ip_address, port, announce):

        status = self._check_port(ip_address, port)

        if announce and status in {"open", "closed"}:
            self.throttle.responded()
            self.send_public(self.checkroom, f"{user}: Your port is {status}")

        self.log("User %s on %s:%s port is %s.", (user, ip_address, port, status))

    def _check_port(self, ip_address, port):

        if ip_address == "0.0.0.0" or not port:
            return "unknown"

        timeout = self.settings["socket_timeout"]
        self.log("Scanning %s:%d (socket timeout %d seconds)...", (ip_address, port, timeout))

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)

        result = sock.connect_ex((ip_address, port))
        sock.close()

        if not result:
            return "open"

        return "closed"

    def port_checker_command(self, args, user=None, **_room):

        if args:
            user = args

        self.resolve(user, False)
