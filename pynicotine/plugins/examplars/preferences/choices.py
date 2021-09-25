# COPYRIGHT (C) 2021 Nicotine+ Team
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

from pynicotine.pluginsystem import BasePlugin


class Plugin(BasePlugin):
    """ Radio Button/Dropdown Example """

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        self.settings = {
            'player_radio': 2,                # id, starts from 0
            'player_dropdown': 'Clementine'   # can be either string or id starting from 0
        }
        self.metasettings = {
            'player_radio': {
                'description': 'Choose an audio player',
                'type': 'radio',
                'options': (
                    'Exaile',
                    'Audacious',
                    'Clementine'
                )
            },
            'player_dropdown': {
                'description': 'Choose an audio player',
                'type': 'dropdown',
                'options': (
                    'Exaile',
                    'Audacious',
                    'Clementine'
                )
            }
        }
