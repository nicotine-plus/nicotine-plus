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

    __name__ = "Port Checker"

    settings = {
        'keyword_enabled': False,
        'socket_timeout': 10
    }
    metasettings = {
        'keyword_enabled': {
            'description': 'Enable "portscan" keyword trigger',
            'type': 'bool'
        },
        'socket_timeout': {
            'description': 'Socket timeout (in seconds)',
            'type': 'int'
        }
    }
    my_username = checkroom = throttle = pending_user = ''

    def init(self):

        self.throttle = ResponseThrottle(self.core, self.__name__)
        self.my_username = self.config.sections["server"]["login"]
        self.checkroom = 'nicotine'

    def incoming_public_chat_notification(self, room, user, line):

        if room != self.checkroom or not self.settings['keyword_enabled'] or self.my_username == user:
            return

        if not self.throttle.ok_to_respond(room, user, line, 10):
            return

        if 'portscan' in line.lower():  # noqa
            self.log("%s requested a port scan", user)
            self.resolve(user, True)

    def user_resolve_notification(self, user, ip, port, _):

        if not self.pending_user or user not in self.pending_user:
            return

        user, announce = self.pending_user
        self.pending_user = ()
        threading.Thread(target=self.check_port, args=(user, ip, port, announce)).start()

    def resolve(self, user, announce):

        if user in self.core.users and isinstance(self.core.users[user].addr, tuple):
            ip, port = self.core.users[user].addr
            threading.Thread(target=self.check_port, args=(user, ip, port, announce)).start()
        else:
            self.pending_user = user, announce
            self.core.queue.append(GetPeerAddress(user))

    def check_port(self, user, ip, port, announce):

        status = self._check_port(ip, port)

        if announce and status in ('open', 'closed'):
            self.throttle.responded()
            self.send_public(self.checkroom, '%s: Your port is %s' % (user, status))

        self.log("User %s on %s:%s port is %s.", (user, ip, port, status))

        return

    def _check_port(self, ip, port):

        if ip in ('0.0.0.0',) or port in (0,):
            return 'unknown'

        timeout = self.settings['socket_timeout']
        self.log('Scanning %s:%d (socket timeout %d seconds)...', (ip, port, timeout))

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)

        result = sock.connect_ex((ip, port))
        sock.close()

        if result == 0:
            return 'open'
        else:
            return 'closed'

    def port_checker_command(self, _, user):

        if user:
            self.resolve(user, False)
        else:
            self.log("Provide a user name as parameter.")

        return returncode['zap']

    __publiccommands__ = __privatecommands__ = [('port', port_checker_command)]  # noqa
