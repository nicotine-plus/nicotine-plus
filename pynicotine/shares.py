# -*- coding: utf-8 -*-
#
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
import time
from gettext import gettext as _

import gi
from gi.repository import GObject as gobject

from pynicotine import metadata_mutagen as metadata
from pynicotine import slskmessages
from pynicotine.logfacility import log
from pynicotine.slskmessages import NetworkIntType
from pynicotine.slskmessages import NetworkLongLongType
from pynicotine.utils import displayTraceback

gi.require_version('Gtk', '3.0')


win32 = sys.platform.startswith("win")


class dircache:
    """Adapted from https://raw.githubusercontent.com/python/cpython/2.7/Lib/dircache.py"""

    cache = {}

    @classmethod
    def listdir(cls, path):
        try:
            cached_mtime, dir_list = cls.cache[path]
            del cls.cache[path]
        except KeyError:
            cached_mtime, dir_list = -1, []
        mtime = os.stat(path).st_mtime
        if mtime != cached_mtime:
            dir_list = os.listdir(path)
            dir_list.sort()
        cls.cache[path] = mtime, dir_list
        return dir_list


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
        self.translatepunctuation = str.maketrans(
            string.punctuation,
            ''.join([' ' for i in string.punctuation])
        )

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
            gobject.idle_add(self.LogMessage, message, debugLevel)

    def sendNumSharedFoldersFiles(self):
        """
        Send number of files in buddy shares if only buddies can
        download, and buddy-shares are enabled.
        """
        conf = self.config.sections

        if conf["transfers"]["enablebuddyshares"] and conf["transfers"]["friendsonly"]:
            shared_db = "bsharedfiles"
        else:
            shared_db = "sharedfiles"

        sharedfolders = len(conf["transfers"][shared_db])
        sharedfiles = sum([len(x) for x in list(conf["transfers"][shared_db].values())])
        self.queue.put(slskmessages.SharedFoldersFiles(sharedfolders, sharedfiles))

    def RebuildShares(self, msg):
        self.RescanShares(msg, rebuild=True)

    def RescanShares(self, msg, rebuild=False):

        try:
            files, streams, wordindex, fileindex, mtimes = self.rescandirs(
                msg.shared,
                self.config.sections["transfers"]["sharedmtimes"],
                self.config.sections["transfers"]["sharedfiles"],
                self.config.sections["transfers"]["sharedfilesstreams"],
                msg.yieldfunction,
                self.np.frame.SharesProgress,
                name=_("Shares"),
                rebuild=rebuild
            )

            time.sleep(0.5)

            self.np.frame.RescanFinished(
                [files, streams, wordindex, fileindex, mtimes],
                "normal"
            )
        except Exception as ex:
            log.addwarning(
                _("Failed to rebuild share, serious error occurred. If this problem persists delete %s/*.db and try again. If that doesn't help please file a bug report with the stack trace included (see terminal output after this message). Technical details: %s") % (self.config.sections["data"]["dir"], ex)
            )
            raise

    def RebuildBuddyShares(self, msg):
        self.RescanBuddyShares(msg, rebuild=True)

    def RescanBuddyShares(self, msg, rebuild=False):

        files, streams, wordindex, fileindex, mtimes = self.rescandirs(
            msg.shared,
            self.config.sections["transfers"]["bsharedmtimes"],
            self.config.sections["transfers"]["bsharedfiles"],
            self.config.sections["transfers"]["bsharedfilesstreams"],
            msg.yieldfunction,
            self.np.frame.BuddySharesProgress,
            name=_("Buddy Shares"),
            rebuild=rebuild
        )

        time.sleep(0.5)

        self.np.frame.RescanFinished(
            [files, streams, wordindex, fileindex, mtimes],
            "buddy"
        )

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
        m.makeNetworkMessage(nozlib=0, rebuild=True)

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
            response = self.queue.put(slskmessages.TransferResponse(msg.conn.conn, 0, reason=reason, req=0))  # noqa: F841
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

    def processExactSearchRequest(self, searchterm, user, searchid, direct=0, checksum=None):
        print(searchterm, user, searchid, checksum)
        pass

    def processSearchRequest(self, searchterm, user, searchid, direct=0):

        if not self.config.sections["searches"]["search_results"]:
            # Don't return _any_ results when this option is disabled
            return

        if searchterm is None:
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
        list = [wordindex[i][:] for i in terms if i in wordindex]

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
                            'query': self.np.decode(searchterm),
                            'num': len(results)
                        }, 2)
                else:
                    self.logMessage(
                        _("User %(user)s is searching for %(query)s, returning %(num)i results") % {
                            'user': user,
                            'query': self.np.decode(searchterm),
                            'num': len(results)
                        }, 2)

    # Rescan directories in shared databases
    def rescandirs(self, shared, oldmtimes, oldfiles, sharedfilesstreams, yieldfunction, progress=None, name="", rebuild=False):
        """
        Check for modified or new files via OS's last mtime on a directory,
        or, if rebuild is True, all directories
        """

        # returns dict in format:  { Directory : mtime, ... }
        shared_directories = [x[1] for x in shared]

        gobject.idle_add(progress.set_text, _("Checking for changes"))
        gobject.idle_add(progress.show)
        gobject.idle_add(progress.set_fraction, 0)

        self.logMessage(_("%(num)s directories found before rescan/rebuild") % {"num": len(oldmtimes)})

        if win32:
            newmtimes = self.getDirsMtimesUnicode(shared_directories, yieldfunction)
        else:
            newmtimes = self.getDirsMtimes(shared_directories, yieldfunction)

        self.logMessage(_("%(num)s directories found after rescan/rebuild") % {"num": len(newmtimes)})

        gobject.idle_add(progress.set_text, _("Scanning %s") % name)

        # Get list of files
        # returns dict in format { Directory : { File : metadata, ... }, ... }
        if win32:
            newsharedfiles = self.getFilesListUnicode(newmtimes, oldmtimes, oldfiles, yieldfunction, progress, rebuild)
        else:
            newsharedfiles = self.getFilesList(newmtimes, oldmtimes, oldfiles, yieldfunction, progress, rebuild)

        # Pack shares data
        # returns dict in format { Directory : hex string of files+metadata, ... }
        gobject.idle_add(progress.set_text, _("Building DataBase"))

        if win32:
            newsharedfilesstreams = self.getFilesStreamsUnicode(newmtimes, oldmtimes, sharedfilesstreams, newsharedfiles, rebuild, yieldfunction)
        else:
            newsharedfilesstreams = self.getFilesStreams(newmtimes, oldmtimes, sharedfilesstreams, newsharedfiles, rebuild, yieldfunction)

        # Update Search Index
        # newwordindex is a dict in format {word: [num, num, ..], ... } with num matching
        # keys in newfileindex
        # newfileindex is a dict in format { num: (path, size, (bitrate, vbr), length), ... }
        gobject.idle_add(progress.set_text, _("Building Index"))

        gobject.idle_add(progress.set_fraction, 0.0)

        newwordindex, newfileindex = self.getFilesIndex(newmtimes, oldmtimes, shared_directories, newsharedfiles, yieldfunction, progress)

        gobject.idle_add(progress.set_fraction, 1.0)

        return newsharedfiles, newsharedfilesstreams, newwordindex, newfileindex, newmtimes

    # Get Modification Times on Unix
    def getDirsMtimes(self, dirs, yieldcall=None):

        list = {}

        for directory in dirs:

            directory = os.path.expanduser(directory.replace("//", "/"))

            if self.hiddenCheck({'dir': directory}):
                continue

            try:
                contents = dircache.listdir(directory)
                mtime = os.path.getmtime(directory)
            except OSError as errtuple:
                message = _("Scanning Directory Error: %(error)s Path: %(path)s") % {'error': errtuple, 'path': directory}
                print(str(message))
                self.logMessage(message)
                displayTraceback(sys.exc_info()[2])
                continue

            contents.sort()

            list[directory] = mtime

            for filename in contents:

                path = os.path.join(directory, filename)

                try:
                    isdir = os.path.isdir(path)
                except OSError as errtuple:
                    message = _("Scanning Error: %(error)s Path: %(path)s") % {'error': errtuple, 'path': path}
                    print(str(message))
                    self.logMessage(message)
                    continue

                try:
                    mtime = os.path.getmtime(path)
                except OSError as errtuple:
                    islink = False
                    try:
                        islink = os.path.islink(path)
                    except OSError as errtuple2:
                        print(errtuple2)

                    if islink:
                        message = _("Scanning Error: Broken link to directory: \"%(link)s\" from Path: \"%(path)s\". Repair or remove this link.") % {
                            'link': os.readlink(path),
                            'path': path
                        }
                    else:
                        message = _("Scanning Error: %(error)s Path: %(path)s") % {
                            'error': errtuple,
                            'path': path
                        }

                    print(str(message))
                    self.logMessage(message)
                    continue
                else:
                    if isdir:
                        list[path] = mtime
                        dircontents = self.getDirsMtimes([path])
                        for k in dircontents:
                            list[k] = dircontents[k]

                    if yieldcall is not None:
                        yieldcall()

        return list

    # Check for new files on Unix
    def getFilesList(self, mtimes, oldmtimes, oldlist, yieldcall=None, progress=None, rebuild=False):
        """ Get a list of files with their filelength, bitrate and track length in seconds """

        list = {}
        count = 0

        for directory in mtimes:

            directory = os.path.expanduser(directory)
            virtualdir = self.real2virtual(directory)
            count += 1

            if progress:
                percent = float(count) / len(mtimes)
                if percent <= 1.0:
                    gobject.idle_add(progress.set_fraction, percent)

            if self.hiddenCheck({'dir': directory}):
                continue

            if not rebuild and directory in oldmtimes:
                if mtimes[directory] == oldmtimes[directory]:
                    if os.path.exists(directory):
                        try:
                            list[virtualdir] = oldlist[virtualdir]
                            continue
                        except KeyError:
                            log.addwarning(_("Inconsistent cache for '%(vdir)s', rebuilding '%(dir)s'") % {
                                'vdir': virtualdir,
                                'dir': directory
                            })
                    else:
                        log.adddebug(_("Dropping missing directory %(dir)s") % {'dir': directory})
                        continue

            list[virtualdir] = []

            try:
                contents = os.listdir(directory)
            except OSError as errtuple:
                print(str(errtuple))
                self.logMessage(str(errtuple))
                continue

            contents.sort()

            for filename in contents:

                if self.hiddenCheck({'dir': directory, 'file': filename}):
                    continue

                path = os.path.join(directory, filename)
                try:
                    isfile = os.path.isfile(path)
                except OSError as errtuple:
                    message = _("Scanning Error: %(error)s Path: %(path)s") % {'error': errtuple, 'path': path}
                    print(str(message))
                    self.logMessage(message)
                    displayTraceback(sys.exc_info()[2])
                    continue
                else:
                    if isfile:
                        # Get the metadata of the file via mutagen
                        data = self.getFileInfo(filename, path)
                        if data is not None:
                            list[virtualdir].append(data)

                if yieldcall is not None:
                    yieldcall()

        return list

    # Get metadata via mutagen on Unix
    def getFileInfo(self, name, pathname):

        try:
            size = os.path.getsize(pathname)
            info = metadata.detect(pathname)

            if info:

                # Sometimes the duration (time) or the bitrate of the file is unknown
                if info["time"] is None or info["bitrate"] is None:
                    fileinfo = (name, size, None, None)
                else:
                    bitrateinfo = (int(info["bitrate"]), int(info["vbr"]))
                    fileinfo = (name, size, bitrateinfo, int(info["time"]))
            else:
                fileinfo = (name, size, None, None)

            return fileinfo

        except Exception as errtuple:
            message = _("Scanning File Error: %(error)s Path: %(path)s") % {'error': errtuple, 'path': pathname}
            self.logMessage(message)
            displayTraceback(sys.exc_info()[2])

    # Get streams of files on Unix
    def getFilesStreams(self, mtimes, oldmtimes, oldstreams, newsharedfiles, rebuild=False, yieldcall=None):

        streams = {}
        shared = self.config.sections["transfers"]["shared"]  # noqa: F841

        for directory in list(mtimes.keys()):

            virtualdir = self.real2virtual(directory)

            if self.hiddenCheck({'dir': directory}):
                continue

            if not rebuild and directory in oldmtimes:
                if mtimes[directory] == oldmtimes[directory]:
                    if os.path.exists(directory):
                        # No change
                        try:
                            streams[virtualdir] = oldstreams[virtualdir]
                            continue
                        except KeyError:
                            log.addwarning(_("Inconsistent cache for '%(vdir)s', rebuilding '%(dir)s'") % {
                                'vdir': virtualdir,
                                'dir': directory
                            })
                    else:
                        log.adddebug(_("Dropping missing directory %(dir)s") % {'dir': directory})
                        continue

            streams[virtualdir] = self.getDirStream(newsharedfiles[virtualdir])

            if yieldcall is not None:
                yieldcall()

        return streams

    # Get Modification Times on Windows
    def getDirsMtimesUnicode(self, dirs, yieldcall=None):

        list = {}

        for directory in dirs:

            directory = os.path.expanduser(directory.replace("//", "/"))

            u_directory = "%s" % directory
            str_directory = str(directory)

            if self.hiddenCheck({'dir': directory}):
                continue

            try:
                contents = dircache.listdir(u_directory)
                mtime = os.path.getmtime(u_directory)
            except OSError as errtuple:
                message = _("Scanning Directory Error: %(error)s Path: %(path)s") % {'error': errtuple, 'path': u_directory}
                print(str(message))
                self.logMessage(message)
                displayTraceback(sys.exc_info()[2])
                continue

            contents.sort()

            list[str_directory] = mtime

            for filename in contents:

                path = os.path.join(directory, filename)

                # force Unicode for reading from disk in win32
                u_path = "%s" % path
                s_path = str(path)

                try:
                    isdir = os.path.isdir(u_path)
                except OSError as errtuple:
                    message = _("Scanning Error: %(error)s Path: %(path)s") % {'error': errtuple, 'path': u_path}
                    print(str(message))
                    self.logMessage(message)
                    continue

                try:
                    mtime = os.path.getmtime(u_path)
                except OSError as errtuple:  # noqa: F841
                    try:
                        mtime = os.path.getmtime(s_path)
                    except OSError as errtuple:
                        message = _("Scanning Error: %(error)s Path: %(path)s") % {'error': errtuple, 'path': u_path}
                        print(str(message))
                        self.logMessage(message)
                        continue
                else:
                    if isdir:
                        list[s_path] = mtime
                        dircontents = self.getDirsMtimesUnicode([path])
                        for k in dircontents:
                            list[k] = dircontents[k]

                    if yieldcall is not None:
                        yieldcall()

        return list

    # Check for new files on Windows
    def getFilesListUnicode(self, mtimes, oldmtimes, oldlist, yieldcall=None, progress=None, rebuild=False):
        """ Get a list of files with their filelength, bitrate and track length in seconds """

        list = {}
        count = 0

        for directory in mtimes:

            directory = os.path.expanduser(directory)
            virtualdir = self.real2virtual(directory)
            count += 1

            if progress:
                percent = float(count) / len(mtimes)
                if percent <= 1.0:
                    gobject.idle_add(progress.set_fraction, percent)

            # force Unicode for reading from disk
            u_directory = "%s" % directory
            str_directory = str(directory)  # noqa: F841

            if self.hiddenCheck({'dir': directory}):
                continue

            if directory in oldmtimes and directory not in oldlist:
                # Partial information, happened with unicode paths that N+ couldn't handle properly
                del oldmtimes[directory]

            if not rebuild and directory in oldmtimes:
                if mtimes[directory] == oldmtimes[directory]:
                    if os.path.exists(directory):
                        try:
                            list[virtualdir] = oldlist[virtualdir]
                            continue
                        except KeyError:
                            log.addwarning(_("Inconsistent cache for '%(vdir)s', rebuilding '%(dir)s'") % {
                                'vdir': virtualdir,
                                'dir': directory
                            })
                    else:
                        log.adddebug(_("Dropping missing directory %(dir)s") % {'dir': directory})
                        continue

            list[virtualdir] = []

            try:
                contents = os.listdir(u_directory)
            except OSError as errtuple:
                print(str(errtuple))
                self.logMessage(str(errtuple))
                continue

            contents.sort()

            for filename in contents:

                if self.hiddenCheck({'dir': directory, 'file': filename}):
                    continue

                path = os.path.join(directory, filename)
                s_path = str(path)
                ppath = str(path)

                s_filename = str(filename)
                try:
                    # try to force Unicode for reading from disk
                    isfile = os.path.isfile(ppath)
                except OSError as errtuple:
                    message = _("Scanning Error: %(error)s Path: %(path)s") % {'error': errtuple, 'path': path}
                    print(str(message))
                    self.logMessage(message)
                    displayTraceback(sys.exc_info()[2])
                    continue
                else:
                    if isfile:
                        # Get the metadata of the file via mutagen
                        data = self.getFileInfoUnicode(s_filename, s_path)
                        if data is not None:
                            list[virtualdir].append(data)

                if yieldcall is not None:
                    yieldcall()

        return list

    # Get metadata via mutagen on Windows
    def getFileInfoUnicode(self, name, pathname):

        try:

            if type(name) is str:
                pathname_f = "%s" % pathname
            else:
                pathname_f = pathname

            try:
                size = os.path.getsize(pathname_f)
            except Exception:
                size = os.path.getsize(pathname)

            try:
                info = metadata.detect(pathname_f)
            except Exception:
                info = metadata.detect(pathname)

            if info:

                # Sometimes the duration (time) or the bitrate of the file is unknown
                if info["time"] is None or info["bitrate"] is None:
                    fileinfo = (name, size, None, None)
                else:
                    bitrateinfo = (int(info["bitrate"]), int(info["vbr"]))
                    fileinfo = (name, size, bitrateinfo, int(info["time"]))
            else:
                fileinfo = (name, size, None, None)

            return fileinfo

        except Exception as errtuple:
            message = _("Scanning File Error: %(error)s Path: %(path)s") % {'error': errtuple, 'path': pathname}
            self.logMessage(message)
            displayTraceback(sys.exc_info()[2])

    # Get streams of files on Windows
    def getFilesStreamsUnicode(self, mtimes, oldmtimes, oldstreams, newsharedfiles, rebuild=False, yieldcall=None):

        streams = {}
        shared = self.config.sections["transfers"]["shared"]  # noqa: F841

        for directory in list(mtimes.keys()):

            virtualdir = self.real2virtual(directory)

            # force Unicode for reading from disk
            u_directory = "%s" % directory
            str_directory = str(directory)  # noqa: F841

            if self.hiddenCheck({'dir': directory}):
                continue

            if directory in oldmtimes and directory not in oldstreams:
                # Partial information, happened with unicode paths that N+ couldn't handle properly
                del oldmtimes[directory]

            if not rebuild and directory in oldmtimes:
                if mtimes[directory] == oldmtimes[directory]:
                    if os.path.exists(u_directory):
                        # No change
                        try:
                            streams[virtualdir] = oldstreams[virtualdir]
                            continue
                        except KeyError:
                            log.addwarning(_("Inconsistent cache for '%(vdir)s', rebuilding '%(dir)s'") % {
                                'vdir': virtualdir,
                                'dir': directory
                            })
                    else:
                        log.adddebug(_("Dropping missing directory %(dir)s") % {'dir': directory})
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
            except ImportError as e:  # noqa: F841
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

        msg = slskmessages.SlskMessage()
        stream = msg.packObject(NetworkIntType(len(dir)))

        for file_and_meta in dir:
            stream += self.getByteStream(file_and_meta)

        return stream

    # Pack a file's metadata
    def getByteStream(self, fileinfo):

        message = slskmessages.SlskMessage()

        stream = bytes([1]) + message.packObject(fileinfo[0]) + message.packObject(NetworkLongLongType(fileinfo[1]))
        if fileinfo[2] is not None:
            try:
                msgbytes = ''
                msgbytes += message.packObject('mp3') + message.packObject(3)
                msgbytes += (
                    message.packObject(0) +
                    message.packObject(NetworkIntType(fileinfo[2][0])) +
                    message.packObject(1) +
                    message.packObject(NetworkIntType(fileinfo[3])) +
                    message.packObject(2) +
                    message.packObject(NetworkIntType(fileinfo[2][1]))
                )
                stream += msgbytes
            except Exception:
                log.addwarning(_("Found meta data that couldn't be encoded, possible corrupt file: '%(file)s' has a bitrate of %(bitrate)s kbs, a length of %(length)s seconds and a VBR of %(vbr)s" % {
                    'file': fileinfo[0],
                    'bitrate': fileinfo[2][0],
                    'length': fileinfo[3],
                    'vbr': fileinfo[2][1]
                }))
                stream += message.packObject('') + message.packObject(0)
        else:
            stream += message.packObject('') + message.packObject(0)

        return stream

    # Update Search index with new files
    def getFilesIndex(self, mtimes, oldmtimes, shareddirs, newsharedfiles, yieldcall=None, progress=None):

        wordindex = {}
        fileindex = {}
        index = 0
        count = 0

        for directory in list(mtimes.keys()):

            virtualdir = self.real2virtual(directory)

            if progress:
                percent = float(count) / len(mtimes)
                if percent <= 1.0:
                    gobject.idle_add(progress.set_fraction, percent)

            count += 1

            if self.hiddenCheck({'dir': directory}):
                continue

            for j in newsharedfiles[virtualdir]:
                indexes = self.getIndexWords(virtualdir, j[0], shareddirs)
                for k in indexes:
                    wordindex.setdefault(k, []).append(index)
                fileindex[str(index)] = ((virtualdir + '\\' + j[0]), ) + j[1:]
                index += 1

            if yieldcall is not None:
                yieldcall()

        return wordindex, fileindex

    # Collect words from filenames for Search index
    def getIndexWords(self, dir, file, shareddirs):

        for i in shareddirs:
            if os.path.commonprefix([dir, i]) == i:
                dir = dir[len(i):]

        words = (dir + ' ' + file).translate(
            str.maketrans(string.punctuation, ''.join([' ' for i in string.punctuation]))
        ).lower().split()

        # remove duplicates
        d = {}
        for x in words:
            d[x] = x
        return list(d.values())

    def addToShared(self, name):
        """ Add a file to the normal shares database """

        config = self.config.sections
        if not config["transfers"]["sharedownloaddir"]:
            return

        shared = config["transfers"]["sharedfiles"]
        sharedstreams = config["transfers"]["sharedfilesstreams"]
        wordindex = config["transfers"]["wordindex"]
        fileindex = config["transfers"]["fileindex"]
        shareddirs = config["transfers"]["shared"] + [config["transfers"]["downloaddir"]]
        sharedmtimes = config["transfers"]["sharedmtimes"]

        dir = str(os.path.expanduser(os.path.dirname(name)))
        file = str(os.path.basename(name))
        size = os.path.getsize(name)  # noqa: F841

        shared[dir] = shared.get(dir, [])

        if file not in [i[0] for i in shared[dir]]:
            fileinfo = self.getFileInfo(file, name)
            shared[dir] = shared[dir] + [fileinfo]
            sharedstreams[dir] = self.getDirStream(shared[dir])
            words = self.getIndexWords(dir, file, shareddirs)
            self.addToIndex(wordindex, fileindex, words, dir, fileinfo)
            sharedmtimes[dir] = os.path.getmtime(dir)
            self.newnormalshares = True

        if config["transfers"]["enablebuddyshares"]:
            self.addToBuddyShared(name)

        self.config.writeShares()

    def addToBuddyShared(self, name):
        """ Add a file to the buddy shares database """

        config = self.config.sections
        if not config["transfers"]["sharedownloaddir"]:
            return

        bshared = config["transfers"]["bsharedfiles"]
        bsharedstreams = config["transfers"]["bsharedfilesstreams"]
        bwordindex = config["transfers"]["bwordindex"]
        bfileindex = config["transfers"]["bfileindex"]
        bshareddirs = config["transfers"]["buddyshared"] + config["transfers"]["shared"] + [config["transfers"]["downloaddir"]]
        bsharedmtimes = config["transfers"]["bsharedmtimes"]

        dir = str(os.path.expanduser(os.path.dirname(name)))
        file = str(os.path.basename(name))
        size = os.path.getsize(name)  # noqa: F841

        bshared[dir] = bshared.get(dir, [])

        if file not in [i[0] for i in bshared[dir]]:
            fileinfo = self.getFileInfo(file, name)
            bshared[dir] = bshared[dir] + [fileinfo]
            bsharedstreams[dir] = self.getDirStream(bshared[dir])
            words = self.getIndexWords(dir, file, bshareddirs)
            self.addToIndex(bwordindex, bfileindex, words, dir, fileinfo)
            bsharedmtimes[dir] = os.path.getmtime(dir)
            self.newbuddyshares = True

    def addToIndex(self, wordindex, fileindex, words, dir, fileinfo):
        index = len(list(fileindex.keys()))
        for i in words:
            if i not in wordindex:
                wordindex[i] = [index]
            else:
                wordindex[i] = wordindex[i] + [index]
        fileindex[str(index)] = (os.path.join(dir, fileinfo[0]),) + fileinfo[1:]
