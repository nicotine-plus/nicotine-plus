from pynicotine.pluginsystem import BasePlugin
from pynicotine.pluginsystem import returncode

from window_helper import get_now_playing


class Plugin(BasePlugin):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.settings = {
            "player": "None",
            "np_prefix": "/me np: ",
            "np_suffix": ""
        }
        self.metasettings = {
            "player": {
                "description": "Choose a media player:",
                "type": "dropdown",
                "options": (
                    "None",
                    "AIMP",
                    "Foobar2000",
                    "MediaMonkey 2024",
                    "MusicBee",
                    "Winamp",
                    "VLC Media Player"
                ),
            },
            'np_prefix': {
                'description': 'Now playing prefix:',
                'type': 'string'
            },
            'np_suffix': {
                'description': 'Now playing suffix:',
                'type': 'string'
            },
        }
        self.commands = {
            "np": {
                "callback": self.now_playing_command,
                "description": "Send now playing to current chat window."
            }
        }

    def now_playing_command(self, _args, **_unused):

        player = self.settings["player"]
        if player in ["None"]:
            self.log("No player selected")
            return returncode['zap']

        players = {
            "AIMP": ("Winamp v1.x", " - Winamp"),
            "Foobar2000": ("{97E27FAA-C0B3-4b8e-A693-ED7881E99FC1}", " [foobar2000]"),
            "MediaMonkey 2024": ("TMediaMonkeyInstanceManager", " - MediaMonkey 2024"),
            "MusicBee": ("WindowsForms10.Window.8.app.0.2bf8098_r8_ad1", " - MusicBee"),
            "Winamp": ("Winamp v1.x", " - Winamp"),
            "VLC Media Player": ("Qt5QWindowIcon", " - VLC media player"),
        }

        player_args = players[player]
        now_playing = get_now_playing(*player_args)

        if now_playing:
            prefix = self.settings['np_prefix']
            suffix = self.settings['np_suffix']
            now_playing = prefix + now_playing + suffix

            self.send_message(now_playing)
        else:
            self.log("%s process not detected." % player)

        return returncode['zap']
