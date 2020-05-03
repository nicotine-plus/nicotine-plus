# COPYRIGHT (c) 2016 Mutnick <muhing@yahoo.com>
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
"""
Requires feedparser

Example uses:
!reddit soulseek
!reddit news/new
!reddit news/top

"""
import feedparser
from pynicotine.pluginsystem import BasePlugin
from pynicotine.pluginsystem import ResponseThrottle


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
                        self.saypublic(room, "/me {}: {}".format(post.title, post.link))
