from pynicotine import slskmessages
from pynicotine.pluginsystem import BasePlugin


def enable(plugins):
    global PLUGIN
    PLUGIN = Plugin(plugins)


def disable(plugins):
    global PLUGIN
    PLUGIN = None


class Plugin(BasePlugin):
    __name__ = "Leech detector"
    __version__ = "2011-10-29r00"
    __author__ = "quinox"
    __desc__ = '''Detects when leechers are downloading'''

    def init(self):
        self.probed = {}

    def UploadQueuedNotification(self, user, virualfile, realfile):
        try:
            self.probed[user]
        except KeyError:
            self.probed[user] = 'requesting'
            self.parent.frame.np.queue.put(slskmessages.GetUserStats(user))
            self.log('New user %s, requesting information...' % user)

    def UserStatsNotification(self, user, stats):
        try:
            status = self.probed[user]
        except KeyError:
            # we did not trigger this notification
            return
        if status == 'requesting':
            if stats['files'] == 0:
                self.sendprivate(user, 'You are not sharing any files, that makes me a sad panda :(')
                self.log("User %s doesn't share any files, sent complaint." % user)
            else:
                self.log('User %s is okay, sharing %s files' % (user, stats['files']))
            self.probed[user] = 'processed'
        else:
            # We already dealt with this user.
            pass
