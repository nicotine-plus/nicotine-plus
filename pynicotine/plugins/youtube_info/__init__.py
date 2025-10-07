# SPDX-FileCopyrightText: 2021-2023 Nicotine+ Contributors
# SPDX-FileCopyrightText: 2021 Inso-m-niaC
# SPDX-License-Identifier: GPL-3.0-or-later

import json
import re

from pynicotine.pluginsystem import BasePlugin
from pynicotine.utils import human_length
from pynicotine.utils import humanize


class Plugin(BasePlugin):

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        self.settings = {
            "api_key": "",
            "color": "Local",
            "format": [
                "* Title: %title%",
                "* Duration: %duration% - Views: %views%"]
        }
        self.metasettings = {
            "api_key": {
                "description": "YouTube Data v3 API key:",
                "type": "string"
            },
            "color": {
                "description": "Message color:",
                "type": "dropdown",
                "options": ("Remote", "Local", "Action", "Hilite")
            },
            "format": {
                "description": "Message format",
                "type": "list string"
            }
        }

        self.last_video_id = {
            "private": {},
            "public": {}
        }

    def incoming_public_chat_notification(self, room, user, line):

        if (self.core.network_filter.is_user_ignored(user)
                or self.core.network_filter.is_user_ip_ignored(user)):
            return

        video_id = self.get_video_id("public", room, line)
        if not video_id:
            return

        parsed = self.parse_response(video_id)
        if not parsed:
            return

        for msg in self.settings["format"]:
            self.echo_public(room, self.str_replace(msg, parsed), self.settings["color"].lower())

    def incoming_private_chat_notification(self, user, line):

        if (self.core.network_filter.is_user_ignored(user)
                or self.core.network_filter.is_user_ip_ignored(user)):
            return

        video_id = self.get_video_id("private", user, line)
        if not video_id:
            return

        parsed = self.parse_response(video_id)
        if not parsed:
            return

        for msg in self.settings["format"]:
            self.echo_private(user, self.str_replace(msg, parsed), self.settings["color"].lower())

    def get_video_id(self, mode, source, line):

        match = re.search(r"(https?://((m|music)\.)?|www\.)youtu(\.be/|be\.com/(shorts/|watch\S+v=))"
                          r"(?P<video_id>[-\w]{11})", line)
        if not match:
            return None

        video_id = match.group("video_id")
        if source in self.last_video_id[mode] and self.last_video_id[mode][source] == video_id:
            return None

        self.last_video_id[mode][source] = video_id

        return video_id

    def parse_response(self, video_id):

        api_key = self.settings["api_key"]

        if not api_key:
            self.log("No API key specified")
            return None

        try:
            from urllib.request import urlopen
            with urlopen((f"https://www.googleapis.com/youtube/v3/videos?part=snippet,statistics,contentDetails"
                          f"&id={video_id}&key={api_key}"), timeout=10) as response:
                response_body = response.read().decode("utf-8", "replace")

        except Exception as error:
            self.log("Failed to connect to www.googleapis.com: %s", error)
            return None

        try:
            data = json.loads(response_body)

        except Exception as error:
            self.log("Failed to parse response from www.googleapis.com: %s", error)
            return None

        if "error" in data:
            error_message = data["error"].get("message", False)
            if not error_message:
                # This should not occur
                error_message = data["error"]
            self.log(error_message)
            return None

        total_results = data.get("pageInfo", {}).get("totalResults", False)

        if not total_results:
            if isinstance(total_results, int):
                # Video removed / invalid id
                self.log("Video unavailable")

            elif isinstance(total_results, bool):
                # This should not occur
                self.log("Youtube API appears to be broken")
            return None

        try:
            data = data["items"][0]

            title = data["snippet"]["title"]
            description = data["snippet"]["description"]
            channel = data["snippet"]["channelTitle"]
            live = data["snippet"]["liveBroadcastContent"]

            duration = data["contentDetails"]["duration"]
            quality = data["contentDetails"]["definition"].upper()

            views = data["statistics"].get("viewCount", "RESTRICTED")
            likes = data["statistics"].get("likeCount", "LIKES")

        except KeyError:
            # This should not occur
            self.log('An error occurred while parsing id "%s"', video_id)
            return None

        if likes != "LIKES":
            likes = humanize(int(likes))

        if views != "RESTRICTED":
            views = humanize(int(views))

        if live in {"live", "upcoming"}:
            duration = live.upper()
        else:
            duration = self.get_duration(duration)

        return {
            "%title%": title, "%description%": description, "%duration%": duration, "%quality%": quality,
            "%channel%": channel, "%views%": views, "%likes%": likes
        }

    @staticmethod
    def str_replace(subject, replacements):

        for string, replacement in replacements.items():
            if string in subject:
                subject = subject.replace(string, replacement)

        return subject

    @staticmethod
    def get_duration(iso_8601_duration):

        seconds = 0
        intervals = {"D": 86400, "H": 3600, "M": 60, "S": 1}

        for num, designator in re.findall(r"(\d+)([DHMS])", iso_8601_duration):
            seconds += intervals[designator] * int(num)

        return human_length(seconds)
