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
