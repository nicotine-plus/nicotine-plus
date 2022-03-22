# Soulseek Protocol Documentation

Last updated on March 22, 2022

Since the official Soulseek client and server is proprietary software, this documentation has been compiled thanks to years of reverse engineering efforts. To preserve the health of the Soulseek network, please do not modify or extend the protocol in ways that negatively impact the network.

If you find any inconsistencies, errors or omissions in the documentation, please report them.

## Sections

- [Packing](#packing)
- [Constants](#constants)
- [Server Messages](#server-messages)
- [Peer Init Messages](#peer-init-messages)
- [Peer Messages](#peer-messages)
- [File Messages](#file-messages)
- [Distributed Messages](#distributed-messages)

# Packing

### String

| Length of String | String |
| ---------------- | ------ |
| 4 Byte           | String |

### Integer

| Number |
| ------ |
| 4 Byte |

### Large Integer

| Number |
| ------ |
| 8 Byte |

### Bool

| Character |
| --------- |
| 1 Byte    |

# Constants

### Connection Types

| Type | Connection          |
| ---- | ------------------- |
| P    | Peer To Peer        |
| F    | File Transfer       |
| D    | Distributed Network |

### Status Codes

| Code | Status  |
| ---- | ------- |
| -1   | Unknown |
| 0    | Offline |
| 1    | Away    |
| 2    | Online  |

### Transfer Direction

| Code | Type     |
| ---- | -------- |
| 0    | Download |
| 1    | Upload   |

### File Attribute Types

| Code | Type             |
| ---- | ---------------- |
| 0    | Bitrate (kbps)   |
| 1    | Length (seconds) |
| 2    | VBR (0 or 1)     |
| 4    | Sample Rate (Hz) |
| 5    | Bit Depth        |

#### Used Attribute Combinations

  - Soulseek NS, SoulseekQt (2015-2-21 and earlier), Nicotine+, Museek+, SoulSeeX:
      - {0: *bitrate*, 1: *length*, 2: *VBR*}

  - SoulseekQt (2015-2-21 and earlier):
      - {0: *bitrate*, 2: *VBR*}

  - SoulseekQt (2015-6-12 and later):
      - {0: *bitrate*}
      - {1: *length*}
      - {0: *bitrate*, 1: *length*}
      - {4: *sample rate*, 5: *bit depth*}
      - {1: *length*, 4: *sample rate*, 5: *bit depth*}

# Server Messages

| Send           | Receive             |
| -------------- | ------------------- |
| Send to Server | Receive from Server |

These messages are used by clients to interface with the server.
Internal Server messages are spooky and not understood, since the OSS
crowd doesn't have access to its source code. If you want a Soulseek
server, check out
[Soulfind](https://github.com/seeschloss/soulfind).
Soulfind is obviously not the exact same the official Soulseek server,
but it handles the protocol well enough (and can be modified).

In Nicotine+, these messages are matched to their message number in
slskproto.py in the SlskProtoThread function, defined in slskmessages.py
and callbacks for the messages are set in pynicotine.py.

### Server Message Format

| Message Length | Code    | Message Contents |
| -------------- | ------- | ---------------- |
| 4 Bytes        | 4 Bytes | ...              |

### Message Index

| Code | Message                                           | Status     |
| ---- | ------------------------------------------------- | ---------- |
| 1    | [Login](#server-code-1)                           |            |
| 2    | [Set Listen Port](#server-code-2)                 |            |
| 3    | [Get Peer Address](#server-code-3)                |            |
| 5    | [Add User](#server-code-5)                        |            |
| 6    | [Remove User](#server-code-6)                     |            |
| 7    | [Get Status](#server-code-7)                      |            |
| 13   | [Say in Chat Room](#server-code-13)               |            |
| 14   | [Join Room](#server-code-14)                      |            |
| 15   | [Leave Room](#server-code-15)                     |            |
| 16   | [User Joined Room](#server-code-16)               |            |
| 17   | [User Left Room](#server-code-17)                 |            |
| 18   | [Connect To Peer](#server-code-18)                |            |
| 22   | [Private Messages](#server-code-22)               |            |
| 23   | [Acknowledge Private Message](#server-code-23)    |            |
| 25   | [File Search Room](#server-code-25)               | Obsolete   |
| 26   | [File Search](#server-code-26)                    |            |
| 28   | [Set Online Status](#server-code-28)              |            |
| 32   | [Ping](#server-code-32)                           | Deprecated |
| 33   | [Send Connect Token](#server-code-33)             | Obsolete   |
| 34   | [Send Download Speed](#server-code-34)            | Obsolete   |
| 35   | [Shared Folders & Files](#server-code-35)         |            |
| 36   | [Get User Stats](#server-code-36)                 |            |
| 40   | [Queued Downloads](#server-code-40)               | Obsolete   |
| 41   | [Kicked from Server](#server-code-41)             |            |
| 42   | [User Search](#server-code-42)                    |            |
| 51   | [Interest Add](#server-code-51)                   | Deprecated |
| 52   | [Interest Remove](#server-code-52)                | Deprecated |
| 54   | [Get Recommendations](#server-code-54)            | Deprecated |
| 56   | [Get Global Recommendations](#server-code-56)     | Deprecated |
| 57   | [Get User Interests](#server-code-57)             | Deprecated |
| 58   | [Admin Command](#server-code-58)                  | Obsolete   |
| 60   | [Place In Line Response](#server-code-60)         | Obsolete   |
| 62   | [Room Added](#server-code-62)                     | Obsolete   |
| 63   | [Room Removed](#server-code-63)                   | Obsolete   |
| 64   | [Room List](#server-code-64)                      |            |
| 65   | [Exact File Search](#server-code-65)              | Obsolete   |
| 66   | [Global/Admin Message](#server-code-66)           |            |
| 67   | [Global User List](#server-code-67)               | Obsolete   |
| 68   | [Tunneled Message](#server-code-68)               | Obsolete   |
| 69   | [Privileged Users](#server-code-69)               |            |
| 71   | [Have No Parents](#server-code-71)                |            |
| 73   | [Parent's IP](#server-code-73)                    | Deprecated |
| 83   | [Parent Min Speed](#server-code-83)               |            |
| 84   | [Parent Speed Ratio](#server-code-84)             |            |
| 86   | [Parent Inactivity Timeout](#server-code-86)      | Obsolete   |
| 87   | [Search Inactivity Timeout](#server-code-87)      | Obsolete   |
| 88   | [Minimum Parents In Cache](#server-code-88)       | Obsolete   |
| 90   | [Distributed Alive Interval](#server-code-90)     | Obsolete   |
| 91   | [Add Privileged User](#server-code-91)            | Obsolete   |
| 92   | [Check Privileges](#server-code-92)               |            |
| 93   | [Embedded Message](#server-code-93)               |            |
| 100  | [Accept Children](#server-code-100)               |            |
| 102  | [Possible Parents](#server-code-102)              |            |
| 103  | [Wishlist Search](#server-code-103)               |            |
| 104  | [Wishlist Interval](#server-code-104)             |            |
| 110  | [Get Similar Users](#server-code-110)             | Deprecated |
| 111  | [Get Item Recommendations](#server-code-111)      | Deprecated |
| 112  | [Get Item Similar Users](#server-code-112)        | Deprecated |
| 113  | [Room Tickers](#server-code-113)                  |            |
| 114  | [Room Ticker Add](#server-code-114)               |            |
| 115  | [Room Ticker Remove](#server-code-115)            |            |
| 116  | [Set Room Ticker](#server-code-116)               |            |
| 117  | [Hated Interest Add](#server-code-117)            | Deprecated |
| 118  | [Hated Interest Remove](#server-code-118)         | Deprecated |
| 120  | [Room Search](#server-code-120)                   |            |
| 121  | [Send Upload Speed](#server-code-121)             |            |
| 122  | [User Privileges](#server-code-122)               | Deprecated |
| 123  | [Give Privileges](#server-code-123)               |            |
| 124  | [Notify Privileges](#server-code-124)             | Deprecated |
| 125  | [Acknowledge Notify Privileges](#server-code-125) | Deprecated |
| 126  | [Branch Level](#server-code-126)                  |            |
| 127  | [Branch Root](#server-code-127)                   |            |
| 129  | [Child Depth](#server-code-129)                   | Deprecated |
| 130  | [Reset Distributed](#server-code-130)             |            |
| 133  | [Private Room Users](#server-code-133)            |            |
| 134  | [Private Room Add User](#server-code-134)         |            |
| 135  | [Private Room Remove User](#server-code-135)      |            |
| 136  | [Private Room Drop Membership](#server-code-136)  |            |
| 137  | [Private Room Drop Ownership](#server-code-137)   |            |
| 138  | [Private Room Unknown](#server-code-138)          | Obsolete   |
| 139  | [Private Room Added](#server-code-139)            |            |
| 140  | [Private Room Removed](#server-code-140)          |            |
| 141  | [Private Room Toggle](#server-code-141)           |            |
| 142  | [New Password](#server-code-142)                  |            |
| 143  | [Private Room Add Operator](#server-code-143)     |            |
| 144  | [Private Room Remove Operator](#server-code-144)  |            |
| 145  | [Private Room Operator Added](#server-code-145)   |            |
| 146  | [Private Room Operator Removed](#server-code-146) |            |
| 148  | [Private Room Owned](#server-code-148)            |            |
| 149  | [Message Users](#server-code-149)                 |            |
| 150  | [Ask Public Chat](#server-code-150)               | Deprecated |
| 151  | [Stop Public Chat](#server-code-151)              | Deprecated |
| 152  | [Public Chat Message](#server-code-152)           | Deprecated |
| 153  | [Related Searches](#server-code-153)              | Obsolete   |
| 1001 | [Can't Connect To Peer](#server-code-1001)        |            |
| 1003 | [Can't Create Room](#server-code-1003)            |            |

## Server Code 1

### Description

We send this to the server right after the connection has been established. Server responds with the greeting message.

### Function Names

  - Nicotine+: Login

### Sending Login Example

| Description | Message Length | Message Code | Username Length | Username                | Password Length | Password                |
| ----------- | -------------- | ------------ | --------------- | ----------------------- | --------------- | ----------------------- |
| Human       | 72             | 1            | 8               | username                | 8               | password                |
| Hex         | 48 00 00 00    | 01 00 00 00  | 08 00 00 00     | 75 73 65 72 6e 61 6d 65 | 08 00 00 00     | 70 61 73 73 77 6f 72 64 |

*Message, continued*

| Description | Version     | Length      | Hash                                                                                            | Minor Version |
| ----------- | ----------- | ----------- | ----------------------------------------------------------------------------------------------- | ------------- |
| Human       | 160         | 32          | d51c9a7e9353746a6020f9602d452929                                                                | 1             |
| Hex         | a0 00 00 00 | 20 00 00 00 | 64 35 31 63 39 61 37 65 39 33 35 33 37 34 36 61 36 30 32 30 66 39 36 30 32 64 34 35 32 39 32 39 | 01 00 00 00   |

*Message as a Hex Stream* **48 00 00 00 01 00 00 00 08 00 00 00 75 73 65
72 6e 61 6d 65 08 00 00 00 70 61 73 73 77 6f 72 64 a0 00 00 00 20 00 00
00 64 35 31 63 39 61 37 65 39 33 35 33 37 34 36 61 36 30 32 30 66 39 36
30 32 64 34 35 32 39 32 39 01 00 00 00**

### Data Order

  - Send
    1.  **string** <ins>username</ins>
    2.  **string** <ins>password</ins> **A non-empty string is required**
    3.  **uint** <ins>version number</ins> *160* for Nicotine+
    4.  **string** <ins>MD5 hex digest of concatenated username & password</ins>
    5.  **uint** <ins>minor version</ins> Minor version (0x13000000 for 157 ns 13e, 0x11000000 for 157 ns 13c)
  - Receive Login Success
    1.  **bool** <ins>success</ins> 1
    2.  **string** <ins>greet</ins> A MOTD string
    3.  **uint** <ins>Your IP Address</ins>
    4.  **string** <ins>MD5 hex digest of the password string</ins> *Windows Soulseek uses this hash to determine if it's connected to the official server*
  - Receive Login Failure
    1.  **bool** <ins>failure</ins> *0*
    2.  **string** <ins>reason</ins> Almost always: *Bad Password*; sometimes it's a banned message or another error.

## Server Code 2

### Description

We send this to the server to indicate the port number that we listen on (2234 by default).

If this value is set to zero, or the message is not sent upon login (which defaults the listen port to 0), remote clients handling a `ConnectToPeer` message (code 18) will fail to properly purge the request.  Confirmed in SoulseekQt 2020.3.12, but probably impacts most or all other versions.

### Function Names

  - Nicotine+: SetWaitPort

### Data Order

  - Send
    1.  **uint** <ins>port</ins>
    2.  **bool** <ins>use obfuscation</ins>
    3.  **uint** <ins>obfuscated port</ins>
  - Receive
      - *No Message*

## Server Code 3

### Description

We send this to the server to ask for a peer's address (IP address and port), given the peer's username.

### Function Names

  - Nicotine+: GetPeerAddress

### Data Order

  - Send
    1.  **string** <ins>username</ins>
  - Receive
    1.  **string** <ins>username</ins>
    2.  **ip** <ins>ip</ins>
    3.  **uint** <ins>port</ins>
    4.  **bool** <ins>use obfuscation</ins>
    5.  **uint** <ins>obfuscated port</ins>

## Server Code 5

### Description

Used to be kept updated about a user's stats. When a user's stats have changed, the server sends a GetUserStats response message with the new user stats.

### Function Names

  - Nicotine+: AddUser

### Data Order

  - Send
    1.  **string** <ins>username</ins>

  - Receive
    1.  **string** <ins>username</ins>
    2.  **bool** <ins>exists</ins>

    - If <ins>exists</ins> is true
        1.  **uint** <ins>status</ins> *0 == Offline, 1 == Away; 2 == Online*
        2.  **uint** <ins>avgspeed</ins>
        3.  **uint64** <ins>uploadnum</ins> *Number of uploaded files. The value changes when sending a [SendUploadSpeed](#server-code-121) server message, and is likely used by the server to calculate the average speed.*
        4.  **uint** <ins>files</ins>
        5.  **uint** <ins>dirs</ins>

        - If <ins>status</ins> is away/online
            1.  **string** <ins>countrycode</ins> *Uppercase country code*

## Server Code 6

### Description

Used when we no longer want to be kept updated about a user's stats.

### Function Names

  - Nicotine+: RemoveUser

### Data Order

  - Send
    1.  **string** <ins>username</ins>
  - Receive
      - *No Message*

## Server Code 7

### Description

The server tells us if a user has gone away or has returned.

### Function Names

  - Nicotine+: GetUserStatus

### Data Order

  - Send
    1.  **string** <ins>username</ins>
  - Receive
    1.  **string** <ins>username</ins>
    2.  **uint** <ins>status</ins> *0 == Offline, 1 == Away; 2 == Online*
    3.  **bool** <ins>privileged</ins>

## Server Code 13

### Description

Either we want to say something in the chatroom, or someone else did.

### Function Names

  - Nicotine+: SayChatroom

### Data Order

  - Send
    1.  **string** <ins>room</ins>
    2.  **string** <ins>message</ins>
  - Receive
    1.  **string** <ins>room</ins>
    2.  **string** <ins>username</ins>
    3.  **string** <ins>message</ins>

## Server Code 14

### Description

We send this message to the server when we want to join a room. If the room doesn't exist, it is created.

Server responds with this message when we join a room. Contains users list with data on everyone.

### Function Names

  - Nicotine+: JoinRoom

### Data Order

  - Send
    1.  **string** <ins>room</ins>
    2.  **bool** <ins>private</ins> *If the room doesn't exist, should the new room be private?*
  - Receive
    1.  **string** <ins>room</ins>
    2.  **uint** <ins>number of users in room</ins> **For private rooms, also contain owner and operators**
    3.  Iterate the <ins>number of users</ins>
        1.  **string** <ins>username</ins>
    4.  **uint** <ins>number of statuses</ins>
    5.  Iterate the <ins>number of statuses</ins>
        1.  **uint** <ins>status</ins>
    6.  **uint** <ins>number of user stats</ins>
    7.  Iterate the <ins>number of user stats</ins>
        1.  **uint** <ins>avgspeed</ins>
        2.  **uint64** <ins>uploadnum</ins>
        3.  **uint** <ins>files</ins>
        4.  **uint** <ins>dirs</ins>
    8.  **uint** <ins>number of slotsfree</ins>
    9.  Iterate the <ins>number of slotsfree</ins>
        1.  **uint** <ins>slotsfree</ins>
    10. **uint** <ins>number of user countries</ins>
    11. Iterate the <ins>number of user countries</ins>
        1.  **string** <ins>countrycode</ins> *Uppercase country code*
    12. **string** <ins>owner</ins> **If private room**
    13. **uint** <ins>number of operators in room</ins> **If private room**
    14. Iterate the <ins>number of operators</ins>
        1.  **string** <ins>operator</ins>

## Server Code 15

### Description

We send this to the server when we want to leave a room.

### Function Names

  - Nicotine+: LeaveRoom

### Data Order

  - Send
    1.  **string** <ins>room</ins>
  - Receive
    1.  **string** <ins>room</ins>

## Server Code 16

### Description

The server tells us someone has just joined a room we're in.

### Function Names

  - Nicotine+: UserJoinedRoom

### Data Order

  - Send
      - *No Message*
  - Receive
    1.  **string** <ins>room</ins>
    2.  **string** <ins>username</ins>
    3.  **uint** <ins>status</ins>
    4.  **uint** <ins>avgspeed</ins>
    5.  **uint64** <ins>uploadnum</ins>
    6.  **uint** <ins>files</ins>
    7.  **uint** <ins>dirs</ins>
    8.  **uint** <ins>slotsfree</ins>
    9.  **string** <ins>countrycode</ins> *Uppercase country code*

## Server Code 17

### Description

The server tells us someone has just left a room we're in.

### Function Names

  - Nicotine+: UserLeftRoom

### Data Order

  - Send
      - *No Message*
  - Receive
    1.  **string** <ins>room</ins>
    2.  **string** <ins>username</ins>

## Server Code 18

### Description

Either we ask server to tell someone else we want to establish a connection with them, or server tells us someone wants to connect with us. Used when the side that wants a connection can't establish it, and tries to go the other way around (direct connection has failed).

See also: [Peer Connection Message Order](#peer-connection-message-order)

### Function Names

  - Nicotine+: ConnectToPeer

### Data Order

  - Send
    1.  **uint** <ins>token</ins>
    2.  **string** <ins>username</ins>
    3.  **string** <ins>type</ins> *Connection Type (P, F or D)*
  - Receive
    1.  **string** <ins>username</ins>
    2.  **string** <ins>type</ins> *Connection Type (P, F or D)*
    3.  **ip** <ins>ip</ins>
    4.  **uint** <ins>port</ins>
    5.  **uint** <ins>token</ins> *Use this token for [Pierce Firewall](#peer-init-code-0)*
    6.  **bool** <ins>privileged</ins>
    7.  **bool** <ins>use obfuscation</ins>
    8.  **uint** <ins>obfuscated port</ins>

## Server Code 22

### Description

Chat phrase sent to someone or received by us in private.

### Function Names

  - Nicotine+: MessageUser

### Data Order

  - Send
    1.  **string** <ins>username</ins>
    2.  **string** <ins>message</ins>
  - Receive
    1.  **uint** <ins>ID</ins>
    2.  **uint** <ins>timestamp</ins>
    3.  **string** <ins>username</ins>
    4.  **string** <ins>message</ins>
    5.  **bool** <ins>new message</ins> **1 if message is new, 0 if message is re-sent (e.g. if recipient was offline)**

## Server Code 23

### Description

We send this to the server to confirm that we received a private message. If we don't send it, the server will keep sending the chat phrase to us.

### Function Names

  - Nicotine+: MessageAcked

### Data Order

  - Send
    1.  **uint** <ins>message ID</ins>
  - Receive
      - *No Message*

## Server Code 25

### Description

**OBSOLETE, use [RoomSearch](#server-code-120) server message**

We send this to the server when we search for something in a room.

### Function Names

  - Nicotine+: FileSearchRoom

### Data Order

  - Send
    1.  **uint** <ins>token</ins>
    1.  **uint** <ins>room id</ins>
    2.  **string** <ins>search query</ins>
  - Receive
      - *No Message*

## Server Code 26

### Description

We send this to the server when we search for something. Alternatively, the server sends this message outside the distributed network to tell us that someone is searching for something, currently used for [UserSearch](#server-code-42) and [RoomSearch](#server-code-120) requests.

The token is a random number generated by the client and is used to track the search results.

### Function Names

  - Nicotine+: FileSearch

### Data Order

  - Send
    1.  **uint** <ins>token</ins>
    2.  **string** <ins>search query</ins>
  - Receive
    1.  **string** <ins>username</ins>
    2.  **uint** <ins>token</ins>
    3.  **string** <ins>search query</ins>

## Server Code 28

### Description

We send our new status to the server. Status is a way to define whether you're available or busy. 

*1 = Away  
2 = Online*

### Function Names

  - Nicotine+: SetStatus

### Data Order

  - Send
    1.  **int** <ins>status</ins>
  - Receive
      - *No Message*

## Server Code 32

### Description

**DEPRECATED**

We test if the server responds.

### Function Names

  - Nicotine+: ServerPing

### Data Order

  - Send
      - Empty Message
  - Receive
      - Empty Message

## Server Code 33

### Description

**OBSOLETE, no longer used**

### Function Names

  - Nicotine+: SendConnectToken

### Data Order

  - Send
    1.  **string** <ins>username</ins>
    2.  **uint** <ins>token</ins>
  - Receive
    1.  **string** <ins>username</ins>
    2.  **uint** <ins>token</ins>

## Server Code 34

### Description

**OBSOLETE, use [SendUploadSpeed](#server-code-121) server message**

We used to send this after a finished download to let the server update the speed statistics for a user.

### Function Names

  - Nicotine+: SendDownloadSpeed

### Data Order

  - Send
    1.  **string** <ins>username</ins>
    2.  **uint** <ins>speed</ins>
  - Receive
      - *No Message*

## Server Code 35

### Description

We send this to server to indicate the number of folder and files that we share.

### Function Names

  - Nicotine+: SharedFoldersFiles

### Data Order

  - Send
    1.  **uint** <ins>dirs</ins>
    2.  **uint** <ins>files</ins>
  - Receive
      - *No Message*

## Server Code 36

### Description

The server sends this to indicate a change in a user's statistics, if we've requested to watch the user in AddUser previously. A user's stats can also be requested by sending a GetUserStats message to the server, but AddUser should be used instead.

### Function Names

  - Nicotine+: GetUserStats

### Data Order

  - Send
    1.  **string** <ins>username</ins>
  - Receive
    1.  **string** <ins>username</ins>
    2.  **uint** <ins>avgspeed</ins>
    3.  **uint64** <ins>uploadnum</ins>
    4.  **uint** <ins>files</ins>
    5.  **uint** <ins>dirs</ins>

## Server Code 40

### Description

**OBSOLETE, no longer sent by the server**

The server sends this to indicate if someone has download slots available or not.

### Function Names

  - Nicotine+: QueuedDownloads

### Data Order

  - Send
      - *No Message*
  - Receive
    1.  **string** <ins>username</ins>
    2.  **bool** <ins>slotsfree</ins> *Can
        immediately download*

## Server Code 41

### Description

The server sends this if someone else logged in under our nickname, and then disconnects us.

### Function Names

  - Nicotine+: Relogged

### Data Order

  - Send
      - *No Message*
  - Receive
      - Empty Message

## Server Code 42

### Description

We send this to the server when we search a specific user's shares. The token is a random number generated by the client and is used to track the search results.

### Function Names

  - Nicotine+: UserSearch

### Data Order

  - Send
    1.  **string** <ins>username</ins>
    2.  **uint** <ins>token</ins>
    3.  **string** <ins>search query</ins>
  - Receive
      - *No Message*

## Server Code 51

### Description

**DEPRECATED, used in Soulseek NS but not SoulseekQt**

We send this to the server when we add an item to our likes list.

### Function Names

  - Nicotine+: AddThingILike

### Data Order

  - Send
    1.  **string** <ins>item</ins>
  - Receive
      - *No Message*

## Server Code 52

### Description

**DEPRECATED, used in Soulseek NS but not SoulseekQt**

We send this to the server when we remove an item from our likes list.

### Function Names

  - Nicotine+: RemoveThingILike

### Data Order

  - Send
    1.  **string** <ins>item</ins>
  - Receive
      - *No Message*

## Server Code 54

### Description

**DEPRECATED, used in Soulseek NS but not SoulseekQt**

The server sends us a list of personal recommendations and a number for each.

### Function Names

  - Nicotine+: Recommendations

### Data Order

  - Send
      - Empty Message
  - Receive
    1.  **uint** <ins>number of total recommendations</ins>
    2.  Iterate for <ins>number of total recommendations</ins>
        1.  **string** <ins>recommendation</ins>
        2.  **int** <ins>number of recommendations this recommendation has</ins>
    3.  **uint** <ins>number of total unrecommendations</ins>
    4.  Iterate for <ins>number of total unrecommendations</ins>
        1.  **string** <ins>unrecommendation</ins>
        2.  **int** <ins>number of unrecommendations this unrecommendation has (negative)</ins>

## Server Code 56

### Description

**DEPRECATED, used in Soulseek NS but not SoulseekQt**

The server sends us a list of global recommendations and a number for each.

### Function Names

  - Nicotine+: GlobalRecommendations

### Data Order

  - Send
      - Empty Message
  - Receive
    1.  **uint** <ins>number of total recommendations</ins>
    2.  Iterate for <ins>number of total recommendations</ins>
        1.  **string** <ins>recommendation</ins>
        2.  **int** <ins>number of recommendations this recommendation has</ins>
    3.  **uint** <ins>number of total unrecommendations</ins>
    4.  Iterate for <ins>number of total unrecommendations</ins>
        1.  **string** <ins>unrecommendation</ins>
        2.  **int** <ins>number of unrecommendations this unrecommendation has (negative)</ins>

## Server Code 57

### Description

**DEPRECATED, used in Soulseek NS but not SoulseekQt**

We ask the server for a user's liked and hated interests. The server responds with a list of interests.

### Function Names

  - Nicotine+: UserInterests

### Data Order

  - Send
    1.  **string** <ins>username</ins>
  - Receive
    1.  **string** <ins>username</ins>
    2.  **uint** <ins>number of liked interests</ins>
    3.  Iterate for <ins>number of liked interests</ins>
        1.  **string** <ins>interest</ins>
    4.  **uint** <ins>number of hated interests</ins>
    5.  Iterate for <ins>number of hated interests</ins>
        1.  **string** <ins>interest</ins>

## Server Code 58

### Description

**OBSOLETE, no longer used since Soulseek stopped supporting third-party servers in 2002**

We send this to the server to run an admin command (e.g. to ban or silence a user) if we have admin status on the server.

### Function Names

  - Nicotine+: AdminCommand

### Data Order

  - Send
    1.  **string** <ins>command</ins>
    2.  **uint** <ins>number of command arguments</ins>
    3.  Iterate for <ins>number of command arguments</ins>
        1.  **string** <ins>command argument</ins>
  - Receive
      - *No Message*

## Server Code 60

### Description

**OBSOLETE, use [PlaceInQueue](#peer-code-44) peer message**

The server sends this to indicate change in place in queue while we're waiting for files from another peer.

### Function Names

  - Nicotine+: PlaceInLineResponse

### Data Order

  - Send
    1.  **string** <ins>username</ins>
    2.  **uint** <ins>req</ins>
    3.  **uint** <ins>place</ins>
  - Receive
    1.  **string** <ins>username</ins>
    2.  **uint** <ins>req</ins>
    3.  **uint** <ins>place</ins>

## Server Code 62

### Description

**OBSOLETE, no longer sent by the server**

The server tells us a new room has been added.

### Function Names

  - Nicotine+: RoomAdded

### Data Order

  - Send
      - *No Message*
  - Receive
    1.  **string** <ins>room</ins>

## Server Code 63

### Description

**OBSOLETE, no longer sent by the server**

The server tells us a room has been removed.

### Function Names

  - Nicotine+: RoomRemoved

### Data Order

  - Send
      - *No Message*
  - Receive
    1.  **string** <ins>room</ins>

## Server Code 64

### Description

The server tells us a list of rooms and the number of users in them. When connecting to the server, the server only sends us rooms with at least 5 users. A few select rooms are also excluded, such as nicotine and The Lobby. Requesting the room list yields a response containing the missing rooms.

### Function Names

  - Nicotine+: RoomList

### Data Order

  - Send
      - Empty Message
  - Receive
    1.  **uint** <ins>number of rooms</ins>
    2.  Iterate for <ins>number of rooms</ins>
        1.  **string** <ins>room</ins>
    3.  **uint** <ins>number of rooms</ins>
    4.  Iterate for <ins>number of rooms</ins>
        1.  **uint** <ins>number of users in room</ins>

<!-- end list -->

1.  **uint** <ins>number of owned private rooms</ins>
2.  Iterate for <ins>number of owned private rooms</ins>
    1.  **string** <ins>owned private room</ins>
3.  **uint** <ins>number of owned private rooms</ins>
4.  Iterate for <ins>number of owned private rooms</ins>
    1.  **uint** <ins>number of users in owned private room</ins>

<!-- end list -->

1.  **uint** <ins>number of private rooms (except owned)</ins>
2.  Iterate for <ins>number of private rooms (except owned)</ins>
    1.  **string** <ins>private room</ins>
3.  **uint** <ins>number of private rooms (except owned)</ins>
4.  Iterate for <ins>number of private rooms (except owned)</ins>
    1.  **uint** <ins>number of users in private rooms (except owned)</ins>

<!-- end list -->

1.  **uint** <ins>number of operated private rooms</ins>
2.  Iterate for <ins>number of operated private rooms</ins>
    1.  **string** <ins>operated private room</ins>

## Server Code 65

### Description

**OBSOLETE, no results even with official client**

We send this to search for an exact file name and folder, to find other sources.

### Function Names

  - Nicotine+: ExactFileSearch

### Data Order

  - Send
    1.  **uint** <ins>token</ins>
    2.  **string** <ins>filename</ins>
    3.  **string** <ins>path</ins>
    4.  **uint64** <ins>filesize</ins>
    5.  **uint** <ins>checksum</ins>
  - Receive
    1.  **string** <ins>username</ins>
    2.  **uint** <ins>token</ins>
    3.  **string** <ins>filename</ins>
    4.  **string** <ins>path</ins>
    5.  **uint64** <ins>filesize</ins>
    6.  **uint** <ins>checksum</ins>

## Server Code 66

### Description

A global message from the server admin has arrived.

### Function Names

  - Nicotine+: AdminMessage

### Data Order

  - Send
      - *No Message*
  - Receive
    1.  **string** <ins>message</ins>

## Server Code 67

### Description

**OBSOLETE, no longer used**

We send this to get a global list of all users online.

### Function Names

  - Nicotine+: GlobalUserList

### Data Order

  - Send
      - Empty Message
  - Receive
    1.  **uint** <ins>number of users in room</ins>
    2.  Iterate the <ins>number of users</ins>
        1.  **string** <ins>username</ins>
    3.  **uint** <ins>number of userdata</ins>
    4.  Iterate the <ins>number of users</ins>
        1.  **uint** <ins>status</ins>
    5.  **uint** <ins>number of userdata</ins>
    6.  Iterate the <ins>userdata</ins>
        1.  **uint** <ins>avgspeed</ins>
        2.  **uint64** <ins>uploadnum</ins>
        3.  **uint** <ins>files</ins>
        4.  **uint** <ins>dirs</ins>
    7.  **uint** <ins>number of slotsfree</ins>
    8.  Iterate thru number of slotsfree
        1.  **uint** <ins>slotsfree</ins>
    9. **uint** <ins>number of usercountries</ins>
    10. Iterate thru number of usercountries
        1.  **string** <ins>countrycode</ins> *Uppercase country code*

## Server Code 68

### Description

**OBSOLETE, no longer used**

Server message for tunneling a chat message.

### Function Names

  - Nicotine+: TunneledMessage

### Data Order

  - Send
    1.  **string** <ins>username</ins>
    2.  **uint** <ins>token</ins>
    3.  **uint** <ins>code</ins>
    4.  **string** <ins>message</ins>
  - Receive
    1.  **string** <ins>username</ins>
    2.  **uint** <ins>code</ins>
    3.  **uint** <ins>token</ins>
    4.  **ip** <ins>ip</ins>
    5.  **uint** <ins>port</ins>
    6.  **string** <ins>message</ins>

## Server Code 69

### Description

The server sends us a list of privileged users, a.k.a. users who have donated.

### Function Names

  - Nicotine+: PrivilegedUsers

### Data Order

  - Send
      - *No Message*
  - Receive
    1.  **uint** <ins>number of users</ins>
    2.  Iterate <ins>number of users</ins>
        1.  **string** <ins>username</ins>

## Server Code 71

### Description

We inform the server if we have a distributed parent or not. If not, the server eventually sends us a PossibleParents message with a list of possible parents to connect to. If no candidates are found, no such message is sent by the server, and we eventually become a branch root.

### Function Names

  - Nicotine+: HaveNoParent

### Data Order

  - Send
    1.  **bool** <ins>have parents</ins>
  - Receive
      - *No Message*

## Server Code 73

### Description

**DEPRECATED, sent by Soulseek NS but not SoulseekQt**

We send the IP address of our parent to the server.

### Function Names

  - Nicotine+: SearchParent

### Data Order

  - Send
    1.  **ip** <ins>ip</ins>
  - Receive
      - *No Message*

## Server Code 83

### Description

The server informs us about the minimum upload speed required to become a parent in the distributed network.

### Function Names

  - Nicotine+: ParentMinSpeed

### Data Order

  - Send
      - *No Message*
  - Receive
    1.  **uint** <ins>speed</ins>

## Server Code 84

### Description

The server sends us a speed ratio determining the number of children we can have in the distributed network. The maximum number of children is our upload speed divided by the speed ratio.

### Function Names

  - Nicotine+: ParentSpeedRatio

### Data Order

  - Send
      - *No Message*
  - Receive
    1.  **uint** <ins>ratio</ins>

## Server Code 86

### Description

**OBSOLETE, no longer sent by the server**

### Function Names

  - Nicotine+: ParentInactivityTimeout

### Data Order

  - Send
      - *No Message*
  - Receive
    1.  **uint** <ins>number</ins>

## Server Code 87

### Description

**OBSOLETE, no longer sent by the server**

### Function Names

  - Nicotine+: SearchInactivityTimeout

### Data Order

  - Send
      - *No Message*
  - Receive
    1.  **uint** <ins>number</ins>

## Server Code 88

### Description

**OBSOLETE, no longer sent by the server**

### Function Names

  - Nicotine+: MinParentsInCache

### Description

### Data Order

  - Send
      - *No Message*
  - Receive
    1.  **uint** <ins>number</ins>

## Server Code 90

### Description

**OBSOLETE, no longer sent by the server**

### Function Names

  - Nicotine+: DistribAliveInterval

### Data Order

  - Send
      - *No Message*
  - Receive
    1.  **uint** <ins>number</ins>

## Server Code 91

### Description

**OBSOLETE, no longer sent by the server**

The server sends us the username of a new privileged user, which we add to our list of global privileged users.

### Function Names

  - Nicotine+: AddToPrivileged

### Data Order

  - Send
      - *No Message*
  - Receive
    1.  **string** <ins>username</ins>

## Server Code 92

### Description

We ask the server how much time we have left of our privileges. The server responds with the remaining time, in seconds.

### Function Names

  - Nicotine+: CheckPrivileges

### Data Order

  - Send
      - Empty Message
  - Receive
    1.  **uint** <ins>time left</ins>

## Server Code 93

### Description

The server sends us an embedded distributed message. The only type of distributed message sent at present is [DistribSearch](#distributed-code-3) (distributed code 3). If we receive such a message, we are a branch root in the distributed network, and we distribute the embedded message (not the unpacked distributed message) to our child peers.

### Function Names

  - Nicotine+: EmbeddedMessage

### Data Order

  - Send
      - *No Message*
  - Receive
    1.  **uchar** <ins>distributed code</ins>
    2.  **bytes** <ins>distributed message</ins> *Raw message associated with distributed code*

## Server Code 100

### Description

We tell the server if we want to accept child nodes.

### Function Names

  - Nicotine+: AcceptChildren

### Data Order

  - Send
    1.  **bool** <ins>accept</ins>
  - Receive
      - *No Message*

## Server Code 102

### Description

The server send us a list of max 10 possible distributed parents to connect to. Messages of this type are sent to us at regular intervals, until we tell the server we don't need more possible parents with a HaveNoParent message.

The received list always contains users whose upload speed is higher than our own. If we have the highest upload speed on the server, we become a branch root, and start receiving [SearchRequest](#server-code-93) messages directly from the server.

### Function Names

  - Nicotine+: PossibleParents

### Data Order

  - Send
      - *No Message*
  - Receive
    1.  **uint** <ins>number of parents</ins>
    2.  Iterate for <ins>number of parents</ins>
        1.  **string** <ins>username</ins>
        2.  **ip** <ins>ip</ins>
        3.  **uint** <ins>port</ins>

## Server Code 103

### Description

### Function Names

  - Nicotine+: WishlistSearch

### Data Order

  - Send
    1.  **uint** <ins>token</ins>
    2.  **string** <ins>search query</ins>
  - Receive
      - *No Message*

## Server Code 104

### Description

### Function Names

  - Nicotine+: WishlistInterval

### Data Order

  - Send
      - *No Message*
  - Receive
    1.  **uint** <ins>interval</ins>

## Server Code 110

### Description

**DEPRECATED, used in Soulseek NS but not SoulseekQt**

The server sends us a list of similar users related to our interests.

### Function Names

  - Nicotine+: SimilarUsers

### Data Order

  - Send
      - Empty Message
  - Receive
    1.  **uint** <ins>number of users</ins>
    2.  Iterate for <ins>number of user</ins>
        1.  **string** <ins>username</ins>
        2.  **uint** <ins>status</ins>

## Server Code 111

### Description

**DEPRECATED, used in Soulseek NS but not SoulseekQt**

The server sends us a list of recommendations related to a specific item, which is usually present in the like/dislike list or an existing recommendation list.

### Function Names

  - Nicotine+: ItemRecommendations

### Data Order

  - Send
    1.  **string** <ins>item</ins>
  - Receive
    1.  **string** <ins>item</ins>
    2.  **uint** <ins>number of
        recommendations</ins><ins> </ins>
    3.  Iterate for <ins>number of
        recommendations</ins><ins> </ins>
        1.  **string** <ins>recommendation</ins>
        2.  **uint** <ins>number of recommendations
            for this recommendation (can be negative)</ins>

## Server Code 112

### Description

**DEPRECATED, used in Soulseek NS but not SoulseekQt**

The server sends us a list of similar users related to a specific item, which is usually present in the like/dislike list or recommendation list.

### Function Names

  - Nicotine+: ItemSimilarUsers

### Data Order

  - Send
    1.  **string** <ins>item</ins>
  - Receive
    1.  **string** <ins>item</ins>
    2.  **uint** <ins>number of users</ins>
    3.  Iterate for <ins>number of user</ins>
        1.  **string** <ins>username</ins>

## Server Code 113

### Description

The server returns a list of tickers in a chat room.

Tickers are customizable, user-specific messages that appear on chat room walls.

### Function Names

  - Nicotine+: RoomTickerState

### Data Order

  - Send
      - *No Message*
  - Receive
    1.  **string** <ins>room</ins>
    2.  **uint** <ins>number of users</ins>
    3.  Iterate for <ins>number of user</ins>
        1.  **string** <ins>username</ins>
        2.  **string** <ins>tickers</ins>

## Server Code 114

### Description

The server sends us a new ticker that was added to a chat room.

Tickers are customizable, user-specific messages that appear on chat room walls.

### Function Names

  - Nicotine+: RoomTickerAdd

### Data Order

  - Send
      - *No Message*
  - Receive
    1.  **string** <ins>room</ins>
    2.  **string** <ins>username</ins>
    3.  **string** <ins>ticker</ins>

## Server Code 115

### Description

The server informs us that a ticker was removed from a chat room.

Tickers are customizable, user-specific messages that appear on chat room walls.

### Function Names

  - Nicotine+: RoomTickerRemove

### Data Order

  - Send
      - *No Message*
  - Receive
    1.  **string** <ins>room</ins>
    2.  **string** <ins>username</ins>

## Server Code 116

### Description

We send this to the server when we change our own ticker in a chat room. Sending an empty ticker string removes any existing ticker in the room.

Tickers are customizable, user-specific messages that appear on chat room walls.

### Function Names

  - Nicotine+: RoomTickerSet

### Data Order

  - Send
    1.  **string** <ins>room</ins>
    2.  **string** <ins>ticker</ins>
  - Receive
      - *No Message*

## Server Code 117

### Description

**DEPRECATED, used in Soulseek NS but not SoulseekQt**

We send this to the server when we add an item to our hate list.

### Function Names

  - Nicotine+: AddThingIHate

### Data Order

  - Send
    1.  **string** <ins>item</ins>
  - Receive
      - *No Message*

## Server Code 118

### Description

**DEPRECATED, used in Soulseek NS but not SoulseekQt**

We send this to the server when we remove an item from our hate list.

### Function Names

  - Nicotine+: RemoveThingIHate

### Data Order

  - Send
    1.  **string** <ins>item</ins>
  - Receive
      - *No Message*

## Server Code 120

### Description

We send this to the server to search files shared by users who have joined a specific chat room. The token is a random number generated by the client and is used to track the search results.

### Function Names

  - Nicotine+: RoomSearch

### Data Order

  - Send
    1.  **string** <ins>room</ins>
    2.  **uint** <ins>token</ins>
    3.  **string** <ins>search query</ins>
  - Receive
      - *No Message*

## Server Code 121

### Description

We send this after a finished upload to let the server update the speed statistics for ourselves.

### Function Names

  - Nicotine+: SendUploadSpeed

### Data Order

  - Send
    1.  **uint** <ins>speed</ins>
  - Receive
      - *No Message*

## Server Code 122

### Description

**DEPRECATED, use [AddUser](#server-code-5) and [GetUserStatus](#server-code-7) server messages**

We ask the server whether a user is privileged or not.

### Function Names

  - Nicotine+: UserPrivileged

### Data Order

  - Send
    1.  **string** <ins>username</ins>
  - Receive
    1.  **string** <ins>username</ins>
    2.  **bool** <ins>privileged</ins>

## Server Code 123

### Description

We give (part of) our privileges, specified in days, to another user on the network.

### Function Names

  - Nicotine+: GivePrivileges

### Data Order

  - Send
    1.  **string** <ins>username</ins>
    2.  **uint** <ins>days</ins>
  - Receive
      - *No Message*

## Server Code 124

### Description

**DEPRECATED, sent by Soulseek NS but not SoulseekQt**

### Function Names

  - Nicotine+: NotifyPrivileges

### Data Order

  - Send
    1.  **uint** <ins>token</ins>
    2.  **string** <ins>username</ins>
  - Receive
    1.  **uint** <ins>token</ins>
    2.  **string** <ins>username</ins>

## Server Code 125

### Description

**DEPRECATED, no longer used**

### Function Names

  - Nicotine+: AckNotifyPrivileges

### Data Order

  - Send
    1.  **uint** <ins>token</ins>
  - Receive
    1.  **uint** <ins>token</ins>

## Server Code 126

### Description

We tell the server what our position is in our branch (xth generation) on the distributed network.

### Function Names

  - Nicotine+: BranchLevel

### Data Order

  - Send
    1.  **uint** <ins>branch level</ins>
  - Receive
      - *No Message*

## Server Code 127

### Description

We tell the server the username of the root of the branch we're in on the distributed network.

### Function Names

  - Nicotine+: BranchRoot

### Data Order

  - Send
    1.  **string** <ins>branch root</ins>
  - Receive
      - *No Message*

## Server Code 129

### Description

**DEPRECATED, sent by Soulseek NS but not SoulseekQt**

We tell the server the maximum number of generation of children we have on the distributed network.

### Function Names

  - Nicotine+: ChildDepth

### Data Order

  - Send
    1.  **uint** <ins>child depth</ins>
  - Receive
      - *No Message*

## Server Code 130

### Description

The server asks us to reset our distributed parent and children.

### Function Names

  - Nicotine+: ResetDistributed

### Data Order

  - Send
      - *No Message*
  - Receive
      - Empty Message

## Server Code 133

### Description

The server sends us a list of room users that we can alter (add operator abilities / dismember).

### Function Names

  - Nicotine+: PrivateRoomUsers

### Data Order

  - Send
    1.  *No Message*
  - Receive
    1.  **string** <ins>room</ins>
    2.  **uint** <ins>number of users</ins>
    3.  Iterate for <ins>number of users</ins>
        1.  **string** <ins>users</ins>

## Server Code 134

### Description

We send this to inform the server that we've added a user to a private room.

### Function Names

  - Nicotine+: PrivateRoomAddUser

### Data Order

  - Send
    1.  **string** <ins>room</ins>
    2.  **string** <ins>username</ins>
  - Receive
    1.  **string** <ins>room</ins>
    2.  **string** <ins>username</ins>

## Server Code 135

### Description

We send this to inform the server that we've removed a user from a private room.

### Function Names

  - Nicotine+: PrivateRoomRemoveUser

### Data Order

  - Send
    1.  **string** <ins>room</ins>
    2.  **string** <ins>username</ins>
  - Receive
    1.  **string** <ins>room</ins>
    2.  **string** <ins>username</ins>

## Server Code 136

### Description

We send this to the server to remove our own membership of a private room.

### Function Names

  - Nicotine+: PrivateRoomDismember

### Data Order

  - Send
    1.  **string** <ins>room</ins>
  - Receive
      - *No Message*

## Server Code 137

### Description

We send this to the server to stop owning a private room.

### Function Names

  - Nicotine+: PrivateRoomDisown

### Data Order

  - Send
    1.  **string** <ins>room</ins>
  - Receive
      - *No Message*

## Server Code 138

### Description

**OBSOLETE, no longer used**

Unknown purporse

### Function Names

  - Nicotine+: PrivateRoomSomething

### Data Order

  - Send
    1.  **string** <ins>room</ins>
  - Receive
    1.  **string** <ins>room</ins>

## Server Code 139

### Description

The server sends us this message when we are added to a private room.

### Function Names

  - Nicotine+: PrivateRoomAdded

### Data Order

  - Send
      - *No Message*
  - Receive
    1.  **string** <ins>room</ins>

## Server Code 140

### Description

The server sends us this message when we are removed from a private room.

### Function Names

  - Nicotine+: PrivateRoomRemoved

### Data Order

  - Send
      - *No Message*
  - Receive
    1.  **string** <ins>room</ins>

## Server Code 141

### Description

We send this when we want to enable or disable invitations to private rooms.

### Function Names

  - Nicotine+: PrivateRoomToggle

### Data Order

  - Send
    1.  **bool** <ins>enable</ins>
  - Receive
    1.  **bool** <ins>enable</ins>

## Server Code 142

### Description

We send this to the server to change our password. We receive a response if our password changes.

### Function Names

  - Nicotine+: ChangePassword

### Data Order

  - Send
    1.  **string** <ins>pass</ins>
  - Receive
    1.  **string** <ins>pass</ins>

## Server Code 143

### Description

We send this to the server to add private room operator abilities to a user.

### Function Names

  - Nicotine+: PrivateRoomAddOperator

### Data Order

  - Send
    1.  **string** <ins>room</ins>
    2.  **string** <ins>username</ins>
  - Receive
    1.  **string** <ins>room</ins>
    2.  **string** <ins>username</ins>

## Server Code 144

### Description

We send this to the server to remove private room operator abilities from a user.

### Function Names

  - Nicotine+: PrivateRoomRemoveOperator

### Data Order

  - Send
    1.  **string** <ins>room</ins>
    2.  **string** <ins>username</ins>
  - Receive
    1.  **string** <ins>room</ins>
    2.  **string** <ins>username</ins>

## Server Code 145

### Description

The server send us this message when we're given operator abilities in a private room.

### Function Names

  - Nicotine+: PrivateRoomOperatorAdded

### Data Order

  - Send
      - *No Message*
  - Receive
    1.  **string** <ins>room</ins>

## Server Code 146

### Description

The server send us this message when our operator abilities are removed in a private room.

### Function Names

  - Nicotine+: PrivateRoomOperatorRemoved

### Data Order

  - Send
      - *No Message*
  - Receive
    1.  **string** <ins>room</ins>

## Server Code 148

### Description

The server sends us a list of operators in a specific room, that we can remove operator abilities from.

### Function Names

  - Nicotine+: PrivateRoomOwned

### Data Order

  - Send
      - *No Message*
  - Receive
    1.  **string** <ins>room</ins>
    2.  **uint** <ins>number of operators in
        room</ins>
    3.  Iterate the <ins>number of operators</ins>
        1.  **string** <ins>operator</ins>

## Server Code 149

### Description

Sends a broadcast private message to the given list of users.

### Function Names

  - Nicotine+: MessageUsers

### Data Order

  - Send
    1.  **uint** <ins>number of users</ins>
    2.  Iterate the <ins>number of users</ins>
        1.  **string** <ins>username</ins>
    3.  **string** <ins>message</ins>
  - Receive
      - *No Message*

## Server Code 150

### Description

**DEPRECATED, used in Soulseek NS but not SoulseekQt**

We ask the server to send us messages from all public rooms, also known as public chat.

### Function Names

  - Nicotine+: JoinPublicRoom

### Data Order

  - Send
      - Empty Message
  - Receive
      - *No Message*

## Server Code 151

### Description

**DEPRECATED, used in Soulseek NS but not SoulseekQt**

We ask the server to stop sending us messages from all public rooms, also known as public chat.

### Function Names

  - Nicotine+: LeavePublicRoom

### Data Order

  - Send
      - Empty Message
  - Receive
      - *No Message*

## Server Code 152

### Description

**DEPRECATED, used in Soulseek NS but not SoulseekQt**

The server sends this when a new message has been written in a public room (every single line written in every public room).

### Function Names

  - Nicotine+: PublicRoomMessage

### Data Order

  - Send
      - *No Message*
  - Receive
    1.  **string** <ins>room</ins>
    2.  **string** <ins>username</ins>
    3.  **string** <ins>message</ins>

## Server Code 153

### Description

**OBSOLETE, server sends empty list as of 2018**

The server returns a list of related search terms for a search query.

### Function Names

  - Nicotine+: RelatedSearch

### Data Order

  - Send
    1.  **string** <ins>query</ins>
  - Receive
    1.  **string** <ins>query</ins>
    2.  **uint** <ins>number of terms</ins>
    3.  Iterate for <ins>number of term</ins>
        1.  **string** <ins>term</ins>
        2.  **uint** <ins>score</ins>

## Server Code 1001

### Description

We send this to say we can't connect to peer after it has asked us to connect. We receive this if we asked peer to connect and it can't do this. This message means a connection can't be established either way.

See also: [Peer Connection Message Order](#peer-connection-message-order)

### Function Names

  - Nicotine+: CantConnectToPeer

### Data Order

  - Send
    1.  **uint** <ins>token</ins>
    2.  **string** <ins>username</ins>
  - Receive
    1.  **uint** <ins>token</ins>
    2.  **string** <ins>username</ins>

## Server Code 1003

### Description

Server tells us a new room cannot be created. This message only seems to be sent if you try to create a room with the same name as an existing private room. In other cases, such as using a room name with leading or trailing spaces, only a private message containing an error message is sent.

### Function Names

  - Nicotine+: CantCreateRoom

### Data Order

  - Send
      - *No Message*
  - Receive
    1.  **string** <ins>room</ins>

# Peer Init Messages

| Send         | Receive           |
| ------------ | ----------------- |
| Send to Peer | Receive from Peer |

In Nicotine+, these messages are matched to their message number in slskproto.py in the SlskProtoThread function, defined in slskmessages.py and callbacks for the messages are set in pynicotine.py.

### Message Format

| Message Length | Code   | Message Contents |
| -------------- | ------ | ---------------- |
| 4 Bytes        | 1 Byte | ...              |

### Message Index

| Code | Message                              |
| ---- | ------------------------------------ |
| 0    | [Pierce Firewall](#peer-init-code-0) |
| 1    | [Peer Init](#peer-init-code-1)       |

## Peer Connection Message Order

1.  User A sends a [Peer Init](#peer-init-code-1) to User B.  
If this succeeds, a connection is established, and User A is free to send peer messages.  
If this fails (socket cannot connect), User A proceeds with an indirect connection request (step 2).
2.  User A sends [ConnectToPeer](#server-code-18) to the Server with a unique token
3.  The Server sends a [ConnectToPeer](#server-code-18) response to User B with the same token
4.  User B sends a [Pierce Firewall](#peer-init-code-0) to User A with the same token.  
If this succeeds, a connection is established, and User A is free to send peer messages.  
If this fails, User B retries for ~1 minute. If this still fails, no connection is possible, and User B proceeds with step 5.
5.  User B sends a [Cannot Connect](#server-code-1001) to the Server.
6.  The Server sends a [Cannot Connect](#server-code-1001) response to User A.

## Peer Init Code 0

### Description

This is the very first message sent by the peer that established a connection, if it has been asked by the other peer to do so. The token is taken from the ConnectToPeer server message.

See also: [Peer Connection Message Order](#peer-connection-message-order)

### Function Names

  - Nicotine+: PierceFireWall

### Data Order

  - Send
      - **uint** <ins>token</ins> *Unique Number*
  - Receive
      - **uint** <ins>token</ins> *Unique Number*

## Peer Init Code 1

### Description

This message is sent by the peer that initiated a connection, not necessarily a peer that actually established it. Token apparently can be anything. Type is 'P' if it's anything but filetransfer, 'F' otherwise.

See also: [Peer Connection Message Order](#peer-connection-message-order)

### Function Names

  - Nicotine+: PeerInit

### Data Order

  - Send
      - **string** <ins>username</ins> *Local Username*
      - **string** <ins>type</ins> *Connection Type (P, F or D)*
      - **uint** <ins>token</ins> *Unique Number*
  - Receive
      - **string** <ins>username</ins> *Remote Username*
      - **string** <ins>type</ins> *Connection Type (P, F or D)*
      - **uint** <ins>token</ins> *Unique Number*

# Peer Messages

| Send         | Receive           |
| ------------ | ----------------- |
| Send to Peer | Receive from Peer |

In Nicotine, these messages are matched to their message number in slskproto.py in the SlskProtoThread function, defined in slskmessages.py and callbacks for the messages are set in pynicotine.py.

### Message Format

| Message Length | Code    | Message Contents |
| -------------- | ------- | ---------------- |
| 4 Bytes        | 4 Bytes | ...              |

### Message Index

| Code | Message                                    | Status                     |
| ---- | ------------------------------------------ | -------------------------- |
| 1    | Private Message                            | Obsolete, contents unknown |
| 4    | [Shares Request](#peer-code-4)             |                            |
| 5    | [Shares Reply](#peer-code-5)               |                            |
| 8    | [Search Request](#peer-code-8)             | Obsolete                   |
| 9    | [Search Reply](#peer-code-9)               |                            |
| 10   | Room Invitation                            | Obsolete, contents unknown |
| 14   | Cancelled Queued Transfer                  | Obsolete, contents unknown |
| 15   | [User Info Request](#peer-code-15)         |                            |
| 16   | [User Info Reply](#peer-code-16)           |                            |
| 33   | Send Connect Token                         | Obsolete, contents unknown |
| 34   | Move Download To Top                       | Obsolete, contents unknown |
| 36   | [Folder Contents Request](#peer-code-36)   |                            |
| 37   | [Folder Contents Reply](#peer-code-37)     |                            |
| 40   | [Transfer Request](#peer-code-40)          |                            |
| 41   | [Download Reply](#peer-code-41-a)          | Deprecated                 |
| 41   | [Upload Reply](#peer-code-41-b)            |                            |
| 42   | [Upload Placehold](#peer-code-42)          | Obsolete                   |
| 43   | [Queue Upload](#peer-code-43)              |                            |
| 44   | [Place In Queue Reply](#peer-code-44)      |                            |
| 46   | [Upload Failed](#peer-code-46)             |                            |
| 47   | Exact File Search Request                  | Obsolete, contents unknown |
| 48   | Queued Downloads                           | Obsolete, contents unknown |
| 49   | Indirect File Search Request               | Obsolete, contents unknown |
| 50   | [Upload Denied](#peer-code-50)             |                            |
| 51   | [Place In Queue Request](#peer-code-51)    |                            |
| 52   | [Upload Queue Notification](#peer-code-52) | Deprecated                 |

## Peer Code 4

### Description

We send this to a peer to ask for a list of shared files.

### Function Names

  - Nicotine+: GetShareFileList

### Data Order

  - Send
      - Empty Message
  - Receive
      - Empty Message

## Peer Code 5

### Description

A peer responds with a list of shared files when we've sent a GetSharedFileList.

### Function Names

  - Nicotine+: SharedFileList

### Data Order

  - Send
    1.  Iterate thru shares database
        1.  **data**
  - Receive
    1.  decompress
    2.  **uint** <ins>number of directories</ins>
    3.  Iterate <ins>number of directories</ins>
        1.  **string** <ins>directory</ins>
        2.  **uint** <ins>number of files</ins>
        3.  Iterate <ins>number of files</ins>
            1.  **uchar** <ins>1</ins>
            2.  **string** <ins>filename</ins>
            3.  **unit64** <ins>file size</ins>
            4.  **string** <ins>file extension</ins>
            5.  **uint** <ins>number of attributes</ins>
            6.  Iterate for <ins>number of attributes</ins>
                1.  **uint** <ins>attribute type</ins> *see [File Attribute Types](#file-attribute-types)*
                2.  **uint** <ins>attribute value</ins>
    4.  **uint** <ins>unknown</ins> *official clients always send a value of 0*
    5.  **uint** <ins>number of private directories</ins>
    6.  Iterate <ins>number of private directories</ins>
        1.  **string** <ins>directory</ins>
        2.  **uint** <ins>number of files</ins>
        3.  Iterate <ins>number of files</ins>
            1.  **uchar** <ins>1</ins>
            2.  **string** <ins>filename</ins>
            3.  **uint64** <ins>file size</ins>
            4.  **string** <ins>file extension</ins>
            5.  **uint** <ins>number of attributes</ins>
            6.  Iterate for <ins>number of attributes</ins>
                1.  **uint** <ins>attribute type</ins> *see [File Attribute Types](#file-attribute-types)*
                2.  **uint** <ins>attribute value</ins>

## Peer Code 8

### Description

**OBSOLETE, use [UserSearch](#server-code-42) server message**

We send this to the peer when we search for a file. Alternatively, the peer sends this to tell us it is searching for a file.

### Function Names

  - Nicotine+: FileSearchRequest

### Data Order

  - Send
    1.  **uint** <ins>token</ins>
    2.  **string** <ins>query</ins>
  - Receive
    1.  **uint** <ins>token</ins>
    2.  **string** <ins>query</ins>

## Peer Code 9

### Description

A peer sends this message when it has a file search match. The token is taken from original FileSearch, UserSearch or RoomSearch message.

### Function Names

  - Nicotine+: FileSearchResult

### Data Order

  - Send
    1.  **string** <ins>username</ins>
    2.  **uint** <ins>token</ins>
    3.  **uint** <ins>number of results</ins>
    4.  Iterate for <ins>number of results</ins>
        1.  **uchar** <ins>1</ins>
        2.  **string** <ins>filename</ins>
        3.  **uint64** <ins>file size</ins>
        4.  **string** <ins>file extension</ins> *(SoulseekNS requires "mp3" to show attributes)*
        5.  **uint** <ins>number of attributes</ins>
        6.  Iterate for <ins>number of attributes</ins>
            1.  **uint** <ins>attribute type</ins> *see [File Attribute Types](#file-attribute-types)*
            2.  **uint** <ins>attribute value</ins>
    5.  **bool** <ins>slotfree</ins>
    6.  **uint** <ins>avgspeed</ins>
    7.  **uint64** <ins>queue length</ins>
    8.  **uint** <ins>number of privately shared results</ins>
    9.  Iterate for <ins>number of privately shared results</ins>
        1.  **uchar** <ins>1</ins>
        2.  **string** <ins>filename</ins>
        3.  **uint64** <ins>file size</ins>
        4.  **string** <ins>file extension</ins> *(SoulseekNS requires "mp3" to show attributes)*
        5.  **uint** <ins>number of attributes</ins>
        6.  Iterate for <ins>number of attributes</ins>
            1.  **uint** <ins>attribute type</ins> *see [File Attribute Types](#file-attribute-types)*
            2.  **uint** <ins>attribute value</ins>
  - Receive
    1.  decompress
    2.  **string** <ins>username</ins>
    3.  **uint** <ins>token</ins>
    4.  **uint** <ins>number of results</ins>
    5.  Iterate for <ins>number of results</ins>
        1.  **uchar** <ins>1</ins>
        2.  **string** <ins>filename</ins>
        3.  **uint64** <ins>size</ins>
        4.  **string** <ins>file extension</ins> *(Always blank from SoulseekQt clients)*
        5.  **uint** <ins>number of attributes</ins>
        6.  Iterate for <ins>number of attributes</ins>
            1.  **uint** <ins>attribute type</ins> *see [File Attribute Types](#file-attribute-types)*
            2.  **uint** <ins>attribute value</ins>
    6.  **bool** <ins>slotfree</ins>
    7.  **uint** <ins>avgspeed</ins>
    8.  **uint64** <ins>queue length</ins>
    9.  **uint** <ins>number of privately shared results</ins>
    10.  Iterate for <ins>number of privately shared results</ins>
         1.  **uchar** <ins>1</ins>
         2.  **string** <ins>filename</ins>
         3.  **uint64** <ins>size</ins>
         4.  **string** <ins>file extension</ins> *(Always blank from SoulseekQt clients)*
         5.  **uint** <ins>number of attributes</ins>
         6.  Iterate for <ins>number of attributes</ins>
             1.  **uint** <ins>attribute type</ins> *see [File Attribute Types](#file-attribute-types)*
             2.  **uint** <ins>attribute value</ins>

## Peer Code 15

### Description

We ask the other peer to send us their user information, picture and all.

### Function Names

  - Nicotine+: UserInfoRequest

### Data Order

  - Send
      - Empty Message
  - Receive
      - Empty Message

## Peer Code 16

### Description

A peer responds with this when we've sent a UserInfoRequest.

### Function Names

  - Nicotine+: UserInfoReply

### Data Order

  - Send
    1.  **string** <ins>description</ins>
    2.  Check contents of <ins>picture</ins>
          - If <ins>picture</ins> is not empty
            1.  **bool** <ins>has picture</ins> 1
            2.  **string** <ins>picture</ins>
          - If <ins>picture</ins> is empty
            1.  **bool** <ins>has picture</ins> 0
    3.  **uint** <ins>totalupl</ins>
    4.  **uint** <ins>queuesize</ins>
    5.  **bool** <ins>slotsfree</ins> *Can immediately upload*
    6.  **uint** <ins>uploadpermitted</ins> *Who can upload anything to us?*
        *0 == No one; 1 == Everyone; 2 == Users in List; 3 == Trusted Users*
  - Receive
    1.  **string** <ins>description</ins>
    2.  **bool** <ins>has picture</ins>
    3.  Check contents of <ins>has picture</ins>
        1.  If <ins>has picture</ins> is not empty
            1.  **string** <ins>picture</ins>
    4.  **uint** <ins>totalupl</ins>
    5.  **uint** <ins>queuesize</ins>
    6.  **bool** <ins>slotsfree</ins> *Can immediately download*
    7.  **uint** <ins>uploadpermitted</ins> *Who can upload anything to this user (not sent by SoulseekQt)?*
        *0 == No one; 1 == Everyone; 2 == Users in List; 3 == Trusted Users*

## Peer Code 36

### Description

We ask the peer to send us the contents of a single folder.

### Function Names

  - Nicotine+: FolderContentsRequest

### Data Order

  - Send
    1.  **uint** <ins>number of files in directory</ins>
    2.  Iterate <ins>number of files in directory</ins>
        1.  **string** <ins>file</ins>
  - Receive
    1.  **uint** <ins>number of files in directory</ins>
    2.  Iterate <ins>number of files in directory</ins>
        1.  **string** <ins>file</ins>

## Peer Code 37

### Description

A peer responds with the contents of a particular folder (with all subfolders) when we've sent a FolderContentsRequest.

### Function Names

  - Nicotine+: FolderContentsResponse

### Data Order

  - Send
    1.  **uint** <ins>number of folders</ins>
    2.  Iterate for <ins>number of folders</ins>
        1.  **string** <ins>dir</ins>
        2.  **uint** <ins>number of files</ins>
        3.  Iterate <ins>number of files</ins>
            1.  **uchar** <ins>1</ins>
            2.  **string** <ins>file</ins>
            3.  **uint64** <ins>file size</ins>
            4.  **string** <ins>file extension</ins> *(Always blank from SoulseekQt clients)*
            5.  **uint** <ins>number of attributes</ins>
            6.  Iterate for <ins>number of attributes</ins>
                1.  **uint** <ins>attribute type</ins> *see [File Attribute Types](#file-attribute-types)*
                2.  **uint** <ins>attribute value</ins>
  - Receive
    1.  decompress
    2.  **uint** <ins>number of folders</ins>
    3.  Iterate for <ins>number of folders</ins>
        1.  **string** <ins>dir</ins>
        2.  **uint** <ins>number of files</ins>
        3.  Iterate <ins>number of files</ins>
            1.  **uchar** <ins>1</ins>
            2.  **string** <ins>file</ins>
            3.  **uint64** <ins>file size</ins>
            4.  **string** <ins>file extension</ins> *(Always blank from SoulseekQt clients)*
            5.  **uint** <ins>number of attributes</ins>
            6.  Iterate for <ins>number of attributes</ins>
                1.  **uint** <ins>attribute type</ins> *see [File Attribute Types](#file-attribute-types)*
                2.  **uint** <ins>attribute value</ins>

## Peer Code 40

### Description

This message is sent by a peer once they are ready to start uploading a file. A [TransferResponse](#peer-code-41-a) message is expected from the recipient, either allowing or rejecting the upload attempt.

This message was formely used to send a download request (direction 0) as well, but Nicotine+, Museek+ and the official clients use the [QueueUpload](#peer-code-43) message for this purpose today.

### Function Names

  - Nicotine+: TransferRequest

### Data Order

  - Send
    1.  **uint** <ins>direction</ins>
    2.  **uint** <ins>token</ins>
    3.  **string** <ins>filename</ins>
    4.  Check contents of <ins>direction</ins>
          - **uint64** <ins>filesize</ins> *if direction == 1 (upload)*
  - Receive
    1.  **uint** <ins>direction</ins>
    2.  **uint** <ins>token</ins>
    3.  **string** <ins>filename</ins>
    4.  Check contents of <ins>direction</ins>
          - **uint64** <ins>filesize</ins> *if direction == 1 (upload)*

## Peer Code 41 a

*Download Reply*

### Description

**DEPRECATED, use QueueUpload to request files**

Response to TransferRequest - either we (or the other peer) agrees, or tells the reason for rejecting the file transfer.

### Function Names

  - Nicotine+: TransferResponse

### Data Order

  - Send
    1.  **uint** <ins>token</ins>
    2.  **bool** <ins>allowed</ins>
    3.  Check contents of <ins>allowed</ins>
          - **uint64** <ins>filesize</ins> *if allowed == 1*
          - **string** <ins>reason</ins> *if allowed == 0*
  - Receive
    1.  **uint** <ins>token</ins>
    2.  **bool** <ins>allowed</ins>
    3.  Check contents of <ins>allowed</ins>
          - **uint64** <ins>filesize</ins> *if allowed == 1*
          - **string** <ins>reason</ins> *if allowed == 0*

## Peer Code 41 b

*Upload Reply*

### Description

Response to TransferRequest - either we (or the other peer) agrees, or tells the reason for rejecting the file transfer.

### Function Names

  - Nicotine+: TransferResponse

### Data Order

  - Send
    1.  **uint** <ins>token</ins>
    2.  **bool** <ins>allowed</ins>
    3.  Check contents of <ins>allowed</ins>
          - **string** <ins>reason</ins> *if allowed == 0*
  - Receive
    1.  **uint** <ins>token</ins>
    2.  **bool** <ins>allowed</ins>
    3.  Check contents of <ins>allowed</ins>
          - **string** <ins>reason</ins> *if allowed == 0*

## Peer Code 42

### Description

**OBSOLETE, no longer used**

### Function Names

  - Nicotine+: PlaceholdUpload

### Data Order

  - Send
    1.  **string** <ins>filename</ins>
  - Receive
    1.  **string** <ins>filename</ins>

## Peer Code 43

### Description

This message is used to tell a peer that an upload should be queued on their end. Once the recipient is ready to transfer the requested file, they will send an upload request.

### Function Names

  - Nicotine+: QueueUpload

### Data Order

  - Send
    1.  **string** <ins>filename</ins>
  - Receive
    1.  **string** <ins>filename</ins>

## Peer Code 44

### Description

The peer replies with the upload queue placement of the requested file.

### Function Names

  - Nicotine+: PlaceInQueue

### Data Order

  - Send
    1.  **string** <ins>filename</ins>
    2.  **uint** <ins>place</ins>
  - Receive
    1.  **string** <ins>filename</ins>
    2.  **uint** <ins>place</ins>

## Peer Code 46

### Description

This message is sent whenever a file connection of an active upload closes. Soulseek NS clients can also send this message when a file can not be read. The recipient either re-queues the upload (download on their end), or ignores the message if the transfer finished.

### Function Names

  - Nicotine+: UploadFailed

### Data Order

  - Send
    1.  **string** <ins>filename</ins>
  - Receive
    1.  **string** <ins>filename</ins>

## Peer Code 50

### Description

This message is sent to reject QueueUpload attempts and previously queued files. The reason for rejection will appear in the transfer list of the recipient.

### Function Names

  - Nicotine+: UploadDenied

### Data Order

  - Send
    1.  **string** <ins>filename</ins>
    2.  **string** <ins>reason</ins>
  - Receive
    1.  **string** <ins>filename</ins>
    2.  **string** <ins>reason</ins>

## Peer Code 51

### Description

This message is sent when asking for the upload queue placement of a file.

### Function Names

  - Nicotine+: PlaceInQueueRequest

### Data Order

  - Send
    1.  **string** <ins>filename</ins>
  - Receive
    1.  **string** <ins>filename</ins>

## Peer Code 52

### Description

**DEPRECATED, sent by Soulseek NS but not SoulseekQt**

This message is sent to inform a peer about an upload attempt initiated by us.

### Function Names

  - Nicotine+: UploadQueueNotification

### Data Order

  - Send
      - Empty Message
  - Receive
      - Empty Message

# File Messages

| Send         | Receive           |
| ------------ | ----------------- |
| Send to Peer | Receive from Peer |

These messages are sent to peers over a 'F' connection, and do not have messages codes associated with them.

### File Connection Message Format

| Message Contents |
| ---------------- |
| ...              |

### File Connection Message Index

| Message                                   |
| ----------------------------------------- |
| [File Download Init](#file-download-init) |
| [File Upload Init](#file-upload-init)     |
| [File Offset](#file-offset)               |

## File Download Init

### Description

We receive this from a peer via a 'F' connection when they want to start uploading a file to us. The token is the same as the one previously included in the TransferRequest message.

### Function Names

  - Nicotine+: FileDownloadInit

### Data Order

  - Send
      - *No Message*
  - Receive
      - **uint** <ins>token</ins>

## File Upload Init

### Description

We send this to a peer via a 'F' connection to tell them that we want to start uploading a file. The token is the same as the one previously included in the TransferRequest message.

### Function Names

  - Nicotine+: FileUploadInit

### Data Order

  - Send
      - **uint** <ins>token</ins>
  - Receive
      - *No Message*

## File Offset

### Description

We send this to the uploading peer at the beginning of a 'F' connection, to tell them how many bytes of the file we've previously downloaded. If none, the offset is 0.

### Function Names

  - Nicotine+: FileOffset

### Data Order

  - Send
      - **uint64** <ins>offset</ins>
  - Receive
      - **uint64** <ins>offset</ins>

# Distributed Messages

| Send         | Receive           |
| ------------ | ----------------- |
| Send to Node | Receive from Node |

In Nicotine+, these messages are matched to their message number in slskproto.py in the SlskProtoThread function, defined in slskmessages.py and callbacks for the messages are set in pynicotine.py.

### The Message format

| Message Length | Code   | Message Contents |
| -------------- | ------ | ---------------- |
| 4 Bytes        | 1 Byte | ...              |

### Message Index

| Code | Message                                  | Status     |
| ---- | ---------------------------------------- | ---------- |
| 0    | [Ping](#distributed-code-0)              |            |
| 3    | [Search Request](#distributed-code-3)    |            |
| 4    | [Branch Level](#distributed-code-4)      |            |
| 5    | [Branch Root](#distributed-code-5)       |            |
| 7    | [Child Depth](#distributed-code-7)       | Deprecated |
| 93   | [Embedded Message](#distributed-code-93) |            |

## Distributed Code 0

### Description

Send it every 60 sec.

### Function Names

  - Nicotine+: DistribAlive

### Data Order

  - Send
      - Empty Message
  - Receive
    1.  **uint** <ins>unknown</ins>

## Distributed Code 3

### Description

Search request that arrives through the distributed network. 
We transmit the search request to our child peers.

### Function Names

  - Nicotine+: DistribSearch

### Data Order

  - Send
    1.  **uint** <ins>unknown</ins>
    2.  **string** <ins>username</ins>
    3.  **uint** <ins>token</ins>
    4.  **string** <ins>query</ins>
  - Receive
    1.  **uint** <ins>unknown</ins>
    2.  **string** <ins>username</ins>
    3.  **uint** <ins>token</ins>
    4.  **string** <ins>query</ins>

## Distributed Code 4

### Description

We tell our distributed children what our position is in our branch (xth generation) on the distributed network.

### Function Names

  - Nicotine+: DistribBranchLevel

### Data Order

  - Send
    1.  **int** <ins>branch level</ins>
  - Receive
    1.  **int** <ins>branch level</ins>

## Distributed Code 5

### Description

We tell our distributed children the username of the root of the branch we're in on the distributed network.

### Function Names

  - Nicotine+: DistribBranchRoot

### Data Order

  - Send
    1.  **string** <ins>branch root</ins>
  - Receive
    1.  **string** <ins>branch root</ins>

## Distributed Code 7

### Description

**DEPRECATED, sent by Soulseek NS but not SoulseekQt**

We tell our distributed parent the maximum number of generation of children we have on the distributed network.

### Function Names

  - Nicotine+: DistribChildDepth

### Data Order

  - Send
    1.  **uint** <ins>child depth</ins>
  - Receive
    1.  **uint** <ins>child depth</ins>

## Distributed Code 93

### Description

A branch root sends us an embedded distributed message. The only type of distributed message sent at present is [DistribSearch](#distributed-code-3) (distributed code 3). We unpack the distributed message and distribute it to our child peers.

### Function Names

  - Nicotine+: DistribEmbeddedMessage

### Data Order

  - Send
    1.  **uchar** <ins>distributed code</ins>
    2.  **bytes** <ins>distributed message</ins> *Raw message associated with distributed code*
  - Receive
    1.  **uchar** <ins>distributed code</ins>
    2.  **bytes** <ins>distributed message</ins> *Raw message associated with distributed code*

# Credits

This documentation exists thanks to efforts from the following projects:

- Nicotine+ (Hyriand, daelstorm, mathiascode)
- slskd (jpdillingham)
- Museek+ (lbponey)
- SoleSeek
- PySoulSeek
