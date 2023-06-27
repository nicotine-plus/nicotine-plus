# COPYRIGHT (C) 2020-2023 Nicotine+ Contributors
# COPYRIGHT (C) 2016-2017 Michael Labouebe <gfarmerfr@free.fr>
# COPYRIGHT (C) 2016 Mutnick <muhing@yahoo.com>
# COPYRIGHT (C) 2009-2011 quinox <quinox@users.sf.net>
# COPYRIGHT (C) 2009 daelstorm <daelstorm@gmail.com>
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
import mmap
import os
import shutil
import stat
import sys
import time

from collections import defaultdict
from collections import deque
from os import SEEK_END
from os import SEEK_SET
from pickle import HIGHEST_PROTOCOL
from pickle import dumps
from pickle import Unpickler
from pickle import UnpicklingError
from struct import Struct
from threading import Thread

from pynicotine import rename_process
from pynicotine import slskmessages
from pynicotine.config import config
from pynicotine.core import core
from pynicotine.events import events
from pynicotine.external.tinytag import TinyTag
from pynicotine.logfacility import LogLevel
from pynicotine.logfacility import log
from pynicotine.utils import TRANSLATE_PUNCTUATION
from pynicotine.utils import UINT32_LIMIT
from pynicotine.utils import encode_path


class FileTypes:
    ARCHIVE = {
        "7z", "br", "bz2", "gz", "iso", "lz", "lzma", "rar", "tar", "tbz", "tbz2", "tgz", "xz", "zip", "zst"
    }
    AUDIO = {
        "aac", "ac3", "afc", "aifc", "aif", "aiff", "ape", "au", "bwav", "bwf", "dff", "dsd", "dsf", "dts", "flac",
        "gbs", "gym", "it", "m4a", "m4b", "mid", "midi", "mka", "mod", "mp1", "mp2", "mp3", "mp+", "mpc", "nsf", "nsfe",
        "ofr", "ofs", "oga", "ogg", "opus", "psf", "psf1", "psf2", "s3m", "sid", "spc", "spx", "ssf", "tak", "tta",
        "wav", "vgm", "vgz", "wma", "vqf", "wv", "xm"
    }
    EXECUTABLE = {
        "apk", "appimage", "bat", "deb", "dmg", "flatpak", "exe", "jar", "msi", "pkg", "rpm", "sh"
    }
    IMAGE = {
        "apng", "avif", "bmp", "gif", "heic", "heif", "ico", "jfif", "jp2", "jpg", "jpe", "jpeg", "jxl", "png", "psd",
        "raw", "svg", "svgz", "tif", "tiff", "webp"
    }
    DOCUMENT_TEXT = {
        "cue", "csv", "doc", "docx", "epub", "htm", "html", "m3u", "m3u8", "md5", "log", "lrc", "md", "mks", "mobi",
        "nfo", "odp", "ods", "odt", "opf", "oxps", "pdf", "ppt", "pptx", "ps", "rst", "rtf", "sfv", "sha1", "sha256",
        "srt", "txt", "xls", "xlsx", "xps"
    }
    VIDEO = {
        "3gp", "amv", "asf", "avi", "f4v", "flv", "m2ts", "m2v", "m4p", "m4v", "mov", "mp4", "mpe", "mpeg", "mpg",
        "mkv", "mts", "ogv", "ts", "vob", "webm", "wmv"
    }


class RestrictedUnpickler(Unpickler):
    """Don't allow code execution from pickles."""

    def find_class(self, module, name):
        # Forbid all globals
        raise UnpicklingError(f"global '{module}.{name}' is forbidden")


class DatabaseError(Exception):
    pass


class Database:
    """Custom key-value database format for Nicotine+ shares."""

    FILE_HEADER = b"N+DB"
    LENGTH_DATA_SIZE = 8
    PACK_LENGTHS = Struct("!II").pack
    UNPACK_LENGTHS = Struct("!II").unpack_from

    def __init__(self, file_path, overwrite=True):

        folder_path = os.path.dirname(file_path)

        if not os.path.exists(folder_path):
            os.makedirs(folder_path)

        if overwrite and os.path.exists(file_path):
            os.remove(file_path)

        self._value_offsets = self._load_value_offsets(file_path)

        if overwrite:
            self._file_handle = open(file_path, mode="ab+")  # pylint: disable=consider-using-with
        else:
            with open(file_path, mode="rb") as file_handle:
                self._file_handle = mmap.mmap(file_handle.fileno(), length=0, access=mmap.ACCESS_READ)

        self._file_offset = self._file_handle.seek(0, SEEK_END)
        self._overwrite = overwrite

    def _load_value_offsets(self, file_path):

        value_offsets = {}

        with open(file_path, "ab+") as file_handle:
            file_size = os.fstat(file_handle.fileno()).st_size

            if not file_size:
                file_handle.write(self.FILE_HEADER)
                return value_offsets

            file_handle.seek(0)

            with mmap.mmap(file_handle.fileno(), length=0, access=mmap.ACCESS_READ) as contents:
                contents_view = memoryview(contents)

                try:
                    file_header_length = current_offset = len(self.FILE_HEADER)

                    if contents_view[:file_header_length] != self.FILE_HEADER:
                        raise DatabaseError("Not a database file")

                    while current_offset < file_size:
                        key_offset = (current_offset + self.LENGTH_DATA_SIZE)
                        key_length, value_length = self.UNPACK_LENGTHS(contents_view[current_offset:key_offset])
                        value_offset = (key_offset + key_length)
                        key = str(contents_view[key_offset:value_offset], encoding="utf-8")

                        value_offsets[key] = value_offset
                        current_offset = (value_offset + value_length)
                finally:
                    contents_view.release()

        return value_offsets

    def __contains__(self, key):
        return key in self._value_offsets

    def __iter__(self):
        for key in self._value_offsets:
            yield key

    def __len__(self):
        return len(self._value_offsets)

    def __getitem__(self, key):

        value_offset = self._value_offsets[key]

        self._file_handle.seek(value_offset, SEEK_SET)
        return RestrictedUnpickler(self._file_handle).load()

    def __setitem__(self, key, value):

        encoded_key = str(key).encode("utf-8")
        pickled_value = dumps(value, protocol=HIGHEST_PROTOCOL)

        key_length = len(encoded_key)
        length_data = self.PACK_LENGTHS(key_length, len(pickled_value))
        item_data = (length_data + encoded_key + pickled_value)

        self._file_handle.write(item_data)

        self._value_offsets[key] = self._file_offset + self.LENGTH_DATA_SIZE + key_length
        self._file_offset += len(item_data)

    def get(self, key, default=None):

        if key in self._value_offsets:
            return self[key]

        return default

    def update(self, obj):
        for key, value in obj.items():
            self[key] = value

    def close(self):

        if self._overwrite:
            os.fsync(self._file_handle)

        self._file_handle.close()


class Scanner:
    """Separate process responsible for building shares.

    It handles scanning of folders and files, as well as building
    databases and writing them to disk.
    """

    def __init__(self, config_obj, queue, shared_folders, share_db_paths, init=False, rescan=True,
                 rebuild=False, is_buddy_visible=False):

        self.config = config_obj
        self.queue = queue
        self.shared_folders, self.shared_buddy_folders = shared_folders
        self.share_dbs = {}
        self.share_db_paths = share_db_paths
        self.init = init
        self.rescan = rescan
        self.rebuild = rebuild
        self.is_buddy_visible = is_buddy_visible
        self.tinytag = None
        self.version = 3

    def run(self):

        try:
            rename_process(b"nicotine-scan")

            shares_loaded = Shares.load_shares(self.share_dbs, self.share_db_paths, remove_failed=True)
            old_mtimes = self.share_dbs.get("mtimes")
            share_version = None

            if old_mtimes is not None:
                share_version = old_mtimes.get("__NICOTINE_SHARE_VERSION__")

            if not shares_loaded or share_version != self.version:
                # Failed to load shares or version is invalid, rebuild
                self.rescan = self.rebuild = True

            if self.init:
                self.create_compressed_shares()

            if self.rescan:
                start_num_folders = len(self.share_dbs.get("buddystreams", {}))

                self.queue.put((_("%(num)s folders found before rescan"), {"num": start_num_folders}, LogLevel.DEFAULT))
                self.queue.put((_("Rebuilding shares…") if self.rebuild else _("Rescanning shares…"),
                               None, LogLevel.DEFAULT))

                num_public_folders, wordindex, start_file_index = self.rescan_dirs("public", rebuild=self.rebuild)
                num_buddy_folders, _wordindex, _start_file_index = self.rescan_dirs(
                    "buddy", old_wordindex=wordindex, rebuild=self.rebuild, start_file_index=start_file_index)

                self.queue.put(
                    (_("Rescan complete: %(num)s folders found"), {"num": num_public_folders + num_buddy_folders},
                     LogLevel.DEFAULT)
                )

                self.create_compressed_shares()

        except Exception:
            from traceback import format_exc

            self.queue.put((
                _("Serious error occurred while rescanning shares. If this problem persists, "
                  "delete %(dir)s/*.db and try again. If that doesn't help, please file a bug "
                  "report with this stack trace included: %(trace)s"), {
                    "dir": self.config.data_folder_path,
                    "trace": "\n" + format_exc()
                }, LogLevel.DEFAULT
            ))
            self.queue.put(Exception("Scanning failed"))

        finally:
            Shares.close_shares(self.share_dbs)

    def create_compressed_shares_message(self, share_type):
        """Create a message that will later contain a compressed list of our
        shares."""

        streams = self.share_dbs.get("streams")
        buddy_streams = self.share_dbs.get("buddystreams")

        if share_type == "public" and not self.is_buddy_visible:
            buddy_streams = None

        compressed_shares = slskmessages.SharedFileListResponse(
            shares=streams, buddy_shares=buddy_streams, share_type=share_type
        )
        compressed_shares.make_network_message()
        compressed_shares.list = compressed_shares.privatelist = []
        compressed_shares.type = share_type

        self.queue.put(compressed_shares)

    def create_compressed_shares(self):
        self.create_compressed_shares_message("public")
        self.create_compressed_shares_message("buddy")

    def create_db_file(self, destination):

        share_db = self.share_dbs.get(destination)

        if share_db is not None:
            share_db.close()

        db_path = os.path.join(self.config.data_folder_path, destination + ".db")
        self.remove_db_file(db_path)

        return Database(encode_path(db_path))

    @staticmethod
    def remove_db_file(db_path):

        db_path_encoded = encode_path(db_path)

        if os.path.isfile(db_path_encoded):
            os.remove(db_path_encoded)

        elif os.path.isdir(db_path_encoded):
            shutil.rmtree(db_path_encoded)

    def real2virtual(self, path):

        path = path.replace("/", "\\")

        for shares in (self.config.sections["transfers"]["shared"], self.config.sections["transfers"]["buddyshared"]):
            for virtual, real, *_unused in shares:
                # Remove slashes from share name to avoid path conflicts
                virtual = virtual.replace("/", "_").replace("\\", "_")

                real = real.replace("/", "\\")
                if path == real:
                    return virtual

                # Use rstrip to remove trailing separator from root folders
                real = real.rstrip("\\") + "\\"

                if path.startswith(real):
                    path_no_prefix = path[len(real):]
                    virtualpath = f"{virtual}\\{path_no_prefix}"
                    return virtualpath

        return "__INTERNAL_ERROR__" + path

    def set_shares(self, share_type=None, files=None, streams=None, mtimes=None, wordindex=None):

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

            if share_type and share_type != "public":
                destination = f"{share_type}{destination}"

            try:
                self.share_dbs[destination] = share_db = self.create_db_file(destination)
                share_db.update(source)

            except Exception as error:
                self.queue.put((_("Can't save %(filename)s: %(error)s"),
                                {"filename": destination + ".db", "error": error}, LogLevel.DEFAULT))
                return

    def rescan_dirs(self, share_type, old_wordindex=None, rebuild=False, start_file_index=0):

        # Reset progress
        self.queue.put("indeterminate")

        if share_type == "buddy":
            shared_folders = (os.path.normpath(x[1]) for x in self.shared_buddy_folders)
            prefix = "buddy"
        else:
            shared_folders = (os.path.normpath(x[1]) for x in self.shared_folders)
            prefix = ""

        new_files = {}
        new_streams = {}
        new_mtimes = {}
        new_wordindex = defaultdict(list)

        old_files = self.share_dbs.get(prefix + "files", {})
        old_mtimes = self.share_dbs.get(prefix + "mtimes", {})

        for folder in shared_folders:
            # Get mtimes for top-level shared folders, then every subfolder
            try:
                files, streams, mtimes, wordindex = self.get_files_list(
                    folder, old_mtimes, old_files, rebuild, start_file_index=start_file_index
                )
                new_files = {**new_files, **files}
                new_streams = {**new_streams, **streams}
                new_mtimes = {**new_mtimes, **mtimes}
                start_file_index += len(new_files)

                for key, values in wordindex.items():
                    new_wordindex[key].extend(values)

            except OSError as error:
                self.queue.put((_("Error while scanning folder %(path)s: %(error)s"), {
                    "path": folder,
                    "error": error
                }, LogLevel.DEFAULT))

        # Save data to databases
        new_mtimes["__NICOTINE_SHARE_VERSION__"] = self.version
        num_folders = len(new_streams)
        self.set_shares(share_type, files=new_files, streams=new_streams, mtimes=new_mtimes)

        # Save data to databases
        if old_wordindex is not None:
            for key, values in new_wordindex.items():
                old_wordindex[key].extend(values)

            self.set_shares(wordindex=old_wordindex)

        for dictionary in (new_files, new_streams, new_mtimes):
            dictionary.clear()

        gc.collect()
        return num_folders, new_wordindex, start_file_index

    @staticmethod
    def is_hidden(folder, filename=None, entry=None):
        """Stop sharing any dot/hidden folders/files."""

        # If the last folder in the path starts with a dot, or is a Synology extended
        # attribute folder, we exclude it
        if filename is None:
            last_folder = os.path.basename(folder)

            if last_folder.startswith(".") or last_folder == "@eaDir":
                return True

        # If we're asked to check a file we exclude it if it start with a dot
        if filename is not None and filename.startswith("."):
            return True

        # Check if file is marked as hidden on Windows
        if sys.platform == "win32":
            if len(folder) == 3 and folder[1] == ":" and folder[2] == os.sep:
                # Root folders are marked as hidden, but we allow scanning them
                return False

            if entry is None:
                if filename is not None:
                    entry_stat = os.stat(encode_path(os.path.join(folder, filename)))
                else:
                    entry_stat = os.stat(encode_path(folder))
            else:
                entry_stat = entry.stat()

            return entry_stat.st_file_attributes & stat.FILE_ATTRIBUTE_HIDDEN

        return False

    def get_files_list(self, shared_folder, oldmtimes, oldfiles, rebuild=False, start_file_index=0):
        """Get a list of files with their filelength, bitrate and track length
        in seconds."""

        files = {}
        streams = {}
        mtimes = {}
        wordindex = defaultdict(list)

        folders = deque([shared_folder])
        file_index = start_file_index - 1

        while folders:
            folder = folders.pop()
            virtual_folder = self.real2virtual(folder)
            file_list = []

            try:
                with os.scandir(encode_path(folder, prefix=False)) as entries:
                    for entry in entries:
                        basename = entry.name.decode("utf-8", "replace")
                        path = os.path.join(folder, basename)

                        if entry.is_dir():
                            if self.is_hidden(path, entry=entry):
                                continue

                            folders.append(path)
                            continue

                        try:
                            if self.is_hidden(folder, basename, entry):
                                continue

                            file_stat = entry.stat()
                            mtimes[path] = file_mtime = file_stat.st_mtime
                            virtual_file_path = f"{virtual_folder}\\{basename}"

                            if not rebuild and file_mtime == oldmtimes.get(path) and path in oldfiles:
                                full_path_file_data = oldfiles[path]
                            else:
                                full_path_file_data = self.get_file_info(virtual_file_path, path, file_stat)

                            basename_file_data = full_path_file_data[:]
                            basename_file_data[0] = basename
                            file_list.append(basename_file_data)

                            files[path] = full_path_file_data
                            file_index += 1

                            for k in set(virtual_file_path.lower().translate(TRANSLATE_PUNCTUATION).split()):
                                wordindex[k].append(file_index)

                        except Exception as error:
                            self.queue.put((_("Error while scanning file %(path)s: %(error)s"),
                                           {"path": entry.path, "error": error}, LogLevel.DEFAULT))

            except OSError as error:
                self.queue.put((_("Error while scanning folder %(path)s: %(error)s"),
                               {"path": folder, "error": error}, LogLevel.DEFAULT))

            streams[virtual_folder] = self.get_dir_stream(file_list)

        return files, streams, mtimes, wordindex

    def get_audio_tag(self, encoded_file_path, size):

        parser_class = TinyTag._get_parser_for_filename(encoded_file_path)  # pylint: disable=protected-access

        if parser_class is None:
            return None

        with open(encoded_file_path, "rb") as file_handle:
            tag = parser_class(file_handle, size)
            tag.load(tags=False, duration=True, image=False)

        return tag

    def get_file_info(self, virtual_file_path, file_path, file_stat):
        """Get file metadata."""

        tag = None
        quality = None
        duration = None
        encoded_file_path = encode_path(file_path)
        size = file_stat.st_size

        # We skip metadata scanning of files without meaningful content
        if size > 128:
            try:
                tag = self.get_audio_tag(encoded_file_path, size)

            except Exception as error:
                self.queue.put((_("Error while scanning metadata for file %(path)s: %(error)s"),
                               {"path": file_path, "error": error}, LogLevel.DEFAULT))

        if tag is not None:
            bitrate = tag.bitrate
            samplerate = tag.samplerate
            bitdepth = tag.bitdepth
            duration = tag.duration

            if bitrate is not None:
                bitrate = int(bitrate + 0.5)  # Round the value with minimal performance loss

                if not UINT32_LIMIT > bitrate >= 0:
                    bitrate = None

            if duration is not None:
                duration = int(duration)

                if not UINT32_LIMIT > duration >= 0:
                    duration = None

            if samplerate is not None:
                samplerate = int(samplerate)

                if not UINT32_LIMIT > samplerate >= 0:
                    samplerate = None

            if bitdepth is not None:
                bitdepth = int(bitdepth)

                if not UINT32_LIMIT > bitdepth >= 0:
                    bitdepth = None

            quality = (bitrate, int(tag.is_vbr), samplerate, bitdepth)

        return [virtual_file_path, size, quality, duration]

    @staticmethod
    def get_dir_stream(folder):
        """Pack all files and metadata in folder."""

        stream = bytearray()
        stream.extend(slskmessages.FileListMessage.pack_uint32(len(folder)))

        for fileinfo in folder:
            stream.extend(slskmessages.FileListMessage.pack_file_info(fileinfo))

        return bytes(stream)


class Shares:

    def __init__(self):

        self.share_dbs = {}
        self.requested_share_times = {}
        self.pending_network_msgs = []
        self.rescanning = False
        self.compressed_shares = {
            "public": slskmessages.SharedFileListResponse(),
            "buddy": slskmessages.SharedFileListResponse()
        }
        self.file_path_index = []

        self.convert_shares()
        self.share_db_paths = [
            ("files", os.path.join(config.data_folder_path, "files.db")),
            ("streams", os.path.join(config.data_folder_path, "streams.db")),
            ("wordindex", os.path.join(config.data_folder_path, "wordindex.db")),
            ("buddyfiles", os.path.join(config.data_folder_path, "buddyfiles.db")),
            ("buddystreams", os.path.join(config.data_folder_path, "buddystreams.db"))
        ]
        self.scanner_share_db_paths = [
            ("mtimes", os.path.join(config.data_folder_path, "mtimes.db")),
            ("buddymtimes", os.path.join(config.data_folder_path, "buddymtimes.db"))
        ]

        for event_name, callback in (
            ("folder-contents-request", self._folder_contents_request),
            ("quit", self._quit),
            ("server-disconnect", self._server_disconnect),
            ("server-login", self._server_login),
            ("shared-file-list-request", self._shared_file_list_request),
            ("start", self._start)
        ):
            events.connect(event_name, callback)

    def _start(self):

        rescan_startup = (config.sections["transfers"]["rescanonstartup"]
                          and not config.need_config())

        self.rescan_shares(init=True, rescan=rescan_startup)

    def _quit(self):
        self.close_shares(self.share_dbs)

    def _server_login(self, _msg):
        self.send_num_shared_folders_files()

    def _server_disconnect(self, _msg):
        self.requested_share_times.clear()
        self.pending_network_msgs.clear()

    # Shares-related Actions #

    def virtual2real(self, path):

        path = path.replace("/", os.sep).replace("\\", os.sep)

        for shares in (config.sections["transfers"]["shared"], config.sections["transfers"]["buddyshared"]):
            for virtual, real, *_unused in shares:
                # Remove slashes from share name to avoid path conflicts
                virtual = virtual.replace("/", "_").replace("\\", "_")
                real = os.path.normpath(real)

                if path == virtual:
                    return real

                if path.startswith(virtual + os.sep):
                    realpath = real.rstrip(os.sep) + path[len(virtual):]
                    return realpath

        return "__INTERNAL_ERROR__" + path

    def convert_shares(self):
        """Convert fs-based shared to virtual shared (pre 1.4.0)"""

        def _convert_to_virtual(shared_folder):
            if isinstance(shared_folder, tuple):
                return shared_folder

            virtual = shared_folder.replace("/", "_").replace("\\", "_").strip("_")
            log.add("Renaming shared folder '%s' to '%s'. A rescan of your share is required.",
                    (shared_folder, virtual))
            return virtual, shared_folder

        config.sections["transfers"]["shared"] = [_convert_to_virtual(x)
                                                  for x in config.sections["transfers"]["shared"]]
        config.sections["transfers"]["buddyshared"] = [_convert_to_virtual(x)
                                                       for x in config.sections["transfers"]["buddyshared"]]

    @classmethod
    def load_shares(cls, shares, dbs, remove_failed=False):

        errors = []
        exception = None

        for destination, db_path in dbs:
            db_path_encoded = encode_path(db_path)

            try:
                if os.path.exists(db_path_encoded):
                    shares[destination] = Database(db_path_encoded, overwrite=False)

            except Exception:
                from traceback import format_exc

                errors.append(db_path)
                exception = format_exc()

                if remove_failed:
                    Scanner.remove_db_file(db_path)

        if not errors:
            return True

        log.add(_("Failed to process the following databases: %(names)s"), {
            "names": "\n".join(errors)
        })
        log.add(exception)
        return False

    def load_shares_instance(self, shares, dbs, remove_failed=False):

        self.load_shares(shares, dbs, remove_failed=remove_failed)

        self.file_path_index = tuple(
            list(self.share_dbs.get("files", {})) + list(self.share_dbs.get("buddyfiles", {}))
        )

    def file_is_shared(self, username, virtualfilename, realfilename):

        log.add_transfer("Checking if file is shared: %(virtual_name)s with real path %(path)s", {
            "virtual_name": virtualfilename,
            "path": realfilename
        })

        shared_files = self.share_dbs.get("files")
        bshared_files = self.share_dbs.get("buddyfiles")
        file_is_shared = False

        if not realfilename.startswith("__INTERNAL_ERROR__"):
            if bshared_files is not None:
                user_data = core.userlist.buddies.get(username)

                if user_data:
                    # Check if buddy is trusted
                    if config.sections["transfers"]["buddysharestrustedonly"] and not user_data.is_trusted:
                        pass

                    elif realfilename in bshared_files:
                        file_is_shared = True

            if not file_is_shared and shared_files is not None and realfilename in shared_files:
                file_is_shared = True

        if not file_is_shared:
            log.add_transfer(("File is not present in the database of shared files, not sharing: "
                              "%(virtual_name)s with real path %(path)s"), {
                "virtual_name": virtualfilename,
                "path": realfilename
            })
            return False

        return True

    def get_shared_folders(self):

        shared_folders = config.sections["transfers"]["shared"]
        shared_folders_buddy = config.sections["transfers"]["buddyshared"]

        return shared_folders, shared_folders_buddy

    def get_normalized_virtual_name(self, virtual_name, shared_folders=None):

        if shared_folders is None:
            public_shares, buddy_shares = self.get_shared_folders()
            shared_folders = (public_shares + buddy_shares)

        # Provide a default name for root folders
        if not virtual_name:
            virtual_name = "Shared"

        # Remove slashes from share name to avoid path conflicts
        virtual_name = virtual_name.replace("/", "_").replace("\\", "_").strip(' "')
        new_virtual_name = str(virtual_name)

        # Check if virtual share name is already in use
        counter = 1
        while new_virtual_name in (x[0] for x in shared_folders):
            new_virtual_name = f"{virtual_name}{counter}"
            counter += 1

        return new_virtual_name

    def add_share(self, folder_path, group_name="public", virtual_name=None, share_groups=None, validate_path=True):

        if validate_path and not os.access(encode_path(folder_path), os.R_OK):
            return None

        if share_groups is None:
            share_groups = self.get_shared_folders()

        # Remove previous share with same path if present
        core.shares.remove_share(folder_path, share_groups=share_groups)

        public_shares, buddy_shares = share_groups
        virtual_name = core.shares.get_normalized_virtual_name(
            virtual_name or os.path.basename(folder_path), shared_folders=(public_shares + buddy_shares)
        )
        shares = buddy_shares if group_name == "buddy" else public_shares

        shares.append((virtual_name, os.path.normpath(folder_path)))
        return virtual_name

    def remove_share(self, virtual_name_or_folder_path, share_groups=None):

        if share_groups is None:
            share_groups = self.get_shared_folders()

        normalized_folder_path = os.path.normpath(virtual_name_or_folder_path)

        for shares in share_groups:
            for virtual_name, folder_path in shares:
                if (virtual_name_or_folder_path in (virtual_name, folder_path)
                        or folder_path == normalized_folder_path):
                    shares.remove((virtual_name, folder_path))
                    return True

        return False

    @staticmethod
    def close_shares(share_dbs):
        for database in share_dbs.copy():
            share_dbs[database].close()
            del share_dbs[database]

    def send_num_shared_folders_files(self):
        """Send number publicly shared files to the server."""

        if not (core and core.user_status != slskmessages.UserStatus.OFFLINE):
            return

        if self.rescanning:
            return

        try:
            shared = self.share_dbs.get("streams")
            index = self.share_dbs.get("files")

            if shared is None or index is None:
                shared = {}
                index = []

            sharedfolders = len(shared)
            sharedfiles = len(index)

            core.send_message_to_server(slskmessages.SharedFoldersFiles(sharedfolders, sharedfiles))

        except Exception as error:
            log.add(_("Failed to send number of shared files to the server: %s"), error)

    # Scanning #

    def build_scanner_process(self, shared_folders=None, init=False, rescan=True, rebuild=False):

        import multiprocessing

        context = multiprocessing.get_context(method="spawn")
        scanner_queue = context.Queue()
        scanner_obj = Scanner(
            config,
            scanner_queue,
            shared_folders,
            self.share_db_paths + self.scanner_share_db_paths,
            init,
            rescan,
            rebuild,
            is_buddy_visible=config.sections["transfers"]["buddy_shares_visible_everyone"]
        )
        scanner = context.Process(target=scanner_obj.run, daemon=True)
        return scanner, scanner_queue

    def rebuild_shares(self, use_thread=True):
        return self.rescan_shares(rebuild=True, use_thread=use_thread)

    def process_scanner_messages(self, scanner, scanner_queue, emit_event):

        while scanner.is_alive():
            # Cooldown
            time.sleep(0.05)

            while not scanner_queue.empty():
                item = scanner_queue.get()

                if isinstance(item, Exception):
                    return True

                if isinstance(item, tuple):
                    template, args, log_level = item
                    log.add(template, msg_args=args, level=log_level)

                elif item == "indeterminate":
                    emit_event("show-scan-progress")

                elif isinstance(item, slskmessages.SharedFileListResponse):
                    self.compressed_shares[item.type] = item

        return False

    def check_shares_available(self):

        share_groups = self.get_shared_folders()
        unavailable_shares = []

        for share in share_groups:
            for virtual_name, folder_path, *_unused in share:
                folder_path = os.path.normpath(folder_path)

                if not os.access(encode_path(folder_path), os.R_OK):
                    unavailable_shares.append((virtual_name, folder_path))

        return unavailable_shares

    def rescan_shares(self, init=False, rescan=True, rebuild=False, use_thread=True, force=False):

        if self.rescanning:
            return None

        if rescan and not force:
            # Verify all shares are mounted before allowing destructive rescan
            unavailable_shares = self.check_shares_available()

            if unavailable_shares:
                log.add(_("Rescan aborted due to unavailable shares: %s"), unavailable_shares)
                rescan = False

                events.emit("shares-unavailable", unavailable_shares)

                if not init:
                    return None

        # Hand over database control to the scanner process
        self.rescanning = True
        self.close_shares(self.share_dbs)

        shared_folders = self.get_shared_folders()
        scanner, scanner_queue = self.build_scanner_process(shared_folders, init, rescan, rebuild)
        scanner.start()

        if use_thread:
            Thread(
                target=self._process_scanner, args=(scanner, scanner_queue, events.emit_main_thread),
                name="ProcessShareScanner", daemon=True
            ).start()
            return None

        return self._process_scanner(scanner, scanner_queue, events.emit)

    def _process_scanner(self, scanner, scanner_queue, emit_event):

        # Let the scanner process do its thing
        error = self.process_scanner_messages(scanner, scanner_queue, emit_event)
        emit_event("hide-scan-progress")

        # Scanning done, load shares in the main process again
        self.load_shares_instance(self.share_dbs, self.share_db_paths)
        self.rescanning = False

        if not error:
            self.send_num_shared_folders_files()

        # Process any file transfer queue requests that arrived while scanning
        if self.pending_network_msgs:
            core.send_message_to_network_thread(slskmessages.EmitNetworkMessageEvents(self.pending_network_msgs[:]))
            self.pending_network_msgs.clear()

        return error

    # Network Messages #

    def _shared_file_list_request(self, msg):
        """Peer code 4."""

        username = msg.init.target_user
        request_time = time.time()

        if username in self.requested_share_times and request_time < self.requested_share_times[username] + 0.4:
            # Ignoring request, because it's less than half a second since the
            # last one by this user
            return

        self.requested_share_times[username] = request_time

        log.add(_("User %(user)s is browsing your list of shared files"), {"user": username})

        ip_address, _port = msg.init.addr
        checkuser, reason = core.network_filter.check_user(username, ip_address)

        if not checkuser:
            message = core.ban_message % reason
            core.privatechat.send_automatic_message(username, message)

        shares_list = None

        if checkuser == 1:
            # Send public shares
            shares_list = self.compressed_shares.get("public")

        elif checkuser == 2:
            # Send buddy shares
            shares_list = self.compressed_shares.get("buddy")

        if not shares_list:
            # Nyah, nyah
            shares_list = slskmessages.SharedFileListResponse()

        core.send_message_to_peer(username, shares_list)

    def _folder_contents_request(self, msg):
        """Peer code 36."""

        ip_address, _port = msg.init.addr
        username = msg.init.target_user
        checkuser, reason = core.network_filter.check_user(username, ip_address)

        if not checkuser:
            message = core.ban_message % reason
            core.privatechat.send_automatic_message(username, message)
            return

        is_buddy_share_visible = config.sections["transfers"]["buddy_shares_visible_everyone"]
        public_shares = self.share_dbs.get("streams")
        buddy_shares = self.share_dbs.get("buddystreams")
        folder_data = None

        try:
            if (checkuser == 2 or is_buddy_share_visible) and msg.dir in buddy_shares:
                folder_data = buddy_shares[msg.dir]

            elif msg.dir in public_shares:
                folder_data = public_shares[msg.dir]

        except Exception as error:
            log.add(_("Failed to fetch the shared folder %(folder)s: %(error)s"),
                    {"folder": msg.dir, "error": error})

        core.send_message_to_peer(
            username, slskmessages.FolderContentsResponse(directory=msg.dir, token=msg.token, shares=folder_data))
