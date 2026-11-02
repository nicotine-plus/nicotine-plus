# SPDX-FileCopyrightText: 2020-2026 Nicotine+ Contributors
# SPDX-FileCopyrightText: 2009-2011 quinox <quinox@users.sf.net>
# SPDX-FileCopyrightText: 2007-2009 daelstorm <daelstorm@gmail.com>
# SPDX-FileCopyrightText: 2003-2004 Hyriand <hyriand@thegraveyard.org>
# SPDX-FileCopyrightText: 2001-2003 Alexander Kanavin
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import zlib

try:
    # Try faster module import first, if available
    from _md5 import md5  # pylint: disable=import-private-name
except ImportError:
    from hashlib import md5

from collections.abc import Callable
from dataclasses import dataclass, field, fields
from enum import IntEnum, StrEnum
from operator import attrgetter, itemgetter
from random import randint
from socket import inet_aton, inet_ntoa, socket
from struct import Struct
from typing import (
    BinaryIO,
    ClassVar,
    NamedTuple,
    Self,
    TYPE_CHECKING,
    cast
)

from pynicotine.utils import (
    UINT32_LIMIT,
    human_length
)

if TYPE_CHECKING:
    from pynicotine.shares import AudioQuality, Database, FileInfo

# This module contains message classes, that networking and UI thread
# exchange. Basically there are three types of messages: internal messages,
# server messages and p2p messages (between clients).


INT32_UNPACK: Callable[[memoryview, int], tuple[int]] = Struct("<i").unpack_from
DOUBLE_UINT32_UNPACK: Callable[[memoryview, int], tuple[int]] = Struct("<II").unpack_from
UINT16_UNPACK: Callable[[memoryview, int], tuple[int]] = Struct("<H").unpack_from
UINT32_UNPACK: Callable[[memoryview, int], tuple[int]] = Struct("<I").unpack_from
UINT64_UNPACK: Callable[[memoryview, int], tuple[int]] = Struct("<Q").unpack_from

BOOL_PACK: Callable[[bool], bytes] = Struct("?").pack
UINT8_PACK: Callable[[int], bytes] = Struct("B").pack
INT32_PACK: Callable[[int], bytes] = Struct("<i").pack
UINT32_PACK: Callable[[int], bytes] = Struct("<I").pack
UINT64_PACK: Callable[[int], bytes] = Struct("<Q").pack

SERVER_USERNAME = "server"
ZLIB_COMPRESSION_LEVEL = 4


def initial_token() -> int:
    """Return a random token in a large enough range to effectively prevent
    conflicting tokens between sessions."""
    return randint(0, UINT32_LIMIT // 1000)


def increment_token(token: int) -> int:
    """Increment a token used by file search, transfer and connection
    requests."""

    if token < 0 or token >= UINT32_LIMIT:
        # Protocol messages use unsigned integers for tokens
        token = 0

    token += 1
    return token


# Constants #


class MessageType(StrEnum):
    INTERNAL = "N"
    INIT = "I"
    SERVER = "S"
    PEER = "P"
    FILE = "F"
    DISTRIBUTED = "D"


class ConnectionType(StrEnum):
    PEER = "P"
    FILE = "F"
    DISTRIBUTED = "D"


class ObfuscationType(IntEnum):
    NONE = 0
    ROTATED = 1


class LoginRejectReason(StrEnum):
    INVALID_USERNAME = "INVALIDUSERNAME"
    EMPTY_PASSWORD = "EMPTYPASSWORD"
    INVALID_PASSWORD = "INVALIDPASS"
    INVALID_VERSION = "INVALIDVERSION"
    SERVER_FULL = "SVRFULL"
    SERVER_PRIVATE = "SVRPRIVATE"


class UserStatus(IntEnum):
    OFFLINE = 0
    AWAY = 1
    ONLINE = 2


class RoomType(IntEnum):
    PUBLIC = 0
    PRIVATE = 1


class TransferDirection(IntEnum):
    DOWNLOAD = 0
    UPLOAD = 1


class TransferRejectReason(StrEnum):
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


class FileAttribute(IntEnum):
    BITRATE = 0
    LENGTH = 1
    VBR = 2
    ENCODER = 3  # Obsolete
    SAMPLE_RATE = 4
    BIT_DEPTH = 5


class ParentStatus(IntEnum):
    ACCEPTED = 0
    WAITING = 1
    REJECTED = 2


# Structures #


class Address(NamedTuple):
    ip: str
    port: int


@dataclass(slots=True, eq=False)
class UserStats:
    username: str
    status: int | None = None
    upload_speed: int = 0
    upload_number: int = 0
    unknown: int = 0
    num_files: int = 0
    num_folders: int = 0
    slots_full: int = 0
    country_code: str = ""


@dataclass(slots=True, eq=False)
class RoomStats:
    name: str
    num_users: int = 0


@dataclass(slots=True, eq=False)
class RoomTicker:
    username: str
    message: str


@dataclass(slots=True, eq=False)
class Recommendation:
    item: str
    rating: int


@dataclass(slots=True, eq=False)
class SimilarUser:
    username: str
    rating: int | None = None


@dataclass(slots=True, eq=False)
class RelatedSearchTerm:
    term: str
    score: int


@dataclass(slots=True, eq=False)
class FileAttributes:
    bitrate: int | None = None
    length: int | None = None
    vbr: int | None = None
    sample_rate: int | None = None
    bit_depth: int | None = None

    def parse_quality_length(
        self, file_size: int, always_show_bitrate: bool = False
    ) -> tuple[str, int, str, int]:

        bitrate = self.bitrate
        length = self.length
        vbr = self.vbr
        sample_rate = self.sample_rate
        bit_depth = self.bit_depth

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

    def serialize(self) -> dict[FileAttribute, int]:
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


@dataclass(slots=True, eq=False)
class SharedFile:
    code: int
    path: str
    size: int
    extension: None  # Obsolete, kept for compatibility
    attributes: FileAttributes

    def serialize(self) -> tuple[int, str, int, None, FileAttributes]:
        return (self.code, self.path, self.size, self.extension, self.attributes)


@dataclass(slots=True, eq=False)
class ParentCandidate:
    username: str
    addr: Address
    sock: socket | None = None
    branch_root: str | None = None
    branch_level: int | None = None


# Internal Messages #


@dataclass(slots=True, eq=False, repr=False)
class InternalMessage:
    TYPE: ClassVar[str] = MessageType.INTERNAL
    LOGGED: ClassVar[bool] = True

    def __repr__(self) -> str:
        attrs = {x.name: getattr(self, x.name) for x in fields(self) if x.repr}
        return f"<{self.TYPE} - {type(self).__name__}> {attrs}"


@dataclass(slots=True, eq=False, repr=False)
class CloseConnection(InternalMessage):
    sock: socket


@dataclass(slots=True, eq=False, repr=False)
class ServerConnect(InternalMessage):
    """Sent to the networking thread to establish a server connection."""

    addr: Address
    username: str
    password: str = field(repr=False)
    listen_port: int
    interface_name: str = ""
    interface_address: str | None = None


@dataclass(slots=True, eq=False, repr=False)
class ServerDisconnect(InternalMessage):
    manual_disconnect: bool = False


@dataclass(slots=True, eq=False, repr=False)
class ServerReconnect(InternalMessage):
    manual_reconnect: bool = False


@dataclass(slots=True, eq=False, repr=False)
class EmitNetworkMessageEvents(InternalMessage):
    """Sent to the networking thread to tell it to emit events for list of
    network messages.

    Currently used after shares have rescanned to process any
    QueueUpload messages that arrived while scanning.
    """

    msgs: list[SlskMessage]


@dataclass(slots=True, eq=False, repr=False)
class DownloadFile(InternalMessage):
    """Sent to the networking thread to pass the file object to write."""

    sock: socket
    token: int
    file_handle: BinaryIO
    num_bytes_left: int
    offset: int
    speed: int = 0


@dataclass(slots=True, eq=False, repr=False)
class UploadFile(InternalMessage):
    sock: socket
    token: int
    file_handle: BinaryIO
    file_size: int
    num_bytes_sent: int = 0
    offset: int | None = None
    speed: int = 0


@dataclass(slots=True, eq=False, repr=False)
class SetUploadLimit(InternalMessage):
    """Sent to the networking thread to indicate changes in bandwidth shaping rules."""

    speed_limit: int
    limit_by_total: bool


@dataclass(slots=True, eq=False, repr=False)
class SetDownloadLimit(InternalMessage):
    """Sent to the networking thread to indicate changes in bandwidth shaping rules."""

    speed_limit: int


@dataclass(slots=True, eq=False, repr=False)
class AddAllowedResponse(InternalMessage):
    """Sent to the networking thread to indicate that we're expecting a message response
    with a certain ID (username, token, etc). More heavy tasks can be performed for allowed
    responses, such as decompression.
    """

    msg_class: type[SlskMessage]
    response_id: str | int


@dataclass(slots=True, eq=False, repr=False)
class RemoveAllowedResponse(InternalMessage):
    """Sent to the networking thread to indicate that we're no longer expecting a message
    response with a certain ID (username, token, etc).
    """

    msg_class: type[SlskMessage]
    response_id: str | int


# Network Messages #


UNSET = "<unset>"
UNSET_ADDR = Address(ip=UNSET, port=-1)
UNSET_STATS = UserStats(username=UNSET)


@dataclass(slots=True, eq=False, repr=False)
class SlskMessage:
    """This is a parent class for all protocol messages."""

    TYPE: ClassVar[str]
    CODE: ClassVar[int | None] = None
    EVENT_NAME: ClassVar[str | None] = None
    LOGGED: ClassVar[bool] = True

    def __repr__(self) -> str:
        attrs = {x.name: getattr(self, x.name) for x in fields(self) if x.repr}
        return f"<{self.TYPE} - {type(self).__name__}> {attrs}"


class MessageParser:

    def __init__(
        self, content: memoryview, source: str | None = None, allowed_ids: set[str | int] | None = None
    ):
        self.content = content
        self.source = source
        self.allowed_ids = allowed_ids
        self.offset = 0

    def has_remaining_content(self) -> bool:
        return bool(self.content[self.offset:])

    def unpack_bytes(self) -> bytes:

        length, = UINT32_UNPACK(self.content, self.offset)
        start = self.offset + 4
        self.offset = start + length
        content = self.content[start:self.offset]

        return content.tobytes()

    def unpack_string(self) -> str:

        length, = UINT32_UNPACK(self.content, self.offset)
        start = self.offset + 4
        self.offset = start + length
        content = self.content[start:self.offset].tobytes()

        try:
            string = content.decode("utf-8")

        except UnicodeDecodeError:
            # Legacy strings
            string = content.decode("latin-1")

        return string

    def unpack_strings(self) -> list[str]:
        return [
            self.unpack_string()
            for _ in range(self.unpack_uint32())
        ]

    def skip_string(self) -> None:
        length, = UINT32_UNPACK(self.content, self.offset)
        self.offset += 4 + length

    def unpack_bool(self) -> bool:
        result = bool(self.content[self.offset])
        self.offset += 1
        return result

    def unpack_ip(self) -> str:
        start = self.offset
        self.offset += 4
        return inet_ntoa(self.content[start:self.offset].tobytes()[::-1])

    def unpack_uint8(self) -> int:
        result = self.content[self.offset]
        self.offset += 1
        return result

    def unpack_uint16(self) -> int:
        result, = UINT16_UNPACK(self.content, self.offset)
        self.offset += 2
        return result

    def unpack_int32(self) -> int:
        result, = INT32_UNPACK(self.content, self.offset)
        self.offset += 4
        return result

    def unpack_uint32(self) -> int:
        result, = UINT32_UNPACK(self.content, self.offset)
        self.offset += 4
        return result

    def unpack_uint64(self) -> int:
        result, = UINT64_UNPACK(self.content, self.offset)
        self.offset += 8
        return result

    def unpack_user_stats(self) -> list[UserStats]:
        users = [
            UserStats(username=self.unpack_string())
            for _ in range(self.unpack_uint32())
        ]

        num_statuses = self.unpack_uint32()
        for i in range(num_statuses):
            users[i].status = self.unpack_uint32()

        num_stats = self.unpack_uint32()
        for i in range(num_stats):
            users[i].upload_speed = self.unpack_uint32()
            users[i].upload_number = self.unpack_uint32()
            users[i].unknown = self.unpack_uint32()
            users[i].num_files = self.unpack_uint32()
            users[i].num_folders = self.unpack_uint32()

        num_slots_full = self.unpack_uint32()
        for i in range(num_slots_full):
            users[i].slots_full = self.unpack_uint32()

        num_country_codes = self.unpack_uint32()
        for i in range(num_country_codes):
            users[i].country_code = self.unpack_string()

        return users

    def unpack_room_stats(self) -> list[RoomStats]:
        rooms = [
            RoomStats(name=self.unpack_string())
            for _ in range(self.unpack_uint32())
        ]

        num_stats = self.unpack_uint32()
        for i in range(num_stats):
            rooms[i].num_users = self.unpack_uint32()

        return rooms

    def unpack_recommendations(self) -> tuple[list[Recommendation], list[Recommendation]]:
        recommendations: list[Recommendation] = []
        unrecommendations: list[Recommendation] = []

        def populate_recommendations(
            recommendations: list[Recommendation], unrecommendations: list[Recommendation]
        ) -> None:
            num_recommendations = self.unpack_uint32()

            for _ in range(num_recommendations):
                recommendation = Recommendation(
                    item=self.unpack_string(),
                    rating=self.unpack_int32()
                )
                lst = recommendations if recommendation.rating >= 0 else unrecommendations

                if recommendation not in lst:
                    lst.append(recommendation)

        populate_recommendations(recommendations, unrecommendations)

        if self.has_remaining_content():
            populate_recommendations(recommendations, unrecommendations)

        return recommendations, unrecommendations

    def unpack_file_size(self) -> int:

        if self.content[self.offset + 7] == 255:
            # Soulseek NS bug: >2 GiB files show up as ~16 EiB when unpacking the size
            # as uint64 (8 bytes), due to the first 4 bytes containing the size, and the
            # last 4 bytes containing garbage (a value of 4294967295 bytes, integer limit).
            # Only unpack the first 4 bytes to work around this issue.

            size = self.unpack_uint32()
            self.offset += 4
        else:
            # Everything looks fine, parse size as usual
            size = self.unpack_uint64()

        return size

    def unpack_file_attributes(self) -> FileAttributes:

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

    def unpack_files(self) -> list[SharedFile]:

        files = [
            SharedFile(
                code=self.unpack_uint8(),
                path=self.unpack_string(),
                size=self.unpack_file_size(),
                extension=self.skip_string(),
                attributes=self.unpack_file_attributes()
            )
            for _ in range(self.unpack_uint32())
        ]

        if len(files) > 1:
            files.sort(key=attrgetter("path"))

        return files


def pack_string(content: str, is_legacy: bool = False) -> bytes:

    if is_legacy:
        # Legacy string
        try:
            encoded = content.encode("latin-1")

        except UnicodeEncodeError:
            encoded = content.encode("utf-8", "replace")

    else:
        encoded = content.encode("utf-8", "replace")

    return UINT32_PACK(len(encoded)) + encoded


def pack_bool(content: bool) -> bytes:
    return BOOL_PACK(content)


def pack_uint8(content: int) -> bytes:
    return UINT8_PACK(content)


def pack_int32(content: int) -> bytes:
    return INT32_PACK(content)


def pack_uint32(content: int) -> bytes:
    return UINT32_PACK(content)


def pack_uint64(content: int) -> bytes:
    return UINT64_PACK(content)


def pack_file_info(fileinfo: FileInfo) -> bytearray:

    virtual_file_path, size, quality, duration = cast(
        tuple[str, int, "AudioQuality | None", int | None], fileinfo
    )
    bitrate = is_vbr = samplerate = bitdepth = None

    if quality is not None:
        bitrate, is_vbr, samplerate, bitdepth = quality

    is_lossless = bitdepth is not None

    msg = bytearray()
    msg += pack_uint8(1)
    msg += pack_string(virtual_file_path)
    msg += pack_uint64(size)
    msg += pack_uint32(0)  # empty ext

    if is_lossless:
        num_attrs = (
            (duration is not None) + (samplerate is not None) + (bitdepth is not None)
        )
        msg += pack_uint32(num_attrs)

        if duration is not None:
            msg += pack_uint32(1)
            msg += pack_uint32(duration)

        if samplerate is not None:
            msg += pack_uint32(4)
            msg += pack_uint32(samplerate)

        if bitdepth is not None:
            msg += pack_uint32(5)
            msg += pack_uint32(bitdepth)
    else:
        num_attrs = (
            (bitrate is not None) + (duration is not None) + (bitrate is not None and is_vbr is not None)
        )
        msg += pack_uint32(num_attrs)

        if bitrate is not None:
            msg += pack_uint32(0)
            msg += pack_uint32(bitrate)

        if duration is not None:
            msg += pack_uint32(1)
            msg += pack_uint32(duration)

        if bitrate is not None and is_vbr is not None:
            msg += pack_uint32(2)
            msg += pack_uint32(is_vbr)

    return msg


# Server Messages #


@dataclass(slots=True, eq=False, repr=False)
class ServerMessage(SlskMessage):
    TYPE = MessageType.SERVER


@dataclass(slots=True, eq=False, repr=False)
class Login(ServerMessage):
    """We send this to the server right after the connection has been
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

    CODE = 1
    EVENT_NAME = "server-login"

    username: str
    password: str = field(repr=False)
    major_version: int
    minor_version: int
    success: bool = False
    rejection_reason: str | None = None
    rejection_detail: str | None = None
    motd: str | None = None
    ip_address: str | None = None
    is_supporter: bool | None = None
    local_address: Address | None = None
    server_address: Address | None = None

    def pack(self) -> bytearray:

        msg = bytearray()
        checksum = md5((self.username + self.password).encode()).hexdigest()

        msg += pack_string(self.username)
        msg += pack_string(self.password)
        msg += pack_uint32(self.major_version)
        msg += pack_string(checksum)
        msg += pack_uint32(self.minor_version)

        return msg

    @classmethod
    def unpack(cls, parser: MessageParser) -> Self:
        msg = cls(
            username=UNSET,
            password=UNSET,
            major_version=-1,
            minor_version=-1,
            success=parser.unpack_bool()
        )

        if not msg.success:
            msg.rejection_reason = parser.unpack_string()

            if parser.has_remaining_content():
                msg.rejection_detail = parser.unpack_string()

            return msg

        msg.motd = parser.unpack_string()
        msg.ip_address = parser.unpack_ip()
        _checksum = parser.unpack_string()  # MD5 checksum of the password you sent
        msg.is_supporter = parser.unpack_bool()
        return msg


@dataclass(slots=True, eq=False, repr=False)
class SetWaitPort(ServerMessage):
    """We send this to the server to indicate the port number that we listen on
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

    CODE = 2

    port: int

    def pack(self) -> bytes:
        return pack_uint32(self.port)


@dataclass(slots=True, eq=False, repr=False)
class GetPeerAddress(ServerMessage):
    """We send this to the server to ask for a peer's address (IP address
    and port), given the peer's username.
    """

    CODE = 3
    EVENT_NAME = "peer-address"

    username: str
    addr: Address = UNSET_ADDR
    obfuscation_type: int = -1
    obfuscated_port: int = -1

    def pack(self) -> bytes:
        return pack_string(self.username)

    @classmethod
    def unpack(cls, parser: MessageParser) -> Self:
        msg = cls(
            username=parser.unpack_string(),
            addr=Address(
                ip=parser.unpack_ip(),
                port=parser.unpack_uint32()
            ),
            obfuscation_type=parser.unpack_uint32(),
            obfuscated_port=parser.unpack_uint16()
        )
        return msg


@dataclass(slots=True, eq=False, repr=False)
class WatchUser(ServerMessage):
    """Used to be kept updated about a user's status. Whenever a user's status
    changes, the server sends a GetUserStatus message.

    Note that the server does not currently send stat updates (GetUserStats)
    when watching a user, only the initial stats in the WatchUser response.
    As a consequence, stats can be outdated.
    """

    CODE = 5
    EVENT_NAME = "watch-user"

    username: str
    exists: bool = False
    stats: UserStats | None = None

    def pack(self) -> bytes:
        return pack_string(self.username)

    @classmethod
    def unpack(cls, parser: MessageParser) -> Self:
        msg = cls(
            username=parser.unpack_string(),
            exists=parser.unpack_bool()
        )

        if not msg.exists:
            return msg

        msg.stats = UserStats(
            username=msg.username,
            status=parser.unpack_uint32(),
            upload_speed=parser.unpack_uint32(),
            upload_number=parser.unpack_uint32(),
            unknown=parser.unpack_uint32(),
            num_files=parser.unpack_uint32(),
            num_folders=parser.unpack_uint32()
        )

        if parser.has_remaining_content():
            msg.stats.country_code = parser.unpack_string()

        return msg


@dataclass(slots=True, eq=False, repr=False)
class UnwatchUser(ServerMessage):
    """Used when we no longer want to be kept updated about a user's status."""

    CODE = 6

    username: str

    def pack(self) -> bytes:
        return pack_string(self.username)


@dataclass(slots=True, eq=False, repr=False)
class GetUserStatus(ServerMessage):
    """The server tells us if a user has gone away or has returned."""

    CODE = 7
    EVENT_NAME = "user-status"

    username: str
    status: int = -1
    privileged: bool = False

    def pack(self) -> bytes:
        return pack_string(self.username)

    @classmethod
    def unpack(cls, parser: MessageParser) -> Self:
        msg = cls(
            username=parser.unpack_string(),
            status=parser.unpack_uint32(),
            privileged=parser.unpack_bool()
        )
        return msg


@dataclass(slots=True, eq=False, repr=False)
class IgnoreUser(ServerMessage):
    """We send this to the server to tell a user we have ignored them.

    The server tells us a user has ignored us.

    OBSOLETE, no longer functional
    """

    CODE = 11

    username: str

    def pack(self) -> bytes:
        return pack_string(self.username)

    @classmethod
    def unpack(cls, parser: MessageParser) -> Self:
        msg = cls(
            username=parser.unpack_string()
        )
        return msg


@dataclass(slots=True, eq=False, repr=False)
class UnignoreUser(ServerMessage):
    """We send this to the server to tell a user we are no longer ignoring them.

    The server tells us a user is no longer ignoring us.

    OBSOLETE, no longer functional
    """

    CODE = 12

    username: str

    def pack(self) -> bytes:
        return pack_string(self.username)

    @classmethod
    def unpack(cls, parser: MessageParser) -> Self:
        msg = cls(
            username=parser.unpack_string()
        )
        return msg


@dataclass(slots=True, eq=False, repr=False)
class SayChatroom(ServerMessage):
    """Either we want to say something in the chatroom, or someone else did."""

    CODE = 13
    EVENT_NAME = "say-chat-room"

    room_name: str
    message: str
    username: str = UNSET
    message_type: str | None = None
    mention_type: str | None = None
    mention_keyword: str | None = None

    def pack(self) -> bytearray:
        msg = bytearray()
        msg += pack_string(self.room_name)
        msg += pack_string(self.message)

        return msg

    @classmethod
    def unpack(cls, parser: MessageParser) -> Self:
        msg = cls(
            room_name=parser.unpack_string(),
            username=parser.unpack_string(),
            message=parser.unpack_string()
        )
        return msg


@dataclass(slots=True, eq=False, repr=False)
class JoinRoom(ServerMessage):
    """We send this message to the server when we want to join a room. If
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

    CODE = 14
    EVENT_NAME = "join-room"

    room_name: str
    room_type: RoomType = RoomType.PUBLIC
    owner: str | None = None
    users: list[UserStats] = field(default_factory=list[UserStats])
    operators: list[str] = field(default_factory=list[str])

    def pack(self) -> bytearray:
        msg = bytearray()
        msg += pack_string(self.room_name)
        msg += pack_uint32(self.room_type)

        return msg

    @classmethod
    def unpack(cls, parser: MessageParser) -> Self:
        msg = cls(
            room_name=parser.unpack_string(),
            users=parser.unpack_user_stats()
        )

        if not parser.has_remaining_content():
            return msg

        msg.room_type = RoomType.PRIVATE
        msg.owner = parser.unpack_string()
        msg.operators = parser.unpack_strings()

        return msg


@dataclass(slots=True, eq=False, repr=False)
class LeaveRoom(ServerMessage):
    """We send this to the server when we want to leave a room."""

    CODE = 15
    EVENT_NAME = "leave-room"

    room_name: str

    def pack(self) -> bytes:
        return pack_string(self.room_name)

    @classmethod
    def unpack(cls, parser: MessageParser) -> Self:
        msg = cls(
            room_name=parser.unpack_string()
        )
        return msg


@dataclass(slots=True, eq=False, repr=False)
class UserJoinedRoom(ServerMessage):
    """The server tells us someone has just joined a room we're in."""

    CODE = 16
    EVENT_NAME = "user-joined-room"

    room_name: str
    username: str
    stats: UserStats

    @classmethod
    def unpack(cls, parser: MessageParser) -> Self:
        room_name = parser.unpack_string()
        username = parser.unpack_string()
        msg = cls(
            room_name=room_name,
            username=username,
            stats=UserStats(
                username=username,
                status=parser.unpack_uint32(),
                upload_speed=parser.unpack_uint32(),
                upload_number=parser.unpack_uint32(),
                unknown=parser.unpack_uint32(),
                num_files=parser.unpack_uint32(),
                num_folders=parser.unpack_uint32(),
                slots_full=parser.unpack_uint32(),
                country_code=parser.unpack_string()
            )
        )
        return msg


@dataclass(slots=True, eq=False, repr=False)
class UserLeftRoom(ServerMessage):
    """The server tells us someone has just left a room we're in."""

    CODE = 17
    EVENT_NAME = "user-left-room"

    room_name: str
    username: str

    @classmethod
    def unpack(cls, parser: MessageParser) -> Self:
        msg = cls(
            room_name=parser.unpack_string(),
            username=parser.unpack_string()
        )
        return msg


@dataclass(slots=True, eq=False, repr=False)
class ConnectToPeer(ServerMessage):
    """We send this to the server to attempt an indirect connection with a user.
    The server forwards the message to the user, who in turn attempts to establish
    a connection to our IP address and port from their end.
    """

    CODE = 18
    EVENT_NAME = "connect-to-peer"

    token: int
    username: str
    conn_type: str
    addr: Address = UNSET_ADDR
    privileged: bool = False
    obfuscation_type: int = -1
    obfuscated_port: int = -1

    def pack(self) -> bytearray:
        msg = bytearray()
        msg += pack_uint32(self.token)
        msg += pack_string(self.username)
        msg += pack_string(self.conn_type)

        return msg

    @classmethod
    def unpack(cls, parser: MessageParser) -> Self:
        msg = cls(
            username=parser.unpack_string(),
            conn_type=parser.unpack_string(),
            addr=Address(
                ip=parser.unpack_ip(),
                port=parser.unpack_uint32()
            ),
            token=parser.unpack_uint32(),
            privileged=parser.unpack_bool(),
            obfuscation_type=parser.unpack_uint32(),
            obfuscated_port=parser.unpack_uint32()
        )
        return msg


@dataclass(slots=True, eq=False, repr=False)
class MessageUser(ServerMessage):
    """Chat phrase sent to someone or received by us in private."""

    CODE = 22
    EVENT_NAME = "message-user"

    username: str
    message: str
    message_id: int = -1
    timestamp: int = -1
    is_new_message: bool = False
    message_type: str | None = None
    mention_type: str | None = None
    mention_keyword: str | None = None

    def pack(self) -> bytearray:
        msg = bytearray()
        msg += pack_string(self.username)
        msg += pack_string(self.message)

        return msg

    @classmethod
    def unpack(cls, parser: MessageParser) -> Self:
        msg = cls(
            message_id=parser.unpack_uint32(),
            timestamp=parser.unpack_uint32(),
            username=parser.unpack_string(),
            message=parser.unpack_string(),
            is_new_message=parser.unpack_bool()
        )
        return msg


@dataclass(slots=True, eq=False, repr=False)
class MessageAcked(ServerMessage):
    """We send this to the server to confirm that we received a private
    message. If we don't send it, the server will keep sending the chat
    phrase to us.
    """

    CODE = 23

    message_id: int

    def pack(self) -> bytes:
        return pack_uint32(self.message_id)


@dataclass(slots=True, eq=False, repr=False)
class FileSearchRoom(ServerMessage):
    """We send this to the server when we search for something in a room.

    OBSOLETE, superseded by RoomSearch server message
    """

    CODE = 25

    token: int
    room_id: int
    search_term: str

    def pack(self) -> bytearray:
        msg = bytearray()
        msg += pack_uint32(self.token)
        msg += pack_uint32(self.room_id)
        msg += pack_string(self.search_term)

        return msg


@dataclass(slots=True, eq=False, repr=False)
class FileSearch(ServerMessage):
    """We send this to the server when we search for something.
    Alternatively, the server sends this message outside the distributed
    network to tell us that someone is searching for something,
    currently used for UserSearch and RoomSearch requests.

    The token is a number generated by the client and is used to track
    the search results.
    """

    CODE = 26
    EVENT_NAME = "file-search-request-server"

    token: int
    search_term: str
    search_username: str = UNSET

    def pack(self) -> bytearray:
        msg = bytearray()
        msg += pack_uint32(self.token)
        msg += pack_string(self.search_term)

        return msg

    @classmethod
    def unpack(cls, parser: MessageParser) -> Self:
        msg = cls(
            search_username=parser.unpack_string(),
            token=parser.unpack_uint32(),
            search_term=parser.unpack_string()
        )
        return msg


@dataclass(slots=True, eq=False, repr=False)
class SetStatus(ServerMessage):
    """We send our new status to the server. Status is a way to define
    whether we're available (online) or busy (away).

    When changing our own status, the server sends us a GetUserStatus
    message when enabling away status, but not when disabling it.

    1 = Away
    2 = Online
    """

    CODE = 28

    status: int

    def pack(self) -> bytes:
        return pack_int32(self.status)


@dataclass(slots=True, eq=False, repr=False)
class ServerPing(ServerMessage):
    """We send this to the server at most once per minute to ensure the
    connection stays alive.

    The server used to send a response message in the past, but this is no
    longer the case.

    Nicotine+ uses TCP keepalive instead of sending this message.
    """

    CODE = 32

    def pack(self) -> bytes:
        return b""

    @classmethod
    def unpack(cls, _parser: MessageParser) -> Self:
        """Obsolete."""
        return cls()


@dataclass(slots=True, eq=False, repr=False)
class SendConnectToken(ServerMessage):
    """This message used to be sent together with the PeerInit message when
    connecting to a user, with the same non-zero token included in both. The
    recipient could then cross-check the username and token, in order to reject
    spoofed connection attempts.

    While the server still recognizes and forwards this message today, no
    clients use it anymore. The lack of adoption by clients in the past has
    effectively rendered the message unusable, since its reintroduction in a
    client would isolate the client from the rest of the network.

    OBSOLETE, no longer used
    """

    CODE = 33

    username: str
    token: int

    def pack(self) -> bytearray:
        msg = bytearray()
        msg += pack_string(self.username)
        msg += pack_uint32(self.token)

        return msg

    @classmethod
    def unpack(cls, parser: MessageParser) -> Self:
        msg = cls(
            username=parser.unpack_string(),
            token=parser.unpack_uint32()
        )
        return msg


@dataclass(slots=True, eq=False, repr=False)
class SendDownloadSpeed(ServerMessage):
    """We used to send this after a finished download to let the server
    update the speed statistics for a user.

    OBSOLETE, superseded by SendUploadSpeed server message
    """

    CODE = 34

    username: str
    speed: int

    def pack(self) -> bytearray:
        msg = bytearray()
        msg += pack_string(self.username)
        msg += pack_uint32(self.speed)

        return msg


@dataclass(slots=True, eq=False, repr=False)
class SharedFoldersFiles(ServerMessage):
    """We send this to server to indicate the number of folder and files
    that we share.
    """

    CODE = 35

    num_folders: int
    num_files: int

    def pack(self) -> bytearray:
        msg = bytearray()
        msg += pack_uint32(self.num_folders)
        msg += pack_uint32(self.num_files)

        return msg


@dataclass(slots=True, eq=False, repr=False)
class GetUserStats(ServerMessage):
    """The server sends this to indicate a change in a user's stats, if we have
    joined the same chat room. We can also request a user's stats by sending
    the message to the server.
    """

    CODE = 36
    EVENT_NAME = "user-stats"

    username: str
    stats: UserStats = UNSET_STATS

    def pack(self) -> bytes:
        return pack_string(self.username)

    @classmethod
    def unpack(cls, parser: MessageParser) -> Self:
        username = parser.unpack_string()
        msg = cls(
            username=username,
            stats=UserStats(
                username=username,
                upload_speed=parser.unpack_uint32(),
                upload_number=parser.unpack_uint32(),
                unknown=parser.unpack_uint32(),
                num_files=parser.unpack_uint32(),
                num_folders=parser.unpack_uint32()
            )
        )
        return msg


@dataclass(slots=True, eq=False, repr=False)
class UploadSlotsFull(ServerMessage):
    """We send this to the server to indicate whether our upload slots are fully
    occupied or not. The server broadcasts the message to joined rooms.

    The official Soulseek client used to send this message on login, as well as
    when upload slots filled up or became available. Users with full slots were
    grayed out in room user lists.

    OBSOLETE, no longer used
    """

    CODE = 40

    slots_full: int
    username: str = UNSET

    def pack(self) -> bytes:
        return pack_uint32(self.slots_full)

    @classmethod
    def unpack(cls, parser: MessageParser) -> Self:
        msg = cls(
            username=parser.unpack_string(),
            slots_full=parser.unpack_uint32()
        )
        return msg


@dataclass(slots=True, eq=False, repr=False)
class Relogged(ServerMessage):
    """The server sends this if someone else logged in under our nickname,
    and then disconnects us.
    """

    CODE = 41

    @classmethod
    def unpack(cls, _parser: MessageParser) -> Self:
        return cls()


@dataclass(slots=True, eq=False, repr=False)
class UserSearch(ServerMessage):
    """We send this to the server when we search a specific user's shares.
    The token is a number generated by the client and is used to track
    the search results.

    The recipient receives the search request in the form of a FileSearch
    message.
    """

    CODE = 42

    username: str
    token: int
    search_term: str

    def pack(self) -> bytearray:
        msg = bytearray()
        msg += pack_string(self.username)
        msg += pack_uint32(self.token)
        msg += pack_string(self.search_term)

        return msg


@dataclass(slots=True, eq=False, repr=False)
class SimilarRecommendations(ServerMessage):
    """We send this to the server when we are adding a recommendation to our
    "My recommendations" list, and want to receive a list of similar
    recommendations.

    The server sends a list of similar recommendations to the one we want to
    add. Older versions of the official Soulseek client would display a dialog
    containing such recommendations, asking us if we want to add our original
    recommendation or one of the similar ones instead.

    OBSOLETE, no longer used, server sends empty list
    """

    CODE = 50

    recommendation: str
    similar_recommendations: list[str] = field(default_factory=list[str])

    def pack(self) -> bytes:
        return pack_string(self.recommendation)

    @classmethod
    def unpack(cls, parser: MessageParser) -> Self:
        msg = cls(
            recommendation=parser.unpack_string(),
            similar_recommendations=parser.unpack_strings()
        )
        return msg


@dataclass(slots=True, eq=False, repr=False)
class AddThingILike(ServerMessage):
    """We send this to the server when we add an item to our likes list."""

    CODE = 51

    item: str

    def pack(self) -> bytes:
        return pack_string(self.item)


@dataclass(slots=True, eq=False, repr=False)
class RemoveThingILike(ServerMessage):
    """We send this to the server when we remove an item from our likes list."""

    CODE = 52

    item: str

    def pack(self) -> bytes:
        return pack_string(self.item)


@dataclass(slots=True, eq=False, repr=False)
class Recommendations(ServerMessage):
    """The server sends us a list of personal recommendations and a number
    for each.
    """

    CODE = 54
    EVENT_NAME = "recommendations"

    recommendations: list[Recommendation] = field(default_factory=list[Recommendation])
    unrecommendations: list[Recommendation] = field(default_factory=list[Recommendation])

    def pack(self) -> bytes:
        return b""

    @classmethod
    def unpack(cls, parser: MessageParser) -> Self:
        recommendations, unrecommendations = parser.unpack_recommendations()
        msg = cls(
            recommendations=recommendations,
            unrecommendations=unrecommendations
        )
        return msg


@dataclass(slots=True, eq=False, repr=False)
class MyRecommendations(ServerMessage):
    """We send this to the server to ask for our own list of added
    likes/recommendations (called "My recommendations" in older versions
    of the official Soulseek client).

    The server sends us the list of recommendations it knows we have added.
    For any recommendations present locally, but not on the server, the
    official Soulseek client would send a AddThingILike message for each
    missing item.

    OBSOLETE, no longer functional
    """

    CODE = 55

    my_recommendations: list[str] = field(default_factory=list[str])

    def pack(self) -> bytes:
        return b""

    @classmethod
    def unpack(cls, parser: MessageParser) -> Self:
        msg = cls(
            my_recommendations=parser.unpack_strings()
        )
        return msg


@dataclass(slots=True, eq=False, repr=False)
class GlobalRecommendations(ServerMessage):
    """The server sends us a list of global recommendations and a number
    for each.
    """

    CODE = 56
    EVENT_NAME = "global-recommendations"

    recommendations: list[Recommendation] = field(default_factory=list[Recommendation])
    unrecommendations: list[Recommendation] = field(default_factory=list[Recommendation])

    def pack(self) -> bytes:
        return b""

    @classmethod
    def unpack(cls, parser: MessageParser) -> Self:
        recommendations, unrecommendations = parser.unpack_recommendations()
        msg = cls(
            recommendations=recommendations,
            unrecommendations=unrecommendations
        )
        return msg


@dataclass(slots=True, eq=False, repr=False)
class UserInterests(ServerMessage):
    """We ask the server for a user's liked and hated interests. The server
    responds with a list of interests.
    """

    CODE = 57
    EVENT_NAME = "user-interests"

    username: str
    likes: list[str] = field(default_factory=list[str])
    hates: list[str] = field(default_factory=list[str])

    def pack(self) -> bytes:
        return pack_string(self.username)

    @classmethod
    def unpack(cls, parser: MessageParser) -> Self:
        msg = cls(
            username=parser.unpack_string(),
            likes=parser.unpack_strings(),
            hates=parser.unpack_strings()
        )
        return msg


@dataclass(slots=True, eq=False, repr=False)
class AdminCommand(ServerMessage):
    """We send this to the server to run an admin command (e.g. to ban or
    silence a user) if we have admin status on the server.

    OBSOLETE, no longer functional
    """

    CODE = 58

    command: str
    command_args: list[str]

    def pack(self) -> bytearray:
        msg = bytearray()
        msg += pack_string(self.command)
        msg += pack_uint32(len(self.command_args))

        for arg in self.command_args:
            msg += pack_string(arg)

        return msg


@dataclass(slots=True, eq=False, repr=False)
class PlaceInLineRequest(ServerMessage):
    """OBSOLETE, superseded by PlaceInQueueRequest peer message"""

    CODE = 59

    username: str
    token: int

    def pack(self) -> bytearray:
        msg = bytearray()
        msg += pack_string(self.username)
        msg += pack_uint32(self.token)

        return msg

    @classmethod
    def unpack(cls, parser: MessageParser) -> Self:
        msg = cls(
            username=parser.unpack_string(),
            token=parser.unpack_uint32()
        )
        return msg


@dataclass(slots=True, eq=False, repr=False)
class PlaceInLineResponse(ServerMessage):
    """The server sends this to indicate change in place in queue while
    we're waiting for files from another peer.

    OBSOLETE, superseded by PlaceInQueueResponse peer message
    """

    CODE = 60

    username: str
    token: int
    place: int

    def pack(self) -> bytearray:
        msg = bytearray()
        msg += pack_string(self.username)
        msg += pack_uint32(self.token)
        msg += pack_uint32(self.place)

        return msg

    @classmethod
    def unpack(cls, parser: MessageParser) -> Self:
        msg = cls(
            username=parser.unpack_string(),
            token=parser.unpack_uint32(),
            place=parser.unpack_uint32()
        )
        return msg


@dataclass(slots=True, eq=False, repr=False)
class RoomAdded(ServerMessage):
    """The server tells us a new room has been added.

    OBSOLETE, no longer sent by the server
    """

    CODE = 62

    room_name: str

    @classmethod
    def unpack(cls, parser: MessageParser) -> Self:
        msg = cls(
            room_name=parser.unpack_string()
        )
        return msg


@dataclass(slots=True, eq=False, repr=False)
class RoomRemoved(ServerMessage):
    """The server tells us a room has been removed.

    OBSOLETE, no longer sent by the server
    """

    CODE = 63

    room_name: str

    @classmethod
    def unpack(cls, parser: MessageParser) -> Self:
        msg = cls(
            room_name=parser.unpack_string()
        )
        return msg


@dataclass(slots=True, eq=False, repr=False)
class RoomList(ServerMessage):
    """The server tells us a list of rooms and the number of users in them.
    When connecting to the server, the server only sends us rooms with
    at least 5 users. A few select rooms are also excluded, such as
    nicotine and The Lobby. Requesting the room list yields a response
    containing the missing rooms.
    """

    CODE = 64
    EVENT_NAME = "room-list"

    rooms: list[RoomStats] = field(default_factory=list[RoomStats])
    rooms_owner: list[RoomStats] = field(default_factory=list[RoomStats])
    rooms_member: list[RoomStats] = field(default_factory=list[RoomStats])
    rooms_operator: list[str] = field(default_factory=list[str])

    def pack(self) -> bytes:
        return b""

    @classmethod
    def unpack(cls, parser: MessageParser) -> Self:
        msg = cls(
            rooms=parser.unpack_room_stats(),
            rooms_owner=parser.unpack_room_stats(),
            rooms_member=parser.unpack_room_stats(),
            rooms_operator=parser.unpack_strings()
        )
        return msg


@dataclass(slots=True, eq=False, repr=False)
class ExactFileSearch(ServerMessage):
    """We send this to search for an exact file name and folder, to find
    other sources.

    OBSOLETE, no results even with official client
    """

    CODE = 65

    token: int
    file_path: str
    folder_path: str
    file_size: int
    checksum: int
    unknown: int | None
    username: str = UNSET

    def pack(self) -> bytearray:
        msg = bytearray()
        msg += pack_uint32(self.token)
        msg += pack_string(self.file_path)
        msg += pack_string(self.folder_path)
        msg += pack_uint64(self.file_size)
        msg += pack_uint32(self.checksum)
        msg += pack_uint8(self.unknown or 0)

        return msg

    @classmethod
    def unpack(cls, parser: MessageParser) -> Self:
        msg = cls(
            username=parser.unpack_string(),
            token=parser.unpack_uint32(),
            file_path=parser.unpack_string(),
            folder_path=parser.unpack_string(),
            file_size=parser.unpack_uint64(),
            checksum=parser.unpack_uint32(),
            unknown=None
        )
        return msg


@dataclass(slots=True, eq=False, repr=False)
class AdminMessage(ServerMessage):
    """A global message from the server admin has arrived."""

    CODE = 66
    EVENT_NAME = "admin-message"

    message: str

    @classmethod
    def unpack(cls, parser: MessageParser) -> Self:
        msg = cls(
            message=parser.unpack_string()
        )
        return msg


@dataclass(slots=True, eq=False, repr=False)
class GlobalUserList(ServerMessage):
    """We send this to get a global list of all users online.

    OBSOLETE, no longer used
    """

    CODE = 67

    users: list[UserStats] = field(default_factory=list[UserStats])

    def pack(self) -> bytes:
        return b""

    @classmethod
    def unpack(cls, parser: MessageParser) -> Self:
        msg = cls(
            users=parser.unpack_user_stats()
        )
        return msg


@dataclass(slots=True, eq=False, repr=False)
class TunneledMessage(ServerMessage):
    """Server message for tunneling a chat message.

    OBSOLETE, no longer used
    """

    CODE = 68

    username: str
    token: int
    code: int
    message: str
    addr: Address = UNSET_ADDR

    def pack(self) -> bytearray:
        msg = bytearray()
        msg += pack_string(self.username)
        msg += pack_uint32(self.token)
        msg += pack_uint32(self.code)
        msg += pack_string(self.message)

        return msg

    @classmethod
    def unpack(cls, parser: MessageParser) -> Self:
        msg = cls(
            username=parser.unpack_string(),
            code=parser.unpack_uint32(),
            token=parser.unpack_uint32(),
            addr=Address(
                ip=parser.unpack_ip(),
                port=parser.unpack_uint32()
            ),
            message=parser.unpack_string()
        )
        return msg


@dataclass(slots=True, eq=False, repr=False)
class PrivilegedUsers(ServerMessage):
    """The server sends us a list of privileged users, a.k.a. users who
    have donated.
    """

    CODE = 69
    EVENT_NAME = "privileged-users"

    usernames: list[str]

    @classmethod
    def unpack(cls, parser: MessageParser) -> Self:
        msg = cls(
            usernames=parser.unpack_strings()
        )
        return msg


@dataclass(slots=True, eq=False, repr=False)
class HaveNoParent(ServerMessage):
    """We inform the server if we have a distributed parent or not. If not, the
    server eventually sends us a PossibleParents message with a list of
    possible parents to connect to. If no candidates are found, no such
    message is sent by the server, and we eventually become a branch root
    (i.e. the server starts sending us EmbeddedMessage messages).
    """

    CODE = 71

    no_parent: bool

    def pack(self) -> bytes:
        return pack_bool(self.no_parent)


@dataclass(slots=True, eq=False, repr=False)
class ParentIP(ServerMessage):
    """We tell the server the IP address of our parent in the distributed network.

    DEPRECATED, sent by Soulseek NS but not SoulseekQt
    """

    CODE = 73

    ip_address: str

    @staticmethod
    def strunreverse(string: str) -> str:
        strlist = string.split(".")
        strlist.reverse()
        return ".".join(strlist)

    def pack(self) -> bytes:
        return inet_aton(self.strunreverse(self.ip_address))


@dataclass(slots=True, eq=False, repr=False)
class ParentMinSpeed(ServerMessage):
    """The server informs us about the minimum upload speed required to
    become a parent in the distributed network.
    """

    CODE = 83

    speed: int

    @classmethod
    def unpack(cls, parser: MessageParser) -> Self:
        msg = cls(
            speed=parser.unpack_uint32()
        )
        return msg


@dataclass(slots=True, eq=False, repr=False)
class ParentSpeedRatio(ServerMessage):
    """The server sends us a speed ratio determining the number of children
    we can have in the distributed network. The maximum number of
    children is our upload speed divided by the speed ratio.
    """

    CODE = 84

    ratio: int

    @classmethod
    def unpack(cls, parser: MessageParser) -> Self:
        msg = cls(
            ratio=parser.unpack_uint32()
        )
        return msg


@dataclass(slots=True, eq=False, repr=False)
class ParentInactivityTimeout(ServerMessage):
    """OBSOLETE, no longer sent by the server"""

    CODE = 86

    seconds: int

    @classmethod
    def unpack(cls, parser: MessageParser) -> Self:
        msg = cls(
            seconds=parser.unpack_uint32()
        )
        return msg


@dataclass(slots=True, eq=False, repr=False)
class SearchInactivityTimeout(ServerMessage):
    """OBSOLETE, no longer sent by the server"""

    CODE = 87

    seconds: int

    @classmethod
    def unpack(cls, parser: MessageParser) -> Self:
        msg = cls(
            seconds=parser.unpack_uint32()
        )
        return msg


@dataclass(slots=True, eq=False, repr=False)
class MinParentsInCache(ServerMessage):
    """OBSOLETE, no longer sent by the server"""

    CODE = 88

    number: int

    @classmethod
    def unpack(cls, parser: MessageParser) -> Self:
        msg = cls(
            number=parser.unpack_uint32()
        )
        return msg


@dataclass(slots=True, eq=False, repr=False)
class DistribPingInterval(ServerMessage):
    """OBSOLETE, no longer sent by the server"""

    CODE = 90

    seconds: int

    @classmethod
    def unpack(cls, parser: MessageParser) -> Self:
        msg = cls(
            seconds=parser.unpack_uint32()
        )
        return msg


@dataclass(slots=True, eq=False, repr=False)
class AddToPrivileged(ServerMessage):
    """The server sends us the username of a new privileged user, which we
    add to our list of global privileged users.

    OBSOLETE, no longer sent by the server
    """

    CODE = 91

    username: str

    @classmethod
    def unpack(cls, parser: MessageParser) -> Self:
        msg = cls(
            username=parser.unpack_string()
        )
        return msg


@dataclass(slots=True, eq=False, repr=False)
class CheckPrivileges(ServerMessage):
    """We ask the server how much time we have left of our privileges. The
    server responds with the remaining time, in seconds.
    """
    CODE = 92
    EVENT_NAME = "check-privileges"

    seconds: int = -1

    def pack(self) -> bytes:
        return b""

    @classmethod
    def unpack(cls, parser: MessageParser) -> Self:
        msg = cls(
            seconds=parser.unpack_uint32()
        )
        return msg


@dataclass(slots=True, eq=False, repr=False)
class EmbeddedMessage(ServerMessage):
    """The server sends us an embedded distributed message. The only sent message
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
    CODE = 93
    LOGGED = False

    distrib_code: int
    distrib_message: memoryview

    @classmethod
    def unpack(cls, parser: MessageParser) -> Self:
        msg = cls(
            distrib_code=parser.unpack_uint8(),
            distrib_message=parser.content[parser.offset:]
        )
        return msg


@dataclass(slots=True, eq=False, repr=False)
class AcceptChildren(ServerMessage):
    """We tell the server if we want to accept child nodes."""
    CODE = 100

    accept: bool

    def pack(self) -> bytes:
        return pack_bool(self.accept)


@dataclass(slots=True, eq=False, repr=False)
class PossibleParents(ServerMessage):
    """The server send us a list of max 10 possible distributed parents to
    connect to. Messages of this type are sent to us at regular intervals,
    until we tell the server we don't need more possible parents with a
    HaveNoParent message.

    The received list always contains users whose upload speed is higher than
    our own. If we have the highest upload speed on the server, we become a
    branch root, and start receiving EmbeddedMessage messages directly from
    the server.
    """

    CODE = 102

    candidates: list[ParentCandidate]

    @classmethod
    def unpack(cls, parser: MessageParser) -> Self:
        msg = cls(
            candidates=[
                ParentCandidate(
                    username=parser.unpack_string(),
                    addr=Address(
                        ip=parser.unpack_ip(),
                        port=parser.unpack_uint32()
                    )
                )
                for _ in range(parser.unpack_uint32())
            ]
        )
        return msg


@dataclass(slots=True, eq=False, repr=False)
class WishlistSearch(ServerMessage):
    """We send the server one of our wishlist search queries at each
    interval.
    """

    CODE = 103

    token: int
    search_term: str

    def pack(self) -> bytearray:
        msg = bytearray()
        msg += pack_uint32(self.token)
        msg += pack_string(self.search_term)

        return msg


@dataclass(slots=True, eq=False, repr=False)
class WishlistInterval(ServerMessage):
    """The server tells us the wishlist search interval."""

    CODE = 104
    EVENT_NAME = "set-wishlist-interval"

    seconds: int

    @classmethod
    def unpack(cls, parser: MessageParser) -> Self:
        msg = cls(
            seconds=parser.unpack_uint32()
        )
        return msg


@dataclass(slots=True, eq=False, repr=False)
class SimilarUsers(ServerMessage):
    """The server sends us a list of similar users related to our
    interests.
    """

    CODE = 110
    EVENT_NAME = "similar-users"

    users: list[SimilarUser] = field(default_factory=list[SimilarUser])

    def pack(self) -> bytes:
        return b""

    @classmethod
    def unpack(cls, parser: MessageParser) -> Self:
        msg = cls(
            users=[
                SimilarUser(
                    username=parser.unpack_string(),
                    rating=parser.unpack_uint32()
                )
                for _ in range(parser.unpack_uint32())
            ]
        )

        if len(msg.users) > 1:
            msg.users.sort(key=attrgetter("rating"), reverse=True)

        return msg


@dataclass(slots=True, eq=False, repr=False)
class ItemRecommendations(ServerMessage):
    """The server sends us a list of recommendations related to a specific
    item, which is usually present in the like/dislike list or an
    existing recommendation list.
    """

    CODE = 111
    EVENT_NAME = "item-recommendations"

    item: str
    recommendations: list[Recommendation] = field(default_factory=list[Recommendation])
    unrecommendations: list[Recommendation] = field(default_factory=list[Recommendation])

    def pack(self) -> bytes:
        return pack_string(self.item)

    @classmethod
    def unpack(cls, parser: MessageParser) -> Self:
        msg = cls(
            item=parser.unpack_string()
        )
        msg.recommendations, msg.unrecommendations = parser.unpack_recommendations()
        return msg


@dataclass(slots=True, eq=False, repr=False)
class ItemSimilarUsers(ServerMessage):
    """The server sends us a list of similar users related to a specific
    item, which is usually present in the like/dislike list or
    recommendation list.
    """

    CODE = 112
    EVENT_NAME = "item-similar-users"

    item: str
    users: list[SimilarUser] = field(default_factory=list[SimilarUser])

    def pack(self) -> bytes:
        return pack_string(self.item)

    @classmethod
    def unpack(cls, parser: MessageParser) -> Self:
        msg = cls(
            item=parser.unpack_string(),
            users=[
                SimilarUser(username=parser.unpack_string())
                for _ in range(parser.unpack_uint32())
            ]
        )
        return msg


@dataclass(slots=True, eq=False, repr=False)
class RoomTickers(ServerMessage):
    """The server returns a list of tickers in a chat room.

    Tickers are customizable, user-specific messages that appear on chat
    room walls.
    """

    CODE = 113
    EVENT_NAME = "room-tickers"

    room_name: str
    tickers: list[RoomTicker]

    @classmethod
    def unpack(cls, parser: MessageParser) -> Self:
        msg = cls(
            room_name=parser.unpack_string(),
            tickers=[
                RoomTicker(
                    username=parser.unpack_string(),
                    message=parser.unpack_string()
                )
                for _ in range(parser.unpack_uint32())
            ]
        )
        return msg


@dataclass(slots=True, eq=False, repr=False)
class RoomTickerAdded(ServerMessage):
    """The server sends us a new ticker that was added to a chat room.

    Tickers are customizable, user-specific messages that appear on chat
    room walls.
    """

    CODE = 114
    EVENT_NAME = "room-ticker-added"

    room_name: str
    ticker: RoomTicker

    @classmethod
    def unpack(cls, parser: MessageParser) -> Self:
        msg = cls(
            room_name=parser.unpack_string(),
            ticker=RoomTicker(
                username=parser.unpack_string(),
                message=parser.unpack_string()
            )
        )
        return msg


@dataclass(slots=True, eq=False, repr=False)
class RoomTickerRemoved(ServerMessage):
    """The server informs us that a ticker was removed from a chat room.

    Tickers are customizable, user-specific messages that appear on chat
    room walls.
    """

    CODE = 115
    EVENT_NAME = "room-ticker-removed"

    room_name: str
    username: str

    @classmethod
    def unpack(cls, parser: MessageParser) -> Self:
        msg = cls(
            room_name=parser.unpack_string(),
            username=parser.unpack_string()
        )
        return msg


@dataclass(slots=True, eq=False, repr=False)
class SetRoomTicker(ServerMessage):
    """We send this to the server when we change our own ticker in a chat
    room. Sending an empty ticker string removes any existing ticker in
    the room.

    Tickers are customizable, user-specific messages that appear on chat
    room walls.
    """

    CODE = 116

    room_name: str
    message: str

    def pack(self) -> bytearray:
        msg = bytearray()
        msg += pack_string(self.room_name)
        msg += pack_string(self.message)

        return msg


@dataclass(slots=True, eq=False, repr=False)
class AddThingIHate(ServerMessage):
    """We send this to the server when we add an item to our hate list."""

    CODE = 117

    item: str

    def pack(self) -> bytes:
        return pack_string(self.item)


@dataclass(slots=True, eq=False, repr=False)
class RemoveThingIHate(ServerMessage):
    """We send this to the server when we remove an item from our hate
    list.
    """

    CODE = 118

    item: str

    def pack(self) -> bytes:
        return pack_string(self.item)


@dataclass(slots=True, eq=False, repr=False)
class RoomSearch(ServerMessage):
    """We send this to the server to search files shared by users who have
    joined a specific chat room. The token is a number generated by the
    client and is used to track the search results.

    Room users receive the search request in the form of a FileSearch
    message.
    """

    CODE = 120

    room_name: str
    token: int
    search_term: str

    def pack(self) -> bytearray:
        msg = bytearray()
        msg += pack_string(self.room_name)
        msg += pack_uint32(self.token)
        msg += pack_string(self.search_term)

        return msg


@dataclass(slots=True, eq=False, repr=False)
class SendUploadSpeed(ServerMessage):
    """We send this after a finished upload to let the server update the
    speed statistics for ourselves.
    """

    CODE = 121

    speed: int

    def pack(self) -> bytes:
        return pack_uint32(self.speed)


@dataclass(slots=True, eq=False, repr=False)
class UserPrivileged(ServerMessage):
    """We ask the server whether a user is privileged or not.

    DEPRECATED, use WatchUser and GetUserStatus server messages
    """

    CODE = 122

    username: str
    privileged: bool = False

    def pack(self) -> bytes:
        return pack_string(self.username)

    @classmethod
    def unpack(cls, parser: MessageParser) -> Self:
        msg = cls(
            username=parser.unpack_string(),
            privileged=parser.unpack_bool()
        )
        return msg


@dataclass(slots=True, eq=False, repr=False)
class GivePrivileges(ServerMessage):
    """We give (part of) our privileges, specified in days, to another user
    on the network.
    """

    CODE = 123

    username: str
    days: int

    def pack(self) -> bytearray:
        msg = bytearray()
        msg += pack_string(self.username)
        msg += pack_uint32(self.days)

        return msg


@dataclass(slots=True, eq=False, repr=False)
class NotifyPrivileges(ServerMessage):
    """DEPRECATED, sent by Soulseek NS but not SoulseekQt"""

    CODE = 124

    token: int
    username: str

    def pack(self) -> bytearray:
        msg = bytearray()
        msg += pack_uint32(self.token)
        msg += pack_string(self.username)

        return msg

    @classmethod
    def unpack(cls, parser: MessageParser) -> Self:
        msg = cls(
            token=parser.unpack_uint32(),
            username=parser.unpack_string()
        )
        return msg


@dataclass(slots=True, eq=False, repr=False)
class AckNotifyPrivileges(ServerMessage):
    """DEPRECATED, no longer used"""

    CODE = 125

    token: int

    def pack(self) -> bytes:
        return pack_uint32(self.token)

    @classmethod
    def unpack(cls, parser: MessageParser) -> Self:
        msg = cls(
            token=parser.unpack_uint32()
        )
        return msg


@dataclass(slots=True, eq=False, repr=False)
class BranchLevel(ServerMessage):
    """We tell the server what our position is in our branch (nth generation) in
    the distributed network.
    """

    CODE = 126

    level: int

    def pack(self) -> bytes:
        return pack_uint32(self.level)


@dataclass(slots=True, eq=False, repr=False)
class BranchRoot(ServerMessage):
    """We tell the server the username of the root of the branch we’re in in the
    distributed network.
    """

    CODE = 127

    username: str

    def pack(self) -> bytes:
        return pack_string(self.username)


@dataclass(slots=True, eq=False, repr=False)
class ChildDepth(ServerMessage):
    """When we are a branch root in the distributed network, and receive a
    DistribChildDepth message from a child peer, we increment the depth and
    send this final value to the server.

    This message is obsolete. While Soulseek NS sends the correct value to the
    server, SoulseekQt doesn't implement this message correctly, always sending
    a uint8 value of 1 instead. Presumably, the server has opted to calculate
    child depths on its own, based on branch level/root information sent by
    peers.

    OBSOLETE, no longer used
    """

    CODE = 129

    depth: int

    def pack(self) -> bytes:
        return pack_uint32(self.depth)


class ResetDistributed(ServerMessage):
    """The server asks us to reset our distributed parent and children."""

    CODE = 130

    @classmethod
    def unpack(cls, _parser: MessageParser) -> Self:
        return cls()


@dataclass(slots=True, eq=False, repr=False)
class RoomMembers(ServerMessage):
    """The server sends us a list of members (excluding the owner) in a private
    room we are in.
    """

    CODE = 133
    EVENT_NAME = "room-members"

    room_name: str
    members: list[str]

    @classmethod
    def unpack(cls, parser: MessageParser) -> Self:
        msg = cls(
            room_name=parser.unpack_string(),
            members=parser.unpack_strings()
        )
        return msg


@dataclass(slots=True, eq=False, repr=False)
class AddRoomMember(ServerMessage):
    """We send this to the server to add a member to a private room, if we are
    the owner or an operator.

    The server tells us a member has been added to a private room we are in.
    """

    CODE = 134
    EVENT_NAME = "add-room-member"

    room_name: str
    username: str

    def pack(self) -> bytearray:
        msg = bytearray()
        msg += pack_string(self.room_name)
        msg += pack_string(self.username)

        return msg

    @classmethod
    def unpack(cls, parser: MessageParser) -> Self:
        msg = cls(
            room_name=parser.unpack_string(),
            username=parser.unpack_string()
        )
        return msg


@dataclass(slots=True, eq=False, repr=False)
class RemoveRoomMember(ServerMessage):
    """We send this to the server to remove a member from a private room, if we
    are the owner or an operator. Owners can remove operators and regular
    members, operators can only remove regular members.

    The server tells us a member has been removed from a private room we are in.
    """

    CODE = 135
    EVENT_NAME = "remove-room-member"

    room_name: str
    username: str

    def pack(self) -> bytearray:
        msg = bytearray()
        msg += pack_string(self.room_name)
        msg += pack_string(self.username)

        return msg

    @classmethod
    def unpack(cls, parser: MessageParser) -> Self:
        msg = cls(
            room_name=parser.unpack_string(),
            username=parser.unpack_string()
        )
        return msg


@dataclass(slots=True, eq=False, repr=False)
class CancelRoomMembership(ServerMessage):
    """We send this to the server to cancel our own membership of a private room."""

    CODE = 136

    room_name: str

    def pack(self) -> bytes:
        return pack_string(self.room_name)


@dataclass(slots=True, eq=False, repr=False)
class CancelRoomOwnership(ServerMessage):
    """We send this to the server to stop owning a private room."""

    CODE = 137

    room_name: str

    def pack(self) -> bytes:
        return pack_string(self.room_name)


@dataclass(slots=True, eq=False, repr=False)
class RoomSomething(ServerMessage):
    """OBSOLETE, no longer used"""

    CODE = 138

    room_name: str

    def pack(self) -> bytes:
        return pack_string(self.room_name)

    @classmethod
    def unpack(cls, parser: MessageParser) -> Self:
        msg = cls(
            room_name=parser.unpack_string()
        )
        return msg


@dataclass(slots=True, eq=False, repr=False)
class RoomMembershipGranted(ServerMessage):
    """The server tells us we were added to a private room."""

    CODE = 139
    EVENT_NAME = "room-membership-granted"

    room_name: str

    @classmethod
    def unpack(cls, parser: MessageParser) -> Self:
        msg = cls(
            room_name=parser.unpack_string()
        )
        return msg


@dataclass(slots=True, eq=False, repr=False)
class RoomMembershipRevoked(ServerMessage):
    """The server tells us we were removed from a private room."""

    CODE = 140
    EVENT_NAME = "room-membership-revoked"

    room_name: str

    @classmethod
    def unpack(cls, parser: MessageParser) -> Self:
        msg = cls(
            room_name=parser.unpack_string()
        )
        return msg


@dataclass(slots=True, eq=False, repr=False)
class EnableRoomInvitations(ServerMessage):
    """We send this when we want to enable or disable invitations to
    private rooms.
    """

    CODE = 141
    EVENT_NAME = "enable-room-invitations"

    enable: bool

    def pack(self) -> bytes:
        return pack_bool(self.enable)

    @classmethod
    def unpack(cls, parser: MessageParser) -> Self:
        msg = cls(
            enable=parser.unpack_bool()
        )
        return msg


@dataclass(slots=True, eq=False, repr=False)
class ChangePassword(ServerMessage):
    """We send this to the server to change our password. We receive a
    response if our password changes.
    """

    CODE = 142
    EVENT_NAME = "change-password"

    password: str = field(repr=False)

    def pack(self) -> bytes:
        return pack_string(self.password)

    @classmethod
    def unpack(cls, parser: MessageParser) -> Self:
        msg = cls(
            password=parser.unpack_string()
        )
        return msg


@dataclass(slots=True, eq=False, repr=False)
class AddRoomOperator(ServerMessage):
    """We send this to the server to add private room operator abilities to
    a member.

    The server tells us a member received operator abilities in a private
    room we are in.
    """

    CODE = 143
    EVENT_NAME = "add-room-operator"

    room_name: str
    username: str

    def pack(self) -> bytearray:
        msg = bytearray()
        msg += pack_string(self.room_name)
        msg += pack_string(self.username)

        return msg

    @classmethod
    def unpack(cls, parser: MessageParser) -> Self:
        msg = cls(
            room_name=parser.unpack_string(),
            username=parser.unpack_string()
        )
        return msg


@dataclass(slots=True, eq=False, repr=False)
class RemoveRoomOperator(ServerMessage):
    """We send this to the server to remove private room operator abilities
    from a member.

    The server tells us operator abilities were removed for a member in a
    private room we are in.
    """

    CODE = 144
    EVENT_NAME = "remove-room-operator"

    room_name: str
    username: str

    def pack(self) -> bytearray:
        msg = bytearray()
        msg += pack_string(self.room_name)
        msg += pack_string(self.username)

        return msg

    @classmethod
    def unpack(cls, parser: MessageParser) -> Self:
        msg = cls(
            room_name=parser.unpack_string(),
            username=parser.unpack_string()
        )
        return msg


@dataclass(slots=True, eq=False, repr=False)
class RoomOperatorshipGranted(ServerMessage):
    """The server tells us we were given operator abilities in a private room
    we are in.
    """

    CODE = 145
    EVENT_NAME = "room-operatorship-granted"

    room_name: str

    @classmethod
    def unpack(cls, parser: MessageParser) -> Self:
        msg = cls(
            room_name=parser.unpack_string()
        )
        return msg


@dataclass(slots=True, eq=False, repr=False)
class RoomOperatorshipRevoked(ServerMessage):
    """The server tells us our operator abilities were removed in a private room
    we are in.
    """

    CODE = 146
    EVENT_NAME = "room-operatorship-revoked"

    room_name: str

    def pack(self) -> bytes:
        return pack_string(self.room_name)

    @classmethod
    def unpack(cls, parser: MessageParser) -> Self:
        msg = cls(
            room_name=parser.unpack_string()
        )
        return msg


@dataclass(slots=True, eq=False, repr=False)
class RoomOperators(ServerMessage):
    """The server sends us a list of operators in a private room we are in."""

    CODE = 148
    EVENT_NAME = "room-operators"

    room_name: str
    operators: list[str]

    @classmethod
    def unpack(cls, parser: MessageParser) -> Self:
        msg = cls(
            room_name=parser.unpack_string(),
            operators=parser.unpack_strings()
        )
        return msg


@dataclass(slots=True, eq=False, repr=False)
class MessageUsers(ServerMessage):
    """Sends a broadcast private message to the given list of online users."""

    CODE = 149

    usernames: list[str]
    message: str

    def pack(self) -> bytearray:
        msg = bytearray()
        msg += pack_uint32(len(self.usernames))

        for username in self.usernames:
            msg += pack_string(username)

        msg += pack_string(self.message)
        return msg


@dataclass(slots=True, eq=False, repr=False)
class JoinGlobalRoom(ServerMessage):
    """We ask the server to send us messages from all public rooms, also
    known as public room feed.
    """

    CODE = 150

    def pack(self) -> bytes:
        return b""


@dataclass(slots=True, eq=False, repr=False)
class LeaveGlobalRoom(ServerMessage):
    """We ask the server to stop sending us messages from all public rooms,
    also known as public room feed.
    """

    CODE = 151

    def pack(self) -> bytes:
        return b""


@dataclass(slots=True, eq=False, repr=False)
class GlobalRoomMessage(ServerMessage):
    """The server sends this when a new message has been written in the
    public room feed (every single line written in every public room).
    """

    CODE = 152
    EVENT_NAME = "global-room-message"

    room_name: str
    username: str
    message: str
    message_type: str | None = None
    mention_type: str | None = None
    mention_keyword: str | None = None

    @classmethod
    def unpack(cls, parser: MessageParser) -> Self:
        msg = cls(
            room_name=parser.unpack_string(),
            username=parser.unpack_string(),
            message=parser.unpack_string()
        )
        return msg


@dataclass(slots=True, eq=False, repr=False)
class RelatedSearch(ServerMessage):
    """The server returns a list of related search terms for a search
    query.

    OBSOLETE, server sends empty list as of 2018
    """

    CODE = 153

    search_term: str
    related_terms: list[RelatedSearchTerm] = field(default_factory=list[RelatedSearchTerm])

    def pack(self) -> bytes:
        return pack_string(self.search_term)

    @classmethod
    def unpack(cls, parser: MessageParser) -> Self:
        msg = cls(
            search_term=parser.unpack_string(),
            related_terms=[
                RelatedSearchTerm(
                    term=parser.unpack_string(),
                    score=parser.unpack_uint32()
                )
                for _ in range(parser.unpack_uint32())
            ]
        )
        return msg


@dataclass(slots=True, eq=False, repr=False)
class ExcludedSearchPhrases(ServerMessage):
    """The server sends a list of phrases not allowed on the search network.
    File paths containing such phrases should be excluded when responding
    to search requests.
    """

    CODE = 160
    EVENT_NAME = "excluded-search-phrases"

    phrases: list[str]

    @classmethod
    def unpack(cls, parser: MessageParser) -> Self:
        msg = cls(
            phrases=parser.unpack_strings()
        )
        return msg


@dataclass(slots=True, eq=False, repr=False)
class CantConnectToPeer(ServerMessage):
    """We send this when we are not able to respond to an indirect connection
    request. We receive this if a peer was not able to respond to our
    indirect connection request. The token is taken from the ConnectToPeer
    message.

    Do not rely on receiving this message from peers. Keep a local timeout
    for indirect connections as well.
    """

    CODE = 1001

    token: int
    username: str

    def pack(self) -> bytearray:
        msg = bytearray()
        msg += pack_uint32(self.token)
        msg += pack_string(self.username)

        return msg

    @classmethod
    def unpack(cls, parser: MessageParser) -> Self:
        msg = cls(
            token=parser.unpack_uint32(),
            username=UNSET
        )
        return msg


@dataclass(slots=True, eq=False, repr=False)
class CantCreateRoom(ServerMessage):
    """Server tells us a new room cannot be created. This message only
    seems to be sent if we try to create a room with the same name as
    an existing private room. In other cases, such as using a room name
    with leading or trailing spaces, only a private message containing
    an error message is sent.
    """

    CODE = 1003

    room_name: str

    @classmethod
    def unpack(cls, parser: MessageParser) -> Self:
        msg = cls(
            room_name=parser.unpack_string()
        )
        return msg


# Peer Init Messages #


@dataclass(slots=True, eq=False, repr=False, kw_only=True)
class PeerInitMessage(SlskMessage):
    TYPE = MessageType.INIT

    sock: socket | None = None


@dataclass(slots=True, eq=False, repr=False)
class PierceFireWall(PeerInitMessage):
    """This message is sent in response to an indirect connection request
    from another user. If the message goes through to the user, the
    connection is ready. The token is taken from the ConnectToPeer
    server message.
    """

    CODE = 0

    token: int

    def pack(self) -> bytes:
        return pack_uint32(self.token)

    @classmethod
    def unpack(cls, parser: MessageParser) -> Self:
        msg = cls(
            token=parser.unpack_uint32()
        )
        return msg


@dataclass(slots=True, eq=False, repr=False)
class PeerInit(PeerInitMessage):
    """This message is sent to initiate a direct connection to another peer. The
    token is always zero and ignored today, but used to be non-zero and
    included in a concurrent SendConnectToken server message for connection
    verification.
    """

    CODE = 1

    conn_type: str
    init_username: str = UNSET      # our own username
    target_username: str = UNSET    # username of peer we're connected to
    target_username_size: int = -1  # in bytes
    indirect_token: int | None = None
    indirect_request_time: int | None = None
    outgoing_msgs: list[SlskMessage] = field(default_factory=list[SlskMessage])

    def pack(self) -> bytearray:
        msg = bytearray()
        msg += pack_string(self.init_username)
        msg += pack_string(self.conn_type)
        msg += pack_uint32(0)  # Empty token

        return msg

    @classmethod
    def unpack(cls, parser: MessageParser) -> Self:
        msg = cls(
            init_username=UNSET,
            target_username=parser.unpack_string(),
            target_username_size=parser.offset - 4,
            conn_type=parser.unpack_string()
        )
        return msg


# Peer Messages #


@dataclass(slots=True, eq=False, repr=False)
class PeerMessage(SlskMessage):
    TYPE = MessageType.PEER

    username: str = field(init=False, default="")
    sock: socket | None = field(init=False, default=None)
    addr: Address | None = field(init=False, default=None)


@dataclass(slots=True, eq=False, repr=False)
class SharedFileListRequest(PeerMessage):
    """We send this to a peer to ask for a list of shared files."""

    CODE = 4
    EVENT_NAME = "shared-file-list-request"

    def pack(self) -> bytes:
        return b""

    @classmethod
    def unpack(cls, _parser: MessageParser) -> Self:
        return cls()


@dataclass(slots=True, eq=False, repr=False)
class SharedFileListResponse(PeerMessage):
    """A peer responds with a list of shared files when we've sent a
    SharedFileListRequest.
    """

    CODE = 5
    EVENT_NAME = "shared-file-list-response"

    public_folders: list[tuple[str, list[SharedFile]]] = field(
        default_factory=list[tuple[str, list[SharedFile]]], repr=False
    )
    private_folders: list[tuple[str, list[SharedFile]]] = field(
        default_factory=list[tuple[str, list[SharedFile]]], repr=False
    )
    unknown: int | None = None

    permission_level: int | None = field(default=None, repr=False)
    cached_response: bytes | None = field(default=None, repr=False)
    public_shares: Database | None = field(default=None, repr=False)
    buddy_shares: Database | None = field(default=None, repr=False)
    trusted_shares: Database | None = field(default=None, repr=False)

    def pack(self) -> bytes:
        if self.cached_response is not None:
            return self.cached_response

        from pynicotine.shares import PermissionLevel

        public_share_groups = []
        private_share_groups = []

        if self.permission_level and self.public_shares:
            public_share_groups.append(self.public_shares)

        if self.permission_level in {PermissionLevel.BUDDY, PermissionLevel.TRUSTED} and self.buddy_shares:
            public_share_groups.append(self.buddy_shares)

        if self.permission_level == PermissionLevel.TRUSTED and self.trusted_shares:
            public_share_groups.append(self.trusted_shares)

        for shares in (self.buddy_shares, self.trusted_shares):
            if shares and shares not in public_share_groups:
                private_share_groups.append(shares)

        num_public_folders = sum(len(shares) for shares in public_share_groups)
        num_private_folders = sum(len(shares) for shares in private_share_groups)

        msg = bytearray()
        msg += pack_uint32(num_public_folders)

        for shares in public_share_groups:
            for folder_path in shares:
                msg += pack_string(folder_path)
                msg += shares[folder_path]

        msg += pack_uint32(self.unknown or 0)
        msg += pack_uint32(num_private_folders)

        for shares in private_share_groups:
            for folder_path in shares:
                msg += pack_string(folder_path)
                msg += shares[folder_path]

        self.cached_response = zlib.compress(msg, ZLIB_COMPRESSION_LEVEL)
        return self.cached_response

    @classmethod
    def unpack(cls, parser: MessageParser) -> Self:
        decompressor = zlib.decompressobj()
        max_uncompressed_size = 2147483648  # 2 GiB total
        parser.content = memoryview(decompressor.decompress(parser.content, max_uncompressed_size))

        if not decompressor.eof:
            raise ValueError("Compressed message invalid or too large")

        msg = cls()
        msg.public_folders = [
            (
                parser.unpack_string(),  # folder_path
                parser.unpack_files()
            )
            for _ in range(parser.unpack_uint32())
        ]
        if len(msg.public_folders) > 1:
            msg.public_folders.sort(key=itemgetter(0))

        if parser.has_remaining_content():
            msg.unknown = parser.unpack_uint32()

        if not parser.has_remaining_content():
            return msg

        msg.private_folders = [
            (
                parser.unpack_string(),  # folder_path
                parser.unpack_files()
            )
            for _ in range(parser.unpack_uint32())
        ]
        if len(msg.private_folders) > 1:
            msg.private_folders.sort(key=itemgetter(0))

        return msg


@dataclass(slots=True, eq=False, repr=False)
class FileSearchRequest(PeerMessage):
    """We send this to the peer when we search for a file. Alternatively,
    the peer sends this to tell us it is searching for a file.

    OBSOLETE, superseded by UserSearch server message
    """

    CODE = 8

    token: int
    search_term: str

    def pack(self) -> bytearray:
        msg = bytearray()
        msg += pack_uint32(self.token)
        msg += pack_string(self.search_term)

        return msg

    @classmethod
    def unpack(cls, parser: MessageParser) -> Self:
        msg = cls(
            token=parser.unpack_uint32(),
            search_term=parser.unpack_string()
        )
        return msg


@dataclass(slots=True, eq=False, repr=False)
class FileSearchResponse(PeerMessage):
    """A peer sends this message when it has a file search match. The token
    is taken from original FileSearch, UserSearch or RoomSearch server
    message.
    """

    CODE = 9
    EVENT_NAME = "file-search-response"

    search_username: str
    token: int
    slot_available: bool
    upload_speed: int
    num_queued_uploads: int
    unknown: int | None = None
    is_rejected: bool = False
    public_files: list[SharedFile] = field(default_factory=list[SharedFile], repr=False)
    private_files: list[SharedFile] = field(default_factory=list[SharedFile], repr=False)

    public_shares: list[FileInfo] = field(default_factory=list["FileInfo"], repr=False)
    private_shares: list[FileInfo] = field(default_factory=list["FileInfo"], repr=False)

    def pack(self) -> bytes:
        msg = bytearray()
        msg += pack_string(self.search_username)
        msg += pack_uint32(self.token)
        msg += pack_uint32(len(self.public_shares))

        for fileinfo in self.public_shares:
            msg += pack_file_info(fileinfo)

        msg += pack_bool(self.slot_available)
        msg += pack_uint32(self.upload_speed)
        msg += pack_uint32(self.num_queued_uploads)
        msg += pack_uint32(self.unknown or 0)
        msg += pack_uint32(len(self.private_shares))

        for fileinfo in self.private_shares:
            msg += pack_file_info(fileinfo)

        return zlib.compress(msg, ZLIB_COMPRESSION_LEVEL)

    @classmethod
    def unpack(cls, parser: MessageParser) -> Self:
        decompressor = zlib.decompressobj()
        message_bytes = decompressor.decompress(parser.content, 4)
        parser.content = memoryview(message_bytes)

        username_len = parser.unpack_uint32()
        max_uncompressed_size = 134217728 - username_len - 8  # 128 MiB total

        if max_uncompressed_size <= 0:
            raise ValueError("Compressed message too large")

        message_bytes += decompressor.decompress(decompressor.unconsumed_tail, username_len + 4)
        parser.content = memoryview(message_bytes)
        parser.offset = 0

        msg = cls(
            search_username=parser.unpack_string(),
            token=parser.unpack_uint32(),
            slot_available=False,
            upload_speed=-1,
            num_queued_uploads=-1
        )

        if parser.allowed_ids and msg.token not in parser.allowed_ids:
            msg.is_rejected = True
            return msg

        # Optimization: only decompress the rest of the message when needed
        parser.offset = 0
        parser.content = memoryview(decompressor.decompress(decompressor.unconsumed_tail, max_uncompressed_size))

        if not decompressor.eof:
            raise ValueError("Compressed message invalid or too large")

        msg.public_files = parser.unpack_files()
        msg.slot_available = parser.unpack_bool()
        msg.upload_speed = parser.unpack_uint32()
        msg.num_queued_uploads = parser.unpack_uint32()

        if parser.has_remaining_content():
            msg.unknown = parser.unpack_uint32()

        if parser.has_remaining_content():
            msg.private_files = parser.unpack_files()

        return msg


@dataclass(slots=True, eq=False, repr=False)
class UserInfoRequest(PeerMessage):
    """We ask the other peer to send us their user information, picture and
    all.
    """

    CODE = 15
    EVENT_NAME = "user-info-request"

    def pack(self) -> bytes:
        return b""

    @classmethod
    def unpack(cls, _parser: MessageParser) -> Self:
        return cls()


@dataclass(slots=True, eq=False, repr=False)
class UserInfoResponse(PeerMessage):
    """A peer responds with this after we've sent a UserInfoRequest."""

    CODE = 16
    EVENT_NAME = "user-info-response"

    description: str
    num_upload_slots: int
    num_queued_uploads: int
    slot_available: bool
    upload_permission: int | None
    picture: bytes | None = field(default=None, repr=False)

    def pack(self) -> bytearray:
        msg = bytearray()
        msg += pack_string(self.description)

        if self.picture is not None:
            msg += pack_bool(True)
            msg += pack_uint32(len(self.picture))
            msg += self.picture
        else:
            msg += pack_bool(False)

        msg += pack_uint32(self.num_upload_slots)
        msg += pack_uint32(self.num_queued_uploads)
        msg += pack_bool(self.slot_available)
        msg += pack_uint32(self.upload_permission or 0)

        return msg

    @classmethod
    def unpack(cls, parser: MessageParser) -> Self:
        msg = cls(
            description=parser.unpack_string(),
            picture=parser.unpack_bytes() if parser.unpack_bool() else None,
            num_upload_slots=parser.unpack_uint32(),
            num_queued_uploads=parser.unpack_uint32(),
            slot_available=parser.unpack_bool(),
            upload_permission=None
        )

        # To prevent errors, ensure that >= 4 bytes are left. Museek+ incorrectly sends
        # slot_available as an integer, resulting in 3 bytes of garbage here.
        if len(parser.content[parser.offset:]) >= 4:
            msg.upload_permission = parser.unpack_uint32()

        return msg


@dataclass(slots=True, eq=False, repr=False)
class FolderContentsRequest(PeerMessage):
    """We ask the peer to send us the contents of a single folder."""

    CODE = 36
    EVENT_NAME = "folder-contents-request"

    token: int
    folder_path: str
    legacy_client: bool = False

    def pack(self) -> bytearray:
        msg = bytearray()
        msg += pack_uint32(self.token)
        msg += pack_string(self.folder_path, is_legacy=self.legacy_client)

        return msg

    @classmethod
    def unpack(cls, parser: MessageParser) -> Self:
        msg = cls(
            token=parser.unpack_uint32(),
            folder_path=parser.unpack_string()
        )
        return msg


@dataclass(slots=True, eq=False, repr=False)
class FolderContentsResponse(PeerMessage):
    """A peer responds with the contents of a particular folder (with all
    subfolders) after we've sent a FolderContentsRequest.
    """

    CODE = 37
    EVENT_NAME = "folder-contents-response"

    token: int
    folder_path: str
    is_rejected: bool = False
    folders: list[tuple[str, list[SharedFile]]] = field(
        default_factory=list[tuple[str, list[SharedFile]]], repr=False
    )

    stream: bytearray | None = field(default=None, repr=False)

    def pack(self) -> bytes:
        msg = bytearray()
        msg += pack_uint32(self.token)
        msg += pack_string(self.folder_path)

        if self.stream is not None:
            msg += pack_uint32(1)
            msg += pack_string(self.folder_path)

            # We already saved the folder contents as a bytearray when scanning our shares
            msg += self.stream
        else:
            # No folder contents
            msg += pack_uint32(0)

        return zlib.compress(msg, ZLIB_COMPRESSION_LEVEL)

    @classmethod
    def unpack(cls, parser: MessageParser) -> Self:
        decompressor = zlib.decompressobj()
        message_bytes = decompressor.decompress(parser.content, 8)
        parser.content = memoryview(message_bytes)

        token = parser.unpack_uint32()
        folder_path_len = parser.unpack_uint32()
        max_uncompressed_size = 134217728 - folder_path_len - 8  # 128 MiB total

        if max_uncompressed_size <= 0:
            raise ValueError("Compressed message too large")

        if folder_path_len:
            message_bytes += decompressor.decompress(decompressor.unconsumed_tail, folder_path_len)
            parser.content = memoryview(message_bytes)

        parser.offset = 4  # Skip token

        msg = cls(
            token=token,
            folder_path=parser.unpack_string()
        )

        if (parser.allowed_ids and parser.source is not None
                and parser.source + msg.folder_path not in parser.allowed_ids):
            msg.is_rejected = True
            return msg

        # Optimization: only decompress the rest of the message when needed
        parser.offset = 0
        parser.content = memoryview(decompressor.decompress(decompressor.unconsumed_tail, max_uncompressed_size))

        if not decompressor.eof:
            raise ValueError("Compressed message invalid or too large")

        msg.folders = [
            (parser.unpack_string(), parser.unpack_files())
            for _ in range(parser.unpack_uint32())
        ]
        return msg


@dataclass(slots=True, eq=False, repr=False)
class TransferRequest(PeerMessage):
    """This message is sent by a peer once they are ready to start
    uploading a file. A TransferResponse message is expected from the
    recipient, either allowing or rejecting the upload attempt.

    This message was formerly used to send a download request (direction
    0) as well, but Nicotine+ >= 3.0.3, Museek+ and the official clients
    use the QueueUpload message for this purpose today.  Clients like
    slskd and Seeker still use this method for downloading, so we need to
    ensure we still understand such requests.
    """

    CODE = 40
    EVENT_NAME = "transfer-request"

    direction: int
    token: int
    file_path: str
    file_size: int | None = None

    def pack(self) -> bytearray:
        msg = bytearray()
        msg += pack_uint32(self.direction)
        msg += pack_uint32(self.token)
        msg += pack_string(self.file_path)

        if self.direction == TransferDirection.UPLOAD:
            if self.file_size is None:
                raise TypeError("'file_size' argument is required")

            msg += pack_uint64(self.file_size)

        return msg

    @classmethod
    def unpack(cls, parser: MessageParser) -> Self:
        msg = cls(
            direction=parser.unpack_uint32(),
            token=parser.unpack_uint32(),
            file_path=parser.unpack_string()
        )

        if msg.direction == TransferDirection.UPLOAD:
            msg.file_size = parser.unpack_uint64()

        return msg


@dataclass(slots=True, eq=False, repr=False)
class TransferResponse(PeerMessage):
    """Response to TransferRequest - We either accept the transfer request,
    or tell the reason for rejecting it.

    Note that accepting a download request is discouraged, since it allows
    a possibly spoofed peer to initialize the file transfer connection
    from their end. Reject the download request with a 'Queued' reason, add
    the ile to the upload queue, and start the next upload as usual, since
    it ensures a connection attempt to a valid user address provided by the
    server.
    """

    CODE = 41
    EVENT_NAME = "transfer-response"

    token: int
    allowed: bool
    reason: str | None = None
    file_size: int | None = None

    def pack(self) -> bytearray:
        msg = bytearray()
        msg += pack_uint32(self.token)
        msg += pack_bool(self.allowed)

        if not self.allowed:
            if self.reason is None:
                raise TypeError("'reason' argument is required")

            msg += pack_string(self.reason)

        elif self.file_size is not None:
            msg += pack_uint64(self.file_size)

        return msg

    @classmethod
    def unpack(cls, parser: MessageParser) -> Self:
        msg = cls(
            token=parser.unpack_uint32(),
            allowed=parser.unpack_bool()
        )

        if not msg.allowed:
            msg.reason = parser.unpack_string()

        elif parser.has_remaining_content():
            msg.file_size = parser.unpack_uint64()

        return msg


@dataclass(slots=True, eq=False, repr=False)
class PlaceholdUpload(PeerMessage):
    """OBSOLETE, no longer used"""

    CODE = 42

    file_path: str

    def pack(self) -> bytes:
        return pack_string(self.file_path)

    @classmethod
    def unpack(cls, parser: MessageParser) -> Self:
        msg = cls(
            file_path=parser.unpack_string()
        )
        return msg


@dataclass(slots=True, eq=False, repr=False)
class QueueUpload(PeerMessage):
    """This message is used to tell a peer that an upload should be queued
    on their end. Once the recipient is ready to transfer the requested
    file, they will send a TransferRequest to us.
    """

    CODE = 43
    EVENT_NAME = "queue-upload"

    file_path: str
    legacy_client: bool = False

    def pack(self) -> bytes:
        return pack_string(self.file_path, is_legacy=self.legacy_client)

    @classmethod
    def unpack(cls, parser: MessageParser) -> Self:
        msg = cls(
            file_path=parser.unpack_string()
        )
        return msg


@dataclass(slots=True, eq=False, repr=False)
class PlaceInQueueResponse(PeerMessage):
    """The peer replies with the upload queue placement of the requested
    file.
    """

    CODE = 44
    EVENT_NAME = "place-in-queue-response"

    file_path: str
    place: int

    def pack(self) -> bytearray:
        msg = bytearray()
        msg += pack_string(self.file_path)
        msg += pack_uint32(self.place)

        return msg

    @classmethod
    def unpack(cls, parser: MessageParser) -> Self:
        msg = cls(
            file_path=parser.unpack_string(),
            place=parser.unpack_uint32()
        )
        return msg


@dataclass(slots=True, eq=False, repr=False)
class UploadFailed(PeerMessage):
    """This message is sent whenever a file connection of an active upload
    closes. Soulseek NS clients can also send this message when a file
    cannot be read. The recipient either re-queues the upload (download
    on their end), or ignores the message if the transfer finished.
    """

    CODE = 46
    EVENT_NAME = "upload-failed"

    file_path: str

    def pack(self) -> bytes:
        return pack_string(self.file_path)

    @classmethod
    def unpack(cls, parser: MessageParser) -> Self:
        msg = cls(
            file_path=parser.unpack_string()
        )
        return msg


@dataclass(slots=True, eq=False, repr=False)
class UploadDenied(PeerMessage):
    """This message is sent to reject QueueUpload attempts and previously
    queued files. The reason for rejection will appear in the transfer
    list of the recipient.
    """

    CODE = 50
    EVENT_NAME = "upload-denied"

    file_path: str
    reason: str

    def pack(self) -> bytearray:
        msg = bytearray()
        msg += pack_string(self.file_path)
        msg += pack_string(self.reason)

        return msg

    @classmethod
    def unpack(cls, parser: MessageParser) -> Self:
        msg = cls(
            file_path=parser.unpack_string(),
            reason=parser.unpack_string()
        )
        return msg


@dataclass(slots=True, eq=False, repr=False)
class PlaceInQueueRequest(PeerMessage):
    """This message is sent when asking for the upload queue placement of a
    file.
    """

    CODE = 51
    EVENT_NAME = "place-in-queue-request"

    file_path: str
    legacy_client: bool = False

    def pack(self) -> bytes:
        return pack_string(self.file_path, is_legacy=self.legacy_client)

    @classmethod
    def unpack(cls, parser: MessageParser) -> Self:
        msg = cls(
            file_path=parser.unpack_string()
        )
        return msg


@dataclass(slots=True, eq=False, repr=False)
class UploadQueueNotification(PeerMessage):
    """This message is sent to inform a peer about an upload attempt
    initiated by us.

    DEPRECATED, sent by Soulseek NS but not SoulseekQt
    """

    CODE = 52

    def pack(self) -> bytes:
        return b""

    @classmethod
    def unpack(cls, _parser: MessageParser) -> Self:
        return cls()


@dataclass(slots=True, eq=False, repr=False)
class UnknownPeerMessage(PeerMessage):
    """UNKNOWN"""

    CODE = 12547
    LOGGED = False

    @classmethod
    def unpack(cls, _parser: MessageParser) -> Self:
        return cls()


# File Messages #


@dataclass(slots=True, eq=False, repr=False, kw_only=True)
class FileMessage(SlskMessage):
    TYPE = MessageType.FILE

    sock: socket | None = None
    username: str = field(init=False, default="")


@dataclass(slots=True, eq=False, repr=False)
class FileTransferInit(FileMessage):
    """We send this to a peer via a 'F' connection to tell them that we want to
    start uploading a file. The token is the same as the one previously included in the
    TransferRequest peer message.
    """

    token: int

    def pack(self) -> bytes:
        return pack_uint32(self.token)

    @classmethod
    def unpack(cls, parser: MessageParser) -> Self:
        msg = cls(
            token=parser.unpack_uint32()
        )
        return msg


@dataclass(slots=True, eq=False, repr=False)
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

    offset: int

    def pack(self) -> bytes:
        return pack_uint64(self.offset)

    @classmethod
    def unpack(cls, parser: MessageParser) -> Self:
        msg = cls(
            offset=parser.unpack_uint64()
        )
        return msg


# Distributed Messages #


@dataclass(slots=True, eq=False, repr=False)
class DistribMessage(SlskMessage):
    TYPE = MessageType.DISTRIBUTED

    sock: socket | None = field(init=False, default=None)
    username: str = field(init=False, default="")


@dataclass(slots=True, eq=False, repr=False)
class DistribPing(DistribMessage):
    """We ping our parent and children every minute.

    DEPRECATED, sent by Soulseek NS but not SoulseekQt
    """

    CODE = 0

    def pack(self) -> bytes:
        return b""

    @classmethod
    def unpack(cls, _parser: MessageParser) -> Self:
        return cls()


@dataclass(slots=True, eq=False, repr=False)
class DistribSearch(DistribMessage):
    """Search request that arrives through the distributed network. We distribute
    the raw message (including unknown message attributes) to our child peers.

    The first potential parent that sends us a search request in addition to
    branch root/level information becomes our actual parent. Some clients,
    such as Soulseek NS and earlier Nicotine+ versions, adopt a parent as soon
    as it sends the branch root/level information instead.

    Identifier is always the code point of ASCII character 1 (49). We reject
    messages that use any other value.
    """

    CODE = 3
    EVENT_NAME = "file-search-request-distributed"
    LOGGED = False

    identifier: str
    search_username: str
    token: int
    search_term: str

    @classmethod
    def unpack(cls, parser: MessageParser) -> Self:
        msg = cls(
            identifier=chr(parser.unpack_uint32()),
            search_username=parser.unpack_string(),
            token=parser.unpack_uint32(),
            search_term=parser.unpack_string()
        )
        return msg


@dataclass(slots=True, eq=False, repr=False)
class DistribBranchLevel(DistribMessage):
    """We tell our distributed children what our position is in our branch (nth
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

    CODE = 4

    level: int

    def pack(self) -> bytes:
        return pack_int32(self.level)

    @classmethod
    def unpack(cls, parser: MessageParser) -> Self:
        msg = cls(
            level=parser.unpack_uint32()
        )
        return msg


@dataclass(slots=True, eq=False, repr=False)
class DistribBranchRoot(DistribMessage):
    """We tell our distributed children the username of the root of the branch
    we're in in the distributed network. If we are the branch root (i.e. the
    server sends us EmbeddedMessage messages), we send our own username.

    When connecting to potential parents, they send us this message. We record
    the information, and adopt the first parent that sends us a DistribSearch
    message in addition to branch root/level information.

    Note that SoulseekQt used to not send this message when becoming a branch
    root. This behavior was corrected in early 2026. We should always send the
    message regardless of our status in the distributed network.
    """

    CODE = 5

    root_username: str
    root_username_size: int = -1  # in bytes

    def pack(self) -> bytes:
        return pack_string(self.root_username)

    @classmethod
    def unpack(cls, parser: MessageParser) -> Self:
        msg = cls(
            root_username=parser.unpack_string(),
            root_username_size=parser.offset - 4
        )
        return msg


@dataclass(slots=True, eq=False, repr=False)
class DistribChildDepth(DistribMessage):
    """When adopting a new parent, we send them this message with a child depth of
    zero. Our parent increments the depth, sends the message to their parent,
    who does the same, until it reaches the branch root, who sends the final
    child depth to the server in the form of a ChildDepth message.

    This message is obsolete, since SoulseekQt doesn't send it. Presumably, the
    server has opted to calculate child depths on its own, based on branch
    level/root information sent by peers.

    OBSOLETE, no longer used
    """

    CODE = 7

    depth: int

    def pack(self) -> bytes:
        return pack_uint32(self.depth)

    @classmethod
    def unpack(cls, parser: MessageParser) -> Self:
        msg = cls(
            depth=parser.unpack_uint32()
        )
        return msg


@dataclass(slots=True, eq=False, repr=False)
class DistribEmbeddedMessage(DistribMessage):
    """A branch root sends us an embedded distributed message. When the embedded
    message type is DistribSearch (distributed code 3), we unpack and
    distribute the raw message to our child peers. All other message types
    are unsupported and ignored.

    Note that older SoulseekQt versions incorrectly distributed this message
    instead of the unpacked message, which resulted in other client
    implementations adopting this erroneous behavior. This bug was fixed in
    SoulseekQt in early 2026.

    DEPRECATED, accidentally sent by older SoulseekQt versions
    """

    CODE = 93
    LOGGED = False

    distrib_code: int
    distrib_message: memoryview

    @classmethod
    def unpack(cls, parser: MessageParser) -> Self:
        # Older SoulseekQt versions send the message type as uint32, while
        # older Nicotine+ versions send it as uint8. Since the message handler
        # in slskproto.py always reads the message type as uint8, skip the
        # remainder in case a uint32 is sent.
        if parser.content[:3] == b"\x00\x00\x00":
            parser.offset += 3

        msg = cls(
            distrib_code=parser.unpack_uint8(),
            distrib_message=parser.content[parser.offset:],
        )
        return msg


# Message Mappings #


SERVER_MESSAGE_CLASSES = {cls.CODE: cls for cls in ServerMessage.__subclasses__()}
PEER_INIT_MESSAGE_CLASSES = {cls.CODE: cls for cls in PeerInitMessage.__subclasses__()}
PEER_MESSAGE_CLASSES = {cls.CODE: cls for cls in PeerMessage.__subclasses__()}
DISTRIBUTED_MESSAGE_CLASSES = {cls.CODE: cls for cls in DistribMessage.__subclasses__()}
