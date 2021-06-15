from pynicotine.pluginsystem import BasePlugin


class Plugin(BasePlugin):
    __name__ = "Radio Button/Dropdown Example"
    settings = {
        'player_radio': 2,                # id, starts from 0
        'player_dropdown': 'Clementine',  # can be either string or id starting from 0
    }
    metasettings = {
        'player_radio': {
            'description': 'Choose an audio player',
            'type': 'radio',
            'options': (
                'Exaile',
                'Audacious',
                'Clementine'
            )},
        'player_dropdown': {
            'description': 'Choose an audio player',
            'type': 'dropdown',
            'options': (
                'Exaile',
                'Audacious',
                'Clementine'
            )}
    }
