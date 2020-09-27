# COPYRIGHT (C) 2020 Nicotine+ Team
# COPYRIGHT (C) 2020 Mathias <mail@mathias.is>
# COPYRIGHT (C) 2016-2017 Michael Labouebe <gfarmerfr@free.fr>
# COPYRIGHT (C) 2016 Mutnick <muhing@yahoo.com>
# COPYRIGHT (C) 2013 eL_vErDe <gandalf@le-vert.net>
# COPYRIGHT (C) 2008-2012 Quinox <quinox@users.sf.net>
# COPYRIGHT (C) 2009 Hedonist <ak@sensi.org>
# COPYRIGHT (C) 2006-2009 Daelstorm <daelstorm@gmail.com>
# COPYRIGHT (C) 2003-2004 Hyriand <hyriand@thegraveyard.org>
# COPYRIGHT (C) 2001-2003 Alexander Kanavin
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

"""
This is the actual client code. Actual GUI classes are in the separate modules
"""

import configparser
import datetime
import os
import queue
import shutil
import threading
import time
from gettext import gettext as _
from socket import socket

from pynicotine import slskmessages
from pynicotine import slskproto
from pynicotine import transfers
from pynicotine.config import Config
from pynicotine.geoip import IP2Location
from pynicotine.logfacility import log
from pynicotine.shares import Shares
from pynicotine.slskmessages import PopupMessage
from pynicotine.slskmessages import newId
from pynicotine.utils import CleanFile
from pynicotine.utils import unescape
from pynicotine.utils import write_log


class PeerConnection:
    """
    Holds information about a peer connection. Not every field may be set
    to something. addr is (ip, port) address, conn is a socket object, msgs is
    a list of outgoing pending messages, token is a reverse-handshake
    number (protocol feature), init is a PeerInit protocol message. (read
    slskmessages docstrings for explanation of these)
    """

    def __init__(self, addr=None, username=None, conn=None, msgs=None, token=None, init=None, conntimer=None, tryaddr=None):
        self.addr = addr
        self.username = username
        self.conn = conn
        self.msgs = msgs
        self.token = token
        self.init = init
        self.conntimer = conntimer
        self.tryaddr = tryaddr


class Timeout:

    def __init__(self, callback):
        self.callback = callback

    def timeout(self):
        try:
            self.callback([self])
        except Exception as e:
            print(("Exception in callback %s: %s" % (self.callback, e)))


class ConnectToPeerTimeout(Timeout):

    def __init__(self, conn, callback):
        self.conn = conn
        self.callback = callback


class RespondToDistributedSearchesTimeout(Timeout):
    pass


class NetworkEventProcessor:
    """ This class contains handlers for various messages from the networking
    thread"""

    def __init__(self, frame, callback, writelog, setstatus, bindip, port, data_dir, config):

        self.frame = frame
        self.callback = callback
        self.logMessage = writelog
        self.setStatus = setstatus

        try:
            self.config = Config(config, data_dir)
        except configparser.Error:
            corruptfile = ".".join([config, CleanFile(datetime.datetime.now().strftime("%Y-%M-%d_%H:%M:%S")), "corrupt"])
            shutil.move(config, corruptfile)
            short = _("Your config file is corrupt")
            long = _("We're sorry, but it seems your configuration file is corrupt. Please reconfigure Nicotine+.\n\nWe renamed your old configuration file to\n%(corrupt)s\nIf you open this file with a text editor you might be able to rescue some of your settings.") % {'corrupt': corruptfile}
            self.config = Config(config, data_dir)
            self.callback([PopupMessage(short, long)])

        # These strings are accessed frequently. We store them to prevent requesting the translation every time.
        self.conn_close_template = _("Connection closed by peer: %s")
        self.conn_remove_template = _("Removed connection closed by peer: %(conn_obj)s %(address)s")

        self.bindip = bindip
        self.port = port
        self.config.frame = frame
        self.config.readConfig()
        self.peerconns = []
        self.watchedusers = []
        self.ipblock_requested = {}
        self.ipignore_requested = {}
        self.ip_requested = []
        self.PrivateMessageQueue = {}
        self.users = {}
        self.user_addr_requested = set()
        self.queue = queue.Queue(0)
        self.shares = Shares(self, self.config, self.queue, self.logMessage)

        script_dir = os.path.dirname(__file__)
        file_path = os.path.join(script_dir, "geoip/ipcountrydb.bin")
        self.geoip = IP2Location.IP2Location(file_path, "SHARED_MEMORY")

        # Give the logger information about log folder
        self.UpdateDebugLogOptions()

        self.protothread = slskproto.SlskProtoThread(self.frame.networkcallback, self.queue, self.bindip, self.port, self.config, self)

        uselimit = self.config.sections["transfers"]["uselimit"]
        uploadlimit = self.config.sections["transfers"]["uploadlimit"]
        limitby = self.config.sections["transfers"]["limitby"]

        self.queue.put(slskmessages.SetUploadLimit(uselimit, uploadlimit, limitby))
        self.queue.put(slskmessages.SetDownloadLimit(self.config.sections["transfers"]["downloadlimit"]))

        if self.config.sections["transfers"]["geoblock"]:
            panic = self.config.sections["transfers"]["geopanic"]
            cc = self.config.sections["transfers"]["geoblockcc"]
            self.queue.put(slskmessages.SetGeoBlock([panic, cc]))
        else:
            self.queue.put(slskmessages.SetGeoBlock(None))

        self.serverconn = None
        self.waitport = None
        self.chatrooms = None
        self.privatechat = None
        self.globallist = None
        self.userinfo = None
        self.userbrowse = None
        self.search = None
        self.transfers = None
        self.userlist = None
        self.logintime = None
        self.ipaddress = None
        self.privileges_left = None
        self.servertimer = None
        self.servertimeout = -1

        self.has_parent = False
        self.branchlevel = 0
        self.branchroot = None

        self.requestedInfo = {}
        self.requestedFolders = {}
        self.speed = 0

        self.respondDistributed = True
        responddistributedtimeout = RespondToDistributedSearchesTimeout(self.callback)
        self.respondDistributedTimer = threading.Timer(60, responddistributedtimeout.timeout)
        self.respondDistributedTimer.setDaemon(True)
        self.respondDistributedTimer.start()

        # Callback handlers for messages
        self.events = {
            slskmessages.ConnectToServer: self.ConnectToServer,
            slskmessages.ConnectError: self.ConnectError,
            slskmessages.IncPort: self.IncPort,
            slskmessages.ServerConn: self.ServerConn,
            slskmessages.ConnClose: self.ConnClose,
            slskmessages.Login: self.Login,
            slskmessages.ChangePassword: self.ChangePassword,
            slskmessages.MessageUser: self.MessageUser,
            slskmessages.PMessageUser: self.PMessageUser,
            slskmessages.ExactFileSearch: self.DummyMessage,
            slskmessages.UserJoinedRoom: self.UserJoinedRoom,
            slskmessages.SayChatroom: self.SayChatRoom,
            slskmessages.JoinRoom: self.JoinRoom,
            slskmessages.UserLeftRoom: self.UserLeftRoom,
            slskmessages.QueuedDownloads: self.DummyMessage,
            slskmessages.GetPeerAddress: self.GetPeerAddress,
            slskmessages.OutConn: self.OutConn,
            slskmessages.UserInfoReply: self.UserInfoReply,
            slskmessages.UserInfoRequest: self.UserInfoRequest,
            slskmessages.PierceFireWall: self.PierceFireWall,
            slskmessages.CantConnectToPeer: self.CantConnectToPeer,
            slskmessages.PeerTransfer: self.PeerTransfer,
            slskmessages.SharedFileList: self.SharedFileList,
            slskmessages.GetSharedFileList: self.shares.GetSharedFileList,
            slskmessages.FileSearchRequest: self.FileSearchRequest,
            slskmessages.FileSearchResult: self.FileSearchResult,
            slskmessages.ConnectToPeer: self.ConnectToPeer,
            slskmessages.GetUserStatus: self.GetUserStatus,
            slskmessages.GetUserStats: self.GetUserStats,
            slskmessages.Relogged: self.Relogged,
            slskmessages.PeerInit: self.PeerInit,
            slskmessages.DownloadFile: self.FileDownload,
            slskmessages.UploadFile: self.FileUpload,
            slskmessages.FileRequest: self.FileRequest,
            slskmessages.TransferRequest: self.TransferRequest,
            slskmessages.TransferResponse: self.TransferResponse,
            slskmessages.QueueUpload: self.QueueUpload,
            slskmessages.QueueFailed: self.QueueFailed,
            slskmessages.UploadFailed: self.UploadFailed,
            slskmessages.PlaceInQueue: self.PlaceInQueue,
            slskmessages.FileError: self.FileError,
            slskmessages.FolderContentsResponse: self.FolderContentsResponse,
            slskmessages.FolderContentsRequest: self.shares.FolderContentsRequest,
            slskmessages.RoomList: self.RoomList,
            slskmessages.LeaveRoom: self.LeaveRoom,
            slskmessages.GlobalUserList: self.GlobalUserList,
            slskmessages.AddUser: self.AddUser,
            slskmessages.PrivilegedUsers: self.PrivilegedUsers,
            slskmessages.AddToPrivileged: self.AddToPrivileged,
            slskmessages.CheckPrivileges: self.CheckPrivileges,
            slskmessages.ServerPing: self.DummyMessage,
            slskmessages.ParentMinSpeed: self.DummyMessage,
            slskmessages.ParentSpeedRatio: self.DummyMessage,
            slskmessages.ParentInactivityTimeout: self.DummyMessage,
            slskmessages.SearchInactivityTimeout: self.DummyMessage,
            slskmessages.MinParentsInCache: self.DummyMessage,
            slskmessages.WishlistInterval: self.WishlistInterval,
            slskmessages.DistribAliveInterval: self.DummyMessage,
            slskmessages.ChildDepth: self.ChildDepth,
            slskmessages.BranchLevel: self.BranchLevel,
            slskmessages.BranchRoot: self.BranchRoot,
            slskmessages.DistribChildDepth: self.DistribChildDepth,
            slskmessages.DistribBranchLevel: self.DistribBranchLevel,
            slskmessages.DistribBranchRoot: self.DistribBranchRoot,
            slskmessages.AdminMessage: self.AdminMessage,
            slskmessages.TunneledMessage: self.TunneledMessage,
            slskmessages.IncConn: self.IncConn,
            slskmessages.PlaceholdUpload: self.DummyMessage,
            slskmessages.PlaceInQueueRequest: self.PlaceInQueueRequest,
            slskmessages.UploadQueueNotification: self.UploadQueueNotification,
            slskmessages.SearchRequest: self.SearchRequest,
            slskmessages.FileSearch: self.SearchRequest,
            slskmessages.RoomSearch: self.RoomSearchRequest,
            slskmessages.UserSearch: self.SearchRequest,
            slskmessages.PossibleParents: self.PossibleParents,
            slskmessages.DistribAlive: self.DummyMessage,
            slskmessages.DistribSearch: self.DistribSearch,
            slskmessages.DistribServerSearch: self.DistribSearch,
            ConnectToPeerTimeout: self.ConnectToPeerTimeout,
            RespondToDistributedSearchesTimeout: self.ToggleRespondDistributed,
            transfers.TransferTimeout: self.TransferTimeout,
            str: self.Notify,
            slskmessages.PopupMessage: self.PopupMessage,
            slskmessages.SetCurrentConnectionCount: self.SetCurrentConnectionCount,
            slskmessages.DebugMessage: self.DebugMessage,
            slskmessages.GlobalRecommendations: self.GlobalRecommendations,
            slskmessages.Recommendations: self.Recommendations,
            slskmessages.ItemRecommendations: self.ItemRecommendations,
            slskmessages.SimilarUsers: self.SimilarUsers,
            slskmessages.ItemSimilarUsers: self.ItemSimilarUsers,
            slskmessages.UserInterests: self.UserInterests,
            slskmessages.RoomTickerState: self.RoomTickerState,
            slskmessages.RoomTickerAdd: self.RoomTickerAdd,
            slskmessages.RoomTickerRemove: self.RoomTickerRemove,
            slskmessages.UserPrivileged: self.UserPrivileged,
            slskmessages.AckNotifyPrivileges: self.AckNotifyPrivileges,
            slskmessages.NotifyPrivileges: self.NotifyPrivileges,
            slskmessages.PrivateRoomUsers: self.PrivateRoomUsers,
            slskmessages.PrivateRoomOwned: self.PrivateRoomOwned,
            slskmessages.PrivateRoomAddUser: self.PrivateRoomAddUser,
            slskmessages.PrivateRoomRemoveUser: self.PrivateRoomRemoveUser,
            slskmessages.PrivateRoomAdded: self.PrivateRoomAdded,
            slskmessages.PrivateRoomRemoved: self.PrivateRoomRemoved,
            slskmessages.PrivateRoomDisown: self.PrivateRoomDisown,
            slskmessages.PrivateRoomToggle: self.PrivateRoomToggle,
            slskmessages.PrivateRoomSomething: self.PrivateRoomSomething,
            slskmessages.PrivateRoomOperatorAdded: self.PrivateRoomOperatorAdded,
            slskmessages.PrivateRoomOperatorRemoved: self.PrivateRoomOperatorRemoved,
            slskmessages.PrivateRoomAddOperator: self.PrivateRoomAddOperator,
            slskmessages.PrivateRoomRemoveOperator: self.PrivateRoomRemoveOperator,
            slskmessages.PublicRoomMessage: self.PublicRoomMessage,
            slskmessages.UnknownPeerMessage: self.DummyMessage,
        }

    def ProcessRequestToPeer(self, user, message, window=None, address=None):
        """
        Sends message to a peer and possibly sets up a window to display
        the result.
        """

        conn = None

        if message.__class__ is not slskmessages.FileRequest:
            for i in self.peerconns:
                if i.username == user and i.init.type == 'P':
                    conn = i
                    break

        if conn is not None and conn.conn is not None:

            message.conn = conn.conn

            self.queue.put(message)

            if window is not None:
                window.InitWindow(conn.username, conn.conn)

            if message.__class__ is slskmessages.TransferRequest and self.transfers is not None:
                self.transfers.gotConnect(message.req, conn.conn, message.direction)

            return

        else:

            if message.__class__ is slskmessages.FileRequest:
                type = 'F'
            elif message.__class__ is slskmessages.DistribConn:
                type = 'D'
            else:
                type = 'P'

            init = slskmessages.PeerInit(None, self.config.sections["server"]["login"], type, 0)
            firewalled = self.config.sections["server"]["firewalled"]
            addr = None
            behindfw = None
            token = None

            if user in self.users:
                addr = self.users[user].addr
                behindfw = self.users[user].behindfw
            elif address is not None:
                self.users[user] = UserAddr(status=-1, addr=address)
                addr = address

            if firewalled:
                if addr is None:
                    if user not in self.user_addr_requested:
                        self.queue.put(slskmessages.GetPeerAddress(user))
                        self.user_addr_requested.add(user)
                elif behindfw is None:
                    self.queue.put(slskmessages.OutConn(None, addr))
                else:
                    firewalled = 0

            if not firewalled:
                token = newId()
                self.queue.put(slskmessages.ConnectToPeer(token, user, type))

            conn = PeerConnection(addr=addr, username=user, msgs=[message], token=token, init=init)
            self.peerconns.append(conn)

            if token is not None:
                timeout = 120.0
                conntimeout = ConnectToPeerTimeout(self.peerconns[-1], self.callback)
                timer = threading.Timer(timeout, conntimeout.timeout)
                timer.setDaemon(True)
                self.peerconns[-1].conntimer = timer
                timer.start()

        if message.__class__ is slskmessages.TransferRequest and self.transfers is not None:

            if conn.addr is None:
                self.transfers.gettingAddress(message.req, message.direction)
            elif conn.token is None:
                self.transfers.gotAddress(message.req, message.direction)
            else:
                self.transfers.gotConnectError(message.req, message.direction)

    def setServerTimer(self):

        if self.servertimeout == -1:
            self.servertimeout = 15
        elif 0 < self.servertimeout < 600:
            self.servertimeout = self.servertimeout * 2

        self.servertimer = threading.Timer(self.servertimeout, self.ServerTimeout)
        self.servertimer.setDaemon(True)
        self.servertimer.start()

        self.setStatus(_("The server seems to be down or not responding, retrying in %i seconds") % (self.servertimeout))

    def ServerTimeout(self):
        if self.config.needConfig() <= 1:
            self.callback([slskmessages.ConnectToServer()])

    def StopTimers(self):

        for i in self.peerconns:
            if i.conntimer is not None:
                i.conntimer.cancel()

        if self.servertimer is not None:
            self.servertimer.cancel()

        if self.respondDistributedTimer is not None:
            self.respondDistributedTimer.cancel()

        if self.transfers is not None:
            self.transfers.AbortTransfers()

    def ConnectToServer(self, msg):
        self.frame.OnConnect(None)

    # Notify user of error when recieving or sending a message
    # @param self NetworkEventProcessor (Class)
    # @param string a string containing an error message
    def Notify(self, string):
        self.logMessage("%s" % string, 4)

    def PopupMessage(self, msg):
        self.setStatus(_(msg.title))
        self.frame.PopupMessage(msg)

    def DummyMessage(self, msg):
        self.logMessage("%s %s" % (msg.__class__, vars(msg)), 4)

    def DebugMessage(self, msg):
        self.logMessage(msg.msg, msg.debugLevel)

    def SetCurrentConnectionCount(self, msg):
        self.frame.SetSocketStatus(msg.msg)

    def ConnectError(self, msg):

        if msg.connobj.__class__ is slskmessages.ServerConn:

            self.setStatus(
                _("Can't connect to server %(host)s:%(port)s: %(error)s") % {
                    'host': msg.connobj.addr[0],
                    'port': msg.connobj.addr[1],
                    'error': msg.err
                }
            )

            self.setServerTimer()

            if self.serverconn is not None:
                self.serverconn = None

            self.frame.ConnectError(msg)

        elif msg.connobj.__class__ is slskmessages.OutConn:

            for i in self.peerconns:

                if i.addr == msg.connobj.addr and i.conn is None:

                    if i.token is None:

                        i.token = newId()
                        self.queue.put(slskmessages.ConnectToPeer(i.token, i.username, i.init.type))

                        if i.username in self.users:
                            self.users[i.username].behindfw = "yes"

                        for j in i.msgs:
                            if j.__class__ is slskmessages.TransferRequest and self.transfers is not None:
                                self.transfers.gotConnectError(j.req, j.direction)

                        conntimeout = ConnectToPeerTimeout(i, self.callback)
                        timer = threading.Timer(120.0, conntimeout.timeout)
                        timer.setDaemon(True)
                        timer.start()

                        if i.conntimer is not None:
                            i.conntimer.cancel()

                        i.conntimer = timer

                    else:
                        for j in i.msgs:
                            if j.__class__ in [slskmessages.TransferRequest, slskmessages.FileRequest] and self.transfers is not None:
                                self.transfers.gotCantConnect(j.req)

                        self.logMessage(
                            _("Can't connect to %s, sending notification via the server") % (i.username),
                            3
                        )
                        self.queue.put(slskmessages.CantConnectToPeer(i.token, i.username))

                        if i.conntimer is not None:
                            i.conntimer.cancel()

                        self.peerconns.remove(i)

                    break
            else:
                self.logMessage("%s %s %s" % (msg.err, msg.__class__, vars(msg)), 4)

        else:
            self.logMessage("%s %s %s" % (msg.err, msg.__class__, vars(msg)), 4)

            self.ClosedConnection(msg.connobj.conn, msg.connobj.addr, msg.err)

    def IncPort(self, msg):
        self.waitport = msg.port
        self.setStatus(_("Listening on port %i") % (msg.port))

    def ServerConn(self, msg):

        self.setStatus(
            _("Connected to server %(host)s:%(port)s, logging in...") % {
                'host': msg.addr[0],
                'port': msg.addr[1]
            }
        )

        self.serverconn = msg.conn
        self.servertimeout = -1
        self.users = {}
        self.queue.put(
            slskmessages.Login(
                self.config.sections["server"]["login"],
                self.config.sections["server"]["passw"],

                # Afaik, the client version was set to 157 ns at some point in the past
                # to support distributed searches properly. Probably no reason to mess
                # with this (yet)

                # Soulseek client version; 155, 156, 157, 180, 181, 183
                157,

                # Soulseek client minor version
                # 17 stands for 157 ns 13c, 19 for 157 ns 13e
                # For client versions newer than 157, the minor version is probably 1
                19,
            )
        )
        if self.waitport is not None:
            self.queue.put(slskmessages.SetWaitPort(self.waitport))

    def PeerInit(self, msg):
        self.peerconns.append(
            PeerConnection(
                addr=msg.conn.addr,
                username=msg.user,
                conn=msg.conn.conn,
                init=msg,
                msgs=[]
            )
        )

    def ConnClose(self, msg):
        self.ClosedConnection(msg.conn, msg.addr)

    def ClosedConnection(self, conn, addr, error=None):

        if conn == self.serverconn:

            self.setStatus(
                _("Disconnected from server %(host)s:%(port)s") % {
                    'host': addr[0],
                    'port': addr[1]
                }
            )
            userchoice = bool(self.frame.manualdisconnect)

            if not self.frame.manualdisconnect:
                self.setServerTimer()
            else:
                self.frame.manualdisconnect = 0

            if self.respondDistributedTimer is not None:
                self.respondDistributedTimer.cancel()

            self.serverconn = None
            self.watchedusers = []

            if self.transfers is not None:
                self.transfers.AbortTransfers()
                self.transfers.SaveDownloads()

            self.privatechat = self.chatrooms = self.userinfo = self.userbrowse = self.search = self.transfers = self.userlist = None
            self.frame.ConnClose(conn, addr)
            self.frame.pluginhandler.ServerDisconnectNotification(userchoice)

        else:
            for i in self.peerconns:
                if i.conn == conn:
                    self.logMessage(self.conn_close_template % vars(i), debugLevel=3)

                    if i.conntimer is not None:
                        i.conntimer.cancel()

                    if self.transfers is not None:
                        self.transfers.ConnClose(conn, addr, i.username, error)

                    if i == self.GetParentConn():
                        self.ParentConnClosed()

                    self.peerconns.remove(i)
                    break
            else:
                self.logMessage(
                    self.conn_remove_template % {
                        'conn_obj': conn,
                        'address': addr
                    },
                    3
                )

    def Login(self, msg):

        self.logintime = time.time()
        conf = self.config.sections

        if msg.success:

            self.transfers = transfers.Transfers(conf["transfers"]["downloads"], self.peerconns, self.queue, self, self.users)

            if msg.ip is not None:
                self.ipaddress = msg.ip

            self.privatechat, self.chatrooms, self.userinfo, self.userbrowse, self.search, downloads, uploads, self.userlist = self.frame.InitInterface(msg)

            self.transfers.setTransferPanels(downloads, uploads)
            self.shares.send_num_shared_folders_files()
            self.queue.put(slskmessages.SetStatus((not self.frame.away) + 1))

            for thing in self.config.sections["interests"]["likes"]:
                self.queue.put(slskmessages.AddThingILike(thing))
            for thing in self.config.sections["interests"]["dislikes"]:
                self.queue.put(slskmessages.AddThingIHate(thing))

            self.queue.put(slskmessages.HaveNoParent(1))

            """ TODO: Nicotine+ can currently receive search requests from a parent connection, but
            redirecting results to children is not implemented yet. Tell the server we don't accept
            children for now. """
            self.queue.put(slskmessages.AcceptChildren(0))

            self.queue.put(slskmessages.NotifyPrivileges(1, self.config.sections["server"]["login"]))
            self.privatechat.Login()
            self.queue.put(slskmessages.CheckPrivileges())
            self.queue.put(slskmessages.PrivateRoomToggle(self.config.sections["server"]["private_chatrooms"]))
        else:
            self.frame.manualdisconnect = 1
            self.setStatus(_("Can not log in, reason: %s") % (msg.reason))

            if self.frame.settingswindow is not None:
                self.frame.settingswindow.SetSettings(self.config.sections)
                self.frame.settingswindow.SwitchToPage("Server")

    def ChangePassword(self, msg):
        password = msg.password
        self.config.sections["server"]["passw"] = password
        self.config.writeConfiguration()
        self.callback([PopupMessage(_("Your password has been changed"), "Password is %s" % password)])

    def NotifyPrivileges(self, msg):

        if msg.token is not None:
            pass

        self.logMessage("%s %s" % (msg.__class__, vars(msg)), 4)

    def UserPrivileged(self, msg):
        if self.transfers is not None:
            if msg.privileged is True:
                self.transfers.addToPrivileged(msg.user)

    def AckNotifyPrivileges(self, msg):

        if msg.token is not None:
            # Until I know the syntax, sending this message is probably a bad idea
            self.queue.put(slskmessages.AckNotifyPrivileges(msg.token))

        self.logMessage("%s %s" % (msg.__class__, vars(msg)), 4)

    def PMessageUser(self, msg):

        user = ip = port = None

        # Get peer's username, ip and port
        for i in self.peerconns:
            if i.conn is msg.conn.conn:
                user = i.username
                if i.addr is not None:
                    ip, port = i.addr
                break

        if user is None:
            # No peer connection
            return

        if user != msg.user:
            text = _("(Warning: %(realuser)s is attempting to spoof %(fakeuser)s) ") % {"realuser": user, "fakeuser": msg.user} + msg.msg
            msg.user = user
        else:
            text = msg.msg

        if self.privatechat is not None:
            self.privatechat.ShowMessage(msg, text, status=0)

        self.logMessage("%s %s" % (msg.__class__, vars(msg)), 4)

    def MessageUser(self, msg):

        status = 0
        if self.logintime:
            if time.time() <= self.logintime + 2:
                # Offline message
                status = 1

        if self.privatechat is not None:

            tuple = self.frame.pluginhandler.IncomingPrivateChatEvent(msg.user, msg.msg)

            if tuple is not None:
                (u, msg.msg) = tuple
                self.privatechat.ShowMessage(msg, msg.msg, status=status)
                self.frame.pluginhandler.IncomingPrivateChatNotification(msg.user, msg.msg)

            self.queue.put(slskmessages.MessageAcked(msg.msgid))

        self.logMessage("%s %s" % (msg.__class__, vars(msg)), 4)

    def UserJoinedRoom(self, msg):

        if self.chatrooms is not None:
            self.chatrooms.roomsctrl.UserJoinedRoom(msg)

        self.logMessage("%s %s" % (msg.__class__, vars(msg)), 4)

    def PublicRoomMessage(self, msg):

        if self.chatrooms is not None:
            self.chatrooms.roomsctrl.PublicRoomMessage(msg, msg.msg)
            self.frame.pluginhandler.PublicRoomMessageNotification(msg.room, msg.user, msg.msg)
        else:
            self.logMessage("%s %s" % (msg.__class__, vars(msg)), 4)

    def JoinRoom(self, msg):

        if self.chatrooms is not None:

            self.chatrooms.roomsctrl.JoinRoom(msg)

        self.logMessage("%s %s" % (msg.__class__, vars(msg)), 4)

    def PrivateRoomUsers(self, msg):
        if self.chatrooms is not None:
            self.chatrooms.roomsctrl.PrivateRoomUsers(msg)
        self.logMessage("%s %s" % (msg.__class__, vars(msg)), 4)

    def PrivateRoomOwned(self, msg):
        if self.chatrooms is not None:
            self.chatrooms.roomsctrl.PrivateRoomOwned(msg)
        self.logMessage("%s %s" % (msg.__class__, vars(msg)), 4)

    def PrivateRoomAddUser(self, msg):
        if self.chatrooms is not None:
            self.chatrooms.roomsctrl.PrivateRoomAddUser(msg)
        self.logMessage("%s %s" % (msg.__class__, vars(msg)), 4)

    def PrivateRoomRemoveUser(self, msg):
        if self.chatrooms is not None:
            self.chatrooms.roomsctrl.PrivateRoomRemoveUser(msg)
        self.logMessage("%s %s" % (msg.__class__, vars(msg)), 4)

    def PrivateRoomOperatorAdded(self, msg):
        if self.chatrooms is not None:
            self.chatrooms.roomsctrl.PrivateRoomOperatorAdded(msg)
        self.logMessage("%s %s" % (msg.__class__, vars(msg)), 4)

    def PrivateRoomOperatorRemoved(self, msg):
        if self.chatrooms is not None:
            self.chatrooms.roomsctrl.PrivateRoomOperatorRemoved(msg)
        self.logMessage("%s %s" % (msg.__class__, vars(msg)), 4)

    def PrivateRoomAddOperator(self, msg):
        if self.chatrooms is not None:
            self.chatrooms.roomsctrl.PrivateRoomAddOperator(msg)
        self.logMessage("%s %s" % (msg.__class__, vars(msg)), 4)

    def PrivateRoomRemoveOperator(self, msg):
        if self.chatrooms is not None:
            self.chatrooms.roomsctrl.PrivateRoomRemoveOperator(msg)
        self.logMessage("%s %s" % (msg.__class__, vars(msg)), 4)

    def PrivateRoomAdded(self, msg):
        if self.chatrooms is not None:
            self.chatrooms.roomsctrl.PrivateRoomAdded(msg)
        self.logMessage("%s %s" % (msg.__class__, vars(msg)), 4)

    def PrivateRoomRemoved(self, msg):
        if self.chatrooms is not None:
            self.chatrooms.roomsctrl.PrivateRoomRemoved(msg)
        self.logMessage("%s %s" % (msg.__class__, vars(msg)), 4)

    def PrivateRoomDisown(self, msg):
        if self.chatrooms is not None:
            self.chatrooms.roomsctrl.PrivateRoomDisown(msg)
        self.logMessage("%s %s" % (msg.__class__, vars(msg)), 4)

    def PrivateRoomToggle(self, msg):
        if self.chatrooms is not None:
            self.chatrooms.roomsctrl.TogglePrivateRooms(msg.enabled)
        self.logMessage("%s %s" % (msg.__class__, vars(msg)), 4)

    def PrivateRoomSomething(self, msg):
        pass

    def LeaveRoom(self, msg):
        if self.chatrooms is not None:
            self.chatrooms.roomsctrl.LeaveRoom(msg)
        else:
            self.logMessage("%s %s" % (msg.__class__, vars(msg)), 4)

    def PrivateMessageQueueAdd(self, msg, text):

        user = msg.user

        if user not in self.PrivateMessageQueue:
            self.PrivateMessageQueue[user] = [[msg, text]]
        else:
            self.PrivateMessageQueue[user].append([msg, text])

    def PrivateMessageQueueProcess(self, user):

        if user in self.PrivateMessageQueue:
            for data in self.PrivateMessageQueue[user][:]:
                msg, text = data
                self.PrivateMessageQueue[user].remove(data)
                self.privatechat.ShowMessage(msg, text, status=0)

    def ipIgnored(self, address):

        if address is None:
            return True

        ips = self.config.sections["server"]["ipignorelist"]
        s_address = address.split(".")

        for ip in ips:

            # No Wildcard in IP
            if "*" not in ip:
                if address == ip:
                    return True
                continue

            # Wildcard in IP
            parts = ip.split(".")
            seg = 0

            for part in parts:
                # Stop if there's no wildcard or matching string number
                if part not in (s_address[seg], "*"):
                    break

                seg += 1

                # Last time around
                if seg == 4:
                    # Wildcard blocked
                    return True

        # Not blocked
        return False

    def SayChatRoom(self, msg):

        if self.chatrooms is not None:
            event = self.frame.pluginhandler.IncomingPublicChatEvent(msg.room, msg.user, msg.msg)
            if event is not None:
                (r, n, msg.msg) = event
                self.chatrooms.roomsctrl.SayChatRoom(msg, msg.msg)
                self.frame.pluginhandler.IncomingPublicChatNotification(msg.room, msg.user, msg.msg)
        else:
            self.logMessage("%s %s" % (msg.__class__, vars(msg)), 4)

    def AddUser(self, msg):

        if msg.user not in self.watchedusers:
            self.watchedusers.append(msg.user)

        if not msg.userexists:
            if msg.user not in self.users:
                self.users[msg.user] = UserAddr(status=-1)

        if self.transfers is not None:
            self.transfers.getAddUser(msg)
        else:
            self.logMessage("%s %s" % (msg.__class__, vars(msg)), 4)

        if msg.status is not None:
            self.GetUserStatus(msg)
        elif msg.userexists and msg.status is None:
            self.queue.put(slskmessages.GetUserStatus(msg.user))

        if msg.files is not None:
            self.GetUserStats(msg)

    def PrivilegedUsers(self, msg):

        if self.transfers is not None:
            self.transfers.setPrivilegedUsers(msg.users)
            self.logMessage(_("%i privileged users") % (len(msg.users)))
            self.queue.put(slskmessages.HaveNoParent(1))
            self.queue.put(slskmessages.AddUser(self.config.sections["server"]["login"]))
            self.frame.pluginhandler.ServerConnectNotification()
        else:
            self.logMessage("%s %s" % (msg.__class__, vars(msg)), 4)

    def AddToPrivileged(self, msg):
        if self.transfers is not None:
            self.transfers.addToPrivileged(msg.user)
        else:
            self.logMessage("%s %s" % (msg.__class__, vars(msg)), 4)

    def CheckPrivileges(self, msg):

        mins = msg.seconds // 60
        hours = mins // 60
        days = hours // 24

        if msg.seconds == 0:
            self.logMessage(
                _("You have no privileges left. They are not necessary, but allow your downloads to be queued ahead of non-privileged users.")
            )
        else:
            self.logMessage(
                _("%(days)i days, %(hours)i hours, %(minutes)i minutes, %(seconds)i seconds of download privileges left.") % {
                    'days': days,
                    'hours': hours % 24,
                    'minutes': mins % 60,
                    'seconds': msg.seconds % 60
                }
            )

        self.privileges_left = msg.seconds

    def AdminMessage(self, msg):
        self.logMessage("%s" % (msg.msg))

    def ChildDepth(self, msg):
        # TODO: Implement me
        self.logMessage("%s %s" % (msg.__class__, vars(msg)), 4)

    def BranchLevel(self, msg):
        # TODO: Implement me
        self.logMessage("%s %s" % (msg.__class__, vars(msg)), 4)

    def BranchRoot(self, msg):
        # TODO: Implement me
        self.logMessage("%s %s" % (msg.__class__, vars(msg)), 4)

    def DistribChildDepth(self, msg):
        # TODO: Implement me
        self.logMessage("%s %s" % (msg.__class__, vars(msg)), 4)

    def DistribBranchRoot(self, msg):
        # TODO: Implement me
        self.logMessage("%s %s" % (msg.__class__, vars(msg)), 4)

    def WishlistInterval(self, msg):
        if self.search is not None:
            self.search.WishList.set_interval(msg)
        else:
            self.logMessage("%s %s" % (msg.__class__, vars(msg)), 4)

    def GetUserStatus(self, msg):

        # Causes recursive requests when privileged?
        # self.queue.put(slskmessages.AddUser(msg.user))
        if msg.user in self.users:
            if msg.status == 0:
                self.users[msg.user] = UserAddr(status=msg.status)
            else:
                self.users[msg.user].status = msg.status
        else:
            self.users[msg.user] = UserAddr(status=msg.status)

        if msg.privileged is not None:
            if msg.privileged == 1:
                if self.transfers is not None:
                    self.transfers.addToPrivileged(msg.user)
                else:
                    self.logMessage("%s %s" % (msg.__class__, vars(msg)), 4)

        self.frame.GetUserStatus(msg)

        if self.userlist is not None:
            self.userlist.GetUserStatus(msg)

        if self.transfers is not None:
            self.transfers.GetUserStatus(msg)

        if self.privatechat is not None:
            self.privatechat.GetUserStatus(msg)

        if self.userinfo is not None:
            self.userinfo.GetUserStatus(msg)

        if self.userbrowse is not None:
            self.userbrowse.GetUserStatus(msg)

        if self.chatrooms is not None:
            self.chatrooms.roomsctrl.GetUserStatus(msg)
        else:
            self.logMessage("%s %s" % (msg.__class__, vars(msg)), 4)

    def UserInterests(self, msg):

        if self.userinfo is not None:
            self.userinfo.ShowInterests(msg)

        self.logMessage("%s %s" % (msg.__class__, vars(msg)), 4)

    def GetUserStats(self, msg):

        if msg.user == self.config.sections["server"]["login"]:
            self.speed = msg.avgspeed

        self.frame.GetUserStats(msg)

        if self.chatrooms is not None:
            self.chatrooms.roomsctrl.GetUserStats(msg)

        if self.userinfo is not None:
            self.userinfo.GetUserStats(msg)

        if self.userlist is not None:
            self.userlist.GetUserStats(msg)
        else:
            self.logMessage("%s %s" % (msg.__class__, vars(msg)), 4)

        stats = {
            'avgspeed': msg.avgspeed,
            'downloadnum': msg.downloadnum,
            'files': msg.files,
            'dirs': msg.dirs,
        }

        self.frame.pluginhandler.UserStatsNotification(msg.user, stats)

    def UserLeftRoom(self, msg):
        if self.chatrooms is not None:
            self.chatrooms.roomsctrl.UserLeftRoom(msg)
        else:
            self.logMessage("%s %s" % (msg.__class__, vars(msg)), 4)

    def GetPeerAddress(self, msg):

        user = msg.user

        for i in self.peerconns:
            if i.username == user and i.addr is None:
                if msg.port != 0 or i.tryaddr == 10:
                    if i.tryaddr == 10:
                        self.logMessage(
                            _("Server reported port 0 for the 10th time for user %(user)s, giving up") % {
                                'user': msg.user
                            },
                            3
                        )
                    elif i.tryaddr is not None:
                        self.logMessage(
                            _("Server reported non-zero port for user %(user)s after %(tries)i retries") % {
                                'user': msg.user,
                                'tries': i.tryaddr
                            },
                            3
                        )

                    if user in self.user_addr_requested:
                        self.user_addr_requested.remove(user)

                    i.addr = (msg.ip, msg.port)
                    i.tryaddr = None

                    self.queue.put(slskmessages.OutConn(None, i.addr))

                    for j in i.msgs:
                        if j.__class__ is slskmessages.TransferRequest and self.transfers is not None:
                            self.transfers.gotAddress(j.req, j.direction)
                else:
                    if i.tryaddr is None:
                        i.tryaddr = 1
                        self.logMessage(
                            _("Server reported port 0 for user %(user)s, retrying") % {
                                'user': user
                            },
                            3
                        )
                    else:
                        i.tryaddr += 1

                    self.queue.put(slskmessages.GetPeerAddress(user))
        else:

            if msg.user in self.users:
                self.users[msg.user].addr = (msg.ip, msg.port)
            else:
                self.users[msg.user] = UserAddr(addr=(msg.ip, msg.port))

            if msg.user in self.ipblock_requested:

                if self.ipblock_requested[msg.user]:
                    self.frame.OnUnBlockUser(msg.user)
                else:
                    self.frame.OnBlockUser(msg.user)

                del self.ipblock_requested[msg.user]
                return

            if msg.user in self.ipignore_requested:

                if self.ipignore_requested[msg.user]:
                    self.frame.OnUnIgnoreUser(msg.user)
                else:
                    self.frame.OnIgnoreUser(msg.user)

                del self.ipignore_requested[msg.user]
                return

            cc = self.geoip.get_all(msg.ip).country_short

            if cc == "-":
                cc = ""

            self.frame.HasUserFlag(msg.user, "flag_" + cc)

            # From this point on all paths should call
            # self.frame.pluginhandler.UserResolveNotification precisely once
            if msg.user in self.PrivateMessageQueue:
                self.PrivateMessageQueueProcess(msg.user)
            if msg.user not in self.ip_requested:
                self.frame.pluginhandler.UserResolveNotification(msg.user, msg.ip, msg.port)
                return

            self.ip_requested.remove(msg.user)

            if cc != "":
                cc = " (%s)" % cc

            message = _("IP address of %(user)s is %(ip)s, port %(port)i%(country)s") % {
                'user': msg.user,
                'ip': msg.ip,
                'port': msg.port,
                'country': cc
            }

            self.logMessage(message)
            self.frame.pluginhandler.UserResolveNotification(msg.user, msg.ip, msg.port, cc)

    def Relogged(self, msg):
        self.logMessage(_("Someone else is logging in with the same nickname, server is going to disconnect us"))
        self.frame.manualdisconnect = 1
        self.frame.pluginhandler.ServerDisconnectNotification(False)

    def OutConn(self, msg):

        for i in self.peerconns:

            if i.addr == msg.addr and i.conn is None:

                if i.token is None:
                    i.init.conn = msg.conn
                    self.queue.put(i.init)
                else:
                    self.queue.put(slskmessages.PierceFireWall(msg.conn, i.token))

                i.conn = msg.conn

                for j in i.msgs:

                    if j.__class__ is slskmessages.UserInfoRequest and self.userinfo is not None:
                        self.userinfo.InitWindow(i.username, msg.conn)

                    if j.__class__ is slskmessages.GetSharedFileList and self.userbrowse is not None:
                        self.userbrowse.InitWindow(i.username, msg.conn)

                    if j.__class__ is slskmessages.FileRequest and self.transfers is not None:
                        self.transfers.gotFileConnect(j.req, msg.conn)

                    if j.__class__ is slskmessages.TransferRequest and self.transfers is not None:
                        self.transfers.gotConnect(j.req, msg.conn, j.direction)

                    j.conn = msg.conn
                    self.queue.put(j)

                i.msgs = []
                break

        self.logMessage("%s %s" % (msg.__class__, vars(msg)), 3)

    def IncConn(self, msg):
        self.logMessage("%s %s" % (msg.__class__, vars(msg)), 3)

    def ConnectToPeer(self, msg):
        init = slskmessages.PeerInit(None, msg.user, msg.type, 0)

        self.queue.put(slskmessages.OutConn(None, (msg.ip, msg.port), init))
        self.peerconns.append(
            PeerConnection(
                addr=(msg.ip, msg.port),
                username=msg.user,
                msgs=[],
                token=msg.token,
                init=init
            )
        )
        self.logMessage("%s %s" % (msg.__class__, vars(msg)), 3)

    def CheckUser(self, user, addr):
        """
        Check if this user is banned, geoip-blocked, and which shares
        it is allowed to access based on transfer and shares settings.
        """

        if user in self.config.sections["server"]["banlist"]:
            if self.config.sections["transfers"]["usecustomban"]:
                return 0, "Banned (%s)" % self.config.sections["transfers"]["customban"]
            else:
                return 0, "Banned"

        if user in [i[0] for i in self.config.sections["server"]["userlist"]] and self.config.sections["transfers"]["enablebuddyshares"]:
            # For sending buddy-only shares
            return 2, ""

        if user in [i[0] for i in self.config.sections["server"]["userlist"]]:
            return 1, ""

        if self.config.sections["transfers"]["friendsonly"]:
            return 0, "Sorry, friends only"

        if not self.config.sections["transfers"]["geoblock"]:
            return 1, ""

        cc = "-"
        if addr is not None:
            cc = self.geoip.get_all(addr).country_short

        if cc == "-":
            if self.config.sections["transfers"]["geopanic"]:
                return 0, "Sorry, geographical paranoia"
            else:
                return 1, ""

        if self.config.sections["transfers"]["geoblockcc"][0].find(cc) >= 0:
            return 0, "Sorry, your country is blocked"

        return 1, ""

    def CheckSpoof(self, user, ip, port):

        if user not in self.users:
            return 0

        if self.users[user].addr is not None:

            if len(self.users[user].addr) == 2:
                if self.users[user].addr is not None:
                    u_ip, u_port = self.users[user].addr
                    if u_ip != ip:
                        warning = _("IP %(ip)s:%(port)s is spoofing user %(user)s with a peer request, blocking because it does not match IP: %(real_ip)s") % {
                            'ip': ip,
                            'port': port,
                            'user': user,
                            'real_ip': u_ip
                        }
                        self.logMessage(warning, 1)
                        print(warning)
                        return 1
        return 0

    def ClosePeerConnection(self, peerconn):
        try:
            conn = peerconn.conn
        except AttributeError:
            conn = peerconn

        if conn is None:
            return

        if not self.protothread.socketStillActive(conn):
            self.queue.put(slskmessages.ConnClose(conn))

            if type(peerconn) is socket:

                for i in self.peerconns:
                    if i.conn == peerconn:
                        self.peerconns.remove(i)
                        break
            else:
                try:
                    self.peerconns.remove(peerconn)
                except ValueError:
                    pass

    def UserInfoReply(self, msg):
        for i in self.peerconns:
            if i.conn is msg.conn.conn and self.userinfo is not None:
                # probably impossible to do this
                if i.username != self.config.sections["server"]["login"]:
                    self.userinfo.ShowInfo(i.username, msg)
                    break

    def UserInfoRequest(self, msg):

        user = ip = port = None

        # Get peer's username, ip and port
        for i in self.peerconns:
            if i.conn is msg.conn.conn:
                user = i.username
                if i.addr is not None:
                    ip, port = i.addr
                break

        if user is None:
            # No peer connection
            return

        requestTime = time.time()

        if user in self.requestedInfo:
            if not requestTime > 10 + self.requestedInfo[user]:
                # Ignoring request, because it's 10 or less seconds since the
                # last one by this user
                return

        self.requestedInfo[user] = requestTime

        # Check address is spoofed, if possible
        if user == self.config.sections["server"]["login"]:

            if ip is not None and port is not None:
                self.logMessage(
                    _("Blocking %(user)s from making a UserInfo request, possible spoofing attempt from IP %(ip)s port %(port)s") % {
                        'user': user,
                        'ip': ip,
                        'port': port
                    },
                    1
                )
            else:
                self.logMessage(
                    _("Blocking %s from making a UserInfo request, possible spoofing attempt from an unknown IP & port") % (user),
                    1
                )

            if msg.conn.conn is not None:
                self.queue.put(slskmessages.ConnClose(msg.conn.conn))

            return

        if user in self.config.sections["server"]["banlist"]:

            self.logMessage(
                _("%(user)s is banned, but is making a UserInfo request") % {
                    'user': user
                },
                1
            )

            self.logMessage("%s %s" % (msg.__class__, vars(msg)), 1)

            return

        try:
            userpic = self.config.sections["userinfo"]["pic"]

            with open(userpic, 'rb') as f:
                pic = f.read()

        except Exception:
            pic = None

        descr = unescape(self.config.sections["userinfo"]["descr"])

        if self.transfers is not None:
            totalupl = self.transfers.getTotalUploadsAllowed()
            queuesize = self.transfers.getUploadQueueSizes()[0]
            slotsavail = self.transfers.allowNewUploads()

            if self.frame.np.config.sections["transfers"]["remotedownloads"]:
                uploadallowed = self.frame.np.config.sections["transfers"]["uploadallowed"]
            else:
                uploadallowed = 0

            self.queue.put(slskmessages.UserInfoReply(msg.conn.conn, descr, pic, totalupl, queuesize, slotsavail, uploadallowed))

        self.logMessage(
            _("%(user)s is making a UserInfo request") % {
                'user': user
            },
            1
        )

    def SharedFileList(self, msg):
        for i in self.peerconns:
            if i.conn is msg.conn.conn and self.userbrowse is not None:
                if i.username != self.config.sections["server"]["login"]:
                    self.userbrowse.ShowInfo(i.username, msg)
                    break

    def FileSearchResult(self, msg):
        if self.search is not None:
            if msg.conn.addr:
                country = self.geoip.get_all(msg.conn.addr[0]).country_short
            else:
                country = ""

            if country == "-":
                country = ""

            self.search.ShowResult(msg, msg.user, country)
            self.ClosePeerConnection(msg.conn)

        self.logMessage("%s %s" % (msg.__class__, vars(msg)), 4)

    def PierceFireWall(self, msg):

        for i in self.peerconns:

            if i.token == msg.token and i.conn is None:

                if i.conntimer is not None:
                    i.conntimer.cancel()

                i.init.conn = msg.conn.conn
                self.queue.put(i.init)
                i.conn = msg.conn.conn

                for j in i.msgs:

                    if j.__class__ is slskmessages.UserInfoRequest and self.userinfo is not None:
                        self.userinfo.InitWindow(i.username, msg.conn.conn)

                    if j.__class__ is slskmessages.GetSharedFileList and self.userbrowse is not None:
                        self.userbrowse.InitWindow(i.username, msg.conn.conn)

                    if j.__class__ is slskmessages.FileRequest and self.transfers is not None:
                        self.transfers.gotFileConnect(j.req, msg.conn.conn)

                    if j.__class__ is slskmessages.TransferRequest and self.transfers is not None:
                        self.transfers.gotConnect(j.req, msg.conn.conn, j.direction)

                    j.conn = msg.conn.conn
                    self.queue.put(j)

                i.msgs = []
                break

        self.logMessage("%s %s" % (msg.__class__, vars(msg)), 3)

    def CantConnectToPeer(self, msg):

        for i in self.peerconns:

            if i.token == msg.token:

                if i.conntimer is not None:
                    i.conntimer.cancel()

                if i == self.GetParentConn():
                    self.ParentConnClosed()

                self.peerconns.remove(i)

                self.logMessage(_("Can't connect to %s (either way), giving up") % (i.username), 3)

                for j in i.msgs:
                    if j.__class__ in [slskmessages.TransferRequest, slskmessages.FileRequest] and self.transfers is not None:
                        self.transfers.gotCantConnect(j.req)
                break

    def ConnectToPeerTimeout(self, msg):
        conn = msg.conn

        if conn == self.GetParentConn():
            self.ParentConnClosed()

        try:
            self.peerconns.remove(conn)
        except ValueError:
            pass

        self.logMessage(_("User %s does not respond to connect request, giving up") % (conn.username), 3)

        for i in conn.msgs:
            if i.__class__ in [slskmessages.TransferRequest, slskmessages.FileRequest] and self.transfers is not None:
                self.transfers.gotCantConnect(i.req)

    def TransferTimeout(self, msg):
        if self.transfers is not None:
            self.transfers.TransferTimeout(msg)
        else:
            self.logMessage("%s %s" % (msg.__class__, vars(msg)), 4)

    def FileDownload(self, msg):
        if self.transfers is not None:
            self.transfers.FileDownload(msg)
        else:
            self.logMessage("%s %s" % (msg.__class__, vars(msg)), 4)

    def FileUpload(self, msg):
        if self.transfers is not None:
            self.transfers.FileUpload(msg)
        else:
            self.logMessage("%s %s" % (msg.__class__, vars(msg)), 4)

    def FileRequest(self, msg):
        if self.transfers is not None:
            self.transfers.FileRequest(msg)
        else:
            self.logMessage("%s %s" % (msg.__class__, vars(msg)), 4)

    def FileError(self, msg):
        if self.transfers is not None:
            self.transfers.FileError(msg)
        else:
            self.logMessage("%s %s" % (msg.__class__, vars(msg)), 4)

    def TransferRequest(self, msg):
        if self.transfers is not None:
            self.transfers.TransferRequest(msg)
        else:
            self.logMessage("%s %s" % (msg.__class__, vars(msg)), 4)

    def TransferResponse(self, msg):
        if self.transfers is not None:
            self.transfers.TransferResponse(msg)
        else:
            self.logMessage("%s %s" % (msg.__class__, vars(msg)), 4)

    def QueueUpload(self, msg):
        if self.transfers is not None:
            self.transfers.QueueUpload(msg)
        else:
            self.logMessage("%s %s" % (msg.__class__, vars(msg)), 4)

    def QueueFailed(self, msg):
        if self.transfers is not None:
            self.transfers.QueueFailed(msg)
        else:
            self.logMessage("%s %s" % (msg.__class__, vars(msg)), 4)

    def PlaceInQueueRequest(self, msg):
        if self.transfers is not None:
            self.transfers.PlaceInQueueRequest(msg)
        else:
            self.logMessage("%s %s" % (msg.__class__, vars(msg)), 4)

    def UploadQueueNotification(self, msg):
        self.logMessage("%s %s" % (msg.__class__, vars(msg)), 4)
        self.transfers.UploadQueueNotification(msg)

    def UploadFailed(self, msg):
        if self.transfers is not None:
            self.transfers.UploadFailed(msg)
        else:
            self.logMessage("%s %s" % (msg.__class__, vars(msg)), 4)

    def PlaceInQueue(self, msg):
        if self.transfers is not None:
            self.transfers.PlaceInQueue(msg)
        else:
            self.logMessage("%s %s" % (msg.__class__, vars(msg)), 4)

    def FolderContentsResponse(self, msg):
        if self.transfers is not None:
            conn = msg.conn.conn
            file_list = msg.list

            # Check for a large number of files
            many = False
            folder = ""

            for i in file_list:
                for j in file_list[i]:
                    if os.path.commonprefix([i, j]) == j:
                        numfiles = len(file_list[i][j])
                        if numfiles > 100:
                            many = True
                            folder = j

            if many:
                for i in self.peerconns:
                    if i.conn is conn:
                        username = i.username
                        break

                self.frame.download_large_folder(username, folder, numfiles, conn, file_list)
            else:
                self.transfers.FolderContentsResponse(conn, file_list)
        else:
            self.logMessage("%s %s" % (msg.__class__, vars(msg)), 4)

    def RoomList(self, msg):
        if self.chatrooms is not None:
            self.chatrooms.roomsctrl.SetRoomList(msg)
            self.setStatus("")
        else:
            self.logMessage("%s %s" % (msg.__class__, vars(msg)), 4)

    def GlobalUserList(self, msg):
        if self.globallist is not None:
            self.globallist.setGlobalUsersList(msg)
        else:
            self.logMessage("%s %s" % (msg.__class__, vars(msg)), 4)

    def PeerTransfer(self, msg):
        if self.userinfo is not None and msg.msg is slskmessages.UserInfoReply:
            self.userinfo.UpdateGauge(msg)
        if self.userbrowse is not None and msg.msg is slskmessages.SharedFileList:
            self.userbrowse.UpdateGauge(msg)

    def TunneledMessage(self, msg):

        if msg.code in self.protothread.peerclasses:
            peermsg = self.protothread.peerclasses[msg.code](None)
            peermsg.parseNetworkMessage(msg.msg)
            peermsg.tunneleduser = msg.user
            peermsg.tunneledreq = msg.req
            peermsg.tunneledaddr = msg.addr
            self.callback([peermsg])
        else:
            self.logMessage(_("Unknown tunneled message: %s") % (vars(msg)), 4)

    def FileSearchRequest(self, msg):
        self.logMessage("%s %s" % (msg.__class__, vars(msg)), 4)
        for i in self.peerconns:
            if i.conn == msg.conn.conn:
                user = i.username
                self.shares.process_search_request(msg.searchterm, user, msg.searchid, direct=1)
                break

    def SearchRequest(self, msg):
        self.logMessage("%s %s" % (msg.__class__, vars(msg)), 4)
        self.shares.process_search_request(msg.searchterm, msg.user, msg.searchid, direct=0)
        self.frame.pluginhandler.SearchRequestNotification(msg.searchterm, msg.user, msg.searchid)

    def RoomSearchRequest(self, msg):
        self.logMessage("%s %s" % (msg.__class__, vars(msg)), 4)
        self.shares.process_search_request(msg.searchterm, msg.room, msg.searchid, direct=0)

    def ToggleRespondDistributed(self, msg, settings=False):
        """
        Toggle responding to distributed search each (default: 60sec)
        interval
        """

        if not self.config.sections["searches"]["search_results"]:
            # Don't return _any_ results when this option is disabled
            if self.respondDistributedTimer is not None:
                self.respondDistributedTimer.cancel()
            self.respondDistributed = False
            return

        if self.respondDistributedTimer is not None:
            self.respondDistributedTimer.cancel()

        if self.config.sections["searches"]["distrib_timer"]:

            if not settings:
                # Don't toggle when just changing the settings
                self.respondDistributed = not self.respondDistributed

            responddistributedtimeout = RespondToDistributedSearchesTimeout(self.callback)
            self.respondDistributedTimer = threading.Timer(self.config.sections["searches"]["distrib_ignore"], responddistributedtimeout.timeout)
            self.respondDistributedTimer.setDaemon(True)
            self.respondDistributedTimer.start()
        else:
            # Always respond
            self.respondDistributed = True

    def DistribSearch(self, msg):
        if self.respondDistributed:  # set in ToggleRespondDistributed
            self.shares.process_search_request(msg.searchterm, msg.user, msg.searchid, 0)
        self.frame.pluginhandler.DistribSearchNotification(msg.searchterm, msg.user, msg.searchid)

    def PossibleParents(self, msg):

        """ Server sent a list of 10 potential parents, whose purpose is to forward us search requests.
        We attempt to connect to them all at once, since connection errors are fairly common. """

        potential_parents = msg.list

        if potential_parents:

            for user in potential_parents:
                addr = potential_parents[user]

                self.ProcessRequestToPeer(user, slskmessages.DistribConn(), None, addr)

        self.logMessage("%s %s" % (msg.__class__, vars(msg)), 4)

    def GetParentConn(self):
        for i in self.peerconns:
            if i.init.type == 'D':
                return i

        return None

    def ParentConnClosed(self):
        """ Tell the server it needs to send us a NetInfo message with a new list of
        potential parents. """

        self.has_parent = False
        self.queue.put(slskmessages.HaveNoParent(1))

    def DistribBranchLevel(self, msg):
        """ This message is received when we have a successful connection with a potential
        parent. Tell the server who our parent is, and stop requesting new potential parents. """

        if not self.has_parent:

            for i in self.peerconns[:]:
                if i.init.type == 'D':
                    """ We previously attempted to connect to all potential parents. Since we now
                    have a parent, stop connecting to the others. """

                    if i.conn != msg.conn.conn:
                        if i.conn is not None:
                            self.queue.put(slskmessages.ConnClose(i.conn))

                        self.peerconns.remove(i)

            parent = self.GetParentConn()

            if parent is not None:
                self.queue.put(slskmessages.HaveNoParent(0))
                self.queue.put(slskmessages.SearchParent(msg.conn.addr[0]))
                self.has_parent = True
            else:
                self.ParentConnClosed()

        self.logMessage("%s %s" % (msg.__class__, vars(msg)), 4)

    def GlobalRecommendations(self, msg):
        self.frame.GlobalRecommendations(msg)

    def Recommendations(self, msg):
        self.frame.Recommendations(msg)

    def ItemRecommendations(self, msg):
        self.frame.ItemRecommendations(msg)

    def SimilarUsers(self, msg):
        self.frame.SimilarUsers(msg)

    def ItemSimilarUsers(self, msg):
        self.frame.ItemSimilarUsers(msg)

    def RoomTickerState(self, msg):

        if self.chatrooms is not None:
            self.chatrooms.roomsctrl.TickerSet(msg)

        self.logMessage("%s %s" % (msg.__class__, vars(msg)), 4)

    def RoomTickerAdd(self, msg):

        if self.chatrooms is not None:
            self.chatrooms.roomsctrl.TickerAdd(msg)

        self.logMessage("%s %s" % (msg.__class__, vars(msg)), 4)

    def RoomTickerRemove(self, msg):
        if self.chatrooms is not None:
            self.chatrooms.roomsctrl.TickerRemove(msg)
        self.logMessage("%s %s" % (msg.__class__, vars(msg)), 4)

    def logTransfer(self, message, toUI=0):

        if self.config.sections["logging"]["transfers"]:
            timestamp_format = self.config.sections["logging"]["log_timestamp"]
            write_log(self.config.sections["logging"]["transferslogsdir"], "transfers", message, timestamp_format)

        if toUI:
            self.logMessage(message)

    def UpdateDebugLogOptions(self):
        """ Gives the logger updated logging settings """

        should_log = self.config.sections["logging"]["debug_file_output"]
        log_folder = self.config.sections["logging"]["debuglogsdir"]
        timestamp_format = self.config.sections["logging"]["log_timestamp"]

        log.set_log_to_file(should_log)
        log.set_folder(log_folder)
        log.set_timestamp_format(timestamp_format)


class UserAddr:

    def __init__(self, addr=None, behindfw=None, status=None):
        self.addr = addr
        self.behindfw = behindfw
        self.status = status
