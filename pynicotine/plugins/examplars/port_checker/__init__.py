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

from pynicotine import slskmessages
from pynicotine.pluginsystem import BasePlugin
from pynicotine.pluginsystem import returncode


class Plugin(BasePlugin):

    __name__ = "Port Checker"

    def init(self):
        # keys are users, value of 1 means pending requested scan, 2 means pending unrequested scan
        # and 3 means the user was scanned
        self.checked = {}
        self.checkroom = 'nicotine'

    def incoming_public_chat_notification(self, room, user, line):

        if room != self.checkroom:
            return
        words = line.lower().split()
        if 'portscan' in words:
            self.log("%s requested a port scan" % (user,))
            self.checked[user] = 1
            self.resolve(user)
        elif (('cant' in words or "can't" in words or 'can someone' in words or 'can anyone' in words)
              and ('browse' in words or 'download' in words or 'connect' in words)):
            if user not in self.checked:
                self.log("%s seems to have trouble, performing a port scan" % (user,))
                self.checked[user] = 2
                self.resolve(user)
            else:
                self.log("%s seems to have trouble, but we already performed a port scan" % (user,))

    def user_resolve_notification(self, user, ip_address, port, country):

        if user in self.checked:
            status = self.checkport(ip_address, port)
            if status in ('open',):
                if self.checked[user] in (1,):
                    self.send_public(
                        self.checkroom,
                        '%s: Your port is accessible, you can blame others in case of problems ;)' % user)
                else:
                    self.log("%s: Port is accessible, not reporting since this was an unrequested scan." % (user,))
            elif status in ('closed',):
                self.send_public(
                    self.checkroom,
                    ('%s: Alas, your firewall and/or router is not configured properly. I could not '
                     'contact you at port %s') % (user, port))
            else:
                if self.checked[user] in (1,):
                    self.send_public(
                        self.checkroom,
                        '%s: the server doesn\'t want to tell me your IP address, I cannot scan you.' % (user,))
                else:
                    self.log("%s: Unknown port status on %s:%s" % (user, ip_address, port))
            self.checked[user] = 3

    def my_public_command(self, room, args):

        if args:
            self.checked[args] = 1
            self.resolve(args)
            return returncode['zap']
        else:
            self.log("Provide a user name as parameter.")

    def resolve(self, user):
        self.core.queue.append(slskmessages.GetPeerAddress(user))

    def checkport(self, ip_address, port):

        if ip_address in ('0.0.0.0',) or port in (0,):
            return 'unknown'
        self.log("Testing port at %s:%s" % (ip_address, port))
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(60)
        try:
            s.connect((ip_address, port))
            self.log("%s:%s: Port is open." % (ip_address, port))
            return 'open'
        except socket.error:
            self.log("%s:%s: Port is closed." % (ip_address, port))
            return 'closed'
        s.close()

    __publiccommands__ = [('port', my_public_command)]
