# COPYRIGHT (C) 2020-2022 Nicotine+ Team
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

import json

from itertools import islice

from pynicotine.pluginsystem import BasePlugin
from pynicotine.pluginsystem import ResponseThrottle
from pynicotine.utils import http_request


class Plugin(BasePlugin):

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        self.settings = {
            'reddit_links': 3
        }
        self.metasettings = {
            'reddit_links': {
                'description': 'Maximum number of links to provide',
                'type': 'integer'
            }
        }

        self.plugin_command = "!reddit"
        self.responder = ResponseThrottle(self.core, self.human_name)

    def incoming_public_chat_notification(self, room, user, line):
        line = line.lower().strip()

        if not line.startswith(self.plugin_command) or " " not in line:
            return

        subreddit = line.split(" ")[1].strip("/")

        if not self.responder.ok_to_respond(room, user, subreddit):
            return

        try:
            response = http_request('https', 'www.reddit.com', '/r/' + subreddit + '/.json',
                                    headers={"User-Agent": self.config.application_name})

        except Exception as error:
            self.log("Could not connect to Reddit: %(error)s", {"error": error})
            return

        try:
            response = json.loads(response)

            for post in islice(response['data']['children'], self.settings['reddit_links']):
                post_data = post['data']
                self.send_public(room, "/me {}: {}".format(post_data['title'], post_data['url']))

        except Exception as error:
            self.log("Failed to parse response from Reddit: %(error)s", {"error": error})
            return

        self.responder.responded()
