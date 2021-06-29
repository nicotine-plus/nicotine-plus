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

    __name__ = "File Chooser Example"
    settings = {
        'file': '/home/example/file.pdf',
        'folder': '/home/example/folder',
        'image': '/home/example/image.jpg',
    }
    metasettings = {
        'file': {
            'description': 'Select a file',
            'type': 'file',
            'chooser': 'file'},
        'folder': {
            'description': 'Select a folder',
            'type': 'file',
            'chooser': 'folder'},
        'image': {
            'description': 'Select an image',
            'type': 'file',
            'chooser': 'image'},
    }
