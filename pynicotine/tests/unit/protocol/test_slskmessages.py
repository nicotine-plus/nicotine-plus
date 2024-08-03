# COPYRIGHT (C) 2020-2023 Nicotine+ Contributors
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

from unittest import TestCase

from pynicotine.slskmessages import AckNotifyPrivileges
from pynicotine.slskmessages import ChangePassword
from pynicotine.slskmessages import FileSearch
from pynicotine.slskmessages import GetPeerAddress
from pynicotine.slskmessages import GetUserStatus
from pynicotine.slskmessages import JoinGlobalRoom
from pynicotine.slskmessages import JoinRoom
from pynicotine.slskmessages import LeaveGlobalRoom
from pynicotine.slskmessages import Login
from pynicotine.slskmessages import NotifyPrivileges
from pynicotine.slskmessages import PrivateRoomAddUser
from pynicotine.slskmessages import PrivateRoomCancelMembership
from pynicotine.slskmessages import PrivateRoomDisown
from pynicotine.slskmessages import PrivateRoomRemoveUser
from pynicotine.slskmessages import PrivateRoomSomething
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
        self.assertEqual(b"\x01", boolean_message)
        self.assertEqual(b"\x7B", unsigned_int8_message)
        self.assertEqual(b"\x7B\x00\x00\x00", unsigned_int32_message)
        self.assertEqual(b"\x7B\x00\x00\x00", signed_int32_message)
        self.assertEqual(b"\x7B\x00\x00\x00\x00\x00\x00\x00", unsigned_int64_message)
        self.assertEqual(b"\t\x00\x00\x00testbytes", bytes_message)
        self.assertEqual(b"\n\x00\x00\x00teststring", str_message)


class LoginMessageTest(TestCase):

    def test_make_network_message(self):
        # Arrange
        obj = Login(username="test", passwd="s33cr3t", version=157, minorversion=19)

        # Act
        message = obj.make_network_message()

        # Assert
        self.assertEqual(
            bytearray(b"\x04\x00\x00\x00test\x07\x00\x00\x00s33cr3t\x9d\x00\x00\x00 "
                      b"\x00\x00\x00dbc93f24d8f3f109deed23c3e2f8b74c\x13\x00\x00\x00"),
            message)


class ChangePasswordMessageTest(TestCase):

    def test_make_network_message(self):
        # Arrange
        obj = ChangePassword(password="s33cr3t")

        # Act
        message = obj.make_network_message()

        # Assert
        self.assertEqual(
            b"\x07\x00\x00\x00s33cr3t",
            message)


class SetWaitPortMessageTest(TestCase):

    def test_make_network_message(self):
        # Arrange
        obj = SetWaitPort(port=1337)

        # Act
        message = obj.make_network_message()

        # Assert
        self.assertEqual(
            b"9\x05\x00\x00",
            message)


class GetPeerAddressMessageTest(TestCase):

    def test_make_network_message(self):
        # Arrange
        obj = GetPeerAddress(user="user1")

        # Act
        message = obj.make_network_message()

        # Assert
        self.assertEqual(
            b"\x05\x00\x00\x00user1",
            message)


class WatchUserMessageTest(TestCase):

    def test_make_network_message(self):
        # Arrange
        obj = WatchUser(user="user2")

        # Act
        message = obj.make_network_message()

        # Assert
        self.assertEqual(
            b"\x05\x00\x00\x00user2",
            message)


class UnwatchUserMessageTest(TestCase):

    def test_make_network_message(self):
        # Arrange
        obj = UnwatchUser(user="user3")

        # Act
        message = obj.make_network_message()

        # Assert
        self.assertEqual(
            b"\x05\x00\x00\x00user3",
            message)


class GetUserStatusMessageTest(TestCase):

    def test_make_network_message(self):
        # Arrange
        obj = GetUserStatus(user="user4")

        # Act
        message = obj.make_network_message()

        # Assert
        self.assertEqual(
            b"\x05\x00\x00\x00user4",
            message)


class FileSearchTest(TestCase):

    def test_make_network_message(self):
        # Arrange
        obj = FileSearch(token=524700074, text="70 gwen auto")

        # Act
        message = obj.make_network_message()

        # Assert
        self.assertEqual(
            b"\xaaIF\x1f\x0c\x00\x00\x0070 gwen auto",
            message)


class SetStatusMessageTest(TestCase):

    def test_make_network_message(self):
        # Arrange
        obj = SetStatus(status=1)

        # Act
        message = obj.make_network_message()

        # Assert
        self.assertEqual(
            b"\x01\x00\x00\x00",
            message)


class NotifyPrivilegesMessageTest(TestCase):

    def test_make_network_message(self):
        # Arrange
        obj = NotifyPrivileges(token=123456, user="user5")

        # Act
        message = obj.make_network_message()

        # Assert
        self.assertEqual(
            b"@\xe2\x01\x00\x05\x00\x00\x00user5",
            message)


class AckNotifyPrivilegesMessageTest(TestCase):

    def test_make_network_message(self):
        # Arrange
        obj = AckNotifyPrivileges(token=123456)

        # Act
        message = obj.make_network_message()

        # Assert
        self.assertEqual(
            b"@\xe2\x01\x00",
            message)


class JoinGlobalRoomMessageTest(TestCase):

    def test_make_network_message(self):
        # Arrange
        obj = JoinGlobalRoom()

        # Act
        message = obj.make_network_message()

        # Assert
        self.assertEqual(
            b"",
            message)


class LeaveGlobalRoomMessageTest(TestCase):

    def test_make_network_message(self):
        # Arrange
        obj = LeaveGlobalRoom()

        # Act
        message = obj.make_network_message()

        # Assert
        self.assertEqual(
            b"",
            message)


class GlobalRoomMessageMessageTest(TestCase):
    ...


class SayChatroomMessageTest(TestCase):

    def test_make_network_message(self):
        # Arrange
        obj = SayChatroom(room="room1", message="Wassup?")

        # Act
        message = obj.make_network_message()

        # Assert
        self.assertEqual(
            b"\x05\x00\x00\x00room1\x07\x00\x00\x00Wassup?",
            message)


class JoinRoomMessageTest(TestCase):

    def test_make_network_message(self):
        # Arrange
        obj = JoinRoom(room="room2", private=False)
        obj_private = JoinRoom(room="room2", private=True)

        # Act
        message = obj.make_network_message()
        message_private = obj_private.make_network_message()

        # Assert
        self.assertEqual(
            b"\x05\x00\x00\x00room2\x00\x00\x00\x00",
            message)
        self.assertEqual(
            b"\x05\x00\x00\x00room2\x01\x00\x00\x00",
            message_private)


class PrivateRoomUsersMessageTest(TestCase):
    ...


class PrivateRoomOwnedMessageTest(TestCase):
    ...


class PrivateRoomAddUserMessageTest(TestCase):

    def test_make_network_message(self):
        # Arrange
        obj = PrivateRoomAddUser(room="room3", user="admin")

        # Act
        message = obj.make_network_message()

        # Assert
        self.assertEqual(
            b"\x05\x00\x00\x00room3\x05\x00\x00\x00admin",
            message)


class PrivateRoomCancelMembershipMessageTest(TestCase):

    def test_make_network_message(self):
        # Arrange
        obj = PrivateRoomCancelMembership(room="room4")

        # Act
        message = obj.make_network_message()

        # Assert
        self.assertEqual(
            b"\x05\x00\x00\x00room4",
            message)


class PrivateRoomDisownMessageTest(TestCase):

    def test_make_network_message(self):
        # Arrange
        obj = PrivateRoomDisown(room="room5")

        # Act
        message = obj.make_network_message()

        # Assert
        self.assertEqual(
            b"\x05\x00\x00\x00room5",
            message)


class PrivateRoomSomethingMessageTest(TestCase):

    def test_make_network_message(self):
        # Arrange
        obj = PrivateRoomSomething(room="room6")

        # Act
        message = obj.make_network_message()

        # Assert
        self.assertEqual(
            b"\x05\x00\x00\x00room6",
            message)


class PrivateRoomRemoveUserMessageTest(TestCase):

    def test_make_network_message(self):
        # Arrange
        obj = PrivateRoomRemoveUser(room="room7", user="admin")

        # Act
        message = obj.make_network_message()

        # Assert
        self.assertEqual(
            b"\x05\x00\x00\x00room7\x05\x00\x00\x00admin",
            message)

    def test_parse_network_message(self):
        # Arrange
        message = b"\x05\x00\x00\x00room7\x05\x00\x00\x00admin"

        # Act
        obj = PrivateRoomRemoveUser()
        obj.parse_network_message(memoryview(message))

        # Assert
        self.assertEqual("room7", obj.room)
        self.assertEqual("admin", obj.user)
