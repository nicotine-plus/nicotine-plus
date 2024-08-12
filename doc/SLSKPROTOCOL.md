# Soulseek Protocol Documentation

[Last updated on August 9, 2024](https://github.com/nicotine-plus/nicotine-plus/commits/master/doc/SLSKPROTOCOL.md)

Since the official Soulseek client and server is proprietary software, this
documentation has been compiled thanks to years of reverse engineering efforts.
To preserve the health of the Soulseek network, please do not modify or extend
the protocol in ways that negatively impact the network.

If you find any inconsistencies, errors or omissions in the documentation,
please report them.


## Sections

 - [Packing](#packing)
 - [Constants](#constants)
 - [Server Messages](#server-messages)
 - [Peer Init Messages](#peer-init-messages)
 - [Peer Messages](#peer-messages)
 - [File Messages](#file-messages)
 - [Distributed Messages](#distributed-messages)


# Packing

## 8-bit Integer

| Number |
|--------|
| 1 byte |


## 16-bit Integer

| Number                  |
|-------------------------|
| 2 bytes (little-endian) |


## 32-bit Integer

| Number                  |
|-------------------------|
| 4 bytes (little-endian) |


## 64-bit Integer

| Number                  |
|-------------------------|
| 8 bytes (little-endian) |


## Bool

| Number          |
|-----------------|
| 1 byte (0 or 1) |


## String

| Length of String | String      |
|------------------|-------------|
| uint32           | byte string |


## Bytes

| Length of Bytes  | Bytes       |
|------------------|-------------|
| uint32           | byte array  |


# Constants

## Connection Types

| Type | Connection          |
|------|---------------------|
| `P`  | Peer To Peer        |
| `F`  | File Transfer       |
| `D`  | Distributed Network |


## Login Failure Reasons

| Reason            | Description                                                                      |
|-------------------|----------------------------------------------------------------------------------|
| `INVALIDUSERNAME` | Username is longer than 30 characters or contains invalid characters (non-ASCII) |
| `INVALIDPASS`     | Password for existing user is incorrect                                          |
| `INVALIDVERSION`  | Client version is outdated                                                       |


## User Status Codes

| Code | Status  |
|------|---------|
| `0`  | Offline |
| `1`  | Away    |
| `2`  | Online  |


## Upload Permissions

| Code | Status          |
|------|-----------------|
| `0`  | No One          |
| `1`  | Everyone        |
| `2`  | Users in List   |
| `3`  | Permitted Users |


## Transfer Directions

| Code | Direction          |
|------|--------------------|
| `0`  | Download from Peer |
| `1`  | Upload to Peer     |


## Transfer Rejection Reasons

### In Use

| String                | Comments                                    |
| --------------------- | ------------------------------------------- |
| `Banned`              | SoulseekQt uses 'File not shared.' instead  |
| `Cancelled`           |                                             |
| `Complete`            |                                             |
| `File not shared.`    | Note: Ends with a dot                       |
| `File read error.`    | Note: Ends with a dot                       |
| `Pending shutdown.`   | Note: Ends with a dot                       |
| `Queued`              |                                             |
| `Too many files`      |                                             |
| `Too many megabytes`  |                                             |


### Deprecated

| String                               | Comments                                                    |
| ------------------------------------ | ----------------------------------------------------------- |
| `Blocked country`                    | Exclusive to Nicotine+, no longer used in Nicotine+ >=3.2.0 |
| `Disallowed extension`               | Sent by Soulseek NS for filtered extensions                 |
| `File not shared`                    | Exclusive to Nicotine+, no longer used in Nicotine+ >=3.1.1 |
| `Remote file error`                  | Sent by Soulseek NS in response to legacy download requests |
| `User limit of x megabytes exceeded` | Exclusive to Nicotine+, no longer used in Nicotine+ >=3.1.1 |
| `User limit of x files exceeded`     | Exclusive to Nicotine+, no longer used in Nicotine+ >=3.1.1 |


## File Attribute Types

| Code   | Attribute (unit)   |
|--------|--------------------|
| `0`    | Bitrate (kbps)     |
| `1`    | Duration (seconds) |
| `2`    | VBR (0 or 1)       |
| `3`    | Encoder (unused)   |
| `4`    | Sample Rate (Hz)   |
| `5`    | Bit Depth (bits)   |


## File Attribute Combinations

These combinations are actively used by clients. Certain attributes can be
missing if a file does not provide them.

  - Soulseek NS, SoulseekQt (2015-2-21 and earlier), Nicotine+ (lossy formats),
    Museek+, SoulSeeX, slskd (lossy formats):
    -   `{0: bitrate, 1: duration, 2: VBR}`

  - SoulseekQt (2015-6-12 and later):
    -   `{0: bitrate, 1: duration}` (MP3, OGG, WMA, M4A)
    -   `{1: duration, 4: sample rate, 5: bit depth}` (FLAC, WAV, APE)
    -   `{0: bitrate, 1: duration, 4: sample rate, 5: bit depth}` (WV)

  - Nicotine+ (lossless formats), slskd (lossless formats):
    -   `{1: duration, 4: sample rate, 5: bit depth}`


# Server Messages

Server messages are used by clients to interface with the server over a
connection (TCP). In Nicotine+, these messages are defined in slskmessages.py.

If you want a Soulseek server, check out [Soulfind](https://github.com/soulfind-dev/soulfind).
Soulfind is obviously not exactly the same as the official proprietary Soulseek
server, but it handles the protocol well enough (and can be modified).


## Server Message Format

| Message Length | Code   | Message Contents |
|----------------|--------|------------------|
| uint32         | uint32 | ...              |


## Server Message Codes

| Code   | Message                                                        |
|--------|----------------------------------------------------------------|
| `1`    | [Login](#server-code-1)                                        |
| `2`    | [Set Listen Port](#server-code-2)                              |
| `3`    | [Get Peer Address](#server-code-3)                             |
| `5`    | [Watch User](#server-code-5)                                   |
| `6`    | [Unwatch User](#server-code-6)                                 |
| `7`    | [Get User Status](#server-code-7)                              |
| `11`   | [Ignore User](#server-code-11) `OBSOLETE`                      |
| `12`   | [Unignore User](#server-code-12) `OBSOLETE`                    |
| `13`   | [Say in Chat Room](#server-code-13)                            |
| `14`   | [Join Room](#server-code-14)                                   |
| `15`   | [Leave Room](#server-code-15)                                  |
| `16`   | [User Joined Room](#server-code-16)                            |
| `17`   | [User Left Room](#server-code-17)                              |
| `18`   | [Connect To Peer](#server-code-18)                             |
| `22`   | [Private Messages](#server-code-22)                            |
| `23`   | [Acknowledge Private Message](#server-code-23)                 |
| `25`   | [File Search Room](#server-code-25) `OBSOLETE`                 |
| `26`   | [File Search](#server-code-26)                                 |
| `28`   | [Set Online Status](#server-code-28)                           |
| `32`   | [Ping](#server-code-32)                                        |
| `33`   | [Send Connect Token](#server-code-33) `OBSOLETE`               |
| `34`   | [Send Download Speed](#server-code-34) `OBSOLETE`              |
| `35`   | [Shared Folders & Files](#server-code-35)                      |
| `36`   | [Get User Stats](#server-code-36)                              |
| `40`   | [Queued Downloads](#server-code-40) `OBSOLETE`                 |
| `41`   | [Kicked from Server](#server-code-41)                          |
| `42`   | [User Search](#server-code-42)                                 |
| `50`   | [Similar Recommendations](#server-code-50) `OBSOLETE`          |
| `51`   | [Interest Add](#server-code-51) `DEPRECATED`                   |
| `52`   | [Interest Remove](#server-code-52) `DEPRECATED`                |
| `54`   | [Get Recommendations](#server-code-54) `DEPRECATED`            |
| `55`   | [My Recommendations](#server-code-55) `OBSOLETE`               |
| `56`   | [Get Global Recommendations](#server-code-56) `DEPRECATED`     |
| `57`   | [Get User Interests](#server-code-57) `DEPRECATED`             |
| `58`   | [Admin Command](#server-code-58) `OBSOLETE`                    |
| `60`   | [Place In Line Response](#server-code-60) `OBSOLETE`           |
| `62`   | [Room Added](#server-code-62) `OBSOLETE`                       |
| `63`   | [Room Removed](#server-code-63) `OBSOLETE`                     |
| `64`   | [Room List](#server-code-64)                                   |
| `65`   | [Exact File Search](#server-code-65) `OBSOLETE`                |
| `66`   | [Global/Admin Message](#server-code-66)                        |
| `67`   | [Global User List](#server-code-67) `OBSOLETE`                 |
| `68`   | [Tunneled Message](#server-code-68) `OBSOLETE`                 |
| `69`   | [Privileged Users](#server-code-69)                            |
| `71`   | [Have No Parents](#server-code-71)                             |
| `73`   | [Parent's IP](#server-code-73) `DEPRECATED`                    |
| `83`   | [Parent Min Speed](#server-code-83)                            |
| `84`   | [Parent Speed Ratio](#server-code-84)                          |
| `86`   | [Parent Inactivity Timeout](#server-code-86) `OBSOLETE`        |
| `87`   | [Search Inactivity Timeout](#server-code-87) `OBSOLETE`        |
| `88`   | [Minimum Parents In Cache](#server-code-88) `OBSOLETE`         |
| `90`   | [Distributed Ping Interval](#server-code-90) `OBSOLETE`        |
| `91`   | [Add Privileged User](#server-code-91) `OBSOLETE`              |
| `92`   | [Check Privileges](#server-code-92)                            |
| `93`   | [Embedded Message](#server-code-93)                            |
| `100`  | [Accept Children](#server-code-100)                            |
| `102`  | [Possible Parents](#server-code-102)                           |
| `103`  | [Wishlist Search](#server-code-103)                            |
| `104`  | [Wishlist Interval](#server-code-104)                          |
| `110`  | [Get Similar Users](#server-code-110) `DEPRECATED`             |
| `111`  | [Get Item Recommendations](#server-code-111) `DEPRECATED`      |
| `112`  | [Get Item Similar Users](#server-code-112) `DEPRECATED`        |
| `113`  | [Room Tickers](#server-code-113)                               |
| `114`  | [Room Ticker Add](#server-code-114)                            |
| `115`  | [Room Ticker Remove](#server-code-115)                         |
| `116`  | [Set Room Ticker](#server-code-116)                            |
| `117`  | [Hated Interest Add](#server-code-117) `DEPRECATED`            |
| `118`  | [Hated Interest Remove](#server-code-118) `DEPRECATED`         |
| `120`  | [Room Search](#server-code-120)                                |
| `121`  | [Send Upload Speed](#server-code-121)                          |
| `122`  | [User Privileges](#server-code-122) `DEPRECATED`               |
| `123`  | [Give Privileges](#server-code-123)                            |
| `124`  | [Notify Privileges](#server-code-124) `DEPRECATED`             |
| `125`  | [Acknowledge Notify Privileges](#server-code-125) `DEPRECATED` |
| `126`  | [Branch Level](#server-code-126)                               |
| `127`  | [Branch Root](#server-code-127)                                |
| `129`  | [Child Depth](#server-code-129) `DEPRECATED`                   |
| `130`  | [Reset Distributed](#server-code-130)                          |
| `133`  | [Private Room Users](#server-code-133)                         |
| `134`  | [Private Room Add User](#server-code-134)                      |
| `135`  | [Private Room Remove User](#server-code-135)                   |
| `136`  | [Private Room Cancel Membership](#server-code-136)             |
| `137`  | [Private Room Disown](#server-code-137)                        |
| `138`  | [Private Room Unknown](#server-code-138) `OBSOLETE`            |
| `139`  | [Private Room Added](#server-code-139)                         |
| `140`  | [Private Room Removed](#server-code-140)                       |
| `141`  | [Private Room Toggle](#server-code-141)                        |
| `142`  | [New Password](#server-code-142)                               |
| `143`  | [Private Room Add Operator](#server-code-143)                  |
| `144`  | [Private Room Remove Operator](#server-code-144)               |
| `145`  | [Private Room Operator Added](#server-code-145)                |
| `146`  | [Private Room Operator Removed](#server-code-146)              |
| `148`  | [Private Room Operators](#server-code-148)                     |
| `149`  | [Message Users](#server-code-149)                              |
| `150`  | [Join Global Room](#server-code-150) `DEPRECATED`              |
| `151`  | [Leave Global Room](#server-code-151) `DEPRECATED`             |
| `152`  | [Global Room Message](#server-code-152) `DEPRECATED`           |
| `153`  | [Related Searches](#server-code-153) `OBSOLETE`                |
| `160`  | [Excluded Search Phrases](#server-code-160)                    |
| `1001` | [Can't Connect To Peer](#server-code-1001)                     |
| `1003` | [Can't Create Room](#server-code-1003)                         |


## Server Code 1

### Login

We send this to the server right after the connection has been established.
Server responds with the greeting message.

### Sending Login Example

#### Message

| Data      | Message Length | Message Code  | Username Length | Username                  | Password Length | Password                  |
|-----------|----------------|---------------|-----------------|---------------------------|-----------------|---------------------------|
| **Human** | 72             | 1             | 8               | username                  | 8               | password                  |
| **Hex**   | `48 00 00 00`  | `01 00 00 00` | `08 00 00 00`   | `75 73 65 72 6e 61 6d 65` | `08 00 00 00`   | `70 61 73 73 77 6f 72 64` |

#### ...continued

| Data      | Version       | Hash Length   | Hash                                                                                              | Minor Version |
|-----------|---------------|---------------|---------------------------------------------------------------------------------------------------|---------------|
| **Human** | 160           | 32            | d51c9a7e9353746a6020f9602d452929                                                                  | 1             |
| **Hex**   | `a0 00 00 00` | `20 00 00 00` | `64 35 31 63 39 61 37 65 39 33 35 33 37 34 36 61 36 30 32 30 66 39 36 30 32 64 34 35 32 39 32 39` | `01 00 00 00` |

#### Message as Hex Stream

```
48 00 00 00 01 00 00 00 08 00 00 00 75 73 65 72 6e 61 6d 65 08 00 00 00 70 61 73 73 77 6f 72 64 a0 00 00 00 20 00
00 00 64 35 31 63 39 61 37 65 39 33 35 33 37 34 36 61 36 30 32 30 66 39 36 30 32 64 34 35 32 39 32 39 01 00 00 00
```

### Data Order
  - Send
    1.  **string** *username*
    2.  **string** *password*  
        A non-empty string is required
    3.  **uint32** *version number*  
        `160` for Nicotine+
    4.  **string** *hash*  
        MD5 hex digest of concatenated username and password
    5.  **uint32** *minor version*  
        `0x13000000` for 157 ns 13e, `0x11000000` for 157 ns 13c
  - Receive
    1.  **bool** *success*
    2.  If *success* is true
        1.  **string** *greet*  
            MOTD string
        2.  **uint32** *own IP address*
        3.  **string** *hash*  
            MD5 hex digest of the password string
        4.  **bool** *is supporter*  
            If we have donated to Soulseek at some point in the past
    3.  If *success* is false
        1.  **bool** *failure*
        2.  **string** *reason*
            See [Login Failure Reasons](#login-failure-reasons)


## Server Code 2

### SetWaitPort

We send this to the server to indicate the port number that we listen on (2234
by default).

If this value is set to zero, or the message is not sent upon login (which
defaults the listen port to 0), remote clients handling a [ConnectToPeer](#server-code-18)
message will fail to properly purge the request.  Confirmed in SoulseekQt
2020.3.12, but probably impacts most or all other versions.

### Data Order
  - Send
    1.  **uint32** *port*
    2.  **uint32** *unknown*  
        SoulseekQt uses a value of `1`
    3.  **uint32** *obfuscated port*
  - Receive
    -   *No Message*


## Server Code 3

### GetPeerAddress

We send this to the server to ask for a peer's address (IP address and port),
given the peer's username.

### Data Order

  - Send
    1.  **string** *username*
  - Receive
    1.  **string** *username*
    2.  **ip** *ip*
    3.  **uint32** *port*
    4.  **uint32** *unknown*
        SoulseekQt uses a value of `1`
    5.  **uint16** *obfuscated port*


## Server Code 5

### WatchUser

Used to be kept updated about a user's status. Whenever a user's status
changes, the server sends a [GetUserStatus](#server-code-7) message.

Note that the server does not currently send stat updates ([GetUserStats](#server-code-36))
when watching a user, only the initial stats in the [WatchUser](#server-code-5)
response. As a consequence, stats can be outdated.

### Data Order

  - Send
    1.  **string** *username*
  - Receive
    1.  **string** *username*
    2.  **bool** *exists*
    3.  If *exists* is true
        1.  **uint32** *status*  
            See [User Status Codes](#user-status-codes)
        2.  **uint32** *avgspeed*
        3.  **uint32** *uploadnum*  
            Number of uploaded files, previously used for number of downloaded
            files in old versions of Soulseek. Used to grow indefinitely, but
            now rolls over after a certain point. The value increments when
            sending a [SendUploadSpeed](#server-code-121) server message.
        4.  **uint32** *unknown*
        5.  **uint32** *files*
        6.  **uint32** *dirs*
        7.  If *status* is away/online
            1.  **string** *countrycode*  
                Uppercase country code


## Server Code 6

### UnwatchUser

Used when we no longer want to be kept updated about a user's status.

### Data Order

  - Send
    1.  **string** *username*
  - Receive
    -   *No Message*


## Server Code 7

### GetUserStatus

The server tells us if a user has gone away or has returned.

### Data Order

  - Send
    1.  **string** *username*
  - Receive
    1.  **string** *username*
    2.  **uint32** *status*  
        See [User Status Codes](#user-status-codes)
    3.  **bool** *privileged*


## Server Code 11

### IgnoreUser

**OBSOLETE, no longer used**

We send this to the server to tell a user we have ignored them.

The server tells us a user has ignored us.

### Data Order

  - Send
    1.  **string** *username*
  - Receive
    1.  **string** *username*


## Server Code 12

### UnignoreUser

**OBSOLETE, no longer used**

We send this to the server to tell a user we are no longer ignoring them.

The server tells us a user is no longer ignoring us.

### Data Order

  - Send
    1.  **string** *username*
  - Receive
    1.  **string** *username*


## Server Code 13

### SayChatroom

Either we want to say something in the chatroom, or someone else did.

### Data Order

  - Send
    1.  **string** *room*
    2.  **string** *message*
  - Receive
    1.  **string** *room*
    2.  **string** *username*
    3.  **string** *message*


## Server Code 14

### JoinRoom

We send this message to the server when we want to join a room. If the
room doesn't exist, it is created.

Server responds with this message when we join a room. Contains users
list with data on everyone.

As long as we're in the room, the server will automatically send us
status/stat updates for room users, including ourselves, in the form
of [GetUserStatus](#server-code-7) and [GetUserStats](#server-code-36)
messages.

Room names must meet certain requirements, otherwise the server will
send a [MessageUser](#server-code-22) message containing an error message.
Requirements include:

  - Non-empty string
  - Only ASCII characters
  - 24 characters or fewer
  - No leading or trailing spaces
  - No consecutive spaces

### Data Order

  - Send
    1.  **string** *room*
    2.  **uint32** *private*  
        If the room doesn't exist, should the new room be private?
  - Receive
    1.  **string** *room*
    2.  **uint32** *number of users in room*  
        For private rooms, also contain owner and operators
    3.  Iterate for *number of users*
        1.  **string** *username*
    4.  **uint32** *number of statuses*
    5.  Iterate for *number of statuses*
        1.  **uint32** *status*
    6.  **uint32** *number of user stats*
    7.  Iterate for *number of user stats*
        1.  **uint32** *avgspeed*
        2.  **uint32** *uploadnum*
        3.  **uint32** *unknown*
        4.  **uint32** *files*
        5.  **uint32** *dirs*
    8.  **uint32** *number of slotsfree*
    9.  Iterate for *number of slotsfree*
        1.  **uint32** *slotsfree*
    10. **uint32** *number of user countries*
    11. Iterate for *number of user countries*
        1.  **string** *countrycode*  
            Uppercase country code
    12. If private room
        1.  **string** *owner*
        2.  **uint32** *number of operators in room*
        3.  Iterate for *number of operators*
            1.  **string** *operator*


## Server Code 15

### LeaveRoom

We send this to the server when we want to leave a room.

### Data Order

  - Send
    1.  **string** *room*
  - Receive
    1.  **string** *room*


## Server Code 16

### UserJoinedRoom

The server tells us someone has just joined a room we're in.

### Data Order

  - Send
    -   *No Message*
  - Receive
    1.  **string** *room*
    2.  **string** *username*
    3.  **uint32** *status*
    4.  **uint32** *avgspeed*
    5.  **uint32** *uploadnum*
    6.  **uint32** *unknown*
    7.  **uint32** *files*
    8.  **uint32** *dirs*
    9.  **uint32** *slotsfree*
    10. **string** *countrycode*  
        Uppercase country code


## Server Code 17

### UserLeftRoom

The server tells us someone has just left a room we're in.

### Data Order

  - Send
    -   *No Message*
  - Receive
    1.  **string** *room*
    2.  **string** *username*


## Server Code 18

### ConnectToPeer

We send this to the server to attempt an indirect connection with a user.
The server forwards the message to the user, who in turn attempts to establish
a connection to our IP address and port from their end.

See also: [Peer Connection Message Order](#modern-peer-connection-message-order)

### Data Order

  - Send
    1.  **uint32** *token*
    2.  **string** *username*
    3.  **string** *type*  
        See [Connection Types](#connection-types)
  - Receive
    1.  **string** *username*
    2.  **string** *type*  
        See [Connection Types](#connection-types)
    3.  **ip** *ip*
    4.  **uint32** *port*
    5.  **uint32** *token*  
        Use this token for [PierceFireWall](#peer-init-code-0)
    6.  **bool** *privileged*
    7.  **uint32** *unknown*  
        SoulseekQt uses a value of `1`
    8.  **uint32** *obfuscated port*


## Server Code 22

### MessageUser

Chat phrase sent to someone or received by us in private.

### Data Order

  - Send
    1.  **string** *username*
    2.  **string** *message*
  - Receive
    1.  **uint32** *ID*
    2.  **uint32** *timestamp*
    3.  **string** *username*
    4.  **string** *message*
    5.  **bool** *new message*  
        True if message is new, false if message is re-sent (e.g. if recipient was offline)


## Server Code 23

### MessageAcked

We send this to the server to confirm that we received a private message. If we
don't send it, the server will keep sending the chat phrase to us.

### Data Order

  - Send
    1.  **uint32** *message ID*
  - Receive
    -   *No Message*


## Server Code 25

### FileSearchRoom

**OBSOLETE, use [RoomSearch](#server-code-120) server message**

We send this to the server when we search for something in a room.

### Data Order

  - Send
    1. **uint32** *token*
    2. **uint32** *room id*
    3. **string** *search query*
  - Receive
    -   *No Message*


## Server Code 26

### FileSearch

We send this to the server when we search for something. Alternatively, the
server sends this message outside the distributed network to tell us that
someone is searching for something, currently used for [UserSearch](#server-code-42)
and [RoomSearch](#server-code-120) requests.

The token is a number generated by the client and is used to track the search
results.

### Data Order

  - Send
    1.  **uint32** *token*
    2.  **string** *search query*
  - Receive
    1.  **string** *username*
    2.  **uint32** *token*
    3.  **string** *search query*


## Server Code 28

### SetStatus

We send our new status to the server. Status is a way to define whether we're
available (online) or busy (away).

When changing our own status, the server sends us a [GetUserStatus](#server-code-7)
message when enabling away status, but not when disabling it.

*1 = Away  
2 = Online*

### Data Order

  - Send
    1.  **int32** *status*  
        See [User Status Codes](#user-status-codes)
  - Receive
    -   *No Message*


## Server Code 32

### ServerPing

We send this to the server at most once per minute to ensure the connection
stays alive.

The server used to send a response message in the past, but this is no
longer the case.

Nicotine+ uses TCP keepalive instead of sending this message.

### Data Order

  - Send
    -   Empty Message
  - Receive `OBSOLETE`
    -   Empty Message


## Server Code 33

### SendConnectToken

**OBSOLETE, no longer used**

### Data Order

  - Send
    1.  **string** *username*
    2.  **uint32** *token*
  - Receive
    1.  **string** *username*
    2.  **uint32** *token*


## Server Code 34

### SendDownloadSpeed

**OBSOLETE, use [SendUploadSpeed](#server-code-121) server message**

We used to send this after a finished download to let the server update the
speed statistics for a user.

### Data Order

  - Send
    1.  **string** *username*
    2.  **uint32** *speed*
  - Receive
    -   *No Message*


## Server Code 35

### SharedFoldersFiles

We send this to server to indicate the number of folder and files that we
share.

### Data Order

  - Send
    1.  **uint32** *dirs*
    2.  **uint32** *files*
  - Receive
    -   *No Message*


## Server Code 36

### GetUserStats

The server sends this to indicate a change in a user's statistics, if we've
requested to watch the user in [WatchUser](#server-code-5) previously. A user's
stats can also be requested by sending a [GetUserStats](#server-code-36)
message to the server, but [WatchUser](#server-code-5) should be used instead.

### Data Order

  - Send
    1.  **string** *username*
  - Receive
    1.  **string** *username*
    2.  **uint32** *avgspeed*
    3.  **uint32** *uploadnum*
    4.  **uint32** *unknown*
    5.  **uint32** *files*
    6.  **uint32** *dirs*


## Server Code 40

### QueuedDownloads

**OBSOLETE, no longer sent by the server**

The server sends this to indicate if someone has download slots available or
not.

### Data Order

  - Send
    -   *No Message*
  - Receive
    1.  **string** *username*
    2.  **bool** *slotsfree*  
        Can immediately download


## Server Code 41

### Relogged

The server sends this if someone else logged in under our nickname, and then
disconnects us.

### Data Order

  - Send
    -   *No Message*
  - Receive
    -   Empty Message


## Server Code 42

### UserSearch

We send this to the server when we search a specific user's shares. The token
is a number generated by the client and is used to track the search results.

In the past, the server sent us this message for UserSearch requests from other
users. Today, the server sends a [FileSearch](#server-code-26) message instead.

### Data Order

  - Send
    1.  **string** *username*
    2.  **uint32** *token*
    3.  **string** *search query*
  - Receive `OBSOLETE`
    1.  **string** *username*
    2.  **uint32** *token*
    3.  **string** *search query*


## Server Code 50

### SimilarRecommendations

**OBSOLETE**

We send this to the server when we are adding a recommendation to our
"My recommendations" list, and want to receive a list of similar
recommendations.

The server sends a list of similar recommendations to the one we want to
add. Older versions of the official Soulseek client would display a dialog
containing such recommendations, asking us if we want to add our original
recommendation or one of the similar ones instead.

### Data Order

  - Send
    1.  **string** *recommendation*
  - Receive
    1.  **string** *recommendation*
    2.  **uint32** *number of similar recommendations*
    3.  Iterate for *number of similar recommendations*
        1.  **string** *similar recommendation*


## Server Code 51

### AddThingILike

**DEPRECATED, used in Soulseek NS but not SoulseekQt**

We send this to the server when we add an item to our likes list.

### Data Order

  - Send
    1.  **string** *item*
  - Receive
    -   *No Message*


## Server Code 52

### RemoveThingILike

**DEPRECATED, used in Soulseek NS but not SoulseekQt**

We send this to the server when we remove an item from our likes list.

### Data Order

  - Send
    1.  **string** *item*
  - Receive
    -   *No Message*


## Server Code 54

### Recommendations

**DEPRECATED, used in Soulseek NS but not SoulseekQt**

The server sends us a list of personal recommendations and a number for each.

### Data Order

  - Send
    -   Empty Message
  - Receive
    1.  **uint32** *number of total recommendations*
    2.  Iterate for *number of total recommendations*
        1.  **string** *recommendation*
        2.  **int32** *number of recommendations this recommendation has*
    3.  **uint32** *number of total unrecommendations*
    4.  Iterate for *number of total unrecommendations*
        1.  **string** *unrecommendation*
        2.  **int32** *number of unrecommendations this unrecommendation has (negative)*


## Server Code 55

### MyRecommendations

**OBSOLETE**

We send this to the server to ask for our own list of added
likes/recommendations (called "My recommendations" in older versions
of the official Soulseek client).

The server sends us the list of recommendations it knows we have added.
For any recommendations present locally, but not on the server, the
official Soulseek client would send a [AddThingILike](#server-code-51)
message for each missing item.

### Data Order

  - Send
    -   Empty Message
  - Receive
    1.  **uint32** *number of own recommendations*
    2.  Iterate for *number of own recommendations*
        1.  **string** *recommendation*


## Server Code 56

### GlobalRecommendations

**DEPRECATED, used in Soulseek NS but not SoulseekQt**

The server sends us a list of global recommendations and a number for each.

### Data Order

  - Send
    -   Empty Message
  - Receive
    1.  **uint32** *number of total recommendations*
    2.  Iterate for *number of total recommendations*
        1.  **string** *recommendation*
        2.  **int32** *number of recommendations this recommendation has*
    3.  **uint32** *number of total unrecommendations*
    4.  Iterate for *number of total unrecommendations*
        1.  **string** *unrecommendation*
        2.  **int32** *number of unrecommendations this unrecommendation has (negative)*


## Server Code 57

### UserInterests

**DEPRECATED, used in Soulseek NS but not SoulseekQt**

We ask the server for a user's liked and hated interests. The server responds
with a list of interests.

### Data Order

  - Send
    1.  **string** *username*
  - Receive
    1.  **string** *username*
    2.  **uint32** *number of liked interests*
    3.  Iterate for *number of liked interests*
        1.  **string** *interest*
    4.  **uint32** *number of hated interests*
    5.  Iterate for *number of hated interests*
        1.  **string** *interest*


## Server Code 58

### AdminCommand

**OBSOLETE**

We send this to the server to run an admin command (e.g. to ban or silence a
user) if we have admin status on the server.

### Data Order

  - Send
    1.  **string** *command*
    2.  **uint32** *number of command arguments*
    3.  Iterate for *number of command arguments*
        1.  **string** *command argument*
  - Receive
    -   *No Message*


## Server Code 60

### PlaceInLineResponse

**OBSOLETE, use [PlaceInQueueResponse](#peer-code-44) peer message**

The server sends this to indicate change in place in queue while we're waiting
for files from another peer.

### Data Order

  - Send
    1.  **string** *username*
    2.  **uint32** *req*
    3.  **uint32** *place*
  - Receive
    1.  **string** *username*
    2.  **uint32** *req*
    3.  **uint32** *place*


## Server Code 62

### RoomAdded

**OBSOLETE, no longer sent by the server**

The server tells us a new room has been added.

### Data Order

  - Send
    -   *No Message*
  - Receive
    1.  **string** *room*


## Server Code 63

### RoomRemoved

**OBSOLETE, no longer sent by the server**

The server tells us a room has been removed.

### Data Order

  - Send
    -   *No Message*
  - Receive
    1.  **string** *room*


## Server Code 64

### RoomList

The server tells us a list of rooms and the number of users in them. When
connecting to the server, the server only sends us rooms with at least 5 users.
A few select rooms are also excluded, such as nicotine and The Lobby.
Requesting the room list yields a response containing the missing rooms.

### Data Order

  - Send
    -   Empty Message
  - Receive
    1.  **uint32** *number of rooms*
    2.  Iterate for *number of rooms*
        1.  **string** *room*
    3.  **uint32** *number of rooms*
    4.  Iterate for *number of rooms*
        1.  **uint32** *number of users in room*
    5.  **uint32** *number of owned private rooms*
    6.  Iterate for *number of owned private rooms*
        1.  **string** *owned private room*
    7.  **uint32** *number of owned private rooms*
    8.  Iterate for *number of owned private rooms*
        1.  **uint32** *number of users in owned private room*
    9.  **uint32** *number of private rooms (except owned)*
    10. Iterate for *number of private rooms (except owned)*
        1.  **string** *private room*
    11. **uint32** *number of private rooms (except owned)*
    12. Iterate for *number of private rooms (except owned)*
        1.  **uint32** *number of users in private rooms (except owned)*
    13. **uint32** *number of operated private rooms*
    14. Iterate for *number of operated private rooms*
        1.  **string** *operated private room*


## Server Code 65

### ExactFileSearch

**OBSOLETE, no results even with official client**

We send this to search for an exact file name and folder, to find other
sources.

### Data Order

  - Send
    1.  **uint32** *token*
    2.  **string** *filename*
    3.  **string** *path*
    4.  **uint64** *file size*
    5.  **uint32** *checksum*
    6.  **uint8** *unknown*
  - Receive
    1.  **string** *username*
    2.  **uint32** *token*
    3.  **string** *filename*
    4.  **string** *path*
    5.  **uint64** *file size*
    6.  **uint32** *checksum*


## Server Code 66

### AdminMessage

A global message from the server admin has arrived.

### Data Order

  - Send
    -   *No Message*
  - Receive
    1.  **string** *message*


## Server Code 67

### GlobalUserList

**OBSOLETE, no longer used**

We send this to get a global list of all users online.

### Data Order

  - Send
    -   Empty Message
  - Receive
    1.  **uint32** *number of users in room*
    2.  Iterate for *number of users*
        1.  **string** *username*
    3.  **uint32** *number of userdata*
    4.  Iterate for *number of users*
        1.  **uint32** *status*
    5.  **uint32** *number of userdata*
    6.  Iterate for *number of userdata*
        1.  **uint32** *avgspeed*
        2.  **uint32** *uploadnum*
        3.  **uint32** *unknown*
        4.  **uint32** *files*
        5.  **uint32** *dirs*
    7.  **uint32** *number of slotsfree*
    8.  Iterate for *number of slotsfree*
        1.  **uint32** *slotsfree*
    9. **uint32** *number of usercountries*
    10. Iterate for *number of usercountries*
        1.  **string** *countrycode*  
            Uppercase country code


## Server Code 68

### TunneledMessage

**OBSOLETE, no longer used**

Server message for tunneling a chat message.

### Data Order

  - Send
    1.  **string** *username*
    2.  **uint32** *token*
    3.  **uint32** *code*
    4.  **string** *message*
  - Receive
    1.  **string** *username*
    2.  **uint32** *code*
    3.  **uint32** *token*
    4.  **ip** *ip*
    5.  **uint32** *port*
    6.  **string** *message*


## Server Code 69

### PrivilegedUsers

The server sends us a list of privileged users, a.k.a. users who have donated.

### Data Order

  - Send
    -   *No Message*
  - Receive
    1.  **uint32** *number of users*
    2.  Iterate *number of users*
        1.  **string** *username*


## Server Code 71

### HaveNoParent

We inform the server if we have a distributed parent or not. If not, the server
eventually sends us a [PossibleParents](#server-code-102) message with a list
of possible parents to connect to. If no candidates are found, no such message
is sent by the server, and we eventually become a branch root.

### Data Order

  - Send
    1.  **bool** *have parents*
  - Receive
    -   *No Message*


## Server Code 73

### SearchParent

**DEPRECATED, sent by Soulseek NS but not SoulseekQt**

We send the IP address of our parent to the server.

### Data Order

  - Send
    1.  **ip** *ip*
  - Receive
    -   *No Message*


## Server Code 83

### ParentMinSpeed

The server informs us about the minimum upload speed required to become a
parent in the distributed network.

### Data Order

  - Send
    -   *No Message*
  - Receive
    1.  **uint32** *speed*


## Server Code 84

### ParentSpeedRatio

The server sends us a speed ratio determining the number of children we can
have in the distributed network. The maximum number of children is our upload
speed divided by the speed ratio.

### Data Order

  - Send
    -   *No Message*
  - Receive
    1.  **uint32** *ratio*


## Server Code 86

### ParentInactivityTimeout

**OBSOLETE, no longer sent by the server**

### Data Order

  - Send
    -   *No Message*
  - Receive
    1.  **uint32** *seconds*


## Server Code 87

### SearchInactivityTimeout

**OBSOLETE, no longer sent by the server**

### Data Order

  - Send
    -   *No Message*
  - Receive
    1.  **uint32** *seconds*


## Server Code 88

### MinParentsInCache

**OBSOLETE, no longer sent by the server**

### Data Order

  - Send
    -   *No Message*
  - Receive
    1.  **uint32** *number*


## Server Code 90

### DistribPingInterval

**OBSOLETE, no longer sent by the server**

### Data Order

  - Send
    -   *No Message*
  - Receive
    1.  **uint32** *seconds*


## Server Code 91

### AddToPrivileged

**OBSOLETE, no longer sent by the server**

The server sends us the username of a new privileged user, which we add to our
list of global privileged users.

### Data Order

  - Send
    -   *No Message*
  - Receive
    1.  **string** *username*


## Server Code 92

### CheckPrivileges

We ask the server how much time we have left of our privileges. The server
responds with the remaining time, in seconds.

### Data Order

  - Send
    -   Empty Message
  - Receive
    1.  **uint32** *time left*


## Server Code 93

### EmbeddedMessage

The server sends us an embedded distributed message. The only type of
distributed message sent at present is [DistribSearch](#distributed-code-3)
(distributed code 3). If we receive such a message, we are a branch root in
the distributed network, and we distribute the embedded message (not the
unpacked distributed message) to our child peers.

### Data Order

  - Send
    -   *No Message*
  - Receive
    1.  **uint8** *distributed code*  
        See [Distributed Message Codes](#distributed-message-codes)
    2.  **bytes** *distributed message*  
        Raw message associated with distributed code


## Server Code 100

### AcceptChildren

We tell the server if we want to accept child nodes.

### Data Order

  - Send
    1.  **bool** *accept*
  - Receive
    -   *No Message*


## Server Code 102

### PossibleParents

The server send us a list of max 10 possible distributed parents to connect to.
Messages of this type are sent to us at regular intervals, until we tell the
server we don't need more possible parents with a [HaveNoParent](#server-code-71)
message.

The received list always contains users whose upload speed is higher than our
own. If we have the highest upload speed on the server, we become a branch
root, and start receiving [SearchRequest](#server-code-93) messages directly
from the server.

### Data Order

  - Send
    -   *No Message*
  - Receive
    1.  **uint32** *number of parents*
    2.  Iterate for *number of parents*
        1.  **string** *username*
        2.  **ip** *ip*
        3.  **uint32** *port*


## Server Code 103

### WishlistSearch

We send the server one of our wishlist search queries at each interval.

### Data Order

  - Send
    1.  **uint32** *token*
    2.  **string** *search query*
  - Receive
    -   *No Message*


## Server Code 104

### WishlistInterval

The server tells us the wishlist search interval.

This interval is almost always 12 minutes, or 2 minutes for privileged users.

### Data Order

  - Send
    -   *No Message*
  - Receive
    1.  **uint32** *interval*


## Server Code 110

### SimilarUsers

**DEPRECATED, used in Soulseek NS but not SoulseekQt**

The server sends us a list of similar users related to our interests.

### Data Order

  - Send
    -   Empty Message
  - Receive
    1.  **uint32** *number of users*
    2.  Iterate for *number of user*
        1.  **string** *username*
        2.  **uint32** *rating*


## Server Code 111

### ItemRecommendations

**DEPRECATED, used in Soulseek NS but not SoulseekQt**

The server sends us a list of recommendations related to a specific item, which
is usually present in the like/dislike list or an existing recommendation list.

### Data Order

  - Send
    1.  **string** *item*
  - Receive
    1.  **string** *item*
    2.  **uint32** *number of recommendations*
    3.  Iterate for *number of recommendations*
        1.  **string** *recommendation*
        2.  **uint32** *number of recommendations for this recommendation (can be negative)*


## Server Code 112

### ItemSimilarUsers

**DEPRECATED, used in Soulseek NS but not SoulseekQt**

The server sends us a list of similar users related to a specific item, which
is usually present in the like/dislike list or recommendation list.

### Data Order

  - Send
    1.  **string** *item*
  - Receive
    1.  **string** *item*
    2.  **uint32** *number of users*
    3.  Iterate for *number of users*
        1.  **string** *username*


## Server Code 113

### RoomTickerState

The server returns a list of tickers in a chat room.

Tickers are customizable, user-specific messages that appear on chat room
walls.

### Data Order

  - Send
    -   *No Message*
  - Receive
    1.  **string** *room*
    2.  **uint32** *number of users*
    3.  Iterate for *number of user*
        1.  **string** *username*
        2.  **string** *tickers*


## Server Code 114

### RoomTickerAdd

The server sends us a new ticker that was added to a chat room.

Tickers are customizable, user-specific messages that appear on chat room
walls.

### Data Order

  - Send
    -   *No Message*
  - Receive
    1.  **string** *room*
    2.  **string** *username*
    3.  **string** *ticker*


## Server Code 115

### RoomTickerRemove

The server informs us that a ticker was removed from a chat room.

Tickers are customizable, user-specific messages that appear on chat room
walls.

### Data Order

  - Send
    -   *No Message*
  - Receive
    1.  **string** *room*
    2.  **string** *username*


## Server Code 116

### RoomTickerSet

We send this to the server when we change our own ticker in a chat room.
Sending an empty ticker string removes any existing ticker in the room.

Tickers are customizable, user-specific messages that appear on chat room
walls.

### Data Order

  - Send
    1.  **string** *room*
    2.  **string** *ticker*
  - Receive
    -   *No Message*


## Server Code 117

### AddThingIHate

**DEPRECATED, used in Soulseek NS but not SoulseekQt**

We send this to the server when we add an item to our hate list.

### Data Order

  - Send
    1.  **string** *item*
  - Receive
    -   *No Message*


## Server Code 118

### RemoveThingIHate

**DEPRECATED, used in Soulseek NS but not SoulseekQt**

We send this to the server when we remove an item from our hate list.

### Data Order

  - Send
    1.  **string** *item*
  - Receive
    -   *No Message*


## Server Code 120

### RoomSearch

We send this to the server to search files shared by users who have joined a
specific chat room. The token is a number generated by the client and is used
to track the search results.

In the past, the server sent us this message for RoomSearch requests from other
users. Today, the server sends a [FileSearch](#server-code-26) message instead.

### Data Order

  - Send
    1.  **string** *room*
    2.  **uint32** *token*
    3.  **string** *search query*
  - Receive `OBSOLETE`
    1.  **string** *username*
    2.  **uint32** *token*
    3.  **string** *search query*


## Server Code 121

### SendUploadSpeed

We send this after a finished upload to let the server update the speed
statistics for ourselves.

### Data Order

  - Send
    1.  **uint32** *speed*
  - Receive
    -   *No Message*


## Server Code 122

### UserPrivileged

**DEPRECATED, use [WatchUser](#server-code-5) and [GetUserStatus](#server-code-7)
server messages**

We ask the server whether a user is privileged or not.

### Data Order

  - Send
    1.  **string** *username*
  - Receive
    1.  **string** *username*
    2.  **bool** *privileged*


## Server Code 123

### GivePrivileges

We give (part of) our privileges, specified in days, to another user on the
network.

### Data Order

  - Send
    1.  **string** *username*
    2.  **uint32** *days*
  - Receive
    -   *No Message*


## Server Code 124

### NotifyPrivileges

**DEPRECATED, sent by Soulseek NS but not SoulseekQt**

### Data Order

  - Send
    1.  **uint32** *token*
    2.  **string** *username*
  - Receive
    1.  **uint32** *token*
    2.  **string** *username*


## Server Code 125

### AckNotifyPrivileges

**DEPRECATED, no longer used**

### Data Order

  - Send
    1.  **uint32** *token*
  - Receive
    1.  **uint32** *token*


## Server Code 126

### BranchLevel

We tell the server what our position is in our branch (xth generation) on the
distributed network.

### Data Order

  - Send
    1.  **uint32** *branch level*
  - Receive
    -   *No Message*


## Server Code 127

### BranchRoot

We tell the server the username of the root of the branch we're in on the
distributed network.

### Data Order

  - Send
    1.  **string** *branch root*
  - Receive
    -   *No Message*


## Server Code 129

### ChildDepth

**DEPRECATED, sent by Soulseek NS but not SoulseekQt**

We tell the server the maximum number of generation of children we have on the
distributed network.

### Data Order

  - Send
    1.  **uint32** *child depth*
  - Receive
    -   *No Message*


## Server Code 130

### ResetDistributed

The server asks us to reset our distributed parent and children.

### Data Order

  - Send
    -   *No Message*
  - Receive
    -   Empty Message


## Server Code 133

### PrivateRoomUsers

The server sends us a list of members (excluding the owner) in a private
room we are in.

### Data Order

  - Send
    1.  *No Message*
  - Receive
    1.  **string** *room*
    2.  **uint32** *number of users*
    3.  Iterate for *number of users*
        1.  **string** *users*


## Server Code 134

### PrivateRoomAddUser

We send this to the server to add a member to a private room, if we are
the owner or an operator.

The server tells us a member has been added to a private room we are in.

### Data Order

  - Send
    1.  **string** *room*
    2.  **string** *username*
  - Receive
    1.  **string** *room*
    2.  **string** *username*


## Server Code 135

### PrivateRoomRemoveUser

We send this to the server to remove a member from a private room, if we
are the owner or an operator. Owners can remove operators and regular
members, operators can only remove regular members.

The server tells us a member has been removed from a private room we are in.

### Data Order

  - Send
    1.  **string** *room*
    2.  **string** *username*
  - Receive
    1.  **string** *room*
    2.  **string** *username*


## Server Code 136

### PrivateRoomCancelMembership

We send this to the server to cancel our own membership of a private room.

### Data Order

  - Send
    1.  **string** *room*
  - Receive
    -   *No Message*


## Server Code 137

### PrivateRoomDisown

We send this to the server to stop owning a private room.

### Data Order

  - Send
    1.  **string** *room*
  - Receive
    -   *No Message*


## Server Code 138

### PrivateRoomSomething

**OBSOLETE, no longer used**

Unknown purpose

### Data Order

  - Send
    1.  **string** *room*
  - Receive
    1.  **string** *room*


## Server Code 139

### PrivateRoomAdded

The server tells us we were added to a private room.

### Data Order

  - Send
    -   *No Message*
  - Receive
    1.  **string** *room*


## Server Code 140

### PrivateRoomRemoved

The server tells us we were removed from a private room.

### Data Order

  - Send
    -   *No Message*
  - Receive
    1.  **string** *room*


## Server Code 141

### PrivateRoomToggle

We send this when we want to enable or disable invitations to private rooms.

### Data Order

  - Send
    1.  **bool** *enable*
  - Receive
    1.  **bool** *enable*


## Server Code 142

### ChangePassword

We send this to the server to change our password. We receive a response if our
password changes.

### Data Order

  - Send
    1.  **string** *pass*
  - Receive
    1.  **string** *pass*


## Server Code 143

### PrivateRoomAddOperator

We send this to the server to add private room operator abilities to
a member.

The server tells us a member received operator abilities in a private
room we are in.

### Data Order

  - Send
    1.  **string** *room*
    2.  **string** *username*
  - Receive
    1.  **string** *room*
    2.  **string** *username*


## Server Code 144

### PrivateRoomRemoveOperator

We send this to the server to remove private room operator abilities
from a member.

The server tells us operator abilities were removed for a member in a
private room we are in.

### Data Order

  - Send
    1.  **string** *room*
    2.  **string** *username*
  - Receive
    1.  **string** *room*
    2.  **string** *username*


## Server Code 145

### PrivateRoomOperatorAdded

The server tells us we were given operator abilities in a private room
we are in.

### Data Order

  - Send
    -   *No Message*
  - Receive
    1.  **string** *room*


## Server Code 146

### PrivateRoomOperatorRemoved

The server tells us our operator abilities were removed in a private room
we are in.

### Data Order

  - Send
    -   *No Message*
  - Receive
    1.  **string** *room*


## Server Code 148

### PrivateRoomOperators

The server sends us a list of operators in a private room we are in.

### Data Order

  - Send
    -   *No Message*
  - Receive
    1.  **string** *room*
    2.  **uint32** *number of operators in room*
    3.  Iterate for *number of operators*
        1.  **string** *operator*


## Server Code 149

### MessageUsers

Sends a broadcast private message to the given list of online users.

### Data Order

  - Send
    1.  **uint32** *number of users*
    2.  Iterate for *number of users*
        1.  **string** *username*
    3.  **string** *message*
  - Receive
    -   *No Message*


## Server Code 150

### JoinGlobalRoom

**DEPRECATED, used in Soulseek NS but not SoulseekQt**

We ask the server to send us messages from all public rooms, also known as
public room feed.

### Data Order

  - Send
    -   Empty Message
  - Receive
    -   *No Message*


## Server Code 151

### LeaveGlobalRoom

**DEPRECATED, used in Soulseek NS but not SoulseekQt**

We ask the server to stop sending us messages from all public rooms, also known
as public room feed.

### Data Order

  - Send
    -   Empty Message
  - Receive
    -   *No Message*


## Server Code 152

### GlobalRoomMessage

**DEPRECATED, used in Soulseek NS but not SoulseekQt**

The server sends this when a new message has been written in the public room
feed (every single line written in every public room).

### Data Order

  - Send
    -   *No Message*
  - Receive
    1.  **string** *room*
    2.  **string** *username*
    3.  **string** *message*


## Server Code 153

### RelatedSearch

**OBSOLETE, server sends empty list as of 2018**

The server returns a list of related search terms for a search query.

### Data Order

  - Send
    1.  **string** *query*
  - Receive
    1.  **string** *query*
    2.  **uint32** *number of terms*
    3.  Iterate for *number of term*
        1.  **string** *term*
        2.  **uint32** *score*


## Server Code 160

### ExcludedSearchPhrases

The server sends a list of phrases not allowed on the search network. File
paths containing such phrases should be excluded when responding to search
requests.

### Data Order

  - Send
    -   *No Message*
  - Receive
    1.  **uint32** *number of phrases*
    2.  Iterate for *number of phrases*
        1.  **string** *phrase*


## Server Code 1001

### CantConnectToPeer

We send this when we are not able to respond to an indirect connection
request. We receive this if a peer was not able to respond to our
indirect connection request. The token is taken from the [ConnectToPeer](#server-code-18)
message.

Do not rely on receiving this message from peers. Keep a local timeout
for indirect connections as well.

See also: [Peer Connection Message Order](#modern-peer-connection-message-order)

### Data Order

  - Send
    1.  **uint32** *token*
    2.  **string** *username*
  - Receive
    1.  **uint32** *token*
    2.  **string** *username*


## Server Code 1003

### CantCreateRoom

Server tells us a new room cannot be created.

This message only seems to be sent if we try to create a room with the same
name as an existing private room. In other cases, such as using a room name
with leading or trailing spaces, only a private message containing an error
message is sent.

### Data Order

  - Send
    -   *No Message*
  - Receive
    1.  **string** *room*


# Peer Init Messages

Peer init messages are used to initiate a `P`, `F` or `D` connection (TCP) to
a peer. In Nicotine+, these messages are defined in slskmessages.py.


## Peer Init Message Format

| Message Length | Code  | Message Contents |
|----------------|-------|------------------|
| uint32         | uint8 | ...              |


## Peer Init Message Codes

| Code | Message                              |
|------|--------------------------------------|
| `0`  | [Pierce Firewall](#peer-init-code-0) |
| `1`  | [Peer Init](#peer-init-code-1)       |


## Modern Peer Connection Message Order

*Used by SoulseekQt, Nicotine+ 3.2.1 and later, Soulseek.NET-based clients
(slskd, Seeker)*

1.  User A sends [ConnectToPeer](#server-code-18) to the Server with a unique
    token (indirect connection request)
2.  User A sends a [PeerInit](#peer-init-code-1) to User B (direct connection
    request)
3.  The Server sends a [ConnectToPeer](#server-code-18) response to User B with
    the same token.  
    If User B receives the *PeerInit* message, a connection is established, and
    user A is free to send peer messages.  
    Otherwise, once User B receives the *ConnectToPeer* message from the
    Server, User B proceeds with step 4.
4.  User B sends a [PierceFireWall](#peer-init-code-0) to User A with the token
    included in the *ConnectToPeer* message.  
    If this succeeds, a connection is established, and User A is free to send
    peer messages.  
    If this fails, no connection is possible, and User B proceeds with step 5.
5.  User B sends a [CantConnectToPeer](#server-code-1001) to the Server.
6.  The Server sends a [CantConnectToPeer](#server-code-1001) response to
    User A.


## Legacy Peer Connection Message Order

*Used by Soulseek NS, Nicotine+ 3.2.0 and earlier (excluding step 5-7),
Museek+ (excluding step 7), soulseeX*

1.  User A sends a [PeerInit](#peer-init-code-1) to User B.  
    If this succeeds, a connection is established, and User A is free to send
    peer messages.  
    If this fails (socket cannot connect), User A proceeds with an indirect
    connection request (step 2).
2.  User A sends [ConnectToPeer](#server-code-18) to the Server with a unique
    token
3.  The Server sends a [ConnectToPeer](#server-code-18) response to User B with
    the same token
4.  User B sends a [PierceFireWall](#peer-init-code-0) to User A with the same
    token.  
    If this succeeds, a connection is established, and User A is free to send
    peer messages.  
    If this fails, no connection is possible, and User B proceeds with step 5.
5.  User B sends a [CantConnectToPeer](#server-code-1001) to the Server.
6.  The Server sends a [CantConnectToPeer](#server-code-1001) response to User A.
7.  After 20 seconds, user A retries an indirect connection request (step 2) up
    to three times before giving up.


## Peer Init Code 0

### PierceFireWall

This message is sent in response to an indirect connection request from another
user. If the message goes through to the user, the connection is ready. The
token is taken from the [ConnectToPeer](#server-code-18) server message.

See also: [Peer Connection Message Order](#modern-peer-connection-message-order)

### Data Order

  - Send
    1.  **uint32** *token*
  - Receive
    1.  **uint32** *token*


## Peer Init Code 1

### PeerInit

This message is sent to initiate a direct connection to another peer. The token
is apparently always 0 and ignored.

See also: [Peer Connection Message Order](#modern-peer-connection-message-order)

### Data Order

  - Send
    1.  **string** *own username*  
    2.  **string** *type*  
        See [Connection Types](#connection-types)
    3.  **uint32** *token*  
        Value is always `0`
  - Receive
    1.  **string** *remote username*
    2.  **string** *type*  
        See [Connection Types](#connection-types)
    3.  **uint32** *token*  
        Value is always `0`

# Peer Messages

Peer messages are sent to peers over a `P` connection (TCP). Only a single
active connection to a peer is allowed. In Nicotine+, these messages are
defined in slskmessages.py.


## Peer Message Format

| Message Length | Code   | Message Contents |
|----------------|--------|------------------|
| uint32         | uint32 | ...              |


## Peer Message Codes

| Code | Message                                                 |
|------|---------------------------------------------------------|
| `1`  | Private Message `OBSOLETE`                              |
| `4`  | [Shared File List Request](#peer-code-4)                |
| `5`  | [Shared File List Response](#peer-code-5)               |
| `8`  | [File Search Request](#peer-code-8) `OBSOLETE`          |
| `9`  | [File Search Response](#peer-code-9)                    |
| `10` | Room Invitation `OBSOLETE`                              |
| `14` | Cancelled Queued Transfer `OBSOLETE`                    |
| `15` | [User Info Request](#peer-code-15)                      |
| `16` | [User Info Response](#peer-code-16)                     |
| `33` | Send Connect Token `OBSOLETE`                           |
| `34` | Move Download To Top `OBSOLETE`                         |
| `36` | [Folder Contents Request](#peer-code-36)                |
| `37` | [Folder Contents Response](#peer-code-37)               |
| `40` | [Transfer Request](#peer-code-40)                       |
| `41` | [Download Response](#peer-code-41-a) `DEPRECATED`       |
| `41` | [Upload Response](#peer-code-41-b)                      |
| `42` | [Upload Placehold](#peer-code-42) `OBSOLETE`            |
| `43` | [Queue Upload](#peer-code-43)                           |
| `44` | [Place In Queue Response](#peer-code-44)                |
| `46` | [Upload Failed](#peer-code-46)                          |
| `47` | Exact File Search Request `OBSOLETE`                    |
| `48` | Queued Downloads `OBSOLETE`                             |
| `49` | Indirect File Search Request `OBSOLETE`                 |
| `50` | [Upload Denied](#peer-code-50)                          |
| `51` | [Place In Queue Request](#peer-code-51)                 |
| `52` | [Upload Queue Notification](#peer-code-52) `DEPRECATED` |


## Peer Code 4

### GetShareFileList

We send this to a peer to ask for a list of shared files.

### Data Order

  - Send
    -   Empty Message
  - Receive
    -   Empty Message


## Peer Code 5

### SharedFileListResponse

A peer responds with a list of shared files after we've sent a
[SharedFileListRequest](#peer-code-4).

### Data Order

  - Send
    1.  Iterate through shares database
        1.  **data**
    2. zlib compress
  - Receive
    1.  zlib decompress
    2.  **uint32** *number of directories*
    3.  Iterate *number of directories*
        1.  **string** *directory*
        2.  **uint32** *number of files*
        3.  Iterate *number of files*
            1.  **uint8** *code*  
                Value is always `1`
            2.  **string** *filename*
            3.  **unit64** *file size*
            4.  **string** *file extension*
            5.  **uint32** *number of attributes*
            6.  Iterate for *number of attributes*
                1.  **uint32** *attribute code*  
                    See [File Attribute Types](#file-attribute-types)
                2.  **uint32** *attribute value*
    4.  **uint32** *unknown*  
        Official clients always send a value of `0`
    5.  **uint32** *number of private directories*
    6.  Iterate *number of private directories*
        1.  **string** *directory*
        2.  **uint32** *number of files*
        3.  Iterate *number of files*
            1.  **uint8** *code*  
                Value is always `1`
            2.  **string** *filename*
            3.  **uint64** *file size*
            4.  **string** *file extension*
            5.  **uint32** *number of attributes*
            6.  Iterate for *number of attributes*
                1.  **uint32** *attribute code*  
                    See [File Attribute Types](#file-attribute-types)
                2.  **uint32** *attribute value*


## Peer Code 8

### FileSearchRequest

**OBSOLETE, use [UserSearch](#server-code-42) server message**

We send this to the peer when we search for a file. Alternatively, the peer
sends this to tell us it is searching for a file.

### Data Order

  - Send
    1.  **uint32** *token*
    2.  **string** *query*
  - Receive
    1.  **uint32** *token*
    2.  **string** *query*


## Peer Code 9

### FileSearchResponse

A peer sends this message when it has a file search match. The token is taken
from original [FileSearch](#server-code-26), [UserSearch](#server-code-42) or
[RoomSearch](#server-code-120) server message.

### Data Order

  - Send
    1.  **string** *username*
    2.  **uint32** *token*
    3.  **uint32** *number of results*
    4.  Iterate for *number of results*
        1.  **uint8** *code*  
            Value is always `1`
        2.  **string** *filename*
        3.  **uint64** *file size*
        4.  **string** *file extension*  
            SoulseekNS requires `mp3` to show attributes
        5.  **uint32** *number of attributes*
        6.  Iterate for *number of attributes*
            1.  **uint32** *attribute code*  
                See [File Attribute Types](#file-attribute-types)
            2.  **uint32** *attribute value*
    5.  **bool** *slotfree*
    6.  **uint32** *avgspeed*
    7.  **uint32** *queue length*
    8.  **uint32** *unknown*
        Official clients always send a value of `0`
    9.  **uint32** *number of privately shared results*
    10. Iterate for *number of privately shared results*
        1.  **uint8** *code*
            Value is always `1`
        2.  **string** *filename*
        3.  **uint64** *file size*
        4.  **string** *file extension*  
            SoulseekNS requires `mp3` to show attributes
        5.  **uint32** *number of attributes*
        6.  Iterate for *number of attributes*
            1.  **uint32** *attribute code*  
                See [File Attribute Types](#file-attribute-types)
            2.  **uint32** *attribute value*
    11. zlib compress
  - Receive
    1.  zlib decompress
    2.  **string** *username*
    3.  **uint32** *token*
    4.  **uint32** *number of results*
    5.  Iterate for *number of results*
        1.  **uint8** *code*
            Value is always `1`
        2.  **string** *filename*
        3.  **uint64** *file size*
        4.  **string** *file extension*  
            Always blank from SoulseekQt clients
        5.  **uint32** *number of attributes*
        6.  Iterate for *number of attributes*
            1.  **uint32** *attribute code*  
                See [File Attribute Types](#file-attribute-types)
            2.  **uint32** *attribute value*
    6.  **bool** *slotfree*
    7.  **uint32** *avgspeed*
    8.  **uint32** *queue length*
    9.  **uint32** *unknown*  
        Official clients always send a value of `0`
    10.  **uint32** *number of privately shared results*
    11.  Iterate for *number of privately shared results*
         1.  **uint8** *code*  
             Value is always `1`
         2.  **string** *filename*
         3.  **uint64** *file size*
         4.  **string** *file extension*  
             Always blank from SoulseekQt clients
         5.  **uint32** *number of attributes*
         6.  Iterate for *number of attributes*
             1.  **uint32** *attribute code*  
                 See [File Attribute Types](#file-attribute-types)
             2.  **uint32** *attribute value*


## Peer Code 15

### UserInfoRequest

We ask the other peer to send us their user information, picture and all.

### Data Order

  - Send
    -   Empty Message
  - Receive
    -   Empty Message


## Peer Code 16

### UserInfoResponse

A peer responds with this after we've sent a [UserInfoRequest](#peer-code-15).

### Data Order

  - Send
    1.  **string** *description*
    2.  If *picture* is not empty
        1.  **bool** *has picture* **True**
        2.  **bytes** *picture*
    3.  If *picture* is empty
        1.  **bool** *has picture* **False**
    4.  **uint32** *totalupl*
    5.  **uint32** *queuesize*
    6.  **bool** *slotsfree*  
        Can immediately upload
    7.  Optional (not sent by SoulseekQt)
        1.  **uint32** *uploadpermitted*  
            Who can upload anything to us? See [Upload Permissions](#upload-permissions).
  - Receive
    1.  **string** *description*
    2.  **bool** *has picture*
    3.  If has picture
        1.  **bytes** *picture*
    4.  **uint32** *totalupl*
    5.  **uint32** *queuesize*
    6.  **bool** *slotsfree*  
        Can immediately download
    7.  Optional (not sent by SoulseekQt)
        1.  **uint32** *uploadpermitted*  
            Who can upload anything to this user? See [Upload Permissions](#upload-permissions).


## Peer Code 36

### FolderContentsRequest

We ask the peer to send us the contents of a single folder.

### Data Order

  - Send
    1.  **uint32** *token*
    2.  **string** *folder*
  - Receive
    1.  **uint32** *token*
    2.  **string** *folder*


## Peer Code 37

### FolderContentsResponse

A peer responds with the contents of a particular folder (with all subfolders)
after we've sent a [FolderContentsRequest](#peer-code-36).

### Data Order

  - Send
    1.  **uint32** *token*
    2.  **string** *folder*
    3.  **uint32** *number of folders*
    4.  Iterate for *number of folders*
        1.  **string** *dir*
        2.  **uint32** *number of files*
        3.  Iterate *number of files*
            1.  **uint8** *code*
                Value is always `1`
            2.  **string** *file*
            3.  **uint64** *file size*
            4.  **string** *file extension*  
                Always blank from SoulseekQt clients
            5.  **uint32** *number of attributes*
            6.  Iterate for *number of attributes*
                1.  **uint32** *attribute code*  
                    See [File Attribute Types](#file-attribute-types)
                2.  **uint32** *attribute value*
    5.  zlib compress
  - Receive
    1.  zlib decompress
    2.  **uint32** *token*
    3.  **string** *folder*
    4.  **uint32** *number of folders*
    5.  Iterate for *number of folders*
        1.  **string** *dir*
        2.  **uint32** *number of files*
        3.  Iterate *number of files*
            1.  **uint8** *code*  
                Value is always `1`
            2.  **string** *file*
            3.  **uint64** *file size*
            4.  **string** *file extension*  
                Always blank from SoulseekQt clients
            5.  **uint32** *number of attributes*
            6.  Iterate for *number of attributes*
                1.  **uint32** *attribute code*  
                    See [File Attribute Types](#file-attribute-types)
                2.  **uint32** *attribute value*


## Peer Code 40

### TransferRequest

This message is sent by a peer once they are ready to start uploading a file to
us. A [TransferResponse](#peer-code-41-a) message is expected from the
recipient, either allowing or rejecting the upload attempt.

This message was formerly used to send a download request (direction 0) as
well, but Nicotine+ >= 3.0.3, Museek+ and the official clients use the
[QueueUpload](#peer-code-43) peer message for this purpose today.

### Data Order

  - Send
    1.  **uint32** *direction*  
        See [Transfer Directions](#transfer-directions)
    2.  **uint32** *token*
    3.  **string** *filename*
    4.  If direction == 1 (upload)
        1.  **uint64** *file size*
  - Receive
    1.  **uint32** *direction*  
        See [Transfer Directions](#transfer-directions)
    2.  **uint32** *token*
    3.  **string** *filename*
    4.  If direction == 1 (upload)
        1.  **uint64** *file size*


## Peer Code 41 a

### TransferResponse *Download Response*

**DEPRECATED, use [QueueUpload](#peer-code-43) to request files**

Response to [TransferRequest](#peer-code-40)

We (or the other peer) either agrees, or tells the reason for rejecting the
file download.

### Data Order

  - Send
    1.  **uint32** *token*
    2.  **bool** *allowed*
    3.  If allowed is true
        1.  **uint64** *file size*
    4.  If allowed is false
        1.  **string** *reason*  
            See [Transfer Rejection Reasons](#transfer-rejection-reasons)
  - Receive
    1.  **uint32** *token*
    2.  **bool** *allowed*
    3.  If allowed is true
        1.  **uint64** *file size*
    4.  If allowed is false
        1.  **string** *reason*  
            See [Transfer Rejection Reasons](#transfer-rejection-reasons)


## Peer Code 41 b

### TransferResponse *Upload Response*

Response to [TransferRequest](#peer-code-40)

We (or the other peer) either agrees, or tells the reason for rejecting the
file upload.

### Data Order

  - Send
    1.  **uint32** *token*
    2.  **bool** *allowed*
    3.  If allowed is false
        1.  **string** *reason*  
            See [Transfer Rejection Reasons](#transfer-rejection-reasons)
  - Receive
    1.  **uint32** *token*
    2.  **bool** *allowed*
    3.  If allowed is false
        1.  **string** *reason*  
            See [Transfer Rejection Reasons](#transfer-rejection-reasons)


## Peer Code 42

### PlaceholdUpload

**OBSOLETE, no longer used**

### Data Order

  - Send
    1.  **string** *filename*
  - Receive
    1.  **string** *filename*


## Peer Code 43

### QueueUpload

This message is used to tell a peer that an upload should be queued on their
end. Once the recipient is ready to transfer the requested file, they will
send a [TransferRequest](#peer-code-40) to us.

### Data Order

  - Send
    1.  **string** *filename*
  - Receive
    1.  **string** *filename*


## Peer Code 44

### PlaceInQueueResponse

The peer replies with the upload queue placement of the requested file.

### Data Order

  - Send
    1.  **string** *filename*
    2.  **uint32** *place*
  - Receive
    1.  **string** *filename*
    2.  **uint32** *place*


## Peer Code 46

### UploadFailed

This message is sent whenever a file connection of an active upload closes.
Soulseek NS clients can also send this message when a file cannot be read.
The recipient either re-queues the upload (download on their end), or ignores
the message if the transfer finished.

### Data Order

  - Send
    1.  **string** *filename*
  - Receive
    1.  **string** *filename*


## Peer Code 50

### UploadDenied

This message is sent to reject [QueueUpload](#peer-code-43) attempts and
previously queued files. The reason for rejection will appear in the transfer
list of the recipient.

### Data Order

  - Send
    1.  **string** *filename*
    2.  **string** *reason*  
        See [Transfer Rejection Reasons](#transfer-rejection-reasons)
  - Receive
    1.  **string** *filename*
    2.  **string** *reason*  
        See [Transfer Rejection Reasons](#transfer-rejection-reasons)


## Peer Code 51

### PlaceInQueueRequest

This message is sent when asking for the upload queue placement of a file.

### Data Order

  - Send
    1.  **string** *filename*
  - Receive
    1.  **string** *filename*


## Peer Code 52

### UploadQueueNotification

**DEPRECATED, sent by Soulseek NS but not SoulseekQt**

This message is sent to inform a peer about an upload attempt initiated by us.

### Data Order

  - Send
    -   Empty Message
  - Receive
    -   Empty Message


# File Messages

File messages are sent to peers over a `F` connection (TCP), and do not have
messages codes associated with them.


## File Connection Message Format

| Message Contents |
|------------------|
| ...              |


## File Connection Messages

| Message                                   |
|-------------------------------------------|
| [File Transfer Init](#file-transfer-init) |
| [File Offset](#file-offset)               |


## File Transfer Init

### FileTransferInit

We send this to a peer via a 'F' connection to tell them that we want to start
uploading a file. The token is the same as the one previously included in the
[TransferRequest](#peer-code-40) peer message.

Note that slskd and Nicotine+ <= 3.0.2 use legacy download requests, and send
this message when initializing our file upload connection from their end.

### Data Order

  - Send
    -   **uint32** *token*
  - Receive
    -   **uint32** *token*


## File Offset

### FileOffset

We send this to the uploading peer at the beginning of a 'F' connection, to
tell them how many bytes of the file we've previously downloaded. If nothing
was downloaded, the offset is 0.

Note that Soulseek NS fails to read the size of an incomplete download if more
than 2 GB of the file has been downloaded, and the download is resumed. In
consequence, the client sends an invalid file offset of -1.

### Data Order

  - Send
    -   **uint64** *offset*
  - Receive
    -   **uint64** *offset*


# Distributed Messages

Distributed messages are sent to peers over a `D` connection (TCP), and are
used for the distributed search network. Only a single active connection to a
peer is allowed. In Nicotine+, these messages are defined in slskmessages.py.


## Distributed Message Format

| Message Length | Code  | Message Contents |
|----------------|-------|------------------|
| uint32         | uint8 | ...              |


## Distributed Message Codes

| Code | Message                                               |
|------|-------------------------------------------------------|
| `0`  | [Ping](#distributed-code-0) `DEPRECATED`              |
| `3`  | [Search Request](#distributed-code-3)                 |
| `4`  | [Branch Level](#distributed-code-4)                   |
| `5`  | [Branch Root](#distributed-code-5)                    |
| `7`  | [Child Depth](#distributed-code-7) `DEPRECATED`       |
| `93` | [Embedded Message](#distributed-code-93)              |


## Distributed Code 0

### DistribPing

**DEPRECATED, sent by Soulseek NS but not SoulseekQt**

We ping distributed children every 60 seconds.

### Data Order

  - Send
    -   Empty Message
  - Receive
    -   Empty Message


## Distributed Code 3

### DistribSearch

Search request that arrives through the distributed network. We transmit the
search request to our child peers.

### Data Order

  - Send
    1.  **uint32** *unknown*
    2.  **string** *username*
    3.  **uint32** *token*
    4.  **string** *query*
  - Receive
    1.  **uint32** *unknown*
    2.  **string** *username*
    3.  **uint32** *token*
    4.  **string** *query*


## Distributed Code 4

### DistribBranchLevel

We tell our distributed children what our position is in our branch (xth
generation) on the distributed network.

If we receive a branch level of 0 from a parent, we should mark the parent as
our branch root, since they won't send a [DistribBranchRoot](#distributed-code-5)
message in this case.

### Data Order

  - Send
    1.  **int32** *branch level*
  - Receive
    1.  **int32** *branch level*


## Distributed Code 5

### DistribBranchRoot

We tell our distributed children the username of the root of the branch we're
in on the distributed network.

This message should not be sent when we're the branch root.

### Data Order

  - Send
    1.  **string** *branch root*
  - Receive
    1.  **string** *branch root*


## Distributed Code 7

### DistribChildDepth

**DEPRECATED, sent by Soulseek NS but not SoulseekQt**

We tell our distributed parent the maximum number of generation of children we
have on the distributed network.

### Data Order

  - Send
    1.  **uint32** *child depth*
  - Receive
    1.  **uint32** *child depth*


## Distributed Code 93

### DistribEmbeddedMessage

A branch root sends us an embedded distributed message. We unpack the
distributed message and distribute it to our child peers.

The only type of distributed message sent at present is [DistribSearch](#distributed-code-3)
(distributed code 3).

### Data Order

  - Send
    1.  **uint8** *distributed code*  
        See [Distributed Message Codes](#distributed-message-codes)
    2.  **bytes** *distributed message*  
        Raw message associated with distributed code
  - Receive
    1.  **uint8** *distributed code*  
        See [Distributed Message Codes](#distributed-message-codes)
    2.  **bytes** *distributed message*  
        Raw message associated with distributed code


# Credits

This documentation exists thanks to efforts from the following projects:

 - Nicotine+ (Hyriand, daelstorm, mathiascode)
 - slskd (jpdillingham)
 - Museek+ (lbponey)
 - SoleSeek (BriEnigma)
 - PySoulSeek (Alexander Kanavin)
