# -*- coding: utf-8 -*-
import os
import sys

from thread import start_new_thread

from traceback import extract_stack, extract_tb, format_list
from pynicotine import slskmessages
from utils import _

WIN32 = sys.platform.startswith("win")

returncode = {'break':0, # don't give other plugins the event, do let n+ process it
              'zap':1,   # don't give other plugins the event, don't let n+ process it
              'pass':2}  # do give other plugins the event, do let n+ process it
                         # returning nothing is the same as 'pass'
tupletype = type(('',''))

class PluginHandler(object):
    frame = None # static variable... but should it be?
    def __init__(self, frame):
        self.frame = frame
        self.log("Loading plugin handler")
        self.myUsername = self.frame.np.config.sections["server"]["login"]
        self.plugins = []
        if WIN32:
            try:
                mydir = os.path.join(os.environ['APPDATA'], 'nicotine')
            except KeyError:
                # windows 9x?
                mydir,x = os.path.split(sys.argv[0])
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
    def TriggerPublicCommandEvent(self, room, command, args):
        return self._TriggerCommand("plugin.PublicCommandEvent", command, room, args)
    def TriggerPrivateCommandEvent(self, user, command, args):
        return self._TriggerCommand("plugin.PrivateCommandEvent", command, user, args)
    def _TriggerCommand(self, strfunc, command, source, args):
        for (module, plugin) in self.plugins:
            try:
                func = eval(strfunc)
                ret = func(command, source, args)
                if ret != None:
                    if ret == returncode['zap']:
                        return True
                    elif ret == returncode['pass']:
                        pass
                    else:
                        self.log(_("Plugin %(module) returned something weird, '%(value)', ignoring") % {'module':module, 'value':ret})
            except:
                self.log(_("Plugin %(module)s failed with error %(errortype)s: %(error)s.\nTrace: %(trace)s\nProblem area:%(area)s") %
                        {'module':module,
                         'errortype':sys.exc_info()[0],
                         'error':sys.exc_info()[1],
                         'trace':''.join(format_list(extract_stack())),
                         'area':''.join(format_list(extract_tb(sys.exc_info()[2])))})
        return False
    def TriggerEvent(self, function, args):
        """Triggers an event for the plugins. Since events and notifications
        are precisely the same except for how n+ responds to them, both can be
        triggered by this function."""
        hotpotato = args
        for (module, plugin) in self.plugins:
            try:
                func = eval("plugin." + function)
                ret = func(*hotpotato)
                if ret != None and type(ret) != tupletype:
                    if ret == returncode['zap']:
                        return None
                    elif ret == returncode['break']:
                        return hotpotato
                    elif ret == returncode['pass']:
                        pass
                    else:
                        self.log(_("Plugin %(module) returned something weird, '%(value)', ignoring") % {'module':module, 'value':ret})
                if ret != None:
                    hotpotato = ret
            except:
                self.log(_("Plugin %(module)s failed with error %(errortype)s: %(error)s.\nTrace: %(trace)s\nProblem area:%(area)s") %
                        {'module':module,
                         'errortype':sys.exc_info()[0],
                         'error':sys.exc_info()[1],
                         'trace':''.join(format_list(extract_stack())),
                         'area':''.join(format_list(extract_tb(sys.exc_info()[2])))})
        return hotpotato
    def IncomingPrivateChatEvent(self, user, line):
        if user != self.myUsername:
            # dont trigger the scripts on our own talking - we've got "Outgoing" for that
            return self.TriggerEvent("IncomingPrivateChatEvent", (user, line))
        else:
            return (user, line)
    def IncomingPrivateChatNotification(self, user, line):
        start_new_thread(self.TriggerEvent, ("IncomingPrivateChatNotification", (user, line)))
    def IncomingPublicChatEvent(self, room, user, line):
        if user != self.myUsername:
            # dont trigger the scripts on our own talking - we've got "Outgoing" for that
            return self.TriggerEvent("IncomingPublicChatEvent", (room, user, line))
        else:
            return (room, user, line)
    def IncomingPublicChatNotification(self, room, user, line):
        start_new_thread(self.TriggerEvent, ("IncomingPublicChatNotification", (room, user, line)))
    def OutgoingPrivateChatEvent(self, user, line):
        if line != None:
            # if line is None nobody actually said anything
            return self.TriggerEvent("OutgoingPrivateChatEvent", (user, line))
        else:
            return (user, line)
    def OutgoingPrivateChatNotification(self, user, line):
        start_new_thread(self.TriggerEvent, ("OutgoingPrivateChatNotification", (user, line)))
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
    def UserResolveNotification(self, user, ip, port, country):
        start_new_thread(self.TriggerEvent, ("UserResolveNotification", (user, ip, port, country)))
    def ServerConnectNotification(self):
        return
        # We're too early!
        start_new_thread(self.TriggerEvent, ("ServerConnectNotification", (),))
    def ServerDisconnectNotification(self):
        start_new_thread(self.TriggerEvent, ("ServerDisconnectNotification", (),))
    def JoinChatroomNotification(self, room):
        start_new_thread(self.TriggerEvent, ("JoinChatroomNotification", (room,)))
    def LeaveChatroomNotification(self, room): 
        start_new_thread(self.TriggerEvent, ("LeaveChatroomNotification", (room,)))
    # other functions
    def log(self, text):
        self.frame.logMessage(text)
    def saychatroom(self, room, text):
        self.frame.np.queue.put(slskmessages.SayChatroom(room, text))
    def sayprivate(self, user, text):
        # If we use the np the chat lines only show up on the receiving end, we won't see anything ourselves.
        self.frame.privatechats.users[user].SendMessage(text)

    
class BasePlugin(object):
    __name__ = "BasePlugin"
    __desc__ = "Blank"
    __version__ = "2008-11-26"
    __publiccommands__ = []
    __privatecommands__ = []
    def __init__(self, parent):
        # Never override this function, override init() instead
        self.parent = parent
        self.frame = parent.frame
        self.init()
        for (trigger, func) in self.__publiccommands__:
            self.frame.chatrooms.roomsctrl.CMDS.add('/'+trigger+' ')
        for (trigger, func) in self.__privatecommands__:
            self.frame.privatechats.CMDS.add('/'+trigger+' ')
    def init(self):
        pass
    def LoadEvent(self):
        pass
    def IncomingPrivateChatEvent(self, user, line):
        pass
    def IncomingPrivateChatNotification(self, user, line):
        pass
    def IncomingPublicChatEvent(self, room, user, line):
        pass
    def IncomingPublicChatNotification(self, room, user, line):
        pass
    def OutgoingPrivateChatEvent(self, user, line):
        pass
    def OutgoingPrivateChatNotification(self, user, line):
        pass
    def OutgoingPublicChatEvent(self, room, line):
        pass
    def OutgoingPublicChatNotification(self, room, line):
        pass
    def OutgoingGlobalSearchEvent(self, text):
        pass
    def OutgoingRoomSearchEvent(self, rooms, text):
        pass
    def OutgoingBuddySearchEvent(self, text):
        pass
    def OutgoingUserSearchEvent(self, users):
        pass
    def UserResolveNotification(self, user, ip, port, country):
        pass
    def PublicCommandEvent(self, command, room, args):
        for (trigger, func) in self.__publiccommands__:
            if trigger == command:
                return func(self, room, args)
    def PrivateCommandEvent(self, command, user, args):
        for (trigger, func) in self.__privatecommands__:
            if trigger == command:
                return func(self, user, args)
    def ServerConnectNotification(self):
        pass
    def ServerDisconnectNotification(self):
        pass
    def JoinChatroomNotification(self, room):
        pass
    def LeaveChatroomNotification(self, room):
        pass
    def log(self, text):
        self.parent.log(self.__name__ + ": " + text)
    def saypublic(self, room, text):
        self.parent.saychatroom(room, text)
    def sayprivate(self, user, text):
        self.parent.sayprivate(user, text)
    def fakepublic(self, room, user, text):
        try:
            room = self.frame.chatrooms.roomsctrl.joinedrooms[room]
        except KeyError:
            return False
        msg = slskmessages.SayChatroom(room, text)
        msg.user = user
        room.SayChatRoom(msg, text)
        return True
