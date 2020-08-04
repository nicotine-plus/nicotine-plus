# COPYRIGHT (C) 2020 Nicotine+ Team
# COPYRIGHT (C) 2016-2017 Michael Labouebe <gfarmerfr@free.fr>
# COPYRIGHT (C) 2016 Mutnick <muhing@yahoo.com>
# COPYRIGHT (C) 2009-2011 Quinox <quinox@users.sf.net>
# COPYRIGHT (C) 2009 Daelstorm <daelstorm@gmail.com>
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

import os
import string
import sys
import taglib
import time
import _thread
from collections import defaultdict
from gettext import gettext as _

from gi.repository import GLib

from pynicotine import slskmessages
from pynicotine.logfacility import log
from pynicotine.slskmessages import NetworkIntType
from pynicotine.slskmessages import NetworkLongLongType
from pynicotine.utils import displayTraceback
from pynicotine.utils import GetUserDirectories


win32 = sys.platform.startswith("win")


class Shares:

    def __init__(self, np):
        self.np = np
        self.config = self.np.config
        self.queue = self.np.queue
        self.LogMessage = self.np.logMessage
        self.CompressedSharesBuddy = self.CompressedSharesNormal = None
        self.CompressShares("normal")
        self.CompressShares("buddy")
        self.requestedShares = {}
        self.newbuddyshares = self.newnormalshares = False
        self.translatepunctuation = str.maketrans(dict.fromkeys(string.punctuation, ' '))

    def real2virtual(self, path):
        for (virtual, real) in self._virtualmapping():
            if path == real:
                return virtual
            if path.startswith(real + os.sep):
                virtualpath = virtual + '\\' + path[len(real + os.sep):].replace(os.sep, '\\')
                return virtualpath
        return "__INTERNAL_ERROR__" + path

    def virtual2real(self, path):
        for (virtual, real) in self._virtualmapping():
            if path == virtual:
                return real
            if path.startswith(virtual + '\\'):
                realpath = real + path[len(virtual):].replace('\\', os.sep)
                return realpath
        return "__INTERNAL_ERROR__" + path

    def _virtualmapping(self):

        mapping = self.config.sections["transfers"]["shared"][:]

        if self.config.sections["transfers"]["enablebuddyshares"]:
            mapping += self.config.sections["transfers"]["buddyshared"]

        if self.config.sections["transfers"]["sharedownloaddir"]:
            mapping += [(_("Downloaded"), self.config.sections["transfers"]["downloaddir"])]

        return mapping

    def logMessage(self, message, debugLevel=0):
        if self.LogMessage is not None:
            GLib.idle_add(self.LogMessage, message, debugLevel)

    def sendNumSharedFoldersFiles(self):
        """
        Send number of files in buddy shares if only buddies can
        download, and buddy-shares are enabled.
        """

        conf = self.config.sections

        if conf["transfers"]["enablebuddyshares"] and conf["transfers"]["friendsonly"]:
            shared_db = "bsharedfiles"
            index_db = "bfileindex"
        else:
            shared_db = "sharedfiles"
            index_db = "fileindex"

        sharedfolders = len(conf["transfers"][shared_db])
        sharedfiles = len(conf["transfers"][index_db])

        self.queue.put(slskmessages.SharedFoldersFiles(sharedfolders, sharedfiles))

    def RebuildShares(self, msg):
        self._RescanShares(msg, "normal", rebuild=True)

    def RescanShares(self, msg, rebuild=False):
        self._RescanShares(msg, "normal", rebuild)

    def RebuildBuddyShares(self, msg):
        self._RescanShares(msg, "buddy", rebuild=True)

    def RescanBuddyShares(self, msg, rebuild=False):
        self._RescanShares(msg, "buddy", rebuild)

    def _RescanShares(self, msg, type, rebuild=False):

        if type == "normal":
            name = _("Shares")
            mtimes = self.config.sections["transfers"]["sharedmtimes"]
            files = self.config.sections["transfers"]["sharedfiles"]
            filesstreams = self.config.sections["transfers"]["sharedfilesstreams"]
        else:
            name = _("Buddy Shares")
            mtimes = self.config.sections["transfers"]["bsharedmtimes"]
            files = self.config.sections["transfers"]["bsharedfiles"]
            filesstreams = self.config.sections["transfers"]["bsharedfilesstreams"]

        try:
            files, streams, wordindex, fileindex, mtimes = self.rescandirs(
                msg.shared,
                mtimes,
                files,
                filesstreams,
                msg.yieldfunction,
                self.np.frame.SharesProgress,
                name=name,
                rebuild=rebuild
            )

            self.np.frame.RescanFinished(
                files, streams, wordindex, fileindex, mtimes,
                type
            )
        except Exception as ex:
            config_dir, data_dir = GetUserDirectories()
            log.addwarning(
                _("Failed to rebuild share, serious error occurred. If this problem persists delete %s/*.db and try again. If that doesn't help please file a bug report with the stack trace included (see terminal output after this message). Technical details: %s") % (data_dir, ex)
            )
            raise

    def CompressShares(self, sharestype):

        if sharestype == "normal":
            streams = self.config.sections["transfers"]["sharedfilesstreams"]
        elif sharestype == "buddy":
            streams = self.config.sections["transfers"]["bsharedfilesstreams"]

        if streams is None:
            message = _("ERROR: No %(type)s shares database available") % {"type": sharestype}
            print(message)
            self.logMessage(message, None)
            return

        m = slskmessages.SharedFileList(None, streams)
        _thread.start_new_thread(m.makeNetworkMessage, (0, True))

        if sharestype == "normal":
            self.CompressedSharesNormal = m
        elif sharestype == "buddy":
            self.CompressedSharesBuddy = m

    def GetSharedFileList(self, msg):

        self.logMessage("%s %s" % (msg.__class__, vars(msg)), 4)
        user = ip = port = None

        # Get peer's username, ip and port
        for i in self.np.peerconns:
            if i.conn is msg.conn.conn:
                user = i.username
                if i.addr is not None:
                    if len(i.addr) != 2:
                        break
                    ip, port = i.addr
                break

        if user is None:
            # No peer connection
            return

        requestTime = time.time()
        if user in self.requestedShares:
            if not requestTime > 10 + self.requestedShares[user]:
                # Ignoring request, because it's 10 or less seconds since the
                # last one by this user
                return
        self.requestedShares[user] = requestTime

        # Check address is spoofed, if possible
        # if self.CheckSpoof(user, ip, port):
        #     # Message IS spoofed
        #     return
        if user == self.config.sections["server"]["login"]:
            if ip is not None and port is not None:
                self.logMessage(
                    _("%(user)s is making a BrowseShares request, blocking possible spoofing attempt from IP %(ip)s port %(port)s") % {
                        'user': user,
                        'ip': ip,
                        'port': port
                    }, 1)
            else:
                self.logMessage(
                    _("%(user)s is making a BrowseShares request, blocking possible spoofing attempt from an unknown IP & port") % {
                        'user': user
                    }, None)

            if msg.conn.conn is not None:
                self.queue.put(slskmessages.ConnClose(msg.conn.conn))
            return

        self.logMessage(_("%(user)s is making a BrowseShares request") % {
            'user': user
        }, 1)

        addr = msg.conn.addr[0]
        checkuser, reason = self.np.CheckUser(user, addr)

        if checkuser == 1:
            # Send Normal Shares
            if self.newnormalshares:
                self.CompressShares("normal")
                self.newnormalshares = False
            m = self.CompressedSharesNormal

        elif checkuser == 2:
            # Send Buddy Shares
            if self.newbuddyshares:
                self.CompressShares("buddy")
                self.newbuddyshares = False
            m = self.CompressedSharesBuddy

        else:
            # Nyah, Nyah
            m = slskmessages.SharedFileList(msg.conn.conn, {})
            m.makeNetworkMessage(nozlib=0)

        m.conn = msg.conn.conn
        self.queue.put(m)

    def FolderContentsRequest(self, msg):

        username = None
        checkuser = None
        reason = ""

        for i in self.np.peerconns:
            if i.conn is msg.conn.conn:
                username = i.username
                checkuser, reason = self.np.CheckUser(username, None)
                break

        if not username:
            return
        if not checkuser:
            self.queue.put(slskmessages.MessageUser(username, "[Automatic Message] " + reason))
            return

        if checkuser == 1:
            shares = self.config.sections["transfers"]["sharedfiles"]
        elif checkuser == 2:
            shares = self.config.sections["transfers"]["bsharedfiles"]
        else:
            self.queue.put(slskmessages.TransferResponse(msg.conn.conn, 0, reason=reason, req=0))
            shares = {}

        if checkuser:
            if msg.dir in shares:
                self.queue.put(slskmessages.FolderContentsResponse(msg.conn.conn, msg.dir, shares[msg.dir]))
            elif msg.dir.rstrip('\\') in shares:
                self.queue.put(slskmessages.FolderContentsResponse(msg.conn.conn, msg.dir, shares[msg.dir.rstrip('\\')]))
            else:
                if checkuser == 2:
                    shares = self.config.sections["transfers"]["sharedfiles"]
                    if msg.dir in shares:
                        self.queue.put(slskmessages.FolderContentsResponse(msg.conn.conn, msg.dir, shares[msg.dir]))
                    elif msg.dir.rstrip("\\") in shares:
                        self.queue.put(slskmessages.FolderContentsResponse(msg.conn.conn, msg.dir, shares[msg.dir.rstrip("\\")]))

        self.logMessage("%s %s" % (msg.__class__, vars(msg)), 4)

    def processSearchRequest(self, searchterm, user, searchid, direct=0):

        if not self.config.sections["searches"]["search_results"]:
            # Don't return _any_ results when this option is disabled
            return

        if searchterm is None:
            return

        if user == self.config.sections["server"]["login"]:
            # We shouldn't send a search response if we initiated the search request
            return

        checkuser, reason = self.np.CheckUser(user, None)
        if not checkuser:
            return

        if reason == "geoip":
            geoip = 1
        else:
            geoip = 0

        maxresults = self.config.sections["searches"]["maxresults"]

        if checkuser == 2:
            wordindex = self.config.sections["transfers"]["bwordindex"]
            fileindex = self.config.sections["transfers"]["bfileindex"]
        else:
            wordindex = self.config.sections["transfers"]["wordindex"]
            fileindex = self.config.sections["transfers"]["fileindex"]

        fifoqueue = self.config.sections["transfers"]["fifoqueue"]

        if maxresults == 0:
            return

        terms = searchterm.translate(self.translatepunctuation).lower().split()

        try:
            list = [wordindex[i][:] for i in terms if i in wordindex]
        except ValueError:
            # Shelf is probably closed, perhaps when rescanning share
            return

        if len(list) != len(terms) or len(list) == 0:
            return

        min = list[0]

        for i in list[1:]:
            if len(i) < len(min):
                min = i

        list.remove(min)

        for i in min[:]:
            for j in list:
                if i not in j:
                    min.remove(i)
                    break

        results = min[:maxresults]

        if len(results) > 0 and self.np.transfers is not None:

            queuesizes = self.np.transfers.getUploadQueueSizes()
            slotsavail = self.np.transfers.allowNewUploads()

            if len(results) > 0:

                message = slskmessages.FileSearchResult(
                    None,
                    self.config.sections["server"]["login"],
                    geoip, searchid, results, fileindex, slotsavail,
                    self.np.speed, queuesizes, fifoqueue
                )

                self.np.ProcessRequestToPeer(user, message)

                if direct:
                    self.logMessage(
                        _("User %(user)s is directly searching for %(query)s, returning %(num)i results") % {
                            'user': user,
                            'query': searchterm,
                            'num': len(results)
                        }, 2)
                else:
                    self.logMessage(
                        _("User %(user)s is searching for %(query)s, returning %(num)i results") % {
                            'user': user,
                            'query': searchterm,
                            'num': len(results)
                        }, 2)

    # Rescan directories in shared databases
    def rescandirs(self, shared, oldmtimes, oldfiles, sharedfilesstreams, yieldfunction, progress=None, name="", rebuild=False):
        """
        Check for modified or new files via OS's last mtime on a directory,
        or, if rebuild is True, all directories
        """

        GLib.idle_add(progress.set_fraction, 0.0)
        GLib.idle_add(progress.show)

        # returns dict in format:  { Directory : mtime, ... }
        shared_directories = [x[1] for x in shared]

        self.logMessage(_("%(num)s directories found before rescan, rebuilding...") % {"num": len(oldmtimes)})

        newmtimes = self.getDirsMtimes(shared_directories, yieldfunction)

        # Get list of files
        # returns dict in format { Directory : { File : metadata, ... }, ... }
        newsharedfiles = self.getFilesList(newmtimes, oldmtimes, oldfiles, yieldfunction, progress, rebuild)

        # Pack shares data
        # returns dict in format { Directory : hex string of files+metadata, ... }
        newsharedfilesstreams = self.getFilesStreams(newmtimes, oldmtimes, sharedfilesstreams, newsharedfiles, rebuild, yieldfunction)

        # Update Search Index
        # newwordindex is a dict in format {word: [num, num, ..], ... } with num matching
        # keys in newfileindex
        # newfileindex is a dict in format { num: (path, size, (bitrate, vbr), length), ... }
        newwordindex, newfileindex = self.getFilesIndex(newmtimes, oldmtimes, newsharedfiles, yieldfunction, progress)

        self.logMessage(_("%(num)s directories found after rescan") % {"num": len(newmtimes)})

        return newsharedfiles, newsharedfilesstreams, newwordindex, newfileindex, newmtimes

    # Get Modification Times
    def getDirsMtimes(self, dirs, yieldcall=None):

        list = {}

        for folder in dirs:

            try:
                if self.hiddenCheck({'dir': folder}):
                    continue

                mtime = os.path.getmtime(folder)
                list[folder] = mtime

                for entry in os.scandir(folder):
                    if entry.is_dir():

                        path = entry.path

                        try:
                            mtime = entry.stat().st_mtime
                        except OSError as errtuple:
                            message = _("Scanning Error: %(error)s Path: %(path)s") % {
                                'error': errtuple,
                                'path': path
                            }

                            print(str(message))
                            self.logMessage(message)
                            continue

                        list[path] = mtime
                        dircontents = self.getDirsMtimes([path])
                        for k in dircontents:
                            list[k] = dircontents[k]

                    if yieldcall is not None:
                        yieldcall()
            except OSError as errtuple:
                message = _("Scanning Directory Error: %(error)s Path: %(path)s") % {'error': errtuple, 'path': folder}
                print(str(message))
                self.logMessage(message)
                continue

        return list

    # Check for new files
    def getFilesList(self, mtimes, oldmtimes, oldlist, yieldcall=None, progress=None, rebuild=False):
        """ Get a list of files with their filelength, bitrate and track length in seconds """

        list = {}
        count = 0
        lastpercent = 0.0

        for folder in mtimes:

            try:
                count += 1

                if progress:
                    # Truncate the percentage to two decimal places to avoid sending data to the GUI thread too often
                    percent = float("%.2f" % (float(count) / len(mtimes) * 0.75))

                    if percent > lastpercent and percent <= 1.0:
                        GLib.idle_add(progress.set_fraction, percent)
                        lastpercent = percent

                if self.hiddenCheck({'dir': folder}):
                    continue

                if not rebuild and folder in oldmtimes:
                    if mtimes[folder] == oldmtimes[folder]:
                        if os.path.exists(folder):
                            try:
                                virtualdir = self.real2virtual(folder)
                                list[virtualdir] = oldlist[virtualdir]
                                continue
                            except KeyError:
                                log.adddebug(_("Inconsistent cache for '%(vdir)s', rebuilding '%(dir)s'") % {
                                    'vdir': virtualdir,
                                    'dir': folder
                                })
                        else:
                            log.adddebug(_("Dropping missing directory %(dir)s") % {'dir': folder})
                            continue

                virtualdir = self.real2virtual(folder)
                list[virtualdir] = []

                for entry in os.scandir(folder):

                    if entry.is_file():
                        filename = entry.name

                        if self.hiddenCheck({'dir': folder, 'file': filename}):
                            continue

                        # Get the metadata of the file
                        data = self.getFileInfo(filename, entry.path)
                        if data is not None:
                            list[virtualdir].append(data)

                    if yieldcall is not None:
                        yieldcall()
            except OSError as errtuple:
                message = _("Scanning Directory Error: %(error)s Path: %(path)s") % {'error': errtuple, 'path': folder}
                print(str(message))
                self.logMessage(message)
                continue

        return list

    # Get metadata via taglib
    def getFileInfo(self, name, pathname):

        try:
            audio = None
            size = os.stat(pathname).st_size

            if size > 0:
                try:
                    audio = taglib.File(pathname)
                except IOError:
                    pass

            if audio is not None:
                # TODO: Variable bitrate is always set to false now, perhaps detect it somehow
                vbr = False
                bitrateinfo = (int(audio.bitrate), int(vbr))
                fileinfo = (name, size, bitrateinfo, int(audio.length))
            else:
                fileinfo = (name, size, None, None)

            return fileinfo

        except Exception as errtuple:
            message = _("Scanning File Error: %(error)s Path: %(path)s") % {'error': errtuple, 'path': pathname}
            self.logMessage(message)
            displayTraceback(sys.exc_info()[2])

    # Get streams of files
    def getFilesStreams(self, mtimes, oldmtimes, oldstreams, newsharedfiles, rebuild=False, yieldcall=None):

        streams = {}

        for folder in mtimes:

            virtualdir = self.real2virtual(folder)

            if self.hiddenCheck({'dir': folder}):
                continue

            if not rebuild and folder in oldmtimes:
                if mtimes[folder] == oldmtimes[folder]:
                    if os.path.exists(folder):
                        # No change
                        try:
                            streams[virtualdir] = oldstreams[virtualdir]
                            continue
                        except KeyError:
                            log.addwarning(_("Inconsistent cache for '%(vdir)s', rebuilding '%(dir)s'") % {
                                'vdir': virtualdir,
                                'dir': folder
                            })
                    else:
                        log.adddebug(_("Dropping missing directory %(dir)s") % {'dir': folder})
                        continue

            streams[virtualdir] = self.getDirStream(newsharedfiles[virtualdir])

            if yieldcall is not None:
                yieldcall()

        return streams

    # Stop sharing any dot/hidden directories/files
    def hiddenCheck(self, stuff):

        subdirs = stuff['dir'].split(os.sep)

        # If any part of the directory structure start with a dot we exclude it
        for part in subdirs:
            if part.startswith("."):
                return True

        # If we're asked to check a file we exclude it if it start with a dot
        if 'file' in stuff and stuff['file'].startswith("."):
            return True

        # On Windows check the directories attributes if the win32file module is available
        if win32:

            try:
                from win32file import GetFileAttributes
            except ImportError:
                pass
            else:

                if 'file' in stuff:
                    # If it's a file it must contain the fully qualified path
                    path = os.path.join(stuff['dir'], stuff['file']).replace('\\', '\\\\')
                else:
                    path = stuff['dir'].replace('\\', '\\\\')

                attrs = GetFileAttributes(str(path))

                # Set a mask to check the 2nd bit
                # See https://msdn.microsoft.com/en-us/library/windows/desktop/gg258117(v=vs.85).aspx
                # FILE_ATTRIBUTE_HIDDEN
                # 2 (0x2)
                mask = 1 << 1

                if attrs & mask:
                    return True

        return False

    # Pack all files and metadata in directory
    def getDirStream(self, dir):

        stream = bytearray()
        stream.extend(slskmessages.SlskMessage().packObject(NetworkIntType(len(dir))))

        for file_and_meta in dir:
            stream.extend(self.getByteStream(file_and_meta))

        return stream

    # Pack a file's metadata
    def getByteStream(self, fileinfo):

        message = slskmessages.SlskMessage()

        stream = bytearray()
        stream.extend(bytes([1]) + message.packObject(fileinfo[0]) + message.packObject(NetworkLongLongType(fileinfo[1])))
        if fileinfo[2] is not None:
            try:
                msgbytes = bytearray()
                msgbytes.extend(message.packObject('mp3') + message.packObject(3))
                msgbytes.extend(
                    message.packObject(0) +
                    message.packObject(NetworkIntType(fileinfo[2][0])) +
                    message.packObject(1) +
                    message.packObject(NetworkIntType(fileinfo[3])) +
                    message.packObject(2) +
                    message.packObject(NetworkIntType(fileinfo[2][1]))
                )
                stream.extend(msgbytes)
            except Exception:
                log.addwarning(_("Found meta data that couldn't be encoded, possible corrupt file: '%(file)s' has a bitrate of %(bitrate)s kbs, a length of %(length)s seconds and a VBR of %(vbr)s" % {
                    'file': fileinfo[0],
                    'bitrate': fileinfo[2][0],
                    'length': fileinfo[3],
                    'vbr': fileinfo[2][1]
                }))
                stream.extend(message.packObject('') + message.packObject(0))
        else:
            stream.extend(message.packObject('') + message.packObject(0))

        return stream

    # Update Search index with new files
    def getFilesIndex(self, mtimes, oldmtimes, newsharedfiles, yieldcall=None, progress=None):

        wordindex = defaultdict(list)
        fileindex = []
        index = 0
        count = len(mtimes)
        lastpercent = 0.0

        for directory in mtimes:

            virtualdir = self.real2virtual(directory)
            count += 1

            if progress:
                # Truncate the percentage to two decimal places to avoid sending data to the GUI thread too often
                percent = float("%.2f" % (float(count) / len(mtimes) * 0.75))

                if percent > lastpercent and percent <= 1.0:
                    GLib.idle_add(progress.set_fraction, percent)
                    lastpercent = percent

            if self.hiddenCheck({'dir': directory}):
                continue

            for j in newsharedfiles[virtualdir]:
                file = j[0]
                fileindex.append((virtualdir + '\\' + file,) + j[1:])

                # Collect words from filenames for Search index (prevent duplicates with set)
                words = set((virtualdir + " " + file).translate(self.translatepunctuation).lower().split())

                for k in words:
                    wordindex[k].append(index)

                index += 1

            if yieldcall is not None:
                yieldcall()

        return wordindex, fileindex

    def addToShared(self, name):
        """ Add a file to the normal shares database """

        config = self.config.sections
        if not config["transfers"]["sharedownloaddir"]:
            return

        shared = config["transfers"]["sharedfiles"]
        sharedstreams = config["transfers"]["sharedfilesstreams"]
        wordindex = config["transfers"]["wordindex"]
        fileindex = config["transfers"]["fileindex"]

        shareddirs = [path for _name, path in config["transfers"]["shared"]]
        shareddirs.append(config["transfers"]["downloaddir"])

        sharedmtimes = config["transfers"]["sharedmtimes"]

        dir = str(os.path.expanduser(os.path.dirname(name)))
        vdir = self.real2virtual(dir)
        file = str(os.path.basename(name))

        shared[vdir] = shared.get(vdir, [])

        if file not in [i[0] for i in shared[vdir]]:
            fileinfo = self.getFileInfo(file, name)
            shared[vdir] = shared[vdir] + [fileinfo]
            sharedstreams[vdir] = self.getDirStream(shared[vdir])
            words = self.getIndexWords(vdir, file, shareddirs)
            self.addToIndex(wordindex, fileindex, words, vdir, fileinfo)
            sharedmtimes[vdir] = os.path.getmtime(dir)
            self.newnormalshares = True

        if config["transfers"]["enablebuddyshares"]:
            self.addToBuddyShared(name)

    def addToBuddyShared(self, name):
        """ Add a file to the buddy shares database """

        config = self.config.sections
        if not config["transfers"]["sharedownloaddir"]:
            return

        bshared = config["transfers"]["bsharedfiles"]
        bsharedstreams = config["transfers"]["bsharedfilesstreams"]
        bwordindex = config["transfers"]["bwordindex"]
        bfileindex = config["transfers"]["bfileindex"]

        bshareddirs = [path for _name, path in config["transfers"]["shared"]]
        bshareddirs += [path for _name, path in config["transfers"]["buddyshared"]]
        bshareddirs.append(config["transfers"]["downloaddir"])

        bsharedmtimes = config["transfers"]["bsharedmtimes"]

        dir = str(os.path.expanduser(os.path.dirname(name)))
        vdir = self.real2virtual(dir)
        file = str(os.path.basename(name))

        bshared[vdir] = bshared.get(vdir, [])

        if file not in [i[0] for i in bshared[vdir]]:
            fileinfo = self.getFileInfo(file, name)
            bshared[vdir] = bshared[vdir] + [fileinfo]
            bsharedstreams[vdir] = self.getDirStream(bshared[vdir])
            words = self.getIndexWords(vdir, file, bshareddirs)
            self.addToIndex(bwordindex, bfileindex, words, vdir, fileinfo)
            bsharedmtimes[vdir] = os.path.getmtime(dir)
            self.newbuddyshares = True

    def addToIndex(self, wordindex, fileindex, words, dir, fileinfo):
        index = len(fileindex)
        for i in words:
            if i not in wordindex:
                wordindex[i] = [index]
            else:
                wordindex[i] = wordindex[i] + [index]
        fileindex.append((os.path.join(dir, fileinfo[0]),) + fileinfo[1:])
