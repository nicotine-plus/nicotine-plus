# Soulseek Protocol Documentation

Last updated on March 16, 2024

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

### 8-bit Integer

| Number |
|--------|
| 1 Byte |

### 16-bit Integer

| Number                  |
|-------------------------|
| 2 Bytes (little-endian) |

### 32-bit Integer

| Number                  |
|-------------------------|
| 4 Bytes (little-endian) |

### 64-bit Integer

| Number                  |
|-------------------------|
| 8 Bytes (little-endian) |

### Bool

| Number          |
|-----------------|
| 1 Byte (0 or 1) |

### String

| Length of String | String |
|------------------|--------|
| uint32           | bytes  |

# Constants

### Connection Types

| Type | Connection          |
|------|---------------------|
| P    | Peer To Peer        |
| F    | File Transfer       |
| D    | Distributed Network |

### Login Failure Reasons

| Reason          | Description                                                                      |
|-----------------|----------------------------------------------------------------------------------|
| INVALIDUSERNAME | Username is longer than 30 characters or contains invalid characters (non-ASCII) |
| INVALIDPASS     | Password for existing user is incorrect                                          |
| INVALIDVERSION  | Client version is outdated                                                       |

### User Status Codes

| Code | Status  |
|------|---------|
| 0    | Offline |
| 1    | Away    |
| 2    | Online  |

### Upload Permissions

| Code | Status          |
|------|-----------------|
| 0    | No One          |
| 1    | Everyone        |
| 2    | Users in List   |
[ 3    | Permitted Users |

### Transfer Directions

| Code | Direction          |
|------|--------------------|
| 0    | Download from Peer |
| 1    | Upload to Peer     |

### Transfer Rejection Reasons

#### In Use

| String                | Comments                                    |
| --------------------- | ------------------------------------------- |
| Banned                | SoulseekQt uses 'File not shared.' instead  |
| Cancelled             |                                             |
| Complete              |                                             |
| File not shared.      | Note: Ends with a dot                       |
| File read error.      | Note: Ends with a dot                       |
| Pending shutdown.     | Note: Ends with a dot                       |
| Queued                |                                             |
| Too many files        |                                             |
| Too many megabytes    |                                             |

#### Deprecated

| String                             | Comments                                                    |
| ---------------------------------- | ----------------------------------------------------------- |
| Blocked country                    | Exclusive to Nicotine+, no longer used in Nicotine+ >=3.2.0 |
| Disallowed extension               | Sent by Soulseek NS for filtered extensions                 |
| File not shared                    | Exclusive to Nicotine+, no longer used in Nicotine+ >=3.1.1 |
| Remote file error                  | Sent by Soulseek NS in response to legacy download requests |
| User limit of x megabytes exceeded | Exclusive to Nicotine+, no longer used in Nicotine+ >=3.1.1 |
| User limit of x files exceeded     | Exclusive to Nicotine+, no longer used in Nicotine+ >=3.1.1 |

### File Attribute Types

| Code | Attribute (unit)   |
|------|--------------------|
| 0    | Bitrate (kbps)     |
| 1    | Duration (seconds) |
| 2    | VBR (0 or 1)       |
| 3    | Encoder (unused)   |
| 4    | Sample Rate (Hz)   |
| 5    | Bit Depth (bits)   |

#### File Attribute Combinations

These combinations are actively used by clients. Certain attributes can be missing if a file does not provide them.

  - Soulseek NS, SoulseekQt (2015-2-21 and earlier), Nicotine+ (lossy formats), Museek+, SoulSeeX, slskd (lossy formats):
      - {0: *bitrate*, 1: *duration*, 2: *VBR*}

  - SoulseekQt (2015-6-12 and later):
      - {0: *bitrate*, 1: *duration*} (MP3, OGG, WMA, M4A)
      - {1: *duration*, 4: *sample rate*, 5: *bit depth*} (FLAC, WAV, APE)
      - {0: *bitrate*, 1: *duration*, 4: *sample rate*, 5: *bit depth*} (WV)

  - Nicotine+ (lossless formats), slskd (lossless formats):
      - {1: *duration*, 4: *sample rate*, 5: *bit depth*}

# Server Messages

| Send           | Receive             |
|----------------|---------------------|
| Send to Server | Receive from Server |

Server messages are used by clients to interface with the server. In Nicotine+, these messages are defined in slskmessages.py.

If you want a Soulseek server, check out [Soulfind](https://github.com/seeschloss/soulfind).
Soulfind is obviously not exactly the same as the official proprietary Soulseek server,
but it handles the protocol well enough (and can be modified).

### Server Message Format

| Message Length | Code   | Message Contents |
|----------------|--------|------------------|
| uint32         | uint32 | ...              |

### Server Message Codes

| Code | Message                                           | Status     |
|------|---------------------------------------------------|------------|
| 1    | [Login](#server-code-1)                           |            |
| 2    | [Set Listen Port](#server-code-2)                 |            |
| 3    | [Get Peer Address](#server-code-3)                |            |
| 5    | [Watch User](#server-code-5)                      |            |
| 6    | [Unwatch User](#server-code-6)                    |            |
| 7    | [Get User Status](#server-code-7)                 |            |
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
| 32   | [Ping](#server-code-32)                           |            |
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
| 90   | [Distributed Ping Interval](#server-code-90)      | Obsolete   |
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
| 150  | [Join Global Room](#server-code-150)              | Deprecated |
| 151  | [Leave Global Room](#server-code-151)             | Deprecated |
| 152  | [Global Room Message](#server-code-152)           | Deprecated |
| 153  | [Related Searches](#server-code-153)              | Obsolete   |
| 160  | [Excluded Search Phrases](#server-code-160)       |            |
| 1001 | [Can't Connect To Peer](#server-code-1001)        |            |
| 1003 | [Can't Create Room](#server-code-1003)            |            |

## Server Code 1

### Login

We send this to the server right after the connection has been established. Server responds with the greeting message.

### Sending Login Example

*Message:*

| Data      | Message Length | Message Code | Username Length | Username                | Password Length | Password                |
|-----------|----------------|--------------|-----------------|-------------------------|-----------------|-------------------------|
| **Human** | 72             | 1            | 8               | username                | 8               | password                |
| **Hex**   | 48 00 00 00    | 01 00 00 00  | 08 00 00 00     | 75 73 65 72 6e 61 6d 65 | 08 00 00 00     | 70 61 73 73 77 6f 72 64 |

*... continued:*

| Data      | Version     | Hash Length | Hash                                                                                            | Minor Version |
|-----------|-------------|-------------|-------------------------------------------------------------------------------------------------|---------------|
| **Human** | 160         | 32          | d51c9a7e9353746a6020f9602d452929                                                                | 1             |
| **Hex**   | a0 00 00 00 | 20 00 00 00 | 64 35 31 63 39 61 37 65 39 33 35 33 37 34 36 61 36 30 32 30 66 39 36 30 32 64 34 35 32 39 32 39 | 01 00 00 00   |

*Message as a Hex Stream:*

  - **48 00 00 00 01 00 00 00 08 00 00 00 75 73 65 72 6e 61 6d 65 08 00 00 00 70 61 73 73 77 6f 72 64 a0 00 00 00 20 00
      00 00 64 35 31 63 39 61 37 65 39 33 35 33 37 34 36 61 36 30 32 30 66 39 36 30 32 64 34 35 32 39 32 39 01 00 00 00**

### Data Order
  - Send Login Attempt
    1.  **string** <ins>username</ins>
    2.  **string** <ins>password</ins> *A non-empty string is required*
    3.  **uint32** <ins>version number</ins> **160** for Nicotine+
    4.  **string** <ins>hash</ins> *MD5 hex digest of concatenated username & password*
    5.  **uint32** <ins>minor version</ins> **0x13000000** for 157 ns 13e, **0x11000000** for 157 ns 13c
  - Receive Login Success
    1.  **bool** <ins>success</ins> **1**
    2.  **string** <ins>greet</ins> *MOTD string*
    3.  **uint32** <ins>Your IP Address</ins>
    4.  **string** <ins>hash</ins> *MD5 hex digest of the password string*
    5.  **bool** <ins>is supporter</ins>  *If we have donated to Soulseek at some point in the past*
  - Receive Login Failure
    1.  **bool** <ins>failure</ins> **0**
    2.  **string** <ins>reason</ins> *see [Login Failure Reasons](#login-failure-reasons)*

## Server Code 2

### SetWaitPort

We send this to the server to indicate the port number that we listen on (2234 by default).

If this value is set to zero, or the message is not sent upon login (which defaults the listen port to 0), remote clients handling a [ConnectToPeer](#server-code-18) message will fail to properly purge the request.  Confirmed in SoulseekQt 2020.3.12, but probably impacts most or all other versions.

### Data Order
  - Send
    1.  **uint32** <ins>port</ins>
    2.  **uint32** <ins>unknown</ins> *(SoulseekQt uses value 1)*
    3.  **uint32** <ins>obfuscated port</ins>
  - Receive
      - *No Message*

## Server Code 3

### GetPeerAddress

We send this to the server to ask for a peer's address (IP address and port), given the peer's username.

### Data Order

  - Send
    1.  **string** <ins>username</ins>
  - Receive
    1.  **string** <ins>username</ins>
    2.  **ip** <ins>ip</ins>
    3.  **uint32** <ins>port</ins>
    4.  **uint32** <ins>unknown</ins> *(SoulseekQt uses value 1)*
    5.  **uint16** <ins>obfuscated port</ins>

## Server Code 5

### WatchUser

Used to be kept updated about a user's stats. When a user's stats have changed, the server sends a [GetUserStats](#server-code-36) response message with the new user stats.

### Data Order

  - Send
    1.  **string** <ins>username</ins>
  - Receive
    1.  **string** <ins>username</ins>
    2.  **bool** <ins>exists</ins>
    - If <ins>exists</ins> is true
        1.  **uint32** <ins>status</ins> *see [User Status Codes](#user-status-codes)*
        2.  **uint32** <ins>avgspeed</ins>
        3.  **uint64** <ins>uploadnum</ins> *Number of uploaded files. The value changes when sending a [SendUploadSpeed](#server-code-121) server message, and is likely used by the server to calculate the average speed.*
        4.  **uint32** <ins>files</ins>
        5.  **uint32** <ins>dirs</ins>
        - If <ins>status</ins> is away/online
            1.  **string** <ins>countrycode</ins> *Uppercase country code*

## Server Code 6

### UnwatchUser

Used when we no longer want to be kept updated about a user's stats.

### Data Order

  - Send
    1.  **string** <ins>username</ins>
  - Receive
      - *No Message*

## Server Code 7

### GetUserStatus

The server tells us if a user has gone away or has returned.

### Data Order

  - Send
    1.  **string** <ins>username</ins>
  - Receive
    1.  **string** <ins>username</ins>
    2.  **uint32** <ins>status</ins> *see [User Status Codes](#user-status-codes)*
    3.  **bool** <ins>privileged</ins>

## Server Code 13

### SayChatroom

Either we want to say something in the chatroom, or someone else did.

### Data Order

  - Send
    1.  **string** <ins>room</ins>
    2.  **string** <ins>message</ins>
  - Receive
    1.  **string** <ins>room</ins>
    2.  **string** <ins>username</ins>
    3.  **string** <ins>message</ins>

## Server Code 14

### JoinRoom

We send this message to the server when we want to join a room. If the room doesn't exist, it is created.

Server responds with this message when we join a room. Contains users list with data on everyone.

### Data Order

  - Send
    1.  **string** <ins>room</ins>
    2.  **uint32** <ins>private</ins> *If the room doesn't exist, should the new room be private?*
  - Receive
    1.  **string** <ins>room</ins>
    2.  **uint32** <ins>number of users in room</ins> *For private rooms, also contain owner and operators*
    3.  Iterate the <ins>number of users</ins>
        1.  **string** <ins>username</ins>
    4.  **uint32** <ins>number of statuses</ins>
    5.  Iterate the <ins>number of statuses</ins>
        1.  **uint32** <ins>status</ins>
    6.  **uint32** <ins>number of user stats</ins>
    7.  Iterate the <ins>number of user stats</ins>
        1.  **uint32** <ins>avgspeed</ins>
        2.  **uint64** <ins>uploadnum</ins>
        3.  **uint32** <ins>files</ins>
        4.  **uint32** <ins>dirs</ins>
    8.  **uint32** <ins>number of slotsfree</ins>
    9.  Iterate the <ins>number of slotsfree</ins>
        1.  **uint32** <ins>slotsfree</ins>
    10. **uint32** <ins>number of user countries</ins>
    11. Iterate the <ins>number of user countries</ins>
        1.  **string** <ins>countrycode</ins> *Uppercase country code*
    12. **string** <ins>owner</ins> **If private room**
    13. **uint32** <ins>number of operators in room</ins> *If private room*
    14. Iterate the <ins>number of operators</ins>
        1.  **string** <ins>operator</ins>

## Server Code 15

### LeaveRoom

We send this to the server when we want to leave a room.

### Data Order

  - Send
    1.  **string** <ins>room</ins>
  - Receive
    1.  **string** <ins>room</ins>

## Server Code 16

### UserJoinedRoom

The server tells us someone has just joined a room we're in.

### Data Order

  - Send
      - *No Message*
  - Receive
    1.  **string** <ins>room</ins>
    2.  **string** <ins>username</ins>
    3.  **uint32** <ins>status</ins>
    4.  **uint32** <ins>avgspeed</ins>
    5.  **uint64** <ins>uploadnum</ins>
    6.  **uint32** <ins>files</ins>
    7.  **uint32** <ins>dirs</ins>
    8.  **uint32** <ins>slotsfree</ins>
    9.  **string** <ins>countrycode</ins> *Uppercase country code*

## Server Code 17

### UserLeftRoom

The server tells us someone has just left a room we're in.

### Data Order

  - Send
      - *No Message*
  - Receive
    1.  **string** <ins>room</ins>
    2.  **string** <ins>username</ins>

## Server Code 18

### ConnectToPeer

Either we ask server to tell someone else we want to establish a connection with them, or server tells us someone wants to connect with us. Used when the side that wants a connection can't establish it, and tries to go the other way around (direct connection has failed).

See also: [Peer Connection Message Order](#modern-peer-connection-message-order)

### Data Order

  - Send
    1.  **uint32** <ins>token</ins>
    2.  **string** <ins>username</ins>
    3.  **string** <ins>type</ins> **P, F or D** *see [Connection Types](#connection-types)*
  - Receive
    1.  **string** <ins>username</ins>
    2.  **string** <ins>type</ins> **P, F or D** *see [Connection Types](#connection-types)*
    3.  **ip** <ins>ip</ins>
    4.  **uint32** <ins>port</ins>
    5.  **uint32** <ins>token</ins> *Use this token for [PierceFireWall](#peer-init-code-0)*
    6.  **bool** <ins>privileged</ins>
    7.  **uint32** <ins>unknown</ins> *(SoulseekQt uses value 1)*
    8.  **uint32** <ins>obfuscated port</ins>

## Server Code 22

### MessageUser

Chat phrase sent to someone or received by us in private.

### Data Order

  - Send
    1.  **string** <ins>username</ins>
    2.  **string** <ins>message</ins>
  - Receive
    1.  **uint32** <ins>ID</ins>
    2.  **uint32** <ins>timestamp</ins>
    3.  **string** <ins>username</ins>
    4.  **string** <ins>message</ins>
    5.  **bool** <ins>new message</ins> **1** if message is new, **0** if message is re-sent (e.g. if recipient was offline)

## Server Code 23

### MessageAcked

We send this to the server to confirm that we received a private message. If we don't send it, the server will keep sending the chat phrase to us.

### Data Order

  - Send
    1.  **uint32** <ins>message ID</ins>
  - Receive
      - *No Message*

## Server Code 25

### FileSearchRoom

**OBSOLETE, use [RoomSearch](#server-code-120) server message**

We send this to the server when we search for something in a room.

### Data Order

  - Send
    1. **uint32** <ins>token</ins>
    2. **uint32** <ins>room id</ins>
    3. **string** <ins>search query</ins>
  - Receive
      - *No Message*

## Server Code 26

### FileSearch

We send this to the server when we search for something. Alternatively, the server sends this message outside the distributed network to tell us that someone is searching for something, currently used for [UserSearch](#server-code-42) and [RoomSearch](#server-code-120) requests.

The token is a number generated by the client and is used to track the search results.

### Data Order

  - Send
    1.  **uint32** <ins>token</ins>
    2.  **string** <ins>search query</ins>
  - Receive
    1.  **string** <ins>username</ins>
    2.  **uint32** <ins>token</ins>
    3.  **string** <ins>search query</ins>

## Server Code 28

### SetStatus

We send our new status to the server. Status is a way to define whether we're available (online) or busy (away). 

*1 = Away  
2 = Online*

### Data Order

  - Send
    1.  **int32** <ins>status</ins> *see [User Status Codes](#user-status-codes)*
  - Receive
      - *No Message*

## Server Code 32

### ServerPing

We send this to the server at most once per minute to ensure the connection stays alive.

Nicotine+ uses TCP keepalive instead.

### Data Order

  - Send
      - Empty Message
  - Receive
      - *No Message*

## Server Code 33

### SendConnectToken

**OBSOLETE, no longer used**

### Data Order

  - Send
    1.  **string** <ins>username</ins>
    2.  **uint32** <ins>token</ins>
  - Receive
    1.  **string** <ins>username</ins>
    2.  **uint32** <ins>token</ins>

## Server Code 34

### SendDownloadSpeed

**OBSOLETE, use [SendUploadSpeed](#server-code-121) server message**

We used to send this after a finished download to let the server update the speed statistics for a user.

### Data Order

  - Send
    1.  **string** <ins>username</ins>
    2.  **uint32** <ins>speed</ins>
  - Receive
      - *No Message*

## Server Code 35

### SharedFoldersFiles

We send this to server to indicate the number of folder and files that we share.

### Data Order

  - Send
    1.  **uint32** <ins>dirs</ins>
    2.  **uint32** <ins>files</ins>
  - Receive
      - *No Message*

## Server Code 36

### GetUserStats

The server sends this to indicate a change in a user's statistics, if we've requested to watch the user in [WatchUser](#server-code-5) previously. A user's stats can also be requested by sending a [GetUserStats](#server-code-36) message to the server, but [WatchUser](#server-code-5) should be used instead.

### Data Order

  - Send
    1.  **string** <ins>username</ins>
  - Receive
    1.  **string** <ins>username</ins>
    2.  **uint32** <ins>avgspeed</ins>
    3.  **uint64** <ins>uploadnum</ins>
    4.  **uint32** <ins>files</ins>
    5.  **uint32** <ins>dirs</ins>

## Server Code 40

### QueuedDownloads

**OBSOLETE, no longer sent by the server**

The server sends this to indicate if someone has download slots available or not.

### Data Order

  - Send
      - *No Message*
  - Receive
    1.  **string** <ins>username</ins>
    2.  **bool** <ins>slotsfree</ins> *Can immediately download*

## Server Code 41

### Relogged

The server sends this if someone else logged in under our nickname, and then disconnects us.

### Data Order

  - Send
      - *No Message*
  - Receive
      - Empty Message

## Server Code 42

### UserSearch

We send this to the server when we search a specific user's shares. The token is a number generated by the client and is used to track the search results.

### Data Order

  - Send
    1.  **string** <ins>username</ins>
    2.  **uint32** <ins>token</ins>
    3.  **string** <ins>search query</ins>
  - Receive
      - *No Message*

## Server Code 51

### AddThingILike

**DEPRECATED, used in Soulseek NS but not SoulseekQt**

We send this to the server when we add an item to our likes list.

### Data Order

  - Send
    1.  **string** <ins>item</ins>
  - Receive
      - *No Message*

## Server Code 52

### RemoveThingILike

**DEPRECATED, used in Soulseek NS but not SoulseekQt**

We send this to the server when we remove an item from our likes list.

### Data Order

  - Send
    1.  **string** <ins>item</ins>
  - Receive
      - *No Message*

## Server Code 54

### Recommendations

**DEPRECATED, used in Soulseek NS but not SoulseekQt**

The server sends us a list of personal recommendations and a number for each.

### Data Order

  - Send
      - Empty Message
  - Receive
    1.  **uint32** <ins>number of total recommendations</ins>
    2.  Iterate for <ins>number of total recommendations</ins>
        1.  **string** <ins>recommendation</ins>
        2.  **int32** <ins>number of recommendations this recommendation has</ins>
    3.  **uint32** <ins>number of total unrecommendations</ins>
    4.  Iterate for <ins>number of total unrecommendations</ins>
        1.  **string** <ins>unrecommendation</ins>
        2.  **int32** <ins>number of unrecommendations this unrecommendation has</ins> *(negative)*

## Server Code 56

### GlobalRecommendations

**DEPRECATED, used in Soulseek NS but not SoulseekQt**

The server sends us a list of global recommendations and a number for each.

### Data Order

  - Send
      - Empty Message
  - Receive
    1.  **uint32** <ins>number of total recommendations</ins>
    2.  Iterate for <ins>number of total recommendations</ins>
        1.  **string** <ins>recommendation</ins>
        2.  **int32** <ins>number of recommendations this recommendation has</ins>
    3.  **uint32** <ins>number of total unrecommendations</ins>
    4.  Iterate for <ins>number of total unrecommendations</ins>
        1.  **string** <ins>unrecommendation</ins>
        2.  **int32** <ins>number of unrecommendations this unrecommendation has</ins> *(negative)*

## Server Code 57

### UserInterests

**DEPRECATED, used in Soulseek NS but not SoulseekQt**

We ask the server for a user's liked and hated interests. The server responds with a list of interests.

### Data Order

  - Send
    1.  **string** <ins>username</ins>
  - Receive
    1.  **string** <ins>username</ins>
    2.  **uint32** <ins>number of liked interests</ins>
    3.  Iterate for <ins>number of liked interests</ins>
        1.  **string** <ins>interest</ins>
    4.  **uint32** <ins>number of hated interests</ins>
    5.  Iterate for <ins>number of hated interests</ins>
        1.  **string** <ins>interest</ins>

## Server Code 58

### AdminCommand

**OBSOLETE**

We send this to the server to run an admin command (e.g. to ban or silence a user) if we have admin status on the server.

### Data Order

  - Send
    1.  **string** <ins>command</ins>
    2.  **uint32** <ins>number of command arguments</ins>
    3.  Iterate for <ins>number of command arguments</ins>
        1.  **string** <ins>command argument</ins>
  - Receive
      - *No Message*

## Server Code 60

### PlaceInLineResponse

**OBSOLETE, use [PlaceInQueueResponse](#peer-code-44) peer message**

The server sends this to indicate change in place in queue while we're waiting for files from another peer.

### Data Order

  - Send
    1.  **string** <ins>username</ins>
    2.  **uint32** <ins>req</ins>
    3.  **uint32** <ins>place</ins>
  - Receive
    1.  **string** <ins>username</ins>
    2.  **uint32** <ins>req</ins>
    3.  **uint32** <ins>place</ins>

## Server Code 62

### RoomAdded

**OBSOLETE, no longer sent by the server**

The server tells us a new room has been added.

### Data Order

  - Send
      - *No Message*
  - Receive
    1.  **string** <ins>room</ins>

## Server Code 63

### RoomRemoved

**OBSOLETE, no longer sent by the server**

The server tells us a room has been removed.

### Data Order

  - Send
      - *No Message*
  - Receive
    1.  **string** <ins>room</ins>

## Server Code 64

### RoomList

The server tells us a list of rooms and the number of users in them. When connecting to the server, the server only sends us rooms with at least 5 users. A few select rooms are also excluded, such as nicotine and The Lobby. Requesting the room list yields a response containing the missing rooms.

### Data Order

  - Send
      - Empty Message
  - Receive
    1.  **uint32** <ins>number of rooms</ins>
    2.  Iterate for <ins>number of rooms</ins>
        1.  **string** <ins>room</ins>
    3.  **uint32** <ins>number of rooms</ins>
    4.  Iterate for <ins>number of rooms</ins>
        1.  **uint32** <ins>number of users in room</ins>

<!-- end list -->

1.  **uint32** <ins>number of owned private rooms</ins>
2.  Iterate for <ins>number of owned private rooms</ins>
    1.  **string** <ins>owned private room</ins>
3.  **uint32** <ins>number of owned private rooms</ins>
4.  Iterate for <ins>number of owned private rooms</ins>
    1.  **uint32** <ins>number of users in owned private room</ins>

<!-- end list -->

1.  **uint32** <ins>number of private rooms (except owned)</ins>
2.  Iterate for <ins>number of private rooms (except owned)</ins>
    1.  **string** <ins>private room</ins>
3.  **uint32** <ins>number of private rooms (except owned)</ins>
4.  Iterate for <ins>number of private rooms (except owned)</ins>
    1.  **uint32** <ins>number of users in private rooms (except owned)</ins>

<!-- end list -->

1.  **uint32** <ins>number of operated private rooms</ins>
2.  Iterate for <ins>number of operated private rooms</ins>
    1.  **string** <ins>operated private room</ins>

## Server Code 65

### ExactFileSearch

**OBSOLETE, no results even with official client**

We send this to search for an exact file name and folder, to find other sources.

### Data Order

  - Send
    1.  **uint32** <ins>token</ins>
    2.  **string** <ins>filename</ins>
    3.  **string** <ins>path</ins>
    4.  **uint64** <ins>filesize</ins>
    5.  **uint32** <ins>checksum</ins>
    6.  **uint8** <ins>unknown</ins>
  - Receive
    1.  **string** <ins>username</ins>
    2.  **uint32** <ins>token</ins>
    3.  **string** <ins>filename</ins>
    4.  **string** <ins>path</ins>
    5.  **uint64** <ins>filesize</ins>
    6.  **uint32** <ins>checksum</ins>

## Server Code 66

### AdminMessage

A global message from the server admin has arrived.

### Data Order

  - Send
      - *No Message*
  - Receive
    1.  **string** <ins>message</ins>

## Server Code 67

### GlobalUserList

**OBSOLETE, no longer used**

We send this to get a global list of all users online.

### Data Order

  - Send
      - Empty Message
  - Receive
    1.  **uint32** <ins>number of users in room</ins>
    2.  Iterate the <ins>number of users</ins>
        1.  **string** <ins>username</ins>
    3.  **uint32** <ins>number of userdata</ins>
    4.  Iterate the <ins>number of users</ins>
        1.  **uint32** <ins>status</ins>
    5.  **uint32** <ins>number of userdata</ins>
    6.  Iterate the <ins>userdata</ins>
        1.  **uint32** <ins>avgspeed</ins>
        2.  **uint64** <ins>uploadnum</ins>
        3.  **uint32** <ins>files</ins>
        4.  **uint32** <ins>dirs</ins>
    7.  **uint32** <ins>number of slotsfree</ins>
    8.  Iterate through number of slotsfree
        1.  **uint32** <ins>slotsfree</ins>
    9. **uint32** <ins>number of usercountries</ins>
    10. Iterate through number of usercountries
        1.  **string** <ins>countrycode</ins> *Uppercase country code*

## Server Code 68

### TunneledMessage

**OBSOLETE, no longer used**

Server message for tunneling a chat message.

### Data Order

  - Send
    1.  **string** <ins>username</ins>
    2.  **uint32** <ins>token</ins>
    3.  **uint32** <ins>code</ins>
    4.  **string** <ins>message</ins>
  - Receive
    1.  **string** <ins>username</ins>
    2.  **uint32** <ins>code</ins>
    3.  **uint32** <ins>token</ins>
    4.  **ip** <ins>ip</ins>
    5.  **uint32** <ins>port</ins>
    6.  **string** <ins>message</ins>

## Server Code 69

### PrivilegedUsers

The server sends us a list of privileged users, a.k.a. users who have donated.

### Data Order

  - Send
      - *No Message*
  - Receive
    1.  **uint32** <ins>number of users</ins>
    2.  Iterate <ins>number of users</ins>
        1.  **string** <ins>username</ins>

## Server Code 71

### HaveNoParent

We inform the server if we have a distributed parent or not. If not, the server eventually sends us a [PossibleParents](#server-code-102) message with a list of possible parents to connect to. If no candidates are found, no such message is sent by the server, and we eventually become a branch root.

### Data Order

  - Send
    1.  **bool** <ins>have parents</ins>
  - Receive
      - *No Message*

## Server Code 73

### SearchParent

**DEPRECATED, sent by Soulseek NS but not SoulseekQt**

We send the IP address of our parent to the server.

### Data Order

  - Send
    1.  **ip** <ins>ip</ins>
  - Receive
      - *No Message*

## Server Code 83

### ParentMinSpeed

The server informs us about the minimum upload speed required to become a parent in the distributed network.

### Data Order

  - Send
      - *No Message*
  - Receive
    1.  **uint32** <ins>speed</ins>

## Server Code 84

### ParentSpeedRatio

The server sends us a speed ratio determining the number of children we can have in the distributed network. The maximum number of children is our upload speed divided by the speed ratio.

### Data Order

  - Send
      - *No Message*
  - Receive
    1.  **uint32** <ins>ratio</ins>

## Server Code 86

### ParentInactivityTimeout

**OBSOLETE, no longer sent by the server**

### Data Order

  - Send
      - *No Message*
  - Receive
    1.  **uint32** <ins>seconds</ins>

## Server Code 87

### SearchInactivityTimeout

**OBSOLETE, no longer sent by the server**

### Data Order

  - Send
      - *No Message*
  - Receive
    1.  **uint32** <ins>seconds</ins>

## Server Code 88

### MinParentsInCache

**OBSOLETE, no longer sent by the server**

### Data Order

  - Send
      - *No Message*
  - Receive
    1.  **uint32** <ins>number</ins>

## Server Code 90

### DistribPingInterval

**OBSOLETE, no longer sent by the server**

### Data Order

  - Send
      - *No Message*
  - Receive
    1.  **uint32** <ins>seconds</ins>

## Server Code 91

### AddToPrivileged

**OBSOLETE, no longer sent by the server**

The server sends us the username of a new privileged user, which we add to our list of global privileged users.

### Data Order

  - Send
      - *No Message*
  - Receive
    1.  **string** <ins>username</ins>

## Server Code 92

### CheckPrivileges

We ask the server how much time we have left of our privileges. The server responds with the remaining time, in seconds.

### Data Order

  - Send
      - Empty Message
  - Receive
    1.  **uint32** <ins>time left</ins>

## Server Code 93

### EmbeddedMessage

The server sends us an embedded distributed message. The only type of distributed message sent at present is [DistribSearch](#distributed-code-3) (distributed code 3). If we receive such a message, we are a branch root in the distributed network, and we distribute the embedded message (not the unpacked distributed message) to our child peers.

### Data Order

  - Send
      - *No Message*
  - Receive
    1.  **uint8** <ins>distributed code</ins> *see [Distributed Message Codes](#distributed-message-codes)*
    2.  **bytes** <ins>distributed message</ins> *Raw message associated with distributed code*

## Server Code 100

### AcceptChildren

We tell the server if we want to accept child nodes.

### Data Order

  - Send
    1.  **bool** <ins>accept</ins>
  - Receive
      - *No Message*

## Server Code 102

### PossibleParents

The server send us a list of max 10 possible distributed parents to connect to. Messages of this type are sent to us at regular intervals, until we tell the server we don't need more possible parents with a [HaveNoParent](#server-code-71) message.

The received list always contains users whose upload speed is higher than our own. If we have the highest upload speed on the server, we become a branch root, and start receiving [SearchRequest](#server-code-93) messages directly from the server.

### Data Order

  - Send
      - *No Message*
  - Receive
    1.  **uint32** <ins>number of parents</ins>
    2.  Iterate for <ins>number of parents</ins>
        1.  **string** <ins>username</ins>
        2.  **ip** <ins>ip</ins>
        3.  **uint32** <ins>port</ins>

## Server Code 103

### WishlistSearch

We send the server one of our wishlist search queries at each interval.

### Data Order

  - Send
    1.  **uint32** <ins>token</ins>
    2.  **string** <ins>search query</ins>
  - Receive
      - *No Message*

## Server Code 104

### WishlistInterval

The server tells us the wishlist search interval.

This interval is almost always 12 minutes, or 2 minutes for privileged users.

### Data Order

  - Send
      - *No Message*
  - Receive
    1.  **uint32** <ins>interval</ins>

## Server Code 110

### SimilarUsers

**DEPRECATED, used in Soulseek NS but not SoulseekQt**

The server sends us a list of similar users related to our interests.

### Data Order

  - Send
      - Empty Message
  - Receive
    1.  **uint32** <ins>number of users</ins>
    2.  Iterate for <ins>number of user</ins>
        1.  **string** <ins>username</ins>
        2.  **uint32** <ins>rating</ins>

## Server Code 111

### ItemRecommendations

**DEPRECATED, used in Soulseek NS but not SoulseekQt**

The server sends us a list of recommendations related to a specific item, which is usually present in the like/dislike list or an existing recommendation list.

### Data Order

  - Send
    1.  **string** <ins>item</ins>
  - Receive
    1.  **string** <ins>item</ins>
    2.  **uint32** <ins>number of recommendations</ins>
    3.  Iterate for <ins>number of recommendations</ins>
        1.  **string** <ins>recommendation</ins>
        2.  **uint32** <ins>number of recommendations for this recommendation</ins> *(can be negative)*

## Server Code 112

### ItemSimilarUsers

**DEPRECATED, used in Soulseek NS but not SoulseekQt**

The server sends us a list of similar users related to a specific item, which is usually present in the like/dislike list or recommendation list.

### Data Order

  - Send
    1.  **string** <ins>item</ins>
  - Receive
    1.  **string** <ins>item</ins>
    2.  **uint32** <ins>number of users</ins>
    3.  Iterate for <ins>number of users</ins>
        1.  **string** <ins>username</ins>

## Server Code 113

### RoomTickerState

The server returns a list of tickers in a chat room.

Tickers are customizable, user-specific messages that appear on chat room walls.

### Data Order

  - Send
      - *No Message*
  - Receive
    1.  **string** <ins>room</ins>
    2.  **uint32** <ins>number of users</ins>
    3.  Iterate for <ins>number of user</ins>
        1.  **string** <ins>username</ins>
        2.  **string** <ins>tickers</ins>

## Server Code 114

### RoomTickerAdd

The server sends us a new ticker that was added to a chat room.

Tickers are customizable, user-specific messages that appear on chat room walls.

### Data Order

  - Send
      - *No Message*
  - Receive
    1.  **string** <ins>room</ins>
    2.  **string** <ins>username</ins>
    3.  **string** <ins>ticker</ins>

## Server Code 115

### RoomTickerRemove

The server informs us that a ticker was removed from a chat room.

Tickers are customizable, user-specific messages that appear on chat room walls.

### Data Order

  - Send
      - *No Message*
  - Receive
    1.  **string** <ins>room</ins>
    2.  **string** <ins>username</ins>

## Server Code 116

### RoomTickerSet

We send this to the server when we change our own ticker in a chat room. Sending an empty ticker string removes any existing ticker in the room.

Tickers are customizable, user-specific messages that appear on chat room walls.

### Data Order

  - Send
    1.  **string** <ins>room</ins>
    2.  **string** <ins>ticker</ins>
  - Receive
      - *No Message*

## Server Code 117

### AddThingIHate

**DEPRECATED, used in Soulseek NS but not SoulseekQt**

We send this to the server when we add an item to our hate list.

### Data Order

  - Send
    1.  **string** <ins>item</ins>
  - Receive
      - *No Message*

## Server Code 118

### RemoveThingIHate

**DEPRECATED, used in Soulseek NS but not SoulseekQt**

We send this to the server when we remove an item from our hate list.

### Data Order

  - Send
    1.  **string** <ins>item</ins>
  - Receive
      - *No Message*

## Server Code 120

### RoomSearch

We send this to the server to search files shared by users who have joined a specific chat room.

The token is a number generated by the client and is used to track the search results.

### Data Order

  - Send
    1.  **string** <ins>room</ins>
    2.  **uint32** <ins>token</ins>
    3.  **string** <ins>search query</ins>
  - Receive
      - *No Message*

## Server Code 121

### SendUploadSpeed

We send this after a finished upload to let the server update the speed statistics for ourselves.

### Data Order

  - Send
    1.  **uint32** <ins>speed</ins>
  - Receive
      - *No Message*

## Server Code 122

### UserPrivileged

**DEPRECATED, use [WatchUser](#server-code-5) and [GetUserStatus](#server-code-7) server messages**

We ask the server whether a user is privileged or not.

### Data Order

  - Send
    1.  **string** <ins>username</ins>
  - Receive
    1.  **string** <ins>username</ins>
    2.  **bool** <ins>privileged</ins>

## Server Code 123

### GivePrivileges

We give (part of) our privileges, specified in days, to another user on the network.

### Data Order

  - Send
    1.  **string** <ins>username</ins>
    2.  **uint32** <ins>days</ins>
  - Receive
      - *No Message*

## Server Code 124

### NotifyPrivileges

**DEPRECATED, sent by Soulseek NS but not SoulseekQt**

### Data Order

  - Send
    1.  **uint32** <ins>token</ins>
    2.  **string** <ins>username</ins>
  - Receive
    1.  **uint32** <ins>token</ins>
    2.  **string** <ins>username</ins>

## Server Code 125

### AckNotifyPrivileges

**DEPRECATED, no longer used**

### Data Order

  - Send
    1.  **uint32** <ins>token</ins>
  - Receive
    1.  **uint32** <ins>token</ins>

## Server Code 126

### BranchLevel

We tell the server what our position is in our branch (xth generation) on the distributed network.

### Data Order

  - Send
    1.  **uint32** <ins>branch level</ins>
  - Receive
      - *No Message*

## Server Code 127

### BranchRoot

We tell the server the username of the root of the branch we're in on the distributed network.

### Data Order

  - Send
    1.  **string** <ins>branch root</ins>
  - Receive
      - *No Message*

## Server Code 129

### ChildDepth

**DEPRECATED, sent by Soulseek NS but not SoulseekQt**

We tell the server the maximum number of generation of children we have on the distributed network.

### Data Order

  - Send
    1.  **uint32** <ins>child depth</ins>
  - Receive
      - *No Message*

## Server Code 130

### ResetDistributed

The server asks us to reset our distributed parent and children.

### Data Order

  - Send
      - *No Message*
  - Receive
      - Empty Message

## Server Code 133

### PrivateRoomUsers

The server sends us a list of room users that we can alter (add operator abilities / dismember).

### Data Order

  - Send
    1.  *No Message*
  - Receive
    1.  **string** <ins>room</ins>
    2.  **uint32** <ins>number of users</ins>
    3.  Iterate for <ins>number of users</ins>
        1.  **string** <ins>users</ins>

## Server Code 134

### PrivateRoomAddUser

We send this to inform the server that we've added a user to a private room.

### Data Order

  - Send
    1.  **string** <ins>room</ins>
    2.  **string** <ins>username</ins>
  - Receive
    1.  **string** <ins>room</ins>
    2.  **string** <ins>username</ins>

## Server Code 135

### PrivateRoomRemoveUser

We send this to inform the server that we've removed a user from a private room.

### Data Order

  - Send
    1.  **string** <ins>room</ins>
    2.  **string** <ins>username</ins>
  - Receive
    1.  **string** <ins>room</ins>
    2.  **string** <ins>username</ins>

## Server Code 136

### PrivateRoomDismember

We send this to the server to remove our own membership of a private room.

### Data Order

  - Send
    1.  **string** <ins>room</ins>
  - Receive
      - *No Message*

## Server Code 137

### PrivateRoomDisown

We send this to the server to stop owning a private room.

### Data Order

  - Send
    1.  **string** <ins>room</ins>
  - Receive
      - *No Message*

## Server Code 138

### PrivateRoomSomething

**OBSOLETE, no longer used**

Unknown purpose

### Data Order

  - Send
    1.  **string** <ins>room</ins>
  - Receive
    1.  **string** <ins>room</ins>

## Server Code 139

### PrivateRoomAdded

The server sends us this message when we are added to a private room.

### Data Order

  - Send
      - *No Message*
  - Receive
    1.  **string** <ins>room</ins>

## Server Code 140

### PrivateRoomRemoved

The server sends us this message when we are removed from a private room.

### Data Order

  - Send
      - *No Message*
  - Receive
    1.  **string** <ins>room</ins>

## Server Code 141

### PrivateRoomToggle

We send this when we want to enable or disable invitations to private rooms.

### Data Order

  - Send
    1.  **bool** <ins>enable</ins>
  - Receive
    1.  **bool** <ins>enable</ins>

## Server Code 142

### ChangePassword

We send this to the server to change our password. We receive a response if our password changes.

### Data Order

  - Send
    1.  **string** <ins>pass</ins>
  - Receive
    1.  **string** <ins>pass</ins>

## Server Code 143

### PrivateRoomAddOperator

We send this to the server to add private room operator abilities to a user.

### Data Order

  - Send
    1.  **string** <ins>room</ins>
    2.  **string** <ins>username</ins>
  - Receive
    1.  **string** <ins>room</ins>
    2.  **string** <ins>username</ins>

## Server Code 144

### PrivateRoomRemoveOperator

We send this to the server to remove private room operator abilities from a user.

### Data Order

  - Send
    1.  **string** <ins>room</ins>
    2.  **string** <ins>username</ins>
  - Receive
    1.  **string** <ins>room</ins>
    2.  **string** <ins>username</ins>

## Server Code 145

### PrivateRoomOperatorAdded

The server send us this message when we're given operator abilities in a private room.

### Data Order

  - Send
      - *No Message*
  - Receive
    1.  **string** <ins>room</ins>

## Server Code 146

### PrivateRoomOperatorRemoved

The server send us this message when our operator abilities are removed in a private room.

### Data Order

  - Send
      - *No Message*
  - Receive
    1.  **string** <ins>room</ins>

## Server Code 148

### PrivateRoomOwned

The server sends us a list of operators in a specific room, that we can remove operator abilities from.

### Data Order

  - Send
      - *No Message*
  - Receive
    1.  **string** <ins>room</ins>
    2.  **uint32** <ins>number of operators in room</ins>
    3.  Iterate the <ins>number of operators</ins>
        1.  **string** <ins>operator</ins>

## Server Code 149

### MessageUsers

Sends a broadcast private message to the given list of online users.

### Data Order

  - Send
    1.  **uint32** <ins>number of users</ins>
    2.  Iterate the <ins>number of users</ins>
        1.  **string** <ins>username</ins>
    3.  **string** <ins>message</ins>
  - Receive
      - *No Message*

## Server Code 150

### JoinGlobalRoom

**DEPRECATED, used in Soulseek NS but not SoulseekQt**

We ask the server to send us messages from all public rooms, also known as public room feed.

### Data Order

  - Send
      - Empty Message
  - Receive
      - *No Message*

## Server Code 151

### LeaveGlobalRoom

**DEPRECATED, used in Soulseek NS but not SoulseekQt**

We ask the server to stop sending us messages from all public rooms, also known as public room feed.

### Data Order

  - Send
      - Empty Message
  - Receive
      - *No Message*

## Server Code 152

### GlobalRoomMessage

**DEPRECATED, used in Soulseek NS but not SoulseekQt**

The server sends this when a new message has been written in the public room feed (every single line written in every public room).

### Data Order

  - Send
      - *No Message*
  - Receive
    1.  **string** <ins>room</ins>
    2.  **string** <ins>username</ins>
    3.  **string** <ins>message</ins>

## Server Code 153

### RelatedSearch

**OBSOLETE, server sends empty list as of 2018**

The server returns a list of related search terms for a search query.

### Data Order

  - Send
    1.  **string** <ins>query</ins>
  - Receive
    1.  **string** <ins>query</ins>
    2.  **uint32** <ins>number of terms</ins>
    3.  Iterate for <ins>number of term</ins>
        1.  **string** <ins>term</ins>
        2.  **uint32** <ins>score</ins>

## Server Code 160

### ExcludedSearchPhrases

The server sends a list of phrases not allowed on the search network. File paths containing such phrases should be excluded when responding to search requests.

### Data Order

  - Send
      - *No Message*
  - Receive
    1.  **uint32** <ins>number of phrases</ins>
    2.  Iterate for <ins>number of phrases</ins>
        1.  **string** <ins>phrase</ins>

## Server Code 1001

### CantConnectToPeer

We send this to say we can't connect to peer after it has asked us to connect. We receive this if we asked peer to connect and it can't do this. This message means a connection can't be established either way.

See also: [Peer Connection Message Order](#modern-peer-connection-message-order)

### Data Order

  - Send
    1.  **uint32** <ins>token</ins>
    2.  **string** <ins>username</ins>
  - Receive
    1.  **uint32** <ins>token</ins>
    2.  **string** <ins>username</ins>

## Server Code 1003

### CantCreateRoom

Server tells us a new room cannot be created.

This message only seems to be sent if you try to create a room with the same name as an existing private room. In other cases, such as using a room name with leading or trailing spaces, only a private message containing an error message is sent.

### Data Order

  - Send
      - *No Message*
  - Receive
    1.  **string** <ins>room</ins>

# Peer Init Messages

| Send         | Receive           |
|--------------|-------------------|
| Send to Peer | Receive from Peer |

Peer init messages are used to initiate a 'P', 'F' or 'D' connection to a peer. In Nicotine+, these messages are defined in slskmessages.py.

### Peer Init Message Format

| Message Length | Code  | Message Contents |
|----------------|-------|------------------|
| uint32         | uint8 | ...              |

### Peer Init Message Codes

| Code | Message                              |
|------|--------------------------------------|
| 0    | [Pierce Firewall](#peer-init-code-0) |
| 1    | [Peer Init](#peer-init-code-1)       |

### Modern Peer Connection Message Order

*Used by SoulseekQt, Nicotine+ 3.2.1 and later, Soulseek.NET-based clients (slskd, Seeker)*

1.  User A sends [ConnectToPeer](#server-code-18) to the Server with a unique token (indirect connection request)
2.  User A sends a [PeerInit](#peer-init-code-1) to User B (direct connection request)
3.  The Server sends a [ConnectToPeer](#server-code-18) response to User B with the same token.  
If User B receives the *PeerInit* message, a connection is established, and user A is free to send peer messages.  
Otherwise, once User B receives the *ConnectToPeer* message from the Server, User B proceeds with step 4.
4.  User B sends a [PierceFireWall](#peer-init-code-0) to User A with the token included in the *ConnectToPeer* message.  
If this succeeds, a connection is established, and User A is free to send peer messages.  
If this fails, User B retries for ~1 minute. If this still fails, no connection is possible, and User B proceeds with step 5.
5.  User B sends a [CantConnectToPeer](#server-code-1001) to the Server.
6.  The Server sends a [CantConnectToPeer](#server-code-1001) response to User A.

Unlike SoulseekQt, Nicotine+ and Soulseek.NET-based clients skip step 5 in favor of letting the connection attempt time out on User A's end.

### Legacy Peer Connection Message Order

*Used by Soulseek NS, Nicotine+ 3.2.0 and earlier, Museek+, soulseeX*

1.  User A sends a [PeerInit](#peer-init-code-1) to User B.  
If this succeeds, a connection is established, and User A is free to send peer messages.  
If this fails (socket cannot connect), User A proceeds with an indirect connection request (step 2).
2.  User A sends [ConnectToPeer](#server-code-18) to the Server with a unique token
3.  The Server sends a [ConnectToPeer](#server-code-18) response to User B with the same token
4.  User B sends a [PierceFireWall](#peer-init-code-0) to User A with the same token.  
If this succeeds, a connection is established, and User A is free to send peer messages.  
If this fails, User B retries for ~1 minute. If this still fails, no connection is possible, and User B proceeds with step 5.
5.  User B sends a [CantConnectToPeer](#server-code-1001) to the Server.
6.  The Server sends a [CantConnectToPeer](#server-code-1001) response to User A.

## Peer Init Code 0

### PierceFireWall

This message is sent in response to an indirect connection request from another user. If the message goes through to the user, the connection is ready. The token is taken from the [ConnectToPeer](#server-code-18) server message.

See also: [Peer Connection Message Order](#modern-peer-connection-message-order)

### Data Order

  - Send
      - **uint32** <ins>token</ins>
  - Receive
      - **uint32** <ins>token</ins>

## Peer Init Code 1

### PeerInit

This message is sent to initiate a direct connection to another peer. The token is apparently always 0 and ignored.

See also: [Peer Connection Message Order](#modern-peer-connection-message-order)

### Data Order

  - Send
      - **string** <ins>username</ins> *local username*
      - **string** <ins>type</ins> **P, F or D** *see [Connection Types](#connection-types)*
      - **uint32** <ins>token</ins> *value is always* **0**
  - Receive
      - **string** <ins>username</ins> *remote username*
      - **string** <ins>type</ins> **P, F or D** *see [Connection Types](#connection-types)*
      - **uint32** <ins>token</ins> *value is always* **0**

# Peer Messages

| Send         | Receive           |
|--------------|-------------------|
| Send to Peer | Receive from Peer |

Peer messages are sent to peers over a 'P' connection. Only a single active connection to a peer is allowed. In Nicotine+, these messages are defined in slskmessages.py.

### Peer Message Format

| Message Length | Code   | Message Contents |
|----------------|--------|------------------|
| uint32         | uint32 | ...              |

### Peer Message Codes

| Code | Message                                    | Status                     |
|------|--------------------------------------------|----------------------------|
| 1    | Private Message                            | Obsolete, contents unknown |
| 4    | [Shared File List Request](#peer-code-4)   |                            |
| 5    | [Shared File List Response](#peer-code-5)  |                            |
| 8    | [File Search Request](#peer-code-8)        | Obsolete                   |
| 9    | [File Search Response](#peer-code-9)       |                            |
| 10   | Room Invitation                            | Obsolete, contents unknown |
| 14   | Cancelled Queued Transfer                  | Obsolete, contents unknown |
| 15   | [User Info Request](#peer-code-15)         |                            |
| 16   | [User Info Response](#peer-code-16)        |                            |
| 33   | Send Connect Token                         | Obsolete, contents unknown |
| 34   | Move Download To Top                       | Obsolete, contents unknown |
| 36   | [Folder Contents Request](#peer-code-36)   |                            |
| 37   | [Folder Contents Response](#peer-code-37)  |                            |
| 40   | [Transfer Request](#peer-code-40)          |                            |
| 41   | [Download Response](#peer-code-41-a)       | Deprecated                 |
| 41   | [Upload Response](#peer-code-41-b)         |                            |
| 42   | [Upload Placehold](#peer-code-42)          | Obsolete                   |
| 43   | [Queue Upload](#peer-code-43)              |                            |
| 44   | [Place In Queue Response](#peer-code-44)   |                            |
| 46   | [Upload Failed](#peer-code-46)             |                            |
| 47   | Exact File Search Request                  | Obsolete, contents unknown |
| 48   | Queued Downloads                           | Obsolete, contents unknown |
| 49   | Indirect File Search Request               | Obsolete, contents unknown |
| 50   | [Upload Denied](#peer-code-50)             |                            |
| 51   | [Place In Queue Request](#peer-code-51)    |                            |
| 52   | [Upload Queue Notification](#peer-code-52) | Deprecated                 |

## Peer Code 4

### GetShareFileList

We send this to a peer to ask for a list of shared files.

### Data Order

  - Send
      - Empty Message
  - Receive
      - Empty Message

## Peer Code 5

### SharedFileListResponse

A peer responds with a list of shared files after we've sent a [SharedFileListRequest](#peer-code-4).

### Data Order

  - Send
    1.  Iterate through shares database
        1.  **data**
    2. zlib compress
  - Receive
    1.  zlib decompress
    2.  **uint32** <ins>number of directories</ins>
    3.  Iterate <ins>number of directories</ins>
        1.  **string** <ins>directory</ins>
        2.  **uint32** <ins>number of files</ins>
        3.  Iterate <ins>number of files</ins>
            1.  **uint8** <ins>code</ins> *value is always* **1**
            2.  **string** <ins>filename</ins>
            3.  **unit64** <ins>file size</ins>
            4.  **string** <ins>file extension</ins>
            5.  **uint32** <ins>number of attributes</ins>
            6.  Iterate for <ins>number of attributes</ins>
                1.  **uint32** <ins>attribute code</ins> *see [File Attribute Types](#file-attribute-types)*
                2.  **uint32** <ins>attribute value</ins>
    4.  **uint32** <ins>unknown</ins> *official clients always send a value of* **0**
    5.  **uint32** <ins>number of private directories</ins>
    6.  Iterate <ins>number of private directories</ins>
        1.  **string** <ins>directory</ins>
        2.  **uint32** <ins>number of files</ins>
        3.  Iterate <ins>number of files</ins>
            1.  **uint8** <ins>code</ins> *value is always* **1**
            2.  **string** <ins>filename</ins>
            3.  **uint64** <ins>file size</ins>
            4.  **string** <ins>file extension</ins>
            5.  **uint32** <ins>number of attributes</ins>
            6.  Iterate for <ins>number of attributes</ins>
                1.  **uint32** <ins>attribute code</ins> *see [File Attribute Types](#file-attribute-types)*
                2.  **uint32** <ins>attribute value</ins>

## Peer Code 8

### FileSearchRequest

**OBSOLETE, use [UserSearch](#server-code-42) server message**

We send this to the peer when we search for a file. Alternatively, the peer sends this to tell us it is searching for a file.

### Data Order

  - Send
    1.  **uint32** <ins>token</ins>
    2.  **string** <ins>query</ins>
  - Receive
    1.  **uint32** <ins>token</ins>
    2.  **string** <ins>query</ins>

## Peer Code 9

### FileSearchResponse

A peer sends this message when it has a file search match. The token is taken from original [FileSearch](#server-code-26), [UserSearch](#server-code-42) or [RoomSearch](#server-code-120) server message.

### Data Order

  - Send
    1.  **string** <ins>username</ins>
    2.  **uint32** <ins>token</ins>
    3.  **uint32** <ins>number of results</ins>
    4.  Iterate for <ins>number of results</ins>
        1.  **uint8** <ins>code</ins> *value is always* **1**
        2.  **string** <ins>filename</ins>
        3.  **uint64** <ins>file size</ins>
        4.  **string** <ins>file extension</ins> *(SoulseekNS requires "mp3" to show attributes)*
        5.  **uint32** <ins>number of attributes</ins>
        6.  Iterate for <ins>number of attributes</ins>
            1.  **uint32** <ins>attribute code</ins> *see [File Attribute Types](#file-attribute-types)*
            2.  **uint32** <ins>attribute value</ins>
    5.  **bool** <ins>slotfree</ins>
    6.  **uint32** <ins>avgspeed</ins>
    7.  **uint32** <ins>queue length</ins>
    8.  **uint32** <ins>unknown</ins> *official clients always send a value of* **0**
    9.  **uint32** <ins>number of privately shared results</ins>
    10. Iterate for <ins>number of privately shared results</ins>
        1.  **uint8** <ins>code</ins> *value is always 1*
        2.  **string** <ins>filename</ins>
        3.  **uint64** <ins>file size</ins>
        4.  **string** <ins>file extension</ins> *(SoulseekNS requires "mp3" to show attributes)*
        5.  **uint32** <ins>number of attributes</ins>
        6.  Iterate for <ins>number of attributes</ins>
            1.  **uint32** <ins>attribute code</ins> *see [File Attribute Types](#file-attribute-types)*
            2.  **uint32** <ins>attribute value</ins>
    11. zlib compress
  - Receive
    1.  zlib decompress
    2.  **string** <ins>username</ins>
    3.  **uint32** <ins>token</ins>
    4.  **uint32** <ins>number of results</ins>
    5.  Iterate for <ins>number of results</ins>
        1.  **uint8** <ins>code</ins> *value is always* **1**
        2.  **string** <ins>filename</ins>
        3.  **uint64** <ins>size</ins>
        4.  **string** <ins>file extension</ins> *(Always blank from SoulseekQt clients)*
        5.  **uint32** <ins>number of attributes</ins>
        6.  Iterate for <ins>number of attributes</ins>
            1.  **uint32** <ins>attribute code</ins> *see [File Attribute Types](#file-attribute-types)*
            2.  **uint32** <ins>attribute value</ins>
    6.  **bool** <ins>slotfree</ins>
    7.  **uint32** <ins>avgspeed</ins>
    8.  **uint32** <ins>queue length</ins>
    9.  **uint32** <ins>unknown</ins> *official clients always send a value of* **0**
    10.  **uint32** <ins>number of privately shared results</ins>
    11.  Iterate for <ins>number of privately shared results</ins>
         1.  **uint8** <ins>code</ins> *value is always 1*
         2.  **string** <ins>filename</ins>
         3.  **uint64** <ins>size</ins>
         4.  **string** <ins>file extension</ins> *(Always blank from SoulseekQt clients)*
         5.  **uint32** <ins>number of attributes</ins>
         6.  Iterate for <ins>number of attributes</ins>
             1.  **uint32** <ins>attribute code</ins> *see [File Attribute Types](#file-attribute-types)*
             2.  **uint32** <ins>attribute value</ins>

## Peer Code 15

### UserInfoRequest

We ask the other peer to send us their user information, picture and all.

### Data Order

  - Send
      - Empty Message
  - Receive
      - Empty Message

## Peer Code 16

### UserInfoResponse

A peer responds with this after we've sent a [UserInfoRequest](#peer-code-15).

### Data Order

  - Send
    1.  **string** <ins>description</ins>
    2.  Check contents of <ins>picture</ins>
          - If <ins>picture</ins> is not empty
            1.  **bool** <ins>has picture</ins> **1**
            2.  **bytes** <ins>picture</ins>
          - If <ins>picture</ins> is empty
            1.  **bool** <ins>has picture</ins> **0**
    3.  **uint32** <ins>totalupl</ins>
    4.  **uint32** <ins>queuesize</ins>
    5.  **bool** <ins>slotsfree</ins> *Can immediately upload*
    6.  Optional (not sent by SoulseekQt)
        1.  **uint32** <ins>uploadpermitted</ins> *Who can upload anything to us? See [Upload Permissions](#upload-permissions).*
  - Receive
    1.  **string** <ins>description</ins>
    2.  **bool** <ins>has picture</ins>
    3.  Check contents of <ins>has picture</ins>
        1.  **bytes** <ins>picture</ins> *if has picture == 1*
    4.  **uint32** <ins>totalupl</ins>
    5.  **uint32** <ins>queuesize</ins>
    6.  **bool** <ins>slotsfree</ins> *Can immediately download*
    7.  Optional (not sent by SoulseekQt)
        1.  **uint32** <ins>uploadpermitted</ins> *Who can upload anything to this user? See [Upload Permissions](#upload-permissions).*

## Peer Code 36

### FolderContentsRequest

We ask the peer to send us the contents of a single folder.

### Data Order

  - Send
    1.  **uint32** <ins>token</ins>
    2.  **string** <ins>folder</ins>
  - Receive
    1.  **uint32** <ins>token</ins>
    2.  **string** <ins>folder</ins>

## Peer Code 37

### FolderContentsResponse

A peer responds with the contents of a particular folder (with all subfolders) after we've sent a [FolderContentsRequest](#peer-code-36).

### Data Order

  - Send
    1.  **uint32** <ins>token</ins>
    2.  **string** <ins>folder</ins>
    3.  **uint32** <ins>number of folders</ins>
    4.  Iterate for <ins>number of folders</ins>
        1.  **string** <ins>dir</ins>
        2.  **uint32** <ins>number of files</ins>
        3.  Iterate <ins>number of files</ins>
            1.  **uint8** <ins>code</ins> *value is always* **1**
            2.  **string** <ins>file</ins>
            3.  **uint64** <ins>file size</ins>
            4.  **string** <ins>file extension</ins> *(Always blank from SoulseekQt clients)*
            5.  **uint32** <ins>number of attributes</ins>
            6.  Iterate for <ins>number of attributes</ins>
                1.  **uint32** <ins>attribute code</ins> *see [File Attribute Types](#file-attribute-types)*
                2.  **uint32** <ins>attribute value</ins>
    5.  zlib compress
  - Receive
    1.  zlib decompress
    2.  **uint32** <ins>token</ins>
    3.  **string** <ins>folder</ins>
    4.  **uint32** <ins>number of folders</ins>
    5.  Iterate for <ins>number of folders</ins>
        1.  **string** <ins>dir</ins>
        2.  **uint32** <ins>number of files</ins>
        3.  Iterate <ins>number of files</ins>
            1.  **uint8** <ins>code</ins> *value is always* **1**
            2.  **string** <ins>file</ins>
            3.  **uint64** <ins>file size</ins>
            4.  **string** <ins>file extension</ins> *(Always blank from SoulseekQt clients)*
            5.  **uint32** <ins>number of attributes</ins>
            6.  Iterate for <ins>number of attributes</ins>
                1.  **uint32** <ins>attribute code</ins> *see [File Attribute Types](#file-attribute-types)*
                2.  **uint32** <ins>attribute value</ins>

## Peer Code 40

### TransferRequest

This message is sent by a peer once they are ready to start uploading a file to us. A [TransferResponse](#peer-code-41-a) message is expected from the recipient, either allowing or rejecting the upload attempt.

This message was formerly used to send a download request (direction 0) as well, but Nicotine+ >= 3.0.3, Museek+ and the official clients use the [QueueUpload](#peer-code-43) peer message for this purpose today.

### Data Order

  - Send
    1.  **uint32** <ins>direction</ins> **0 or 1** *see [Transfer Directions](#transfer-directions)*
    2.  **uint32** <ins>token</ins>
    3.  **string** <ins>filename</ins>
    4.  Check contents of <ins>direction</ins>
          - **uint64** <ins>filesize</ins> *if direction == 1 (upload)*
  - Receive
    1.  **uint32** <ins>direction</ins> **0 or 1** *see [Transfer Directions](#transfer-directions)*
    2.  **uint32** <ins>token</ins>
    3.  **string** <ins>filename</ins>
    4.  Check contents of <ins>direction</ins>
          - **uint64** <ins>filesize</ins> *if direction == 1 (upload)*

## Peer Code 41 a

### TransferResponse *Download Response*

**DEPRECATED, use [QueueUpload](#peer-code-43) to request files**

Response to [TransferRequest](#peer-code-40)

We (or the other peer) either agrees, or tells the reason for rejecting the file download.

### Data Order

  - Send
    1.  **uint32** <ins>token</ins>
    2.  **bool** <ins>allowed</ins>
    3.  Check contents of <ins>allowed</ins>
          - **uint64** <ins>filesize</ins> *if allowed == 1*
          - **string** <ins>reason</ins> *if allowed == 0* ; *see [Transfer Rejection Reasons](#transfer-rejection-reasons)*
  - Receive
    1.  **uint32** <ins>token</ins>
    2.  **bool** <ins>allowed</ins>
    3.  Check contents of <ins>allowed</ins>
          - **uint64** <ins>filesize</ins> *if allowed == 1*
          - **string** <ins>reason</ins> *if allowed == 0* ; *see [Transfer Rejection Reasons](#transfer-rejection-reasons)*

## Peer Code 41 b

### TransferResponse *Upload Response*

Response to [TransferRequest](#peer-code-40)

We (or the other peer) either agrees, or tells the reason for rejecting the file upload.

### Data Order

  - Send
    1.  **uint32** <ins>token</ins>
    2.  **bool** <ins>allowed</ins>
    3.  Check contents of <ins>allowed</ins>
          - **string** <ins>reason</ins> *if allowed == 0* ; *see [Transfer Rejection Reasons](#transfer-rejection-reasons)*
  - Receive
    1.  **uint32** <ins>token</ins>
    2.  **bool** <ins>allowed</ins>
    3.  Check contents of <ins>allowed</ins>
          - **string** <ins>reason</ins> *if allowed == 0* ; *see [Transfer Rejection Reasons](#transfer-rejection-reasons)*

## Peer Code 42

### PlaceholdUpload

**OBSOLETE, no longer used**

### Data Order

  - Send
    1.  **string** <ins>filename</ins>
  - Receive
    1.  **string** <ins>filename</ins>

## Peer Code 43

### QueueUpload

This message is used to tell a peer that an upload should be queued on their end. Once the recipient is ready to transfer the requested file, they will send a [TransferRequest](#peer-code-40) to us.

### Data Order

  - Send
    1.  **string** <ins>filename</ins>
  - Receive
    1.  **string** <ins>filename</ins>

## Peer Code 44

### PlaceInQueueResponse

The peer replies with the upload queue placement of the requested file.

### Data Order

  - Send
    1.  **string** <ins>filename</ins>
    2.  **uint32** <ins>place</ins>
  - Receive
    1.  **string** <ins>filename</ins>
    2.  **uint32** <ins>place</ins>

## Peer Code 46

### UploadFailed

This message is sent whenever a file connection of an active upload closes. Soulseek NS clients can also send this message when a file cannot be read. The recipient either re-queues the upload (download on their end), or ignores the message if the transfer finished.

### Data Order

  - Send
    1.  **string** <ins>filename</ins>
  - Receive
    1.  **string** <ins>filename</ins>

## Peer Code 50

### UploadDenied

This message is sent to reject [QueueUpload](#peer-code-43) attempts and previously queued files. The reason for rejection will appear in the transfer list of the recipient.

### Data Order

  - Send
    1.  **string** <ins>filename</ins>
    2.  **string** <ins>reason</ins> *see [Transfer Rejection Reasons](#transfer-rejection-reasons)*
  - Receive
    1.  **string** <ins>filename</ins>
    2.  **string** <ins>reason</ins> *see [Transfer Rejection Reasons](#transfer-rejection-reasons)*

## Peer Code 51

### PlaceInQueueRequest

This message is sent when asking for the upload queue placement of a file.

### Data Order

  - Send
    1.  **string** <ins>filename</ins>
  - Receive
    1.  **string** <ins>filename</ins>

## Peer Code 52

### UploadQueueNotification

**DEPRECATED, sent by Soulseek NS but not SoulseekQt**

This message is sent to inform a peer about an upload attempt initiated by us.

### Data Order

  - Send
      - Empty Message
  - Receive
      - Empty Message

# File Messages

| Send         | Receive           |
|--------------|-------------------|
| Send to Peer | Receive from Peer |

File messages are sent to peers over a 'F' connection, and do not have messages codes associated with them.

### File Connection Message Format

| Message Contents |
|------------------|
| ...              |

### File Connection Messages

| Message                                   |
|-------------------------------------------|
| [File Transfer Init](#file-transfer-init) |
| [File Offset](#file-offset)               |

## File Transfer Init

### FileTransferInit

We send this to a peer via a 'F' connection to tell them that we want to start uploading a file. The token is the same as the one previously included in the [TransferRequest](#peer-code-40) peer message.

Note that slskd and Nicotine+ <= 3.0.2 use legacy download requests, and send this message when initializing our file upload connection from their end.

### Data Order

  - Send
      - **uint32** <ins>token</ins>
  - Receive
      - **uint32** <ins>token</ins>

## File Offset

### FileOffset

We send this to the uploading peer at the beginning of a 'F' connection, to tell them how many bytes of the file we've previously downloaded. If nothing was downloaded, the offset is 0.

Note that Soulseek NS fails to read the size of an incomplete download if more than 2 GB of the file has been downloaded, and the download is resumed. In consequence, the client sends an invalid file offset of -1.

### Data Order

  - Send
      - **uint64** <ins>offset</ins>
  - Receive
      - **uint64** <ins>offset</ins>

# Distributed Messages

| Send         | Receive           |
|--------------|-------------------|
| Send to Node | Receive from Node |

Distributed messages are sent to peers over a 'D' connection, and are used for the distributed search network. Only a single active connection to a peer is allowed. In Nicotine+, these messages are defined in slskmessages.py.

### Distributed Message Format

| Message Length | Code  | Message Contents |
|----------------|-------|------------------|
| uint32         | uint8 | ...              |

### Distributed Message Codes

| Code | Message                                  | Status     |
|------|------------------------------------------|------------|
| 0    | [Ping](#distributed-code-0)              | Deprecated |
| 3    | [Search Request](#distributed-code-3)    |            |
| 4    | [Branch Level](#distributed-code-4)      |            |
| 5    | [Branch Root](#distributed-code-5)       |            |
| 7    | [Child Depth](#distributed-code-7)       | Deprecated |
| 93   | [Embedded Message](#distributed-code-93) |            |

## Distributed Code 0

### DistribPing

**DEPRECATED, sent by Soulseek NS but not SoulseekQt**

We ping distributed children every 60 seconds.

### Data Order

  - Send
      - Empty Message
  - Receive
    1.  **uint32** <ins>unknown</ins>

## Distributed Code 3

### DistribSearch

Search request that arrives through the distributed network. We transmit the search request to our child peers.

### Data Order

  - Send
    1.  **uint32** <ins>unknown</ins>
    2.  **string** <ins>username</ins>
    3.  **uint32** <ins>token</ins>
    4.  **string** <ins>query</ins>
  - Receive
    1.  **uint32** <ins>unknown</ins>
    2.  **string** <ins>username</ins>
    3.  **uint32** <ins>token</ins>
    4.  **string** <ins>query</ins>

## Distributed Code 4

### DistribBranchLevel

We tell our distributed children what our position is in our branch (xth generation) on the distributed network.

If we receive a branch level of 0 from a parent, we should mark the parent as our branch root, since they won't send a [DistribBranchRoot](#distributed-code-5) message in this case.

### Data Order

  - Send
    1.  **int32** <ins>branch level</ins>
  - Receive
    1.  **int32** <ins>branch level</ins>

## Distributed Code 5

### DistribBranchRoot

We tell our distributed children the username of the root of the branch we're in on the distributed network.

This message should not be sent when we're the branch root.

### Data Order

  - Send
    1.  **string** <ins>branch root</ins>
  - Receive
    1.  **string** <ins>branch root</ins>

## Distributed Code 7

### DistribChildDepth

**DEPRECATED, sent by Soulseek NS but not SoulseekQt**

We tell our distributed parent the maximum number of generation of children we have on the distributed network.

### Data Order

  - Send
    1.  **uint32** <ins>child depth</ins>
  - Receive
    1.  **uint32** <ins>child depth</ins>

## Distributed Code 93

### DistribEmbeddedMessage

A branch root sends us an embedded distributed message. We unpack the distributed message and distribute it to our child peers.

The only type of distributed message sent at present is [DistribSearch](#distributed-code-3) (distributed code 3).

### Data Order

  - Send
    1.  **uint8** <ins>distributed code</ins> *see [Distributed Message Codes](#distributed-message-codes)*
    2.  **bytes** <ins>distributed message</ins> *Raw message associated with distributed code*
  - Receive
    1.  **uint8** <ins>distributed code</ins> *see [Distributed Message Codes](#distributed-message-codes)*
    2.  **bytes** <ins>distributed message</ins> *Raw message associated with distributed code*

# Credits

This documentation exists thanks to efforts from the following projects:

- Nicotine+ (Hyriand, daelstorm, mathiascode)
- slskd (jpdillingham)
- Museek+ (lbponey)
- SoleSeek (BriEnigma)
- PySoulSeek (Alexander Kanavin)
