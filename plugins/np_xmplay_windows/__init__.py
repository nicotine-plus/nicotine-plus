#!/usr/bin/env python3

from os.path import exists
from subprocess import PIPE
from subprocess import Popen

from _thread import start_new_thread
from pynicotine.pluginsystem import BasePlugin
from pynicotine.pluginsystem import returncode


def enable(frame):
    global PLUGIN
    PLUGIN = Plugin(frame)


def disable(frame):
    global PLUGIN
    PLUGIN = None


class Plugin(BasePlugin):
    __name__ = "XMPlay (Windows) Now Playing"
    __id__ = "np-xmplay-windows"
    settings = {
        'format': 'XMPlay: {%artist - }{%title }{[%album]}',
        'pythonbin': 'C:\\Python27\\Python.exe',
        'helperpath': 'C:\\xmplaynp.py',
    }
    metasettings = {
        'format': {'description': 'The layout of your np-message. Things between curly brackets will be removed if they did not change after filling in the information.', 'type': 'string'},
        'pythonbin': {'description': 'Path to your python executable', 'type': 'file'},
        'helperpath': {'description': 'Path to the helper file for this script', 'type': 'file'},
    }

    def OutgoingPublicChatEvent(self, room, line):
        # Workaround!
        if line in ('-xm', '-xmplay'):
            start_new_thread(self.spam, (self.saypublic, room))
            return returncode['zap']

    def OutgoingPrivateChatEvent(self, nick, line):
        # Workaround!
        if line in ('-xm', '-xmplay'):
            start_new_thread(self.spam, (self.sayprivate, nick))
            return returncode['zap']

    def MyPublicCommand(self, room, args):
        # We'll fork the request since it might be slow
        start_new_thread(self.spam, (self.saypublic, room))
        return returncode['zap']

    def MyPrivateCommand(self, user, args):
        # We'll fork the request since it might be slow
        start_new_thread(self.spam, (self.sayprivate, user))
        return returncode['zap']

    def spam(self, callbackfunc, destination):
        if not exists(self.settings['pythonbin']):
            self.log('The path to python, %s, does not exist. Edit your settings.' % self.settings['pythonbin'])
            return
        if not exists(self.settings['helperpath']):
            self.log('The path to the helper script, %s, does not exist. Edit your settings.' % self.settings['helperpath'])
            return
        self.log("Probing XMPlay...")
        try:
            proc = Popen([self.settings['pythonbin'], self.settings['helperpath'], self.settings['format']], stdout=PIPE)
        except Exception as inst:
            self.log("Probing failed (do you use Windows?): %s" % (inst,))
            return
        (out, err) = proc.communicate()
        out = out.rstrip('\r\n ')
        if not out:
            self.log("The output was empty.")
            return
        callbackfunc(destination, out)
    __publiccommands__ = [('xm', MyPublicCommand)]  # borked right now
    __privatecommands__ = [('xm', MyPrivateCommand)]  # borked right now
