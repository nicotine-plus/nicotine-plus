# COPYRIGHT (C) 2020-2024 Nicotine+ Contributors
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
from pynicotine.config import config
from pynicotine.core import core
from pynicotine.events import events
from pynicotine.external.tinytag import TinyTag
from pynicotine.logfacility import log
from pynicotine.slskmessages import FileListMessage
from pynicotine.slskmessages import FolderContentsResponse
from pynicotine.slskmessages import GetUserStats
from pynicotine.slskmessages import SharedFileListResponse
from pynicotine.slskmessages import SharedFoldersFiles
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
    DOCUMENT = {
        "doc", "docx", "epub", "mobi", "odp", "ods", "odt", "opf", "oxps", "pdf", "ppt", "pptx", "rtf", "xls", "xlsx",
        "xps"
    }
    TEXT = {
        "cue", "csv", "htm", "html", "m3u", "m3u8", "md5", "log", "lrc", "md", "mks", "nfo", "ps", "rst", "sfv",
        "sha1", "sha256", "srt", "txt"
    }
    VIDEO = {
        "3gp", "amv", "asf", "avi", "f4v", "flv", "m2ts", "m2v", "m4p", "m4v", "mov", "mp4", "mpe", "mpeg", "mpg",
        "mkv", "mts", "ogv", "ts", "vob", "webm", "wmv"
    }


class PermissionLevel:
    PUBLIC = "public"
    BUDDY = "buddy"
    TRUSTED = "trusted"
    BANNED = "banned"


class RestrictedUnpickler(Unpickler):
    """Don't allow code execution from pickles."""

    def find_class(self, module, name):
        # Forbid all globals
        raise UnpicklingError(f"global '{module}.{name}' is forbidden")


class DatabaseError(Exception):
    pass


class Database:
    """Custom key-value database format for Nicotine+ shares."""

    __slots__ = ("_value_offsets", "_file_handle", "_file_offset", "_overwrite")

    FILE_SIGNATURE = b"DBN+"
    VERSION = 3
    LENGTH_DATA_SIZE = 8
    PACK_LENGTHS = Struct("!II").pack
    UNPACK_LENGTHS = Struct("!II").unpack_from
    PICKLE_PROTOCOL = min(HIGHEST_PROTOCOL, 5)  # Use version 5 when available

    def __init__(self, file_path, overwrite=True):

        folder_path = os.path.dirname(file_path)
        mode = "ab+" if overwrite else "rb"

        if not os.path.exists(folder_path):
            os.makedirs(folder_path)

        if overwrite and os.path.exists(file_path):
            os.remove(file_path)

        self._value_offsets = self._load_value_offsets(file_path, mode)

        if overwrite:
            self._file_handle = open(file_path, mode)  # pylint: disable=consider-using-with
        else:
            with open(file_path, mode) as file_handle:
                self._file_handle = mmap.mmap(file_handle.fileno(), length=0, access=mmap.ACCESS_READ)

        self._file_offset = self._file_handle.seek(0, SEEK_END)
        self._overwrite = overwrite

    def _parse_content(self, content, total_size):

        value_offsets = {}
        file_signature_length = len(self.FILE_SIGNATURE)

        if content[:file_signature_length] != self.FILE_SIGNATURE:
            raise DatabaseError("Not a database file")

        if content[file_signature_length:file_signature_length + 1][0] != self.VERSION:
            raise DatabaseError("Incompatible version")

        current_offset = (file_signature_length + 1)

        while current_offset < total_size:
            key_offset = (current_offset + self.LENGTH_DATA_SIZE)
            key_length, value_length = self.UNPACK_LENGTHS(content[current_offset:key_offset])
            value_offset = (key_offset + key_length)
            key = content[key_offset:value_offset].tobytes().decode("utf-8")

            value_offsets[key] = value_offset
            current_offset = (value_offset + value_length)

        return value_offsets

    def _load_value_offsets(self, file_path, mode):

        value_offsets = {}

        with open(file_path, mode) as file_handle:  # pylint: disable=unspecified-encoding
            file_size = os.fstat(file_handle.fileno()).st_size

            if not file_size:
                file_handle.write(self.FILE_SIGNATURE)
                file_handle.write(bytes([self.VERSION]))
                return value_offsets

            file_handle.seek(0)

            with mmap.mmap(file_handle.fileno(), length=0, access=mmap.ACCESS_READ) as content:
                value_offsets = self._parse_content(memoryview(content), file_size)

        return value_offsets

    def __contains__(self, key):
        return key in self._value_offsets

    def __iter__(self):
        yield from self._value_offsets

    def __len__(self):
        return len(self._value_offsets)

    def __getitem__(self, key):

        value_offset = self._value_offsets[key]

        self._file_handle.seek(value_offset, SEEK_SET)
        return RestrictedUnpickler(self._file_handle).load()

    def __setitem__(self, key, value):

        encoded_key = key.encode("utf-8")
        pickled_value = dumps(value, protocol=self.PICKLE_PROTOCOL)

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

    __slots__ = ("queue", "share_groups", "share_dbs", "share_db_paths", "init",
                 "rescan", "rebuild", "reveal_buddy_shares", "reveal_trusted_shares",
                 "files", "streams", "mtimes", "word_index", "processed_share_names",
                 "processed_share_paths", "current_file_index", "current_folder_count")

    HIDDEN_FOLDER_NAMES = {"@eaDir", "#recycle", "#snapshot"}

    def __init__(self, queue, share_groups, share_db_paths, init=False, rescan=True,
                 rebuild=False, reveal_buddy_shares=False, reveal_trusted_shares=False):

        self.queue = queue
        self.share_groups = share_groups
        self.share_dbs = {}
        self.share_db_paths = share_db_paths
        self.init = init
        self.rescan = rescan
        self.rebuild = rebuild
        self.reveal_buddy_shares = reveal_buddy_shares
        self.reveal_trusted_shares = reveal_trusted_shares
        self.files = {}
        self.streams = {}
        self.mtimes = {}
        self.word_index = defaultdict(list)
        self.processed_share_names = set()
        self.processed_share_paths = set()
        self.current_file_index = 0
        self.current_folder_count = 0

    def run(self):

        try:
            rename_process(b"nicotine-scan")

            if self.init:
                try:
                    self.create_compressed_shares()
                    self.create_file_path_index()

                except Exception:
                    # Failed to load shares or version is invalid, rebuild
                    self.rescan = self.rebuild = True

                self.queue.put("initialized")

            if self.rescan:
                self.queue.put("rescanning")
                self.queue.put((_("Rebuilding shares…") if self.rebuild else _("Rescanning shares…"), None))

                # Clear previous word index to prevent inconsistent state if the scanner fails
                self.set_shares(word_index={})

                # Scan shares
                for permission_level in (
                    PermissionLevel.PUBLIC,
                    PermissionLevel.BUDDY,
                    PermissionLevel.TRUSTED
                ):
                    self.rescan_dirs(permission_level)

                self.set_shares(word_index=self.word_index)
                self.word_index.clear()

                self.create_compressed_shares()
                self.create_file_path_index()

                self.queue.put(
                    (_("Rescan complete: %(num)s folders found"),
                     {"num": self.current_folder_count})
                )

        except Exception:
            from traceback import format_exc

            self.queue.put((
                _("Serious error occurred while rescanning shares. If this problem persists, "
                  "delete %(dir)s/*.dbn and try again. If that doesn't help, please file a bug "
                  "report with this stack trace included: %(trace)s"), {
                    "dir": os.path.dirname(next(iter(self.share_db_paths.values()))),
                    "trace": "\n" + format_exc()
                }
            ))
            self.queue.put(Exception("Scanning failed"))

        finally:
            Shares.close_shares(self.share_dbs)

    def create_compressed_shares_message(self, permission_level):
        """Create a message that will later contain a compressed list of our
        shares."""

        public_streams = self.share_dbs["public_streams"]
        buddy_streams = self.share_dbs["buddy_streams"]
        trusted_streams = self.share_dbs["trusted_streams"]

        if permission_level == PermissionLevel.PUBLIC and not self.reveal_buddy_shares:
            buddy_streams = None

        if permission_level in {PermissionLevel.PUBLIC, PermissionLevel.BUDDY} and not self.reveal_trusted_shares:
            trusted_streams = None

        compressed_shares = SharedFileListResponse(
            public_shares=public_streams, buddy_shares=buddy_streams, trusted_shares=trusted_streams,
            permission_level=permission_level
        )
        compressed_shares.make_network_message()
        compressed_shares.public_shares = compressed_shares.buddy_shares = compressed_shares.trusted_shares = None

        self.queue.put(compressed_shares)

    def create_compressed_shares(self):

        Shares.load_shares(
            self.share_dbs, self.share_db_paths, destinations={"public_streams", "buddy_streams", "trusted_streams"}
        )

        for permission_level in (PermissionLevel.PUBLIC, PermissionLevel.BUDDY, PermissionLevel.TRUSTED):
            self.create_compressed_shares_message(permission_level)

        Shares.close_shares(self.share_dbs)

    def create_file_path_index(self):

        Shares.load_shares(
            self.share_dbs, self.share_db_paths, destinations={"public_files", "buddy_files", "trusted_files"}
        )

        file_path_index = (
            list(self.share_dbs["public_files"])
            + list(self.share_dbs["buddy_files"])
            + list(self.share_dbs["trusted_files"])
        )
        self.queue.put(file_path_index)

        Shares.close_shares(self.share_dbs)

    def real2virtual(self, real_path):

        real_path = real_path.replace("/", "\\")

        for shared_folder_paths in self.share_groups:
            for virtual_name, folder_path, *_unused in shared_folder_paths:
                folder_path = folder_path.replace("/", "\\")

                if real_path == folder_path:
                    return virtual_name

                # Use rstrip to remove trailing separator from root folders
                folder_path = folder_path.rstrip("\\") + "\\"

                if real_path.startswith(folder_path):
                    real_path_no_prefix = real_path[len(folder_path):]
                    virtual_path = f"{virtual_name}\\{real_path_no_prefix}"
                    return virtual_path

        raise ValueError(f"Cannot find virtual path for {real_path}")

    def set_shares(self, permission_level=None, files=None, streams=None, mtimes=None, word_index=None):

        for source, destination in (
            (files, "files"),
            (streams, "streams"),
            (mtimes, "mtimes"),
            (word_index, "words")
        ):
            if source is None:
                continue

            if destination != "words":
                destination = f"{permission_level}_{destination}"

            share_db = None

            try:
                share_db_path = self.share_db_paths[destination]
                share_db = Shares.create_db_file(share_db_path)
                share_db.update(source)

            finally:
                if share_db is not None:
                    share_db.close()

    def rescan_dirs(self, permission_level):

        shared_public_folders, shared_buddy_folders, shared_trusted_folders = self.share_groups

        if permission_level == PermissionLevel.TRUSTED:
            shared_folder_paths = sorted(shared_trusted_folders)

        elif permission_level == PermissionLevel.BUDDY:
            shared_folder_paths = sorted(shared_buddy_folders)

        else:
            shared_folder_paths = sorted(shared_public_folders)

        try:
            Shares.load_shares(
                self.share_dbs, self.share_db_paths,
                destinations={f"{permission_level}_files", f"{permission_level}_mtimes"})

        except Exception:
            # No previous share databases, rebuild
            self.rebuild = True

        old_files = self.share_dbs.get(f"{permission_level}_files")
        old_mtimes = self.share_dbs.get(f"{permission_level}_mtimes")

        for virtual_name, folder_path, *_unused in shared_folder_paths:
            if virtual_name in self.processed_share_names:
                # No duplicate names
                continue

            if folder_path in self.processed_share_paths:
                # No duplicate folder paths
                continue

            self.scan_shared_folder(folder_path, old_mtimes, old_files)

            self.processed_share_names.add(virtual_name)
            self.processed_share_paths.add(folder_path)

        # Save data to databases
        Shares.close_shares(self.share_dbs)
        self.set_shares(permission_level, files=self.files, streams=self.streams, mtimes=self.mtimes)

        for dictionary in (self.files, self.streams, self.mtimes):
            dictionary.clear()

        gc.collect()

    @classmethod
    def is_hidden(cls, folder, filename=None, entry=None):
        """Stop sharing any dot/hidden folders/files."""

        if filename is None:
            last_folder = os.path.basename(folder)

            if last_folder.startswith(".") or last_folder in cls.HIDDEN_FOLDER_NAMES:
                return True

        # If we're asked to check a file, we exclude it if it starts with a dot
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

    def scan_shared_folder(self, shared_folder_path, old_mtimes, old_files):
        """Scan a shared folder for all subfolders, files and their metadata."""

        folder_paths = deque([shared_folder_path])

        while folder_paths:
            folder_path = folder_paths.pop()
            virtual_folder_path = self.real2virtual(folder_path)

            if virtual_folder_path in self.streams:
                # Sharing a folder twice, no go
                continue

            file_list = []

            try:
                with os.scandir(encode_path(folder_path, prefix=False)) as entries:
                    for entry in entries:
                        basename = entry.name.decode("utf-8", "replace")
                        path = os.path.join(folder_path, basename)

                        if entry.is_dir():
                            if self.is_hidden(path, entry=entry):
                                continue

                            self.current_folder_count += 1
                            folder_paths.append(path)

                            if not self.current_folder_count % 100:
                                self.queue.put(self.current_folder_count)
                            continue

                        try:
                            if self.is_hidden(folder_path, basename, entry):
                                continue

                            file_stat = entry.stat()
                            file_index = self.current_file_index
                            self.mtimes[path] = file_mtime = file_stat.st_mtime
                            virtual_file_path = f"{virtual_folder_path}\\{basename}"

                            if not self.rebuild and file_mtime == old_mtimes.get(path) and path in old_files:
                                full_path_file_data = old_files[path]
                                full_path_file_data[0] = virtual_file_path  # Virtual name might have changed
                            else:
                                full_path_file_data = self.get_file_info(virtual_file_path, path, file_stat)

                            basename_file_data = full_path_file_data[:]
                            basename_file_data[0] = basename
                            file_list.append(basename_file_data)

                            for k in set(virtual_file_path.lower().translate(TRANSLATE_PUNCTUATION).split()):
                                self.word_index[k].append(file_index)

                            self.files[path] = full_path_file_data
                            self.current_file_index += 1

                        except OSError as error:
                            self.queue.put((_("Error while scanning file %(path)s: %(error)s"),
                                           {"path": path, "error": error}))

            except OSError as error:
                self.queue.put((_("Error while scanning folder %(path)s: %(error)s"),
                               {"path": folder_path, "error": error}))

            self.streams[virtual_folder_path] = self.get_folder_stream(file_list)

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
                               {"path": file_path, "error": error}))

        if tag is not None:
            bitrate = tag.bitrate
            samplerate = tag.samplerate
            bitdepth = tag.bitdepth
            duration = tag.duration

            if bitrate is not None:
                bitrate = int(bitrate + 0.5)  # Round the value with minimal performance loss

                if not UINT32_LIMIT > bitrate > 0:
                    bitrate = None

            if samplerate is not None:
                samplerate = int(samplerate)

                if not UINT32_LIMIT > samplerate > 0:
                    samplerate = None

            if bitdepth is not None:
                bitdepth = int(bitdepth)

                if not UINT32_LIMIT > bitdepth > 0:
                    bitdepth = None

            if duration is not None:
                duration = int(duration)

                if not UINT32_LIMIT > duration >= 0:
                    duration = None

            quality = (bitrate, int(tag.is_vbr), samplerate, bitdepth)

        return [virtual_file_path, size, quality, duration]

    @staticmethod
    def get_folder_stream(file_list):
        """Pack all files and metadata in folder."""

        stream = bytearray()
        stream += FileListMessage.pack_uint32(len(file_list))

        for fileinfo in file_list:
            stream += FileListMessage.pack_file_info(fileinfo)

        return bytes(stream)


class Shares:
    __slots__ = ("share_dbs", "requested_share_times", "initialized", "rescanning", "compressed_shares",
                 "share_db_paths", "file_path_index", "_scanner_process")

    def __init__(self):

        self.share_dbs = {}
        self.requested_share_times = {}
        self.initialized = False
        self.rescanning = False
        self.compressed_shares = {
            PermissionLevel.PUBLIC: SharedFileListResponse(permission_level=PermissionLevel.PUBLIC),
            PermissionLevel.BUDDY: SharedFileListResponse(permission_level=PermissionLevel.BUDDY),
            PermissionLevel.TRUSTED: SharedFileListResponse(permission_level=PermissionLevel.TRUSTED),
            PermissionLevel.BANNED: SharedFileListResponse(permission_level=PermissionLevel.BANNED)
        }
        self.share_db_paths = {
            "words": os.path.join(config.data_folder_path, "words.dbn"),
            "public_files": os.path.join(config.data_folder_path, "publicfiles.dbn"),
            "public_mtimes": os.path.join(config.data_folder_path, "publicmtimes.dbn"),
            "public_streams": os.path.join(config.data_folder_path, "publicstreams.dbn"),
            "buddy_files": os.path.join(config.data_folder_path, "buddyfiles.dbn"),
            "buddy_mtimes": os.path.join(config.data_folder_path, "buddymtimes.dbn"),
            "buddy_streams": os.path.join(config.data_folder_path, "buddystreams.dbn"),
            "trusted_files": os.path.join(config.data_folder_path, "trustedfiles.dbn"),
            "trusted_mtimes": os.path.join(config.data_folder_path, "trustedmtimes.dbn"),
            "trusted_streams": os.path.join(config.data_folder_path, "trustedstreams.dbn")
        }
        self.file_path_index = ()

        self._scanner_process = None

        for event_name, callback in (
            ("folder-contents-request", self._folder_contents_request),
            ("quit", self._quit),
            ("server-disconnect", self._server_disconnect),
            ("server-login", self._server_login),
            ("shared-file-list-request", self._shared_file_list_request),
            ("shares-ready", self._shares_ready),
            ("start", self._start)
        ):
            events.connect(event_name, callback)

    def _start(self):

        rescan_startup = (config.sections["transfers"]["rescanonstartup"]
                          and not config.need_config())

        self.convert_shares()
        self.rescan_shares(init=True, rescan=rescan_startup)

    def _quit(self):

        self.close_shares(self.share_dbs)
        self.initialized = False

        if self._scanner_process is not None:
            self._scanner_process.terminate()

    def _server_login(self, msg):
        if msg.success:
            self.send_num_shared_folders_files()

    def _server_disconnect(self, _msg):
        self.requested_share_times.clear()

    # Shares-related Actions #

    @classmethod
    def create_db_file(cls, db_path):
        cls.remove_db_file(db_path)
        return Database(encode_path(db_path))

    @staticmethod
    def remove_db_file(db_path):

        db_path_encoded = encode_path(db_path)

        if os.path.isfile(db_path_encoded):
            os.remove(db_path_encoded)

        elif os.path.isdir(db_path_encoded):
            import shutil
            shutil.rmtree(db_path_encoded)

    def virtual2real(self, virtual_path):

        for shares in (
            config.sections["transfers"]["shared"],
            config.sections["transfers"]["buddyshared"],
            config.sections["transfers"]["trustedshared"]
        ):
            for virtual_name, folder_path, *_unused in shares:
                if virtual_path == virtual_name:
                    return folder_path

                if virtual_path.startswith(virtual_name + "\\"):
                    real_path = folder_path.rstrip(os.sep) + virtual_path[len(virtual_name):].replace("\\", os.sep)
                    return real_path

        return "__INVALID_SHARE__" + virtual_path

    def convert_shares(self):

        def _convert_share(shared_folder):
            if isinstance(shared_folder, tuple):
                virtual, shared_folder, *_unused = shared_folder
                virtual = str(virtual)
                shared_folder = str(shared_folder)
            else:
                # Convert fs-based shared to virtual shared (pre-1.4.0)
                virtual = str(shared_folder).replace("/", "_").replace("\\", "_").strip("_")
                log.add("Renaming shared folder '%s' to '%s'. A rescan of your share is required.",
                        (shared_folder, virtual))

            # Remove slashes from share name to avoid path conflicts
            virtual = virtual.replace("/", "_").replace("\\", "_")

            if shared_folder:
                shared_folder = os.path.normpath(shared_folder)

            return virtual, shared_folder

        config.sections["transfers"]["shared"] = [_convert_share(x)
                                                  for x in config.sections["transfers"]["shared"]]
        config.sections["transfers"]["buddyshared"] = [_convert_share(x)
                                                       for x in config.sections["transfers"]["buddyshared"]]

        # Remove old share databases (pre-3.3.0)
        for destination in (
            "wordindex", "fileindex", "files", "mtimes", "streams",
            "buddywordindex", "buddyfileindex", "buddyfiles", "buddymtimes", "buddystreams"
        ):
            file_path = os.path.join(config.data_folder_path, f"{destination}.db")

            try:
                self.remove_db_file(file_path)

            except OSError as error:
                log.add_debug("Failed to remove old share database %s: %s", (file_path, error))

    @classmethod
    def load_shares(cls, share_dbs, share_db_paths, destinations=None):

        exception = None

        for destination, db_path in share_db_paths.items():
            if destinations and destination not in destinations:
                continue

            try:
                share_dbs[destination] = Database(encode_path(db_path), overwrite=False)

            except Exception as error:
                exception = error
                cls.remove_db_file(db_path)

        if exception:
            cls.close_shares(share_dbs)
            raise exception

    def file_is_shared(self, username, virtual_path, real_path):

        log.add_transfer("Checking if file is shared: %s with real path %s",
                         (virtual_path, real_path))

        public_shared_files = self.share_dbs.get("public_files")
        buddy_shared_files = self.share_dbs.get("buddy_files")
        trusted_shared_files = self.share_dbs.get("trusted_files")
        file_is_shared = False
        size = None

        if not real_path.startswith("__INVALID_SHARE__"):
            if public_shared_files is not None and real_path in public_shared_files:
                file_is_shared = True
                _file_name, size, *_unused = public_shared_files[real_path]

            elif (buddy_shared_files is not None and username in core.buddies.users
                    and real_path in buddy_shared_files):
                file_is_shared = True
                _file_name, size, *_unused = buddy_shared_files[real_path]

            elif trusted_shared_files is not None:
                user_data = core.buddies.users.get(username)

                if user_data and user_data.is_trusted and real_path in trusted_shared_files:
                    file_is_shared = True
                    _file_name, size, *_unused = trusted_shared_files[real_path]

        if not file_is_shared:
            log.add_transfer("File is not present in the database of shared files, not sharing: "
                             "%s with real path %s", (virtual_path, real_path))
            return False, size

        return True, size

    def check_user_permission(self, username, ip_address=None):
        """Check if this user is banned, geoip-blocked, and which shares it is
        allowed to access based on transfer and shares settings."""

        if core.network_filter.is_user_banned(username) or core.network_filter.is_user_ip_banned(username, ip_address):
            if config.sections["transfers"]["usecustomban"]:
                ban_message = config.sections["transfers"]["customban"]
                return PermissionLevel.BANNED, ban_message

            return PermissionLevel.BANNED, ""

        user_data = core.buddies.users.get(username)

        if user_data:
            if user_data.is_trusted:
                return PermissionLevel.TRUSTED, ""

            return PermissionLevel.BUDDY, ""

        if ip_address is None or not config.sections["transfers"]["geoblock"]:
            return PermissionLevel.PUBLIC, ""

        country_code = core.network_filter.get_country_code(ip_address)

        # Please note that all country codes are stored in the same string at the first index
        # of an array, separated by commas (no idea why this decision was made...)

        if country_code and config.sections["transfers"]["geoblockcc"][0].find(country_code) >= 0:
            if config.sections["transfers"]["usecustomgeoblock"]:
                ban_message = config.sections["transfers"]["customgeoblock"]
                return PermissionLevel.BANNED, ban_message

            return PermissionLevel.BANNED, ""

        return PermissionLevel.PUBLIC, ""

    def get_shared_folders(self):

        shared_public_folders = config.sections["transfers"]["shared"]
        shared_buddy_folders = config.sections["transfers"]["buddyshared"]
        shared_trusted_folders = config.sections["transfers"]["trustedshared"]

        return shared_public_folders, shared_buddy_folders, shared_trusted_folders

    def get_normalized_virtual_name(self, virtual_name, shared_folders=None):

        if shared_folders is None:
            public_shares, buddy_shares, trusted_shares = self.get_shared_folders()
            shared_folders = (public_shares + buddy_shares + trusted_shares)

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

    def add_share(self, folder_path, permission_level=PermissionLevel.PUBLIC, virtual_name=None,
                  share_groups=None, validate_path=True):

        if validate_path and not os.access(encode_path(folder_path), os.R_OK):
            return None

        if share_groups is None:
            share_groups = self.get_shared_folders()

        # Remove previous share with same path if present
        core.shares.remove_share(folder_path, share_groups=share_groups)

        public_shares, buddy_shares, trusted_shares = share_groups
        virtual_name = core.shares.get_normalized_virtual_name(
            virtual_name or os.path.basename(folder_path),
            shared_folders=(public_shares + buddy_shares + trusted_shares)
        )
        permission_level_shares = {
            PermissionLevel.PUBLIC: public_shares,
            PermissionLevel.BUDDY: buddy_shares,
            PermissionLevel.TRUSTED: trusted_shares
        }
        shares = permission_level_shares.get(permission_level)

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

        for destination in share_dbs.copy():
            database = share_dbs.pop(destination, None)

            if database is not None:
                database.close()

    def send_num_shared_folders_files(self):
        """Send number of publicly shared files to the server."""

        if self.rescanning:
            return

        local_username = core.users.login_username
        num_shared_folders = len(self.share_dbs.get("public_streams", {}))
        num_shared_files = len(self.share_dbs.get("public_files", {}))

        if config.sections["transfers"]["reveal_buddy_shares"]:
            num_shared_folders += len(self.share_dbs.get("buddy_streams", {}))
            num_shared_files += len(self.share_dbs.get("buddy_files", {}))

        if config.sections["transfers"]["reveal_trusted_shares"]:
            num_shared_folders += len(self.share_dbs.get("trusted_streams", {}))
            num_shared_files += len(self.share_dbs.get("trusted_files", {}))

        core.send_message_to_server(SharedFoldersFiles(num_shared_folders, num_shared_files))

        if not local_username:
            # The shares module is initialized before the users module (to send updated share
            # stats to the server before watching our own username), and receives the login
            # event first, so local_username is still None when connecting. For this reason,
            # this check only happens after sending the SharedFoldersFiles server message.
            return

        # We've connected and rescanned our shares again. Fake a user stats message, since
        # server doesn't send updates for our own username after the first WatchUser message
        # response
        events.emit(
            "user-stats",
            GetUserStats(
                user=local_username,
                avgspeed=core.uploads.upload_speed, files=num_shared_files, dirs=num_shared_folders
            )
        )

    # Scanning #

    def rebuild_shares(self, use_thread=True):
        return self.rescan_shares(rebuild=True, use_thread=use_thread)

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
        self.file_path_index = ()

        events.emit("shares-preparing")

        share_groups = self.get_shared_folders()
        self._scanner_process, scanner_queue = self._build_scanner_process(share_groups, init, rescan, rebuild)
        self._scanner_process.start()

        if use_thread:
            Thread(
                target=self._process_scanner, args=(scanner_queue, events.emit_main_thread),
                name="ProcessShareScanner", daemon=True
            ).start()
            return None

        return self._process_scanner(scanner_queue)

    def check_shares_available(self):

        share_groups = self.get_shared_folders()
        unavailable_shares = []

        for share in share_groups:
            for virtual_name, folder_path, *_unused in share:
                if not os.access(encode_path(folder_path), os.R_OK):
                    unavailable_shares.append((virtual_name, folder_path))

        return unavailable_shares

    def _build_scanner_process(self, share_groups=None, init=False, rescan=True, rebuild=False):

        import multiprocessing

        context = multiprocessing.get_context(method="spawn")
        scanner_queue = context.Queue()
        scanner_obj = Scanner(
            scanner_queue,
            share_groups,
            self.share_db_paths,
            init,
            rescan,
            rebuild,
            reveal_buddy_shares=config.sections["transfers"]["reveal_buddy_shares"],
            reveal_trusted_shares=config.sections["transfers"]["reveal_trusted_shares"]
        )
        scanner = context.Process(target=scanner_obj.run, daemon=True)
        return scanner, scanner_queue

    def _process_scanner(self, scanner_queue, emit_event=None):

        successful = True

        while self._scanner_process.is_alive():
            # Cooldown
            time.sleep(0.05)

            while not scanner_queue.empty():
                item = scanner_queue.get()

                if isinstance(item, Exception):
                    successful = False
                    break

                if isinstance(item, tuple):
                    template, args = item
                    log.add(template, args)

                elif isinstance(item, SharedFileListResponse):
                    self.compressed_shares[item.permission_level] = item

                elif isinstance(item, list):
                    self.file_path_index = tuple(item)

                elif isinstance(item, int):
                    if emit_event is not None:
                        emit_event("shares-scanning", item)

                elif item == "rescanning":
                    if emit_event is not None:
                        emit_event("shares-scanning")

                elif item == "initialized":
                    self.initialized = True

        self._scanner_process = None

        if emit_event is not None:
            emit_event("shares-ready", successful)

        return successful

    def _shares_ready(self, successful):

        # Scanning done, load shares in the main process again
        if successful:
            try:
                self.load_shares(
                    self.share_dbs, self.share_db_paths, destinations={
                        "words", "public_files", "public_streams", "buddy_files", "buddy_streams",
                        "trusted_files", "trusted_streams"
                    })

            except Exception:
                successful = False

        self.rescanning = False

        if not successful:
            self.file_path_index = ()
            return

        self.send_num_shared_folders_files()

    # Network Messages #

    def _shared_file_list_request(self, msg):
        """Peer code 4."""

        username = msg.username
        request_time = time.monotonic()

        if username in self.requested_share_times and request_time < self.requested_share_times[username] + 0.4:
            # Ignoring request, because it's less than half a second since the
            # last one by this user
            return

        self.requested_share_times[username] = request_time

        log.add(_("User %(user)s is browsing your list of shared files"), {"user": username})

        ip_address, _port = msg.addr
        permission_level, _reject_reason = self.check_user_permission(username, ip_address)
        shares_list = self.compressed_shares.get(permission_level)
        shares_list.username = shares_list.sock = None  # Reset previous connection

        core.send_message_to_peer(username, shares_list)

    def _folder_contents_request(self, msg):
        """Peer code 36."""

        ip_address, _port = msg.addr
        username = msg.username
        folder_path = msg.dir
        permission_level, _reject_reason = self.check_user_permission(username, ip_address)
        folder_data = None

        if permission_level != PermissionLevel.BANNED:
            folder_data = self.share_dbs.get("public_streams", {}).get(folder_path)

            if (folder_data is None
                    and (config.sections["transfers"]["reveal_buddy_shares"]
                         or permission_level in {PermissionLevel.BUDDY, PermissionLevel.TRUSTED})):
                folder_data = self.share_dbs.get("buddy_streams", {}).get(folder_path)

            if (folder_data is None
                    and (config.sections["transfers"]["reveal_trusted_shares"]
                         or permission_level == PermissionLevel.TRUSTED)):
                folder_data = self.share_dbs.get("trusted_streams", {}).get(folder_path)

        core.send_message_to_peer(
            username, FolderContentsResponse(directory=folder_path, token=msg.token, shares=folder_data))
