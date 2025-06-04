import ctypes
import ctypes.wintypes
import re

from pynicotine.pluginsystem import BasePlugin
from pynicotine.pluginsystem import returncode


def get_now_playing(class_name, endswith_text):
    wnd_enum_proc = ctypes.WINFUNCTYPE(
        ctypes.wintypes.BOOL,
        ctypes.wintypes.HWND,
        ctypes.wintypes.LPARAM
    )
    found_text = None

    def enum_windows_callback(hwnd, _lparam):
        nonlocal found_text
        class_name_buffer = ctypes.create_unicode_buffer(256)
        text_buffer = ctypes.create_unicode_buffer(256)

        if ctypes.windll.user32.GetClassNameW(hwnd, class_name_buffer, 256) > 0:
            if class_name_buffer.value == class_name:
                if ctypes.windll.user32.GetWindowTextW(hwnd, text_buffer, 256) > 0:
                    window_text = text_buffer.value
                    if window_text.endswith(endswith_text):
                        found_text = window_text.removesuffix(endswith_text)
                        if endswith_text in {" - Winamp", " - MediaMonkey 2024"}:
                            found_text = re.sub(r"^\d+\.\s", "", found_text)  # strip track number
                        return False  # Stop enumeration once found
        return True  # Continue enumeration

    enum_func = wnd_enum_proc(enum_windows_callback)
    ctypes.windll.user32.EnumWindows(enum_func, 0)

    return found_text


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
        if player == "None":
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

        return None
