# DBM format based on Semidbm (https://github.com/jamesls/semidbm)

# Copyright (c) 2022 Nicotine+ Contributors
# Copyright (c) 2011-2018 James Saryerwinnie
# All rights reserved.

# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
# 1. Redistributions of source code must retain the above copyright notice,
#    this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
# 3. The name of the author may not be used to endorse or promote products
#    derived from this software without specific prior written permission.

# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

import mmap
import os
import shelve
import struct
import sys


FILE_FORMAT_VERSION = (10, 0)
FILE_IDENTIFIER = b'\x53\x45\x4d\x49'
MAPPED_LOAD_PAGES = 300
DELETED = -1


class DBMError(Exception):
    pass


class DBMLoadError(DBMError):
    pass


class DBMLoader:

    def iter_keys(self, filename):

        with open(filename, 'rb') as file_handle:
            header = file_handle.read(8)
            self._verify_header(header)

            contents = mmap.mmap(file_handle.fileno(), 0, access=mmap.ACCESS_READ)
            remap_size = mmap.ALLOCATIONGRANULARITY * MAPPED_LOAD_PAGES
            max_index = os.path.getsize(filename)
            file_size_bytes = max_index
            num_resizes = 0
            current = 8

            try:
                while current != max_index:
                    try:
                        key_size, val_size = struct.unpack('!ii', contents[current:current + 8])

                    except struct.error as error:
                        raise DBMLoadError() from error

                    key = contents[current + 8:current + 8 + key_size]

                    if len(key) != key_size:
                        raise DBMLoadError()

                    offset = (remap_size * num_resizes) + current + 8 + key_size

                    if offset + val_size > file_size_bytes:
                        return

                    yield (key, offset, val_size)

                    if val_size == DELETED:
                        val_size = 0

                    current = current + 8 + key_size + val_size

                    if current >= remap_size:
                        contents.close()
                        num_resizes += 1
                        offset = num_resizes * remap_size
                        contents = mmap.mmap(file_handle.fileno(), file_size_bytes - offset,
                                             access=mmap.ACCESS_READ,
                                             offset=offset)
                        current -= remap_size
                        max_index -= remap_size
            finally:
                contents.close()

    @staticmethod
    def _verify_header(header):

        sig = header[:4]

        if sig != FILE_IDENTIFIER:
            raise DBMLoadError("File is not a db file.")

        major, _minor = struct.unpack('!HH', header[4:])

        if major != FILE_FORMAT_VERSION[0]:
            raise DBMLoadError(
                'Incompatible file version (got: v%s, can handle: v%s)' % (
                    (major, FILE_FORMAT_VERSION[0])))


class DBM:

    DATA_OPEN_FLAGS = os.O_RDWR | os.O_CREAT | os.O_APPEND

    if sys.platform == "win32":
        # On windows we need to specify that we should be
        # reading the file as a binary file so it doesn't
        # change any line ending characters.
        DATA_OPEN_FLAGS = DATA_OPEN_FLAGS | os.O_BINARY  # pylint: disable=no-member

    def __init__(self, data_filename):

        self._data_loader = DBMLoader()
        self._dbdir = os.path.dirname(data_filename)
        self._data_filename = data_filename

        # The in memory index, mapping of key to (offset, size).
        self._index = None
        self._data_fd = None
        self._current_offset = 0
        self._load_db()

    def _create_db_dir(self):
        if not os.path.exists(self._dbdir):
            os.makedirs(self._dbdir)

    def _load_db(self):

        self._create_db_dir()

        self._index = self._load_index(self._data_filename)
        self._data_fd = os.open(self._data_filename, self.DATA_OPEN_FLAGS)
        self._current_offset = os.lseek(self._data_fd, 0, os.SEEK_END)

    def _load_index(self, filename):

        if not os.path.exists(filename):
            self._write_headers(filename)
            return {}

        try:
            return self._load_index_from_fileobj(filename)

        except ValueError as error:
            raise DBMLoadError("Bad index file %s: %s" % (filename, error)) from error

    @staticmethod
    def _write_headers(filename):

        with open(filename, 'wb') as file_handle:
            file_handle.write(FILE_IDENTIFIER)
            file_handle.write(struct.pack('!HH', *FILE_FORMAT_VERSION))

    def _load_index_from_fileobj(self, filename):

        index = {}

        for key_name, offset, size in self._data_loader.iter_keys(filename):
            size = int(size)
            offset = int(offset)

            if size == DELETED:
                # This is a deleted item so we need to make sure that this
                # value is not in the index.  We know that the key is already
                # in the index, because a delete is only written to the index
                # if the key already exists in the db.
                del index[key_name]
            else:
                if key_name in index:
                    index[key_name] = (offset, size)
                else:
                    index[key_name] = (offset, size)

        return index

    def __getitem__(self, key):

        if isinstance(key, str):
            key = key.encode('utf-8')

        offset, size = self._index[key]
        os.lseek(self._data_fd, offset, os.SEEK_SET)

        return os.read(self._data_fd, size)

    def __setitem__(self, key, value):

        if isinstance(key, str):
            key = key.encode('utf-8')

        if isinstance(value, str):
            value = value.encode('utf-8')

        key_size = len(key)
        val_size = len(value)
        keyval_size = struct.pack('!ii', key_size, val_size)
        keyval = key + value
        blob = keyval_size + keyval

        os.write(self._data_fd, blob)

        # Update the in memory index.
        self._index[key] = (self._current_offset + 8 + key_size, val_size)
        self._current_offset += len(blob)

    def __contains__(self, key):
        return key in self._index

    def __delitem__(self, key):

        if isinstance(key, str):
            key = key.encode('utf-8')

        del self._index[key]

        key_size = struct.pack('!ii', len(key), DELETED)
        blob = key_size + key

        os.write(self._data_fd, blob)

        self._current_offset += len(blob)

    def __iter__(self):
        for key in self._index:
            yield key

    def __len__(self):
        return len(self._index)

    def keys(self):
        return self._index.keys()

    def values(self):
        return [self[key] for key in self._index]

    def sync(self):
        os.fsync(self._data_fd)

    def close(self):
        self.sync()
        os.close(self._data_fd)


class DBMReadOnly(DBM):

    DATA_OPEN_FLAGS = os.O_RDONLY

    def __delitem__(self, key):
        self._method_not_allowed('delitem')

    def __setitem__(self, key, value):
        self._method_not_allowed('setitem')

    @staticmethod
    def _method_not_allowed(method_name):
        raise DBMError("Can't %s: db opened in read only mode." % method_name)

    def sync(self):
        pass

    def close(self):
        os.close(self._data_fd)


class DBMReadWrite(DBM):

    def _load_db(self):

        if not os.path.isfile(self._data_filename):
            raise DBMError("Not a file: %s" % self._data_filename)

        super()._load_db()


class DBMNew(DBM):

    def _load_db(self):

        self._create_db_dir()

        if os.path.exists(self._data_filename):
            os.remove(self._data_filename)

        super()._load_db()


def _open(filename, flag='r', _mode=0o666):

    if flag == 'r':
        return DBMReadOnly(filename)

    if flag == 'c':
        return DBM(filename)

    if flag == 'w':
        return DBMReadWrite(filename)

    if flag == 'n':
        return DBMNew(filename)

    raise ValueError("flag argument must be 'r', 'c', 'w', or 'n'")


def open_shelve(filename, flag='c', protocol=None, writeback=False):
    return shelve.Shelf(_open(filename, flag), protocol, writeback)
