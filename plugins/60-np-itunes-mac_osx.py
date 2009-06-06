#!/usr/bin/env python

from subprocess import Popen, PIPE
from thread import start_new_thread

from pynicotine.pluginsystem import BasePlugin, returncode

class Plugin(BasePlugin):
    __name__ = "iTunes OSX Now Playing"
    __version__ = "2008-11-28r00"
    __desc__ = """NowPlaying command to use with iTunes on OSX (other operating systems not supported).

Usage: after enabling this plugin you can type /itunes in a chatroom or private conversation to show the world what you're listening to."""
    osascript = """
tell application "iTunes"
    set myartist to the artist of current track as string
    set mytrack to the name of current track
    set mystate to the player state
    if myartist is not "" then
        set info to (the myartist & the " - " & the mytrack)
    else
        set info to the mytrack
    end if
    set info to (the info & " [" & the mystate & "]")
end tell """
    

    def MyPublicCommand(self, room, args):
        # We'll fork the osascript since it' slow as hell
        start_new_thread(self.spam, (self.saypublic, room))
        return returncode['zap']
    def MyPrivateCommand(self, user, args):
        # We'll fork the osascript since it' slow as hell
        start_new_thread(self.spam, (self.sayprivate, user))
        return returncode['zap']
    def spam(self, callbackfunc, destination):
        self.log("Probing iTunes...")
        try:
            proc = Popen(['osascript','-e',self.osascript], stdout=PIPE)
        except OSError, inst:
            self.log("Probing failed (do you run MacOS?): " + str(inst))
            return
        (out, err) = proc.communicate()
        out = out.rstrip('\r\n ')
        if not out:
            self.log("The output was empty.")
            return
        out = ' '.join(['iTunes:',out])
        callbackfunc(destination, out)
    __publiccommands__ = [('itunes', MyPublicCommand)]
    __privatecommands__ = [('itunes',MyPrivateCommand)]
