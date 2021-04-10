from pynicotine.pluginsystem import BasePlugin


def enable(plugins):
    global PLUGIN
    PLUGIN = Plugin(plugins)


def disable(plugins):
    global PLUGIN
    PLUGIN = None


class Plugin(BasePlugin):
    __name__ = "Radio Button Example"
    settings = {
        'player': 2,
    }
    metasettings = {
        'player': {
            'description': 'Choose an audio player',
            'type': 'radio',
            'options': (
                'Exaile',
                'Audacious',
                'Clementine'
            )}
    }
