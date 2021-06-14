# COPYRIGHT (C) 2020-2021 Nicotine+ Team
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

import unittest

from pynicotine.slskmessages import AckNotifyPrivileges
from pynicotine.slskmessages import AddUser
from pynicotine.slskmessages import ChangePassword
from pynicotine.slskmessages import GetPeerAddress
from pynicotine.slskmessages import GetUserStatus
from pynicotine.slskmessages import JoinPublicRoom
from pynicotine.slskmessages import JoinRoom
from pynicotine.slskmessages import LeavePublicRoom
from pynicotine.slskmessages import Login
from pynicotine.slskmessages import NotifyPrivileges
from pynicotine.slskmessages import PrivateRoomAddUser
from pynicotine.slskmessages import PrivateRoomDismember
from pynicotine.slskmessages import PrivateRoomDisown
from pynicotine.slskmessages import PrivateRoomRemoveUser
from pynicotine.slskmessages import PrivateRoomSomething
from pynicotine.slskmessages import RemoveUser
from pynicotine.slskmessages import SayChatroom
from pynicotine.slskmessages import SetStatus
from pynicotine.slskmessages import SetWaitPort
from pynicotine.slskmessages import SlskMessage


class SlskMessageTest(unittest.TestCase):
    def test_pack_object(self):
        # Arrange
        obj = SlskMessage()

        # Act
        int_message = obj.pack_object(123)
        unsigned_int_message = obj.pack_object(123, unsignedint=True)
        long_long_message = obj.pack_object(123, unsignedlonglong=True)
        bytes_message = obj.pack_object(b'testbytes')
        str_message = obj.pack_object('teststring')

        # Assert
        self.assertEqual(b'{\x00\x00\x00', int_message)
        self.assertEqual(b'{\x00\x00\x00', unsigned_int_message)
        self.assertEqual(b'{\x00\x00\x00\x00\x00\x00\x00', long_long_message)
        self.assertEqual(b'\n\x00\x00\x00teststring', str_message)
        self.assertEqual(b'\t\x00\x00\x00testbytes', bytes_message)


class LoginMessageTest(unittest.TestCase):
    def test_make_network_message(self):
        # Arrange
        obj = Login(username='test', passwd='s33cr3t', version=157, minorversion=19)

        # Act
        message = obj.make_network_message()

        # Assert
        self.assertEqual(
            bytearray(b'\x04\x00\x00\x00test\x07\x00\x00\x00s33cr3t\x9d\x00\x00\x00 '
                      b'\x00\x00\x00dbc93f24d8f3f109deed23c3e2f8b74c\x13\x00\x00\x00'),
            message)


class ChangePasswordMessageTest(unittest.TestCase):
    def test_make_network_message(self):
        # Arrange
        obj = ChangePassword(password='s33cr3t')

        # Act
        message = obj.make_network_message()

        # Assert
        self.assertEqual(
            b'\x07\x00\x00\x00s33cr3t',
            message)


class SetWaitPortMessageTest(unittest.TestCase):
    def test_make_network_message(self):
        # Arrange
        obj = SetWaitPort(port=1337)

        # Act
        message = obj.make_network_message()

        # Assert
        self.assertEqual(
            b'9\x05\x00\x00',
            message)


class GetPeerAddressMessageTest(unittest.TestCase):
    def test_make_network_message(self):
        # Arrange
        obj = GetPeerAddress(user='test')

        # Act
        message = obj.make_network_message()

        # Assert
        self.assertEqual(
            b'\x04\x00\x00\x00test',
            message)


class AddUserMessageTest(unittest.TestCase):
    def test_make_network_message(self):
        # Arrange
        obj = AddUser(user='test')

        # Act
        message = obj.make_network_message()

        # Assert
        self.assertEqual(
            b'\x04\x00\x00\x00test',
            message)


class RemoveUserMessageTest(unittest.TestCase):
    def test_make_network_message(self):
        # Arrange
        obj = RemoveUser(user='test')

        # Act
        message = obj.make_network_message()

        # Assert
        self.assertEqual(
            b'\x04\x00\x00\x00test',
            message)


class GetUserStatusMessageTest(unittest.TestCase):
    def test_make_network_message(self):
        # Arrange
        obj = GetUserStatus(user='test')

        # Act
        message = obj.make_network_message()

        # Assert
        self.assertEqual(
            b'\x04\x00\x00\x00test',
            message)


class SetStatusMessageTest(unittest.TestCase):
    def test_make_network_message(self):
        # Arrange
        obj = SetStatus(status=1)

        # Act
        message = obj.make_network_message()

        # Assert
        self.assertEqual(
            b'\x01\x00\x00\x00',
            message)


class NotifyPrivilegesMessageTest(unittest.TestCase):
    def test_make_network_message(self):
        # Arrange
        obj = NotifyPrivileges(token=123456, user='test')

        # Act
        message = obj.make_network_message()

        # Assert
        self.assertEqual(
            b'@\xe2\x01\x00\x04\x00\x00\x00test',
            message)


class AckNotifyPrivilegesMessageTest(unittest.TestCase):
    def test_make_network_message(self):
        # Arrange
        obj = AckNotifyPrivileges(token=123456)

        # Act
        message = obj.make_network_message()

        # Assert
        self.assertEqual(
            b'@\xe2\x01\x00',
            message)


class JoinPublicRoomMessageTest(unittest.TestCase):
    def test_make_network_message(self):
        # Arrange
        obj = JoinPublicRoom()

        # Act
        message = obj.make_network_message()

        # Assert
        self.assertEqual(
            b'',
            message)


class LeavePublicRoomMessageTest(unittest.TestCase):
    def test_make_network_message(self):
        # Arrange
        obj = LeavePublicRoom()

        # Act
        message = obj.make_network_message()

        # Assert
        self.assertEqual(
            b'',
            message)


class PublicRoomMessageMessageTest(unittest.TestCase):
    ...


class SayChatroomMessageTest(unittest.TestCase):
    def test_make_network_message(self):
        # Arrange
        obj = SayChatroom(room='nicotine', msg='Wassup?')

        # Act
        message = obj.make_network_message()

        # Assert
        self.assertEqual(
            b'\x08\x00\x00\x00nicotine\x07\x00\x00\x00Wassup?',
            message)


class JoinRoomMessageTest(unittest.TestCase):
    def test_make_network_message(self):
        # Arrange
        obj = JoinRoom(room='nicotine', private=0)
        obj_private = JoinRoom(room='nicotine', private=1)

        # Act
        message = obj.make_network_message()
        message_private = obj_private.make_network_message()

        # Assert
        self.assertEqual(
            b'\x08\x00\x00\x00nicotine\x00\x00\x00\x00',
            message)
        self.assertEqual(
            b'\x08\x00\x00\x00nicotine\x01\x00\x00\x00',
            message_private)


class PrivateRoomUsersMessageTest(unittest.TestCase):
    ...


class PrivateRoomOwnedMessageTest(unittest.TestCase):
    ...


class PrivateRoomAddUserMessageTest(unittest.TestCase):
    def test_make_network_message(self):
        # Arrange
        obj = PrivateRoomAddUser(room='nicotine', user='admin')

        # Act
        message = obj.make_network_message()

        # Assert
        self.assertEqual(
            b'\x08\x00\x00\x00nicotine\x05\x00\x00\x00admin',
            message)


class PrivateRoomDismemberMessageTest(unittest.TestCase):
    def test_make_network_message(self):
        # Arrange
        obj = PrivateRoomDismember(room='nicotine')

        # Act
        message = obj.make_network_message()

        # Assert
        self.assertEqual(
            b'\x08\x00\x00\x00nicotine',
            message)


class PrivateRoomDisownMessageTest(unittest.TestCase):
    def test_make_network_message(self):
        # Arrange
        obj = PrivateRoomDisown(room='nicotine')

        # Act
        message = obj.make_network_message()

        # Assert
        self.assertEqual(
            b'\x08\x00\x00\x00nicotine',
            message)


class PrivateRoomSomethingMessageTest(unittest.TestCase):
    def test_make_network_message(self):
        # Arrange
        obj = PrivateRoomSomething(room='nicotine')

        # Act
        message = obj.make_network_message()

        # Assert
        self.assertEqual(
            b'\x08\x00\x00\x00nicotine',
            message)


class PrivateRoomRemoveUserMessageTest(unittest.TestCase):
    def test_make_network_message(self):
        # Arrange
        obj = PrivateRoomRemoveUser(room='nicotine', user='admin')

        # Act
        message = obj.make_network_message()

        # Assert
        self.assertEqual(
            b'\x08\x00\x00\x00nicotine\x05\x00\x00\x00admin',
            message)

    def test_parse_network_message(self):
        # Arrange
        message = b'\x08\x00\x00\x00nicotine\x05\x00\x00\x00admin'

        # Act
        obj = PrivateRoomRemoveUser()
        obj.parse_network_message(message)

        # Assert
        self.assertEqual('nicotine', obj.room)
        self.assertEqual('admin', obj.user)
