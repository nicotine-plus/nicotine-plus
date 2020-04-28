from dogtail.tree import *
from dogtail.utils import run
from sys import exit

run('gedit')

gedit = root.application('gedit')

while True:
    try:
        gedit.child('Open').click()
    except SearchError: #toolbar not present?
        gedit.child('Open...').click()

    try:
        filechooser = gedit.child(name='Open Files', roleName='file chooser')
        filechooser.childNamed('Cancel').click()
    except SearchError:
        print('File chooser did not open')
        exit(1)
