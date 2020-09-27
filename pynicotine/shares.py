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
import pickle
import re
import shelve
import stat
import string
import sys
import taglib
import _thread

from gettext import gettext as _

from gi.repository import GLib

from pynicotine import slskmessages
from pynicotine.utils import GetUserDirectories

if sys.platform == "win32":
    # Use semidbm for faster shelves on Windows

    def shelve_open_semidbm(filename, flag='c', protocol=None, writeback=False):
        import semidbm
        return shelve.Shelf(semidbm.open(filename, flag), protocol, writeback)

    shelve.open = shelve_open_semidbm


class Shares:

    def __init__(self, np):
        self.np = np
        self.config = self.np.config

        # Convert fs-based shared to virtual shared (pre 1.4.0)
        def _convert_to_virtual(x):
            if isinstance(x, tuple):
                return x
            virtual = x.replace('/', '_').replace('\\', '_').strip('_')
            self.logMessage("Renaming shared folder '%s' to '%s'. A rescan of your share is required." % (x, virtual), 1)
            return (virtual, x)

        self.config.sections["transfers"]["shared"] = [_convert_to_virtual(x) for x in self.config.sections["transfers"]["shared"]]
        self.config.sections["transfers"]["buddyshared"] = [_convert_to_virtual(x) for x in self.config.sections["transfers"]["buddyshared"]]

        self.load_shares(
            [
                os.path.join(self.config.data_dir, "files.db"),
                os.path.join(self.config.data_dir, "buddyfiles.db"),
                os.path.join(self.config.data_dir, "streams.db"),
                os.path.join(self.config.data_dir, "buddystreams.db"),
                os.path.join(self.config.data_dir, "wordindex.db"),
                os.path.join(self.config.data_dir, "buddywordindex.db"),
                os.path.join(self.config.data_dir, "fileindex.db"),
                os.path.join(self.config.data_dir, "buddyfileindex.db"),
                os.path.join(self.config.data_dir, "mtimes.db"),
                os.path.join(self.config.data_dir, "buddymtimes.db")
            ]
        )

        self.queue = self.np.queue
        self.logMessage = self.np.logMessage
        self.CompressedSharesBuddy = self.CompressedSharesNormal = None
        self.compress_shares("normal")
        self.compress_shares("buddy")
        self.newbuddyshares = self.newnormalshares = False
        self.translatepunctuation = str.maketrans(dict.fromkeys(string.punctuation, ' '))

    """ Shares-related actions """

    def real2virtual(self, path):
        path = os.path.normpath(path)

        for (virtual, real) in self._virtualmapping():
            real = os.path.normpath(real)

            if path == real:
                return virtual
            if path.startswith(real + os.sep):
                virtualpath = virtual + '\\' + path[len(real + os.sep):].replace(os.sep, '\\')
                return virtualpath
        return "__INTERNAL_ERROR__" + path

    def virtual2real(self, path):
        path = os.path.normpath(path)

        for (virtual, real) in self._virtualmapping():
            virtual = os.path.normpath(virtual)

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

    def load_shares(self, dbs):
        opened_shelves = []
        errors = []

        for shelvefile in dbs:
            try:
                opened_shelves.append(shelve.open(shelvefile, protocol=pickle.HIGHEST_PROTOCOL))
            except Exception:
                errors.append(shelvefile)
                try:
                    os.unlink(shelvefile)
                    opened_shelves.append(shelve.open(shelvefile, flag='n', protocol=pickle.HIGHEST_PROTOCOL))
                except Exception as ex:
                    print(("Failed to unlink %s: %s" % (shelvefile, ex)))

        self.config.sections["transfers"]["sharedfiles"] = opened_shelves.pop(0)
        self.config.sections["transfers"]["bsharedfiles"] = opened_shelves.pop(0)
        self.config.sections["transfers"]["sharedfilesstreams"] = opened_shelves.pop(0)
        self.config.sections["transfers"]["bsharedfilesstreams"] = opened_shelves.pop(0)
        self.config.sections["transfers"]["wordindex"] = opened_shelves.pop(0)
        self.config.sections["transfers"]["bwordindex"] = opened_shelves.pop(0)
        self.config.sections["transfers"]["fileindex"] = opened_shelves.pop(0)
        self.config.sections["transfers"]["bfileindex"] = opened_shelves.pop(0)
        self.config.sections["transfers"]["sharedmtimes"] = opened_shelves.pop(0)
        self.config.sections["transfers"]["bsharedmtimes"] = opened_shelves.pop(0)

        if errors:
            self.logMessage(_("Failed to process the following databases: %(names)s") % {'names': '\n'.join(errors)}, 1)

            self.set_shares(sharestype="normal", files={}, streams={}, mtimes={}, wordindex={}, fileindex={})
            self.set_shares(sharestype="buddy", files={}, streams={}, mtimes={}, wordindex={}, fileindex={})

            self.logMessage(_("Shared files database seems to be corrupted, rescan your shares"), 1)
            return

    def set_shares(self, sharestype="normal", files=None, streams=None, mtimes=None, wordindex=None, fileindex=None):

        if sharestype == "normal":
            storable_objects = [
                (files, "sharedfiles", "files.db"),
                (streams, "sharedfilesstreams", "streams.db"),
                (mtimes, "sharedmtimes", "mtimes.db"),
                (wordindex, "wordindex", "wordindex.db"),
                (fileindex, "fileindex", "fileindex.db")
            ]
        else:
            storable_objects = [
                (files, "bsharedfiles", "buddyfiles.db"),
                (streams, "bsharedfilesstreams", "buddystreams.db"),
                (mtimes, "bsharedmtimes", "buddymtimes.db"),
                (wordindex, "bwordindex", "buddywordindex.db"),
                (fileindex, "bfileindex", "buddyfileindex.db")
            ]

        for source, destination, filename in storable_objects:
            if source is not None:
                try:
                    self.config.sections["transfers"][destination].close()
                    self.config.sections["transfers"][destination] = shelve.open(os.path.join(self.config.data_dir, filename), flag='n', protocol=pickle.HIGHEST_PROTOCOL)
                    self.config.sections["transfers"][destination].update(source)

                except Exception as e:
                    self.logMessage(_("Can't save %s: %s") % (filename, e), 1)
                    return

    def compress_shares(self, sharestype):

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

    def send_num_shared_folders_files(self):
        """
        Send number of files in buddy shares if only buddies can
        download, and buddy-shares are enabled.
        """

        config = self.config.sections

        if config["transfers"]["enablebuddyshares"] and config["transfers"]["friendsonly"]:
            shared_db = "bsharedfiles"
            index_db = "bfileindex"
        else:
            shared_db = "sharedfiles"
            index_db = "fileindex"

        try:
            sharedfolders = len(config["transfers"][shared_db])
            sharedfiles = len(config["transfers"][index_db])

        except TypeError:
            sharedfolders = len(list(config["transfers"][shared_db]))
            sharedfiles = len(list(config["transfers"][index_db]))

        self.queue.put(slskmessages.SharedFoldersFiles(sharedfolders, sharedfiles))

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
                self.compress_shares("normal")
                self.newnormalshares = False
            m = self.CompressedSharesNormal

        elif checkuser == 2:
            # Send Buddy Shares
            if self.newbuddyshares:
                self.compress_shares("buddy")
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

    """ Scanning """

    def RebuildShares(self):
        self._RescanShares("normal", rebuild=True)

    def RescanShares(self, rebuild=False):
        self._RescanShares("normal", rebuild)

    def RebuildBuddyShares(self):
        self._RescanShares("buddy", rebuild=True)

    def RescanBuddyShares(self, rebuild=False):
        self._RescanShares("buddy", rebuild)

    def _RescanShares(self, sharestype, rebuild=False):

        if sharestype == "normal":
            progress = self.np.frame.SharesProgress
            mtimes = self.config.sections["transfers"]["sharedmtimes"]
            files = self.config.sections["transfers"]["sharedfiles"]
            filesstreams = self.config.sections["transfers"]["sharedfilesstreams"]

            shared_folders = self.config.sections["transfers"]["shared"][:]

            if self.config.sections["transfers"]["sharedownloaddir"]:
                shared_folders.append((_('Downloaded'), self.config.sections["transfers"]["downloaddir"]))

        else:
            progress = self.np.frame.BuddySharesProgress
            mtimes = self.config.sections["transfers"]["bsharedmtimes"]
            files = self.config.sections["transfers"]["bsharedfiles"]
            filesstreams = self.config.sections["transfers"]["bsharedfilesstreams"]

            shared_folders = self.config.sections["transfers"]["buddyshared"][:] + self.config.sections["transfers"]["shared"][:]

            if self.config.sections["transfers"]["sharedownloaddir"]:
                shared_folders.append((_('Downloaded'), self.config.sections["transfers"]["downloaddir"]))

        try:
            GLib.idle_add(progress.set_fraction, 0.0)
            GLib.idle_add(progress.show)

            self.rescan_dirs(
                sharestype,
                shared_folders,
                mtimes,
                files,
                filesstreams,
                progress=progress,
                rebuild=rebuild
            )

            self.np.frame.RescanFinished(sharestype)

            self.compress_shares(sharestype)

            if self.np.transfers is not None:
                self.np.shares.send_num_shared_folders_files()

        except Exception as ex:
            config_dir, data_dir = GetUserDirectories()
            self.logMessage(
                _("Failed to rebuild share, serious error occurred. If this problem persists delete %s/*.db and try again. If that doesn't help please file a bug report with the stack trace included (see terminal output after this message). Technical details: %s") % (data_dir, ex),
                1
            )
            GLib.idle_add(self.np.frame.SharesProgress.hide)
            raise

    def rescan_dirs(self, sharestype, shared, oldmtimes, oldfiles, sharedfilesstreams, progress=None, rebuild=False):
        """
        Check for modified or new files via OS's last mtime on a directory,
        or, if rebuild is True, all directories
        """

        # returns dict in format:  { Directory : mtime, ... }
        shared_directories = [x[1] for x in shared]

        try:
            num_folders = len(oldmtimes)

        except TypeError:
            num_folders = len(list(oldmtimes))

        self.logMessage(_("%(num)s folders found before rescan, rebuilding...") % {"num": num_folders})

        newmtimes = self.get_dirs_mtimes(shared_directories)

        # Get list of files
        # returns dict in format { Directory : { File : metadata, ... }, ... }
        newsharedfiles = self.get_files_list(newmtimes, oldmtimes, oldfiles, progress, rebuild)

        # Pack shares data
        # returns dict in format { Directory : hex string of files+metadata, ... }
        newsharedfilesstreams = self.get_files_streams(newmtimes, oldmtimes, sharedfilesstreams, newsharedfiles, rebuild)

        # Save data to shelves
        self.set_shares(sharestype=sharestype, files=newsharedfiles, streams=newsharedfilesstreams, mtimes=newmtimes)

        # Update Search Index
        # wordindex is a dict in format {word: [num, num, ..], ... } with num matching keys in newfileindex
        # fileindex is a dict in format { num: (path, size, (bitrate, vbr), length), ... }
        self.get_files_index(sharestype, newsharedfiles, progress)

        self.logMessage(_("%(num)s folders found after rescan") % {"num": len(newsharedfiles)})

    def is_hidden(self, folder, filename=None):
        """ Stop sharing any dot/hidden directories/files """

        subfolders = folder.split(os.sep)

        # If any part of the directory structure start with a dot we exclude it
        for part in subfolders:
            if part.startswith("."):
                return True

        # If we're asked to check a file we exclude it if it start with a dot
        if filename is not None and filename.startswith("."):
            return True

        # Check if file is marked as hidden on Windows
        if sys.platform == "win32":
            if filename is not None:
                folder = os.path.join(folder, filename)

            return os.stat(folder).st_file_attributes & stat.FILE_ATTRIBUTE_HIDDEN

        return False

    def add_file_to_index(self, index, filename, folder, fileinfo, wordindex, fileindex, override_wordindex=False):
        """ Add a file to the file index database """

        fileindex[repr(index)] = (folder + '\\' + filename, *fileinfo[1:])

        # Collect words from filenames for Search index
        # Use set to prevent duplicates
        for k in set((folder + " " + filename).lower().translate(self.translatepunctuation).split()):
            try:
                wordindex[k].append(index)
            except KeyError:
                wordindex[k] = [index]

        # If we're working directly on the shelve, we need to save it back
        if override_wordindex:
            wordindex[k] = wordindex[k]

    def add_file_to_shared(self, name):
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
            fileinfo = self.get_file_info(file, name)
            shared[vdir] += [fileinfo]

            sharedstreams[vdir] = self.get_dir_stream(shared[vdir])

            index = len(fileindex)

            self.add_file_to_index(index, file, vdir, fileinfo, wordindex, fileindex, override_wordindex=True)

            sharedmtimes[vdir] = os.path.getmtime(dir)
            self.newnormalshares = True

        if config["transfers"]["enablebuddyshares"]:
            self.add_file_to_buddy_shared(name)

    def add_file_to_buddy_shared(self, name):
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

            fileinfo = self.get_file_info(file, name)
            bshared[vdir] += [fileinfo]

            bsharedstreams[vdir] = self.get_dir_stream(bshared[vdir])

            index = len(bfileindex)

            self.add_file_to_index(index, file, vdir, fileinfo, bwordindex, bfileindex, override_wordindex=True)

            bsharedmtimes[vdir] = os.path.getmtime(dir)
            self.newbuddyshares = True

    def get_dirs_mtimes(self, dirs):
        """ Get Modification Times """

        list = {}

        for folder in dirs:

            try:
                if self.is_hidden(folder):
                    continue

                mtime = os.path.getmtime(folder)
                list[folder] = mtime

                for entry in os.scandir(folder):
                    if entry.is_dir():

                        path = entry.path

                        try:
                            mtime = entry.stat().st_mtime
                        except OSError as errtuple:
                            message = _("Error while scanning %(path)s: %(error)s") % {
                                'path': path,
                                'error': errtuple
                            }

                            print(str(message))
                            self.logMessage(message)
                            continue

                        list[path] = mtime
                        dircontents = self.get_dirs_mtimes([path])
                        for k in dircontents:
                            list[k] = dircontents[k]

            except OSError as errtuple:
                message = _("Error while scanning folder %(path)s: %(error)s") % {'path': folder, 'error': errtuple}
                print(str(message))
                self.logMessage(message)
                continue

        return list

    def get_files_list(self, mtimes, oldmtimes, oldlist, progress=None, rebuild=False):
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

                if not rebuild and folder in oldmtimes:
                    if mtimes[folder] == oldmtimes[folder]:
                        if os.path.exists(folder):
                            try:
                                virtualdir = self.real2virtual(folder)
                                list[virtualdir] = oldlist[virtualdir]
                                continue
                            except KeyError:
                                self.logMessage(_("Inconsistent cache for '%(vdir)s', rebuilding '%(dir)s'") % {
                                    'vdir': virtualdir,
                                    'dir': folder
                                }, 6)
                        else:
                            self.logMessage(_("Dropping missing folder %(dir)s") % {'dir': folder}, 6)
                            continue

                virtualdir = self.real2virtual(folder)
                list[virtualdir] = []

                for entry in os.scandir(folder):

                    if entry.is_file():
                        filename = entry.name

                        if self.is_hidden(folder, filename):
                            continue

                        # Get the metadata of the file
                        data = self.get_file_info(filename, entry.path)
                        if data is not None:
                            list[virtualdir].append(data)

            except OSError as errtuple:
                message = _("Error while scanning folder %(path)s: %(error)s") % {'path': folder, 'error': errtuple}
                print(str(message))
                self.logMessage(message)
                continue

        return list

    def get_file_info(self, name, pathname):
        """ Get metadata via taglib """

        try:
            audio = None
            size = os.stat(pathname).st_size

            if size > 0:
                try:
                    audio = taglib.File(pathname)
                except IOError:
                    pass

            if audio is not None:
                bitrateinfo = (int(audio.bitrate), int(False))  # Second argument used to be VBR (variable bitrate)
                fileinfo = (name, size, bitrateinfo, int(audio.length))
            else:
                fileinfo = (name, size, None, None)

            return fileinfo

        except Exception as errtuple:
            message = _("Error while scanning file %(path)s: %(error)s") % {'path': pathname, 'error': errtuple}
            self.logMessage(message)

    def get_files_streams(self, mtimes, oldmtimes, oldstreams, newsharedfiles, rebuild=False):
        """ Get streams of files """

        streams = {}

        for folder in mtimes:

            virtualdir = self.real2virtual(folder)

            if not rebuild and folder in oldmtimes:

                if mtimes[folder] == oldmtimes[folder]:
                    if os.path.exists(folder):
                        # No change
                        try:
                            streams[virtualdir] = oldstreams[virtualdir]
                            continue
                        except KeyError:
                            self.logMessage(_("Inconsistent cache for '%(vdir)s', rebuilding '%(dir)s'") % {
                                'vdir': virtualdir,
                                'dir': folder
                            }, 6)
                    else:
                        self.logMessage(_("Dropping missing folder %(dir)s") % {'dir': folder}, 6)
                        continue

            streams[virtualdir] = self.get_dir_stream(newsharedfiles[virtualdir])

        return streams

    def get_dir_stream(self, dir):
        """ Pack all files and metadata in directory """

        message = slskmessages.SlskMessage()
        stream = bytearray()
        stream.extend(message.packObject(len(dir)))

        for fileinfo in dir:
            stream.extend(bytes([1]))
            stream.extend(message.packObject(fileinfo[0]))
            stream.extend(message.packObject(fileinfo[1], unsignedlonglong=True))

            if fileinfo[2] is not None:
                try:
                    stream.extend(message.packObject('mp3'))
                    stream.extend(message.packObject(3))

                    stream.extend(message.packObject(0))
                    stream.extend(message.packObject(fileinfo[2][0]))
                    stream.extend(message.packObject(1))
                    stream.extend(message.packObject(fileinfo[3]))
                    stream.extend(message.packObject(2))
                    stream.extend(message.packObject(fileinfo[2][1]))
                except Exception:
                    self.logMessage(_("Found meta data that couldn't be encoded, possible corrupt file: '%(file)s' has a bitrate of %(bitrate)s kbs, a length of %(length)s seconds and a VBR of %(vbr)s" % {
                        'file': fileinfo[0],
                        'bitrate': fileinfo[2][0],
                        'length': fileinfo[3],
                        'vbr': fileinfo[2][1]
                    }), 1)
                    stream.extend(message.packObject(''))
                    stream.extend(message.packObject(0))
            else:
                stream.extend(message.packObject(''))
                stream.extend(message.packObject(0))

        return stream

    def get_files_index(self, sharestype, sharedfiles, progress=None):
        """ Update Search index with new files """

        """ We dump data directly into the file index shelf to save memory """
        if sharestype == "normal":
            section = target = "fileindex"
        else:
            section = "bfileindex"
            target = "buddyfileindex"

        self.config.sections["transfers"][section].close()

        fileindex = self.config.sections["transfers"][section] = \
            shelve.open(os.path.join(self.config.data_dir, target + ".db"), flag='n', protocol=pickle.HIGHEST_PROTOCOL)

        """ For the word index, we can't use the same approach as above, as we need
        to access dict elements frequently. This would take too long on a shelf. """
        wordindex = {}

        index = 0
        count = len(sharedfiles)
        lastpercent = 0.0

        for folder in sharedfiles:
            count += 1

            if progress:
                # Truncate the percentage to two decimal places to avoid sending data to the GUI thread too often
                percent = float("%.2f" % (float(count) / len(sharedfiles) * 0.75))

                if percent > lastpercent and percent <= 1.0:
                    GLib.idle_add(progress.set_fraction, percent)
                    lastpercent = percent

            for fileinfo in sharedfiles[folder]:
                self.add_file_to_index(index, fileinfo[0], folder, fileinfo, wordindex, fileindex)
                index += 1

        self.set_shares(sharestype=sharestype, wordindex=wordindex)

    """ Search request processing """

    def create_search_result_list(self, searchterm, wordindex, maxresults=50):

        try:
            """ Stage 1: Check if each word in the search term is included in our word index.
            If this is the case, we select the word that has the most file matches in our
            word index. If not, exit, since we don't have relevant results. """

            largest = 0

            for i in re.finditer(r'\S+', searchterm):
                i = i.group(0)

                if i not in wordindex:
                    return

                list_size = len(wordindex[i])

                if list_size > largest:
                    largest = list_size
                    largest_key = i

            """ Stage 2: Start with the word that has the most file matches, which we selected
            in the previous step, and gradually remove matches that other words in the search
            term don't have. Return the remaining matches, if any. """

            results = wordindex[largest_key]
            searchterm.replace(largest_key, '')

            for i in re.finditer(r'\S+', searchterm):
                results = set(results).intersection(wordindex[i.group(0)])

            return results

        except ValueError:
            # DB is closed, perhaps when rescanning share or closing Nicotine+
            return

    def process_search_request(self, searchterm, user, searchid, direct=0):

        """ Note: since this section is accessed every time a search request arrives,
        several times a second, please keep it as optimized and memory
        sparse as possible! """

        if not self.config.sections["searches"]["search_results"]:
            # Don't return _any_ results when this option is disabled
            return

        if searchterm is None:
            return

        if user == self.config.sections["server"]["login"]:
            # We shouldn't send a search response if we initiated the search request
            return

        maxresults = self.config.sections["searches"]["maxresults"]

        if maxresults == 0:
            return

        # Don't count excluded words as matches (words starting with -)
        # Strip punctuation
        searchterm = re.sub(r'(\s)-\w+', r'\1', searchterm).lower().translate(self.translatepunctuation).strip()

        if len(searchterm) < self.config.sections["searches"]["min_search_chars"]:
            # Don't send search response if search term contains too few characters
            return

        checkuser, reason = self.np.CheckUser(user, None)

        if not checkuser:
            return

        if checkuser == 2:
            wordindex = self.config.sections["transfers"]["bwordindex"]
        else:
            wordindex = self.config.sections["transfers"]["wordindex"]

        # Find common file matches for each word in search term
        resultlist = self.create_search_result_list(searchterm, wordindex, maxresults)

        if not resultlist:
            return

        if self.np.transfers is not None:

            numresults = min(len(resultlist), maxresults)
            queuesizes = self.np.transfers.getUploadQueueSizes()
            slotsavail = self.np.transfers.allowNewUploads()

            if reason == "geoip":
                geoip = 1
            else:
                geoip = 0

            if checkuser == 2:
                fileindex = self.config.sections["transfers"]["bfileindex"]
            else:
                fileindex = self.config.sections["transfers"]["fileindex"]

            fifoqueue = self.config.sections["transfers"]["fifoqueue"]

            message = slskmessages.FileSearchResult(
                None,
                self.config.sections["server"]["login"],
                geoip, searchid, resultlist, fileindex, slotsavail,
                self.np.speed, queuesizes, fifoqueue, numresults
            )

            self.np.ProcessRequestToPeer(user, message)

            if direct:
                self.logMessage(
                    _("User %(user)s is directly searching for \"%(query)s\", returning %(num)i results") % {
                        'user': user,
                        'query': searchterm,
                        'num': numresults
                    }, 2)
            else:
                self.logMessage(
                    _("User %(user)s is searching for \"%(query)s\", returning %(num)i results") % {
                        'user': user,
                        'query': searchterm,
                        'num': numresults
                    }, 2)
