# COPYRIGHT (C) 2020-2021 Nicotine+ Team
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

import gc
import importlib.util
import os
import pickle
import shelve
import stat
import sys
import threading
import time

from pynicotine import slskmessages
from pynicotine.logfacility import log
from pynicotine.utils import PUNCTUATION
from pynicotine.utils import rename_process

""" Check if there's an appropriate (performant) database type for shelves """

if importlib.util.find_spec("_gdbm"):

    def shelve_open_gdbm(filename, flag='c', protocol=None, writeback=False):
        import _gdbm  # pylint: disable=import-error
        return shelve.Shelf(_gdbm.open(filename, flag), protocol, writeback)

    shelve.open = shelve_open_gdbm

elif importlib.util.find_spec("semidbm"):

    def shelve_open_semidbm(filename, flag='c', protocol=None, writeback=False):
        import semidbm  # pylint: disable=import-error
        return shelve.Shelf(semidbm.open(filename, flag), protocol, writeback)

    shelve.open = shelve_open_semidbm

else:
    print(_("Cannot find %(option1)s or %(option2)s, please install either one.") % {
        "option1": "gdbm",
        "option2": "semidbm"
    })
    sys.exit()

UINT_LIMIT = 4294967295


class Scanner:
    """ Separate process responsible for building shares. It handles scanning of
    folders and files, as well as building databases and writing them to disk. """

    def __init__(self, config, queue, shared_folders, rebuild=False):

        self.config = config
        self.queue = queue
        self.shared_folders, self.shared_buddy_folders = shared_folders
        self.share_dbs = {}
        self.rebuild = rebuild
        self.tinytag = None
        self.translatepunctuation = str.maketrans(dict.fromkeys(PUNCTUATION, ' '))

    def run(self):

        try:
            from pynicotine.metadata.tinytag import TinyTag
            self.tinytag = TinyTag()

            rename_process(b'nicotine-scan')

            Shares.load_shares(self.share_dbs, [
                ("files", os.path.join(self.config.data_dir, "files.db")),
                ("streams", os.path.join(self.config.data_dir, "streams.db")),
                ("wordindex", os.path.join(self.config.data_dir, "wordindex.db")),
                ("mtimes", os.path.join(self.config.data_dir, "mtimes.db")),
                ("buddyfiles", os.path.join(self.config.data_dir, "buddyfiles.db")),
                ("buddystreams", os.path.join(self.config.data_dir, "buddystreams.db")),
                ("buddywordindex", os.path.join(self.config.data_dir, "buddywordindex.db")),
                ("buddymtimes", os.path.join(self.config.data_dir, "buddymtimes.db"))
            ])

            start_num_folders = len(list(self.share_dbs["buddymtimes"]))

            self.queue.put((_("Rescanning shares…"), None, None))
            self.queue.put((_("%(num)s folders found before rescan, rebuilding…"), {"num": start_num_folders}, None))

            new_mtimes, new_files, new_streams = self.rescan_dirs("normal", rebuild=self.rebuild)
            _new_mtimes, new_files, _new_streams = self.rescan_dirs("buddy", new_mtimes, new_files,
                                                                    new_streams, self.rebuild)

            self.queue.put((_("%(num)s folders found after rescan"), {"num": len(new_files)}, None))
            self.queue.put((_("Finished rescanning shares"), None, None))

        except Exception:
            from traceback import format_exc

            self.queue.put((
                _("Serious error occurred while rescanning shares. If this problem persists, "
                  "delete %(dir)s/*.db and try again. If that doesn't help, please file a bug "
                  "report with this stack trace included: %(trace)s"), {
                    "dir": self.config.data_dir,
                    "trace": "\n" + format_exc()
                }, None
            ))
            self.queue.put(Exception("Scanning failed"))

    def set_shares(self, share_type, files=None, streams=None, mtimes=None, wordindex=None):

        self.config.create_data_folder()

        storable_objects = [
            (files, "files"),
            (streams, "streams"),
            (mtimes, "mtimes"),
            (wordindex, "wordindex")
        ]

        for source, destination in storable_objects:
            if source is None:
                continue

            try:
                if share_type == "buddy":
                    destination = "buddy" + destination

                # Close old db
                self.share_dbs[destination].close()

                database = shelve.open(os.path.join(self.config.data_dir, destination + ".db"),
                                       flag='n', protocol=pickle.HIGHEST_PROTOCOL)
                database.update(source)
                database.close()

            except Exception as error:
                self.queue.put((_("Can't save %(filename)s: %(error)s"),
                                {"filename": destination + ".db", "error": error}, None))
                return

    def rescan_dirs(self, share_type, mtimes=None, files=None, streams=None, rebuild=False):
        """
        Check for modified or new files via OS's last mtime on a directory,
        or, if rebuild is True, all directories
        """

        if share_type == "buddy":
            shared_folders = (x[1] for x in self.shared_buddy_folders)
            prefix = "buddy"
        else:
            shared_folders = (x[1] for x in self.shared_folders)
            prefix = ""

        new_mtimes = {}

        for folder in shared_folders:
            # Get mtimes for top-level shared folders, then every subfolder
            try:
                mtime = os.stat(folder).st_mtime
                new_mtimes[folder] = mtime
                new_mtimes = {**new_mtimes, **self.get_folder_mtimes(folder)}

            except OSError as errtuple:
                self.queue.put((_("Error while scanning folder %(path)s: %(error)s"), {
                    'path': folder,
                    'error': errtuple
                }, None))

        # Get list of files
        # returns dict in format { Directory : { File : metadata, ... }, ... }
        # returns dict in format { Directory : hex string of files+metadata, ... }
        new_files, new_streams = self.get_files_list(
            new_mtimes, self.share_dbs[prefix + "mtimes"], self.share_dbs[prefix + "files"],
            self.share_dbs[prefix + "streams"], rebuild
        )

        # Save data to databases
        if files is not None:
            new_files = {**files, **new_files}

        if streams is not None:
            new_streams = {**streams, **new_streams}

        if mtimes is not None:
            new_mtimes = {**mtimes, **new_mtimes}

        self.set_shares(share_type, files=new_files, streams=new_streams, mtimes=new_mtimes)

        # Update Search Index
        # wordindex is a dict in format {word: [num, num, ..], ... } with num matching keys in newfileindex
        # fileindex is a dict in format { num: (path, size, (bitrate, vbr), length), ... }
        wordindex = self.get_files_index(new_files, prefix + "fileindex")

        # Save data to databases
        self.set_shares(share_type, wordindex=wordindex)

        del wordindex
        gc.collect()

        return new_mtimes, new_files, new_streams

    @staticmethod
    def is_hidden(folder, filename=None, folder_obj=None):
        """ Stop sharing any dot/hidden directories/files """

        # If the last folder in the path starts with a dot, we exclude it
        if filename is None:
            last_folder = os.path.basename(os.path.normpath(folder.replace('\\', '/')))

            if last_folder.startswith("."):
                return True

        # If we're asked to check a file we exclude it if it start with a dot
        if filename is not None and filename.startswith("."):
            return True

        # Check if file is marked as hidden on Windows
        if sys.platform == "win32":
            if filename is not None:
                folder += '\\' + filename

            elif len(folder) == 3 and folder[1] == ":" and folder[2] in ("\\", "/"):
                # Root directories are marked as hidden, but we allow scanning them
                return False

            elif folder_obj is not None:
                # Faster way if we use scandir
                return folder_obj.stat().st_file_attributes & stat.FILE_ATTRIBUTE_HIDDEN

            return os.stat(folder).st_file_attributes & stat.FILE_ATTRIBUTE_HIDDEN

        return False

    @staticmethod
    def get_utf8_path(path):
        """ Convert a path to utf-8, if necessary """

        try:
            # latin-1 to utf-8
            return path.encode('latin-1').decode('utf-8')

        except Exception:
            # fix any remaining oddities (e.g. surrogates)
            return path.encode('utf-8', 'replace').decode('utf-8')

    def get_folder_mtimes(self, folder):
        """ Get Modification Times """

        mtimes = {}

        try:
            for entry in os.scandir(folder):
                if entry.is_dir():
                    path = self.get_utf8_path(entry.path).replace('\\', os.sep)

                    if self.is_hidden(path):
                        continue

                    try:
                        mtime = entry.stat().st_mtime

                    except OSError as errtuple:
                        self.queue.put((_("Error while scanning %(path)s: %(error)s"), {
                            'path': path,
                            'error': errtuple
                        }, None))
                        continue

                    mtimes[path] = mtime
                    dircontents = self.get_folder_mtimes(path)

                    for k, contents in dircontents.items():
                        mtimes[k] = contents

        except OSError as errtuple:
            self.queue.put((_("Error while scanning folder %(path)s: %(error)s"),
                           {'path': folder, 'error': errtuple}, None))

        return mtimes

    def get_files_list(self, mtimes, oldmtimes, oldfiles, oldstreams, rebuild=False):
        """ Get a list of files with their filelength, bitrate and track length in seconds """

        files = {}
        streams = {}
        count = 0
        lastpercent = 0.0

        for folder in mtimes:

            try:
                count += 1

                # Truncate the percentage to two decimal places to avoid sending data to the GUI thread too often
                percent = float("%.2f" % (float(count) / len(mtimes) * 0.5))

                if lastpercent < percent <= 1.0:
                    self.queue.put(percent)
                    lastpercent = percent

                virtualdir = Shares.real2virtual_cls(folder, self.config)

                if not rebuild and folder in oldmtimes and mtimes[folder] == oldmtimes[folder]:
                    if os.path.exists(folder):
                        try:
                            files[virtualdir] = oldfiles[virtualdir]
                            streams[virtualdir] = oldstreams[virtualdir]
                            continue
                        except KeyError:
                            self.queue.put(("Inconsistent cache for '%(vdir)s', rebuilding '%(dir)s'", {
                                'vdir': virtualdir,
                                'dir': folder
                            }, "miscellaneous"))
                    else:
                        self.queue.put(("Dropping missing folder %(dir)s", {'dir': folder}, "miscellaneous"))
                        continue

                files[virtualdir] = []

                for entry in os.scandir(folder):

                    if entry.is_file():
                        filename = self.get_utf8_path(entry.name)

                        if self.is_hidden(folder, filename):
                            continue

                        # Get the metadata of the file
                        path = self.get_utf8_path(entry.path)
                        data = self.get_file_info(filename, path, self.tinytag, self.queue, entry)
                        files[virtualdir].append(data)

                streams[virtualdir] = self.get_dir_stream(files[virtualdir])

            except OSError as errtuple:
                self.queue.put((_("Error while scanning folder %(path)s: %(error)s"),
                               {'path': folder, 'error': errtuple}, None))
                continue

        return files, streams

    @staticmethod
    def get_file_info(name, pathname, tinytag, queue=None, file=None):
        """ Get file metadata """

        size = 0
        audio = None
        bitrate_info = None
        duration_info = None

        try:
            if file:
                # Faster way if we use scandir
                size = file.stat().st_size
            else:
                size = os.stat(pathname).st_size

            """ We skip metadata scanning of files without meaningful content """
            if size > 128:
                try:
                    audio = tinytag.get(pathname, size, tags=False)

                except Exception as errtuple:
                    error = _("Error while scanning metadata for file %(path)s: %(error)s")
                    args = {'path': pathname, 'error': errtuple}

                    if queue:
                        queue.put((error, args, None))
                    else:
                        log.add(error, args)

            if audio is not None and audio.bitrate is not None and audio.duration is not None:
                bitrate = int(audio.bitrate)
                duration = int(audio.duration)

                if UINT_LIMIT > bitrate > 0:
                    bitrate_info = (bitrate, int(False))  # Second argument used to be VBR (variable bitrate)

                if UINT_LIMIT > duration > 0:
                    duration_info = duration

                if bitrate_info is None or duration_info is None:
                    error = "Ignoring invalid metadata for file %(path)s: %(metadata)s"
                    args = {'path': pathname, 'metadata': "bitrate: %s, duration: %s s" % (bitrate, duration)}

                    if queue:
                        queue.put((error, args, "miscellaneous"))
                    else:
                        log.add(error, args)

        except Exception as errtuple:
            error = _("Error while scanning file %(path)s: %(error)s")
            args = {'path': pathname, 'error': errtuple}

            if queue:
                queue.put((error, args, None))
            else:
                log.add(error, args)

        return (name, size, bitrate_info, duration_info)

    @staticmethod
    def get_dir_stream(folder):
        """ Pack all files and metadata in directory """

        message = slskmessages.FileSearchResult()
        stream = bytearray()
        stream.extend(message.pack_object(len(folder)))

        for fileinfo in folder:
            stream.extend(message.pack_file_info(fileinfo))

        return stream

    @staticmethod
    def add_file_to_index(index, filename, folder, fileinfo, wordindex, fileindex, pattern):
        """ Add a file to the file index database """

        fileindex[repr(index)] = (folder + '\\' + filename, *fileinfo[1:])

        # Collect words from filenames for Search index
        # Use set to prevent duplicates
        for k in set((folder + " " + filename).lower().translate(pattern).split()):
            try:
                wordindex[k].append(index)
            except KeyError:
                wordindex[k] = [index]

    def get_files_index(self, sharedfiles, fileindex_dest):
        """ Update Search index with new files """

        """ We dump data directly into the file index database to save memory.
        For the word index db, we can't use the same approach, as we need to access
        dict elements frequently. This would take too long to access from disk. """

        fileindex = shelve.open(os.path.join(self.config.data_dir, fileindex_dest + ".db"),
                                flag='n', protocol=pickle.HIGHEST_PROTOCOL)
        wordindex = {}

        index = 0
        count = len(sharedfiles)
        lastpercent = 0.0

        for folder in sharedfiles:
            count += 1

            # Truncate the percentage to two decimal places to avoid sending data to the GUI thread too often
            percent = float("%.2f" % (float(count) / len(sharedfiles) * 0.5))

            if lastpercent < percent <= 1.0:
                self.queue.put(percent)
                lastpercent = percent

            for fileinfo in sharedfiles[folder]:
                self.add_file_to_index(
                    index, fileinfo[0], folder, fileinfo, wordindex, fileindex, self.translatepunctuation)
                index += 1

        fileindex.close()
        return wordindex


class Shares:

    def __init__(self, core, config, queue, init_shares=True, ui_callback=None):

        self.core = core
        self.ui_callback = ui_callback
        self.config = config
        self.queue = queue
        self.translatepunctuation = str.maketrans(dict.fromkeys(PUNCTUATION, ' '))
        self.share_dbs = {}
        self.rescanning = False
        self.newbuddyshares = False
        self.newnormalshares = False
        self.compressed_shares_normal = slskmessages.SharedFileList(None, None)
        self.compressed_shares_buddy = slskmessages.SharedFileList(None, None)

        self.convert_shares()
        self.public_share_dbs = [
            ("files", os.path.join(self.config.data_dir, "files.db")),
            ("streams", os.path.join(self.config.data_dir, "streams.db")),
            ("wordindex", os.path.join(self.config.data_dir, "wordindex.db")),
            ("fileindex", os.path.join(self.config.data_dir, "fileindex.db")),
            ("mtimes", os.path.join(self.config.data_dir, "mtimes.db"))
        ]
        self.buddy_share_dbs = [
            ("buddyfiles", os.path.join(self.config.data_dir, "buddyfiles.db")),
            ("buddystreams", os.path.join(self.config.data_dir, "buddystreams.db")),
            ("buddywordindex", os.path.join(self.config.data_dir, "buddywordindex.db")),
            ("buddyfileindex", os.path.join(self.config.data_dir, "buddyfileindex.db")),
            ("buddymtimes", os.path.join(self.config.data_dir, "buddymtimes.db"))
        ]

        if not init_shares:
            return

        if ui_callback:
            # Slight delay to prevent minor performance hit when compressing large file share
            timer = threading.Timer(0.75, self.init_shares)
            timer.name = "InitSharesTimer"
            timer.daemon = True
            timer.start()
        else:
            self.init_shares()

    """ Shares-related actions """

    def real2virtual(self, path):
        return self.real2virtual_cls(path, self.config)

    @classmethod
    def real2virtual_cls(cls, path, config):

        path = path.replace('/', '\\')

        for (virtual, real, *_unused) in cls._virtualmapping(config):
            # Remove slashes from share name to avoid path conflicts
            virtual = virtual.replace('/', '_').replace('\\', '_')

            real = real.replace('/', '\\')
            if path == real:
                return virtual

            # Use rstrip to remove trailing separator from root directories
            real = real.rstrip('\\') + '\\'

            if path.startswith(real):
                virtualpath = virtual + '\\' + path[len(real):]
                return virtualpath

        return "__INTERNAL_ERROR__" + path

    def virtual2real(self, path):

        path = path.replace('/', os.sep).replace('\\', os.sep)

        for (virtual, real, *_unused) in self._virtualmapping(self.config):
            # Remove slashes from share name to avoid path conflicts
            virtual = virtual.replace('/', '_').replace('\\', '_')

            if path == virtual:
                return real

            if path.startswith(virtual + os.sep):
                realpath = real + path[len(virtual):]
                return realpath

        return "__INTERNAL_ERROR__" + path

    @staticmethod
    def _virtualmapping(config):

        mapping = config.sections["transfers"]["shared"][:]
        mapping += config.sections["transfers"]["buddyshared"]

        if config.sections["transfers"]["sharedownloaddir"]:
            mapping += [(_("Downloaded"), config.sections["transfers"]["downloaddir"])]

        return mapping

    def init_shares(self):

        rescan_startup = (self.config.sections["transfers"]["rescanonstartup"]
                          and not self.config.need_config())

        # Rescan shares if necessary
        if rescan_startup:
            self.rescan_shares()
            return

        self.load_shares(self.share_dbs, self.public_share_dbs)
        self.create_compressed_shares_message("normal")
        self.compress_shares("normal")

        self.load_shares(self.share_dbs, self.buddy_share_dbs)
        self.create_compressed_shares_message("buddy")
        self.compress_shares("buddy")

    def convert_shares(self):
        """ Convert fs-based shared to virtual shared (pre 1.4.0) """

        def _convert_to_virtual(shared_folder):
            if isinstance(shared_folder, tuple):
                return shared_folder

            virtual = shared_folder.replace('/', '_').replace('\\', '_').strip('_')
            log.add("Renaming shared folder '%s' to '%s'. A rescan of your share is required.",
                    (shared_folder, virtual))
            return (virtual, shared_folder)

        self.config.sections["transfers"]["shared"] = [_convert_to_virtual(x)
                                                       for x in self.config.sections["transfers"]["shared"]]
        self.config.sections["transfers"]["buddyshared"] = [_convert_to_virtual(x)
                                                            for x in self.config.sections["transfers"]["buddyshared"]]

    @classmethod
    def load_shares(cls, shares, dbs, reset_shares=False):

        errors = []

        for destination, shelvefile in dbs:
            try:
                if not reset_shares:
                    shares[destination] = shelve.open(shelvefile, protocol=pickle.HIGHEST_PROTOCOL)
                else:
                    try:
                        os.remove(shelvefile)

                    except IsADirectoryError:
                        # Potentially trying to use gdbm with a semidbm database
                        os.rmdir(shelvefile)

                    shares[destination] = shelve.open(shelvefile, flag='n', protocol=pickle.HIGHEST_PROTOCOL)

            except Exception:
                from traceback import format_exc

                shares[destination] = None
                errors.append(shelvefile)
                exception = format_exc()

        if not errors:
            return

        log.add(_("Failed to process the following databases: %(names)s"), {
            'names': '\n'.join(errors)
        })
        log.add(exception)

        if not reset_shares:
            log.add(_("Attempting to reset index of shared files due to an error. Please rescan your shares."))
            cls.load_shares(shares, dbs, reset_shares=True)
            return

        log.add(_("File index of shared files could not be accessed. This could occur due to several instances of "
                  "Nicotine+ being active simultaneously, file permission issues, or another issue in Nicotine+."))

    def file_is_shared(self, user, virtualfilename, realfilename):

        log.add_transfer("Checking if file %(virtual_name)s with real path %(path)s is shared", {
            "virtual_name": virtualfilename,
            "path": realfilename
        })

        if not os.access(realfilename, os.R_OK):
            log.add_transfer("Can't access file %(virtual_name)s with real path %(path)s, not sharing", {
                "virtual_name": virtualfilename,
                "path": realfilename
            })
            return False

        folder, _sep, file = virtualfilename.rpartition('\\')
        shared = self.share_dbs.get("files")
        bshared = self.share_dbs.get("buddyfiles")

        if bshared is not None:
            for row in self.config.sections["server"]["userlist"]:
                if row[0] != user:
                    continue

                # Check if buddy is trusted
                if self.config.sections["transfers"]["buddysharestrustedonly"] and not row[4]:
                    break

                for fileinfo in bshared.get(str(folder), ""):
                    if file == fileinfo[0]:
                        return True

        if shared is not None:
            for fileinfo in shared.get(str(folder), ""):
                if file == fileinfo[0]:
                    return True

        log.add_transfer("Failed to share file %(virtual_name)s with real path %(path)s, since it wasn't found", {
            "virtual_name": virtualfilename,
            "path": realfilename
        })
        return False

    def add_file_to_shared(self, name):
        """ Add a file to the normal shares database """

        if not self.config.sections["transfers"]["sharedownloaddir"]:
            return

        shared = self.share_dbs.get("files")

        if shared is None:
            return

        try:
            shareddirs = [path for _name, path in self.config.sections["transfers"]["shared"]]
            shareddirs.append(self.config.sections["transfers"]["downloaddir"])

            rdir = str(os.path.expanduser(os.path.dirname(name)))
            vdir = self.real2virtual(rdir)
            file = str(os.path.basename(name))

            if not shared.get(vdir):
                shared[vdir] = []

            if file not in (i[0] for i in shared[vdir]):
                from pynicotine.metadata.tinytag import TinyTag
                fileinfo = Scanner.get_file_info(file, name, TinyTag())
                shared[vdir] += [fileinfo]

                self.share_dbs["streams"][vdir] = Scanner.get_dir_stream(shared[vdir])

                fileindex = self.share_dbs["fileindex"]

                try:
                    index = len(fileindex)
                except TypeError:
                    index = len(list(fileindex))

                Scanner.add_file_to_index(
                    index, file, vdir, fileinfo, self.share_dbs["wordindex"], fileindex, self.translatepunctuation)

                self.share_dbs["mtimes"][vdir] = os.path.getmtime(rdir)
                self.newnormalshares = True

        except Exception as error:
            log.add(_("Failed to add download %(filename)s to shared files: %(error)s"),
                    {"filename": name, "error": error})

    def add_file_to_buddy_shared(self, name):
        """ Add a file to the buddy shares database """

        if not self.config.sections["transfers"]["sharedownloaddir"]:
            return

        bshared = self.share_dbs.get("buddyfiles")

        if bshared is None:
            return

        try:
            bshareddirs = [path for _name, path in self.config.sections["transfers"]["shared"]]
            bshareddirs += [path for _name, path in self.config.sections["transfers"]["buddyshared"]]
            bshareddirs.append(self.config.sections["transfers"]["downloaddir"])

            rdir = str(os.path.expanduser(os.path.dirname(name)))
            vdir = self.real2virtual(rdir)
            file = str(os.path.basename(name))

            if not bshared.get(vdir):
                bshared[vdir] = []

            if file not in (i[0] for i in bshared[vdir]):
                from pynicotine.metadata.tinytag import TinyTag
                fileinfo = Scanner.get_file_info(file, name, TinyTag())
                bshared[vdir] += [fileinfo]

                self.share_dbs["buddystreams"][vdir] = Scanner.get_dir_stream(bshared[vdir])

                bfileindex = self.share_dbs["buddyfileindex"]

                try:
                    index = len(bfileindex)
                except TypeError:
                    index = len(list(bfileindex))

                Scanner.add_file_to_index(
                    index, file, vdir, fileinfo,
                    self.share_dbs["buddywordindex"], bfileindex, self.translatepunctuation
                )

                self.share_dbs["buddymtimes"][vdir] = os.path.getmtime(rdir)
                self.newbuddyshares = True

        except Exception as error:
            log.add(_("Failed to add download %(filename)s to shared files: %(error)s"),
                    {"filename": name, "error": error})

    def create_compressed_shares_message(self, share_type):
        """ Create a message that will later contain a compressed list of our shares """

        if share_type == "normal":
            self.compressed_shares_normal = slskmessages.SharedFileList(
                None,
                self.share_dbs.get("streams")
            )

        elif share_type == "buddy":
            self.compressed_shares_buddy = slskmessages.SharedFileList(
                None,
                self.share_dbs.get("buddystreams")
            )

    def get_compressed_shares_message(self, share_type):
        """ Returns the compressed shares message. Creates a new one if necessary, e.g.
        if an individual file was added to our shares. """

        if (share_type == "normal" and self.newnormalshares
                or share_type == "buddy" and self.newbuddyshares):
            self.create_compressed_shares_message(share_type)

        if share_type == "normal":
            self.newnormalshares = False
            return self.compressed_shares_normal

        if share_type == "buddy":
            self.newbuddyshares = False
            return self.compressed_shares_buddy

        return None

    def compress_shares(self, share_type):
        """ Begin compressing the shares list. This compressed list will be used to
        quickly send our file list to users. """

        if share_type == "normal":
            self.compressed_shares_normal.built = None
            thread = threading.Thread(target=self.compressed_shares_normal.make_network_message)

        elif share_type == "buddy":
            self.compressed_shares_buddy.built = None
            thread = threading.Thread(target=self.compressed_shares_buddy.make_network_message)

        thread.name = "CompressShares"
        thread.daemon = True
        thread.start()

    def close_shares(self, share_type):

        if share_type == "normal":
            dbs = [
                "files", "streams", "wordindex",
                "fileindex", "mtimes"
            ]
        else:
            dbs = [
                "buddyfiles", "buddystreams", "buddywordindex",
                "buddyfileindex", "buddymtimes"
            ]

        for database in dbs:
            db_file = self.share_dbs.get(database)

            if db_file is not None:
                self.share_dbs[database].close()
                del self.share_dbs[database]

    def send_num_shared_folders_files(self):
        """ Send number publicly shared files to the server. """

        try:
            shared = self.share_dbs.get("files")
            index = self.share_dbs.get("fileindex")

            if shared is None or index is None:
                return

            try:
                sharedfolders = len(shared)
                sharedfiles = len(index)

            except TypeError:
                sharedfolders = len(list(shared))
                sharedfiles = len(list(index))

            self.queue.append(slskmessages.SharedFoldersFiles(sharedfolders, sharedfiles))

        except Exception as error:
            log.add(_("Failed to send number of shared files to the server: %s"), error)

    """ Scanning """

    def build_scanner_process(self, shared_folders=None, rebuild=False):

        import multiprocessing

        multiprocessing.set_start_method("spawn", force=True)

        scanner_queue = multiprocessing.Queue()
        scanner = Scanner(
            self.config,
            scanner_queue,
            shared_folders,
            rebuild
        )
        scanner = multiprocessing.Process(target=scanner.run)
        scanner.daemon = True
        return scanner, scanner_queue

    def rebuild_shares(self, use_thread=True):
        return self.rescan_shares(rebuild=True, use_thread=use_thread)

    def get_shared_folders(self):

        shared_folders = self.config.sections["transfers"]["shared"][:]
        shared_folders_buddy = self.config.sections["transfers"]["buddyshared"][:]

        if self.config.sections["transfers"]["sharedownloaddir"]:
            shared_folders.append((_('Downloaded'), self.config.sections["transfers"]["downloaddir"]))

        return (shared_folders, shared_folders_buddy)

    def process_scanner_messages(self, scanner, scanner_queue):

        while scanner.is_alive():
            # Cooldown
            time.sleep(0.5)

            while not scanner_queue.empty():
                item = scanner_queue.get()

                if isinstance(item, Exception):
                    return True

                if isinstance(item, tuple):
                    template, args, log_level = item
                    log.add(template, args, log_level)

                elif isinstance(item, float):
                    if self.ui_callback:
                        self.ui_callback.set_scan_progress(item)
                    else:
                        log.add(_("Progress: %s"), str(int(item * 100)) + " %")

        return False

    def rescan_shares(self, rebuild=False, use_thread=True):

        if self.rescanning:
            return None

        self.rescanning = True
        shared_folders = self.get_shared_folders()

        # Hand over database control to the scanner process
        self.close_shares("normal")
        self.close_shares("buddy")

        scanner, scanner_queue = self.build_scanner_process(shared_folders, rebuild)
        scanner.start()

        if use_thread:
            thread = threading.Thread(target=self._process_scanner, args=(scanner, scanner_queue))
            thread.name = "ProcessShareScanner"
            thread.daemon = True
            thread.start()
            return None

        return self._process_scanner(scanner, scanner_queue)

    def _process_scanner(self, scanner, scanner_queue):

        if self.ui_callback:
            self.ui_callback.show_scan_progress()
            self.ui_callback.set_scan_indeterminate()

        # Let the scanner process do its thing
        error = self.process_scanner_messages(scanner, scanner_queue)

        # Scanning done, load shares in the main process again
        self.load_shares(self.share_dbs, self.public_share_dbs)

        self.create_compressed_shares_message("normal")
        self.compress_shares("normal")

        self.load_shares(self.share_dbs, self.buddy_share_dbs)

        self.create_compressed_shares_message("buddy")
        self.compress_shares("buddy")

        if not error:
            if self.core and self.core.logged_in:
                """ Don't attempt to send file stats to the server before we're connected. If we skip the
                step here, it will be done once we log in instead ("login" function in pynicotine.py). """

                self.send_num_shared_folders_files()

        self.rescanning = False

        if self.ui_callback:
            self.ui_callback.hide_scan_progress()

        return error
