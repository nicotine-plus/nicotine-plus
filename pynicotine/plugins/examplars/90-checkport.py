import socket

from pynicotine import slskmessages
from pynicotine.pluginsystem import BasePlugin
from pynicotine.pluginsystem import returncode


def enable(plugins):
    global PLUGIN
    PLUGIN = Plugin(plugins)


def disable(plugins):
    global PLUGIN
    PLUGIN = None


class Plugin(BasePlugin):
    __name__ = "Port Checker"
    __version__ = "2008-11-26r00"
    __author__ = "quinox"
    __desc__ = ("By examining chatroom messages this plugin tries to find people that have a potential "
                "firewall/router problem, and if found tests their port. If a closed port is encountered "
                "a message will be sent to him/her.")

    def init(self):
        # keys are users, value of 1 means pending requested scan, 2 means pending unrequested scan
        # and 3 means the user was scanned
        self.checked = {}
        self.checkroom = 'nicotine'

    def IncomingPublicChatNotification(self, room, user, line):  # noqa
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

    def UserResolveNotification(self, user, ip, port, country):  # noqa
        if user in self.checked:
            status = self.checkport(ip, port)
            if status in ('open',):
                if self.checked[user] in (1,):
                    self.saypublic(
                        self.checkroom,
                        '%s: Your port is accessible, you can blame others in case of problems ;)' % user)
                else:
                    self.log("%s: Port is accessible, not reporting since this was an unrequested scan." % (user,))
            elif status in ('closed',):
                self.saypublic(
                    self.checkroom,
                    ('%s: Alas, your firewall and/or router is not configured properly. I could not '
                     'contact you at port %s') % (user, port))
            else:
                if self.checked[user] in (1,):
                    self.saypublic(
                        self.checkroom,
                        '%s: the server doesn\'t want to tell me your IP address, I cannot scan you.' % (user,))
                else:
                    self.log("%s: Unknown port status on %s:%s" % (user, ip, port))
            self.checked[user] = 3

    def my_public_command(self, room, args):
        if args:
            self.checked[args] = 1
            self.resolve(args)
            return returncode['zap']
        else:
            self.log("Provide a user name as parameter.")

    def resolve(self, user):
        self.parent.frame.np.queue.append(slskmessages.GetPeerAddress(user))

    def checkport(self, ip, port):
        if ip in ('0.0.0.0',) or port in (0,):
            return 'unknown'
        self.log("Testing port at %s:%s" % (ip, port))
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(60)
        try:
            s.connect((ip, port))
            self.log("%s:%s: Port is open." % (ip, port))
            return 'open'
        except socket.error:
            self.log("%s:%s: Port is closed." % (ip, port))
            return 'closed'
        s.close()

    __publiccommands__ = [('port', my_public_command)]
