# -*- coding: utf-8 -*-
"""
Requires feedparser

Example uses:
!reddit soulseek
!reddit news/new
!reddit news/top

"""
import feedparser
from pynicotine.pluginsystem import BasePlugin, ResponseThrottle


def enable(plugins):
    global PLUGIN
    PLUGIN = Plugin(plugins)


def disable(plugins):
    global PLUGIN
    PLUGIN = None


class Plugin(BasePlugin):
    __name__ = "reddit"
    __version__ = "2015-08-02r05"
    __author__ = "Mutnick"
    __desc__ = """Displays topics and links for a requested subreddit."""
    settings = {'reddit_links': 3}
    metasettings = {'reddit_links': {"description": 'Maximum number of links to provide', 'type': 'integer'}}

    def init(self):
        self.plugin_command = "!reddit"
        self.responder = ResponseThrottle(self.frame, self.__name__)

    def IncomingPublicChatEvent(self, room, nick, line):
        line = line.lower().strip()
        if line.startswith(self.plugin_command) and (" " in line):
            subreddit = line.split(" ")[1].strip("/")
            if self.responder.ok_to_respond(room, nick, subreddit):
                    posts = feedparser.parse('https://www.reddit.com/r/' + subreddit + '/.rss')
                    if posts.entries:
                        self.responder.responded()
                        for post in posts.entries[0:self.settings['reddit_links']]:
                            self.saypublic(room, u"/me {}: {}".format(post.title, post.link))
