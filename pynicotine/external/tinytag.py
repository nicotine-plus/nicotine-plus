# SPDX-FileCopyrightText: 2020-2026 Nicotine+ Contributors
# SPDX-FileCopyrightText: 2014-2026 tinytag Contributors
# SPDX-License-Identifier: MIT

# tinytag - an audio file metadata reader
# http://github.com/tinytag/tinytag

# MIT License

# Copyright (c) 2014-2026 Tom Wallroth, Mat (mathiascode), et al.
# Copyright (c) 2020-2026 Nicotine+ Contributors

# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the "Software"),
# to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
# OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.

# pyright: reportPrivateUsage=false

"""Audio file metadata reader."""

from __future__ import annotations
from binascii import a2b_base64
from io import BytesIO
from os import PathLike, SEEK_CUR, SEEK_END, environ, fsdecode
from struct import unpack, unpack_from

TYPE_CHECKING = False

# Lazy imports for type checking
if TYPE_CHECKING:
    from collections.abc import Callable, Iterator  # pylint: disable-all
    from typing import Any, BinaryIO, Dict, List, Tuple, Union

    _StringListDict = Dict[str, List[str]]
    _ImageListDict = Dict[str, List['Image']]
    _AtomParser = Callable[
        [bytes],
        Iterator[
            Tuple[str, Union[str, float, List[str], 'Image']]
        ]
    ]
    _AtomTreeDict = Dict[bytes, Union['_AtomTreeDict', _AtomParser]]
else:
    _StringListDict = _ImageListDict = dict

# some of the parsers can print debug info
_DEBUG = bool(environ.get('TINYTAG_DEBUG'))


class TinyTagException(Exception):
    """Base class for exceptions."""


class ParseError(TinyTagException):
    """Parsing an audio file failed."""


class UnsupportedFormatError(TinyTagException):
    """File format is not supported."""


class TinyTag:
    """A class containing audio file properties and metadata fields."""

    SUPPORTED_FILE_EXTENSIONS = (
        '.mp1', '.mp2', '.mp3',
        '.oga', '.ogv', '.ogg', '.opus', '.spx',
        '.wav', '.flac',
        '.wma', '.wmv', '.asf',
        '.m4b', '.m4a', '.m4r', '.m4v', '.mp4', '.aax', '.aaxc',
        '.aiff', '.aifc', '.aif', '.afc'
    )
    _OTHER_PREFIX = 'other.'
    _file_extension_mapping: dict[tuple[str, ...], type[TinyTag]] | None = None

    def __init__(self) -> None:
        self.filename: str | None = None
        self.filesize = 0

        self.mime_type: str | None = None
        self.is_lossless: bool | None = None
        self.duration: float | None = None
        self.channels: int | None = None
        self.bitrate: float | None = None
        self.bitdepth: int | None = None
        self.samplerate: int | None = None
        self.is_vbr = False  # Nicotine+ extension

        self.artist: str | None = None
        self.albumartist: str | None = None
        self.composer: str | None = None
        self.album: str | None = None
        self.disc: int | None = None
        self.disc_total: int | None = None
        self.title: str | None = None
        self.track: int | None = None
        self.track_total: int | None = None
        self.genre: str | None = None
        self.year: str | None = None
        self.comment: str | None = None

        self.images = Images()
        self.other = OtherFields()

        self._filehandler: BinaryIO | None = None
        self._default_encoding: str | None = None  # override for some formats
        self._parse_duration = True
        self._parse_tags = True
        self._load_image = False
        self._duration_parsed = False
        self._tags_parsed = False
        self.__dict__: dict[str, str | float | Images | OtherFields | None]

    @classmethod
    def get(cls,
            filename: bytes | str | PathLike[Any] | None = None,
            file_obj: BinaryIO | None = None,
            tags: bool = True,
            duration: bool = True,
            image: bool = False,
            encoding: str | None = None,
            ignore_errors: bool | None = None,
            check_magic_bytes: bool = True) -> TinyTag:
        """Return a tag object for an audio file."""
        should_close_file = file_obj is None
        parser_class = None
        filename_str = None
        if filename:
            filename_str = fsdecode(filename)
            if not check_magic_bytes:
                # Raises UnsupportedFormatError
                parser_class = cls._get_parser_class(filename_str)
            if should_close_file:
                # pylint: disable=consider-using-with
                file_obj = open(filename, 'rb')
        if file_obj is None:
            raise ValueError(
                'Either filename or file_obj argument is required')
        if ignore_errors is not None:
            # pylint: disable=import-outside-toplevel
            from warnings import warn
            warn('ignore_errors argument is obsolete, and will be removed in '
                 'the future', DeprecationWarning, stacklevel=2)
        try:
            if parser_class is None:  # check_magic_bytes is True
                # Raises UnsupportedFormatError
                parser_class = cls._get_parser_class(filename_str, file_obj)
            file_obj.seek(0, SEEK_END)
            filesize = file_obj.tell()
            file_obj.seek(0)
            # pylint: disable=protected-access
            tag = parser_class()
            tag._filehandler = file_obj
            tag._default_encoding = encoding
            tag.filename = filename_str
            tag.filesize = filesize
            try:
                tag._load(tags=tags, duration=duration, image=image)
            except Exception as exc:
                raise ParseError(exc) from exc
            return tag
        finally:
            if should_close_file:
                file_obj.close()

    @classmethod
    def is_supported(cls, filename: bytes | str | PathLike[Any]) -> bool:
        """Check if a specific file is supported based on its file
        extension."""
        filename_str = fsdecode(filename)
        return cls._get_parser_for_filename(filename_str) is not None

    def as_dict(self) -> dict[str, str | float | list[str]]:
        """Return a flat dictionary representation of available
        metadata."""
        audio_property_keys = {
            'filename', 'filesize', 'mime_type', 'duration', 'channels',
            'bitrate', 'bitdepth', 'samplerate', 'is_lossless'
        }
        fields: dict[str, str | float | list[str]] = {}
        for key, value in self.__dict__.items():
            if key.startswith('_'):
                continue
            if isinstance(value, Images):
                continue
            if not isinstance(value, OtherFields):
                if value is None:
                    continue
                if key in audio_property_keys:
                    fields[key] = value
                else:
                    fields[key] = [str(value)]
                continue
            for other_key, other_values in value.items():
                other_fields = fields.get(other_key)
                if not isinstance(other_fields, list):
                    fields[other_key] = other_values
                else:
                    other_fields += other_values
        return fields

    @classmethod
    def _get_parser_for_filename(cls, filename: str) -> type[TinyTag] | None:
        if cls._file_extension_mapping is None:
            cls._file_extension_mapping = {
                ('.mp1', '.mp2', '.mp3', '.flac'): _ID3,
                ('.oga', '.ogv', '.ogg', '.opus', '.spx'): _Ogg,
                ('.wav',): _Wave,
                ('.wma', '.wmv', '.asf'): _ASF,
                ('.m4b', '.m4a', '.m4r', '.m4v', '.mp4',
                 '.aax', '.aaxc'): _MP4,
                ('.aiff', '.aifc', '.aif', '.afc'): _Aiff,
            }
        filename = filename.lower()
        for ext, tagclass in cls._file_extension_mapping.items():
            if filename.endswith(ext):
                return tagclass
        return None

    @classmethod
    def _get_parser_for_file_handle(
        cls,
        filehandle: BinaryIO
    ) -> type[TinyTag] | None:
        # https://en.wikipedia.org/wiki/List_of_file_signatures
        header = filehandle.read(30)
        if header.startswith(b'ID3'):
            return _ID3
        if (len(header) >= 2
                and header[0] == 0xFF and (header[1] & 0xE0) == 0xE0):
            footer = None
            try:
                filehandle.seek(-_ID3._ID3V1_TAG_SIZE, SEEK_END)
                footer = filehandle.read(3)
            except OSError:
                # File smaller than ID3v1 tag size
                pass
            if footer == b'TAG':
                return _ID3
            return _MPEG
        if header.startswith(b'fLaC'):
            return _Flac
        if header.startswith(b'ftyp', 4):
            return _MP4
        if header.startswith(b'OggS'):
            return _Ogg
        if header.startswith(b'RIFF') and header.startswith(b'WAVE', 8):
            return _Wave
        if header.startswith(
            b'\x30\x26\xB2\x75\x8E\x66\xCF\x11\xA6\xD9\x00\xAA\x00\x62\xCE\x6C'
        ) and header.startswith(b'\x02', 29):
            return _ASF
        if (header.startswith(b'FORM')
                and header.startswith((b'AIFF', b'AIFC'), 8)):
            return _Aiff
        return None

    @classmethod
    def _get_parser_class(
        cls,
        filename: str | None = None,
        filehandle: BinaryIO | None = None
    ) -> type[TinyTag]:
        if cls != TinyTag:
            return cls
        if filename:
            parser_class = cls._get_parser_for_filename(filename)
            if parser_class is not None:
                return parser_class
        # try determining the file type by magic byte header, if provided
        if filehandle:
            parser_class = cls._get_parser_for_file_handle(filehandle)
            if parser_class is not None:
                return parser_class
        raise UnsupportedFormatError(
            'No tag reader found to support file type')

    def _load(self, tags: bool, duration: bool, image: bool = False) -> None:
        self._parse_tags = tags
        self._parse_duration = duration
        self._load_image = image
        if self._filehandler is None:
            raise ValueError("File handle is required")
        if not self.filesize:
            return
        if tags or duration:
            self._parse(self._filehandler)

    def _set_field(self, fieldname: str, value: str | float) -> None:
        if isinstance(value, str) and not value:
            return
        old_value = self.__dict__.get(fieldname)
        if value == old_value:
            return
        if old_value is not None:
            self._set_other_field(fieldname, str(value))
            return
        if fieldname.startswith(self._OTHER_PREFIX):
            fieldname = fieldname[len(self._OTHER_PREFIX):]
            if fieldname in self.__dict__:
                fieldname = '_' + fieldname
            self._set_other_field(fieldname, str(value))
            return
        if _DEBUG:
            print(f'Setting field {fieldname} to {value!r}')
        self.__dict__[fieldname] = value

    def _set_other_field(self, fieldname: str, value: str) -> None:
        if not value:
            return
        if fieldname not in self.other:
            self.other[fieldname] = []
        if value in self.other[fieldname]:
            return
        if _DEBUG:
            print(f'Adding value {value!r} to field {fieldname}')
        self.other[fieldname].append(value)

    def _parse(self, fh: BinaryIO) -> None:
        raise NotImplementedError

    def _update(self, other: TinyTag) -> None:
        # update the values of this tag with the values from another tag
        ignored_keys = {'filename', 'filesize', 'mime_type'}
        for key, value in other.__dict__.items():
            if key.startswith('_') or key in ignored_keys:
                continue
            if isinstance(value, OtherFields):
                for other_key, other_values in other.other.items():
                    for other_value in other_values:
                        self._set_other_field(other_key, other_value)
            elif isinstance(value, Images):
                self.images._update(value)  # pylint: disable=protected-access
            elif value is not None:
                self._set_field(key, value)

    @staticmethod
    def _unpad(s: str) -> str:
        # certain strings *may* be terminated with a zero byte at the end
        return s.rstrip('\x00')

    @staticmethod
    def _unpad_bytes(s: bytes) -> bytes:
        return s.rstrip(b'\x00')

    def get_image(self) -> bytes | None:
        """Deprecated, use 'images.any' instead."""
        from warnings import warn  # pylint: disable=import-outside-toplevel
        warn('get_image() is deprecated, and will be removed in the future. '
             "Use 'images.any' instead.",
             DeprecationWarning, stacklevel=2)
        image = self.images.any
        return image.data if image is not None else None

    @property
    def audio_offset(self) -> None:  # pylint: disable=useless-return
        """Obsolete."""
        from warnings import warn  # pylint: disable=import-outside-toplevel
        warn("'audio_offset' attribute is obsolete, and will be "
             'removed in the future',
             DeprecationWarning, stacklevel=2)
        return None

    @property
    def extra(self) -> dict[str, str]:
        """Obsolete, use 'other' instead."""
        from warnings import warn  # pylint: disable=import-outside-toplevel
        warn("'extra' attribute is obsolete, and will be "
             "removed in the future. Use 'other' instead.",
             DeprecationWarning, stacklevel=2)
        return {}


class Images:
    """A class containing images embedded in an audio file."""
    _OTHER_PREFIX = 'other.'

    def __init__(self) -> None:
        self.front_cover: Image | None = None
        self.back_cover: Image | None = None
        self.media: Image | None = None

        self.other = OtherImages()
        self.__dict__: dict[str, Image | OtherImages | None]

    @property
    def any(self) -> Image | None:
        """Return a cover image.
        If not present, fall back to any other available image.
        """
        for value in self.__dict__.values():
            if isinstance(value, OtherImages):
                for other_images in value.values():
                    for image in other_images:
                        return image
                continue
            if value is not None:
                return value
        return None

    def as_dict(self) -> dict[str, list[Image]]:
        """Return a flat dictionary representation of available images."""
        images: dict[str, list[Image]] = {}
        for key, value in self.__dict__.items():
            if not isinstance(value, OtherImages):
                if value is not None:
                    images[key] = [value]
                continue
            for other_key, other_values in value.items():
                other_images = images.get(other_key)
                if not isinstance(other_images, list):
                    images[other_key] = other_values
                else:
                    other_images += other_values
        return images

    def _set_field(self, fieldname: str, value: Image) -> None:
        old_value = self.__dict__.get(fieldname)
        if old_value is not None:
            self._set_other_field(fieldname, value)
            return
        if fieldname.startswith(self._OTHER_PREFIX):
            fieldname = fieldname[len(self._OTHER_PREFIX):]
            self._set_other_field(fieldname, value)
            return
        if _DEBUG:
            print(f'Setting image field {fieldname}')
        self.__dict__[fieldname] = value

    def _set_other_field(self, fieldname: str, value: Image) -> None:
        if fieldname not in self.other:
            self.other[fieldname] = []
        if _DEBUG:
            print(f'Adding image to field {fieldname}')
        self.other[fieldname].append(value)

    def _update(self, other: Images) -> None:
        for key, value in other.__dict__.items():
            if isinstance(value, OtherImages):
                for other_key, other_values in value.items():
                    for image_other in other_values:
                        self._set_other_field(other_key, image_other)
                continue
            if value is not None:
                self._set_field(key, value)


class Image:
    """A class representing an image embedded in an audio file."""
    def __init__(self,
                 name: str,
                 size: int,
                 data: bytes,
                 mime_type: str | None = None,
                 description: str | None = None) -> None:
        self.name = name
        self.size = size
        self.data = data
        self.mime_type = mime_type
        self.description: str | None = description

    def __repr__(self) -> str:
        variables = vars(self).copy()
        data = variables.get("data")
        if data is not None:
            variables["data"] = (data[:45] + b'..') if len(data) > 45 else data
        data_str = ', '.join(f'{k}={v!r}' for k, v in variables.items())
        return f'{type(self).__name__}({data_str})'


class OtherFields(_StringListDict):
    """A dictionary containing additional metadata fields of an audio file."""


class OtherImages(_ImageListDict):
    """A dictionary containing additional images embedded in an audio file."""


class _MP4(TinyTag):
    """MP4 Audio Parser.

    https://developer.apple.com/library/mac/documentation/QuickTime/QTFF/Metadata/Metadata.html
    https://developer.apple.com/library/mac/documentation/QuickTime/QTFF/QTFFChap2/qtff2.html
    """

    _CUSTOM_FIELD_NAME_MAPPING = {
        'artists': 'artist',
        'conductor': 'other.conductor',
        'discsubtitle': 'other.set_subtitle',
        'initialkey': 'other.initial_key',
        'isrc': 'other.isrc',
        'language': 'other.language',
        'lyricist': 'other.lyricist',
        'media': 'other.media',
        'website': 'other.url',
        'license': 'other.license',
        'barcode': 'other.barcode',
        'catalognumber': 'other.catalog_number',
    }
    _IMAGE_MIME_TYPES = {
        12: 'image/gif',
        13: 'image/jpeg',
        14: 'image/png',
        27: 'image/bmp'
    }
    _UNPACK_FORMATS = {
        1: '>b',
        2: '>h',
        4: '>i',
        8: '>q'
    }
    _LOSSLESS_CODECS = {
        'mp4a.40.35',  # DST
        'mp4a.40.36',  # ALS
        'mp4a.40.37',  # SLS
        'mp4a.40.38',  # SLS non-core
    }
    _VERSIONED_ATOMS = {b'meta', b'stsd'}  # those have an extra 4 byte header
    _FLAGGED_ATOMS = {b'stsd'}  # these also have an extra 4 byte header
    _ILST_PATH = [b'ftyp', b'moov', b'udta', b'meta', b'ilst']
    _COVR_PATH = [b'ftyp', b'moov', b'udta', b'meta', b'ilst', b'covr']

    _audio_data_tree: _AtomTreeDict | None = None
    _meta_data_tree: _AtomTreeDict | None = None
    _combined_tree: _AtomTreeDict | None = None

    def _parse(self, fh: BinaryIO) -> None:
        # The parser tree: Each key is an atom name which is traversed if
        # existing. Leaves of the parser tree are callables which receive
        # the atom data. Callables return {fieldname: value} which is updates
        # the TinyTag.
        tree: _AtomTreeDict = {}
        if self._parse_duration and self._parse_tags:
            tree = self._build_combined_tree()
        elif self._parse_duration:
            tree = self._build_audio_data_tree()
        elif self._parse_tags:
            tree = self._build_meta_data_tree()
        self._traverse_atoms(fh, path=tree)
        self._duration_parsed = self._parse_duration
        self._tags_parsed = self._parse_tags

    @classmethod
    def _build_audio_data_tree(cls) -> _AtomTreeDict:
        if cls._audio_data_tree is None:
            # https://developer.apple.com/library/mac/documentation/QuickTime/QTFF/QTFFChap3/qtff3.html
            cls._audio_data_tree = {
                b'moov': {
                    b'mvhd': _MP4._parse_mvhd,
                    b'trak': {b'mdia': {b"minf": {b"stbl": {b"stsd": {
                        b'mp4a': _MP4._parse_mp4a,
                        b'alac': _MP4._parse_alac
                    }}}}}
                }
            }
        return cls._audio_data_tree

    @classmethod
    def _build_meta_data_tree(cls) -> _AtomTreeDict:
        if cls._meta_data_tree is None:
            cls._meta_data_tree = {b'moov': {b'udta': {b'meta': {b'ilst': {
                # http://atomicparsley.sourceforge.net/mpeg-4files.html
                # https://metacpan.org/dist/Image-ExifTool/source/lib/Image/ExifTool/QuickTime.pm#L3093
                b'\xA9ART': {b'data': _MP4._data_parser('artist')},
                b'\xA9alb': {b'data': _MP4._data_parser('album')},
                b'\xA9cmt': {b'data': _MP4._data_parser('comment')},
                b'\xA9com': {b'data': _MP4._data_parser('composer')},
                b'\xA9con': {b'data': _MP4._data_parser('other.conductor')},
                b'\xA9day': {b'data': _MP4._data_parser('year')},
                b'\xA9des': {b'data': _MP4._data_parser('other.description')},
                b'\xA9dir': {b'data': _MP4._data_parser('other.director')},
                b'\xA9gen': {b'data': _MP4._data_parser('genre')},
                b'\xA9grp': {b'data': _MP4._data_parser('other.grouping')},
                b'\xA9lyr': {b'data': _MP4._data_parser('other.lyrics')},
                b'\xA9mvc': {
                    b'data': _MP4._data_parser('other.movement_total')
                },
                b'\xA9mvi': {b'data': _MP4._data_parser('other.movement')},
                b'\xA9mvn': {
                    b'data': _MP4._data_parser('other.movement_name')
                },
                b'\xA9nam': {b'data': _MP4._data_parser('title')},
                b'\xA9pub': {b'data': _MP4._data_parser('other.publisher')},
                b'\xA9too': {b'data': _MP4._data_parser('other.encoded_by')},
                b'\xA9wrk': {b'data': _MP4._data_parser('other.work')},
                b'\xA9wrt': {b'data': _MP4._data_parser('composer')},
                b'aART': {b'data': _MP4._data_parser('albumartist')},
                b'cprt': {b'data': _MP4._data_parser('other.copyright')},
                b'desc': {b'data': _MP4._data_parser('other.description')},
                b'disk': {b'data': _MP4._nums_parser('disc', 'disc_total')},
                b'gnre': {b'data': _MP4._parse_id3v1_genre},
                b'shwm': {b'data': _MP4._data_parser('other.show_movement')},
                b'trkn': {b'data': _MP4._nums_parser('track', 'track_total')},
                b'tmpo': {b'data': _MP4._data_parser('other.bpm')},
                b'covr': {b'data': _MP4._parse_cover_image},
                b'----': _MP4._parse_custom_field,
            }}}}, b'uuid': _MP4._parse_uuid}
        return cls._meta_data_tree

    @classmethod
    def _build_combined_tree(cls) -> _AtomTreeDict:
        if cls._combined_tree is None:
            cls._combined_tree = result = dict(cls._build_audio_data_tree())
            for key, value in cls._build_meta_data_tree().items():
                current = result.get(key)
                if isinstance(current, dict) and isinstance(value, dict):
                    result[key] = {**current, **value}
                else:
                    result[key] = value
        return cls._combined_tree

    @staticmethod
    def _read_atom_header(
        fh: BinaryIO
    ) -> tuple[bytes | None, int, int | None]:
        atom_type = None
        atom_size = None
        atom_header = fh.read(8)
        header_size = len(atom_header)
        if header_size < 8:
            return atom_type, header_size, atom_size
        atom_size = unpack_from('>I', atom_header)[0]
        atom_type = atom_header[4:]
        if atom_size == 1:  # 64-bit size
            ext_size_header = fh.read(8)
            header_size += len(ext_size_header)
            if header_size == 16:
                atom_size = unpack('>Q', ext_size_header)[0]
        if atom_size < header_size:
            # Invalid atom size, stop parsing. Technically an atom size of
            # 0 is valid, and means the atom extends to the end of the file,
            # but we likely don't care about such atoms anyway.
            atom_size = None
        else:
            atom_size -= header_size
        return atom_type, header_size, atom_size

    def _traverse_atoms(self,
                        fh: BinaryIO,
                        path: _AtomTreeDict,
                        curr_pos: int | None = None,
                        stop_pos: int | None = None,
                        curr_path: list[bytes] | None = None) -> int:
        if curr_pos is None:
            curr_pos = fh.tell()
        atom_type, header_size, atom_size = self._read_atom_header(fh)
        if curr_path is None:
            # Should be safe enough for a quick header check. Newer MP4
            # files tend to start with an 'ftyp' atom. Older files don't,
            # but their initial atom type only seem to use ASCII chars.
            if atom_type is None or not atom_type.isascii():
                raise ParseError('Invalid MP4 header')
            self.mime_type = 'audio/mp4'
        while atom_type is not None and atom_size is not None:
            curr_pos += header_size
            if curr_path is None:
                curr_path = [atom_type]
            if _DEBUG:
                print(f'{" " * 4 * len(curr_path)} '
                      f'pos: {curr_pos - header_size} '
                      f'atom: {atom_type!r} len: {atom_size + header_size}')
            if atom_size >= 4:
                if atom_type in self._VERSIONED_ATOMS:  # skip atom version
                    curr_pos = fh.seek(4, SEEK_CUR)
                    atom_size -= 4
                if atom_type in self._FLAGGED_ATOMS:  # skip atom flags
                    curr_pos = fh.seek(4, SEEK_CUR)
                    atom_size -= 4
            sub_path = path.get(atom_type)
            # if the path-leaf is a callable, call it on the atom data
            if callable(sub_path):
                if not self._load_image and curr_path == self._COVR_PATH:
                    curr_pos = fh.seek(atom_size, SEEK_CUR)
                else:
                    data = fh.read(atom_size)
                    curr_pos += len(data)
                    for fieldname, value in sub_path(data):
                        if _DEBUG:
                            print(' ' * 4 * len(curr_path), 'FIELD: ',
                                  fieldname)
                        if isinstance(value, Image):
                            # pylint: disable=protected-access
                            self.images._set_field(fieldname, value)
                        elif isinstance(value, list):
                            for subval in value:
                                self._set_field(fieldname, subval)
                        elif fieldname == 'codec':
                            self.mime_type = f'audio/mp4; codecs="{value}"'
                        else:
                            self._set_field(fieldname, value)
            # if the path leaf is a dict, traverse deeper into the tree:
            elif isinstance(sub_path, dict):
                curr_pos = self._traverse_atoms(
                    fh, path=sub_path,
                    curr_pos=curr_pos,
                    stop_pos=curr_pos + atom_size,
                    curr_path=curr_path + [atom_type]
                )
            # unknown data atom, try to parse it
            elif curr_path == self._ILST_PATH:
                field_name = (
                    self._OTHER_PREFIX + atom_type.decode('latin-1').lower()
                )
                fh.seek(-header_size, SEEK_CUR)
                curr_pos -= header_size
                curr_pos = self._traverse_atoms(
                    fh,
                    path={atom_type: {b'data': self._data_parser(field_name)}},
                    curr_pos=curr_pos,
                    stop_pos=curr_pos + atom_size + header_size,
                    curr_path=curr_path + [atom_type])
            # if no action was specified using dict or callable, jump over atom
            else:
                curr_pos = fh.seek(atom_size, SEEK_CUR)
            # check if we have reached the end of this branch:
            if stop_pos and curr_pos >= stop_pos:
                return curr_pos  # return to parent (next parent node in tree)
            atom_type, header_size, atom_size = self._read_atom_header(fh)
        return curr_pos

    @classmethod
    def _data_parser(
        cls, fieldname: str
    ) -> Callable[[bytes], Iterator[tuple[str, str]]]:
        def _parse_data_atom(data: bytes) -> Iterator[tuple[str, str]]:
            data_type = unpack_from('>I', data)[0]
            data = data[8:]
            value = ""
            if data_type == 1:     # UTF-8 string
                value = data.decode('utf-8', 'replace')
            elif data_type == 21:  # BE signed integer
                fmts = cls._UNPACK_FORMATS
                data_len = len(data)
                if data_len in fmts:
                    value = str(unpack(fmts[data_len], data)[0])
            yield fieldname, value
        return _parse_data_atom

    @classmethod
    def _nums_parser(
        cls, fieldname1: str, fieldname2: str
    ) -> Callable[[bytes], Iterator[tuple[str, int]]]:
        def _parse_nums(data: bytes) -> Iterator[tuple[str, int]]:
            number_data = data[8:14]
            numbers = unpack('>3H', number_data)
            # for some reason the first number is always irrelevant.
            yield fieldname1, numbers[1]
            yield fieldname2, numbers[2]
        return _parse_nums

    @classmethod
    def _parse_id3v1_genre(cls, data: bytes) -> Iterator[tuple[str, str]]:
        # dunno why genre is offset by -1 but that's how mutagen does it
        idx = unpack_from('>H', data, 8)[0] - 1
        # pylint: disable=protected-access
        if idx < len(_ID3._ID3V1_GENRES):
            yield 'genre', _ID3._ID3V1_GENRES[idx]

    @classmethod
    def _parse_cover_image(cls,
                           data: bytes) -> Iterator[tuple[str, Image]]:
        data_type = unpack_from('>I', data)[0]
        image_name = 'front_cover'
        image_data = data[8:]
        image = Image(
            image_name, len(image_data), image_data,
            cls._IMAGE_MIME_TYPES.get(data_type))
        yield image_name, image

    @classmethod
    def _parse_custom_field(cls,
                            data: bytes) -> Iterator[tuple[str, list[str]]]:
        fh = BytesIO(data)
        field_name = None
        values: list[str] = []
        atom_type, _header_size, atom_size = cls._read_atom_header(fh)
        while atom_type is not None and atom_size is not None:
            if atom_type == b'name':
                atom_value = fh.read(atom_size)[4:].lower()
                field_name = atom_value.decode('utf-8', 'replace')
                # pylint: disable=protected-access
                field_name = cls._CUSTOM_FIELD_NAME_MAPPING.get(
                    field_name, cls._OTHER_PREFIX + field_name)
            elif atom_type == b'data' and field_name:
                data_atom = fh.read(atom_size)
                parser = cls._data_parser(field_name)
                atom_values = parser(data_atom)
                for _field_name, value in atom_values:
                    values.append(value)
                    break
            else:
                fh.seek(atom_size, SEEK_CUR)
            atom_type, _header_size, atom_size = cls._read_atom_header(fh)
        if field_name and values:
            yield field_name, values

    @classmethod
    def _parse_uuid(cls, data: bytes) -> Iterator[tuple[str, str]]:
        uuid_len = 16
        uuid = data[:uuid_len]
        if uuid == (
            b'\xBE\x7A\xCF\xCB\x97\xA9\x42\xE8\x9C\x71\x99\x94\x91\xE3\xAF\xAC'
        ):
            yield 'other.xmp', data[uuid_len:].decode('utf-8', 'replace')

    @classmethod
    def _parse_mp4a(cls, data: bytes) -> Iterator[tuple[str, str | float]]:
        # this atom also contains the esds atom:
        # https://ffmpeg.org/doxygen/0.6/mov_8c-source.html
        # http://xhelmboyx.tripod.com/formats/mp4-layout.txt
        # http://sasperger.tistory.com/103

        # jump over version and flags
        channels = unpack_from('>H', data, 16)[0]
        # jump over bit_depth, QT compr id & pkt size
        samplerate = unpack_from('>I', data, 22)[0]
        if channels > 0:
            yield 'channels', channels
        if samplerate > 0:
            yield 'samplerate', samplerate

        # ES Description Atom
        def _read_descriptor_size(data: bytes, offset: int) -> tuple[int, int]:
            size = 0
            continuation = 1 << 7
            for _i in range(4):
                byte = data[offset]
                offset += 1
                size = (size << 7) | (byte & ((1 << 7) - 1))
                if not (byte & continuation):
                    break
            return size, offset

        offset = 36 + 5   # jump over version, flags and tag

        # ES Descriptor
        _size, offset = _read_descriptor_size(data, offset)
        offset += 4   # jump over ES id, flags and tag

        # Decoder Config Descriptor
        _size, offset = _read_descriptor_size(data, offset)
        object_type = data[offset]
        codec = f'mp4a.{object_type:X}'
        offset += 9
        avg_br = unpack_from('>I', data, offset)[0]
        if avg_br > 0:
            yield 'bitrate', avg_br / 1000  # kbit/s
        offset += 5

        # Decoder Specific Info
        _size, offset = _read_descriptor_size(data, offset)
        first = data[offset]
        second = data[offset + 1]
        audio_object_type = first >> 3
        if audio_object_type == 31:
            # Read extended value
            extended = ((first & 0x07) << 3) | (second >> 5)
            audio_object_type = 32 + extended
        if audio_object_type:
            codec += f'.{audio_object_type}'
        if object_type:
            yield 'codec', codec
            yield 'is_lossless', codec in cls._LOSSLESS_CODECS

    @classmethod
    def _parse_alac(cls, data: bytes) -> Iterator[tuple[str, str | int]]:
        # https://github.com/macosforge/alac/blob/master/ALACMagicCookieDescription.txt
        yield 'codec', 'alac'
        yield 'is_lossless', True
        bitdepth = data[45]
        channels = data[49]
        avg_br, samplerate = unpack_from('>II', data, 56)
        if bitdepth > 0:
            yield 'bitdepth', bitdepth
        if channels > 0:
            yield 'channels', channels
        if avg_br > 0:
            yield 'bitrate', avg_br / 1000
        if samplerate:
            yield 'samplerate', samplerate

    @classmethod
    def _parse_mvhd(cls, data: bytes) -> Iterator[tuple[str, float]]:
        # http://stackoverflow.com/a/3639993/1191373
        version = data[0]
        # jump over flags, create & mod times
        if version == 0:  # uses 32 bit integers for timestamps
            time_scale, duration = unpack_from('>II', data, 12)
            if time_scale > 0:
                yield 'duration', duration / time_scale
        elif version == 1:  # uses 64-bit integers for timestamps
            time_scale, duration = unpack_from('>IQ', data, 20)
            if time_scale > 0:
                yield 'duration', duration / time_scale


class _ID3(TinyTag):
    """ID3 Parser."""

    _ID3_MAPPING = {
        # Mapping from Frame ID to a field of the TinyTag
        # https://exiftool.org/TagNames/ID3.html
        b'COMM': 'comment', b'COM': 'comment',
        b'TRCK': 'track', b'TRK': 'track',
        b'TYER': 'year', b'TYE': 'year', b'TDRC': 'year',
        b'TALB': 'album', b'TAL': 'album',
        b'TPE1': 'artist', b'TP1': 'artist',
        b'TIT2': 'title', b'TT2': 'title',
        b'TCON': 'genre', b'TCO': 'genre',
        b'TPOS': 'disc', b'TPA': 'disc',
        b'TPE2': 'albumartist', b'TP2': 'albumartist',
        b'TCOM': 'composer', b'TCM': 'composer',
        b'WOAR': 'other.url', b'WAR': 'other.url',
        b'TSRC': 'other.isrc', b'TRC': 'other.isrc',
        b'TCOP': 'other.copyright', b'TCR': 'other.copyright',
        b'TBPM': 'other.bpm', b'TBP': 'other.bpm',
        b'TKEY': 'other.initial_key', b'TKE': 'other.initial_key',
        b'TLAN': 'other.language', b'TLA': 'other.language',
        b'TPUB': 'other.publisher', b'TPB': 'other.publisher',
        b'USLT': 'other.lyrics', b'ULT': 'other.lyrics',
        b'TPE3': 'other.conductor', b'TP3': 'other.conductor',
        b'TEXT': 'other.lyricist', b'TXT': 'other.lyricist',
        b'TSST': 'other.set_subtitle',
        b'TENC': 'other.encoded_by', b'TEN': 'other.encoded_by',
        b'TSSE': 'other.encoder_settings', b'TSS': 'other.encoder_settings',
        b'TMED': 'other.media', b'TMT': 'other.media',
        b'WCOP': 'other.license',
        b'MVNM': 'other.movement_name',
        b'MVIN': 'other.movement',
        b'GRP1': 'modern_grouping', b'GP1': 'modern_grouping',
        b'TIT1': 'legacy_grouping', b'TT1': 'legacy_grouping',
    }
    _ID3_MAPPING_CUSTOM = {
        'artists': 'artist',
        'director': 'other.director',
        'license': 'other.license',
        'barcode': 'other.barcode',
        'catalognumber': 'other.catalog_number',
        'showmovement': 'other.show_movement'
    }
    _EMPTY_FRAME_IDS = {b'\x00\x00\x00\x00', b'\x00\x00\x00'}
    _IMAGE_FRAME_IDS = {b'APIC', b'PIC'}
    _CUSTOM_FRAME_IDS = {b'TXXX', b'TXX'}
    _SYNCED_LYRICS_FRAME_IDS = {b'SYLT', b'SLT'}
    _IGNORED_FRAME_IDS = {
        b'AENC', b'CRA',
        b'APIC', b'PIC',
        b'ASPI',
        b'ATXT',
        b'CHAP',
        b'COMR',
        b'CRM',
        b'CTOC',
        b'ENCR',
        b'EQU2', b'EQU',
        b'ETCO', b'ETC',
        b'GEOB', b'GEO',
        b'GRID',
        b'LINK', b'LNK',
        b'MCDI', b'MCI',
        b'MLLT', b'MLL',
        b'OWNE',
        b'PCNT', b'CNT',
        b'POPM', b'POP',
        b'POSS',
        b'RBUF', b'BUF',
        b'RGAD',
        b'RVA2', b'RVA',
        b'RVRB', b'REV',
        b'SEEK',
        b'SIGN',
        b'SYTC', b'STC',
        b'USER',
        b'WXXX', b'WXX',
    }
    _VALID_STRING_ENCODINGS = {0x00, 0x01, 0x02, 0x03}
    _ID3V1_TAG_SIZE = 128
    _ID3V2_HEADER_SIZE = 10
    _ID3V1_GENRES = (
        'Blues', 'Classic Rock', 'Country', 'Dance', 'Disco',
        'Funk', 'Grunge', 'Hip-Hop', 'Jazz', 'Metal', 'New Age', 'Oldies',
        'Other', 'Pop', 'R&B', 'Rap', 'Reggae', 'Rock', 'Techno', 'Industrial',
        'Alternative', 'Ska', 'Death Metal', 'Pranks', 'Soundtrack',
        'Euro-Techno', 'Ambient', 'Trip-Hop', 'Vocal', 'Jazz+Funk', 'Fusion',
        'Trance', 'Classical', 'Instrumental', 'Acid', 'House', 'Game',
        'Sound Clip', 'Gospel', 'Noise', 'AlternRock', 'Bass', 'Soul', 'Punk',
        'Space', 'Meditative', 'Instrumental Pop', 'Instrumental Rock',
        'Ethnic', 'Gothic', 'Darkwave', 'Techno-Industrial', 'Electronic',
        'Pop-Folk', 'Eurodance', 'Dream', 'Southern Rock', 'Comedy', 'Cult',
        'Gangsta', 'Top 40', 'Christian Rap', 'Pop/Funk', 'Jungle',
        'Native American', 'Cabaret', 'New Wave', 'Psychadelic', 'Rave',
        'Showtunes', 'Trailer', 'Lo-Fi', 'Tribal', 'Acid Punk', 'Acid Jazz',
        'Polka', 'Retro', 'Musical', 'Rock & Roll', 'Hard Rock',
        # Wimamp Extended Genres
        'Folk', 'Folk-Rock', 'National Folk', 'Swing', 'Fast Fusion', 'Bebob',
        'Latin', 'Revival', 'Celtic', 'Bluegrass', 'Avantgarde', 'Gothic Rock',
        'Progressive Rock', 'Psychedelic Rock', 'Symphonic Rock', 'Slow Rock',
        'Big Band', 'Chorus', 'Easy listening', 'Acoustic', 'Humour', 'Speech',
        'Chanson', 'Opera', 'Chamber Music', 'Sonata', 'Symphony',
        'Booty Bass', 'Primus', 'Porn Groove', 'Satire', 'Slow Jam', 'Club',
        'Tango', 'Samba', 'Folklore', 'Ballad', 'Power Ballad',
        'Rhythmic Soul', 'Freestyle', 'Duet', 'Punk Rock', 'Drum Solo',
        'A capella', 'Euro-House', 'Dance Hall', 'Goa', 'Drum & Bass',
        'Club-House', 'Hardcore Techno', 'Terror', 'Indie', 'BritPop',
        'Afro-Punk', 'Polsk Punk', 'Beat', 'Christian Gangsta Rap',
        'Heavy Metal', 'Black Metal', 'Contemporary Christian',
        'Christian Rock',
        # WinAmp 1.91
        'Merengue', 'Salsa', 'Thrash Metal', 'Anime', 'Jpop', 'Synthpop',
        # WinAmp 5.6
        'Abstract', 'Art Rock', 'Baroque', 'Bhangra', 'Big Beat', 'Breakbeat',
        'Chillout', 'Downtempo', 'Dub', 'EBM', 'Eclectic', 'Electro',
        'Electroclash', 'Emo', 'Experimental', 'Garage', 'Illbient',
        'Industro-Goth', 'Jam Band', 'Krautrock', 'Leftfield', 'Lounge',
        'Math Rock', 'New Romantic', 'Nu-Breakz', 'Post-Punk', 'Post-Rock',
        'Psytrance', 'Shoegaze', 'Space Rock', 'Trop Rock', 'World Music',
        'Neoclassical', 'Audiobook', 'Audio Theatre', 'Neue Deutsche Welle',
        'Podcast', 'Indie Rock', 'G-Funk', 'Dubstep', 'Garage Rock',
        'Psybient',
    )
    _ID3V2_2_IMAGE_FORMATS = {
        b'bmp': 'image/bmp',
        b'jpg': 'image/jpeg',
        b'png': 'image/png',
    }
    _IMAGE_TYPES = (
        'other.generic',
        'other.icon',
        'other.alt_icon',
        'front_cover',
        'back_cover',
        'other.leaflet',
        'media',
        'other.lead_artist',
        'other.artist',
        'other.conductor',
        'other.band',
        'other.composer',
        'other.lyricist',
        'other.recording_location',
        'other.during_recording',
        'other.during_performance',
        'other.screen_capture',
        'other.bright_colored_fish',
        'other.illustration',
        'other.band_logo',
        'other.publisher_logo',
    )
    _UNKNOWN_IMAGE_TYPE = 'other.unknown'

    def __init__(self) -> None:
        super().__init__()
        self._only_id3 = False
        self._modern_grouping_values: list[str] = []
        self._legacy_grouping_values: list[str] = []

    def _parse(self, fh: BinaryIO) -> None:
        audio_offset = fh.tell()
        tag_size = 0
        if self._parse_tags:
            tag_size = self._parse_id3v2(fh)
        elif self._parse_duration:
            tag_size, _extended, _major = self._parse_id3v2_header(fh)
        if tag_size > 0:
            audio_offset += self._ID3V2_HEADER_SIZE + tag_size
        fh.seek(audio_offset)
        if self._only_id3:
            return
        header = fh.read(4)
        if ((self.filename is not None and self.filename.endswith('.flac'))
                or header == b'fLaC'):
            self.mime_type = 'audio/flac'
            fh.seek(audio_offset)
            flac_tag = _Flac()
            flac_tag.filename = self.filename
            flac_tag.filesize = self.filesize
            flac_tag._filehandler = fh
            flac_tag._load(
                tags=self._parse_tags, duration=self._parse_duration,
                image=self._load_image)
            self._update(flac_tag)
        else:
            self.mime_type = 'audio/mpeg'
            end_padding = 0
            if self.filesize >= self._ID3V1_TAG_SIZE:
                # try parsing id3v1 at the end of file
                fh.seek(-self._ID3V1_TAG_SIZE, SEEK_END)
                if self._parse_id3v1(fh):
                    end_padding = self._ID3V1_TAG_SIZE
            fh.seek(audio_offset)
            mpeg_tag = _MPEG()
            mpeg_tag.filename = self.filename
            mpeg_tag.filesize = self.filesize
            mpeg_tag._filehandler = fh
            mpeg_tag._end_padding = end_padding
            mpeg_tag._load(tags=False, duration=self._parse_duration)
            self._update(mpeg_tag)
        self._tags_parsed = self._parse_tags
        self._duration_parsed = self._parse_duration

    def _parse_id3v2_header(self, fh: BinaryIO) -> tuple[int, bool, int]:
        size = major = 0
        extended = False
        # for info on the specs, see: http://id3.org/Developer%20Information
        header = fh.read(self._ID3V2_HEADER_SIZE)
        # check if there is an ID3v2 tag at the beginning of the file
        if (len(header) == self._ID3V2_HEADER_SIZE
                and header.startswith(b'ID3')):
            major = header[3]
            extended = (header[5] & 0x40) > 0
            size += self._unsynchsafe(header, 6)
            if _DEBUG:
                print(f'Found id3 v2.{major} tag with size {size}')
        return size, extended, major

    def _parse_id3v2(self, fh: BinaryIO) -> int:
        size, extended, major = self._parse_id3v2_header(fh)
        if size <= 0:
            return size
        parsed_size = self._ID3V2_HEADER_SIZE
        if extended:  # just read over the extended header.
            extd_size = self._unsynchsafe(fh.read(6))
            parsed_size += extd_size
            fh.seek(extd_size - 6, SEEK_CUR)  # jump over extended_header
        while parsed_size < size:
            frame_size = self._parse_frame(fh, size, id3version=major)
            if frame_size == -1:
                break
            parsed_size += frame_size
        self._set_grouping_work_fields()
        return size

    def _parse_id3v1(self, fh: BinaryIO) -> bool:
        if self._parse_tags:
            content = fh.read(3 + 30 + 30 + 30 + 4 + 30 + 1)
        else:
            content = fh.read(3)
        if not content.startswith(b'TAG'):  # check if this is an ID3 v1 tag
            return False
        if not self._parse_tags:
            return True

        def asciidecode(x: bytes) -> str:
            return self._unpad(
                x.decode(self._default_encoding or 'latin1', 'replace'))
        # Only set fields that were not set by ID3v2 tags, as ID3v1
        # tags are more likely to be outdated or have encoding issues
        if not self.title:
            value = asciidecode(content[3:33])
            self._set_field('title', value)
        if not self.artist:
            value = asciidecode(content[33:63])
            self._set_field('artist', value)
        if not self.album:
            value = asciidecode(content[63:93])
            self._set_field('album', value)
        if not self.year:
            value = asciidecode(content[93:97])
            self._set_field('year', value)
        comment = content[97:127]
        if comment[-2] == 0 and comment[-1] != 0:
            if self.track is None:
                self._set_field('track', comment[-1])
            comment = comment[:-2]
        if not self.comment:
            value = asciidecode(comment)
            self._set_field('comment', value)
        if not self.genre:
            genre_id = content[127]
            if genre_id < len(self._ID3V1_GENRES):
                self._set_field('genre', self._ID3V1_GENRES[genre_id])
        return True

    def _set_custom_field(self, custom_field_name: str, value: str) -> None:
        custom_field_name_lower = custom_field_name.lower()
        field_name = self._ID3_MAPPING_CUSTOM.get(
            custom_field_name_lower,
            self._OTHER_PREFIX + custom_field_name_lower)
        self._set_field(field_name, value)

    def _set_grouping_work_fields(self) -> None:
        # iTunes 12.5.4.42 added a new GRP1 frame for 'grouping', and
        # repurposed the TIT1 frame for 'work'. Handle this mess here.
        if self._modern_grouping_values:
            for value in self._modern_grouping_values:
                self._set_other_field('grouping', value)
            for value in self._legacy_grouping_values:
                self._set_other_field('work', value)
            return
        for value in self._legacy_grouping_values:
            self._set_other_field('grouping', value)

    @classmethod
    def _create_tag_image(cls,
                          data: bytes,
                          pic_type: int,
                          mime_type: str | None = None,
                          description: str | None = None) -> tuple[str, Image]:
        field_name = cls._UNKNOWN_IMAGE_TYPE
        if 0 <= pic_type <= len(cls._IMAGE_TYPES):
            field_name = cls._IMAGE_TYPES[pic_type]
        name = field_name
        if field_name.startswith(cls._OTHER_PREFIX):
            name = field_name[len(cls._OTHER_PREFIX):]
        image = Image(name, len(data), data)
        if mime_type:
            image.mime_type = mime_type
        if description:
            image.description = description
        return field_name, image

    def _parse_image(self,
                     frame_id: bytes,
                     content: bytes) -> tuple[str, Image]:
        # See section 4.14: http://id3.org/id3v2.4.0-frames
        encoding = content[0]
        if frame_id == b'PIC':  # ID3 v2.2:
            imgformat = content[1:4].lower()
            mime_type = self._ID3V2_2_IMAGE_FORMATS.get(imgformat)
            desc_start_pos = 5
        else:  # ID3 v2.3+
            mime_start_pos = 1
            mime_end_pos = self._find_string_end_pos(
                content, start_pos=mime_start_pos)
            mime_type = self._decode_string(
                content[mime_start_pos:mime_end_pos]).lower()
            desc_start_pos = mime_end_pos + 1
        pic_type = content[desc_start_pos - 1]
        desc_end_pos = self._find_string_end_pos(
            content, encoding, desc_start_pos)
        # skip stray null byte in broken file
        if (desc_end_pos + 1 < len(content)
                and content[desc_end_pos] == 0x00
                and content[desc_end_pos + 1] != 0x00):
            desc_end_pos += 1
        desc = self._decode_string(
            content[desc_start_pos:desc_end_pos], encoding)
        return self._create_tag_image(
            content[desc_end_pos:], pic_type, mime_type, desc)

    @staticmethod
    def _lrc_timestamp(seconds: float) -> str:
        cs = int(seconds * 100)
        minutes, cs = divmod(cs, 6000)
        seconds, cs = divmod(cs, 100)
        return f"{minutes:02d}:{seconds:02d}.{cs:02d}"

    def _parse_synced_lyrics(self, content: bytes) -> str:
        # Convert ID3 synced lyrics to LRC format
        lyrics = ""
        content_length = len(content)
        encoding = content[0]
        # skip language (3)
        timestamp_format = content[4]
        # skip content type (1)
        start_pos = 6
        end_pos = self._find_string_end_pos(content, encoding, start_pos)
        offset = end_pos
        found_line = False
        while offset < content_length:
            end_pos = self._find_string_end_pos(content, encoding, offset)
            value = self._decode_string(
                content[offset:end_pos], encoding).lstrip('\n')
            offset = end_pos
            if offset + 4 > content_length:
                break
            time = unpack_from('>I', content, offset)[0]
            offset += 4
            if found_line:
                lyrics += '\n'
            found_line = True
            if timestamp_format == 0x02:
                # time in milliseconds
                timestamp = self._lrc_timestamp(time / 1000)
            else:
                lyrics += value
                continue
            lyrics += f'[{timestamp}]{value}'
        return lyrics

    def _parse_frame(self,
                     fh: BinaryIO,
                     total_size: int,
                     id3version: int | None = None) -> int:
        # ID3v2.2 especially ugly. see: http://id3.org/id3v2-00
        header_len = parsed_size = 6 if id3version == 2 else 10
        frame_size_bytes = 3 if id3version == 2 else 4
        is_synchsafe_int = id3version == 4
        header = fh.read(header_len)
        if len(header) != header_len:
            return -1
        frame_id = header[:frame_size_bytes]
        if frame_id in self._EMPTY_FRAME_IDS:
            return -1
        frame_size: int
        if frame_size_bytes == 3:
            frame_size = int.from_bytes(header[3:6], 'big')
        elif is_synchsafe_int:
            frame_size = self._unsynchsafe(header, 4)
        else:
            frame_size = unpack_from('>I', header, 4)[0]
        parsed_size += frame_size
        if _DEBUG:
            print(f'Found id3 Frame {frame_id!r} at '
                  f'{fh.tell()}-{fh.tell() + frame_size} of {self.filesize}')
        if frame_size == 0:
            return parsed_size
        if frame_size > total_size:
            # invalid frame size, stop here
            return -1
        if self._parse_tags and frame_id in self._ID3_MAPPING:
            fieldname = self._ID3_MAPPING[frame_id]
            content = fh.read(frame_size)
            if fieldname in {'comment', 'other.lyrics'}:
                encoding = content[0]
                content = content[4:]
                end_pos = self._find_string_end_pos(content, encoding)
                value = self._decode_string(content[:end_pos], encoding)
                if end_pos < len(content):
                    content_descriptor = value
                    value = self._decode_string(content[end_pos:], encoding)
                    # check if comment is a key-value pair (used by iTunes)
                    if fieldname == 'comment' and content_descriptor and value:
                        self._set_custom_field(content_descriptor, value)
                        return parsed_size
                self._set_field(fieldname, value)
                return parsed_size
            if frame_id.startswith(b'W'):  # URL frame, no custom encoding
                value = self._decode_string(content)
                self._set_field(fieldname, value)
                return parsed_size
            encoding = content[0]
            content = content[1:]
            content_length = len(content)
            offset = 0
            while offset < content_length:
                end_pos = self._find_string_end_pos(content, encoding, offset)
                if end_pos <= offset:
                    end_pos = content_length
                value = self._decode_string(content[offset:end_pos], encoding)
                offset = end_pos
                if fieldname in {'track', 'disc', 'other.movement'}:
                    if '/' in value:
                        value, total = value.split('/')[:2]
                        if total.isdecimal():
                            self._set_field(f'{fieldname}_total', int(total))
                    if value.isdecimal():
                        self._set_field(fieldname, int(value))
                elif fieldname == 'genre':
                    genre_id = 255
                    # funky: id3v1 genre hidden in a id3v2 field
                    if value.isdecimal():
                        genre_id = int(value)
                    # funkier: the TCO may contain genres in parens, e.g '(13)'
                    elif value.startswith('('):
                        end_pos = value.find(')')
                        parens_text = value[1:end_pos]
                        if end_pos > 0 and parens_text.isdecimal():
                            genre_id = int(parens_text)
                    if 0 <= genre_id < len(self._ID3V1_GENRES):
                        value = self._ID3V1_GENRES[genre_id]
                    self._set_field(fieldname, value)
                elif fieldname == 'modern_grouping':
                    self._modern_grouping_values.append(value)
                elif fieldname == 'legacy_grouping':
                    self._legacy_grouping_values.append(value)
                else:
                    self._set_field(fieldname, value)
        elif self._parse_tags and frame_id in self._SYNCED_LYRICS_FRAME_IDS:
            content = fh.read(frame_size)
            lyrics = self._parse_synced_lyrics(content)
            self._set_other_field('lyrics', lyrics)
        elif self._parse_tags and frame_id in self._CUSTOM_FRAME_IDS:
            # custom fields
            content = fh.read(frame_size)
            encoding = content[0]
            end_pos = self._find_string_end_pos(
                content, encoding, start_pos=1)
            description = self._decode_string(content[1:end_pos], encoding)
            value = self._decode_string(content[end_pos:], encoding)
            if description and value:
                self._set_custom_field(description, value)
        elif self._parse_tags and frame_id == b'PRIV':
            content = fh.read(frame_size)
            owner_id_end_pos = self._find_string_end_pos(content)
            owner_id = content[:owner_id_end_pos - 1]
            if owner_id == b'XMP':
                value = self._unpad_bytes(
                    content[owner_id_end_pos:]).decode('utf-8', 'replace')
                self._set_other_field('xmp', value)
        elif self._parse_tags and frame_id not in self._IGNORED_FRAME_IDS:
            # unknown, try to add to other dict
            content = fh.read(frame_size)
            encoding = content[0]
            if encoding in self._VALID_STRING_ENCODINGS:
                value = self._decode_string(content[1:], encoding)
            else:
                value = self._decode_string(content)
            self._set_field(
                self._OTHER_PREFIX + frame_id.decode('latin-1').lower(),
                value)
        elif self._load_image and frame_id in self._IMAGE_FRAME_IDS:
            content = fh.read(frame_size)
            field_name, image = self._parse_image(frame_id, content)
            # pylint: disable=protected-access
            self.images._set_field(field_name, image)
        else:  # skip frame
            fh.seek(frame_size, SEEK_CUR)
        return parsed_size

    @staticmethod
    def _find_string_end_pos(content: bytes,
                             encoding: int = 0x00,
                             start_pos: int = 0) -> int:
        # latin1 and utf-8 are 1 byte
        if encoding == 0x00 or encoding == 0x03:
            end_pos = content.find(b'\x00', start_pos)
            return start_pos if end_pos < 0 else end_pos + 1
        end_pos = -1
        for i in range(start_pos, len(content) - 1, 2):
            if content[i] == 0x00 and content[i + 1] == 0x00:
                end_pos = i + 2
                break
        return start_pos if end_pos < 0 else end_pos

    def _decode_string(self, value: bytes, encoding: int | None = None) -> str:
        if encoding == 0x00:  # ISO-8859-1 (but allow override)
            encoding_name = self._default_encoding or 'ISO-8859-1'
        elif encoding == 0x01:  # UTF-16 with BOM
            # read byte order mark to determine endianness
            encoding_name = (
                'UTF-16be' if value.startswith(b'\xFE\xFF') else 'UTF-16le')
            # strip the bom if it exists
            if value.startswith(b'\xFE\xFF') or value.startswith(b'\xFF\xFE'):
                value = value[2:] if len(value) % 2 == 0 else value[2:-1]
        elif encoding == 0x02:  # UTF-16 without BOM
            encoding_name = 'UTF-16be'
            # strip optional null byte, if byte count uneven
            if len(value) % 2 != 0:
                value = value[:-1]
        elif encoding == 0x03:  # UTF-8
            encoding_name = 'UTF-8'
        else:
            encoding_name = 'ISO-8859-1'
        return self._unpad(value.decode(encoding_name, 'replace'))

    @staticmethod
    def _unsynchsafe(data: bytes, offset: int = 0) -> int:
        return (
            (data[offset] << 21)
            | (data[offset + 1] << 14)
            | (data[offset + 2] << 7)
            | data[offset + 3]
        )


class _MPEG(TinyTag):
    """MPEG Audio Parser."""

    _MAX_ESTIMATION_SEC = 30
    _CBR_DETECTION_FRAME_COUNT = 5
    _USE_XING_HEADER = True  # much faster, but can be deactivated for testing

    # see this page for the magic values used in mp3:
    # http://www.mpgedit.org/mpgedit/mpeg_format/mpeghdr.htm
    _SAMPLE_RATES = (
        (11025, 12000, 8000),   # MPEG Version 2.5
        (0, 0, 0),              # reserved
        (22050, 24000, 16000),  # MPEG Version 2
        (44100, 48000, 32000),  # MPEG Version 1
    )
    _V1L1 = (0, 32, 64, 96, 128, 160, 192, 224, 256, 288, 320, 352, 384, 416,
             448, 0)
    _V1L2 = (0, 32, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320,
             384, 0)
    _V1L3 = (0, 32, 40, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256,
             320, 0)
    _V2L1 = (0, 32, 48, 56, 64, 80, 96, 112, 128, 144, 160, 176, 192, 224,
             256, 0)
    _V2L2 = (0, 8, 16, 24, 32, 40, 48, 56, 64, 80, 96, 112, 128, 144, 160, 0)
    _V2L3 = _V2L2
    _NONE = (0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
    _BITRATE_VERSION_LAYERS = (
        # note that layers go from 3 to 1 by design, first layer id is reserved
        (_NONE, _V2L3, _V2L2, _V2L1),  # MPEG Version 2.5
        (_NONE, _NONE, _NONE, _NONE),  # reserved
        (_NONE, _V2L3, _V2L2, _V2L1),  # MPEG Version 2
        (_NONE, _V1L3, _V1L2, _V1L1),  # MPEG Version 1
    )
    _SAMPLES_PER_FRAME = (
        # note that layers go from 3 to 1 by design, first layer id is reserved
        (0, 576, 1152, 384),   # MPEG Version 2.5
        (0, 0, 0, 0),          # reserved
        (0, 576, 1152, 384),   # MPEG Version 2
        (0, 1152, 1152, 384),  # MPEG Version 1
    )
    _SLOT_SIZES = (
        0,  # reserved
        1,  # Layer III
        1,  # Layer II
        4,  # Layer I
    )
    _CHANNELS_PER_CHANNEL_MODE = (
        2,  # 00 Stereo
        2,  # 01 Joint stereo (Stereo)
        2,  # 10 Dual channel (2 mono channels)
        1,  # 11 Single channel (Mono)
    )

    def __init__(self) -> None:
        super().__init__()
        self._end_padding = 0

    def _parse(self, fh: BinaryIO) -> None:
        self.mime_type = 'audio/mpeg'
        if not self._parse_duration:
            return
        self.is_lossless = False
        samples_pf = 0
        max_estimation_frames = 0
        frame_size_accu = 0
        frames = 0  # count frames for determining mp3 duration
        bitrate_accu = 0    # add up bitrates to find average bitrate to detect
        last_bitrates: set[int] = set()  # CBR mp3s (many frames with same brs)
        # seek to first position after id3 tag (speedup for large header)
        first_id = None
        audio_offset = fh.tell()
        while True:
            # reading through garbage until 11 '1' sync-bits are found
            header = fh.read(4)
            header_len = len(header)
            if header_len < 4:
                if frames > 0:
                    self.bitrate = bitrate_accu / frames
                break  # EOF
            id_byte = header[1]
            br_sr_byte = header[2]
            br_id = (br_sr_byte >> 4) & ((1 << 4) - 1)
            sr_id = (br_sr_byte >> 2) & ((1 << 2) - 1)
            padding = (br_sr_byte >> 1) & ((1 << 1) - 1)
            mpeg_id = (id_byte >> 3) & ((1 << 2) - 1)
            layer_id = (id_byte >> 1) & ((1 << 2) - 1)
            version_id = (id_byte >> 1) & ((1 << 4) - 1)
            channel_mode = (header[3] >> 6) & ((1 << 2) - 1)
            # check for eleven 1s, validate bitrate and sample rate
            if (header[0] != 0xFF or (id_byte & 0xE0) != 0xE0
                    or (first_id is not None and first_id != version_id)
                    or br_id > 14 or br_id == 0 or sr_id == 3 or layer_id == 0
                    or mpeg_id == 1):
                # invalid frame, find next sync header
                idx = header.find(b'\xFF', 1)
                next_offset = header_len
                if idx != -1:
                    next_offset = idx
                    fh.seek(idx - header_len, SEEK_CUR)
                if frames == 0:
                    audio_offset += next_offset
                continue
            self.channels = self._CHANNELS_PER_CHANNEL_MODE[channel_mode]
            frame_br = self._BITRATE_VERSION_LAYERS[mpeg_id][layer_id][br_id]
            self.samplerate = samplerate = self._SAMPLE_RATES[mpeg_id][sr_id]
            samples_pf = self._SAMPLES_PER_FRAME[mpeg_id][layer_id]
            slot_size = self._SLOT_SIZES[layer_id]
            coefficient = (samples_pf // 8 // slot_size) * 1000
            frame_length = (
                ((coefficient * frame_br) // samplerate + padding) * slot_size)
            if first_id is None:
                first_id = version_id
                max_estimation_frames = (
                    (self._MAX_ESTIMATION_SEC * samplerate) // samples_pf)
            # There might be a xing header in the first frame that contains
            # all the info we need, otherwise parse multiple frames to find the
            # accurate average bitrate
            if frames == 0 and self._USE_XING_HEADER:
                xframes = 0
                byte_count = 0
                prev_offset = header_len + audio_offset
                frame_content = fh.read(min(50, frame_length))  # optimization
                xing_header_offset = frame_content.find(b'Xing')  # VBR
                if xing_header_offset == -1:
                    xing_header_offset = frame_content.find(b'Info')  # CBR
                if xing_header_offset != -1:
                    xframes, byte_count = self._parse_xing_header(
                        frame_content, xing_header_offset)
                    byte_count -= frame_length  # xing frame doesn't count
                else:
                    vbri_header_offset = frame_content.find(b'VBRI')
                    if vbri_header_offset != -1:
                        xframes, byte_count = self._parse_vbri_header(
                            frame_content, vbri_header_offset)
                if xframes > 0 and byte_count > 0:
                    self.duration = dur = xframes * samples_pf / samplerate
                    self.bitrate = byte_count * 8 / dur / 1000
                    self.is_vbr = True
                    self._duration_parsed = True
                    return
                fh.seek(prev_offset)
            frames += 1  # it's most probably a mp3 frame
            bitrate_accu += frame_br
            if frames <= self._CBR_DETECTION_FRAME_COUNT:
                last_bitrates.add(frame_br)
            frame_size_accu += frame_length
            # if bitrate does not change over time its probably CBR
            is_cbr = (frames == self._CBR_DETECTION_FRAME_COUNT
                      and len(last_bitrates) == 1)
            if frames == max_estimation_frames or is_cbr:
                # try to estimate duration
                stream_size = (
                    self.filesize - audio_offset - self._end_padding)
                est_frame_count = int(
                    stream_size / (frame_size_accu / frames) + 0.5)
                samples = est_frame_count * samples_pf
                self.duration = samples / samplerate
                self.bitrate = bitrate_accu / frames
                self._duration_parsed = True
                return
            if frame_length > 1:  # jump over current frame body
                fh.seek(frame_length - header_len, SEEK_CUR)
        if self.samplerate:
            self.duration = frames * samples_pf / self.samplerate
        self._duration_parsed = True

    @staticmethod
    def _parse_xing_header(content: bytes, offset: int) -> tuple[int, int]:
        # see: http://www.mp3-tech.org/programmer/sources/vbrheadersdk.zip
        offset += 4  # skip header ID
        header_flags = unpack_from('>i', content, offset)[0]
        offset += 4
        frames = byte_count = 0
        if header_flags & 1:  # FRAMES FLAG
            frames = unpack_from('>i', content, offset)[0]
            offset += 4
        if header_flags & 2:  # BYTES FLAG
            byte_count = unpack_from('>i', content, offset)[0]
            offset += 4
        return frames, byte_count

    @staticmethod
    def _parse_vbri_header(content: bytes, offset: int) -> tuple[int, int]:
        # https://teslabs.com/openplayer/docs/docs/specs/mp3_structure2.pdf
        offset += 10
        byte_count = unpack_from('>I', content, offset)[0]
        offset += 4
        frames = unpack_from('>I', content, offset)[0]
        offset += 4
        return frames, byte_count


class _Ogg(TinyTag):
    """OGG Parser."""

    _VORBIS_MAPPING = {
        'album': 'album',
        'albumartist': 'albumartist',
        'title': 'title',
        'artist': 'artist',
        'artists': 'artist',
        'author': 'artist',
        'date': 'year',
        'tracknumber': 'track',
        'tracktotal': 'track_total',
        'totaltracks': 'track_total',
        'discnumber': 'disc',
        'disctotal': 'disc_total',
        'totaldiscs': 'disc_total',
        'genre': 'genre',
        'description': 'comment',
        'comment': 'comment',
        'comments': 'comment',
        'composer': 'composer',
        'bpm': 'other.bpm',
        'copyright': 'other.copyright',
        'isrc': 'other.isrc',
        'lyrics': 'other.lyrics',
        'unsyncedlyrics': 'other.lyrics',
        'publisher': 'other.publisher',
        'language': 'other.language',
        'director': 'other.director',
        'website': 'other.url',
        'conductor': 'other.conductor',
        'lyricist': 'other.lyricist',
        'discsubtitle': 'other.set_subtitle',
        'setsubtitle': 'other.set_subtitle',
        'initialkey': 'other.initial_key',
        'key': 'other.initial_key',
        'encodedby': 'other.encoded_by',
        'encodersettings': 'other.encoder_settings',
        'media': 'other.media',
        'license': 'other.license',
        'barcode': 'other.barcode',
        'catalognumber': 'other.catalog_number',
        'movementname': 'other.movement_name',
        'movement': 'other.movement',
        'movementtotal': 'other.movement_total',
        'showmovement': 'other.show_movement',
        'grouping': 'other.grouping',
        'contentgroup': 'other.grouping',
        'work': 'other.work'
    }

    def __init__(self) -> None:
        super().__init__()
        self._granule_pos = 0
        self._audio_size = 0  # size of opus audio stream
        self._granule_pos_serial: int | None = None
        self._audio_size_serial: int | None = None

    def _parse(self, fh: BinaryIO) -> None:
        check_flac_second_packet = False
        check_speex_second_packet = False
        preskip = 0  # number of samples to skip in opus stream
        for packet, serial in self._parse_pages(fh):
            if packet.startswith(b'\x01vorbis'):
                if self._parse_duration:
                    channels, samplerate = unpack_from('<Bi', packet, 11)
                    bitrate = unpack_from('<i', packet, 20)[0]
                    if channels > 0:
                        self.channels = channels
                    if samplerate > 0:
                        self.samplerate = samplerate
                    if bitrate > 0:
                        self.bitrate = bitrate / 1000
                    self.mime_type = 'audio/ogg; codecs="vorbis"'
                    self.is_lossless = False
                    self._granule_pos_serial = serial
                    self._duration_parsed = True
            elif packet.startswith(b'\x03vorbis'):
                if self._parse_tags:
                    walker = BytesIO(packet)
                    walker.seek(7)  # jump over header name
                    self._set_vorbis_comment_fields(walker)
                    self._tags_parsed = True
            elif packet.startswith(b'OpusHead'):
                if self._parse_duration:  # parse opus header
                    # https://www.videolan.org/developers/vlc/modules/codec/opus_header.c
                    # https://mf4.xiph.org/jenkins/view/opus/job/opusfile-unix/ws/doc/html/structOpusHead.html
                    version, channels, preskip = unpack_from('<BBH', packet, 8)
                    if (version & 0xF0) == 0:  # only major version 0 supported
                        if channels > 0:
                            self.channels = channels
                        self.samplerate = 48000
                    self.mime_type = 'audio/ogg; codecs="opus"'
                    self.is_lossless = False
                    self._duration_parsed = True
                    self._granule_pos_serial = serial
            elif packet.startswith(b'OpusTags'):
                if self._parse_tags:  # parse opus metadata:
                    walker = BytesIO(packet)
                    walker.seek(8)  # jump over header name
                    self._set_vorbis_comment_fields(walker)
                    self._tags_parsed = True
                self._audio_size_serial = serial
            elif packet.startswith(b'\x7FFLAC'):
                # https://xiph.org/flac/ogg_mapping.html
                walker = BytesIO(packet)
                # jump over header name, version and number of headers
                walker.seek(9)
                # pylint: disable=protected-access
                flactag = _Flac()
                flactag.filename = self.filename
                flactag.filesize = self.filesize
                flactag._filehandler = walker
                flactag._load(
                    tags=False, duration=self._parse_duration,
                    image=self._load_image)
                self._update(flactag)
                if self._parse_duration:
                    self.mime_type = 'audio/ogg; codecs="flac"'
                    self.is_lossless = True
                self._duration_parsed = self._parse_duration
                check_flac_second_packet = True
            elif check_flac_second_packet:
                # second packet contains FLAC metadata block
                if self._parse_tags:
                    walker = BytesIO(packet)
                    meta_header = walker.read(4)
                    block_type = meta_header[0] & 0x7f
                    # pylint: disable=protected-access
                    if block_type == _Flac._VORBIS_COMMENT:
                        self._set_vorbis_comment_fields(walker)
                    self._tags_parsed = True
                check_flac_second_packet = False
            elif packet.startswith(b'Speex   '):
                # https://speex.org/docs/manual/speex-manual/node8.html
                if self._parse_duration:
                    samplerate = unpack_from('<i', packet, 36)[0]
                    channels, bitrate = unpack_from('<ii', packet, 48)
                    if samplerate > 0:
                        self.samplerate = samplerate
                    if channels > 0:
                        self.channels = channels
                    if bitrate > 0:
                        self.bitrate = bitrate / 1000
                    self.mime_type = 'audio/ogg; codecs="speex"'
                    self.is_lossless = False
                    self._granule_pos_serial = serial
                    self._duration_parsed = True
                check_speex_second_packet = True
            elif check_speex_second_packet:
                if self._parse_tags:
                    walker = BytesIO(packet)
                    self._set_vorbis_comment_fields(walker)
                    self._tags_parsed = True
                check_speex_second_packet = False
            if self._tags_parsed and not self._parse_duration:
                # Optimization: If we need to determine the duration, read
                # granule_pos of remaining pages, but skip contents of
                # segments. If we don't need the duration, stop here.
                break
        if self.duration is not None or not self.samplerate:
            return  # either ogg flac or invalid file
        self.duration = max(
            (self._granule_pos - preskip) / self.samplerate, 0
        )
        if self._audio_size and self.duration:  # opus file
            self.bitrate = self._audio_size * 8 / self.duration / 1000

    @classmethod
    def _parse_vorbis_comment(
        cls,
        fh: BinaryIO,
        load_image: bool = False,
        read_data: bool = True
    ) -> Iterator[tuple[str, str | int | Image]]:
        # for the spec, see: http://xiph.org/vorbis/doc/v-comment.html
        # discnumber tag based on: https://en.wikipedia.org/wiki/Vorbis_comment
        # https://sno.phy.queensu.ca/~phil/exiftool/TagNames/Vorbis.html
        vendor_length = unpack('<I', fh.read(4))[0]
        fh.seek(vendor_length, SEEK_CUR)  # jump over vendor
        elements = unpack('<I', fh.read(4))[0]
        for _i in range(elements):
            length = unpack('<I', fh.read(4))[0]
            if not read_data:
                fh.seek(length, SEEK_CUR)
                continue
            keyvalpair = fh.read(length).decode('utf-8', 'replace')
            if '=' in keyvalpair:
                key, value = keyvalpair.split('=', 1)
                key_lower = key.lower()
                if key_lower == "metadata_block_picture":
                    if load_image:
                        if _DEBUG:
                            print('Found Vorbis Image', key, value[:64])
                        # pylint: disable=protected-access
                        result = _Flac._parse_image(BytesIO(a2b_base64(value)))
                        if result is not None:
                            fieldname, fieldvalue = result
                            yield fieldname, fieldvalue
                else:
                    if _DEBUG:
                        print('Found Vorbis Comment', key, value[:64])
                    fieldname = cls._VORBIS_MAPPING.get(
                        key_lower, cls._OTHER_PREFIX + key_lower)
                    if fieldname in {
                        'track', 'disc', 'track_total', 'disc_total'
                    }:
                        if fieldname in {'track', 'disc'} and '/' in value:
                            value, total = value.split('/')[:2]
                            if total.isdecimal():
                                yield f'{fieldname}_total', int(total)
                        if value.isdecimal():
                            yield fieldname, int(value)
                    else:
                        yield fieldname, value

    def _set_vorbis_comment_fields(self, fh: BinaryIO) -> None:
        for fieldname, value in self._parse_vorbis_comment(
            fh, self._load_image
        ):
            if isinstance(value, Image):
                self.images._set_field(fieldname, value)
                continue
            self._set_field(fieldname, value)

    def _parse_pages(self, fh: BinaryIO) -> Iterator[tuple[bytearray, int]]:
        # for the spec, see: https://wiki.xiph.org/Ogg
        packets: dict[int, bytearray] = {}
        last_granule_pos = 0
        last_audio_size = 0
        header_len = 27
        page_header = fh.read(header_len)  # read ogg page header
        if (not page_header.startswith(b'OggS')
                or not page_header.startswith(b'\x00', 4)):
            raise ParseError('Invalid OGG header')
        self.mime_type = 'audio/ogg'
        while len(page_header) == header_len:
            version = page_header[4]
            if not page_header.startswith(b'OggS') or version != 0:
                # Garbage found after parsing a valid page
                break
            # https://xiph.org/ogg/doc/framing.html
            header_type = page_header[5]
            eos = header_type & 0x04
            granule_pos, serial = unpack_from('<qI', page_header, 6)
            if serial not in packets:
                packets[serial] = bytearray()
            packet_data = packets[serial]
            audio_size_serial_match = serial == self._audio_size_serial
            if serial == self._granule_pos_serial:
                if eos:
                    self._granule_pos = granule_pos
                else:
                    self._granule_pos = last_granule_pos
                    last_granule_pos = granule_pos
            segments = page_header[26]
            seg_sizes = fh.read(segments)
            read_size = 0
            audio_size = 0
            for seg_size in seg_sizes:  # read all segments
                read_size += seg_size
                if audio_size_serial_match:
                    audio_size += seg_size
                # less than 255 bytes means end of packet
                if seg_size < 255 and not self._tags_parsed:
                    packet_data += fh.read(read_size)
                    yield packet_data, serial
                    packet_data.clear()
                    read_size = 0
            if read_size > 0:
                if self._tags_parsed and self._duration_parsed:
                    fh.seek(read_size, SEEK_CUR)
                else:  # packet continues on next page
                    packet_data += fh.read(read_size)
            if audio_size_serial_match:
                if eos:
                    self._audio_size += last_audio_size + audio_size
                else:
                    self._audio_size += last_audio_size
                    last_audio_size = audio_size
            page_header = fh.read(header_len)


class _Wave(TinyTag):
    """WAVE Parser.

    https://sno.phy.queensu.ca/~phil/exiftool/TagNames/RIFF.html
    """

    _RIFF_MAPPING = {
        b'INAM': 'title',
        b'TITL': 'title',
        b'IPRD': 'album',
        b'IART': 'artist',
        b'IBPM': 'other.bpm',
        b'ICMT': 'comment',
        b'IMUS': 'composer',
        b'ICOP': 'other.copyright',
        b'ICRD': 'year',
        b'IGNR': 'genre',
        b'ILNG': 'other.language',
        b'ISRC': 'other.isrc',
        b'IPUB': 'other.publisher',
        b'IPRT': 'track',
        b'ITRK': 'track',
        b'TRCK': 'track',
        b'IBSU': 'other.url',
        b'YEAR': 'year',
        b'IWRI': 'other.lyricist',
        b'IENC': 'other.encoded_by',
        b'IMED': 'other.media',
    }
    _UNCOMPRESSED_FORMATS = {
        0x01,  # PCM
        0x03,  # IEEE Float
    }
    _LOSSLESS_FORMATS = {
        0x01,    # PCM
        0x03,    # IEEE Float
        0x163,   # WMA Lossless
        0x8ae,   # ClearJump LiteWave (lossless)
        0x1971,  # Sonic Foundry LOSSLESS
        0xf1ac,  # FLAC
    }

    def _parse(self, fh: BinaryIO) -> None:
        # http://www-mmsp.ece.mcgill.ca/Documents/AudioFormats/WAVE/WAVE.html
        # https://en.wikipedia.org/wiki/WAV
        header = fh.read(12)
        if not header.startswith(b'RIFF') or not header.startswith(b'WAVE', 8):
            raise ParseError('Invalid WAV header')
        self.mime_type = 'audio/wav'
        block_align = 0
        audio_size = 0
        num_samples = 0
        header_len = 8
        chunk_header = fh.read(header_len)
        while len(chunk_header) == header_len:
            subchunk_size = unpack_from('<I', chunk_header, 4)[0]
            subchunk_size_unpadded = subchunk_size
            # IFF chunks are padded to an even number of bytes
            subchunk_size += subchunk_size % 2
            if self._parse_duration and chunk_header.startswith(b'fmt '):
                chunk = fh.read(subchunk_size)
                format_tag, channels, samplerate = unpack_from(
                    '<HHI', chunk)
                block_align, bitdepth = unpack_from('<HH', chunk, 12)
                if format_tag == 0xFFFE:  # Extensible, read subformat
                    format_tag = unpack_from('<H', chunk, 24)[0]
                if channels > 0:
                    self.channels = channels
                if samplerate > 0:
                    self.samplerate = samplerate
                if bitdepth > 0:
                    self.bitdepth = bitdepth
                if format_tag:
                    self.mime_type = f'audio/wav; codecs="{format_tag:X}"'
                    self.is_lossless = format_tag in self._LOSSLESS_FORMATS
            elif self._parse_duration and chunk_header.startswith(b'data'):
                audio_size = subchunk_size_unpadded
                fh.seek(subchunk_size, SEEK_CUR)
            elif self._parse_duration and chunk_header.startswith(b'fact'):
                chunk = fh.read(subchunk_size)
                num_samples = unpack_from('<I', chunk)[0]
            elif self._parse_tags and chunk_header.startswith(b'LIST'):
                chunk = fh.read(subchunk_size)
                if chunk.startswith(b'INFO'):
                    walker = BytesIO(chunk)
                    walker.seek(4)  # skip header
                    field = walker.read(4)
                    while len(field) == 4:
                        data_length = unpack('<I', walker.read(4))[0]
                        # IFF chunks are padded to an even size
                        data_length += data_length % 2
                        data = self._unpad_bytes(walker.read(data_length))
                        if field in self._RIFF_MAPPING:
                            fieldname = self._RIFF_MAPPING[field]
                        else:
                            fieldname = (
                                self._OTHER_PREFIX
                                + field.decode('latin-1')).lower()
                        value = data.decode('utf-8', 'replace')
                        if fieldname == 'track':
                            if value.isdecimal():
                                self._set_field(fieldname, int(value))
                        else:
                            self._set_field(fieldname, value)
                        field = walker.read(4)
            elif (self._parse_tags
                    and chunk_header.startswith((b'id3 ', b'ID3 '))):
                # pylint: disable=protected-access
                id3 = _ID3()
                id3.filename = self.filename
                id3.filesize = self.filesize
                id3._filehandler = BytesIO(fh.read(subchunk_size))
                id3._only_id3 = True
                id3._load(tags=True, duration=False, image=self._load_image)
                self._update(id3)
            elif self._parse_tags and chunk_header.startswith(b'_PMX'):
                chunk = self._unpad_bytes(fh.read(subchunk_size))
                value = chunk.decode('utf-8', 'replace')
                self._set_other_field('xmp', value)
            else:  # some other chunk, just skip the data
                fh.seek(subchunk_size, SEEK_CUR)
            chunk_header = fh.read(header_len)
        if not self.is_lossless and self.samplerate:
            if audio_size == 0:
                # Normalization due to some encoders setting num_samples to 1
                # when no audio data is present.
                num_samples = 0
            self.duration = num_samples / self.samplerate
            if self.duration:
                self.bitrate = audio_size * 8 / self.duration / 1000
        elif block_align and self.samplerate:
            self.duration = audio_size / (block_align * self.samplerate)
            self.bitrate = block_align * self.samplerate * 8 / 1000
        self._duration_parsed = self._parse_duration
        self._tags_parsed = self._parse_tags


class _Flac(TinyTag):
    """FLAC Parser."""

    _STREAMINFO = 0
    _VORBIS_COMMENT = 4
    _PICTURE = 6

    def _parse(self, fh: BinaryIO) -> None:
        header = fh.read(4)
        if not header.startswith(b'fLaC'):
            raise ParseError('Invalid FLAC header')
        # for spec, see https://xiph.org/flac/ogg_mapping.html
        self.mime_type = 'audio/flac'
        found_streaminfo = False
        header_len = 4
        block_header = fh.read(header_len)
        while len(block_header) == header_len:
            block_type = block_header[0] & 0x7f
            is_last_block = bool(block_header[0] & 0x80)
            is_streaminfo_block = (block_type == self._STREAMINFO)
            size = int.from_bytes(block_header[1:], 'big')
            # http://xiph.org/flac/format.html#metadata_block_streaminfo
            if (self._parse_duration and is_streaminfo_block
                    and not found_streaminfo):
                head = fh.read(size)
                # From the xiph documentation:
                # py | <bits>
                # ----------------------------------------------
                # H  | <16>  The minimum block size (in samples)
                # H  | <16>  The maximum block size (in samples)
                # 3s | <24>  The minimum frame size (in bytes)
                # 3s | <24>  The maximum frame size (in bytes)
                # 8B | <20>  Sample rate in Hz.
                #    | <3>   (number of channels)-1.
                #    | <5>   (bits per sample)-1.
                #    | <36>  Total samples in stream.
                # 16s| <128> MD5 signature
                #                 channels--.  bits      total samples
                # |----- samplerate -----| |-||----| |---------~   ~----|
                # 0000 0000 0000 0000 0000 0000 0000 0000 0000      0000
                # #---4---# #---5---# #---6---# #---7---# #--8-~   ~-12-#
                info_byte = unpack_from(">Q", head, 10)[0]
                samplerate = (info_byte >> 44) & ((1 << 20) - 1)
                channels = ((info_byte >> 41) & ((1 << 3) - 1)) + 1
                bitdepth = ((info_byte >> 36) & ((1 << 5) - 1)) + 1
                total_samples = info_byte & ((1 << 36) - 1)
                if samplerate > 0:
                    self.samplerate = samplerate
                    self.duration = duration = total_samples / samplerate
                    if duration > 0:
                        self.bitrate = self.filesize * 8 / duration / 1000
                self.channels = channels
                self.bitdepth = bitdepth
                self.is_lossless = True
            elif block_type == self._VORBIS_COMMENT:
                # Some files in the wild contain incorrect block sizes for
                # Vorbis comment blocks. Attempt to parse the block as usual
                # to find the actual size.
                # pylint: disable=protected-access
                for fieldname, value in _Ogg._parse_vorbis_comment(
                    fh, read_data=self._parse_tags
                ):
                    if not isinstance(value, Image):
                        self._set_field(fieldname, value)
            elif block_type == self._PICTURE:
                # Some files in the wild contain incorrect block sizes for
                # picture blocks. Attempt to parse the block as usual to find
                # the actual size.
                result = self._parse_image(fh, read_data=self._load_image)
                if result is not None:
                    # pylint: disable=protected-access
                    fieldname, value = result
                    self.images._set_field(fieldname, value)
            else:
                fh.seek(size, SEEK_CUR)  # seek over this block
            if is_streaminfo_block and not found_streaminfo:
                # Ignore subsequent STREAMINFO blocks, if any. They are not
                # permitted in the spec, and increase the risk of parsing
                # garbage data as stream info due to the zero value block type.
                found_streaminfo = True
            if is_last_block:
                break
            block_header = fh.read(header_len)
        if self.duration:
            audio_offset = fh.tell()
            bitrate = (self.filesize - audio_offset) * 8 / self.duration / 1000
            if bitrate > 0:
                self.bitrate = bitrate
        self._duration_parsed = self._parse_duration
        self._tags_parsed = self._parse_tags

    @classmethod
    def _parse_image(cls,
                     fh: BinaryIO,
                     read_data: bool = True) -> tuple[str, Image] | None:
        # https://xiph.org/flac/format.html#metadata_block_picture
        mime_type = None
        pic_type, mime_type_len = unpack('>II', fh.read(8))
        if read_data:
            mime_type = fh.read(mime_type_len).decode('utf-8', 'replace')
        else:
            fh.seek(mime_type_len, SEEK_CUR)
        description = None
        description_len = unpack('>I', fh.read(4))[0]
        if read_data:
            description = fh.read(description_len).decode('utf-8', 'replace')
        else:
            fh.seek(description_len, SEEK_CUR)
        fh.seek(16, SEEK_CUR)  # jump over width, height, depth, colors
        pic_len = unpack('>I', fh.read(4))[0]
        if not read_data:
            fh.seek(pic_len, SEEK_CUR)
            return None
        # pylint: disable=protected-access
        return _ID3._create_tag_image(
            fh.read(pic_len), pic_type, mime_type, description)


class _ASF(TinyTag):
    """ASF (WMA) Parser.

    http://web.archive.org/web/20131203084402/http://msdn.microsoft.com/en-us/library/bb643323.aspx
    http://uguisu.skr.jp/Windows/format_asf.html
    """

    _ASF_MAPPING = {
        'Title': 'title',
        'Author': 'artist',
        'Description': 'comment',
        'Copyright': 'other.copyright',
        'WM/ARTISTS': 'artist',
        'WM/TrackNumber': 'track',
        'WM/PartOfSet': 'disc',
        'WM/Year': 'year',
        'WM/AlbumArtist': 'albumartist',
        'WM/Genre': 'genre',
        'WM/AlbumTitle': 'album',
        'WM/Composer': 'composer',
        'WM/Publisher': 'other.publisher',
        'WM/BeatsPerMinute': 'other.bpm',
        'WM/InitialKey': 'other.initial_key',
        'WM/Lyrics': 'other.lyrics',
        'WM/Language': 'other.language',
        'WM/Director': 'other.director',
        'WM/AuthorURL': 'other.url',
        'WM/ISRC': 'other.isrc',
        'WM/Conductor': 'other.conductor',
        'WM/Writer': 'other.lyricist',
        'WM/SetSubTitle': 'other.set_subtitle',
        'WM/EncodedBy': 'other.encoded_by',
        'WM/EncodingSettings': 'other.encoder_settings',
        'WM/Media': 'other.media',
        'WM/Barcode': 'other.barcode',
        'WM/CatalogNo': 'other.catalog_number',
        'WM/ContentGroupDescription': 'other.grouping',
        'WM/Work': 'other.work'
    }
    _UNPACK_FORMATS = {
        1: '<B',
        2: '<H',
        4: '<I',
        8: '<Q'
    }
    _ASF_CONTENT_DESC = (
        b'\x33\x26\xB2\x75\x8E\x66\xCF\x11\xA6\xD9\x00\xAA\x00\x62\xCE\x6C'
    )
    _ASF_EXT_CONTENT_DESC = (
        b'\x40\xA4\xD0\xD2\x07\xE3\xD2\x11\x97\xF0\x00\xA0\xC9\x5E\xA8\x50'
    )
    _ASF_FILE_PROP = (
        b'\xA1\xDC\xAB\x8C\x47\xA9\xCF\x11\x8E\xE4\x00\xC0\x0C\x20\x53\x65'
    )
    _ASF_STREAM_PROPS = (
        b'\x91\x07\xDC\xB7\xB7\xA9\xCF\x11\x8E\xE6\x00\xC0\x0C\x20\x53\x65'
    )
    _STREAM_TYPE_ASF_AUDIO_MEDIA = (
        b'\x40\x9E\x69\xF8\x4D\x5B\xCF\x11\xA8\xFD\x00\x80\x5F\x5C\x44\x2B'
    )
    _ASF_HEADER_EXTENSION = (
        b'\xB5\x03\xBf\x5F\x2E\xA9\xCF\x11\x8E\xE3\x00\xC0\x0C\x20\x53\x65'
    )
    _ASF_METADATA = (
        b'\xEA\xCB\xF8\xC5\xAF\x5B\x77\x48\x84\x67\xAA\x8C\x44\xFA\x4C\xCA'
    )
    _ASF_METADATA_LIBRARY = (
        b'\x94\x1c\x23\x44\x98\x94\xd1\x49\xa1\x41\x1d\x13\x4E\x45\x70\x54'
    )
    _XMP_METADATA = (
        b'\xCB\xCF\x7A\xBE\xA9\x97\xE8\x42\x9C\x71\x99\x94\x91\xE3\xAF\xAC'
    )

    def _parse(self, fh: BinaryIO) -> None:
        # http://www.garykessler.net/library/file_sigs.html
        # http://web.archive.org/web/20131203084402/http://msdn.microsoft.com/en-us/library/bb643323.aspx#_Toc521913958
        header = fh.read(30)
        if (not header.startswith(
            b'\x30\x26\xB2\x75\x8E\x66\xCF\x11\xA6\xD9\x00\xAA\x00\x62\xCE\x6C'
        ) or not header.startswith(b'\x02', 29)):
            raise ParseError('Invalid WMA header')
        self.mime_type = 'application/vnd.ms-asf'
        header_len = 24
        object_header = fh.read(header_len)
        while len(object_header) == header_len:
            object_size = unpack_from('<Q', object_header, 16)[0]
            if object_size < header_len:
                break
            object_size -= header_len
            if (self._parse_tags
                    and object_header.startswith(self._ASF_CONTENT_DESC)):
                walker = BytesIO(fh.read(object_size))
                (title_length, author_length,
                 copyright_length, description_length,
                 rating_length) = unpack('<5H', walker.read(10))
                data_blocks = {
                    'title': title_length,
                    'artist': author_length,
                    'other.copyright': copyright_length,
                    'comment': description_length,
                    '_rating': rating_length,
                }
                for i_field_name, length in data_blocks.items():
                    value = self._unpad(
                        walker.read(length).decode('utf-16', 'replace'))
                    if not i_field_name.startswith('_') and value:
                        self._set_field(i_field_name, value)
            elif (self._parse_tags
                    and object_header.startswith(self._ASF_EXT_CONTENT_DESC)):
                # http://web.archive.org/web/20131203084402/http://msdn.microsoft.com/en-us/library/bb643323.aspx#_Toc509555195
                walker = BytesIO(fh.read(object_size))
                descriptor_count = unpack('<H', walker.read(2))[0]
                for _ in range(descriptor_count):
                    name_len = unpack('<H', walker.read(2))[0]
                    name = self._unpad(
                        walker.read(name_len).decode('utf-16', 'replace'))
                    value_type, value_len = unpack('<HH', walker.read(4))
                    self._parse_value(walker, name, value_type, value_len)
            elif (self._parse_tags
                    and object_header.startswith(self._ASF_HEADER_EXTENSION)):
                offset = fh.seek(18, SEEK_CUR)  # skip reserved fields
                data_size = unpack('<I', fh.read(4))[0]
                offset += 4
                end_offset = offset + data_size
                while offset < end_offset:
                    subheader = fh.read(header_len)
                    offset += len(subheader)
                    sub_size = max(
                        unpack_from('<Q', subheader, 16)[0] - header_len, 0)
                    if subheader.startswith(
                        (self._ASF_METADATA, self._ASF_METADATA_LIBRARY)
                    ):
                        content = fh.read(sub_size)
                        walker = BytesIO(content)
                        offset += len(content)
                        descriptor_count = unpack('<H', walker.read(2))[0]
                        for _ in range(descriptor_count):
                            walker.seek(4, SEEK_CUR)  # skip lang, stream num
                            name_len = unpack('<H', walker.read(2))[0]
                            value_type = unpack('<H', walker.read(2))[0]
                            value_len = unpack('<I', walker.read(4))[0]
                            name = self._unpad(
                                walker.read(name_len)
                                .decode('utf-16', 'replace'))
                            self._parse_value(
                                walker, name, value_type, value_len)
                    else:
                        offset = fh.seek(sub_size, SEEK_CUR)
            elif (self._parse_duration
                    and object_header.startswith(self._ASF_FILE_PROP)):
                data = fh.read(object_size)
                play_duration = unpack_from('<Q', data, 40)[0] / 10000000
                preroll = unpack_from('<Q', data, 56)[0] / 1000
                # subtract the preroll to get the actual duration
                self.duration = max(play_duration - preroll, 0.0)
            elif (self._parse_duration
                    and object_header.startswith(self._ASF_STREAM_PROPS)):
                data = fh.read(object_size)
                stream_type = data[:16]
                if stream_type == self._STREAM_TYPE_ASF_AUDIO_MEDIA:
                    (format_tag, channels, samplerate,
                     avg_bytes_per_second) = unpack_from('<HHII', data, 54)
                    if channels > 0:
                        self.channels = channels
                    if samplerate > 0:
                        self.samplerate = samplerate
                    if avg_bytes_per_second > 0:
                        self.bitrate = avg_bytes_per_second * 8 / 1000
                    if format_tag:
                        self.mime_type = (
                            f'application/vnd.ms-asf; codecs="{format_tag:X}"')
                        # pylint: disable=protected-access
                        self.is_lossless = (
                            format_tag in _Wave._LOSSLESS_FORMATS)
                    bitdepth = unpack_from('<H', data, 68)[0]
                    if bitdepth > 0:
                        self.bitdepth = bitdepth
            elif (self._parse_tags
                    and object_header.startswith(self._XMP_METADATA)):
                value = fh.read(object_size).decode('utf-8', 'replace')
                self._set_other_field('xmp', value)
            else:
                # skip unknown object ids
                fh.seek(object_size, SEEK_CUR)
            object_header = fh.read(header_len)
        self._duration_parsed = self._parse_duration
        self._tags_parsed = self._parse_tags

    def _parse_value(self,
                     fh: BytesIO,
                     name: str,
                     value_type: int,
                     value_len: int) -> None:
        # Unicode string
        if value_type == 0:
            value = self._unpad(fh.read(value_len).decode('utf-16', 'replace'))
        # DWORD / QWORD / WORD
        elif (1 < value_type < 6
                and value_len in self._UNPACK_FORMATS):
            fmt = self._UNPACK_FORMATS[value_len]
            value = str(unpack(fmt, fh.read(value_len))[0])
        else:
            fh.seek(value_len, SEEK_CUR)  # skip other values
            return
        # try to get normalized field name
        if name in self._ASF_MAPPING:
            field_name = self._ASF_MAPPING[name]
        else:  # custom field
            if name.startswith('WM/'):
                name = name[3:]
            field_name = self._OTHER_PREFIX + name.lower()
        if field_name in {'track', 'disc'}:
            if value.isdecimal():
                self._set_field(field_name, int(value))
        else:
            self._set_field(field_name, value)


class _Aiff(TinyTag):
    """AIFF Parser.

    https://en.wikipedia.org/wiki/Audio_Interchange_File_Format#Data_format
    https://web.archive.org/web/20171118222232/http://www-mmsp.ece.mcgill.ca/documents/audioformats/aiff/aiff.html
    https://web.archive.org/web/20071219035740/http://www.cnpbagwell.com/aiff-c.txt

    A few things about the spec:

    * IFF strings are not supposed to be null terminated, but sometimes
      are.
    * Some tools might throw more metadata into the ANNO chunk, but it is
      wildly unreliable to count on it. In fact, the official spec
      recommends against using it. That said... this code throws the
      ANNO field into comment and hopes for the best.

    The key thing here is that AIFF metadata is usually in a handful of
    fields and the rest is an ID3 or XMP field.  XMP is too complicated
    and only Adobe-related products support it. The vast majority use
    ID3.
    """

    _AIFF_MAPPING = {
        b'NAME': 'title',
        b'AUTH': 'artist',
        b'ANNO': 'comment',
        b'(c) ': 'other.copyright',
    }
    _UNCOMPRESSED_FORMATS = {
        'NONE',
        'raw ',
        'twos',
        'sowt',
        'in24',
        '42ni',
        'in32',
        '23ni',
        'fl32',
        'FL32',
        'fl64',
        'FL64',
    }

    def _parse(self, fh: BinaryIO) -> None:
        header = fh.read(12)
        if (not header.startswith(b'FORM')
                or not header.startswith((b'AIFC', b'AIFF'), 8)):
            raise ParseError('Invalid AIFF header')
        self.mime_type = 'audio/aiff'
        header_len = 8
        chunk_header = fh.read(header_len)
        while len(chunk_header) == header_len:
            subchunk_id = chunk_header[:4]
            subchunk_size = unpack_from('>I', chunk_header, 4)[0]
            # IFF chunks are padded to an even number of bytes
            subchunk_size += subchunk_size % 2
            if self._parse_tags and subchunk_id in self._AIFF_MAPPING:
                chunk = self._unpad_bytes(fh.read(subchunk_size))
                for subvalue in chunk.split(b'\x00'):
                    self._set_field(
                        self._AIFF_MAPPING[subchunk_id],
                        subvalue.decode('utf-8', 'replace'))
            elif self._parse_duration and chunk_header.startswith(b'COMM'):
                chunk = fh.read(subchunk_size)
                channels, num_frames, bitdepth = unpack_from('>hLh', chunk)
                if channels > 0:
                    self.channels = channels
                if bitdepth > 0:
                    self.bitdepth = bitdepth
                try:
                    # Extended precision
                    exp, mantissa = unpack_from('>HQ', chunk, 8)
                    sr = int(mantissa * (2 ** (exp - 0x3FFF - 63)))
                    if sr > 0:
                        duration = num_frames / sr
                        bitrate = sr * channels * bitdepth / 1000
                        if bitrate > 0:
                            self.bitrate = bitrate
                        self.samplerate, self.duration = sr, duration
                except OverflowError:
                    # Invalid sample rate
                    pass
                compression_type = chunk[18:22].decode('latin-1')
                if not compression_type:
                    compression_type = 'NONE'  # uncompressed
                self.mime_type = (
                    f'audio/aiff; codecs="{compression_type}"')
                self.is_lossless = (
                    compression_type in self._UNCOMPRESSED_FORMATS)
                self._duration_parsed = True
                if not self._parse_tags:
                    break
            elif (self._parse_tags
                    and chunk_header.startswith((b'id3 ', b'ID3 '))):
                # pylint: disable=protected-access
                id3 = _ID3()
                id3.filename = self.filename
                id3.filesize = self.filesize
                id3._filehandler = BytesIO(fh.read(subchunk_size))
                id3._only_id3 = True
                id3._load(tags=True, duration=False, image=self._load_image)
                self._update(id3)
            elif self._parse_tags and chunk_header.startswith(b'APPL'):
                chunk = fh.read(subchunk_size)
                if chunk.startswith(b'XMP '):
                    content = self._unpad_bytes(chunk[4:])
                    value = content.decode('utf-8', 'replace')
                    self._set_other_field('xmp', value)
            else:  # some other chunk, just skip the data
                fh.seek(subchunk_size, SEEK_CUR)
            chunk_header = fh.read(header_len)
        self._tags_parsed = self._parse_tags
