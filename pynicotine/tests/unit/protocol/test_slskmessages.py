# SPDX-FileCopyrightText: 2020-2026 Nicotine+ Contributors
# SPDX-License-Identifier: GPL-3.0-or-later

from unittest import TestCase

from pynicotine.slskmessages import AckNotifyPrivileges
from pynicotine.slskmessages import AddRoomMember
from pynicotine.slskmessages import CancelRoomMembership
from pynicotine.slskmessages import CancelRoomOwnership
from pynicotine.slskmessages import ChangePassword
from pynicotine.slskmessages import FileSearch
from pynicotine.slskmessages import GetPeerAddress
from pynicotine.slskmessages import GetUserStatus
from pynicotine.slskmessages import JoinGlobalRoom
from pynicotine.slskmessages import JoinRoom
from pynicotine.slskmessages import LeaveGlobalRoom
from pynicotine.slskmessages import Login
from pynicotine.slskmessages import NotifyPrivileges
from pynicotine.slskmessages import RemoveRoomMember
from pynicotine.slskmessages import RoomSomething
from pynicotine.slskmessages import SayChatroom
from pynicotine.slskmessages import SetStatus
from pynicotine.slskmessages import SetWaitPort
from pynicotine.slskmessages import SlskMessage
from pynicotine.slskmessages import UnwatchUser
from pynicotine.slskmessages import WatchUser


class SlskMessageTest(TestCase):

    def test_pack_objects(self):
        # Arrange
        obj = SlskMessage()

        # Act
        boolean_message = obj.pack_bool(123)
        unsigned_int8_message = obj.pack_uint8(123)
        unsigned_int32_message = obj.pack_uint32(123)
        signed_int32_message = obj.pack_int32(123)
        unsigned_int64_message = obj.pack_uint64(123)
        bytes_message = obj.pack_bytes(b"testbytes")
        str_message = obj.pack_string("teststring")

        # Assert
        self.assertEqual(boolean_message, b"\x01")
        self.assertEqual(unsigned_int8_message, b"\x7B")
        self.assertEqual(unsigned_int32_message, b"\x7B\x00\x00\x00")
        self.assertEqual(signed_int32_message, b"\x7B\x00\x00\x00")
        self.assertEqual(unsigned_int64_message, b"\x7B\x00\x00\x00\x00\x00\x00\x00")
        self.assertEqual(bytes_message, b"\t\x00\x00\x00testbytes")
        self.assertEqual(str_message, b"\n\x00\x00\x00teststring")


class LoginMessageTest(TestCase):

    def test_make_network_message(self):
        # Arrange
        obj = Login(username="test", passwd="s33cr3t", version=157, minorversion=19)

        # Act
        message = obj.make_network_message()

        # Assert
        self.assertEqual(
            message,
            bytearray(b"\x04\x00\x00\x00test\x07\x00\x00\x00s33cr3t\x9d\x00\x00\x00 "
                      b"\x00\x00\x00dbc93f24d8f3f109deed23c3e2f8b74c\x13\x00\x00\x00")
        )


class ChangePasswordMessageTest(TestCase):

    def test_make_network_message(self):
        # Arrange
        obj = ChangePassword(password="s33cr3t")

        # Act
        message = obj.make_network_message()

        # Assert
        self.assertEqual(message, b"\x07\x00\x00\x00s33cr3t")


class SetWaitPortMessageTest(TestCase):

    def test_make_network_message(self):
        # Arrange
        obj = SetWaitPort(port=1337)

        # Act
        message = obj.make_network_message()

        # Assert
        self.assertEqual(message, b"9\x05\x00\x00")


class GetPeerAddressMessageTest(TestCase):

    def test_make_network_message(self):
        # Arrange
        obj = GetPeerAddress(user="user1")

        # Act
        message = obj.make_network_message()

        # Assert
        self.assertEqual(message, b"\x05\x00\x00\x00user1")


class WatchUserMessageTest(TestCase):

    def test_make_network_message(self):
        # Arrange
        obj = WatchUser(user="user2")

        # Act
        message = obj.make_network_message()

        # Assert
        self.assertEqual(message, b"\x05\x00\x00\x00user2")


class UnwatchUserMessageTest(TestCase):

    def test_make_network_message(self):
        # Arrange
        obj = UnwatchUser(user="user3")

        # Act
        message = obj.make_network_message()

        # Assert
        self.assertEqual(message, b"\x05\x00\x00\x00user3")


class GetUserStatusMessageTest(TestCase):

    def test_make_network_message(self):
        # Arrange
        obj = GetUserStatus(user="user4")

        # Act
        message = obj.make_network_message()

        # Assert
        self.assertEqual(message, b"\x05\x00\x00\x00user4")


class FileSearchTest(TestCase):

    def test_make_network_message(self):
        # Arrange
        obj = FileSearch(token=524700074, text="70 gwen auto")

        # Act
        message = obj.make_network_message()

        # Assert
        self.assertEqual(message, b"\xaaIF\x1f\x0c\x00\x00\x0070 gwen auto")


class SetStatusMessageTest(TestCase):

    def test_make_network_message(self):
        # Arrange
        obj = SetStatus(status=1)

        # Act
        message = obj.make_network_message()

        # Assert
        self.assertEqual(message, b"\x01\x00\x00\x00")


class NotifyPrivilegesMessageTest(TestCase):

    def test_make_network_message(self):
        # Arrange
        obj = NotifyPrivileges(token=123456, user="user5")

        # Act
        message = obj.make_network_message()

        # Assert
        self.assertEqual(message, b"@\xe2\x01\x00\x05\x00\x00\x00user5")


class AckNotifyPrivilegesMessageTest(TestCase):

    def test_make_network_message(self):
        # Arrange
        obj = AckNotifyPrivileges(token=123456)

        # Act
        message = obj.make_network_message()

        # Assert
        self.assertEqual(message, b"@\xe2\x01\x00")


class JoinGlobalRoomMessageTest(TestCase):

    def test_make_network_message(self):
        # Arrange
        obj = JoinGlobalRoom()

        # Act
        message = obj.make_network_message()

        # Assert
        self.assertEqual(message, b"")


class LeaveGlobalRoomMessageTest(TestCase):

    def test_make_network_message(self):
        # Arrange
        obj = LeaveGlobalRoom()

        # Act
        message = obj.make_network_message()

        # Assert
        self.assertEqual(message, b"")


class SayChatroomMessageTest(TestCase):

    def test_make_network_message(self):
        # Arrange
        obj = SayChatroom(room="room1", message="Wassup?")

        # Act
        message = obj.make_network_message()

        # Assert
        self.assertEqual(message, b"\x05\x00\x00\x00room1\x07\x00\x00\x00Wassup?")


class JoinRoomMessageTest(TestCase):

    def test_make_network_message(self):
        # Arrange
        obj = JoinRoom(room="room2", private=False)
        obj_private = JoinRoom(room="room2", private=True)

        # Act
        message = obj.make_network_message()
        message_private = obj_private.make_network_message()

        # Assert
        self.assertEqual(message, b"\x05\x00\x00\x00room2\x00\x00\x00\x00")
        self.assertEqual(message_private, b"\x05\x00\x00\x00room2\x01\x00\x00\x00")


class AddRoomMemberMessageTest(TestCase):

    def test_make_network_message(self):
        # Arrange
        obj = AddRoomMember(room="room3", user="admin")

        # Act
        message = obj.make_network_message()

        # Assert
        self.assertEqual(message, b"\x05\x00\x00\x00room3\x05\x00\x00\x00admin")


class CancelRoomMembershipMessageTest(TestCase):

    def test_make_network_message(self):
        # Arrange
        obj = CancelRoomMembership(room="room4")

        # Act
        message = obj.make_network_message()

        # Assert
        self.assertEqual(message, b"\x05\x00\x00\x00room4")


class CancelRoomOwnershipMessageTest(TestCase):

    def test_make_network_message(self):
        # Arrange
        obj = CancelRoomOwnership(room="room5")

        # Act
        message = obj.make_network_message()

        # Assert
        self.assertEqual(message, b"\x05\x00\x00\x00room5")


class RoomSomethingMessageTest(TestCase):

    def test_make_network_message(self):
        # Arrange
        obj = RoomSomething(room="room6")

        # Act
        message = obj.make_network_message()

        # Assert
        self.assertEqual(message, b"\x05\x00\x00\x00room6")


class RemoveRoomMemberMessageTest(TestCase):

    def test_make_network_message(self):
        # Arrange
        obj = RemoveRoomMember(room="room7", user="admin")

        # Act
        message = obj.make_network_message()

        # Assert
        self.assertEqual(message, b"\x05\x00\x00\x00room7\x05\x00\x00\x00admin")

    def test_parse_network_message(self):
        # Arrange
        message = b"\x05\x00\x00\x00room7\x05\x00\x00\x00admin"

        # Act
        obj = RemoveRoomMember(msg_content=memoryview(message))
        obj.parse_network_message()

        # Assert
        self.assertEqual(obj.room, "room7")
        self.assertEqual(obj.user, "admin")
