# pylint: disable=attribute-defined-outside-init

# COPYRIGHT (C) 2020-2021 Nicotine+ Team
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
Example uses:
!reddit soulseek
!reddit news/new
!reddit news/top

"""

from itertools import islice

from pynicotine.pluginsystem import BasePlugin
from pynicotine.pluginsystem import ResponseThrottle


class Plugin(BasePlugin):

    __name__ = "Reddit"
    settings = {'reddit_links': 3}
    metasettings = {'reddit_links': {"description": 'Maximum number of links to provide', 'type': 'integer'}}

    def init(self):
        self.plugin_command = "!reddit"
        self.responder = ResponseThrottle(self.core, self.__name__)

    @staticmethod
    def get_feed(domain, path):
        import http.client
        import json

        conn = http.client.HTTPSConnection(domain)
        conn.request("GET", path, headers={"User-Agent": "Nicotine+"})
        response = json.loads(conn.getresponse().read().decode("utf-8"))
        conn.close()

        return response

    def incoming_public_chat_event(self, room, user, line):
        line = line.lower().strip()

        if line.startswith(self.plugin_command) and (" " in line):
            subreddit = line.split(" ")[1].strip("/")

            if self.responder.ok_to_respond(room, user, subreddit):
                response = self.get_feed('www.reddit.com', '/r/' + subreddit + '/.json')

                if response:
                    self.responder.responded()

                    for post in islice(response['data']['children'], self.settings['reddit_links']):
                        post_data = post['data']
                        self.saypublic(room, "/me {}: {}".format(post_data['title'], post_data['url']))
