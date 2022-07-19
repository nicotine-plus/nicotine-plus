# COPYRIGHT (C) 2020-2022 Nicotine+ Contributors
# COPYRIGHT (C) 2009-2011 Quinox <quinox@users.sf.net>
# COPYRIGHT (C) 2007-2009 Daelstorm <daelstorm@gmail.com>
# COPYRIGHT (C) 2003-2004 Hyriand <hyriand@thegraveyard.org>
# COPYRIGHT (C) 2001-2003 Alexander Kanavin
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

import socket
import struct
import zlib

from pynicotine.config import config
from pynicotine.logfacility import log

""" This module contains message classes, that networking and UI thread
exchange. Basically there are three types of messages: internal messages,
server messages and p2p messages (between clients). """


UINT_LIMIT = 4294967295

INT_UNPACK = struct.Struct("<i").unpack
UINT_UNPACK = struct.Struct("<I").unpack
UINT64_UNPACK = struct.Struct("<Q").unpack

INT_PACK = struct.Struct("<i").pack
UINT_PACK = struct.Struct("<I").pack
UINT64_PACK = struct.Struct("<Q").pack

SEARCH_TOKENS_ALLOWED = set()


def increment_token(token):
    """ Increment a token used by file search, transfer and connection requests """

    if token < 0 or token >= UINT_LIMIT:
        # Protocol messages use unsigned integers for tokens
        token = 0

    token += 1
    return token


"""
Constants
"""


class MessageType:
    INTERNAL = 0
    INIT = 1
    SERVER = 2
    PEER = 3
    FILE = 4
    DISTRIBUTED = 5


class ConnectionType:
    SERVER = 'S'
    PEER = 'P'
    FILE = 'F'
    DISTRIBUTED = 'D'


class UserStatus:
    OFFLINE = 0
    AWAY = 1
    ONLINE = 2


class TransferDirection:
    DOWNLOAD = 0
    UPLOAD = 1


class FileAttribute:
    BITRATE = 0
    DURATION = 1
    VBR = 2
    ENCODER = 3
    SAMPLE_RATE = 4
    BIT_DEPTH = 5


"""
Internal Messages
"""


class InternalMessage:
    msgtype = MessageType.INTERNAL


class ServerConnect(InternalMessage):
    """ NicotineCore sends this to make networking thread establish a server connection. """

    def __init__(self, addr=None, login=None):
        self.addr = addr
        self.login = login


class ServerDisconnect(InternalMessage):

    def __init__(self, manual_disconnect=False):
        self.manual_disconnect = manual_disconnect


class ServerTimeout(InternalMessage):
    pass


class InitPeerConn(InternalMessage):

    __slots__ = ("addr", "init")

    def __init__(self, addr=None, init=None):
        self.addr = addr
        self.init = init


class ConnClose(InternalMessage):

    def __init__(self, sock=None):
        self.sock = sock


class ConnCloseIP(InternalMessage):
    """ Sent by the main thread to the networking thread in order to close any connections
    using a certain IP address. """

    def __init__(self, addr=None):
        self.addr = addr


class SendNetworkMessage(InternalMessage):

    def __init__(self, user=None, message=None, addr=None):
        self.user = user
        self.message = message
        self.addr = addr


class ShowConnectionErrorMessage(InternalMessage):

    def __init__(self, user=None, msgs=None):
        self.user = user
        self.msgs = msgs


class MessageProgress(InternalMessage):
    """ Used to indicate progress of long transfers. """

    __slots__ = ("user", "msg_type", "position", "total")

    def __init__(self, user=None, msg_type=None, position=None, total=None):
        self.user = user
        self.msg_type = msg_type
        self.position = position
        self.total = total


class TransferTimeout(InternalMessage):

    __slots__ = ("transfer",)

    def __init__(self, transfer):
        self.transfer = transfer


class CheckDownloadQueue(InternalMessage):
    """ Sent from a timer to the main thread to indicate that stuck downloads
    should be checked. """


class CheckUploadQueue(InternalMessage):
    """ Sent from a timer to the main thread to indicate that the upload queue
    should be checked. """


class DownloadFile(InternalMessage):
    """ Sent by networking thread to indicate file transfer progress.
    Sent by UI to pass the file object to write. """

    __slots__ = ("sock", "file", "leftbytes")

    def __init__(self, sock=None, file=None, leftbytes=None):
        self.sock = sock
        self.file = file
        self.leftbytes = leftbytes


class UploadFile(InternalMessage):

    __slots__ = ("sock", "file", "size", "sentbytes", "offset")

    def __init__(self, sock=None, file=None, size=None, sentbytes=0, offset=None):
        self.sock = sock
        self.file = file
        self.size = size
        self.sentbytes = sentbytes
        self.offset = offset


class DownloadFileError(InternalMessage):
    """ Sent by networking thread to indicate that a file error occurred during
    filetransfer. """

    __slots__ = ("sock", "file", "error")

    def __init__(self, sock=None, file=None, error=None):
        self.sock = sock
        self.file = file
        self.error = error


class UploadFileError(DownloadFileError):
    pass


class DownloadConnClose(InternalMessage):
    """ Sent by networking thread to indicate a file transfer connection has been closed """

    __slots__ = ("sock",)

    def __init__(self, sock=None):
        self.sock = sock


class UploadConnClose(DownloadConnClose):
    pass


class SetUploadLimit(InternalMessage):
    """ Sent by the GUI thread to indicate changes in bandwidth shaping rules"""

    def __init__(self, uselimit, limit, limitby):
        self.uselimit = uselimit
        self.limit = limit
        self.limitby = limitby


class SetDownloadLimit(InternalMessage):
    """ Sent by the GUI thread to indicate changes in bandwidth shaping rules"""

    def __init__(self, limit):
        self.limit = limit


class SetConnectionStats(InternalMessage):
    """ Sent by networking thread to update the number of current
    connections shown in the GUI. """

    __slots__ = ("total_conns", "download_conns", "download_bandwidth", "upload_conns", "upload_bandwidth")

    def __init__(self, total_conns=0, download_conns=0, download_bandwidth=0, upload_conns=0, upload_bandwidth=0):
        self.total_conns = total_conns
        self.download_conns = download_conns
        self.download_bandwidth = download_bandwidth
        self.upload_conns = upload_conns
        self.upload_bandwidth = upload_bandwidth


class SlskMessage:
    """ This is a parent class for all protocol messages. """

    @staticmethod
    def pack_bytes(content):
        return UINT_PACK(len(content)) + content

    @staticmethod
    def pack_string(content, latin1=False):

        if latin1:
            try:
                # Try to encode in latin-1 first for older clients (Soulseek NS)
                encoded = bytes(content, "latin-1")

            except Exception:
                encoded = bytes(content, "utf-8", "replace")

        else:
            encoded = bytes(content, "utf-8", "replace")

        return UINT_PACK(len(encoded)) + encoded

    @staticmethod
    def pack_bool(content):
        return bytes([1]) if content else bytes([0])

    @staticmethod
    def pack_uint8(content):
        return bytes([content])

    @staticmethod
    def pack_int32(content):
        return INT_PACK(content)

    @staticmethod
    def pack_uint32(content):
        return UINT_PACK(content)

    @staticmethod
    def pack_uint64(content):
        return UINT64_PACK(content)

    @staticmethod
    def unpack_bytes(message, start=0):

        length = UINT_UNPACK(message[start:start + 4])[0]
        content = message[start + 4:start + length + 4]

        return start + 4 + length, content

    def make_network_message(self):
        """ Returns binary array, that can be sent over the network"""

        log.add_debug("Empty message made, class %s", self.__class__)
        return b""

    @staticmethod
    def unpack_string(message, start=0):

        length = UINT_UNPACK(message[start:start + 4])[0]
        string = message[start + 4:start + length + 4]

        try:
            string = str(string, "utf-8")
        except Exception:
            # Older clients (Soulseek NS)

            try:
                string = str(string, "latin-1")
            except Exception as error:
                log.add_debug("Error trying to decode string '%s': %s", (string, error))

        return start + 4 + length, string

    @staticmethod
    def unpack_bool(message, start=0):
        return start + 1, bool(message[start])

    @staticmethod
    def unpack_ip(message, start=0):
        return start + 4, socket.inet_ntoa(bytes(message[start:start + 4][::-1]))

    @staticmethod
    def unpack_uint8(message, start=0):
        return start + 1, message[start]

    @staticmethod
    def unpack_int32(message, start=0):
        return start + 4, INT_UNPACK(message[start:start + 4])[0]

    @staticmethod
    def unpack_uint32(message, start=0):
        return start + 4, UINT_UNPACK(message[start:start + 4])[0]

    @staticmethod
    def unpack_uint64(message, start=0):
        return start + 8, UINT64_UNPACK(message[start:start + 8])[0]

    def parse_network_message(self, _message):
        """ Extracts information from the message and sets up fields
        in an object"""

        log.add_debug("Can't parse incoming messages, class %s", self.__class__)

    def debug(self, message=None):
        from pynicotine.utils import debug
        debug(type(self).__name__, self.__dict__, repr(message))


"""
Server Messages
"""


class ServerMessage(SlskMessage):
    msgtype = MessageType.SERVER


class Login(ServerMessage):
    """ Server code: 1 """
    """ We send this to the server right after the connection has been
    established. Server responds with the greeting message. """

    def __init__(self, username=None, passwd=None, version=None, minorversion=None):
        self.username = username
        self.passwd = passwd
        self.version = version
        self.minorversion = minorversion
        self.success = None
        self.reason = None
        self.banner = None
        self.ip_address = None
        self.checksum = None

    def make_network_message(self):
        from hashlib import md5

        msg = bytearray()
        msg.extend(self.pack_string(self.username))
        msg.extend(self.pack_string(self.passwd))
        msg.extend(self.pack_uint32(self.version))

        payload = self.username + self.passwd
        md5hash = md5(payload.encode()).hexdigest()
        msg.extend(self.pack_string(md5hash))

        msg.extend(self.pack_uint32(self.minorversion))

        return msg

    def parse_network_message(self, message):
        pos, self.success = self.unpack_bool(message)

        if not self.success:
            pos, self.reason = self.unpack_string(message, pos)
        else:
            pos, self.banner = self.unpack_string(message, pos)

        if not message[pos:]:
            return

        try:
            pos, self.ip_address = self.unpack_ip(message, pos)

        except Exception as error:
            log.add_debug("Error unpacking IP address: %s", error)

        # MD5 hexdigest of the password you sent
        if len(message[pos:]) >= 4:
            pos, self.checksum = self.unpack_string(message, pos)


class SetWaitPort(ServerMessage):
    """ Server code: 2 """
    """ We send this to the server to indicate the port number that we
    listen on (2234 by default). """

    def __init__(self, port=None):
        self.port = port

    def make_network_message(self):
        return self.pack_uint32(self.port)


class GetPeerAddress(ServerMessage):
    """ Server code: 3 """
    """ We send this to the server to ask for a peer's address
    (IP address and port), given the peer's username. """

    def __init__(self, user=None):
        self.user = user
        self.ip_address = None
        self.port = None

    def make_network_message(self):
        return self.pack_string(self.user)

    def parse_network_message(self, message):
        pos, self.user = self.unpack_string(message)
        pos, self.ip_address = self.unpack_ip(message, pos)
        pos, self.port = self.unpack_uint32(message, pos)


class AddUser(ServerMessage):
    """ Server code: 5 """
    """ Used to be kept updated about a user's stats. When a user's
    stats have changed, the server sends a GetUserStats response message
    with the new user stats. """

    def __init__(self, user=None):
        self.user = user
        self.userexists = None
        self.status = None
        self.avgspeed = None
        self.uploadnum = None
        self.files = None
        self.dirs = None
        self.country = None

    def make_network_message(self):
        return self.pack_string(self.user)

    def parse_network_message(self, message):
        pos, self.user = self.unpack_string(message)
        pos, self.userexists = self.unpack_bool(message, pos)

        if not message[pos:]:
            # User does not exist
            return

        pos, self.status = self.unpack_uint32(message, pos)
        pos, self.avgspeed = self.unpack_uint32(message, pos)
        pos, self.uploadnum = self.unpack_uint64(message, pos)

        pos, self.files = self.unpack_uint32(message, pos)
        pos, self.dirs = self.unpack_uint32(message, pos)

        if not message[pos:]:
            # User is offline
            return

        pos, self.country = self.unpack_string(message, pos)


class RemoveUser(ServerMessage):
    """ Server code: 6 """
    """ Used when we no longer want to be kept updated about a
    user's stats. """

    def __init__(self, user=None):
        self.user = user

    def make_network_message(self):
        return self.pack_string(self.user)


class GetUserStatus(ServerMessage):
    """ Server code: 7 """
    """ The server tells us if a user has gone away or has returned. """

    def __init__(self, user=None):
        self.user = user
        self.status = None
        self.privileged = None

    def make_network_message(self):
        return self.pack_string(self.user)

    def parse_network_message(self, message):
        pos, self.user = self.unpack_string(message)
        pos, self.status = self.unpack_uint32(message, pos)

        # Soulfind support
        if message[pos:]:
            pos, self.privileged = self.unpack_bool(message, pos)


class SayChatroom(ServerMessage):
    """ Server code: 13 """
    """ Either we want to say something in the chatroom, or someone else did. """

    def __init__(self, room=None, msg=None):
        self.room = room
        self.msg = msg
        self.user = None

    def make_network_message(self):
        msg = bytearray()
        msg.extend(self.pack_string(self.room))
        msg.extend(self.pack_string(self.msg))

        return msg

    def parse_network_message(self, message):
        pos, self.room = self.unpack_string(message)
        pos, self.user = self.unpack_string(message, pos)
        pos, self.msg = self.unpack_string(message, pos)


class UserData:
    """ When we join a room, the server sends us a bunch of these for each user. """

    __slots__ = ("username", "status", "avgspeed", "uploadnum", "files", "dirs", "slotsfull", "country")

    def __init__(self, username=None, status=None, avgspeed=None, uploadnum=None, files=None, dirs=None,
                 slotsfull=None, country=None):
        self.username = username
        self.status = status
        self.avgspeed = avgspeed
        self.uploadnum = uploadnum
        self.files = files
        self.dirs = dirs
        self.slotsfull = slotsfull
        self.country = country


class JoinRoom(ServerMessage):
    """ Server code: 14 """
    """ We send this message to the server when we want to join a room. If the
    room doesn't exist, it is created.

    Server responds with this message when we join a room. Contains users list
    with data on everyone. """

    def __init__(self, room=None, private=None):
        self.room = room
        self.private = private
        self.owner = None
        self.users = []
        self.operators = []

    def make_network_message(self):
        msg = bytearray()
        msg.extend(self.pack_string(self.room))
        msg.extend(self.pack_uint32(1 if self.private else 0))

        return msg

    def parse_network_message(self, message):
        pos, self.room = self.unpack_string(message)
        pos, self.users = self.parse_users(message, pos)

        if message[pos:]:
            self.private = True
            pos, self.owner = self.unpack_string(message, pos)

        if message[pos:] and self.private:
            pos, numops = self.unpack_uint32(message, pos)

            for _ in range(numops):
                pos, operator = self.unpack_string(message, pos)

                self.operators.append(operator)

    def parse_users(self, message, pos):
        pos, numusers = self.unpack_uint32(message, pos)

        users = []
        for i in range(numusers):
            users.append(UserData())
            pos, users[i].username = self.unpack_string(message, pos)

        pos, statuslen = self.unpack_uint32(message, pos)
        for i in range(statuslen):
            pos, users[i].status = self.unpack_uint32(message, pos)

        pos, statslen = self.unpack_uint32(message, pos)
        for i in range(statslen):
            pos, users[i].avgspeed = self.unpack_uint32(message, pos)
            pos, users[i].uploadnum = self.unpack_uint64(message, pos)
            pos, users[i].files = self.unpack_uint32(message, pos)
            pos, users[i].dirs = self.unpack_uint32(message, pos)

        pos, slotslen = self.unpack_uint32(message, pos)
        for i in range(slotslen):
            pos, users[i].slotsfull = self.unpack_uint32(message, pos)

        if message[pos:]:
            pos, countrylen = self.unpack_uint32(message, pos)
            for i in range(countrylen):
                pos, users[i].country = self.unpack_string(message, pos)

        return pos, users


class LeaveRoom(ServerMessage):
    """ Server code: 15 """
    """ We send this to the server when we want to leave a room. """

    def __init__(self, room=None):
        self.room = room

    def make_network_message(self):
        return self.pack_string(self.room)

    def parse_network_message(self, message):
        _pos, self.room = self.unpack_string(message)


class UserJoinedRoom(ServerMessage):
    """ Server code: 16 """
    """ The server tells us someone has just joined a room we're in. """

    def __init__(self):
        self.room = None
        self.userdata = None

    def parse_network_message(self, message):
        pos, self.room = self.unpack_string(message)

        self.userdata = UserData()
        pos, self.userdata.username = self.unpack_string(message, pos)
        pos, self.userdata.status = self.unpack_uint32(message, pos)
        pos, self.userdata.avgspeed = self.unpack_uint32(message, pos)
        pos, self.userdata.uploadnum = self.unpack_uint64(message, pos)
        pos, self.userdata.files = self.unpack_uint32(message, pos)
        pos, self.userdata.dirs = self.unpack_uint32(message, pos)
        pos, self.userdata.slotsfull = self.unpack_uint32(message, pos)

        # Soulfind support
        if message[pos:]:
            pos, self.userdata.country = self.unpack_string(message, pos)


class UserLeftRoom(ServerMessage):
    """ Server code: 17 """
    """ The server tells us someone has just left a room we're in. """

    def __init__(self):
        self.room = None
        self.username = None

    def parse_network_message(self, message):
        pos, self.room = self.unpack_string(message)
        pos, self.username = self.unpack_string(message, pos)


class ConnectToPeer(ServerMessage):
    """ Server code: 18 """
    """ Either we ask server to tell someone else we want to establish a
    connection with them, or server tells us someone wants to connect with us.
    Used when the side that wants a connection can't establish it, and tries
    to go the other way around (direct connection has failed).
    """

    def __init__(self, token=None, user=None, conn_type=None):
        self.token = token
        self.user = user
        self.conn_type = conn_type
        self.ip_address = None
        self.port = None
        self.privileged = None

    def make_network_message(self):
        msg = bytearray()
        msg.extend(self.pack_uint32(self.token))
        msg.extend(self.pack_string(self.user))
        msg.extend(self.pack_string(self.conn_type))

        return msg

    def parse_network_message(self, message):
        pos, self.user = self.unpack_string(message)
        pos, self.conn_type = self.unpack_string(message, pos)
        pos, self.ip_address = self.unpack_ip(message, pos)
        pos, self.port = self.unpack_uint32(message, pos)
        pos, self.token = self.unpack_uint32(message, pos)

        # Soulfind support
        if message[pos:]:
            pos, self.privileged = self.unpack_bool(message, pos)


class MessageUser(ServerMessage):
    """ Server code: 22 """
    """ Chat phrase sent to someone or received by us in private. """

    def __init__(self, user=None, msg=None):
        self.user = user
        self.msg = msg
        self.msgid = None
        self.timestamp = None
        self.newmessage = None

    def make_network_message(self):
        msg = bytearray()
        msg.extend(self.pack_string(self.user))
        msg.extend(self.pack_string(self.msg))

        return msg

    def parse_network_message(self, message):
        pos, self.msgid = self.unpack_uint32(message)
        pos, self.timestamp = self.unpack_uint32(message, pos)
        pos, self.user = self.unpack_string(message, pos)
        pos, self.msg = self.unpack_string(message, pos)

        if message[pos:]:
            pos, self.newmessage = self.unpack_bool(message, pos)
        else:
            self.newmessage = True


class MessageAcked(ServerMessage):
    """ Server code: 23 """
    """ We send this to the server to confirm that we received a private message.
    If we don't send it, the server will keep sending the chat phrase to us.
    """

    def __init__(self, msgid=None):
        self.msgid = msgid

    def make_network_message(self):
        return self.pack_uint32(self.msgid)


class FileSearchRoom(ServerMessage):
    """ Server code: 25 """
    """ We send this to the server when we search for something in a room. """
    """ OBSOLETE, use RoomSearch server message """

    def __init__(self, token=None, roomid=None, text=None):
        self.token = token
        self.roomid = roomid
        self.searchterm = text

    def make_network_message(self):
        msg = bytearray()
        msg.extend(self.pack_uint32(self.token))
        msg.extend(self.pack_uint32(self.roomid))
        msg.extend(self.pack_string(self.searchterm))

        return msg


class FileSearch(ServerMessage):
    """ Server code: 26 """
    """ We send this to the server when we search for something. Alternatively,
    the server sends this message outside the distributed network to tell us
    that someone is searching for something, currently used for UserSearch and
    RoomSearch requests.

    The token is a number generated by the client and is used to track the
    search results.
    """

    def __init__(self, token=None, text=None):
        self.token = token
        self.searchterm = text
        self.user = None

        if text:
            self.searchterm = ' '.join(x for x in text.split() if x != '-')

    def make_network_message(self):
        msg = bytearray()
        msg.extend(self.pack_uint32(self.token))
        msg.extend(self.pack_string(self.searchterm, latin1=True))

        return msg

    def parse_network_message(self, message):
        pos, self.user = self.unpack_string(message)
        pos, self.token = self.unpack_uint32(message, pos)
        pos, self.searchterm = self.unpack_string(message, pos)


class SetStatus(ServerMessage):
    """ Server code: 28 """
    """ We send our new status to the server. Status is a way to define whether
    we're available (online) or busy (away).

    1 = Away
    2 = Online
    """

    def __init__(self, status=None):
        self.status = status

    def make_network_message(self):
        return self.pack_int32(self.status)


class ServerPing(ServerMessage):
    """ Server code: 32 """
    """ We test if the server responds. """
    """ DEPRECATED """

    def make_network_message(self):
        return b""

    def parse_network_message(self, message):
        # Empty message
        pass


class SendConnectToken(ServerMessage):
    """ Server code: 33 """
    """ OBSOLETE, no longer used """

    def __init__(self, user, token):
        self.user = user
        self.token = token

    def make_network_message(self):
        msg = bytearray()
        msg.extend(self.pack_string(self.user))
        msg.extend(self.pack_uint32(self.token))

        return msg

    def parse_network_message(self, message):
        pos, self.user = self.unpack_string(message)
        pos, self.token = self.unpack_uint32(message, pos)


class SendDownloadSpeed(ServerMessage):
    """ Server code: 34 """
    """ We used to send this after a finished download to let the server update
    the speed statistics for a user. """
    """ OBSOLETE, use SendUploadSpeed server message """

    def __init__(self, user=None, speed=None):
        self.user = user
        self.speed = speed

    def make_network_message(self):
        msg = bytearray()
        msg.extend(self.pack_string(self.user))
        msg.extend(self.pack_uint32(self.speed))

        return msg


class SharedFoldersFiles(ServerMessage):
    """ Server code: 35 """
    """ We send this to server to indicate the number of folder and files
    that we share. """

    def __init__(self, folders=None, files=None):
        self.folders = folders
        self.files = files

    def make_network_message(self):
        msg = bytearray()
        msg.extend(self.pack_uint32(self.folders))
        msg.extend(self.pack_uint32(self.files))

        return msg


class GetUserStats(ServerMessage):
    """ Server code: 36 """
    """ The server sends this to indicate a change in a user's statistics,
    if we've requested to watch the user in AddUser previously. A user's
    stats can also be requested by sending a GetUserStats message to the
    server, but AddUser should be used instead. """

    def __init__(self, user=None):
        self.user = user
        self.avgspeed = None
        self.uploadnum = None
        self.files = None
        self.dirs = None

    def make_network_message(self):
        return self.pack_string(self.user)

    def parse_network_message(self, message):
        pos, self.user = self.unpack_string(message)
        pos, self.avgspeed = self.unpack_uint32(message, pos)
        pos, self.uploadnum = self.unpack_uint64(message, pos)
        pos, self.files = self.unpack_uint32(message, pos)
        pos, self.dirs = self.unpack_uint32(message, pos)


class QueuedDownloads(ServerMessage):
    """ Server code: 40 """
    """ The server sends this to indicate if someone has download slots available
    or not. """
    """ OBSOLETE, no longer sent by the server """

    def __init__(self):
        self.user = None
        self.slotsfull = None

    def parse_network_message(self, message):
        pos, self.user = self.unpack_string(message)
        pos, self.slotsfull = self.unpack_uint32(message, pos)


class Relogged(ServerMessage):
    """ Server code: 41 """
    """ The server sends this if someone else logged in under our nickname,
    and then disconnects us. """

    def parse_network_message(self, message):
        # Empty message
        pass


class UserSearch(ServerMessage):
    """ Server code: 42 """
    """ We send this to the server when we search a specific user's shares.
    The token is a number generated by the client and is used to track the
    search results. """

    def __init__(self, user=None, token=None, text=None):
        self.user = user
        self.token = token
        self.searchterm = text

    def make_network_message(self):
        msg = bytearray()
        msg.extend(self.pack_string(self.user))
        msg.extend(self.pack_uint32(self.token))
        msg.extend(self.pack_string(self.searchterm, latin1=True))

        return msg

    # Soulfind support, the official server sends a FileSearch message (code 26) instead
    def parse_network_message(self, message):
        pos, self.user = self.unpack_string(message)
        pos, self.token = self.unpack_uint32(message, pos)
        pos, self.searchterm = self.unpack_string(message, pos)


class AddThingILike(ServerMessage):
    """ Server code: 51 """
    """ We send this to the server when we add an item to our likes list. """
    """ DEPRECATED, used in Soulseek NS but not SoulseekQt """

    def __init__(self, thing=None):
        self.thing = thing

    def make_network_message(self):
        return self.pack_string(self.thing)


class RemoveThingILike(ServerMessage):
    """ Server code: 52 """
    """ We send this to the server when we remove an item from our likes list. """
    """ DEPRECATED, used in Soulseek NS but not SoulseekQt """

    def __init__(self, thing=None):
        self.thing = thing

    def make_network_message(self):
        return self.pack_string(self.thing)


class Recommendations(ServerMessage):
    """ Server code: 54 """
    """ The server sends us a list of personal recommendations and a number
    for each. """
    """ DEPRECATED, used in Soulseek NS but not SoulseekQt """

    def __init__(self):
        self.recommendations = []
        self.unrecommendations = []

    def make_network_message(self):
        return b""

    def parse_network_message(self, message):
        self.parse_recommendations(message)

    def parse_recommendations(self, message, pos=0):
        pos, num = self.unpack_uint32(message, pos)

        for _ in range(num):
            pos, key = self.unpack_string(message, pos)
            pos, rating = self.unpack_int32(message, pos)

            # The server also includes unrecommendations here for some reason, don't add them
            if rating >= 0:
                self.recommendations.append((key, rating))

        if not message[pos:]:
            return

        pos, num2 = self.unpack_uint32(message, pos)

        for _ in range(num2):
            pos, key = self.unpack_string(message, pos)
            pos, rating = self.unpack_int32(message, pos)

            # The server also includes recommendations here for some reason, don't add them
            if rating < 0:
                self.unrecommendations.append((key, rating))


class GlobalRecommendations(Recommendations):
    """ Server code: 56 """
    """ The server sends us a list of global recommendations and a number
    for each. """
    """ DEPRECATED, used in Soulseek NS but not SoulseekQt """


class UserInterests(ServerMessage):
    """ Server code: 57 """
    """ We ask the server for a user's liked and hated interests. The server
    responds with a list of interests. """
    """ DEPRECATED, used in Soulseek NS but not SoulseekQt """

    def __init__(self, user=None):
        self.user = user
        self.likes = []
        self.hates = []

    def make_network_message(self):
        return self.pack_string(self.user)

    def parse_network_message(self, message):
        pos, self.user = self.unpack_string(message)
        pos, likesnum = self.unpack_uint32(message, pos)

        for _ in range(likesnum):
            pos, key = self.unpack_string(message, pos)

            self.likes.append(key)

        pos, hatesnum = self.unpack_uint32(message, pos)

        for _ in range(hatesnum):
            pos, key = self.unpack_string(message, pos)

            self.hates.append(key)


class AdminCommand(ServerMessage):
    """ Server code: 58 """
    """ We send this to the server to run an admin command (e.g. to ban or
    silence a user) if we have admin status on the server. """
    """ OBSOLETE, no longer used since Soulseek stopped supporting third-party
    servers in 2002 """

    def __init__(self, command=None, command_args=None):
        self.command = command
        self.command_args = command_args

    def make_network_message(self):
        msg = bytearray()
        msg.extend(self.pack_string(self.command))
        msg.extend(self.pack_uint32(len(self.command_args)))

        for arg in self.command_args:
            msg.extend(self.pack_string(arg))

        return msg


class PlaceInLineResponse(ServerMessage):
    """ Server code: 60 """
    """ The server sends this to indicate change in place in queue while we're
    waiting for files from another peer. """
    """ OBSOLETE, use PlaceInQueue peer message """

    def __init__(self, user=None, token=None, place=None):
        self.token = token
        self.user = user
        self.place = place

    def make_network_message(self):
        msg = bytearray()
        msg.extend(self.pack_string(self.user))
        msg.extend(self.pack_uint32(self.token))
        msg.extend(self.pack_uint32(self.place))

        return msg

    def parse_network_message(self, message):
        pos, self.user = self.unpack_string(message)
        pos, self.token = self.unpack_uint32(message, pos)
        pos, self.place = self.unpack_uint32(message, pos)


class RoomAdded(ServerMessage):
    """ Server code: 62 """
    """ The server tells us a new room has been added. """
    """ OBSOLETE, no longer sent by the server """

    def __init__(self):
        self.room = None

    def parse_network_message(self, message):
        _pos, self.room = self.unpack_string(message)


class RoomRemoved(ServerMessage):
    """ Server code: 63 """
    """ The server tells us a room has been removed. """
    """ OBSOLETE, no longer sent by the server """

    def __init__(self):
        self.room = None

    def parse_network_message(self, message):
        _pos, self.room = self.unpack_string(message)


class RoomList(ServerMessage):
    """ Server code: 64 """
    """ The server tells us a list of rooms and the number of users in
    them. When connecting to the server, the server only sends us rooms
    with at least 5 users. A few select rooms are also excluded, such as
    nicotine and The Lobby. Requesting the room list yields a response
    containing the missing rooms. """

    def __init__(self):
        self.rooms = []
        self.ownedprivaterooms = []
        self.otherprivaterooms = []

    def make_network_message(self):
        return b""

    def parse_network_message(self, message):
        pos, numrooms = self.unpack_uint32(message)

        for i in range(numrooms):
            pos, room = self.unpack_string(message, pos)

            self.rooms.append([room, None])

        pos, numusers = self.unpack_uint32(message, pos)

        for i in range(numusers):
            pos, usercount = self.unpack_uint32(message, pos)

            self.rooms[i][1] = usercount

        if not message[pos:]:
            return

        pos, self.ownedprivaterooms = self.parse_rooms(message, pos)
        pos, self.otherprivaterooms = self.parse_rooms(message, pos)

    def parse_rooms(self, message, pos):
        pos, numrooms = self.unpack_uint32(message, pos)

        rooms = []
        for i in range(numrooms):
            pos, room = self.unpack_string(message, pos)

            rooms.append([room, None])

        pos, numusers = self.unpack_uint32(message, pos)

        for i in range(numusers):
            pos, usercount = self.unpack_uint32(message, pos)

            rooms[i][1] = usercount

        return pos, rooms


class ExactFileSearch(ServerMessage):
    """ Server code: 65 """
    """ We send this to search for an exact file name and folder,
    to find other sources. """
    """ OBSOLETE, no results even with official client """

    def __init__(self, token=None, file=None, folder=None, size=None, checksum=None):
        self.token = token
        self.file = file
        self.folder = folder
        self.size = size
        self.checksum = checksum
        self.user = None

    def make_network_message(self):
        msg = bytearray()
        msg.extend(self.pack_uint32(self.token))
        msg.extend(self.pack_string(self.file))
        msg.extend(self.pack_string(self.folder))
        msg.extend(self.pack_uint64(self.size))
        msg.extend(self.pack_uint32(self.checksum))

        return msg

    def parse_network_message(self, message):
        pos, self.user = self.unpack_string(message)
        pos, self.token = self.unpack_uint32(message, pos)
        pos, self.file = self.unpack_string(message, pos)
        pos, self.folder = self.unpack_string(message, pos)
        pos, self.size = self.unpack_uint64(message, pos)
        pos, self.checksum = self.unpack_uint32(message, pos)


class AdminMessage(ServerMessage):
    """ Server code: 66 """
    """ A global message from the server admin has arrived. """

    def __init__(self):
        self.msg = None

    def parse_network_message(self, message):
        _pos, self.msg = self.unpack_string(message)


class GlobalUserList(ServerMessage):
    """ Server code: 67 """
    """ We send this to get a global list of all users online. """
    """ OBSOLETE, no longer used """

    def __init__(self):
        self.users = None

    def make_network_message(self):
        return b""

    def parse_network_message(self, message):
        _pos, self.users = self.parse_users(message)

    def parse_users(self, message):
        pos, numusers = self.unpack_uint32(message)

        users = []
        for i in range(numusers):
            users.append(UserData())
            pos, users[i].username = self.unpack_string(message, pos)

        pos, statuslen = self.unpack_uint32(message, pos)
        for i in range(statuslen):
            pos, users[i].status = self.unpack_uint32(message, pos)

        pos, statslen = self.unpack_uint32(message, pos)
        for i in range(statslen):
            pos, users[i].avgspeed = self.unpack_uint32(message, pos)
            pos, users[i].uploadnum = self.unpack_uint64(message, pos)
            pos, users[i].files = self.unpack_uint32(message, pos)
            pos, users[i].dirs = self.unpack_uint32(message, pos)

        pos, slotslen = self.unpack_uint32(message, pos)
        for i in range(slotslen):
            pos, users[i].slotsfull = self.unpack_uint32(message, pos)

        if message[pos:]:
            pos, countrylen = self.unpack_uint32(message, pos)
            for i in range(countrylen):
                pos, users[i].country = self.unpack_string(message, pos)

        return pos, users


class TunneledMessage(ServerMessage):
    """ Server code: 68 """
    """ Server message for tunneling a chat message. """
    """ OBSOLETE, no longer used """

    def __init__(self, user=None, token=None, code=None, msg=None):
        self.user = user
        self.token = token
        self.code = code
        self.msg = msg
        self.addr = None

    def make_network_message(self):
        msg = bytearray()
        msg.extend(self.pack_string(self.user))
        msg.extend(self.pack_uint32(self.token))
        msg.extend(self.pack_uint32(self.code))
        msg.extend(self.pack_string(self.msg))

        return msg

    def parse_network_message(self, message):
        pos, self.user = self.unpack_string(message)
        pos, self.code = self.unpack_uint32(message, pos)
        pos, self.token = self.unpack_uint32(message, pos)

        pos, ip_address = self.unpack_ip(message, pos)
        pos, port = self.unpack_uint32(message, pos)
        self.addr = (ip_address, port)

        pos, self.msg = self.unpack_string(message, pos)


class PrivilegedUsers(ServerMessage):
    """ Server code: 69 """
    """ The server sends us a list of privileged users, a.k.a. users who
    have donated. """

    def __init__(self):
        self.users = []

    def parse_network_message(self, message):
        pos, numusers = self.unpack_uint32(message)

        for _ in range(numusers):
            pos, user = self.unpack_string(message, pos)

            self.users.append(user)


class HaveNoParent(ServerMessage):
    """ Server code: 71 """
    """ We inform the server if we have a distributed parent or not.
    If not, the server eventually sends us a PossibleParents message with a
    list of 10 possible parents to connect to. """

    def __init__(self, noparent=None):
        self.noparent = noparent

    def make_network_message(self):
        return self.pack_bool(self.noparent)


class SearchParent(ServerMessage):
    """ Server code: 73 """
    """ We send the IP address of our parent to the server. """
    """ DEPRECATED, sent by Soulseek NS but not SoulseekQt """

    def __init__(self, parentip=None):
        self.parentip = parentip

    @staticmethod
    def strunreverse(string):
        strlist = string.split(".")
        strlist.reverse()
        return '.'.join(strlist)

    def make_network_message(self):
        return self.pack_uint32(socket.inet_aton(self.strunreverse(self.parentip)))


class ParentMinSpeed(ServerMessage):
    """ Server code: 83 """
    """ The server informs us about the minimum upload speed required to become
    a parent in the distributed network. """

    def __init__(self):
        self.speed = None

    def parse_network_message(self, message):
        _pos, self.speed = self.unpack_uint32(message)


class ParentSpeedRatio(ServerMessage):
    """ Server code: 84 """
    """ The server sends us a speed ratio determining the number of children we
    can have in the distributed network. The maximum number of children is our
    upload speed divided by the speed ratio. """

    def __init__(self):
        self.ratio = None

    def parse_network_message(self, message):
        _pos, self.ratio = self.unpack_uint32(message)


class ParentInactivityTimeout(ServerMessage):
    """ Server code: 86 """
    """ OBSOLETE, no longer sent by the server """

    def __init__(self):
        self.seconds = None

    def parse_network_message(self, message):
        _pos, self.seconds = self.unpack_uint32(message)


class SearchInactivityTimeout(ServerMessage):
    """ Server code: 87 """
    """ OBSOLETE, no longer sent by the server """

    def __init__(self):
        self.seconds = None

    def parse_network_message(self, message):
        _pos, self.seconds = self.unpack_uint32(message)


class MinParentsInCache(ServerMessage):
    """ Server code: 88 """
    """ OBSOLETE, no longer sent by the server """

    def __init__(self):
        self.num = None

    def parse_network_message(self, message):
        _pos, self.num = self.unpack_uint32(message)


class DistribAliveInterval(ServerMessage):
    """ Server code: 90 """
    """ OBSOLETE, no longer sent by the server """

    def __init__(self):
        self.seconds = None

    def parse_network_message(self, message):
        _pos, self.seconds = self.unpack_uint32(message)


class AddToPrivileged(ServerMessage):
    """ Server code: 91 """
    """ The server sends us the username of a new privileged user, which we
    add to our list of global privileged users. """
    """ OBSOLETE, no longer sent by the server """

    def __init__(self):
        self.user = None

    def parse_network_message(self, message):
        _pos, self.user = self.unpack_string(message)


class CheckPrivileges(ServerMessage):
    """ Server code: 92 """
    """ We ask the server how much time we have left of our privileges.
    The server responds with the remaining time, in seconds. """

    def __init__(self):
        self.seconds = None

    def make_network_message(self):
        return b""

    def parse_network_message(self, message):
        _pos, self.seconds = self.unpack_uint32(message)


class EmbeddedMessage(ServerMessage):
    """ Server code: 93 """
    """ The server sends us an embedded distributed message. The only type
    of distributed message sent at present is DistribSearch (distributed code 3).
    If we receive such a message, we are a branch root in the distributed network,
    and we distribute the embedded message (not the unpacked distributed message)
    to our child peers. """

    __slots__ = ("distrib_code", "distrib_message")

    def __init__(self):
        self.distrib_code = None
        self.distrib_message = None

    def parse_network_message(self, message):
        pos, self.distrib_code = self.unpack_uint8(message)
        self.distrib_message = message[pos:]


class AcceptChildren(ServerMessage):
    """ Server code: 100 """
    """ We tell the server if we want to accept child nodes. """

    def __init__(self, enabled=None):
        self.enabled = enabled

    def make_network_message(self):
        return self.pack_bool(self.enabled)


class PossibleParents(ServerMessage):
    """ Server code: 102 """
    """ The server send us a list of 10 possible distributed parents to connect to.
    This message is sent to us at regular intervals until we tell the server we don't
    need more possible parents, through a HaveNoParent message. """

    def __init__(self):
        self.list = {}

    def parse_network_message(self, message):
        pos, num = self.unpack_uint32(message)

        for _ in range(num):
            pos, username = self.unpack_string(message, pos)
            pos, ip_address = self.unpack_ip(message, pos)
            pos, port = self.unpack_uint32(message, pos)

            self.list[username] = (ip_address, port)


class WishlistSearch(FileSearch):
    """ Server code: 103 """
    """ We send the server one of our wishlist search queries at each interval. """


class WishlistInterval(ServerMessage):
    """ Server code: 104 """
    """ The server tells us the wishlist search interval. """

    def __init__(self):
        self.seconds = None

    def parse_network_message(self, message):
        _pos, self.seconds = self.unpack_uint32(message)


class SimilarUsers(ServerMessage):
    """ Server code: 110 """
    """ The server sends us a list of similar users related to our interests. """
    """ DEPRECATED, used in Soulseek NS but not SoulseekQt """

    def __init__(self):
        self.users = {}

    def make_network_message(self):
        return b""

    def parse_network_message(self, message):
        pos, num = self.unpack_uint32(message)

        for _ in range(num):
            pos, user = self.unpack_string(message, pos)
            pos, rating = self.unpack_uint32(message, pos)

            self.users[user] = rating


class ItemRecommendations(Recommendations):
    """ Server code: 111 """
    """ The server sends us a list of recommendations related to a specific
    item, which is usually present in the like/dislike list or an existing
    recommendation list. """
    """ DEPRECATED, used in Soulseek NS but not SoulseekQt """

    def __init__(self, thing=None):
        super().__init__()
        self.thing = thing

    def make_network_message(self):
        return self.pack_string(self.thing)

    def parse_network_message(self, message):
        pos, self.thing = self.unpack_string(message)
        self.parse_recommendations(message, pos)


class ItemSimilarUsers(ServerMessage):
    """ Server code: 112 """
    """ The server sends us a list of similar users related to a specific item,
    which is usually present in the like/dislike list or recommendation list. """
    """ DEPRECATED, used in Soulseek NS but not SoulseekQt """

    def __init__(self, thing=None):
        self.thing = thing
        self.users = []

    def make_network_message(self):
        return self.pack_string(self.thing)

    def parse_network_message(self, message):
        pos, self.thing = self.unpack_string(message)
        pos, num = self.unpack_uint32(message, pos)

        for _ in range(num):
            pos, user = self.unpack_string(message, pos)
            self.users.append(user)


class RoomTickerState(ServerMessage):
    """ Server code: 113 """
    """ The server returns a list of tickers in a chat room.

    Tickers are customizable, user-specific messages that appear on
    chat room walls. """

    def __init__(self):
        self.room = None
        self.user = None
        self.msgs = []

    def parse_network_message(self, message):
        pos, self.room = self.unpack_string(message)
        pos, num = self.unpack_uint32(message, pos)

        for _ in range(num):
            pos, user = self.unpack_string(message, pos)
            pos, msg = self.unpack_string(message, pos)

            self.msgs.append((user, msg))


class RoomTickerAdd(ServerMessage):
    """ Server code: 114 """
    """ The server sends us a new ticker that was added to a chat room.

    Tickers are customizable, user-specific messages that appear on
    chat room walls. """

    def __init__(self):
        self.room = None
        self.user = None
        self.msg = None

    def parse_network_message(self, message):
        pos, self.room = self.unpack_string(message)
        pos, self.user = self.unpack_string(message, pos)
        pos, self.msg = self.unpack_string(message, pos)


class RoomTickerRemove(ServerMessage):
    """ Server code: 115 """
    """ The server informs us that a ticker was removed from a chat room.

    Tickers are customizable, user-specific messages that appear on
    chat room walls. """

    def __init__(self):
        self.room = None
        self.user = None

    def parse_network_message(self, message):
        pos, self.room = self.unpack_string(message)
        pos, self.user = self.unpack_string(message, pos)


class RoomTickerSet(ServerMessage):
    """ Server code: 116 """
    """ We send this to the server when we change our own ticker in
    a chat room. Sending an empty ticker string removes any existing
    ticker in the room.

    Tickers are customizable, user-specific messages that appear on
    chat room walls. """

    def __init__(self, room=None, msg=""):
        self.room = room
        self.msg = msg

    def make_network_message(self):
        msg = bytearray()
        msg.extend(self.pack_string(self.room))
        msg.extend(self.pack_string(self.msg))

        return msg


class AddThingIHate(AddThingILike):
    """ Server code: 117 """
    """ We send this to the server when we add an item to our hate list. """
    """ DEPRECATED, used in Soulseek NS but not SoulseekQt """


class RemoveThingIHate(RemoveThingILike):
    """ Server code: 118 """
    """ We send this to the server when we remove an item from our hate list. """
    """ DEPRECATED, used in Soulseek NS but not SoulseekQt """


class RoomSearch(ServerMessage):
    """ Server code: 120 """
    """ We send this to the server to search files shared by users who have
    joined a specific chat room. The token is a number generated by the client
    and is used to track the search results. """

    def __init__(self, room=None, token=None, text=""):
        self.room = room
        self.token = token
        self.searchterm = ' '.join([x for x in text.split() if x != '-'])
        self.user = None

    def make_network_message(self):
        msg = bytearray()
        msg.extend(self.pack_string(self.room))
        msg.extend(self.pack_uint32(self.token))
        msg.extend(self.pack_string(self.searchterm, latin1=True))

        return msg

    # Soulfind support, the official server sends a FileSearch message (code 26) instead
    def parse_network_message(self, message):
        pos, self.user = self.unpack_string(message)
        pos, self.token = self.unpack_uint32(message, pos)
        pos, self.searchterm = self.unpack_string(message, pos)


class SendUploadSpeed(ServerMessage):
    """ Server code: 121 """
    """ We send this after a finished upload to let the server update the speed
    statistics for ourselves. """

    def __init__(self, speed=None):
        self.speed = speed

    def make_network_message(self):
        return self.pack_uint32(self.speed)


class UserPrivileged(ServerMessage):
    """ Server code: 122 """
    """ We ask the server whether a user is privileged or not. """
    """ DEPRECATED, use AddUser and GetUserStatus server messages """

    def __init__(self, user=None):
        self.user = user
        self.privileged = None

    def make_network_message(self):
        return self.pack_string(self.user)

    def parse_network_message(self, message):
        pos, self.user = self.unpack_string(message)
        pos, self.privileged = self.unpack_bool(message, pos)


class GivePrivileges(ServerMessage):
    """ Server code: 123 """
    """ We give (part of) our privileges, specified in days, to another
    user on the network. """

    def __init__(self, user=None, days=None):
        self.user = user
        self.days = days

    def make_network_message(self):
        msg = bytearray()
        msg.extend(self.pack_string(self.user))
        msg.extend(self.pack_uint32(self.days))

        return msg


class NotifyPrivileges(ServerMessage):
    """ Server code: 124 """
    """ DEPRECATED, sent by Soulseek NS but not SoulseekQt """

    def __init__(self, token=None, user=None):
        self.token = token
        self.user = user

    def parse_network_message(self, message):
        pos, self.token = self.unpack_uint32(message)
        pos, self.user = self.unpack_string(message, pos)

    def make_network_message(self):
        msg = bytearray()
        msg.extend(self.pack_uint32(self.token))
        msg.extend(self.pack_string(self.user))

        return msg


class AckNotifyPrivileges(ServerMessage):
    """ Server code: 125 """
    """ DEPRECATED, no longer used """

    def __init__(self, token=None):
        self.token = token

    def parse_network_message(self, message):
        _pos, self.token = self.unpack_uint32(message)

    def make_network_message(self):
        return self.pack_uint32(self.token)


class BranchLevel(ServerMessage):
    """ Server code: 126 """
    """ We tell the server what our position is in our branch (xth generation)
    on the distributed network. """

    def __init__(self, value=None):
        self.value = value

    def make_network_message(self):
        return self.pack_uint32(self.value)


class BranchRoot(ServerMessage):
    """ Server code: 127 """
    """ We tell the server the username of the root of the branch we’re in on
    the distributed network. """

    def __init__(self, user=None):
        self.user = user

    def make_network_message(self):
        return self.pack_string(self.user)


class ChildDepth(ServerMessage):
    """ Server code: 129 """
    """ We tell the server the maximum number of generation of children we
    have on the distributed network. """
    """ DEPRECATED, sent by Soulseek NS but not SoulseekQt """

    def __init__(self, value=None):
        self.value = value

    def make_network_message(self):
        return self.pack_uint32(self.value)


class ResetDistributed(ServerMessage):
    """ Server code: 130 """
    """ The server asks us to reset our distributed parent and children. """

    def parse_network_message(self, message):
        # Empty message
        pass


class PrivateRoomUsers(ServerMessage):
    """ Server code: 133 """
    """ The server sends us a list of room users that we can alter
    (add operator abilities / dismember). """

    def __init__(self):
        self.room = None
        self.numusers = None
        self.users = []

    def parse_network_message(self, message):
        pos, self.room = self.unpack_string(message)
        pos, self.numusers = self.unpack_uint32(message, pos)

        for _ in range(self.numusers):
            pos, user = self.unpack_string(message, pos)

            self.users.append(user)


class PrivateRoomAddUser(ServerMessage):
    """ Server code: 134 """
    """ We send this to inform the server that we've added a user to a private room. """

    def __init__(self, room=None, user=None):
        self.room = room
        self.user = user

    def make_network_message(self):
        msg = bytearray()
        msg.extend(self.pack_string(self.room))
        msg.extend(self.pack_string(self.user))

        return msg

    def parse_network_message(self, message):
        pos, self.room = self.unpack_string(message)
        pos, self.user = self.unpack_string(message, pos)


class PrivateRoomRemoveUser(PrivateRoomAddUser):
    """ Server code: 135 """
    """ We send this to inform the server that we've removed a user from a private room. """


class PrivateRoomDismember(ServerMessage):
    """ Server code: 136 """
    """ We send this to the server to remove our own membership of a private room. """

    def __init__(self, room=None):
        self.room = room

    def make_network_message(self):
        return self.pack_string(self.room)


class PrivateRoomDisown(ServerMessage):
    """ Server code: 137 """
    """ We send this to the server to stop owning a private room. """

    def __init__(self, room=None):
        self.room = room

    def make_network_message(self):
        return self.pack_string(self.room)


class PrivateRoomSomething(ServerMessage):
    """ Server code: 138 """
    """ OBSOLETE, no longer used """

    def __init__(self, room=None):
        self.room = room

    def make_network_message(self):
        return self.pack_string(self.room)

    def parse_network_message(self, message):
        _pos, self.room = self.unpack_string(message)


class PrivateRoomAdded(ServerMessage):
    """ Server code: 139 """
    """ The server sends us this message when we are added to a private room. """

    def __init__(self, room=None):
        self.room = room

    def parse_network_message(self, message):
        _pos, self.room = self.unpack_string(message)


class PrivateRoomRemoved(PrivateRoomAdded):
    """ Server code: 140 """
    """ The server sends us this message when we are removed from a private room. """


class PrivateRoomToggle(ServerMessage):
    """ Server code: 141 """
    """ We send this when we want to enable or disable invitations to private rooms. """

    def __init__(self, enabled=None):
        self.enabled = enabled

    def make_network_message(self):
        return self.pack_bool(self.enabled)

    def parse_network_message(self, message):
        # When this is received, we store it in the config, and disable the appropriate menu item
        _pos, self.enabled = self.unpack_bool(message)


class ChangePassword(ServerMessage):
    """ Server code: 142 """
    """ We send this to the server to change our password. We receive a
    response if our password changes. """

    def __init__(self, password=None):
        self.password = password

    def make_network_message(self):
        return self.pack_string(self.password)

    def parse_network_message(self, message):
        _pos, self.password = self.unpack_string(message)


class PrivateRoomAddOperator(PrivateRoomAddUser):
    """ Server code: 143 """
    """ We send this to the server to add private room operator abilities to a user. """


class PrivateRoomRemoveOperator(PrivateRoomAddUser):
    """ Server code: 144 """
    """ We send this to the server to remove private room operator abilities from a user. """


class PrivateRoomOperatorAdded(ServerMessage):
    """ Server code: 145 """
    """ The server send us this message when we're given operator abilities
    in a private room. """

    def __init__(self, room=None):
        self.room = room

    def parse_network_message(self, message):
        _pos, self.room = self.unpack_string(message)


class PrivateRoomOperatorRemoved(ServerMessage):
    """ Server code: 146 """
    """ The server send us this message when our operator abilities are removed
    in a private room. """

    def __init__(self, room=None):
        self.room = room

    def make_network_message(self):
        return self.pack_string(self.room)

    def parse_network_message(self, message):
        _pos, self.room = self.unpack_string(message)


class PrivateRoomOwned(ServerMessage):
    """ Server code: 148 """
    """ The server sends us a list of operators in a specific room, that we can
    remove operator abilities from. """

    def __init__(self):
        self.room = None
        self.number = None
        self.operators = []

    def parse_network_message(self, message):
        pos, self.room = self.unpack_string(message)
        pos, self.number = self.unpack_uint32(message, pos)

        for _ in range(self.number):
            pos, user = self.unpack_string(message, pos)

            self.operators.append(user)


class MessageUsers(ServerMessage):
    """ Server code: 149 """
    """ Sends a broadcast private message to the given list of users. """

    def __init__(self, users=None, msg=None):
        self.users = users
        self.msg = msg

    def make_network_message(self):
        msg = bytearray()
        msg.extend(self.pack_uint32(len(self.users)))

        for user in self.users:
            msg.extend(self.pack_string(user))

        msg.extend(self.pack_string(self.msg))


class JoinPublicRoom(ServerMessage):
    """ Server code: 150 """
    """ We ask the server to send us messages from all public rooms, also
    known as public room feed. """
    """ DEPRECATED, used in Soulseek NS but not SoulseekQt """

    def make_network_message(self):
        return b""


class LeavePublicRoom(ServerMessage):
    """ Server code: 151 """
    """ We ask the server to stop sending us messages from all public rooms,
    also known as public room feed. """
    """ DEPRECATED, used in Soulseek NS but not SoulseekQt """

    def make_network_message(self):
        return b""


class PublicRoomMessage(ServerMessage):
    """ Server code: 152 """
    """ The server sends this when a new message has been written in the public
    room feed (every single line written in every public room). """
    """ DEPRECATED, used in Soulseek NS but not SoulseekQt """

    def __init__(self):
        self.room = None
        self.user = None
        self.msg = None

    def parse_network_message(self, message):
        pos, self.room = self.unpack_string(message)
        pos, self.user = self.unpack_string(message, pos)
        pos, self.msg = self.unpack_string(message, pos)


class RelatedSearch(ServerMessage):
    """ Server code: 153 """
    """ The server returns a list of related search terms for a search query. """
    """ OBSOLETE, server sends empty list as of 2018 """

    def __init__(self, query=None):
        self.query = query
        self.terms = []

    def make_network_message(self):
        return self.pack_string(self.query)

    def parse_network_message(self, message):
        pos, self.query = self.unpack_string(message)
        pos, num = self.unpack_uint32(message, pos)

        for _ in range(num):
            pos, term = self.unpack_string(message, pos)
            pos, score = self.unpack_uint32(message, pos)

            self.terms.append((term, score))


class CantConnectToPeer(ServerMessage):
    """ Server code: 1001 """
    """ We send this to say we can't connect to peer after it has asked us
    to connect. We receive this if we asked peer to connect and it can't do
    this. This message means a connection can't be established either way. """

    def __init__(self, token=None, user=None):
        self.token = token
        self.user = user

    def make_network_message(self):
        msg = bytearray()
        msg.extend(self.pack_uint32(self.token))
        msg.extend(self.pack_string(self.user))

        return msg

    def parse_network_message(self, message):
        _pos, self.token = self.unpack_uint32(message)


class CantCreateRoom(ServerMessage):
    """ Server code: 1003 """
    """ Server tells us a new room cannot be created. This message only seems
    to be sent if you try to create a room with the same name as an existing
    private room. In other cases, such as using a room name with leading or
    trailing spaces, only a private message containing an error message is sent. """

    def __init__(self):
        self.room = None

    def parse_network_message(self, message):
        _pos, self.room = self.unpack_string(message)


"""
Peer Init Messages
"""


class PeerInitMessage(SlskMessage):
    msgtype = MessageType.INIT


class PierceFireWall(PeerInitMessage):
    """ Peer init code: 0 """
    """ This message is sent in response to an indirect connection request
    from another user. If the message goes through to the user, the connection
    is ready. The token is taken from the ConnectToPeer server message. """

    def __init__(self, sock=None, token=None):
        self.sock = sock
        self.token = token

    def make_network_message(self):
        return self.pack_uint32(self.token)

    def parse_network_message(self, message):
        if message:
            # A token is not guaranteed to be sent (buggy client?)
            _pos, self.token = self.unpack_uint32(message)


class PeerInit(PeerInitMessage):
    """ Peer init code: 1 """
    """ This message is sent to initiate a direct connection to another
    peer. The token is apparently always 0 and ignored.

    Nicotine+ extends the PeerInit class to reuse and keep track of peer
    connections internally. """

    __slots__ = ("sock", "addr", "init_user", "target_user", "conn_type", "indirect", "token")

    def __init__(self, sock=None, addr=None, init_user=None, target_user=None, conn_type=None, indirect=False, token=0):
        self.sock = sock
        self.addr = addr
        self.init_user = init_user      # username of peer who initiated the message
        self.target_user = target_user  # username of peer we're connected to
        self.conn_type = conn_type
        self.indirect = indirect
        self.token = token
        self.outgoing_msgs = []

    def make_network_message(self):
        msg = bytearray()
        msg.extend(self.pack_string(self.init_user))
        msg.extend(self.pack_string(self.conn_type))
        msg.extend(self.pack_uint32(self.token))

        return msg

    def parse_network_message(self, message):
        pos, self.init_user = self.unpack_string(message)
        pos, self.conn_type = self.unpack_string(message, pos)

        if self.target_user is None:
            # The user we're connecting to initiated the connection. Set them as target user.
            self.target_user = self.init_user


"""
Peer Messages
"""


class PeerMessage(SlskMessage):

    msgtype = MessageType.PEER

    def parse_file_size(self, message, pos):

        if message[pos + 7] == 255:
            # Soulseek NS bug: >2 GiB files show up as ~16 EiB when unpacking the size
            # as uint64 (8 bytes), due to the first 4 bytes containing the size, and the
            # last 4 bytes containing garbage (a value of 4294967295 bytes, integer limit).
            # Only unpack the first 4 bytes to work around this issue.

            pos, size = self.unpack_uint32(message, pos)
            pos, _garbage = self.unpack_uint32(message, pos)

        else:
            # Everything looks fine, parse size as usual
            pos, size = self.unpack_uint64(message, pos)

        return pos, size


class GetSharedFileList(PeerMessage):
    """ Peer code: 4 """
    """ We send this to a peer to ask for a list of shared files. """

    def __init__(self, init=None):
        self.init = init

    def make_network_message(self):
        return b""

    def parse_network_message(self, message):
        # Empty message
        pass


class SharedFileList(PeerMessage):
    """ Peer code: 5 """
    """ A peer responds with a list of shared files when we've sent
    a GetSharedFileList. """

    def __init__(self, init=None, shares=None):
        self.init = init
        self.list = shares
        self.unknown = 0
        self.privatelist = []
        self.built = None

    def make_network_message(self):
        # Elaborate hack to save CPU
        # Store packed message contents in self.built, and use instead of repacking it
        if self.built is not None:
            return self.built

        msg = bytearray()
        msg_list = bytearray()

        if self.list is None:
            # DB is closed
            msg_list = self.pack_uint32(0)

        else:
            try:
                try:
                    msg_list.extend(self.pack_uint32(len(self.list)))

                except TypeError:
                    msg_list.extend(self.pack_uint32(len(list(self.list))))

                for key in self.list:
                    msg_list.extend(self.pack_string(key.replace('/', '\\')))
                    msg_list.extend(self.list[key])

            except Exception as error:
                msg_list = self.pack_uint32(0)
                log.add(_("Unable to read shares database. Please rescan your shares. Error: %s"), error)

        msg.extend(msg_list)

        # Unknown purpose, but official clients always send a value of 0
        msg.extend(self.pack_uint32(self.unknown))

        self.built = zlib.compress(msg)
        return self.built

    def parse_network_message(self, message):
        try:
            message = memoryview(zlib.decompress(message))
            self._parse_network_message(message)

        except Exception as error:
            log.add_debug("Exception during parsing %(area)s: %(exception)s",
                          {'area': 'SharedFileList', 'exception': error})
            self.list = []
            self.privatelist = []

    def _parse_result_list(self, message, pos=0):
        pos, ndir = self.unpack_uint32(message, pos)

        shares = []
        for _ in range(ndir):
            pos, directory = self.unpack_string(message, pos)
            directory = directory.replace('/', '\\')
            pos, nfiles = self.unpack_uint32(message, pos)

            files = []

            for _ in range(nfiles):
                pos, code = self.unpack_uint8(message, pos)
                pos, name = self.unpack_string(message, pos)
                pos, size = self.parse_file_size(message, pos)
                pos, ext = self.unpack_string(message, pos)
                pos, numattr = self.unpack_uint32(message, pos)

                attrs = {}

                for _ in range(numattr):
                    pos, attrnum = self.unpack_uint32(message, pos)
                    pos, attr = self.unpack_uint32(message, pos)
                    attrs[str(attrnum)] = attr

                files.append((code, name, size, ext, attrs))

            shares.append((directory, files))

        return pos, shares

    def _parse_network_message(self, message):
        pos, self.list = self._parse_result_list(message)

        if message[pos:]:
            pos, self.unknown = self.unpack_uint32(message, pos)

        if message[pos:]:
            pos, self.privatelist = self._parse_result_list(message, pos)


class FileSearchRequest(PeerMessage):
    """ Peer code: 8 """
    """ We send this to the peer when we search for a file.
    Alternatively, the peer sends this to tell us it is
    searching for a file. """
    """ OBSOLETE, use UserSearch server message """

    def __init__(self, init=None, token=None, text=None):
        self.init = init
        self.token = token
        self.text = text
        self.token = None
        self.searchterm = None

    def make_network_message(self):
        msg = bytearray()
        msg.extend(self.pack_uint32(self.token))
        msg.extend(self.pack_string(self.text))

        return msg

    def parse_network_message(self, message):
        pos, self.token = self.unpack_uint32(message)
        pos, self.searchterm = self.unpack_string(message, pos)


class FileSearchResult(PeerMessage):
    """ Peer code: 9 """
    """ A peer sends this message when it has a file search match. The token is
    taken from original FileSearch, UserSearch or RoomSearch server message. """

    __slots__ = ("init", "user", "token", "list", "privatelist", "freeulslots",
                 "ulspeed", "inqueue", "fifoqueue")

    def __init__(self, init=None, user=None, token=None, shares=None, freeulslots=None,
                 ulspeed=None, inqueue=None, fifoqueue=None):
        self.init = init
        self.user = user
        self.token = token
        self.list = shares
        self.privatelist = []
        self.freeulslots = freeulslots
        self.ulspeed = ulspeed
        self.inqueue = inqueue
        self.fifoqueue = fifoqueue
        self.unknown = 0

    def pack_file_info(self, fileinfo):
        msg = bytearray()
        msg.extend(self.pack_uint8(1))
        msg.extend(self.pack_string(fileinfo[0].replace('/', '\\')))
        msg.extend(self.pack_uint64(fileinfo[1]))

        if fileinfo[2] is None or fileinfo[3] is None:
            # No metadata
            msg.extend(self.pack_string(''))
            msg.extend(self.pack_uint32(0))
        else:
            # FileExtension, NumAttributes
            msg.extend(self.pack_string("mp3"))
            msg.extend(self.pack_uint32(3))

            # Bitrate
            msg.extend(self.pack_uint32(0))
            msg.extend(self.pack_uint32(fileinfo[2][0] or 0))

            # Duration
            msg.extend(self.pack_uint32(1))
            msg.extend(self.pack_uint32(fileinfo[3] or 0))

            # VBR
            msg.extend(self.pack_uint32(2))
            msg.extend(self.pack_uint32(fileinfo[2][1] or 0))

        return msg

    def make_network_message(self):
        msg = bytearray()
        msg.extend(self.pack_string(self.user))
        msg.extend(self.pack_uint32(self.token))
        msg.extend(self.pack_uint32(len(self.list)))

        for fileinfo in self.list:
            msg.extend(self.pack_file_info(fileinfo))

        msg.extend(self.pack_bool(self.freeulslots))
        msg.extend(self.pack_uint32(self.ulspeed))
        msg.extend(self.pack_uint32(self.inqueue))
        msg.extend(self.pack_uint32(self.unknown))

        return zlib.compress(msg)

    def parse_network_message(self, message):
        try:
            message = memoryview(zlib.decompress(message))
            self._parse_network_message(message)

        except Exception as error:
            log.add_debug("Exception during parsing %(area)s: %(exception)s",
                          {'area': 'FileSearchResult', 'exception': error})
            self.list = []
            self.privatelist = []

    def _parse_result_list(self, message, pos):
        pos, nfiles = self.unpack_uint32(message, pos)

        shares = []
        for _ in range(nfiles):
            pos, code = self.unpack_uint8(message, pos)
            pos, name = self.unpack_string(message, pos)
            pos, size = self.parse_file_size(message, pos)
            pos, ext = self.unpack_string(message, pos)
            pos, numattr = self.unpack_uint32(message, pos)

            attrs = {}

            if numattr:
                for _ in range(numattr):
                    pos, attrnum = self.unpack_uint32(message, pos)
                    pos, attr = self.unpack_uint32(message, pos)
                    attrs[str(attrnum)] = attr

            shares.append((code, name.replace('/', '\\'), size, ext, attrs))

        return pos, shares

    def _parse_network_message(self, message):
        pos, self.user = self.unpack_string(message)
        pos, self.token = self.unpack_uint32(message, pos)

        if self.token not in SEARCH_TOKENS_ALLOWED:
            # Results are no longer accepted for this search token, stop parsing message
            self.list = []
            return

        pos, self.list = self._parse_result_list(message, pos)

        pos, self.freeulslots = self.unpack_bool(message, pos)
        pos, self.ulspeed = self.unpack_uint32(message, pos)
        pos, self.inqueue = self.unpack_uint32(message, pos)

        if message[pos:]:
            pos, self.unknown = self.unpack_uint32(message, pos)

        if message[pos:] and config.sections["searches"]["private_search_results"]:
            pos, self.privatelist = self._parse_result_list(message, pos)


class UserInfoRequest(PeerMessage):
    """ Peer code: 15 """
    """ We ask the other peer to send us their user information, picture and all. """

    def __init__(self, init=None):
        self.init = init

    def make_network_message(self):
        return b""

    def parse_network_message(self, message):
        # Empty message
        pass


class UserInfoReply(PeerMessage):
    """ Peer code: 16 """
    """ A peer responds with this after we've sent a UserInfoRequest. """

    def __init__(self, init=None, descr=None, pic=None, totalupl=None, queuesize=None,
                 slotsavail=None, uploadallowed=None):
        self.init = init
        self.descr = descr
        self.pic = pic
        self.totalupl = totalupl
        self.queuesize = queuesize
        self.slotsavail = slotsavail
        self.uploadallowed = uploadallowed
        self.has_pic = None

    def make_network_message(self):
        msg = bytearray()
        msg.extend(self.pack_string(self.descr))

        if self.pic is not None:
            msg.extend(self.pack_bool(True))
            msg.extend(self.pack_bytes(self.pic))
        else:
            msg.extend(self.pack_bool(False))

        msg.extend(self.pack_uint32(self.totalupl))
        msg.extend(self.pack_uint32(self.queuesize))
        msg.extend(self.pack_bool(self.slotsavail))
        msg.extend(self.pack_uint32(self.uploadallowed))

        return msg

    def parse_network_message(self, message):
        pos, self.descr = self.unpack_string(message)
        pos, self.has_pic = self.unpack_bool(message, pos)

        if self.has_pic:
            pos, self.pic = self.unpack_bytes(message, pos)

        pos, self.totalupl = self.unpack_uint32(message, pos)
        pos, self.queuesize = self.unpack_uint32(message, pos)
        pos, self.slotsavail = self.unpack_bool(message, pos)

        # To prevent errors, ensure that >= 4 bytes are left. Museek+ incorrectly sends
        # slotsavail as an integer, resulting in 3 bytes of garbage here.
        if len(message[pos:]) >= 4:
            pos, self.uploadallowed = self.unpack_uint32(message, pos)


class PMessageUser(PeerMessage):
    """ Peer code: 22 """
    """ Chat phrase sent to someone or received by us in private.
    This is a Nicotine+ extension to the Soulseek protocol. """
    """ DEPRECATED """

    def __init__(self, init=None, user=None, msg=None):
        self.init = init
        self.user = user
        self.msg = msg
        self.msgid = None
        self.timestamp = None

    def make_network_message(self):
        msg = bytearray()
        msg.extend(self.pack_uint32(0))
        msg.extend(self.pack_uint32(0))
        msg.extend(self.pack_string(self.user))
        msg.extend(self.pack_string(self.msg))

        return msg

    def parse_network_message(self, message):
        pos, self.msgid = self.unpack_uint32(message)
        pos, self.timestamp = self.unpack_uint32(message, pos)
        pos, self.user = self.unpack_string(message, pos)
        pos, self.msg = self.unpack_string(message, pos)


class FolderContentsRequest(PeerMessage):
    """ Peer code: 36 """
    """ We ask the peer to send us the contents of a single folder. """

    def __init__(self, init=None, directory=None):
        self.init = init
        self.dir = directory
        self.something = None

    def make_network_message(self):
        msg = bytearray()
        msg.extend(self.pack_uint32(1))
        msg.extend(self.pack_string(self.dir, latin1=True))

        return msg

    def parse_network_message(self, message):
        pos, self.something = self.unpack_uint32(message)
        pos, self.dir = self.unpack_string(message, pos)


class FolderContentsResponse(PeerMessage):
    """ Peer code: 37 """
    """ A peer responds with the contents of a particular folder
    (with all subfolders) after we've sent a FolderContentsRequest. """

    def __init__(self, init=None, directory=None, shares=None):
        self.init = init
        self.dir = directory
        self.list = shares

    def parse_network_message(self, message):
        try:
            message = memoryview(zlib.decompress(message))
            self._parse_network_message(message)

        except Exception as error:
            log.add_debug("Exception during parsing %(area)s: %(exception)s",
                          {'area': 'FolderContentsResponse', 'exception': error})
            self.list = {}

    def _parse_network_message(self, message):
        shares = {}
        pos, nfolders = self.unpack_uint32(message)

        for _ in range(nfolders):
            pos, folder = self.unpack_string(message, pos)

            shares[folder] = {}

            pos, ndir = self.unpack_uint32(message, pos)

            for _ in range(ndir):
                pos, directory = self.unpack_string(message, pos)
                directory = directory.replace('/', '\\')
                pos, nfiles = self.unpack_uint32(message, pos)

                shares[folder][directory] = []

                for _ in range(nfiles):
                    pos, code = self.unpack_uint8(message, pos)
                    pos, name = self.unpack_string(message, pos)
                    pos, size = self.unpack_uint64(message, pos)
                    pos, ext = self.unpack_string(message, pos)
                    pos, numattr = self.unpack_uint32(message, pos)

                    attrs = {}

                    for _ in range(numattr):
                        pos, attrnum = self.unpack_uint32(message, pos)
                        pos, attr = self.unpack_uint32(message, pos)
                        attrs[str(attrnum)] = attr

                    shares[folder][directory].append((code, name, size, ext, attrs))

        self.list = shares

    def make_network_message(self):
        msg = bytearray()
        msg.extend(self.pack_uint32(1))
        msg.extend(self.pack_string(self.dir))
        msg.extend(self.pack_uint32(1))
        msg.extend(self.pack_string(self.dir))

        if self.list is not None:
            # We already saved the folder contents as a bytearray when scanning our shares
            msg.extend(self.list)
        else:
            # No folder contents
            msg.extend(self.pack_uint32(0))

        return zlib.compress(msg)


class TransferRequest(PeerMessage):
    """ Peer code: 40 """
    """ This message is sent by a peer once they are ready to start uploading a file.
    A TransferResponse message is expected from the recipient, either allowing or
    rejecting the upload attempt.

    This message was formely used to send a download request (direction 0) as well,
    but Nicotine+, Museek+ and the official clients use the QueueUpload message for
    this purpose today. """

    def __init__(self, init=None, direction=None, token=None, file=None, filesize=None, realfile=None):
        self.init = init
        self.direction = direction
        self.token = token
        self.file = file  # virtual file
        self.realfile = realfile
        self.filesize = filesize

    def make_network_message(self):
        msg = bytearray()
        msg.extend(self.pack_uint32(self.direction))
        msg.extend(self.pack_uint32(self.token))
        msg.extend(self.pack_string(self.file))

        if self.direction == TransferDirection.UPLOAD:
            msg.extend(self.pack_uint64(self.filesize))

        return msg

    def parse_network_message(self, message):
        pos, self.direction = self.unpack_uint32(message)
        pos, self.token = self.unpack_uint32(message, pos)
        pos, self.file = self.unpack_string(message, pos)

        if self.direction == TransferDirection.UPLOAD:
            pos, self.filesize = self.unpack_uint64(message, pos)


class TransferResponse(PeerMessage):
    """ Peer code: 41 """
    """ Response to TransferRequest - We (or the other peer) either agrees,
    or tells the reason for rejecting the file transfer. """

    def __init__(self, init=None, allowed=None, reason=None, token=None, filesize=None):
        self.init = init
        self.allowed = allowed
        self.token = token
        self.reason = reason
        self.filesize = filesize

    def make_network_message(self):
        msg = bytearray()
        msg.extend(self.pack_uint32(self.token))
        msg.extend(self.pack_bool(self.allowed))

        if self.reason is not None:
            msg.extend(self.pack_string(self.reason))

        if self.filesize is not None:
            msg.extend(self.pack_uint64(self.filesize))

        return msg

    def parse_network_message(self, message):
        pos, self.token = self.unpack_uint32(message)
        pos, self.allowed = self.unpack_bool(message, pos)

        if message[pos:]:
            if self.allowed:
                pos, self.filesize = self.unpack_uint64(message, pos)
            else:
                pos, self.reason = self.unpack_string(message, pos)


class PlaceholdUpload(PeerMessage):
    """ Peer code: 42 """
    """ OBSOLETE, no longer used """

    def __init__(self, init=None, file=None):
        self.init = init
        self.file = file

    def make_network_message(self):
        return self.pack_string(self.file)

    def parse_network_message(self, message):
        _pos, self.file = self.unpack_string(message)


class QueueUpload(PeerMessage):
    """ Peer code: 43 """
    """ This message is used to tell a peer that an upload should be queued on
    their end. Once the recipient is ready to transfer the requested file, they
    will send a TransferRequest to us. """

    def __init__(self, init=None, file=None, legacy_client=False):
        self.init = init
        self.file = file
        self.legacy_client = legacy_client

    def make_network_message(self):
        return self.pack_string(self.file, latin1=self.legacy_client)

    def parse_network_message(self, message):
        _pos, self.file = self.unpack_string(message)


class PlaceInQueue(PeerMessage):
    """ Peer code: 44 """
    """ The peer replies with the upload queue placement of the requested file. """

    def __init__(self, init=None, filename=None, place=None):
        self.init = init
        self.filename = filename
        self.place = place

    def make_network_message(self):
        msg = bytearray()
        msg.extend(self.pack_string(self.filename))
        msg.extend(self.pack_uint32(self.place))

        return msg

    def parse_network_message(self, message):
        pos, self.filename = self.unpack_string(message)
        pos, self.place = self.unpack_uint32(message, pos)


class UploadFailed(PlaceholdUpload):
    """ Peer code: 46 """
    """ This message is sent whenever a file connection of an active upload
    closes. Soulseek NS clients can also send this message when a file can
    not be read. The recipient either re-queues the upload (download on their
    end), or ignores the message if the transfer finished. """


class UploadDenied(PeerMessage):
    """ Peer code: 50 """
    """ This message is sent to reject QueueUpload attempts and previously queued
    files. The reason for rejection will appear in the transfer list of the recipient. """

    def __init__(self, init=None, file=None, reason=None):
        self.init = init
        self.file = file
        self.reason = reason

    def make_network_message(self):
        msg = bytearray()
        msg.extend(self.pack_string(self.file))
        msg.extend(self.pack_string(self.reason))

        return msg

    def parse_network_message(self, message):
        pos, self.file = self.unpack_string(message)
        pos, self.reason = self.unpack_string(message, pos)


class PlaceInQueueRequest(QueueUpload):
    """ Peer code: 51 """
    """ This message is sent when asking for the upload queue placement of a file. """


class UploadQueueNotification(PeerMessage):
    """ Peer code: 52 """
    """ This message is sent to inform a peer about an upload attempt initiated by us. """
    """ DEPRECATED, sent by Soulseek NS but not SoulseekQt """

    def __init__(self, init=None):
        self.init = init

    def make_network_message(self):
        return b""

    def parse_network_message(self, _message):
        return b""


class UnknownPeerMessage(PeerMessage):
    """ Peer code: 12547 """
    """ UNKNOWN """

    def __init__(self, init=None):
        self.init = init

    def parse_network_message(self, message):
        # Empty message
        pass


"""
File Messages
"""


class FileMessage(SlskMessage):
    msgtype = MessageType.FILE


class FileDownloadInit(FileMessage):
    """ We receive this from a peer via a 'F' connection when they want to start
    uploading a file to us. The token is the same as the one previously included
    in the TransferRequest peer message. """

    def __init__(self, init=None, token=None):
        self.init = init
        self.token = token

    def parse_network_message(self, message):
        _pos, self.token = self.unpack_uint32(message)


class FileUploadInit(FileMessage):
    """ We send this to a peer via a 'F' connection to tell them that we want to
    start uploading a file. The token is the same as the one previously included
    in the TransferRequest peer message. """

    def __init__(self, init=None, token=None):
        self.init = init
        self.token = token

    def make_network_message(self):
        return self.pack_uint32(self.token)


class FileOffset(FileMessage):
    """ We send this to the uploading peer at the beginning of a 'F' connection,
    to tell them how many bytes of the file we've previously downloaded. If none,
    the offset is 0. """

    def __init__(self, init=None, offset=None):
        self.init = init
        self.offset = offset

    def make_network_message(self):
        return self.pack_uint64(self.offset)

    def parse_network_message(self, message):
        _pos, self.offset = self.unpack_uint64(message)


"""
Distributed Messages
"""


class DistribMessage(SlskMessage):
    msgtype = MessageType.DISTRIBUTED


class DistribAlive(DistribMessage):
    """ Distrib code: 0 """

    def __init__(self, init=None):
        self.init = init

    def make_network_message(self):
        return b""

    def parse_network_message(self, message):
        # Empty message
        pass


class DistribSearch(DistribMessage):
    """ Distrib code: 3 """
    """ Search request that arrives through the distributed network.
    We transmit the search request to our child peers. """

    __slots__ = ("unknown", "init", "user", "token", "searchterm")

    def __init__(self, init=None, unknown=None, user=None, token=None, searchterm=None):
        self.init = init
        self.unknown = unknown
        self.user = user
        self.token = token
        self.searchterm = searchterm

    def make_network_message(self):
        msg = bytearray()
        msg.extend(self.pack_uint32(self.unknown))
        msg.extend(self.pack_string(self.user))
        msg.extend(self.pack_uint32(self.token))
        msg.extend(self.pack_string(self.searchterm))

        return msg

    def parse_network_message(self, message):
        try:
            self._parse_network_message(message)

        except Exception as error:
            log.add_debug("Exception during parsing %(area)s: %(exception)s",
                          {'area': 'DistribSearch', 'exception': error})

    def _parse_network_message(self, message):
        pos, self.unknown = self.unpack_uint32(message)
        pos, self.user = self.unpack_string(message, pos)
        pos, self.token = self.unpack_uint32(message, pos)
        pos, self.searchterm = self.unpack_string(message, pos)


class DistribBranchLevel(DistribMessage):
    """ Distrib code: 4 """
    """ We tell our distributed children what our position is in our branch (xth
    generation) on the distributed network. """

    def __init__(self, init=None, value=None):
        self.init = init
        self.value = value

    def make_network_message(self):
        return self.pack_int32(self.value)

    def parse_network_message(self, message):
        _pos, self.value = self.unpack_int32(message)


class DistribBranchRoot(DistribMessage):
    """ Distrib code: 5 """
    """ We tell our distributed children the username of the root of the branch
    we’re in on the distributed network. """

    def __init__(self, init=None, user=None):
        self.init = init
        self.user = user

    def make_network_message(self):
        return self.pack_string(self.user)

    def parse_network_message(self, message):
        _pos, self.user = self.unpack_string(message)


class DistribChildDepth(DistribMessage):
    """ Distrib code: 7 """
    """ We tell our distributed parent the maximum number of generation of children
    we have on the distributed network. """
    """ DEPRECATED, sent by Soulseek NS but not SoulseekQt """

    def __init__(self, init=None, value=None):
        self.init = init
        self.value = value

    def make_network_message(self):
        return self.pack_uint32(self.value)

    def parse_network_message(self, message):
        _pos, self.value = self.unpack_uint32(message)


class DistribEmbeddedMessage(DistribMessage):
    """ Distrib code: 93 """
    """ A branch root sends us an embedded distributed message. We unpack the
    distributed message and distribute it to our child peers. The only type of
    distributed message sent at present is DistribSearch (distributed code 3). """

    __slots__ = ("init", "distrib_code", "distrib_message")

    def __init__(self, init=None, distrib_code=None, distrib_message=None):
        self.init = init
        self.distrib_code = distrib_code
        self.distrib_message = distrib_message

    def make_network_message(self):
        msg = bytearray()
        msg.extend(self.pack_uint8(self.distrib_code))
        msg.extend(self.distrib_message)

        return msg

    def parse_network_message(self, message):
        pos, self.distrib_code = self.unpack_uint8(message, 3)
        self.distrib_message = message[pos:]


"""
Message Codes
"""


SERVER_MESSAGE_CODES = {
    Login: 1,
    SetWaitPort: 2,
    GetPeerAddress: 3,
    AddUser: 5,
    RemoveUser: 6,
    GetUserStatus: 7,
    SayChatroom: 13,
    JoinRoom: 14,
    LeaveRoom: 15,
    UserJoinedRoom: 16,
    UserLeftRoom: 17,
    ConnectToPeer: 18,
    MessageUser: 22,
    MessageAcked: 23,
    FileSearchRoom: 25,           # Obsolete
    FileSearch: 26,
    SetStatus: 28,
    ServerPing: 32,               # Deprecated
    SendConnectToken: 33,         # Obsolete
    SendDownloadSpeed: 34,        # Obsolete
    SharedFoldersFiles: 35,
    GetUserStats: 36,
    QueuedDownloads: 40,          # Obsolete
    Relogged: 41,
    UserSearch: 42,
    AddThingILike: 51,            # Deprecated
    RemoveThingILike: 52,         # Deprecated
    Recommendations: 54,          # Deprecated
    GlobalRecommendations: 56,    # Deprecated
    UserInterests: 57,            # Deprecated
    AdminCommand: 58,             # Obsolete
    PlaceInLineResponse: 60,      # Obsolete
    RoomAdded: 62,                # Obsolete
    RoomRemoved: 63,              # Obsolete
    RoomList: 64,
    ExactFileSearch: 65,          # Obsolete
    AdminMessage: 66,
    GlobalUserList: 67,           # Obsolete
    TunneledMessage: 68,          # Obsolete
    PrivilegedUsers: 69,
    HaveNoParent: 71,
    SearchParent: 73,             # Deprecated
    ParentMinSpeed: 83,
    ParentSpeedRatio: 84,
    ParentInactivityTimeout: 86,  # Obsolete
    SearchInactivityTimeout: 87,  # Obsolete
    MinParentsInCache: 88,        # Obsolete
    DistribAliveInterval: 90,     # Obsolete
    AddToPrivileged: 91,          # Obsolete
    CheckPrivileges: 92,
    EmbeddedMessage: 93,
    AcceptChildren: 100,
    PossibleParents: 102,
    WishlistSearch: 103,
    WishlistInterval: 104,
    SimilarUsers: 110,            # Deprecated
    ItemRecommendations: 111,     # Deprecated
    ItemSimilarUsers: 112,        # Deprecated
    RoomTickerState: 113,
    RoomTickerAdd: 114,
    RoomTickerRemove: 115,
    RoomTickerSet: 116,
    AddThingIHate: 117,           # Deprecated
    RemoveThingIHate: 118,        # Deprecated
    RoomSearch: 120,
    SendUploadSpeed: 121,
    UserPrivileged: 122,          # Deprecated
    GivePrivileges: 123,
    NotifyPrivileges: 124,        # Deprecated
    AckNotifyPrivileges: 125,     # Deprecated
    BranchLevel: 126,
    BranchRoot: 127,
    ChildDepth: 129,              # Deprecated
    ResetDistributed: 130,
    PrivateRoomUsers: 133,
    PrivateRoomAddUser: 134,
    PrivateRoomRemoveUser: 135,
    PrivateRoomDismember: 136,
    PrivateRoomDisown: 137,
    PrivateRoomSomething: 138,    # Obsolete
    PrivateRoomAdded: 139,
    PrivateRoomRemoved: 140,
    PrivateRoomToggle: 141,
    ChangePassword: 142,
    PrivateRoomAddOperator: 143,
    PrivateRoomRemoveOperator: 144,
    PrivateRoomOperatorAdded: 145,
    PrivateRoomOperatorRemoved: 146,
    PrivateRoomOwned: 148,
    MessageUsers: 149,
    JoinPublicRoom: 150,          # Deprecated
    LeavePublicRoom: 151,         # Deprecated
    PublicRoomMessage: 152,       # Deprecated
    RelatedSearch: 153,           # Obsolete
    CantConnectToPeer: 1001,
    CantCreateRoom: 1003
}

PEER_INIT_MESSAGE_CODES = {
    PierceFireWall: 0,
    PeerInit: 1
}

PEER_MESSAGE_CODES = {
    GetSharedFileList: 4,
    SharedFileList: 5,
    FileSearchRequest: 8,         # Obsolete
    FileSearchResult: 9,
    UserInfoRequest: 15,
    UserInfoReply: 16,
    PMessageUser: 22,             # Deprecated
    FolderContentsRequest: 36,
    FolderContentsResponse: 37,
    TransferRequest: 40,
    TransferResponse: 41,
    PlaceholdUpload: 42,          # Obsolete
    QueueUpload: 43,
    PlaceInQueue: 44,
    UploadFailed: 46,
    UploadDenied: 50,
    PlaceInQueueRequest: 51,
    UploadQueueNotification: 52,  # Deprecated
    UnknownPeerMessage: 12547
}

DISTRIBUTED_MESSAGE_CODES = {
    DistribAlive: 0,
    DistribSearch: 3,
    DistribBranchLevel: 4,
    DistribBranchRoot: 5,
    DistribChildDepth: 7,         # Deprecated
    DistribEmbeddedMessage: 93
}

SERVER_MESSAGE_CLASSES = {v: k for k, v in SERVER_MESSAGE_CODES.items()}
PEER_INIT_MESSAGE_CLASSES = {v: k for k, v in PEER_INIT_MESSAGE_CODES.items()}
PEER_MESSAGE_CLASSES = {v: k for k, v in PEER_MESSAGE_CODES.items()}
DISTRIBUTED_MESSAGE_CLASSES = {v: k for k, v in DISTRIBUTED_MESSAGE_CODES.items()}
