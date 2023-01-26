# COPYRIGHT (C) 2020-2022 Nicotine+ Contributors
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

import json

from itertools import islice

from pynicotine.pluginsystem import BasePlugin
from pynicotine.pluginsystem import returncode


class Plugin(BasePlugin):

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        self.settings = {
            "reddit_links": 3
        }
        self.metasettings = {
            "reddit_links": {
                "description": "Maximum number of links to provide",
                "type": "integer"
            }
        }
        self.__publiccommands__ = self.__privatecommands__ = [("reddit", self.reddit_command)]

    def reddit_command(self, _source, subreddit):

        try:
            from urllib.request import urlopen
            with urlopen("https://www.reddit.com/r/%s/.json" % subreddit, timeout=10) as response:
                response_body = response.read().decode("utf-8")

        except Exception as error:
            self.log("Could not connect to Reddit: %(error)s", {"error": error})
            return returncode["zap"]

        try:
            response = json.loads(response_body)

            for post in islice(response["data"]["children"], self.settings["reddit_links"]):
                post_data = post["data"]
                self.echo_message("%s: %s" % (post_data["title"], post_data["url"]))

        except Exception as error:
            self.log("Failed to parse response from Reddit: %(error)s", {"error": error})

        return returncode["zap"]
