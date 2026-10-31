# SPDX-FileCopyrightText: 2020-2026 Nicotine+ Contributors
# SPDX-FileCopyrightText: 2009-2011 quinox <quinox@users.sf.net>
# SPDX-FileCopyrightText: 2007-2009 daelstorm <daelstorm@gmail.com>
# SPDX-FileCopyrightText: 2003-2004 Hyriand <hyriand@thegraveyard.org>
# SPDX-FileCopyrightText: 2001-2003 Alexander Kanavin
# SPDX-License-Identifier: GPL-3.0-or-later

import zlib

try:
    # Try faster module import first, if available
    from _md5 import md5  # pylint: disable=import-private-name
except ImportError:
    from hashlib import md5

from operator import itemgetter
from random import randint
from socket import inet_aton
from socket import inet_ntoa
from struct import Struct

from pynicotine.logfacility import log
from pynicotine.utils import UINT32_LIMIT
from pynicotine.utils import human_length

# This module contains message classes, that networking and UI thread
# exchange. Basically there are three types of messages: internal messages,
# server messages and p2p messages (between clients).


INT32_UNPACK = Struct("<i").unpack_from
DOUBLE_UINT32_UNPACK = Struct("<II").unpack_from
UINT16_UNPACK = Struct("<H").unpack_from
UINT32_UNPACK = Struct("<I").unpack_from
UINT64_UNPACK = Struct("<Q").unpack_from

BOOL_PACK = Struct("?").pack
UINT8_PACK = Struct("B").pack
INT32_PACK = Struct("<i").pack
UINT32_PACK = Struct("<I").pack
UINT64_PACK = Struct("<Q").pack

SERVER_USERNAME = "server"
ZLIB_COMPRESSION_LEVEL = 4


def initial_token():
    """Return a random token in a large enough range to effectively prevent
    conflicting tokens between sessions."""
    return randint(0, UINT32_LIMIT // 1000)


def increment_token(token):
    """Increment a token used by file search, transfer and connection
    requests."""

    if token < 0 or token >= UINT32_LIMIT:
        # Protocol messages use unsigned integers for tokens
        token = 0

    token += 1
    return token


# Constants #


class MessageType:
    INTERNAL = "N"
    INIT = "I"
    SERVER = "S"
    PEER = "P"
    FILE = "F"
    DISTRIBUTED = "D"


class ConnectionType:
    SERVER = "S"
    PEER = "P"
    FILE = "F"
    DISTRIBUTED = "D"


class ObfuscationType:
    NONE = 0
    ROTATED = 1


class LoginRejectReason:
    INVALID_USERNAME = "INVALIDUSERNAME"
    EMPTY_PASSWORD = "EMPTYPASSWORD"
    INVALID_PASSWORD = "INVALIDPASS"
    INVALID_VERSION = "INVALIDVERSION"
    SERVER_FULL = "SVRFULL"
    SERVER_PRIVATE = "SVRPRIVATE"


class UserStatus:
    OFFLINE = 0
    AWAY = 1
    ONLINE = 2


class RoomType:
    PUBLIC = 0
    PRIVATE = 1


class TransferDirection:
    DOWNLOAD = 0
    UPLOAD = 1


class TransferRejectReason:
    QUEUED = "Queued"
    COMPLETE = "Complete"
    CANCELLED = "Cancelled"
    FILE_READ_ERROR = "File read error."
    FILE_NOT_SHARED = "File not shared."
    BANNED = "Banned"
    PENDING_SHUTDOWN = "Pending shutdown."
    TOO_MANY_FILES = "Too many files"
    TOO_MANY_MEGABYTES = "Too many megabytes"
    DISALLOWED_EXTENSION = "Disallowed extension"


class FileAttribute:
    BITRATE = 0
    LENGTH = 1
    VBR = 2
    ENCODER = 3  # Obsolete
    SAMPLE_RATE = 4
    BIT_DEPTH = 5


class ParentStatus:
    ACCEPTED = 0
    WAITING = 1
    REJECTED = 2


# Internal Messages #


class InternalMessage:
    __slots__ = ()
    TYPE = MessageType.INTERNAL
    LOGGED = True
    HIDDEN_FIELDS = {}

    def __repr__(self):
        attrs = {s: getattr(self, s) for s in self.__slots__ if s not in self.HIDDEN_FIELDS}
        return f"<{self.TYPE} - {type(self).__name__}> {attrs}"


class CloseConnection(InternalMessage):
    __slots__ = ("sock",)

    def __init__(self, sock=None):
        self.sock = sock


class ServerConnect(InternalMessage):
    """Sent to the networking thread to establish a server connection."""

    __slots__ = ("addr", "username", "password", "interface_name", "interface_address", "listen_port",
                 "portmapper")
    HIDDEN_FIELDS = {"username", "password"}

    def __init__(self, addr=None, username=None, password=None, interface_name=None, interface_address=None,
                 listen_port=None, portmapper=None):
        self.addr = addr
        self.username = username
        self.password = password
        self.interface_name = interface_name
        self.interface_address = interface_address
        self.listen_port = listen_port
        self.portmapper = portmapper


class ServerDisconnect(InternalMessage):
    __slots__ = ("manual_disconnect",)

    def __init__(self, manual_disconnect=False):
        self.manual_disconnect = manual_disconnect


class ServerReconnect(InternalMessage):
    __slots__ = ("manual_reconnect",)

    def __init__(self, manual_reconnect=False):
        self.manual_reconnect = manual_reconnect


class EmitNetworkMessageEvents(InternalMessage):
    """Sent to the networking thread to tell it to emit events for list of
    network messages.

    Currently used after shares have rescanned to process any
    QueueUpload messages that arrived while scanning.
    """

    __slots__ = ("msgs",)

    def __init__(self, msgs=None):
        self.msgs = msgs


class DownloadFile(InternalMessage):
    """Sent to the networking thread to pass the file object to write."""

    __slots__ = ("sock", "token", "file_handle", "num_bytes_left", "speed")

    def __init__(self, sock=None, token=None, file_handle=None, num_bytes_left=None):
        self.sock = sock
        self.token = token
        self.file_handle = file_handle
        self.num_bytes_left = num_bytes_left
        self.speed = 0


class UploadFile(InternalMessage):
    __slots__ = ("sock", "token", "file_handle", "file_size", "num_bytes_sent", "offset", "speed")

    def __init__(self, sock=None, token=None, file_handle=None, file_size=None, num_bytes_sent=0,
                 offset=None):
        self.sock = sock
        self.token = token
        self.file_handle = file_handle
        self.file_size = file_size
        self.num_bytes_sent = num_bytes_sent
        self.offset = offset
        self.speed = 0


class SetUploadLimit(InternalMessage):
    """Sent to the networking thread to indicate changes in bandwidth shaping rules."""

    __slots__ = ("limit", "limitby")

    def __init__(self, limit, limitby):
        self.limit = limit
        self.limitby = limitby


class SetDownloadLimit(InternalMessage):
    """Sent to the networking thread to indicate changes in bandwidth shaping rules."""

    __slots__ = ("limit",)

    def __init__(self, limit):
        self.limit = limit


class AddAllowedResponse(InternalMessage):
    """Sent to the networking thread to indicate that we're expecting a message response
    with a certain ID (username, token, etc). More heavy tasks can be performed for allowed
    responses, such as decompression.
    """

    __slots__ = ("msg_class", "response_id")

    def __init__(self, msg_class, response_id):
        self.msg_class = msg_class
        self.response_id = response_id


class RemoveAllowedResponse(InternalMessage):
    """Sent to the networking thread to indicate that we're no longer expecting a message
    response with a certain ID (username, token, etc).
    """

    __slots__ = ("msg_class", "response_id")

    def __init__(self, msg_class, response_id):
        self.msg_class = msg_class
        self.response_id = response_id


# Network Messages #


class SlskMessage:
    """This is a parent class for all protocol messages."""

    __slots__ = ("_message", "_offset")
    TYPE = None
    CODE = None
    EVENT_NAME = None
    LOGGED = True
    HIDDEN_FIELDS = {}

    def __init__(self, msg_content=None):
        self._message = msg_content
        self._offset = 0

    def finish_parsing(self):
        self._message = None
        self._offset = 0

    @staticmethod
    def pack_bytes(content):
        return UINT32_PACK(len(content)) + content

    @staticmethod
    def pack_string(content, is_legacy=False):

        if is_legacy:
            # Legacy string
            try:
                encoded = content.encode("latin-1")

            except UnicodeEncodeError:
                encoded = content.encode("utf-8", "replace")

        else:
            encoded = content.encode("utf-8", "replace")

        return UINT32_PACK(len(encoded)) + encoded

    @staticmethod
    def pack_bool(content):
        return BOOL_PACK(content)

    @staticmethod
    def pack_uint8(content):
        return UINT8_PACK(content)

    @staticmethod
    def pack_int32(content):
        return INT32_PACK(content)

    @staticmethod
    def pack_uint32(content):
        return UINT32_PACK(content)

    @staticmethod
    def pack_uint64(content):
        return UINT64_PACK(content)

    def has_remaining_content(self):
        return bool(self._message[self._offset:])

    def unpack_bytes(self):

        length, = UINT32_UNPACK(self._message, self._offset)
        start = self._offset + 4
        self._offset = start + length
        content = self._message[start:self._offset]

        return content.tobytes()

    def unpack_string(self):

        length, = UINT32_UNPACK(self._message, self._offset)
        start = self._offset + 4
        self._offset = start + length
        content = self._message[start:self._offset].tobytes()

        try:
            string = content.decode("utf-8")

        except UnicodeDecodeError:
            # Legacy strings
            string = content.decode("latin-1")

        return string

    def unpack_bool(self):
        result = bool(self._message[self._offset])
        self._offset += 1
        return result

    def unpack_ip(self):
        start = self._offset
        self._offset += 4
        return inet_ntoa(self._message[start:self._offset].tobytes()[::-1])

    def unpack_uint8(self):
        result = self._message[self._offset]
        self._offset += 1
        return result

    def unpack_uint16(self):
        result, = UINT16_UNPACK(self._message, self._offset)
        self._offset += 2
        return result

    def unpack_int32(self):
        result, = INT32_UNPACK(self._message, self._offset)
        self._offset += 4
        return result

    def unpack_uint32(self):
        result, = UINT32_UNPACK(self._message, self._offset)
        self._offset += 4
        return result

    def unpack_uint64(self):
        result, = UINT64_UNPACK(self._message, self._offset)
        self._offset += 8
        return result

    def __repr__(self):
        attrs = {s: getattr(self, s) for s in self.__slots__ if s not in self.HIDDEN_FIELDS}
        return f"<{self.TYPE} - {type(self).__name__}> {attrs}"


class FileListMessage(SlskMessage):
    __slots__ = ()

    @classmethod
    def pack_file_info(cls, fileinfo):

        msg = bytearray()
        virtual_file_path, size, quality, duration = fileinfo
        bitrate = is_vbr = samplerate = bitdepth = None

        if quality is not None:
            bitrate, is_vbr, samplerate, bitdepth = quality

        msg += cls.pack_uint8(1)
        msg += cls.pack_string(virtual_file_path)
        msg += cls.pack_uint64(size)
        msg += cls.pack_uint32(0)  # empty ext

        num_attrs = 0
        msg_attrs = bytearray()

        is_lossless = bitdepth is not None

        if is_lossless:
            if duration is not None:
                msg_attrs += cls.pack_uint32(1)
                msg_attrs += cls.pack_uint32(duration)
                num_attrs += 1

            if samplerate is not None:
                msg_attrs += cls.pack_uint32(4)
                msg_attrs += cls.pack_uint32(samplerate)
                num_attrs += 1

            if bitdepth is not None:
                msg_attrs += cls.pack_uint32(5)
                msg_attrs += cls.pack_uint32(bitdepth)
                num_attrs += 1
        else:
            if bitrate is not None:
                msg_attrs += cls.pack_uint32(0)
                msg_attrs += cls.pack_uint32(bitrate)
                num_attrs += 1

            if duration is not None:
                msg_attrs += cls.pack_uint32(1)
                msg_attrs += cls.pack_uint32(duration)
                num_attrs += 1

            if bitrate is not None:
                msg_attrs += cls.pack_uint32(2)
                msg_attrs += cls.pack_uint32(is_vbr)
                num_attrs += 1

        msg += cls.pack_uint32(num_attrs)

        if msg_attrs:
            msg += msg_attrs

        return msg

    @classmethod
    def parse_audio_quality_length(cls, file_size, attributes, always_show_bitrate=False):

        bitrate = attributes.bitrate
        length = attributes.length
        vbr = attributes.vbr
        sample_rate = attributes.sample_rate
        bit_depth = attributes.bit_depth

        if bitrate is None:
            if sample_rate and bit_depth:
                # Bitrate = sample rate (Hz) * word length (bits) * channel count
                # Bitrate = 44100 * 16 * 2
                bitrate = (sample_rate * bit_depth * 2) // 1000
            else:
                bitrate = -1

        if length is None:
            if bitrate > 0:
                # Dividing the file size by the bitrate in Bytes should give us a good enough approximation
                length = file_size // (bitrate * 125)
            else:
                length = -1

        # Ignore invalid values
        if bitrate <= 0 or bitrate > UINT32_LIMIT:
            bitrate = 0
            h_quality = ""

        elif sample_rate and bit_depth:
            h_quality = f"{sample_rate / 1000:.3g} kHz / {bit_depth} bit"

            if always_show_bitrate:
                h_quality += f" / {bitrate} kbps"
        else:
            h_quality = f"{bitrate} kbps"

            if vbr == 1:
                h_quality += " (vbr)"

        if length < 0 or length > UINT32_LIMIT:
            length = 0
            h_length = ""
        else:
            h_length = human_length(length)

        return h_quality, bitrate, h_length, length


class SimilarUser:
    __slots__ = ("username", "rating")

    def __init__(self, username, rating=None):
        self.username = username
        self.rating = rating

    def __repr__(self):
        return f"({self.username!r}, {self.rating!r})"


class UserData:
    """When we join a room, the server sends us a bunch of these for each
    user."""

    __slots__ = ("username", "status", "upload_speed", "upload_number", "unknown", "num_files", "num_folders",
                 "slots_full", "country")

    def __init__(self, username=None, status=None, upload_speed=None, upload_number=None, unknown=None,
                 num_files=None, num_folders=None, slots_full=None, country=None):
        self.username = username
        self.status = status
        self.upload_speed = upload_speed
        self.upload_number = upload_number
        self.unknown = unknown
        self.num_files = num_files
        self.num_folders = num_folders
        self.slots_full = slots_full
        self.country = country


class FileAttributes:
    __slots__ = ("bitrate", "length", "vbr", "sample_rate", "bit_depth")

    def __init__(self, bitrate=None, length=None, vbr=None, sample_rate=None, bit_depth=None):
        self.bitrate = bitrate
        self.length = length
        self.vbr = vbr
        self.sample_rate = sample_rate
        self.bit_depth = bit_depth

    def as_dict(self):
        attributes = {}

        if self.bitrate is not None:
            attributes[FileAttribute.BITRATE] = self.bitrate

        if self.length is not None:
            attributes[FileAttribute.LENGTH] = self.length

        if self.vbr is not None:
            attributes[FileAttribute.VBR] = self.vbr

        if self.sample_rate is not None:
            attributes[FileAttribute.SAMPLE_RATE] = self.sample_rate

        if self.bit_depth is not None:
            attributes[FileAttribute.BIT_DEPTH] = self.bit_depth

        return attributes


class ParentCandidate:

    __slots__ = ("username", "ip_address", "port", "sock", "branch_root", "branch_level")

    def __init__(self, username, ip_address, port):
        self.username = username
        self.ip_address = ip_address
        self.port = port

        self.sock = None
        self.branch_root = None
        self.branch_level = None


# Server Messages #


class ServerMessage(SlskMessage):
    __slots__ = ()
    TYPE = MessageType.SERVER

    def parse_users(self):
        numusers = self.unpack_uint32()

        users = []
        for i in range(numusers):
            users.append(UserData())
            users[i].username = self.unpack_string()

        statuslen = self.unpack_uint32()
        for i in range(statuslen):
            users[i].status = self.unpack_uint32()

        statslen = self.unpack_uint32()
        for i in range(statslen):
            users[i].upload_speed = self.unpack_uint32()
            users[i].upload_number = self.unpack_uint32()
            users[i].unknown = self.unpack_uint32()
            users[i].num_files = self.unpack_uint32()
            users[i].num_folders = self.unpack_uint32()

        slotslen = self.unpack_uint32()
        for i in range(slotslen):
            users[i].slots_full = self.unpack_uint32()

        countrylen = self.unpack_uint32()
        for i in range(countrylen):
            users[i].country = self.unpack_string()

        return users

    def populate_recommendations(self, recommendations, unrecommendations):
        num = self.unpack_uint32()

        for _ in range(num):
            key = self.unpack_string()
            rating = self.unpack_int32()

            lst = recommendations if rating >= 0 else unrecommendations
            item = (key, rating)

            if item not in lst:
                lst.append(item)

    def parse_recommendations(self):
        recommendations = []
        unrecommendations = []

        self.populate_recommendations(recommendations, unrecommendations)

        if self.has_remaining_content():
            self.populate_recommendations(recommendations, unrecommendations)

        return recommendations, unrecommendations


class Login(ServerMessage):
    """Server code 1.

    We send this to the server right after the connection has been
    established. Server responds with the greeting message or a rejection.

    There is no mechanism to reset a forgotten password, so account credentials
    should be validated and must be remembered locally. It is unacceptable to
    use randomly generated usernames, as such automated scripting is disallowed
    by the official server rules (https://www.slsknet.org/news/node/681).

    The server uses the major and minor versions to differentiate between
    clients. Numbers are chosen that avoid impersonating clients with reserved
    major versions. Downstream projects have their own rules for minor
    versions. Experimental clients may use major version `177` and any minor
    version number they choose for each project.
    """

    __slots__ = ("username", "passwd", "version", "minorversion", "success", "rejection_reason",
                 "rejection_detail", "banner", "ip_address", "local_address", "server_address",
                 "is_supporter")
    CODE = 1
    EVENT_NAME = "server-login"
    HIDDEN_FIELDS = {"passwd"}

    def __init__(self, username=None, passwd=None, version=None, minorversion=None, *, msg_content=None):
        ServerMessage.__init__(self, msg_content)
        self.username = username
        self.passwd = passwd
        self.version = version
        self.minorversion = minorversion
        self.success = None
        self.rejection_reason = None
        self.rejection_detail = None
        self.banner = None
        self.ip_address = None
        self.local_address = None
        self.server_address = None
        self.is_supporter = None

    def make_network_message(self):

        msg = bytearray()
        msg += self.pack_string(self.username)
        msg += self.pack_string(self.passwd)
        msg += self.pack_uint32(self.version)

        payload = self.username + self.passwd
        md5hash = md5(payload.encode()).hexdigest()
        msg += self.pack_string(md5hash)

        msg += self.pack_uint32(self.minorversion)

        return msg

    def parse_network_message(self):
        self.success = self.unpack_bool()

        if not self.success:
            self.rejection_reason = self.unpack_string()

            if self.has_remaining_content():
                self.rejection_detail = self.unpack_string()
            return

        self.banner = self.unpack_string()
        self.ip_address = self.unpack_ip()
        _checksum = self.unpack_string()  # MD5 hexdigest of the password you sent
        self.is_supporter = self.unpack_bool()


class SetWaitPort(ServerMessage):
    """Server code 2.

    We send this to the server to indicate the port number that we listen on
    (2234 by default). Certain clients like SoulseekQt implement obfuscation of
    peer messages, and also send the obfuscation type and obfuscated port to
    accept such connections on.

    Nicotine+ does not implement obfuscated connections, since there is no
    evidence that ISP traffic shaping targeting the Soulseek network (the
    original issue obfuscation attempted to mitigate) is prevalent today.
    Forwarding multiple ports is also becoming increasingly difficult due to
    IPv4 address exhaustion, and only requiring a single unobfuscated port
    allows users to use their remaining free ports in other applications
    instead.
    """

    __slots__ = ("port",)
    CODE = 2

    def __init__(self, port=None):
        ServerMessage.__init__(self)
        self.port = port

    def make_network_message(self):
        return self.pack_uint32(self.port)


class GetPeerAddress(ServerMessage):
    """Server code 3.

    We send this to the server to ask for a peer's address (IP address
    and port), given the peer's username.
    """

    __slots__ = ("user", "ip_address", "port", "obfuscation_type", "obfuscated_port")
    CODE = 3
    EVENT_NAME = "peer-address"

    def __init__(self, user=None, *, msg_content=None):
        ServerMessage.__init__(self, msg_content)
        self.user = user
        self.ip_address = None
        self.port = None
        self.obfuscation_type = None
        self.obfuscated_port = None

    def make_network_message(self):
        return self.pack_string(self.user)

    def parse_network_message(self):
        self.user = self.unpack_string()
        self.ip_address = self.unpack_ip()
        self.port = self.unpack_uint32()
        self.obfuscation_type = self.unpack_uint32()
        self.obfuscated_port = self.unpack_uint16()


class WatchUser(ServerMessage):
    """Server code 5.

    Used to be kept updated about a user's status. Whenever a user's status
    changes, the server sends a GetUserStatus message.

    Note that the server does not currently send stat updates (GetUserStats)
    when watching a user, only the initial stats in the WatchUser response.
    As a consequence, stats can be outdated.
    """

    __slots__ = ("user", "userexists", "status", "upload_speed", "upload_number", "unknown", "num_files",
                 "num_folders", "country")
    CODE = 5
    EVENT_NAME = "watch-user"

    def __init__(self, user=None, *, msg_content=None):
        ServerMessage.__init__(self, msg_content)
        self.user = user
        self.userexists = None
        self.status = None
        self.upload_speed = None
        self.upload_number = None
        self.unknown = None
        self.num_files = None
        self.num_folders = None
        self.country = None

    def make_network_message(self):
        return self.pack_string(self.user)

    def parse_network_message(self):
        self.user = self.unpack_string()
        self.userexists = self.unpack_bool()

        if not self.userexists:
            return

        self.status = self.unpack_uint32()
        self.upload_speed = self.unpack_uint32()
        self.upload_number = self.unpack_uint32()
        self.unknown = self.unpack_uint32()
        self.num_files = self.unpack_uint32()
        self.num_folders = self.unpack_uint32()

        if not self.has_remaining_content():
            # User is offline
            return

        self.country = self.unpack_string()


class UnwatchUser(ServerMessage):
    """Server code 6.

    Used when we no longer want to be kept updated about a user's status.
    """

    __slots__ = ("user",)
    CODE = 6

    def __init__(self, user=None, *, msg_content=None):
        ServerMessage.__init__(self)
        self.user = user

    def make_network_message(self):
        return self.pack_string(self.user)


class GetUserStatus(ServerMessage):
    """Server code 7.

    The server tells us if a user has gone away or has returned.
    """

    __slots__ = ("user", "status", "privileged")
    CODE = 7
    EVENT_NAME = "user-status"

    def __init__(self, user=None, status=None, *, msg_content=None):
        ServerMessage.__init__(self, msg_content)
        self.user = user
        self.status = status
        self.privileged = None

    def make_network_message(self):
        return self.pack_string(self.user)

    def parse_network_message(self):
        self.user = self.unpack_string()
        self.status = self.unpack_uint32()
        self.privileged = self.unpack_bool()


class IgnoreUser(ServerMessage):
    """Server code 11.

    We send this to the server to tell a user we have ignored them.

    The server tells us a user has ignored us.

    OBSOLETE, no longer functional
    """

    __slots__ = ("user",)
    CODE = 11

    def __init__(self, user=None, *, msg_content=None):
        ServerMessage.__init__(self, msg_content)
        self.user = user

    def make_network_message(self):
        return self.pack_string(self.user)

    def parse_network_message(self):
        self.user = self.unpack_string()


class UnignoreUser(ServerMessage):
    """Server code 12.

    We send this to the server to tell a user we are no longer ignoring them.

    The server tells us a user is no longer ignoring us.

    OBSOLETE, no longer functional
    """

    __slots__ = ("user",)
    CODE = 12

    def __init__(self, user=None, *, msg_content=None):
        ServerMessage.__init__(self, msg_content)
        self.user = user

    def make_network_message(self):
        return self.pack_string(self.user)

    def parse_network_message(self):
        self.user = self.unpack_string()


class SayChatroom(ServerMessage):
    """Server code 13.

    Either we want to say something in the chatroom, or someone else
    did.
    """

    __slots__ = ("room", "message", "user", "message_type", "mention_type", "mention_keyword")
    CODE = 13
    EVENT_NAME = "say-chat-room"

    def __init__(self, room=None, message=None, user=None, *, msg_content=None):
        ServerMessage.__init__(self, msg_content)
        self.room = room
        self.message = message
        self.user = user
        self.message_type = None
        self.mention_type = None
        self.mention_keyword = None

    def make_network_message(self):
        msg = bytearray()
        msg += self.pack_string(self.room)
        msg += self.pack_string(self.message)

        return msg

    def parse_network_message(self):
        self.room = self.unpack_string()
        self.user = self.unpack_string()
        self.message = self.unpack_string()


class JoinRoom(ServerMessage):
    """Server code 14.

    We send this message to the server when we want to join a room. If
    the room doesn't exist, it is created.

    Server responds with this message when we join a room. Contains
    users list with data on everyone.

    As long as we're in the room, the server will automatically send us
    status/stat updates for room users, including ourselves, in the form
    of GetUserStatus and GetUserStats messages.

    Room names must meet certain requirements, otherwise the server will
    send a MessageUser message containing an error message. Requirements
    include:

      - Non-empty string
      - Only ASCII characters
      - 24 characters or fewer
      - No leading or trailing spaces
      - No consecutive spaces
    """

    __slots__ = ("room", "room_type", "owner", "users", "operators")
    CODE = 14
    EVENT_NAME = "join-room"

    def __init__(self, room=None, room_type=RoomType.PUBLIC, *, msg_content=None):
        ServerMessage.__init__(self, msg_content)
        self.room = room
        self.room_type = room_type
        self.owner = None
        self.users = []
        self.operators = []

    def make_network_message(self):
        msg = bytearray()
        msg += self.pack_string(self.room)
        msg += self.pack_uint32(self.room_type)

        return msg

    def parse_network_message(self):
        self.room = self.unpack_string()
        self.users = self.parse_users()

        if not self.has_remaining_content():
            return

        self.room_type = RoomType.PRIVATE
        self.owner = self.unpack_string()
        numops = self.unpack_uint32()

        for _ in range(numops):
            operator = self.unpack_string()
            self.operators.append(operator)


class LeaveRoom(ServerMessage):
    """Server code 15.

    We send this to the server when we want to leave a room.
    """

    __slots__ = ("room",)
    CODE = 15
    EVENT_NAME = "leave-room"

    def __init__(self, room=None, *, msg_content=None):
        ServerMessage.__init__(self, msg_content)
        self.room = room

    def make_network_message(self):
        return self.pack_string(self.room)

    def parse_network_message(self):
        self.room = self.unpack_string()


class UserJoinedRoom(ServerMessage):
    """Server code 16.

    The server tells us someone has just joined a room we're in.
    """

    __slots__ = ("room", "userdata")
    CODE = 16
    EVENT_NAME = "user-joined-room"

    def __init__(self, *, msg_content=None):
        ServerMessage.__init__(self, msg_content)
        self.room = None
        self.userdata = None

    def parse_network_message(self):
        self.room = self.unpack_string()
        self.userdata = UserData(
            username=self.unpack_string(),
            status=self.unpack_uint32(),
            upload_speed=self.unpack_uint32(),
            upload_number=self.unpack_uint32(),
            unknown=self.unpack_uint32(),
            num_files=self.unpack_uint32(),
            num_folders=self.unpack_uint32(),
            slots_full=self.unpack_uint32(),
            country=self.unpack_string()
        )


class UserLeftRoom(ServerMessage):
    """Server code 17.

    The server tells us someone has just left a room we're in.
    """

    __slots__ = ("room", "username")
    CODE = 17
    EVENT_NAME = "user-left-room"

    def __init__(self, *, msg_content=None):
        ServerMessage.__init__(self, msg_content)
        self.room = None
        self.username = None

    def parse_network_message(self):
        self.room = self.unpack_string()
        self.username = self.unpack_string()


class ConnectToPeer(ServerMessage):
    """Server code 18.

    We send this to the server to attempt an indirect connection with a user.
    The server forwards the message to the user, who in turn attempts to establish
    a connection to our IP address and port from their end.
    """

    __slots__ = ("token", "user", "conn_type", "ip_address", "port", "privileged", "obfuscation_type",
                 "obfuscated_port")
    CODE = 18
    EVENT_NAME = "connect-to-peer"

    def __init__(self, token=None, user=None, conn_type=None, *, msg_content=None):
        ServerMessage.__init__(self, msg_content)
        self.token = token
        self.user = user
        self.conn_type = conn_type
        self.ip_address = None
        self.port = None
        self.privileged = None
        self.obfuscation_type = None
        self.obfuscated_port = None

    def make_network_message(self):
        msg = bytearray()
        msg += self.pack_uint32(self.token)
        msg += self.pack_string(self.user)
        msg += self.pack_string(self.conn_type)

        return msg

    def parse_network_message(self):
        self.user = self.unpack_string()
        self.conn_type = self.unpack_string()
        self.ip_address = self.unpack_ip()
        self.port = self.unpack_uint32()
        self.token = self.unpack_uint32()
        self.privileged = self.unpack_bool()
        self.obfuscation_type = self.unpack_uint32()
        self.obfuscated_port = self.unpack_uint32()


class MessageUser(ServerMessage):
    """Server code 22.

    Chat phrase sent to someone or received by us in private.
    """

    __slots__ = ("user", "message", "message_id", "timestamp", "is_new_message", "message_type",
                 "mention_type", "mention_keyword")
    CODE = 22
    EVENT_NAME = "message-user"

    def __init__(self, user=None, message=None, *, msg_content=None):
        ServerMessage.__init__(self, msg_content)
        self.user = user
        self.message = message
        self.message_id = None
        self.timestamp = None
        self.is_new_message = True
        self.message_type = None
        self.mention_type = None
        self.mention_keyword = None

    def make_network_message(self):
        msg = bytearray()
        msg += self.pack_string(self.user)
        msg += self.pack_string(self.message)

        return msg

    def parse_network_message(self):
        self.message_id = self.unpack_uint32()
        self.timestamp = self.unpack_uint32()
        self.user = self.unpack_string()
        self.message = self.unpack_string()
        self.is_new_message = self.unpack_bool()


class MessageAcked(ServerMessage):
    """Server code 23.

    We send this to the server to confirm that we received a private
    message. If we don't send it, the server will keep sending the chat
    phrase to us.
    """

    __slots__ = ("msgid",)
    CODE = 23

    def __init__(self, msgid=None):
        ServerMessage.__init__(self)
        self.msgid = msgid

    def make_network_message(self):
        return self.pack_uint32(self.msgid)


class FileSearchRoom(ServerMessage):
    """Server code 25.

    We send this to the server when we search for something in a room.

    OBSOLETE, superseded by RoomSearch server message
    """

    __slots__ = ("token", "roomid", "searchterm")
    CODE = 25

    def __init__(self, token=None, roomid=None, text=None):
        ServerMessage.__init__(self)
        self.token = token
        self.roomid = roomid
        self.searchterm = text

    def make_network_message(self):
        msg = bytearray()
        msg += self.pack_uint32(self.token)
        msg += self.pack_uint32(self.roomid)
        msg += self.pack_string(self.searchterm)

        return msg


class FileSearch(ServerMessage):
    """Server code 26.

    We send this to the server when we search for something.
    Alternatively, the server sends this message outside the distributed
    network to tell us that someone is searching for something,
    currently used for UserSearch and RoomSearch requests.

    The token is a number generated by the client and is used to track
    the search results.
    """

    __slots__ = ("token", "searchterm", "search_username")
    CODE = 26
    EVENT_NAME = "file-search-request-server"

    def __init__(self, token=None, text=None, *, msg_content=None):
        ServerMessage.__init__(self, msg_content)
        self.token = token
        self.searchterm = text
        self.search_username = None

    def make_network_message(self):
        msg = bytearray()
        msg += self.pack_uint32(self.token)
        msg += self.pack_string(self.searchterm)

        return msg

    def parse_network_message(self):
        self.search_username = self.unpack_string()
        self.token = self.unpack_uint32()
        self.searchterm = self.unpack_string()


class SetStatus(ServerMessage):
    """Server code 28.

    We send our new status to the server. Status is a way to define
    whether we're available (online) or busy (away).

    When changing our own status, the server sends us a GetUserStatus
    message when enabling away status, but not when disabling it.

    1 = Away 2 = Online
    """

    __slots__ = ("status",)
    CODE = 28

    def __init__(self, status=None):
        ServerMessage.__init__(self)
        self.status = status

    def make_network_message(self):
        return self.pack_int32(self.status)


class ServerPing(ServerMessage):
    """Server code 32.

    We send this to the server at most once per minute to ensure the
    connection stays alive.

    The server used to send a response message in the past, but this is no
    longer the case.

    Nicotine+ uses TCP keepalive instead of sending this message.
    """

    __slots__ = ()
    CODE = 32

    def make_network_message(self):
        return b""

    def parse_network_message(self):
        """Obsolete."""


class SendConnectToken(ServerMessage):
    """Server code 33.

    This message used to be sent together with the PeerInit message when
    connecting to a user, with the same non-zero token included in both. The
    recipient could then cross-check the username and token, in order to reject
    spoofed connection attempts.

    While the server still recognizes and forwards this message today, no
    clients use it anymore. The lack of adoption by clients in the past has
    effectively rendered the message unusable, since its reintroduction in a
    client would isolate the client from the rest of the network.

    OBSOLETE, no longer used
    """

    __slots__ = ("user", "token")
    CODE = 33

    def __init__(self, user=None, token=None, *, msg_content=None):
        ServerMessage.__init__(self, msg_content)
        self.user = user
        self.token = token

    def make_network_message(self):
        msg = bytearray()
        msg += self.pack_string(self.user)
        msg += self.pack_uint32(self.token)

        return msg

    def parse_network_message(self):
        self.user = self.unpack_string()
        self.token = self.unpack_uint32()


class SendDownloadSpeed(ServerMessage):
    """Server code 34.

    We used to send this after a finished download to let the server
    update the speed statistics for a user.

    OBSOLETE, superseded by SendUploadSpeed server message
    """

    __slots__ = ("user", "speed")
    CODE = 34

    def __init__(self, user=None, speed=None):
        ServerMessage.__init__(self)
        self.user = user
        self.speed = speed

    def make_network_message(self):
        msg = bytearray()
        msg += self.pack_string(self.user)
        msg += self.pack_uint32(self.speed)

        return msg


class SharedFoldersFiles(ServerMessage):
    """Server code 35.

    We send this to server to indicate the number of folder and files
    that we share.
    """

    __slots__ = ("num_folders", "num_files")
    CODE = 35

    def __init__(self, num_folders=None, num_files=None):
        ServerMessage.__init__(self)
        self.num_folders = num_folders
        self.num_files = num_files

    def make_network_message(self):
        msg = bytearray()
        msg += self.pack_uint32(self.num_folders)
        msg += self.pack_uint32(self.num_files)

        return msg


class GetUserStats(ServerMessage):
    """Server code 36.

    The server sends this to indicate a change in a user's stats, if we have
    joined the same chat room. We can also request a user's stats by sending
    the message to the server.
    """

    __slots__ = ("user", "upload_speed", "upload_number", "unknown", "num_files", "num_folders")
    CODE = 36
    EVENT_NAME = "user-stats"

    def __init__(self, user=None, upload_speed=None, num_files=None, num_folders=None, *, msg_content=None):
        ServerMessage.__init__(self, msg_content)
        self.user = user
        self.upload_speed = upload_speed
        self.num_files = num_files
        self.num_folders = num_folders
        self.upload_number = None
        self.unknown = None

    def make_network_message(self):
        return self.pack_string(self.user)

    def parse_network_message(self):
        self.user = self.unpack_string()
        self.upload_speed = self.unpack_uint32()
        self.upload_number = self.unpack_uint32()
        self.unknown = self.unpack_uint32()
        self.num_files = self.unpack_uint32()
        self.num_folders = self.unpack_uint32()


class UploadSlotsFull(ServerMessage):
    """Server code 40.

    We send this to the server to indicate whether our upload slots are fully
    occupied or not. The server broadcasts the message to joined rooms.

    The official Soulseek client used to send this message on login, as well as
    when upload slots filled up or became available. Users with full slots were
    grayed out in room user lists.

    OBSOLETE, no longer used
    """

    __slots__ = ("user", "slots_full")
    CODE = 40

    def __init__(self, slots_full=None, *, msg_content=None):
        ServerMessage.__init__(self, msg_content)
        self.slots_full = slots_full
        self.user = None

    def make_network_message(self):
        return self.pack_uint32(self.slots_full)

    def parse_network_message(self):
        self.user = self.unpack_string()
        self.slots_full = self.unpack_uint32()


class Relogged(ServerMessage):
    """Server code 41.

    The server sends this if someone else logged in under our nickname,
    and then disconnects us.
    """

    __slots__ = ()
    CODE = 41

    def parse_network_message(self):
        # Empty message
        pass


class UserSearch(ServerMessage):
    """Server code 42.

    We send this to the server when we search a specific user's shares.
    The token is a number generated by the client and is used to track
    the search results.

    The recipient receives the search request in the form of a FileSearch
    message.
    """

    __slots__ = ("search_username", "token", "searchterm")
    CODE = 42

    def __init__(self, search_username=None, token=None, text=None):
        ServerMessage.__init__(self)
        self.search_username = search_username
        self.token = token
        self.searchterm = text

    def make_network_message(self):
        msg = bytearray()
        msg += self.pack_string(self.search_username)
        msg += self.pack_uint32(self.token)
        msg += self.pack_string(self.searchterm)

        return msg


class SimilarRecommendations(ServerMessage):
    """Server code 50.

    We send this to the server when we are adding a recommendation to our
    "My recommendations" list, and want to receive a list of similar
    recommendations.

    The server sends a list of similar recommendations to the one we want to
    add. Older versions of the official Soulseek client would display a dialog
    containing such recommendations, asking us if we want to add our original
    recommendation or one of the similar ones instead.

    OBSOLETE, no longer used, server sends empty list
    """

    __slots__ = ("recommendation", "similar_recommendations")
    CODE = 50

    def __init__(self, recommendation=None, *, msg_content=None):
        ServerMessage.__init__(self, msg_content)
        self.recommendation = recommendation
        self.similar_recommendations = []

    def make_network_message(self):
        return self.pack_string(self.recommendation)

    def parse_network_message(self):
        self.recommendation = self.unpack_string()
        num = self.unpack_uint32()

        for _ in range(num):
            similar_recommendation = self.unpack_string()
            self.similar_recommendations.append(similar_recommendation)


class AddThingILike(ServerMessage):
    """Server code 51.

    We send this to the server when we add an item to our likes list.
    """

    __slots__ = ("thing",)
    CODE = 51

    def __init__(self, thing=None):
        ServerMessage.__init__(self)
        self.thing = thing

    def make_network_message(self):
        return self.pack_string(self.thing)


class RemoveThingILike(ServerMessage):
    """Server code 52.

    We send this to the server when we remove an item from our likes
    list.
    """

    __slots__ = ("thing",)
    CODE = 52

    def __init__(self, thing=None):
        ServerMessage.__init__(self)
        self.thing = thing

    def make_network_message(self):
        return self.pack_string(self.thing)


class Recommendations(ServerMessage):
    """Server code 54.

    The server sends us a list of personal recommendations and a number
    for each.
    """

    __slots__ = ("recommendations", "unrecommendations")
    CODE = 54
    EVENT_NAME = "recommendations"

    def __init__(self, *, msg_content=None):
        ServerMessage.__init__(self, msg_content)
        self.recommendations = []
        self.unrecommendations = []

    def make_network_message(self):
        return b""

    def parse_network_message(self):
        self.recommendations, self.unrecommendations = self.parse_recommendations()


class MyRecommendations(ServerMessage):
    """Server code 55.

    We send this to the server to ask for our own list of added
    likes/recommendations (called "My recommendations" in older versions
    of the official Soulseek client).

    The server sends us the list of recommendations it knows we have added.
    For any recommendations present locally, but not on the server, the
    official Soulseek client would send a AddThingILike message for each
    missing item.

    OBSOLETE, no longer functional
    """

    __slots__ = ("my_recommendations",)
    CODE = 55

    def __init__(self, *, msg_content=None):
        ServerMessage.__init__(self, msg_content)
        self.my_recommendations = []

    def make_network_message(self):
        return b""

    def parse_network_message(self):
        num = self.unpack_uint32()

        for _ in range(num):
            recommendation = self.unpack_string()
            self.my_recommendations.append(recommendation)


class GlobalRecommendations(ServerMessage):
    """Server code 56.

    The server sends us a list of global recommendations and a number
    for each.
    """

    __slots__ = ("recommendations", "unrecommendations")
    CODE = 56
    EVENT_NAME = "global-recommendations"

    def __init__(self, *, msg_content=None):
        ServerMessage.__init__(self, msg_content)
        self.recommendations = []
        self.unrecommendations = []

    def make_network_message(self):
        return b""

    def parse_network_message(self):
        self.recommendations, self.unrecommendations = self.parse_recommendations()


class UserInterests(ServerMessage):
    """Server code 57.

    We ask the server for a user's liked and hated interests. The server
    responds with a list of interests.
    """

    __slots__ = ("user", "likes", "hates")
    CODE = 57
    EVENT_NAME = "user-interests"

    def __init__(self, user=None, *, msg_content=None):
        ServerMessage.__init__(self, msg_content)
        self.user = user
        self.likes = []
        self.hates = []

    def make_network_message(self):
        return self.pack_string(self.user)

    def parse_network_message(self):
        self.user = self.unpack_string()
        likesnum = self.unpack_uint32()

        for _ in range(likesnum):
            key = self.unpack_string()
            self.likes.append(key)

        hatesnum = self.unpack_uint32()

        for _ in range(hatesnum):
            key = self.unpack_string()
            self.hates.append(key)


class AdminCommand(ServerMessage):
    """Server code 58.

    We send this to the server to run an admin command (e.g. to ban or
    silence a user) if we have admin status on the server.

    OBSOLETE, no longer functional
    """

    __slots__ = ("command", "command_args")
    CODE = 58

    def __init__(self, command=None, command_args=None):
        ServerMessage.__init__(self)
        self.command = command
        self.command_args = command_args

    def make_network_message(self):
        msg = bytearray()
        msg += self.pack_string(self.command)
        msg += self.pack_uint32(len(self.command_args))

        for arg in self.command_args:
            msg += self.pack_string(arg)

        return msg


class PlaceInLineRequest(ServerMessage):
    """Server code 59.

    OBSOLETE, superseded by PlaceInQueueRequest peer message
    """

    __slots__ = ("user", "token")
    CODE = 59

    def __init__(self, user=None, token=None, *, msg_content=None):
        ServerMessage.__init__(self, msg_content)
        self.token = token
        self.user = user

    def make_network_message(self):
        msg = bytearray()
        msg += self.pack_string(self.user)
        msg += self.pack_uint32(self.token)

        return msg

    def parse_network_message(self):
        self.user = self.unpack_string()
        self.token = self.unpack_uint32()


class PlaceInLineResponse(ServerMessage):
    """Server code 60.

    The server sends this to indicate change in place in queue while
    we're waiting for files from another peer.

    OBSOLETE, superseded by PlaceInQueueResponse peer message
    """

    __slots__ = ("token", "user", "place")
    CODE = 60

    def __init__(self, user=None, token=None, place=None, *, msg_content=None):
        ServerMessage.__init__(self, msg_content)
        self.token = token
        self.user = user
        self.place = place

    def make_network_message(self):
        msg = bytearray()
        msg += self.pack_string(self.user)
        msg += self.pack_uint32(self.token)
        msg += self.pack_uint32(self.place)

        return msg

    def parse_network_message(self):
        self.user = self.unpack_string()
        self.token = self.unpack_uint32()
        self.place = self.unpack_uint32()


class RoomAdded(ServerMessage):
    """Server code 62.

    The server tells us a new room has been added.

    OBSOLETE, no longer sent by the server
    """

    __slots__ = ("room",)
    CODE = 62

    def __init__(self, *, msg_content=None):
        ServerMessage.__init__(self, msg_content)
        self.room = None

    def parse_network_message(self):
        self.room = self.unpack_string()


class RoomRemoved(ServerMessage):
    """Server code 63.

    The server tells us a room has been removed.

    OBSOLETE, no longer sent by the server
    """

    __slots__ = ("room",)
    CODE = 63

    def __init__(self, *, msg_content=None):
        ServerMessage.__init__(self, msg_content)
        self.room = None

    def parse_network_message(self):
        self.room = self.unpack_string()


class RoomList(ServerMessage):
    """Server code 64.

    The server tells us a list of rooms and the number of users in them.
    When connecting to the server, the server only sends us rooms with
    at least 5 users. A few select rooms are also excluded, such as
    nicotine and The Lobby. Requesting the room list yields a response
    containing the missing rooms.
    """

    __slots__ = ("rooms", "rooms_owner", "rooms_member", "rooms_operator")
    CODE = 64
    EVENT_NAME = "room-list"

    def __init__(self, *, msg_content=None):
        ServerMessage.__init__(self, msg_content)
        self.rooms = []
        self.rooms_owner = []
        self.rooms_member = []
        self.rooms_operator = []

    def make_network_message(self):
        return b""

    def parse_rooms(self, has_count=True):
        numrooms = self.unpack_uint32()

        rooms = []
        for i in range(numrooms):
            room = self.unpack_string()

            if has_count:
                rooms.append([room, None])
            else:
                rooms.append(room)

        if not has_count:
            return rooms

        numusers = self.unpack_uint32()

        for i in range(numusers):
            rooms[i][1] = self.unpack_uint32()

        return rooms

    def parse_network_message(self):
        self.rooms = self.parse_rooms()
        self.rooms_owner = self.parse_rooms()
        self.rooms_member = self.parse_rooms()
        self.rooms_operator = self.parse_rooms(has_count=False)


class ExactFileSearch(ServerMessage):
    """Server code 65.

    We send this to search for an exact file name and folder, to find
    other sources.

    OBSOLETE, no results even with official client
    """

    __slots__ = ("token", "file_path", "folder_path", "file_size", "checksum", "user", "unknown")
    CODE = 65

    def __init__(self, token=None, file_path=None, folder_path=None, file_size=None, checksum=None,
                 unknown=None, *, msg_content=None):
        ServerMessage.__init__(self, msg_content)
        self.token = token
        self.file_path = file_path
        self.folder_path = folder_path
        self.file_size = file_size
        self.checksum = checksum
        self.unknown = unknown
        self.user = None

    def make_network_message(self):
        msg = bytearray()
        msg += self.pack_uint32(self.token)
        msg += self.pack_string(self.file_path)
        msg += self.pack_string(self.folder_path)
        msg += self.pack_uint64(self.file_size)
        msg += self.pack_uint32(self.checksum)
        msg += self.pack_uint8(self.unknown)

        return msg

    def parse_network_message(self):
        self.user = self.unpack_string()
        self.token = self.unpack_uint32()
        self.file_path = self.unpack_string()
        self.folder_path = self.unpack_string()
        self.file_size = self.unpack_uint64()
        self.checksum = self.unpack_uint32()


class AdminMessage(ServerMessage):
    """Server code 66.

    A global message from the server admin has arrived.
    """

    __slots__ = ("msg",)
    CODE = 66
    EVENT_NAME = "admin-message"

    def __init__(self, *, msg_content=None):
        ServerMessage.__init__(self, msg_content)
        self.msg = None

    def parse_network_message(self):
        self.msg = self.unpack_string()


class GlobalUserList(ServerMessage):
    """Server code 67.

    We send this to get a global list of all users online.

    OBSOLETE, no longer used
    """

    __slots__ = ("users",)
    CODE = 67

    def __init__(self, *, msg_content=None):
        ServerMessage.__init__(self, msg_content)
        self.users = None

    def make_network_message(self):
        return b""

    def parse_network_message(self):
        self.users = self.parse_users()


class TunneledMessage(ServerMessage):
    """Server code 68.

    Server message for tunneling a chat message.

    OBSOLETE, no longer used
    """

    __slots__ = ("user", "token", "code", "msg", "addr")
    CODE = 68

    def __init__(self, user=None, token=None, code=None, msg=None, *, msg_content=None):
        ServerMessage.__init__(self, msg_content)
        self.user = user
        self.token = token
        self.code = code
        self.msg = msg
        self.addr = None

    def make_network_message(self):
        msg = bytearray()
        msg += self.pack_string(self.user)
        msg += self.pack_uint32(self.token)
        msg += self.pack_uint32(self.code)
        msg += self.pack_string(self.msg)

        return msg

    def parse_network_message(self):
        self.user = self.unpack_string()
        self.code = self.unpack_uint32()
        self.token = self.unpack_uint32()

        ip_address = self.unpack_ip()
        port = self.unpack_uint32()
        self.addr = (ip_address, port)

        self.msg = self.unpack_string()


class PrivilegedUsers(ServerMessage):
    """Server code 69.

    The server sends us a list of privileged users, a.k.a. users who
    have donated.
    """

    __slots__ = ("users",)
    CODE = 69
    EVENT_NAME = "privileged-users"

    def __init__(self, *, msg_content=None):
        ServerMessage.__init__(self, msg_content)
        self.users = []

    def parse_network_message(self):
        numusers = self.unpack_uint32()

        for _ in range(numusers):
            user = self.unpack_string()
            self.users.append(user)


class HaveNoParent(ServerMessage):
    """Server code 71.

    We inform the server if we have a distributed parent or not. If not, the
    server eventually sends us a PossibleParents message with a list of
    possible parents to connect to. If no candidates are found, no such
    message is sent by the server, and we eventually become a branch root
    (i.e. the server starts sending us EmbeddedMessage messages).
    """

    __slots__ = ("noparent",)
    CODE = 71

    def __init__(self, noparent=None):
        ServerMessage.__init__(self)
        self.noparent = noparent

    def make_network_message(self):
        return self.pack_bool(self.noparent)


class ParentIP(ServerMessage):
    """Server code 73.

    We tell the server the IP address of our parent in the distributed network.

    DEPRECATED, sent by Soulseek NS but not SoulseekQt
    """

    __slots__ = ("parentip",)
    CODE = 73

    def __init__(self, parentip=None):
        ServerMessage.__init__(self)
        self.parentip = parentip

    @staticmethod
    def strunreverse(string):
        strlist = string.split(".")
        strlist.reverse()
        return ".".join(strlist)

    def make_network_message(self):
        return self.pack_uint32(inet_aton(self.strunreverse(self.parentip)))


class ParentMinSpeed(ServerMessage):
    """Server code 83.

    The server informs us about the minimum upload speed required to
    become a parent in the distributed network.
    """

    __slots__ = ("speed",)
    CODE = 83

    def __init__(self, *, msg_content=None):
        ServerMessage.__init__(self, msg_content)
        self.speed = None

    def parse_network_message(self):
        self.speed = self.unpack_uint32()


class ParentSpeedRatio(ServerMessage):
    """Server code 84.

    The server sends us a speed ratio determining the number of children
    we can have in the distributed network. The maximum number of
    children is our upload speed divided by the speed ratio.
    """

    __slots__ = ("ratio",)
    CODE = 84

    def __init__(self, *, msg_content=None):
        ServerMessage.__init__(self, msg_content)
        self.ratio = None

    def parse_network_message(self):
        self.ratio = self.unpack_uint32()


class ParentInactivityTimeout(ServerMessage):
    """Server code 86.

    OBSOLETE, no longer sent by the server
    """

    __slots__ = ("seconds",)
    CODE = 86

    def __init__(self, *, msg_content=None):
        ServerMessage.__init__(self, msg_content)
        self.seconds = None

    def parse_network_message(self):
        self.seconds = self.unpack_uint32()


class SearchInactivityTimeout(ServerMessage):
    """Server code 87.

    OBSOLETE, no longer sent by the server
    """

    __slots__ = ("seconds",)
    CODE = 87

    def __init__(self, *, msg_content=None):
        ServerMessage.__init__(self, msg_content)
        self.seconds = None

    def parse_network_message(self):
        self.seconds = self.unpack_uint32()


class MinParentsInCache(ServerMessage):
    """Server code 88.

    OBSOLETE, no longer sent by the server
    """

    __slots__ = ("num",)
    CODE = 88

    def __init__(self, *, msg_content=None):
        ServerMessage.__init__(self, msg_content)
        self.num = None

    def parse_network_message(self):
        self.num = self.unpack_uint32()


class DistribPingInterval(ServerMessage):
    """Server code 90.

    OBSOLETE, no longer sent by the server
    """

    __slots__ = ("seconds",)
    CODE = 90

    def __init__(self, *, msg_content=None):
        ServerMessage.__init__(self, msg_content)
        self.seconds = None

    def parse_network_message(self):
        self.seconds = self.unpack_uint32()


class AddToPrivileged(ServerMessage):
    """Server code 91.

    The server sends us the username of a new privileged user, which we
    add to our list of global privileged users.

    OBSOLETE, no longer sent by the server
    """

    __slots__ = ("user",)
    CODE = 91

    def __init__(self, *, msg_content=None):
        ServerMessage.__init__(self, msg_content)
        self.user = None

    def parse_network_message(self):
        self.user = self.unpack_string()


class CheckPrivileges(ServerMessage):
    """Server code 92.

    We ask the server how much time we have left of our privileges. The
    server responds with the remaining time, in seconds.
    """

    __slots__ = ("seconds",)
    CODE = 92
    EVENT_NAME = "check-privileges"

    def __init__(self, *, msg_content=None):
        ServerMessage.__init__(self, msg_content)
        self.seconds = None

    def make_network_message(self):
        return b""

    def parse_network_message(self):
        self.seconds = self.unpack_uint32()


class EmbeddedMessage(ServerMessage):
    """Server code 93.

    The server sends us an embedded distributed message. The only sent message
    type is DistribSearch (distributed code 3). If we receive such a message,
    we are a branch root in the distributed network, and we distribute the
    unpacked message to our child peers.

    Note that older SoulseekQt versions incorrectly distributed the whole
    server message instead of the unpacked message, which resulted in other
    client implementations adopting this erroneous behavior. This bug was
    fixed in SoulseekQt in early 2026.

    Soulseek NS also distributes DistribBranchLevel and DistribBranchRoot
    messages, although the server doesn't send them, and increments the branch
    level before distribution. This is presumably a side effect of processing
    embedded messages as regular distributed messages, since SoulseekQt
    doesn't accept messages other than DistribSearch from the server.
    """

    __slots__ = ("distrib_code", "distrib_message")
    CODE = 93
    LOGGED = False

    def __init__(self, *, msg_content=None):
        ServerMessage.__init__(self, msg_content)
        self.distrib_code = None
        self.distrib_message = None

    def parse_network_message(self):
        self.distrib_code = self.unpack_uint8()
        self.distrib_message = self._message[self._offset:]


class AcceptChildren(ServerMessage):
    """Server code 100.

    We tell the server if we want to accept child nodes.
    """

    __slots__ = ("enabled",)
    CODE = 100

    def __init__(self, enabled=None):
        ServerMessage.__init__(self)
        self.enabled = enabled

    def make_network_message(self):
        return self.pack_bool(self.enabled)


class PossibleParents(ServerMessage):
    """Server code 102.

    The server send us a list of max 10 possible distributed parents to
    connect to. Messages of this type are sent to us at regular intervals,
    until we tell the server we don't need more possible parents with a
    HaveNoParent message.

    The received list always contains users whose upload speed is higher than
    our own. If we have the highest upload speed on the server, we become a
    branch root, and start receiving EmbeddedMessage messages directly from
    the server.
    """

    __slots__ = ("list",)
    CODE = 102

    def __init__(self, *, msg_content=None):
        ServerMessage.__init__(self, msg_content)
        self.list = {}

    def parse_network_message(self):
        num = self.unpack_uint32()

        for _ in range(num):
            username = self.unpack_string()
            ip_address = self.unpack_ip()
            port = self.unpack_uint32()

            self.list[username] = ParentCandidate(username, ip_address, port)


class WishlistSearch(ServerMessage):
    """Server code 103.

    We send the server one of our wishlist search queries at each
    interval.
    """

    __slots__ = ("token", "searchterm")
    CODE = 103

    def __init__(self, token=None, text=None):
        ServerMessage.__init__(self)
        self.token = token
        self.searchterm = text

    def make_network_message(self):
        msg = bytearray()
        msg += self.pack_uint32(self.token)
        msg += self.pack_string(self.searchterm)

        return msg


class WishlistInterval(ServerMessage):
    """Server code 104.

    The server tells us the wishlist search interval.
    """

    __slots__ = ("seconds",)
    CODE = 104
    EVENT_NAME = "set-wishlist-interval"

    def __init__(self, *, msg_content=None):
        ServerMessage.__init__(self, msg_content)
        self.seconds = None

    def parse_network_message(self):
        self.seconds = self.unpack_uint32()


class SimilarUsers(ServerMessage):
    """Server code 110.

    The server sends us a list of similar users related to our
    interests.
    """

    __slots__ = ("users",)
    CODE = 110
    EVENT_NAME = "similar-users"

    def __init__(self, *, msg_content=None):
        ServerMessage.__init__(self, msg_content)
        self.users = []

    def make_network_message(self):
        return b""

    def parse_network_message(self):
        num = self.unpack_uint32()

        for _ in range(num):
            self.users.append(
                SimilarUser(
                    username=self.unpack_string(),
                    rating=self.unpack_uint32()
                )
            )

        if num > 1:
            self.users.sort(key=lambda x: x.rating, reverse=True)


class ItemRecommendations(ServerMessage):
    """Server code 111.

    The server sends us a list of recommendations related to a specific
    item, which is usually present in the like/dislike list or an
    existing recommendation list.
    """

    __slots__ = ("thing", "recommendations", "unrecommendations")
    CODE = 111
    EVENT_NAME = "item-recommendations"

    def __init__(self, thing=None, *, msg_content=None):
        ServerMessage.__init__(self, msg_content)
        self.thing = thing
        self.recommendations = []
        self.unrecommendations = []

    def make_network_message(self):
        return self.pack_string(self.thing)

    def parse_network_message(self):
        self.thing = self.unpack_string()
        self.recommendations, self.unrecommendations = self.parse_recommendations()


class ItemSimilarUsers(ServerMessage):
    """Server code 112.

    The server sends us a list of similar users related to a specific
    item, which is usually present in the like/dislike list or
    recommendation list.
    """

    __slots__ = ("thing", "users")
    CODE = 112
    EVENT_NAME = "item-similar-users"

    def __init__(self, thing=None, *, msg_content=None):
        ServerMessage.__init__(self, msg_content)
        self.thing = thing
        self.users = []

    def make_network_message(self):
        return self.pack_string(self.thing)

    def parse_network_message(self):
        self.thing = self.unpack_string()
        num = self.unpack_uint32()

        for _ in range(num):
            self.users.append(SimilarUser(username=self.unpack_string()))


class RoomTickers(ServerMessage):
    """Server code 113.

    The server returns a list of tickers in a chat room.

    Tickers are customizable, user-specific messages that appear on chat
    room walls.
    """

    __slots__ = ("room", "user", "msgs")
    CODE = 113
    EVENT_NAME = "room-tickers"

    def __init__(self, *, msg_content=None):
        ServerMessage.__init__(self, msg_content)
        self.room = None
        self.user = None
        self.msgs = []

    def parse_network_message(self):
        self.room = self.unpack_string()
        num = self.unpack_uint32()

        for _ in range(num):
            user = self.unpack_string()
            msg = self.unpack_string()

            self.msgs.append((user, msg))


class RoomTickerAdded(ServerMessage):
    """Server code 114.

    The server sends us a new ticker that was added to a chat room.

    Tickers are customizable, user-specific messages that appear on chat
    room walls.
    """

    __slots__ = ("room", "user", "msg")
    CODE = 114
    EVENT_NAME = "room-ticker-added"

    def __init__(self, *, msg_content=None):
        ServerMessage.__init__(self, msg_content)
        self.room = None
        self.user = None
        self.msg = None

    def parse_network_message(self):
        self.room = self.unpack_string()
        self.user = self.unpack_string()
        self.msg = self.unpack_string()


class RoomTickerRemoved(ServerMessage):
    """Server code 115.

    The server informs us that a ticker was removed from a chat room.

    Tickers are customizable, user-specific messages that appear on chat
    room walls.
    """

    __slots__ = ("room", "user")
    CODE = 115
    EVENT_NAME = "room-ticker-removed"

    def __init__(self, *, msg_content=None):
        ServerMessage.__init__(self, msg_content)
        self.room = None
        self.user = None

    def parse_network_message(self):
        self.room = self.unpack_string()
        self.user = self.unpack_string()


class SetRoomTicker(ServerMessage):
    """Server code 116.

    We send this to the server when we change our own ticker in a chat
    room. Sending an empty ticker string removes any existing ticker in
    the room.

    Tickers are customizable, user-specific messages that appear on chat
    room walls.
    """

    __slots__ = ("room", "msg")
    CODE = 116

    def __init__(self, room=None, msg=""):
        ServerMessage.__init__(self)
        self.room = room
        self.msg = msg

    def make_network_message(self):
        msg = bytearray()
        msg += self.pack_string(self.room)
        msg += self.pack_string(self.msg)

        return msg


class AddThingIHate(ServerMessage):
    """Server code 117.

    We send this to the server when we add an item to our hate list.
    """

    __slots__ = ("thing",)
    CODE = 117

    def __init__(self, thing=None):
        ServerMessage.__init__(self)
        self.thing = thing

    def make_network_message(self):
        return self.pack_string(self.thing)


class RemoveThingIHate(ServerMessage):
    """Server code 118.

    We send this to the server when we remove an item from our hate
    list.
    """

    __slots__ = ("thing",)
    CODE = 118

    def __init__(self, thing=None):
        ServerMessage.__init__(self)
        self.thing = thing

    def make_network_message(self):
        return self.pack_string(self.thing)


class RoomSearch(ServerMessage):
    """Server code 120.

    We send this to the server to search files shared by users who have
    joined a specific chat room. The token is a number generated by the
    client and is used to track the search results.

    Room users receive the search request in the form of a FileSearch
    message.
    """

    __slots__ = ("room", "token", "searchterm")
    CODE = 120

    def __init__(self, room=None, token=None, text=""):
        ServerMessage.__init__(self)
        self.room = room
        self.token = token
        self.searchterm = text

    def make_network_message(self):
        msg = bytearray()
        msg += self.pack_string(self.room)
        msg += self.pack_uint32(self.token)
        msg += self.pack_string(self.searchterm)

        return msg


class SendUploadSpeed(ServerMessage):
    """Server code 121.

    We send this after a finished upload to let the server update the
    speed statistics for ourselves.
    """

    __slots__ = ("speed",)
    CODE = 121

    def __init__(self, speed=None):
        ServerMessage.__init__(self)
        self.speed = speed

    def make_network_message(self):
        return self.pack_uint32(self.speed)


class UserPrivileged(ServerMessage):
    """Server code 122.

    We ask the server whether a user is privileged or not.

    DEPRECATED, use WatchUser and GetUserStatus server messages
    """

    __slots__ = ("user", "privileged")
    CODE = 122

    def __init__(self, user=None, *, msg_content=None):
        ServerMessage.__init__(self, msg_content)
        self.user = user
        self.privileged = None

    def make_network_message(self):
        return self.pack_string(self.user)

    def parse_network_message(self):
        self.user = self.unpack_string()
        self.privileged = self.unpack_bool()


class GivePrivileges(ServerMessage):
    """Server code 123.

    We give (part of) our privileges, specified in days, to another user
    on the network.
    """

    __slots__ = ("user", "days")
    CODE = 123

    def __init__(self, user=None, days=None):
        ServerMessage.__init__(self)
        self.user = user
        self.days = days

    def make_network_message(self):
        msg = bytearray()
        msg += self.pack_string(self.user)
        msg += self.pack_uint32(self.days)

        return msg


class NotifyPrivileges(ServerMessage):
    """Server code 124.

    DEPRECATED, sent by Soulseek NS but not SoulseekQt
    """

    __slots__ = ("token", "user")
    CODE = 124

    def __init__(self, token=None, user=None, *, msg_content=None):
        ServerMessage.__init__(self, msg_content)
        self.token = token
        self.user = user

    def make_network_message(self):
        msg = bytearray()
        msg += self.pack_uint32(self.token)
        msg += self.pack_string(self.user)

        return msg

    def parse_network_message(self):
        self.token = self.unpack_uint32()
        self.user = self.unpack_string()


class AckNotifyPrivileges(ServerMessage):
    """Server code 125.

    DEPRECATED, no longer used
    """

    __slots__ = ("token",)
    CODE = 125

    def __init__(self, token=None, *, msg_content=None):
        ServerMessage.__init__(self, msg_content)
        self.token = token

    def make_network_message(self):
        return self.pack_uint32(self.token)

    def parse_network_message(self):
        self.token = self.unpack_uint32()


class BranchLevel(ServerMessage):
    """Server code 126.

    We tell the server what our position is in our branch (nth generation) in
    the distributed network.
    """

    __slots__ = ("value",)
    CODE = 126

    def __init__(self, value=None):
        ServerMessage.__init__(self)
        self.value = value

    def make_network_message(self):
        return self.pack_uint32(self.value)


class BranchRoot(ServerMessage):
    """Server code 127.

    We tell the server the username of the root of the branch we’re in in the
    distributed network.
    """

    __slots__ = ("user",)
    CODE = 127

    def __init__(self, user=None):
        ServerMessage.__init__(self)
        self.user = user

    def make_network_message(self):
        return self.pack_string(self.user)


class ChildDepth(ServerMessage):
    """Server code 129.

    When we are a branch root in the distributed network, and receive a
    DistribChildDepth message from a child peer, we increment the depth and
    send this final value to the server.

    This message is obsolete. While Soulseek NS sends the correct value to the
    server, SoulseekQt doesn't implement this message correctly, always sending
    a uint8 value of 1 instead. Presumably, the server has opted to calculate
    child depths on its own, based on branch level/root information sent by
    peers.

    OBSOLETE, no longer used
    """

    __slots__ = ("value",)
    CODE = 129

    def __init__(self, value=None):
        ServerMessage.__init__(self)
        self.value = value

    def make_network_message(self):
        return self.pack_uint32(self.value)


class ResetDistributed(ServerMessage):
    """Server code 130.

    The server asks us to reset our distributed parent and children.
    """

    __slots__ = ()
    CODE = 130

    def parse_network_message(self):
        # Empty message
        pass


class RoomMembers(ServerMessage):
    """Server code 133.

    The server sends us a list of members (excluding the owner) in a private
    room we are in.
    """

    __slots__ = ("room", "members")
    CODE = 133
    EVENT_NAME = "room-members"

    def __init__(self, *, msg_content=None):
        ServerMessage.__init__(self, msg_content)
        self.room = None
        self.members = []

    def parse_network_message(self):
        self.room = self.unpack_string()
        num_members = self.unpack_uint32()

        for _ in range(num_members):
            user = self.unpack_string()
            self.members.append(user)


class AddRoomMember(ServerMessage):
    """Server code 134.

    We send this to the server to add a member to a private room, if we are
    the owner or an operator.

    The server tells us a member has been added to a private room we are in.
    """

    __slots__ = ("room", "user")
    CODE = 134
    EVENT_NAME = "add-room-member"

    def __init__(self, room=None, user=None, *, msg_content=None):
        ServerMessage.__init__(self, msg_content)
        self.room = room
        self.user = user

    def make_network_message(self):
        msg = bytearray()
        msg += self.pack_string(self.room)
        msg += self.pack_string(self.user)

        return msg

    def parse_network_message(self):
        self.room = self.unpack_string()
        self.user = self.unpack_string()


class RemoveRoomMember(ServerMessage):
    """Server code 135.

    We send this to the server to remove a member from a private room, if we
    are the owner or an operator. Owners can remove operators and regular
    members, operators can only remove regular members.

    The server tells us a member has been removed from a private room we are in.
    """

    __slots__ = ("room", "user")
    CODE = 135
    EVENT_NAME = "remove-room-member"

    def __init__(self, room=None, user=None, *, msg_content=None):
        ServerMessage.__init__(self, msg_content)
        self.room = room
        self.user = user

    def make_network_message(self):
        msg = bytearray()
        msg += self.pack_string(self.room)
        msg += self.pack_string(self.user)

        return msg

    def parse_network_message(self):
        self.room = self.unpack_string()
        self.user = self.unpack_string()


class CancelRoomMembership(ServerMessage):
    """Server code 136.

    We send this to the server to cancel our own membership of a private room.
    """

    __slots__ = ("room",)
    CODE = 136

    def __init__(self, room=None):
        ServerMessage.__init__(self)
        self.room = room

    def make_network_message(self):
        return self.pack_string(self.room)


class CancelRoomOwnership(ServerMessage):
    """Server code 137.

    We send this to the server to stop owning a private room.
    """

    __slots__ = ("room",)
    CODE = 137

    def __init__(self, room=None):
        ServerMessage.__init__(self)
        self.room = room

    def make_network_message(self):
        return self.pack_string(self.room)


class RoomSomething(ServerMessage):
    """Server code 138.

    OBSOLETE, no longer used
    """

    __slots__ = ("room",)
    CODE = 138

    def __init__(self, room=None, *, msg_content=None):
        ServerMessage.__init__(self, msg_content)
        self.room = room

    def make_network_message(self):
        return self.pack_string(self.room)

    def parse_network_message(self):
        self.room = self.unpack_string()


class RoomMembershipGranted(ServerMessage):
    """Server code 139.

    The server tells us we were added to a private room.
    """

    __slots__ = ("room",)
    CODE = 139
    EVENT_NAME = "room-membership-granted"

    def __init__(self, room=None, *, msg_content=None):
        ServerMessage.__init__(self, msg_content)
        self.room = room

    def parse_network_message(self):
        self.room = self.unpack_string()


class RoomMembershipRevoked(ServerMessage):
    """Server code 140.

    The server tells us we were removed from a private room.
    """

    __slots__ = ("room",)
    CODE = 140
    EVENT_NAME = "room-membership-revoked"

    def __init__(self, room=None, *, msg_content=None):
        ServerMessage.__init__(self, msg_content)
        self.room = room

    def parse_network_message(self):
        self.room = self.unpack_string()


class EnableRoomInvitations(ServerMessage):
    """Server code 141.

    We send this when we want to enable or disable invitations to
    private rooms.
    """

    __slots__ = ("enabled",)
    CODE = 141
    EVENT_NAME = "enable-room-invitations"

    def __init__(self, enabled=None, *, msg_content=None):
        ServerMessage.__init__(self, msg_content)
        self.enabled = enabled

    def make_network_message(self):
        return self.pack_bool(self.enabled)

    def parse_network_message(self):
        self.enabled = self.unpack_bool()


class ChangePassword(ServerMessage):
    """Server code 142.

    We send this to the server to change our password. We receive a
    response if our password changes.
    """

    __slots__ = ("password",)
    CODE = 142
    EVENT_NAME = "change-password"
    HIDDEN_FIELDS = {"password"}

    def __init__(self, password=None, *, msg_content=None):
        ServerMessage.__init__(self, msg_content)
        self.password = password

    def make_network_message(self):
        return self.pack_string(self.password)

    def parse_network_message(self):
        self.password = self.unpack_string()


class AddRoomOperator(ServerMessage):
    """Server code 143.

    We send this to the server to add private room operator abilities to
    a member.

    The server tells us a member received operator abilities in a private
    room we are in.
    """

    __slots__ = ("room", "user")
    CODE = 143
    EVENT_NAME = "add-room-operator"

    def __init__(self, room=None, user=None, *, msg_content=None):
        ServerMessage.__init__(self, msg_content)
        self.room = room
        self.user = user

    def make_network_message(self):
        msg = bytearray()
        msg += self.pack_string(self.room)
        msg += self.pack_string(self.user)

        return msg

    def parse_network_message(self):
        self.room = self.unpack_string()
        self.user = self.unpack_string()


class RemoveRoomOperator(ServerMessage):
    """Server code 144.

    We send this to the server to remove private room operator abilities
    from a member.

    The server tells us operator abilities were removed for a member in a
    private room we are in.
    """

    __slots__ = ("room", "user")
    CODE = 144
    EVENT_NAME = "remove-room-operator"

    def __init__(self, room=None, user=None, *, msg_content=None):
        ServerMessage.__init__(self, msg_content)
        self.room = room
        self.user = user

    def make_network_message(self):
        msg = bytearray()
        msg += self.pack_string(self.room)
        msg += self.pack_string(self.user)

        return msg

    def parse_network_message(self):
        self.room = self.unpack_string()
        self.user = self.unpack_string()


class RoomOperatorshipGranted(ServerMessage):
    """Server code 145.

    The server tells us we were given operator abilities in a private room
    we are in.
    """

    __slots__ = ("room",)
    CODE = 145
    EVENT_NAME = "room-operatorship-granted"

    def __init__(self, room=None, *, msg_content=None):
        ServerMessage.__init__(self, msg_content)
        self.room = room

    def parse_network_message(self):
        self.room = self.unpack_string()


class RoomOperatorshipRevoked(ServerMessage):
    """Server code 146.

    The server tells us our operator abilities were removed in a private room
    we are in.
    """

    __slots__ = ("room",)
    CODE = 146
    EVENT_NAME = "room-operatorship-revoked"

    def __init__(self, room=None, *, msg_content=None):
        ServerMessage.__init__(self, msg_content)
        self.room = room

    def make_network_message(self):
        return self.pack_string(self.room)

    def parse_network_message(self):
        self.room = self.unpack_string()


class RoomOperators(ServerMessage):
    """Server code 148.

    The server sends us a list of operators in a private room we are in.
    """

    __slots__ = ("room", "operators")
    CODE = 148
    EVENT_NAME = "room-operators"

    def __init__(self, *, msg_content=None):
        ServerMessage.__init__(self, msg_content)
        self.room = None
        self.operators = []

    def parse_network_message(self):
        self.room = self.unpack_string()
        num_operators = self.unpack_uint32()

        for _ in range(num_operators):
            user = self.unpack_string()
            self.operators.append(user)


class MessageUsers(ServerMessage):
    """Server code 149.

    Sends a broadcast private message to the given list of online users.
    """

    __slots__ = ("users", "msg")
    CODE = 149

    def __init__(self, users=None, msg=None):
        ServerMessage.__init__(self)
        self.users = users
        self.msg = msg

    def make_network_message(self):
        msg = bytearray()
        msg += self.pack_uint32(len(self.users))

        for user in self.users:
            msg += self.pack_string(user)

        msg += self.pack_string(self.msg)
        return msg


class JoinGlobalRoom(ServerMessage):
    """Server code 150.

    We ask the server to send us messages from all public rooms, also
    known as public room feed.
    """

    __slots__ = ()
    CODE = 150

    def __init__(self):
        ServerMessage.__init__(self)

    def make_network_message(self):
        return b""


class LeaveGlobalRoom(ServerMessage):
    """Server code 151.

    We ask the server to stop sending us messages from all public rooms,
    also known as public room feed.
    """

    __slots__ = ()
    CODE = 151

    def __init__(self):
        ServerMessage.__init__(self)

    def make_network_message(self):
        return b""


class GlobalRoomMessage(ServerMessage):
    """Server code 152.

    The server sends this when a new message has been written in the
    public room feed (every single line written in every public room).
    """

    __slots__ = ("room", "user", "message", "message_type", "mention_type", "mention_keyword")
    CODE = 152
    EVENT_NAME = "global-room-message"

    def __init__(self, *, msg_content=None):
        ServerMessage.__init__(self, msg_content)
        self.room = None
        self.user = None
        self.message = None
        self.message_type = None
        self.mention_type = None
        self.mention_keyword = None

    def parse_network_message(self):
        self.room = self.unpack_string()
        self.user = self.unpack_string()
        self.message = self.unpack_string()


class RelatedSearch(ServerMessage):
    """Server code 153.

    The server returns a list of related search terms for a search
    query.

    OBSOLETE, server sends empty list as of 2018
    """

    __slots__ = ("query", "terms")
    CODE = 153

    def __init__(self, query=None, *, msg_content=None):
        ServerMessage.__init__(self, msg_content)
        self.query = query
        self.terms = []

    def make_network_message(self):
        return self.pack_string(self.query)

    def parse_network_message(self):
        self.query = self.unpack_string()
        num = self.unpack_uint32()

        for _ in range(num):
            term = self.unpack_string()
            score = self.unpack_uint32()

            self.terms.append((term, score))


class ExcludedSearchPhrases(ServerMessage):
    """Server code 160.

    The server sends a list of phrases not allowed on the search network.
    File paths containing such phrases should be excluded when responding
    to search requests.
    """

    __slots__ = ("phrases",)
    CODE = 160
    EVENT_NAME = "excluded-search-phrases"

    def __init__(self, *, msg_content=None):
        ServerMessage.__init__(self, msg_content)
        self.phrases = []

    def parse_network_message(self):
        num = self.unpack_uint32()

        for _ in range(num):
            phrase = self.unpack_string()
            self.phrases.append(phrase)


class CantConnectToPeer(ServerMessage):
    """Server code 1001.

    We send this when we are not able to respond to an indirect connection
    request. We receive this if a peer was not able to respond to our
    indirect connection request. The token is taken from the ConnectToPeer
    message.

    Do not rely on receiving this message from peers. Keep a local timeout
    for indirect connections as well.
    """

    __slots__ = ("token", "user")
    CODE = 1001

    def __init__(self, token=None, user=None, *, msg_content=None):
        ServerMessage.__init__(self, msg_content)
        self.token = token
        self.user = user

    def make_network_message(self):
        msg = bytearray()
        msg += self.pack_uint32(self.token)
        msg += self.pack_string(self.user)

        return msg

    def parse_network_message(self):
        self.token = self.unpack_uint32()


class CantCreateRoom(ServerMessage):
    """Server code 1003.

    Server tells us a new room cannot be created. This message only
    seems to be sent if we try to create a room with the same name as
    an existing private room. In other cases, such as using a room name
    with leading or trailing spaces, only a private message containing
    an error message is sent.
    """

    __slots__ = ("room",)
    CODE = 1003

    def __init__(self, *, msg_content=None):
        ServerMessage.__init__(self, msg_content)
        self.room = None

    def parse_network_message(self):
        self.room = self.unpack_string()


# Peer Init Messages #


class PeerInitMessage(SlskMessage):
    __slots__ = ()
    TYPE = MessageType.INIT


class PierceFireWall(PeerInitMessage):
    """Peer init code 0.

    This message is sent in response to an indirect connection request
    from another user. If the message goes through to the user, the
    connection is ready. The token is taken from the ConnectToPeer
    server message.
    """

    __slots__ = ("sock", "token")
    CODE = 0

    def __init__(self, sock=None, token=None, *, msg_content=None):
        PeerInitMessage.__init__(self, msg_content)
        self.sock = sock
        self.token = token

    def make_network_message(self):
        return self.pack_uint32(self.token)

    def parse_network_message(self):
        self.token = self.unpack_uint32()


class PeerInit(PeerInitMessage):
    """Peer init code 1.

    This message is sent to initiate a direct connection to another peer. The
    token is always zero and ignored today, but used to be non-zero and
    included in a concurrent SendConnectToken server message for connection
    verification.
    """

    __slots__ = ("sock", "init_user", "target_user", "conn_type", "target_username_size",
                 "indirect_token", "indirect_request_time", "outgoing_msgs")
    CODE = 1

    def __init__(self, sock=None, init_user=None, target_user=None, conn_type=None, *, msg_content=None):
        PeerInitMessage.__init__(self, msg_content)
        self.sock = sock
        self.init_user = init_user        # our own username
        self.target_user = target_user    # username of peer we're connected to
        self.conn_type = conn_type
        self.target_username_size = None  # in bytes
        self.indirect_token = None
        self.indirect_request_time = None
        self.outgoing_msgs = []

    def make_network_message(self):
        msg = bytearray()
        msg += self.pack_string(self.init_user)
        msg += self.pack_string(self.conn_type)
        msg += self.pack_uint32(0)  # Empty token

        return msg

    def parse_network_message(self):
        self.target_user = self.unpack_string()
        self.target_username_size = self._offset - 4
        self.conn_type = self.unpack_string()


# Peer Messages #


class PeerMessage(SlskMessage):

    __slots__ = ("username", "sock", "addr", "allowed_responses")
    TYPE = MessageType.PEER

    def __init__(self, msg_content=None):
        SlskMessage.__init__(self, msg_content)
        self.username = None
        self.sock = None
        self.addr = None
        self.allowed_responses = set()

    def unpack_file_size(self):

        if self._message[self._offset + 7] == 255:
            # Soulseek NS bug: >2 GiB files show up as ~16 EiB when unpacking the size
            # as uint64 (8 bytes), due to the first 4 bytes containing the size, and the
            # last 4 bytes containing garbage (a value of 4294967295 bytes, integer limit).
            # Only unpack the first 4 bytes to work around this issue.

            size = self.unpack_uint32()
            self._offset += 4

        else:
            # Everything looks fine, parse size as usual
            size = self.unpack_uint64()

        return size

    def unpack_file_attributes(self):

        attributes = FileAttributes()
        num_attributes = self.unpack_uint32()

        for _ in range(num_attributes):
            attribute = self.unpack_uint32()
            value = self.unpack_uint32()

            if attribute == FileAttribute.BITRATE:
                attributes.bitrate = value

            elif attribute == FileAttribute.LENGTH:
                attributes.length = value

            elif attribute == FileAttribute.VBR:
                attributes.vbr = value

            elif attribute == FileAttribute.SAMPLE_RATE:
                attributes.sample_rate = value

            elif attribute == FileAttribute.BIT_DEPTH:
                attributes.bit_depth = value

        return attributes


class SharedFileListRequest(PeerMessage):
    """Peer code 4.

    We send this to a peer to ask for a list of shared files.
    """

    __slots__ = ()
    CODE = 4
    EVENT_NAME = "shared-file-list-request"

    def make_network_message(self):
        return b""

    def parse_network_message(self):
        # Empty message
        pass


class SharedFileListResponse(PeerMessage):
    """Peer code 5.

    A peer responds with a list of shared files when we've sent a
    SharedFileListRequest.
    """

    __slots__ = ("list", "unknown", "private_list", "built", "permission_level",
                 "public_shares", "buddy_shares", "trusted_shares")
    CODE = 5
    EVENT_NAME = "shared-file-list-response"
    HIDDEN_FIELDS = {"list", "private_list", "built"}

    def __init__(self, public_shares=None, buddy_shares=None, trusted_shares=None,
                 permission_level=None, *, msg_content=None):
        PeerMessage.__init__(self, msg_content)
        self.public_shares = public_shares
        self.buddy_shares = buddy_shares
        self.trusted_shares = trusted_shares
        self.permission_level = permission_level
        self.list = []
        self.private_list = []
        self.unknown = 0
        self.built = None

    def _make_shares_list(self, share_groups):

        try:
            msg_list = bytearray()
            num_folders = 0

            for shares in share_groups:
                num_folders += len(shares)

            msg_list += self.pack_uint32(num_folders)

            for shares in share_groups:
                for key in shares:
                    msg_list += self.pack_string(key)
                    msg_list += shares[key]

        except Exception as error:
            msg_list = self.pack_uint32(0)
            log.add(_("Unable to read shares database. Please rescan your shares. Error: %s"), error)

        return msg_list

    def make_network_message(self):
        # Elaborate hack to save CPU
        # Store packed message contents in self.built, and use instead of repacking it
        if self.built is not None:
            return self.built

        from pynicotine.shares import PermissionLevel

        msg = bytearray()
        share_groups = []
        private_share_groups = []

        if self.permission_level and self.public_shares:
            share_groups.append(self.public_shares)

        if self.permission_level in {PermissionLevel.BUDDY, PermissionLevel.TRUSTED} and self.buddy_shares:
            share_groups.append(self.buddy_shares)

        if self.permission_level == PermissionLevel.TRUSTED and self.trusted_shares:
            share_groups.append(self.trusted_shares)

        msg += self._make_shares_list(share_groups)

        # Unknown purpose, but official clients always send a value of 0
        msg += self.pack_uint32(self.unknown)

        for shares in (self.buddy_shares, self.trusted_shares):
            if shares and shares not in share_groups:
                private_share_groups.append(shares)

        msg += self._make_shares_list(share_groups=private_share_groups)

        self.built = zlib.compress(msg, ZLIB_COMPRESSION_LEVEL)
        return self.built

    def _parse_result_list(self):
        num_folders = self.unpack_uint32()
        file_extension = None
        shares = []

        for _ in range(num_folders):
            folder_path = self.unpack_string()
            num_files = self.unpack_uint32()
            files = []

            for _ in range(num_files):
                code = self.unpack_uint8()
                basename = self.unpack_string()
                file_size = self.unpack_file_size()
                file_extension_len = self.unpack_uint32()  # Obsolete, ignore
                self._offset += file_extension_len
                file_attributes = self.unpack_file_attributes()

                files.append((code, basename, file_size, file_extension, file_attributes))

            if num_files > 1:
                files.sort(key=itemgetter(1))

            shares.append((folder_path, files))

        if num_folders > 1:
            shares.sort(key=itemgetter(0))

        return shares

    def parse_network_message(self):
        decompressor = zlib.decompressobj()
        max_uncompressed_size = 2147483648  # 2 GiB total
        self._message = memoryview(decompressor.decompress(self._message, max_uncompressed_size))

        if not decompressor.eof:
            raise ValueError("Compressed message invalid or too large")

        self.list = self._parse_result_list()

        if self.has_remaining_content():
            self.unknown = self.unpack_uint32()

        if self.has_remaining_content():
            self.private_list = self._parse_result_list()

    def parse_local_message(self):
        self._message = memoryview(self.make_network_message())
        self._offset = 0

        self.parse_network_message()


class FileSearchRequest(PeerMessage):
    """Peer code 8.

    We send this to the peer when we search for a file. Alternatively,
    the peer sends this to tell us it is searching for a file.

    OBSOLETE, superseded by UserSearch server message
    """

    __slots__ = ("token", "text", "searchterm")
    CODE = 8

    def __init__(self, token=None, text=None, *, msg_content=None):
        PeerMessage.__init__(self, msg_content)
        self.token = token
        self.text = text
        self.searchterm = None

    def make_network_message(self):
        msg = bytearray()
        msg += self.pack_uint32(self.token)
        msg += self.pack_string(self.text)

        return msg

    def parse_network_message(self):
        self.token = self.unpack_uint32()
        self.searchterm = self.unpack_string()


class FileSearchResponse(PeerMessage):
    """Peer code 9.

    A peer sends this message when it has a file search match. The token
    is taken from original FileSearch, UserSearch or RoomSearch server
    message.
    """

    __slots__ = ("search_username", "token", "list", "private_list", "slot_available",
                 "upload_speed", "num_queued_uploads", "unknown")
    CODE = 9
    EVENT_NAME = "file-search-response"
    HIDDEN_FIELDS = {"list", "private_list"}

    def __init__(self, search_username=None, token=None, shares=None, slot_available=None,
                 upload_speed=None, num_queued_uploads=None, private_shares=None, *, msg_content=None):
        PeerMessage.__init__(self, msg_content)
        self.search_username = search_username
        self.token = token
        self.list = shares
        self.private_list = private_shares
        self.slot_available = slot_available
        self.upload_speed = upload_speed
        self.num_queued_uploads = num_queued_uploads
        self.unknown = 0

    def make_network_message(self):
        msg = bytearray()
        msg += self.pack_string(self.search_username)
        msg += self.pack_uint32(self.token)
        msg += self.pack_uint32(len(self.list))

        for fileinfo in self.list:
            msg += FileListMessage.pack_file_info(fileinfo)

        msg += self.pack_bool(self.slot_available)
        msg += self.pack_uint32(self.upload_speed)
        msg += self.pack_uint32(self.num_queued_uploads)
        msg += self.pack_uint32(self.unknown)
        msg += self.pack_uint32(len(self.private_list))

        for fileinfo in self.private_list:
            msg += FileListMessage.pack_file_info(fileinfo)

        return zlib.compress(msg, ZLIB_COMPRESSION_LEVEL)

    def _parse_result_list(self):
        num_files = self.unpack_uint32()
        file_extension = None
        results = []

        for _ in range(num_files):
            code = self.unpack_uint8()
            file_path = self.unpack_string()
            file_size = self.unpack_file_size()
            file_extension_len = self.unpack_uint32()  # Obsolete, ignore
            self._offset += file_extension_len
            file_attributes = self.unpack_file_attributes()

            results.append((code, file_path, file_size, file_extension, file_attributes))

        if num_files > 1:
            results.sort(key=itemgetter(1))

        return results

    def parse_network_message(self):
        decompressor = zlib.decompressobj()
        self._message = memoryview(decompressor.decompress(self._message, 4))

        username_len = self.unpack_uint32()
        max_uncompressed_size = 134217728 - username_len - 8  # 128 MiB total

        if max_uncompressed_size <= 0:
            raise ValueError("Compressed message too large")

        self._offset = username_len
        self._message = memoryview(decompressor.decompress(decompressor.unconsumed_tail, username_len + 4))
        self.token = self.unpack_uint32()

        if self.token not in self.allowed_responses:
            return

        # Optimization: only decompress the rest of the message when needed
        self._offset = 0
        self._message = memoryview(decompressor.decompress(decompressor.unconsumed_tail, max_uncompressed_size))

        if not decompressor.eof:
            raise ValueError("Compressed message invalid or too large")

        self.list = self._parse_result_list()
        self.slot_available = self.unpack_bool()
        self.upload_speed = self.unpack_uint32()
        self.num_queued_uploads = self.unpack_uint32()

        if self.has_remaining_content():
            self.unknown = self.unpack_uint32()

        if self.has_remaining_content():
            self.private_list = self._parse_result_list()


class UserInfoRequest(PeerMessage):
    """Peer code 15.

    We ask the other peer to send us their user information, picture and
    all.
    """

    __slots__ = ()
    CODE = 15
    EVENT_NAME = "user-info-request"

    def make_network_message(self):
        return b""

    def parse_network_message(self):
        # Empty message
        pass


class UserInfoResponse(PeerMessage):
    """Peer code 16.

    A peer responds with this after we've sent a UserInfoRequest.
    """

    __slots__ = ("descr", "pic", "num_upload_slots", "num_queued_uploads", "slot_available",
                 "upload_permission", "has_pic")
    CODE = 16
    EVENT_NAME = "user-info-response"
    HIDDEN_FIELDS = {"pic"}

    def __init__(self, descr=None, pic=None, num_upload_slots=None, num_queued_uploads=None,
                 slot_available=None, upload_permission=None, *, msg_content=None):
        PeerMessage.__init__(self, msg_content)
        self.descr = descr
        self.pic = pic
        self.num_upload_slots = num_upload_slots
        self.num_queued_uploads = num_queued_uploads
        self.slot_available = slot_available
        self.upload_permission = upload_permission
        self.has_pic = None

    def make_network_message(self):
        msg = bytearray()
        msg += self.pack_string(self.descr)

        if self.pic is not None:
            msg += self.pack_bool(True)
            msg += self.pack_bytes(self.pic)
        else:
            msg += self.pack_bool(False)

        msg += self.pack_uint32(self.num_upload_slots)
        msg += self.pack_uint32(self.num_queued_uploads)
        msg += self.pack_bool(self.slot_available)
        msg += self.pack_uint32(self.upload_permission)

        return msg

    def parse_network_message(self):
        self.descr = self.unpack_string()
        self.has_pic = self.unpack_bool()

        if self.has_pic:
            self.pic = self.unpack_bytes()

        self.num_upload_slots = self.unpack_uint32()
        self.num_queued_uploads = self.unpack_uint32()
        self.slot_available = self.unpack_bool()

        # To prevent errors, ensure that >= 4 bytes are left. Museek+ incorrectly sends
        # slot_available as an integer, resulting in 3 bytes of garbage here.
        if len(self._message[self._offset:]) >= 4:
            self.upload_permission = self.unpack_uint32()


class FolderContentsRequest(PeerMessage):
    """Peer code 36.

    We ask the peer to send us the contents of a single folder.
    """

    __slots__ = ("folder_path", "token", "legacy_client")
    CODE = 36
    EVENT_NAME = "folder-contents-request"

    def __init__(self, folder_path=None, token=None, legacy_client=False, *, msg_content=None):
        PeerMessage.__init__(self, msg_content)
        self.folder_path = folder_path
        self.token = token
        self.legacy_client = legacy_client

    def make_network_message(self):
        msg = bytearray()
        msg += self.pack_uint32(self.token)
        msg += self.pack_string(self.folder_path, is_legacy=self.legacy_client)

        return msg

    def parse_network_message(self):
        self.token = self.unpack_uint32()
        self.folder_path = self.unpack_string()


class FolderContentsResponse(PeerMessage):
    """Peer code 37.

    A peer responds with the contents of a particular folder (with all
    subfolders) after we've sent a FolderContentsRequest.
    """

    __slots__ = ("folder_path", "token", "list")
    CODE = 37
    EVENT_NAME = "folder-contents-response"
    HIDDEN_FIELDS = {"list"}

    def __init__(self, folder_path=None, token=None, shares=None, *, msg_content=None):
        PeerMessage.__init__(self, msg_content)
        self.folder_path = folder_path
        self.token = token
        self.list = shares

    def make_network_message(self):
        msg = bytearray()
        msg += self.pack_uint32(self.token)
        msg += self.pack_string(self.folder_path)

        if self.list is not None:
            msg += self.pack_uint32(1)
            msg += self.pack_string(self.folder_path)

            # We already saved the folder contents as a bytearray when scanning our shares
            msg += self.list
        else:
            # No folder contents
            msg += self.pack_uint32(0)

        return zlib.compress(msg, ZLIB_COMPRESSION_LEVEL)

    def parse_network_message(self):
        decompressor = zlib.decompressobj()
        message_bytes = decompressor.decompress(self._message, 8)
        self._message = memoryview(message_bytes)

        self.token = self.unpack_uint32()
        folder_path_len = self.unpack_uint32()
        max_uncompressed_size = 134217728 - folder_path_len - 8  # 128 MiB total

        if max_uncompressed_size <= 0:
            raise ValueError("Compressed message too large")

        if folder_path_len:
            message_bytes += decompressor.decompress(decompressor.unconsumed_tail, folder_path_len)
            self._message = memoryview(message_bytes)

        self._offset = 4  # Skip token
        self.folder_path = self.unpack_string()

        if self.username + self.folder_path not in self.allowed_responses:
            return

        # Optimization: only decompress the rest of the message when needed
        self._offset = 0
        self._message = memoryview(decompressor.decompress(decompressor.unconsumed_tail, max_uncompressed_size))

        if not decompressor.eof:
            raise ValueError("Compressed message invalid or too large")

        num_folders = self.unpack_uint32()
        folders = {}

        for _ in range(num_folders):
            folder_path = self.unpack_string()
            num_files = self.unpack_uint32()
            file_extension = None
            folders[folder_path] = []

            for _ in range(num_files):
                code = self.unpack_uint8()
                basename = self.unpack_string()
                file_size = self.unpack_file_size()
                file_extension_len = self.unpack_uint32()  # Obsolete, ignore
                self._offset += file_extension_len
                file_attributes = self.unpack_file_attributes()

                folders[folder_path].append((code, basename, file_size, file_extension, file_attributes))

            if num_files > 1:
                folders[folder_path].sort(key=itemgetter(1))

        self.list = folders


class TransferRequest(PeerMessage):
    """Peer code 40.

    This message is sent by a peer once they are ready to start
    uploading a file. A TransferResponse message is expected from the
    recipient, either allowing or rejecting the upload attempt.

    This message was formerly used to send a download request (direction
    0) as well, but Nicotine+ >= 3.0.3, Museek+ and the official clients
    use the QueueUpload message for this purpose today.  Clients like
    slskd and Seeker still use this method for downloading, so we need to
    ensure we still understand such requests.
    """

    __slots__ = ("direction", "token", "file_path", "file_size")
    CODE = 40
    EVENT_NAME = "transfer-request"

    def __init__(self, direction=None, token=None, file_path=None, file_size=None, *, msg_content=None):
        PeerMessage.__init__(self, msg_content)
        self.direction = direction
        self.token = token
        self.file_path = file_path
        self.file_size = file_size

    def make_network_message(self):
        msg = bytearray()
        msg += self.pack_uint32(self.direction)
        msg += self.pack_uint32(self.token)
        msg += self.pack_string(self.file_path)

        if self.direction == TransferDirection.UPLOAD:
            msg += self.pack_uint64(self.file_size)

        return msg

    def parse_network_message(self):
        self.direction = self.unpack_uint32()
        self.token = self.unpack_uint32()
        self.file_path = self.unpack_string()

        if self.direction == TransferDirection.UPLOAD:
            self.file_size = self.unpack_uint64()


class TransferResponse(PeerMessage):
    """Peer code 41.

    Response to TransferRequest - We either accept the transfer request,
    or tell the reason for rejecting it.

    Note that accepting a download request is discouraged, since it allows
    a possibly spoofed peer to initialize the file transfer connection
    from their end. Reject the download request with a 'Queued' reason, add
    the ile to the upload queue, and start the next upload as usual, since
    it ensures a connection attempt to a valid user address provided by the
    server.
    """

    __slots__ = ("allowed", "token", "reason", "file_size")
    CODE = 41
    EVENT_NAME = "transfer-response"

    def __init__(self, allowed=None, reason=None, token=None, file_size=None, *, msg_content=None):
        PeerMessage.__init__(self, msg_content)
        self.allowed = allowed
        self.token = token
        self.reason = reason
        self.file_size = file_size

    def make_network_message(self):
        msg = bytearray()
        msg += self.pack_uint32(self.token)
        msg += self.pack_bool(self.allowed)

        if not self.allowed:
            msg += self.pack_string(self.reason)

        elif self.file_size is not None:
            msg += self.pack_uint64(self.file_size)

        return msg

    def parse_network_message(self):
        self.token = self.unpack_uint32()
        self.allowed = self.unpack_bool()

        if not self.allowed:
            self.reason = self.unpack_string()

        elif self.has_remaining_content():
            self.file_size = self.unpack_uint64()


class PlaceholdUpload(PeerMessage):
    """Peer code 42.

    OBSOLETE, no longer used
    """

    __slots__ = ("file_path",)
    CODE = 42

    def __init__(self, file_path=None, *, msg_content=None):
        PeerMessage.__init__(self, msg_content)
        self.file_path = file_path

    def make_network_message(self):
        return self.pack_string(self.file_path)

    def parse_network_message(self):
        self.file_path = self.unpack_string()


class QueueUpload(PeerMessage):
    """Peer code 43.

    This message is used to tell a peer that an upload should be queued
    on their end. Once the recipient is ready to transfer the requested
    file, they will send a TransferRequest to us.
    """

    __slots__ = ("file_path", "legacy_client")
    CODE = 43
    EVENT_NAME = "queue-upload"

    def __init__(self, file_path=None, legacy_client=False, *, msg_content=None):
        PeerMessage.__init__(self, msg_content)
        self.file_path = file_path
        self.legacy_client = legacy_client

    def make_network_message(self):
        return self.pack_string(self.file_path, is_legacy=self.legacy_client)

    def parse_network_message(self):
        self.file_path = self.unpack_string()


class PlaceInQueueResponse(PeerMessage):
    """Peer code 44.

    The peer replies with the upload queue placement of the requested
    file.
    """

    __slots__ = ("file_path", "place")
    CODE = 44
    EVENT_NAME = "place-in-queue-response"

    def __init__(self, file_path=None, place=None, *, msg_content=None):
        PeerMessage.__init__(self, msg_content)
        self.file_path = file_path
        self.place = place

    def make_network_message(self):
        msg = bytearray()
        msg += self.pack_string(self.file_path)
        msg += self.pack_uint32(self.place)

        return msg

    def parse_network_message(self):
        self.file_path = self.unpack_string()
        self.place = self.unpack_uint32()


class UploadFailed(PeerMessage):
    """Peer code 46.

    This message is sent whenever a file connection of an active upload
    closes. Soulseek NS clients can also send this message when a file
    cannot be read. The recipient either re-queues the upload (download
    on their end), or ignores the message if the transfer finished.
    """

    __slots__ = ("file_path",)
    CODE = 46
    EVENT_NAME = "upload-failed"

    def __init__(self, file_path=None, *, msg_content=None):
        PeerMessage.__init__(self, msg_content)
        self.file_path = file_path

    def make_network_message(self):
        return self.pack_string(self.file_path)

    def parse_network_message(self):
        self.file_path = self.unpack_string()


class UploadDenied(PeerMessage):
    """Peer code 50.

    This message is sent to reject QueueUpload attempts and previously
    queued files. The reason for rejection will appear in the transfer
    list of the recipient.
    """

    __slots__ = ("file_path", "reason")
    CODE = 50
    EVENT_NAME = "upload-denied"

    def __init__(self, file_path=None, reason=None, *, msg_content=None):
        PeerMessage.__init__(self, msg_content)
        self.file_path = file_path
        self.reason = reason

    def make_network_message(self):
        msg = bytearray()
        msg += self.pack_string(self.file_path)
        msg += self.pack_string(self.reason)

        return msg

    def parse_network_message(self):
        self.file_path = self.unpack_string()
        self.reason = self.unpack_string()


class PlaceInQueueRequest(PeerMessage):
    """Peer code 51.

    This message is sent when asking for the upload queue placement of a
    file.
    """

    __slots__ = ("file_path", "legacy_client")
    CODE = 51
    EVENT_NAME = "place-in-queue-request"

    def __init__(self, file_path=None, legacy_client=False, *, msg_content=None):
        PeerMessage.__init__(self, msg_content)
        self.file_path = file_path
        self.legacy_client = legacy_client

    def make_network_message(self):
        return self.pack_string(self.file_path, is_legacy=self.legacy_client)

    def parse_network_message(self):
        self.file_path = self.unpack_string()


class UploadQueueNotification(PeerMessage):
    """Peer code 52.

    This message is sent to inform a peer about an upload attempt
    initiated by us.

    DEPRECATED, sent by Soulseek NS but not SoulseekQt
    """

    __slots__ = ()
    CODE = 52

    def make_network_message(self):
        return b""

    def parse_network_message(self):
        return b""


class UnknownPeerMessage(PeerMessage):
    """Peer code 12547.

    UNKNOWN
    """

    __slots__ = ()
    CODE = 12547
    LOGGED = False

    def parse_network_message(self):
        # Empty message
        pass


# File Messages #


class FileMessage(SlskMessage):

    __slots__ = ("sock", "username")
    TYPE = MessageType.FILE

    def __init__(self, msg_content=None, sock=None):
        SlskMessage.__init__(self, msg_content)
        self.sock = sock
        self.username = None


class FileTransferInit(FileMessage):
    """We send this to a peer via a 'F' connection to tell them that we want to
    start uploading a file. The token is the same as the one previously included in the
    TransferRequest peer message.
    """

    __slots__ = ("token",)

    def __init__(self, token=None, *, msg_content=None):
        FileMessage.__init__(self, msg_content)
        self.token = token

    def make_network_message(self):
        return self.pack_uint32(self.token)

    def parse_network_message(self):
        self.token = self.unpack_uint32()


class FileOffset(FileMessage):
    """We send this to the uploading peer at the beginning of a 'F' connection,
    to tell them how many bytes of the file we've previously downloaded. If nothing
    was downloaded, the offset is 0.

    Note that the offset is intended for resuming previous file downloads, not
    downloading specific chunks of a file. Attempting to retrofit such
    functionality is a bad idea for several reasons:

    1. The protocol doesn't support hashing of file chunks for verification.
    2. Every download request occupies an upload slot, causing congestion if
       small chunks are requested from many users at once.
    3. Aborting an incomplete file transfer makes it appear as failed on the
       uploader's end, resulting in confusion.

    Note that Soulseek NS fails to read the size of an incomplete download if more
    than 2 GB of the file has been downloaded, and the download is resumed. In
    consequence, the client sends an invalid file offset of -1.
    """

    __slots__ = ("offset",)

    def __init__(self, sock=None, offset=None, *, msg_content=None):
        FileMessage.__init__(self, msg_content, sock)
        self.offset = offset

    def make_network_message(self):
        return self.pack_uint64(self.offset)

    def parse_network_message(self):
        self.offset = self.unpack_uint64()


# Distributed Messages #


class DistribMessage(SlskMessage):

    __slots__ = ("sock", "username")
    TYPE = MessageType.DISTRIBUTED

    def __init__(self, msg_content=None):
        SlskMessage.__init__(self, msg_content)
        self.sock = None
        self.username = None


class DistribPing(DistribMessage):
    """Distrib code 0.

    We ping our parent and children every minute.

    DEPRECATED, sent by Soulseek NS but not SoulseekQt
    """

    __slots__ = ()
    CODE = 0

    def make_network_message(self):
        return b""

    def parse_network_message(self):
        # Empty message
        pass


class DistribSearch(DistribMessage):
    """Distrib code 3.

    Search request that arrives through the distributed network. We distribute
    the raw message (including unknown message attributes) to our child peers.

    The first potential parent that sends us a search request in addition to
    branch root/level information becomes our actual parent. Some clients,
    such as Soulseek NS and earlier Nicotine+ versions, adopt a parent as soon
    as it sends the branch root/level information instead.

    Identifier is always the code point of ASCII character 1 (49). We reject
    messages that use any other value.
    """

    __slots__ = ("identifier", "search_username", "token", "searchterm")
    CODE = 3
    EVENT_NAME = "file-search-request-distributed"
    LOGGED = False

    def __init__(self, *, msg_content=None):
        DistribMessage.__init__(self, msg_content)
        self.identifier = None
        self.search_username = None
        self.token = None
        self.searchterm = None

    def parse_network_message(self):
        codepoint = self.unpack_uint32()
        self.identifier = chr(codepoint)
        self.search_username = self.unpack_string()
        self.token = self.unpack_uint32()
        self.searchterm = self.unpack_string()


class DistribBranchLevel(DistribMessage):
    """Distrib code 4.

    We tell our distributed children what our position is in our branch (nth
    generation) in the distributed network. Our branch level is the branch
    level from our parent incremented by one. If we are a branch root (i.e.
    the server sends us EmbeddedMessage messages), our branch level is 0
    instead.

    When connecting to potential parents, they send us this message. We record
    the information, and adopt the first parent that sends us a DistribSearch
    message in addition to branch root/level information.

    If we receive a branch level of 0 from a parent, we should mark the
    parent as our branch root. Due to incorrect behavior in older client
    versions, they aren't guaranteed to send a separate DistribBranchRoot
    message in this case.
    """

    __slots__ = ("level",)
    CODE = 4

    def __init__(self, level=None, *, msg_content=None):
        DistribMessage.__init__(self, msg_content)
        self.level = level

    def make_network_message(self):
        return self.pack_int32(self.level)

    def parse_network_message(self):
        self.level = self.unpack_int32()


class DistribBranchRoot(DistribMessage):
    """Distrib code 5.

    We tell our distributed children the username of the root of the branch
    we're in in the distributed network. If we are the branch root (i.e. the
    server sends us EmbeddedMessage messages), we send our own username.

    When connecting to potential parents, they send us this message. We record
    the information, and adopt the first parent that sends us a DistribSearch
    message in addition to branch root/level information.

    Note that SoulseekQt used to not send this message when becoming a branch
    root. This behavior was corrected in early 2026. We should always send the
    message regardless of our status in the distributed network.
    """

    __slots__ = ("root_username", "root_username_size")
    CODE = 5

    def __init__(self, root_username=None, *, msg_content=None):
        DistribMessage.__init__(self, msg_content)
        self.root_username = root_username
        self.root_username_size = None  # in bytes

    def make_network_message(self):
        return self.pack_string(self.root_username)

    def parse_network_message(self):
        self.root_username = self.unpack_string()
        self.root_username_size = self._offset - 4


class DistribChildDepth(DistribMessage):
    """Distrib code 7.

    When adopting a new parent, we send them this message with a child depth of
    zero. Our parent increments the depth, sends the message to their parent,
    who does the same, until it reaches the branch root, who sends the final
    child depth to the server in the form of a ChildDepth message.

    This message is obsolete, since SoulseekQt doesn't send it. Presumably, the
    server has opted to calculate child depths on its own, based on branch
    level/root information sent by peers.

    OBSOLETE, no longer used
    """

    __slots__ = ("value",)
    CODE = 7

    def __init__(self, value=None, *, msg_content=None):
        DistribMessage.__init__(self, msg_content)
        self.value = value

    def make_network_message(self):
        return self.pack_uint32(self.value)

    def parse_network_message(self):
        self.value = self.unpack_uint32()


class DistribEmbeddedMessage(DistribMessage):
    """Distrib code 93.

    A branch root sends us an embedded distributed message. When the embedded
    message type is DistribSearch (distributed code 3), we unpack and
    distribute the raw message to our child peers. All other message types
    are unsupported and ignored.

    Note that older SoulseekQt versions incorrectly distributed this message
    instead of the unpacked message, which resulted in other client
    implementations adopting this erroneous behavior. This bug was fixed in
    SoulseekQt in early 2026.

    DEPRECATED, accidentally sent by older SoulseekQt versions
    """

    __slots__ = ("distrib_code", "distrib_message")
    CODE = 93
    LOGGED = False

    def __init__(self, *, msg_content=None):
        DistribMessage.__init__(self, msg_content)
        self.distrib_code = None
        self.distrib_message = None

    def parse_network_message(self):
        # Older SoulseekQt versions send the message type as uint32, while
        # older Nicotine+ versions send it as uint8. Since the message handler
        # in slskproto.py always reads the message type as uint8, skip the
        # remainder in case a uint32 is sent.
        if self._message[:3] == b"\x00\x00\x00":
            self._offset += 3
        self.distrib_code = self.unpack_uint8()
        self.distrib_message = self._message[self._offset:]


# Message Mappings #


SERVER_MESSAGE_CLASSES = {cls.CODE: cls for cls in ServerMessage.__subclasses__()}
PEER_INIT_MESSAGE_CLASSES = {cls.CODE: cls for cls in PeerInitMessage.__subclasses__()}
PEER_MESSAGE_CLASSES = {cls.CODE: cls for cls in PeerMessage.__subclasses__()}
DISTRIBUTED_MESSAGE_CLASSES = {cls.CODE: cls for cls in DistribMessage.__subclasses__()}
