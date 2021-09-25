# COPYRIGHT (C) 2020-2021 Nicotine+ Team
# COPYRIGHT (C) 2008-2011 Quinox <quinox@users.sf.net>
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

from pynicotine.pluginsystem import BasePlugin, ResponseThrottle, returncode
from pynicotine.slskmessages import GetPeerAddress


class Plugin(BasePlugin):

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        self.settings = {
            'keyword_enabled': False,
            'socket_timeout': 10
        }
        self.metasettings = {
            'keyword_enabled': {
                'description': 'Enable "portscan" keyword trigger',
                'type': 'bool'
            },
            'socket_timeout': {
                'description': 'Socket timeout (in seconds)',
                'type': 'int'
            }
        }
        self.__publiccommands__ = self.__privatecommands__ = [('port', self.port_checker_command)]

        self.throttle = ResponseThrottle(self.core, self.human_name)
        self.checkroom = "nicotine"
        self.pending_user = ""

    def incoming_public_chat_notification(self, room, user, line):

        my_username = self.config.sections["server"]["login"]

        if room != self.checkroom or not self.settings['keyword_enabled'] or my_username == user:
            return

        if not self.throttle.ok_to_respond(room, user, line, 10):
            return

        if 'portscan' in line.lower():
            self.log("%s requested a port scan", user)
            self.resolve(user, True)

    def user_resolve_notification(self, user, ip_address, port, _country):

        if not self.pending_user or user not in self.pending_user:
            return

        user, announce = self.pending_user
        self.pending_user = ()
        threading.Thread(target=self.check_port, args=(user, ip_address, port, announce)).start()

    def resolve(self, user, announce):

        if user in self.core.users and isinstance(self.core.users[user].addr, tuple):
            ip_address, port = self.core.users[user].addr
            threading.Thread(target=self.check_port, args=(user, ip_address, port, announce)).start()
        else:
            self.pending_user = user, announce
            self.core.queue.append(GetPeerAddress(user))

    def check_port(self, user, ip_address, port, announce):

        status = self._check_port(ip_address, port)

        if announce and status in ('open', 'closed'):
            self.throttle.responded()
            self.send_public(self.checkroom, '%s: Your port is %s' % (user, status))

        self.log("User %s on %s:%s port is %s.", (user, ip_address, port, status))

    def _check_port(self, ip_address, port):

        if ip_address in ('0.0.0.0',) or port in (0,):
            return 'unknown'

        timeout = self.settings['socket_timeout']
        self.log('Scanning %s:%d (socket timeout %d seconds)...', (ip_address, port, timeout))

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)

        result = sock.connect_ex((ip_address, port))
        sock.close()

        if result == 0:
            return 'open'

        return 'closed'

    def port_checker_command(self, _public_command, _, user):

        if user:
            self.resolve(user, False)
        else:
            self.log("Provide a user name as parameter.")

        return returncode['zap']
