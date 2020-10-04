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
    settings = {
        'message': 'You are not sharing any files, that makes me a sad panda :(',
    }
    metasettings = {
        'message': {
            'description': 'Message to send to leechers\n(new lines are sent as separate\nmessages, too many lines may\nget you tempbanned for spam)',
            'type': 'textview'},
    }

    def init(self):
        self.probed = {}

    def UploadQueuedNotification(self, user, virualfile, realfile):  # noqa
        try:
            self.probed[user]
        except KeyError:
            self.probed[user] = 'requesting'
            self.parent.frame.np.queue.put(slskmessages.GetUserStats(user))
            self.log('New user %s, requesting information...' % user)

    def UserStatsNotification(self, user, stats):  # noqa
        try:
            status = self.probed[user]
        except KeyError:
            # we did not trigger this notification
            return
        if status == 'requesting':
            if stats['files'] == 0:
                for line in self.settings['message'].splitlines():
                    self.sendprivate(user, line)

                self.log("User %s doesn't share any files, sent complaint." % user)
            else:
                self.log('User %s is okay, sharing %s files' % (user, stats['files']))
            self.probed[user] = 'processed'
        else:
            # We already dealt with this user.
            pass
