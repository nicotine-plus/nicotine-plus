# -*- coding: utf-8 -*-
import os
import sys

from thread import start_new_thread

from traceback import extract_stack, extract_tb, format_list
from pynicotine import slskmessages

WIN32 = sys.platform.startswith("win")

returncode = {'break':0, # don't give other plugins the event, do let n+ process it
              'zap':1,   # don't give other plugins the event, don't let n+ process it
              'pass':2}  # do give other plugins the event, do let n+ process it
                         # returning nothing is the same as 'pass'
tupletype = type(('',''))

class PluginHandler(object):
    frame = None # static variable
    def __init__(self, frame):
        self.frame = frame
        self.log("Loading plugin handler")
        self.plugins = []
        if WIN32:
            mydir = (os.path.split(sys.argv[0]))[0]
            self.plugindir = os.path.join(mydir, "plugins")
        else:
            self.plugindir = os.path.join(os.path.expanduser("~"),'.nicotine','plugins')
        if os.path.isdir(self.plugindir):
            self.load(self.plugindir)
        else:
            self.log("It appears '%s' is not a directory, not loading plugins." % self.plugindir)
    def load(self, directory):
        """Loads all plugins in the given directory."""
        pyfiles = [x for x in os.listdir(directory) if x[-3:] == '.py' and len(x) > 3]
        pyfiles.sort()
        for f in pyfiles:
            (modulename, sep, ext) = f.rpartition('.')
            # http://mail.python.org/pipermail/python-list/2005-July/331818.html
            sys.path.insert(0, directory)
            try:
                module = __import__(modulename,[],[],[],0)
                instance = module.Plugin(self)
                instance.LoadEvent()
                self.log("Loaded plugin %s (version %s) from %s" % (instance.__name__, instance.__version__, modulename))
                self.plugins.append((module, instance))
            except:
                self.log("While loading %s an error occurred, %s: %s.\nTrace: %s\nProblem area:%s" %
                       (modulename,
                        sys.exc_info()[0],
                        sys.exc_info()[1],
                        ''.join(format_list(extract_stack())),
                        ''.join(format_list(extract_tb(sys.exc_info()[2])))))
            sys.path.pop(0)
        self.log("Loaded " + str(len(self.plugins)) + " plugins.")
    def reread(self):
        """Reloads plugins so changes in the .py files are processed. Might not
        actually work (see python docs on reloading)"""
        self.log("Rereading plugins.")
        sys.path.insert(0, self.plugindir)
        for (module, plugin) in self.plugins:
            try:
                module = reload(module)
            except:
                self.log("Failed to reload module " + repr(module))
        sys.path.pop(0)
    def reload(self):
        """Reloads already loaded plugins."""
        self.reread()
        self.plugins = []
        self.load(self.plugindir)
    def TriggerEvent(self, function, args):
        """Triggers an event for the plugins. Since events and notifications
        are precisely the same except for how n+ responds to them, both can be
        triggered by this function."""
        #print "%s by handler. %s plugins active" % (function, str(len(self.plugins)))
        hotpotato = args
        for (module, plugin) in self.plugins:
            #print "Trying " + repr(plugin)
            try:
                func = eval("plugin." + function)
                ret = func(*hotpotato)
                if ret != None and type(ret) != tupletype:
                    print "Some return code since %s != %s" % (type(ret), tupletype)
                    if ret == returncode['zap']:
                        print "zapped"
                        return None
                    elif ret == returncode['stop']:
                        print "stopped"
                        return hotpotato
                    elif ret == returncode['pass']:
                        print "passing"
                        pass
                    else:
                        self.log("Plugin returned something weird (" + repr(ret) + "), ignoring")
                if ret != None:
                    hotpotato = ret
            except:
                self.log("Plugin %s failed with error %s: %s.\nTrace: %s\nProblem area:%s" %
                        (module,
                        sys.exc_info()[0],
                        sys.exc_info()[1],
                        ''.join(format_list(extract_stack())),
                        ''.join(format_list(extract_tb(sys.exc_info()[2])))))
        print function + " Potato is " + repr(hotpotato)
        return hotpotato
    def IncomingPrivateChatEvent(self, nick, line):
        if nick != self.frame.np.config.sections["server"]["login"]:
            # dont trigger the scripts on our own talking - we've got "Outgoing" for that
            return self.TriggerEvent("IncomingPrivateChatEvent", (nick, line))
        else:
            return (nick, line)
    def IncomingPrivateChatNotification(self, nick, line):
        start_new_thread(self.TriggerEvent, ("IncomingPrivateChatNotification", (nick, line)))
    def IncomingPublicChatEvent(self, room, nick, line):
        if nick != self.frame.np.config.sections["server"]["login"]:
            # dont trigger the scripts on our own talking - we've got "Outgoing" for that
            return self.TriggerEvent("IncomingPublicChatEvent", (room, nick, line))
        else:
            return (room, nick, line)
    def IncomingPublicChatNotification(self, room, nick, line):
        start_new_thread(self.TriggerEvent, ("IncomingPublicChatNotification", (room, nick, line)))
    def OutgoingPrivateChatEvent(self, nick, line):
        if line != None:
            # if line is None nobody actually said anything
            return self.TriggerEvent("OutgoingPrivateChatEvent", (nick, line))
        else:
            print "Line is none"
            return (nick, line)
    def OutgoingPrivateChatNotification(self, nick, line):
        start_new_thread(self.TriggerEvent, ("OutgoingPublicChatEvent", (nick, line)))
    def OutgoingPublicChatEvent(self, room, line):
        return self.TriggerEvent("OutgoingPublicChatEvent", (room, line))
    def OutgoingPublicChatNotification(self, room, line):
        start_new_thread(self.TriggerEvent, ("OutgoingPublicChatNotification", (room, line)))
    def OutgoingGlobalSearchEvent(self, text):
        return self.TriggerEvent("OutgoingGlobalSearchEvent", (text,))
    def OutgoingRoomSearchEvent(self, rooms, text):
        return self.TriggerEvent("OutgoingRoomSearchEvent", (rooms, text))
    def OutgoingBuddySearchEvent(self, text):
        return self.TriggerEvent("OutgoingBuddySearchEvent", (text,))
    def OutgoingUserSearchEvent(self, users):
        return self.TriggerEvent("OutgoingUserSearchEvent", (users,))
    # other functions
    def log(self, text):
        self.frame.logMessage(text)
    def SayChatroom(self, room, text):
        self.frame.np.queue.put(slskmessages.SayChatroom(room, text))
    
class BasePlugin(object):
    __name__ = "BasePlugin"
    __desc__ = "Blank"
    __version__ = "2008-07-05"
    def __init__(self, parent):
        self.parent = parent
    def LoadEvent(self):
        pass
    def IncomingPrivateChatEvent(self, nick, line):
        pass
    def IncomingPrivateChatNotification(self, nick, line):
        pass
    def IncomingPublicChatEvent(self, room, nick, line):
        pass
    def IncomingPublicChatNotification(self, room, nick, line):
        pass
    def OutgoingPrivateChatEvent(self, nick, line):
        pass
    def OutgoingPrivateChatNotification(self, nick, line):
        pass
    def OutgoingPublicChatEvent(self, nick, line):
        pass
    def OutgoingPublicChatNotification(self, nick, line):
        pass
    def OutgoingGlobalSearchEvent(self, text):
        pass
    def OutgoingRoomSearchEvent(self, rooms, text):
        pass
    def OutgoingBuddySearchEvent(self, text):
        pass
    def OutgoingUserSearchEvent(self, users):
        pass

    def log(self, text):
        self.parent.log(self.__name__ + ": " + text)
