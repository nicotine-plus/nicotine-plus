# tinytag - an audio file metadata reader
# http://github.com/tinytag/tinytag

# MIT License

# Copyright (c) 2014-2025 Tom Wallroth, Mat (mathiascode), et al.
# Copyright (c) 2020-2025 Nicotine+ Contributors

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

"""Audio file metadata reader."""

from __future__ import annotations
from binascii import a2b_base64
from io import BytesIO
from os import PathLike, SEEK_CUR, SEEK_END, environ, fsdecode
from struct import unpack

TYPE_CHECKING = False

# Lazy imports for type checking
if TYPE_CHECKING:
    from collections.abc import Callable, Iterator  # pylint: disable-all
    from typing import Any, BinaryIO, Dict, List, Union

    _StringListDict = Dict[str, List[str]]
    _ImageListDict = Dict[str, List["Image"]]
    _DataTreeDict = Dict[
        bytes, Union['_DataTreeDict', Callable[..., Dict[str, Any]]]]
else:
    _StringListDict = _ImageListDict = _DataTreeDict = dict

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
        '.oga', '.ogg', '.opus', '.spx',
        '.wav', '.flac', '.wma',
        '.m4b', '.m4a', '.m4r', '.m4v', '.mp4', '.aax', '.aaxc',
        '.aiff', '.aifc', '.aif', '.afc'
    )
    _OTHER_PREFIX = 'other.'
    _file_extension_mapping: dict[tuple[str, ...], type[TinyTag]] | None = None

    def __init__(self) -> None:
        self.filename: str | None = None
        self.filesize = 0

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
        self.other: _StringListDict = OtherFields()

        self._filehandler: BinaryIO | None = None
        self._default_encoding: str | None = None  # override for some formats
        self._parse_duration = True
        self._parse_tags = True
        self._load_image = False
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
            ignore_errors: bool | None = None) -> TinyTag:
        """Return a tag object for an audio file."""
        should_close_file = file_obj is None
        filename_str = None
        if filename:
            if should_close_file:
                # pylint: disable=consider-using-with
                file_obj = open(filename, 'rb')
            filename_str = fsdecode(filename)
        if file_obj is None:
            raise ValueError(
                'Either filename or file_obj argument is required')
        if ignore_errors is not None:
            # pylint: disable=import-outside-toplevel
            from warnings import warn
            warn('ignore_errors argument is obsolete, and will be removed in '
                 'the future', DeprecationWarning, stacklevel=2)
        try:
            # pylint: disable=protected-access
            file_obj.seek(0, SEEK_END)
            filesize = file_obj.tell()
            file_obj.seek(0)
            parser_class = cls._get_parser_class(filename_str, file_obj)
            tag = parser_class()
            tag._filehandler = file_obj
            tag._default_encoding = encoding
            tag.filename = filename_str
            tag.filesize = filesize
            if filesize > 0:
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
        fields: dict[str, str | float | list[str]] = {}
        for key, value in self.__dict__.items():
            if key.startswith('_'):
                continue
            if isinstance(value, Images):
                continue
            if not isinstance(value, OtherFields):
                if value is None:
                    continue
                if key != 'filename' and isinstance(value, str):
                    fields[key] = [value]
                else:
                    fields[key] = value
                continue
            for other_key, other_values in value.items():
                other_fields = fields.get(other_key)
                if not isinstance(other_fields, list):
                    other_fields = fields[other_key] = []
                other_fields += other_values
        return fields

    @classmethod
    def _get_parser_for_filename(cls, filename: str) -> type[TinyTag] | None:
        if cls._file_extension_mapping is None:
            cls._file_extension_mapping = {
                ('.mp1', '.mp2', '.mp3'): _ID3,
                ('.oga', '.ogg', '.opus', '.spx'): _Ogg,
                ('.wav',): _Wave,
                ('.flac',): _Flac,
                ('.wma',): _Wma,
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
        header = filehandle.read(35)
        filehandle.seek(0)
        if header.startswith(b'ID3') or header.startswith(b'\xff\xfb'):
            return _ID3
        if header.startswith(b'fLaC'):
            return _Flac
        if ((header[4:8] == b'ftyp'
             and header[8:11] in {b'M4A', b'M4B', b'aax'})
                or b'\xff\xf1' in header):
            return _MP4
        if (header.startswith(b'OggS')
            and (header[29:33] == b'FLAC' or header[29:35] == b'vorbis'
                 or header[28:32] == b'Opus' or header[29:34] == b'Speex')):
            return _Ogg
        if header.startswith(b'RIFF') and header[8:12] == b'WAVE':
            return _Wave
        if header.startswith(b'\x30\x26\xB2\x75\x8E\x66\xCF\x11\xA6\xD9\x00'
                             b'\xAA\x00\x62\xCE\x6C'):
            return _Wma
        if header.startswith(b'FORM') and header[8:12] in {b'AIFF', b'AIFC'}:
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
        # try determining the file type by magic byte header
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
        if tags:
            self._parse_tag(self._filehandler)
        if duration:
            if tags:  # rewind file if the tags were already parsed
                self._filehandler.seek(0)
            self._determine_duration(self._filehandler)

    def _set_field(self, fieldname: str, value: str | float,
                   check_conflict: bool = True) -> None:
        if fieldname.startswith(self._OTHER_PREFIX):
            fieldname = fieldname[len(self._OTHER_PREFIX):]
            if check_conflict and fieldname in self.__dict__:
                fieldname = '_' + fieldname
            if fieldname not in self.other:
                self.other[fieldname] = []
            self.other[fieldname].append(str(value))
            if _DEBUG:
                print(f'Adding value "{value} to field "{fieldname}"')
            return
        old_value = self.__dict__.get(fieldname)
        new_value = value
        if isinstance(new_value, str):
            # First value goes in tag, others in tag.other
            values = new_value.split('\x00')
            for index, i_value in enumerate(values):
                if index or old_value and i_value != old_value:
                    self._set_field(
                        self._OTHER_PREFIX + fieldname, i_value,
                        check_conflict=False)
                    continue
                new_value = i_value
            if old_value:
                return
        elif not new_value and old_value:
            # Prioritize non-zero integer values
            return
        if _DEBUG:
            print(f'Setting field "{fieldname}" to "{new_value!r}"')
        self.__dict__[fieldname] = new_value

    def _determine_duration(self, fh: BinaryIO) -> None:
        raise NotImplementedError

    def _parse_tag(self, fh: BinaryIO) -> None:
        raise NotImplementedError

    def _update(self, other: TinyTag) -> None:
        # update the values of this tag with the values from another tag
        for key, value in other.__dict__.items():
            if key.startswith('_'):
                continue
            if isinstance(value, OtherFields):
                for other_key, other_values in other.other.items():
                    for other_value in other_values:
                        self._set_field(
                            self._OTHER_PREFIX + other_key, other_value,
                            check_conflict=False)
            elif isinstance(value, Images):
                self.images._update(value)  # pylint: disable=protected-access
            elif value is not None:
                self._set_field(key, value)

    @staticmethod
    def _unpad(s: str) -> str:
        # certain strings *may* be terminated with a zero byte at the end
        return s.strip('\x00')

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
        """Deprecated, use 'other' instead."""
        from warnings import warn  # pylint: disable=import-outside-toplevel
        warn("'extra' attribute is deprecated, and will be "
             "removed in the future. Use 'other' instead.",
             DeprecationWarning, stacklevel=2)
        extra_keys = {'copyright', 'initial_key', 'isrc', 'lyrics', 'url'}
        return {k: v[0] for k, v in self.other.items() if k in extra_keys}


class Images:
    """A class containing images embedded in an audio file."""
    _OTHER_PREFIX = 'other.'

    def __init__(self) -> None:
        self.front_cover: Image | None = None
        self.back_cover: Image | None = None
        self.media: Image | None = None

        self.other: _ImageListDict = OtherImages()
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
                    other_images = images[other_key] = []
                other_images += other_values
        return images

    def _set_field(self, fieldname: str, value: Image) -> None:
        old_value = self.__dict__.get(fieldname)
        if fieldname.startswith(self._OTHER_PREFIX) or old_value is not None:
            fieldname = fieldname[len(self._OTHER_PREFIX):]
            other_values = self.other.get(fieldname, [])
            other_values.append(value)
            if _DEBUG:
                print(f'Setting other image field "{fieldname}"')
            self.other[fieldname] = other_values
            return
        if _DEBUG:
            print(f'Setting image field "{fieldname}"')
        self.__dict__[fieldname] = value

    def _update(self, other: Images) -> None:
        for key, value in other.__dict__.items():
            if isinstance(value, OtherImages):
                for other_key, other_values in value.items():
                    for image_other in other_values:
                        self._set_field(
                            self._OTHER_PREFIX + other_key, image_other)
                continue
            if value is not None:
                self._set_field(key, value)


class Image:
    """A class representing an image embedded in an audio file."""
    def __init__(self,
                 name: str,
                 data: bytes,
                 mime_type: str | None = None) -> None:
        self.name = name
        self.data = data
        self.mime_type = mime_type
        self.description: str | None = None

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
        13: 'image/jpeg',
        14: 'image/png'
    }
    _UNPACK_FORMATS = {
        1: '>b',
        2: '>h',
        4: '>i',
        8: '>q'
    }
    _VERSIONED_ATOMS = {b'meta', b'stsd'}  # those have an extra 4 byte header
    _FLAGGED_ATOMS = {b'stsd'}  # these also have an extra 4 byte header
    _ILST_PATH = [b'ftyp', b'moov', b'udta', b'meta', b'ilst']

    _audio_data_tree: _DataTreeDict | None = None
    _meta_data_tree: _DataTreeDict | None = None

    def _determine_duration(self, fh: BinaryIO) -> None:
        # https://developer.apple.com/library/mac/documentation/QuickTime/QTFF/QTFFChap3/qtff3.html
        if _MP4._audio_data_tree is None:
            _MP4._audio_data_tree = {
                b'moov': {
                    b'mvhd': _MP4._parse_mvhd,
                    b'trak': {b'mdia': {b"minf": {b"stbl": {b"stsd": {
                        b'mp4a': _MP4._parse_audio_sample_entry_mp4a,
                        b'alac': _MP4._parse_audio_sample_entry_alac
                    }}}}}
                }
            }
        self._traverse_atoms(fh, path=_MP4._audio_data_tree)

    def _parse_tag(self, fh: BinaryIO) -> None:
        # The parser tree: Each key is an atom name which is traversed if
        # existing. Leaves of the parser tree are callables which receive
        # the atom data. Callables return {fieldname: value} which is updates
        # the TinyTag.
        if _MP4._meta_data_tree is None:
            _MP4._meta_data_tree = {b'moov': {b'udta': {b'meta': {b'ilst': {
                # http://atomicparsley.sourceforge.net/mpeg-4files.html
                # https://metacpan.org/dist/Image-ExifTool/source/lib/Image/ExifTool/QuickTime.pm#L3093
                b'\xa9ART': {b'data': _MP4._data_parser('artist')},
                b'\xa9alb': {b'data': _MP4._data_parser('album')},
                b'\xa9cmt': {b'data': _MP4._data_parser('comment')},
                b'\xa9com': {b'data': _MP4._data_parser('composer')},
                b'\xa9con': {b'data': _MP4._data_parser('other.conductor')},
                b'\xa9day': {b'data': _MP4._data_parser('year')},
                b'\xa9des': {b'data': _MP4._data_parser('other.description')},
                b'\xa9dir': {b'data': _MP4._data_parser('other.director')},
                b'\xa9gen': {b'data': _MP4._data_parser('genre')},
                b'\xa9lyr': {b'data': _MP4._data_parser('other.lyrics')},
                b'\xa9mvn': {b'data': _MP4._data_parser('movement')},
                b'\xa9nam': {b'data': _MP4._data_parser('title')},
                b'\xa9pub': {b'data': _MP4._data_parser('other.publisher')},
                b'\xa9too': {b'data': _MP4._data_parser('other.encoded_by')},
                b'\xa9wrt': {b'data': _MP4._data_parser('composer')},
                b'aART': {b'data': _MP4._data_parser('albumartist')},
                b'cprt': {b'data': _MP4._data_parser('other.copyright')},
                b'desc': {b'data': _MP4._data_parser('other.description')},
                b'disk': {b'data': _MP4._nums_parser('disc', 'disc_total')},
                b'gnre': {b'data': _MP4._parse_id3v1_genre},
                b'trkn': {b'data': _MP4._nums_parser('track', 'track_total')},
                b'tmpo': {b'data': _MP4._data_parser('other.bpm')},
                b'covr': {b'data': _MP4._parse_cover_image},
                b'----': _MP4._parse_custom_field,
            }}}}}
        self._traverse_atoms(fh, path=_MP4._meta_data_tree)

    def _traverse_atoms(self,
                        fh: BinaryIO,
                        path: _DataTreeDict,
                        stop_pos: int | None = None,
                        curr_path: list[bytes] | None = None) -> None:
        header_len = 8
        atom_header = fh.read(header_len)
        while len(atom_header) == header_len:
            atom_size = unpack('>I', atom_header[:4])[0] - header_len
            atom_type = atom_header[4:]
            if curr_path is None:  # keep track how we traversed in the tree
                curr_path = [atom_type]
            if atom_size <= 0:  # empty atom, jump to next one
                atom_header = fh.read(header_len)
                continue
            if _DEBUG:
                print(f'{" " * 4 * len(curr_path)} '
                      f'pos: {fh.tell() - header_len} '
                      f'atom: {atom_type!r} len: {atom_size + header_len}')
            if atom_type in self._VERSIONED_ATOMS:  # jump atom version for now
                fh.seek(4, SEEK_CUR)
            if atom_type in self._FLAGGED_ATOMS:  # jump atom flags for now
                fh.seek(4, SEEK_CUR)
            sub_path = path.get(atom_type, None)
            # if the path leaf is a dict, traverse deeper into the tree:
            if isinstance(sub_path, dict):
                atom_end_pos = fh.tell() + atom_size
                self._traverse_atoms(fh, path=sub_path, stop_pos=atom_end_pos,
                                     curr_path=curr_path + [atom_type])
            # if the path-leaf is a callable, call it on the atom data
            elif callable(sub_path):
                for fieldname, value in sub_path(fh.read(atom_size)).items():
                    if _DEBUG:
                        print(' ' * 4 * len(curr_path), 'FIELD: ', fieldname)
                    if isinstance(value, Image):
                        if self._load_image:
                            # pylint: disable=protected-access
                            self.images._set_field(
                                fieldname[len('images.'):], value)
                    elif isinstance(value, list):
                        for subval in value:
                            self._set_field(fieldname, subval)
                    else:
                        self._set_field(fieldname, value)
            # unknown data atom, try to parse it
            elif curr_path == self._ILST_PATH:
                atom_end_pos = fh.tell() + atom_size
                field_name = self._OTHER_PREFIX + atom_type.decode('latin-1')
                fh.seek(-header_len, SEEK_CUR)
                self._traverse_atoms(
                    fh,
                    path={atom_type: {b'data': self._data_parser(field_name)}},
                    stop_pos=atom_end_pos, curr_path=curr_path + [atom_type])
            # if no action was specified using dict or callable, jump over atom
            else:
                fh.seek(atom_size, SEEK_CUR)
            # check if we have reached the end of this branch:
            if stop_pos and fh.tell() >= stop_pos:
                return  # return to parent (next parent node in tree)
            atom_header = fh.read(header_len)  # read next atom

    @classmethod
    def _data_parser(cls, fieldname: str) -> Callable[[bytes], dict[str, str]]:
        def _parse_data_atom(data_atom: bytes) -> dict[str, str]:
            data_type = unpack('>I', data_atom[:4])[0]
            data = data_atom[8:]
            value = None
            if data_type == 1:     # UTF-8 string
                value = data.decode('utf-8', 'replace')
            elif data_type == 21:  # BE signed integer
                fmts = cls._UNPACK_FORMATS
                data_len = len(data)
                if data_len in fmts:
                    value = str(unpack(fmts[data_len], data)[0])
            if value:
                return {fieldname: value}
            return {}
        return _parse_data_atom

    @classmethod
    def _nums_parser(
        cls, fieldname1: str, fieldname2: str
    ) -> Callable[[bytes], dict[str, int]]:
        def _parse_nums(data_atom: bytes) -> dict[str, int]:
            number_data = data_atom[8:14]
            numbers = unpack('>3H', number_data)
            # for some reason the first number is always irrelevant.
            return {fieldname1: numbers[1], fieldname2: numbers[2]}
        return _parse_nums

    @classmethod
    def _parse_id3v1_genre(cls, data_atom: bytes) -> dict[str, str]:
        # dunno why genre is offset by -1 but that's how mutagen does it
        idx = unpack('>H', data_atom[8:])[0] - 1
        result = {}
        # pylint: disable=protected-access
        if idx < len(_ID3._ID3V1_GENRES):
            result['genre'] = _ID3._ID3V1_GENRES[idx]
        return result

    @classmethod
    def _parse_cover_image(cls, data_atom: bytes) -> dict[str, Image]:
        data_type = unpack('>I', data_atom[:4])[0]
        image = Image(
            'front_cover', data_atom[8:], cls._IMAGE_MIME_TYPES.get(data_type))
        return {'images.front_cover': image}

    @classmethod
    def _read_extended_descriptor(cls, esds_atom: BinaryIO) -> None:
        for _i in range(4):
            if esds_atom.read(1) != b'\x80':
                break

    @classmethod
    def _parse_custom_field(cls, data: bytes) -> dict[str, list[str]]:
        fh = BytesIO(data)
        header_len = 8
        field_name = None
        values = []
        atom_header = fh.read(header_len)
        while len(atom_header) == header_len:
            atom_size = unpack('>I', atom_header[:4])[0] - header_len
            atom_type = atom_header[4:]
            if atom_type == b'name':
                atom_value = fh.read(atom_size)[4:].lower()
                field_name = atom_value.decode('utf-8', 'replace')
                # pylint: disable=protected-access
                field_name = cls._CUSTOM_FIELD_NAME_MAPPING.get(
                    field_name, TinyTag._OTHER_PREFIX + field_name)
            elif atom_type == b'data' and field_name:
                data_atom = fh.read(atom_size)
                parser = cls._data_parser(field_name)
                atom_values = parser(data_atom)
                if field_name in atom_values:
                    values.append(atom_values[field_name])
            else:
                fh.seek(atom_size, SEEK_CUR)
            atom_header = fh.read(header_len)  # read next atom
        if field_name and values:
            return {field_name: values}
        return {}

    @classmethod
    def _parse_audio_sample_entry_mp4a(cls, data: bytes) -> dict[str, int]:
        # this atom also contains the esds atom:
        # https://ffmpeg.org/doxygen/0.6/mov_8c-source.html
        # http://xhelmboyx.tripod.com/formats/mp4-layout.txt
        # http://sasperger.tistory.com/103

        # jump over version and flags
        channels = unpack('>H', data[16:18])[0]
        # jump over bit_depth, QT compr id & pkt size
        sr = unpack('>I', data[22:26])[0]

        # ES Description Atom
        esds_atom_size = unpack('>I', data[28:32])[0]
        esds_atom = BytesIO(data[36:36 + esds_atom_size])
        esds_atom.seek(5, SEEK_CUR)   # jump over version, flags and tag

        # ES Descriptor
        cls._read_extended_descriptor(esds_atom)
        esds_atom.seek(4, SEEK_CUR)   # jump over ES id, flags and tag

        # Decoder Config Descriptor
        cls._read_extended_descriptor(esds_atom)
        esds_atom.seek(9, SEEK_CUR)
        avg_br = unpack('>I', esds_atom.read(4))[0] / 1000  # kbit/s
        return {'channels': channels, 'samplerate': sr, 'bitrate': avg_br}

    @classmethod
    def _parse_audio_sample_entry_alac(cls, data: bytes) -> dict[str, int]:
        # https://github.com/macosforge/alac/blob/master/ALACMagicCookieDescription.txt
        bitdepth = data[45]
        channels = data[49]
        avg_br, sr = unpack('>II', data[56:64])
        avg_br /= 1000  # kbit/s
        return {'channels': channels, 'samplerate': sr, 'bitrate': avg_br,
                'bitdepth': bitdepth}

    @classmethod
    def _parse_mvhd(cls, data: bytes) -> dict[str, float]:
        # http://stackoverflow.com/a/3639993/1191373
        version = data[0]
        # jump over flags, create & mod times
        if version == 0:  # uses 32 bit integers for timestamps
            time_scale, duration = unpack('>II', data[12:20])
        else:  # version == 1:  # uses 64-bit integers for timestamps
            time_scale, duration = unpack('>IQ', data[20:32])
        return {'duration': duration / time_scale}


class _ID3(TinyTag):
    """MP3 Parser."""

    _ID3_MAPPING = {
        # Mapping from Frame ID to a field of the TinyTag
        # https://exiftool.org/TagNames/ID3.html
        'COMM': 'comment', 'COM': 'comment',
        'TRCK': 'track', 'TRK': 'track',
        'TYER': 'year', 'TYE': 'year', 'TDRC': 'year',
        'TALB': 'album', 'TAL': 'album',
        'TPE1': 'artist', 'TP1': 'artist',
        'TIT2': 'title', 'TT2': 'title',
        'TCON': 'genre', 'TCO': 'genre',
        'TPOS': 'disc', 'TPA': 'disc',
        'TPE2': 'albumartist', 'TP2': 'albumartist',
        'TCOM': 'composer', 'TCM': 'composer',
        'WOAR': 'other.url', 'WAR': 'other.url',
        'TSRC': 'other.isrc', 'TRC': 'other.isrc',
        'TCOP': 'other.copyright', 'TCR': 'other.copyright',
        'TBPM': 'other.bpm', 'TBP': 'other.bpm',
        'TKEY': 'other.initial_key', 'TKE': 'other.initial_key',
        'TLAN': 'other.language', 'TLA': 'other.language',
        'TPUB': 'other.publisher', 'TPB': 'other.publisher',
        'USLT': 'other.lyrics', 'ULT': 'other.lyrics',
        'TPE3': 'other.conductor', 'TP3': 'other.conductor',
        'TEXT': 'other.lyricist', 'TXT': 'other.lyricist',
        'TSST': 'other.set_subtitle',
        'TENC': 'other.encoded_by', 'TEN': 'other.encoded_by',
        'TSSE': 'other.encoder_settings', 'TSS': 'other.encoder_settings',
        'TMED': 'other.media', 'TMT': 'other.media',
        'WCOP': 'other.license',
    }
    _ID3_MAPPING_CUSTOM = {
        'artists': 'artist',
        'director': 'other.director',
        'license': 'other.license',
        'barcode': 'other.barcode',
        'catalognumber': 'other.catalog_number',
    }
    _IMAGE_FRAME_IDS = {'APIC', 'PIC'}
    _CUSTOM_FRAME_IDS = {'TXXX', 'TXX'}
    _IGNORED_FRAME_IDS = {
        'AENC', 'CRA',
        'ATXT',
        'CHAP',
        'COMR',
        'CRM',
        'CTOC',
        'ENCR',
        'GEOB', 'GEO',
        'GRID',
        'MCDI', 'MCI',
        'PRIV',
        'RGAD',
        'STC', 'SYTC'
    }
    _ID3V1_TAG_SIZE = 128
    _MAX_ESTIMATION_SEC = 30.0
    _CBR_DETECTION_FRAME_COUNT = 5
    _USE_XING_HEADER = True  # much faster, but can be deactivated for testing

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
        'bmp': 'image/bmp',
        'jpg': 'image/jpeg',
        'png': 'image/png',
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

    # see this page for the magic values used in mp3:
    # http://www.mpgedit.org/mpgedit/mpeg_format/mpeghdr.htm
    _SAMPLE_RATES = (
        (11025, 12000, 8000),   # MPEG 2.5
        (0, 0, 0),              # reserved
        (22050, 24000, 16000),  # MPEG 2
        (44100, 48000, 32000),  # MPEG 1
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
    _SAMPLES_PER_FRAME = 1152  # the default frame size for mp3
    _CHANNELS_PER_CHANNEL_MODE = (
        2,  # 00 Stereo
        2,  # 01 Joint stereo (Stereo)
        2,  # 10 Dual channel (2 mono channels)
        1,  # 11 Single channel (Mono)
    )

    def __init__(self) -> None:
        super().__init__()
        # save position after the ID3 tag for duration measurement speedup
        self._bytepos_after_id3v2 = -1

    @staticmethod
    def _parse_xing_header(fh: BinaryIO) -> tuple[int, int]:
        # see: http://www.mp3-tech.org/programmer/sources/vbrheadersdk.zip
        fh.seek(4, SEEK_CUR)  # read over Xing header
        header_flags = unpack('>i', fh.read(4))[0]
        frames = byte_count = 0
        if header_flags & 1:  # FRAMES FLAG
            frames = unpack('>i', fh.read(4))[0]
        if header_flags & 2:  # BYTES FLAG
            byte_count = unpack('>i', fh.read(4))[0]
        if header_flags & 4:  # TOC FLAG
            fh.seek(100, SEEK_CUR)
        if header_flags & 8:  # VBR SCALE FLAG
            fh.seek(4, SEEK_CUR)
        return frames, byte_count

    def _determine_duration(self, fh: BinaryIO) -> None:
        # if tag reading was disabled, find start position of audio data
        if self._bytepos_after_id3v2 == -1:
            self._parse_id3v2_header(fh)

        max_estimation_frames = (
            (self._MAX_ESTIMATION_SEC * 44100) // self._SAMPLES_PER_FRAME)
        frame_size_accu = 0
        audio_offset = self._bytepos_after_id3v2
        frames = 0  # count frames for determining mp3 duration
        bitrate_accu = 0    # add up bitrates to find average bitrate to detect
        last_bitrates = set()  # CBR mp3s (multiple frames with same bitrates)
        # seek to first position after id3 tag (speedup for large header)
        first_mpeg_id = None
        fh.seek(self._bytepos_after_id3v2)
        while True:
            # reading through garbage until 11 '1' sync-bits are found
            header = fh.read(4)
            header_len = len(header)
            if header_len < 4:
                if frames:
                    self.bitrate = bitrate_accu / frames
                break  # EOF
            _sync, conf, bitrate_freq, rest = unpack('4B', header)
            br_id = (bitrate_freq >> 4) & 0x0F  # biterate id
            sr_id = (bitrate_freq >> 2) & 0x03  # sample rate id
            padding = 1 if bitrate_freq & 0x02 > 0 else 0
            mpeg_id = (conf >> 3) & 0x03
            layer_id = (conf >> 1) & 0x03
            channel_mode = (rest >> 6) & 0x03
            # check for eleven 1s, validate bitrate and sample rate
            if (header[:2] <= b'\xFF\xE0'
                    or (first_mpeg_id is not None and first_mpeg_id != mpeg_id)
                    or br_id > 14 or br_id == 0 or sr_id == 3 or layer_id == 0
                    or mpeg_id == 1):
                # invalid frame, find next sync header
                idx = header.find(b'\xFF', 1)
                next_offset = header_len
                if idx != -1:
                    next_offset -= idx
                    fh.seek(idx - header_len, SEEK_CUR)
                if frames == 0:
                    audio_offset += next_offset
                continue
            if first_mpeg_id is None:
                first_mpeg_id = mpeg_id
            self.channels = self._CHANNELS_PER_CHANNEL_MODE[channel_mode]
            frame_br = self._BITRATE_VERSION_LAYERS[mpeg_id][layer_id][br_id]
            self.samplerate = samplerate = self._SAMPLE_RATES[mpeg_id][sr_id]
            frame_length = (144000 * frame_br) // samplerate + padding
            # There might be a xing header in the first frame that contains
            # all the info we need, otherwise parse multiple frames to find the
            # accurate average bitrate
            if frames == 0 and self._USE_XING_HEADER:
                prev_offset = header_len + audio_offset
                frame_content = fh.read(frame_length)
                xing_header_offset = frame_content.find(b'Xing')
                if xing_header_offset != -1:
                    fh.seek(prev_offset + xing_header_offset)
                    xframes, byte_count = self._parse_xing_header(fh)
                    if xframes > 0 and byte_count > 0:
                        # MPEG-2 Audio Layer III uses 576 samples per frame
                        samples_pf = self._SAMPLES_PER_FRAME
                        if mpeg_id <= 2:
                            samples_pf = 576
                        self.duration = dur = xframes * samples_pf / samplerate
                        self.bitrate = byte_count * 8 / dur / 1000
                        self.is_vbr = True
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
                    self.filesize - audio_offset - self._ID3V1_TAG_SIZE)
                est_frame_count = stream_size / (frame_size_accu / frames)
                samples = est_frame_count * self._SAMPLES_PER_FRAME
                self.duration = samples / samplerate
                self.bitrate = bitrate_accu / frames
                return

            if frame_length > 1:  # jump over current frame body
                fh.seek(frame_length - header_len, SEEK_CUR)
        if self.samplerate:
            self.duration = frames * self._SAMPLES_PER_FRAME / self.samplerate

    def _parse_tag(self, fh: BinaryIO) -> None:
        self._parse_id3v2(fh)
        if self.filesize >= self._ID3V1_TAG_SIZE:
            # try parsing id3v1 at the end of file
            fh.seek(self.filesize - self._ID3V1_TAG_SIZE)
            self._parse_id3v1(fh)

    def _parse_id3v2_header(self, fh: BinaryIO) -> tuple[int, bool, int]:
        size = major = 0
        extended = False
        # for info on the specs, see: http://id3.org/Developer%20Information
        header = fh.read(10)
        # check if there is an ID3v2 tag at the beginning of the file
        if header.startswith(b'ID3'):
            major = header[3]
            if _DEBUG:
                print(f'Found id3 v2.{major}')
            extended = (header[5] & 0x40) > 0
            size = self._unsynchsafe(unpack('4B', header[6:10]))
        self._bytepos_after_id3v2 = size
        return size, extended, major

    def _parse_id3v2(self, fh: BinaryIO) -> None:
        size, extended, major = self._parse_id3v2_header(fh)
        if size <= 0:
            return
        end_pos = fh.tell() + size
        parsed_size = 0
        if extended:  # just read over the extended header.
            extd_size = self._unsynchsafe(unpack('4B', fh.read(6)[:4]))
            fh.seek(extd_size - 6, SEEK_CUR)  # jump over extended_header
        while parsed_size < size:
            frame_size = self._parse_frame(fh, size, id3version=major)
            if frame_size == 0:
                break
            parsed_size += frame_size
        fh.seek(end_pos)

    def _parse_id3v1(self, fh: BinaryIO) -> None:
        content = fh.read(3 + 30 + 30 + 30 + 4 + 30 + 1)
        if content[:3] != b'TAG':  # check if this is an ID3 v1 tag
            return

        def asciidecode(x: bytes) -> str:
            return self._unpad(
                x.decode(self._default_encoding or 'latin1', 'replace'))
        # Only set fields that were not set by ID3v2 tags, as ID3v1
        # tags are more likely to be outdated or have encoding issues
        if not self.title:
            value = asciidecode(content[3:33])
            if value:
                self._set_field('title', value)
        if not self.artist:
            value = asciidecode(content[33:63])
            if value:
                self._set_field('artist', value)
        if not self.album:
            value = asciidecode(content[63:93])
            if value:
                self._set_field('album', value)
        if not self.year:
            value = asciidecode(content[93:97])
            if value:
                self._set_field('year', value)
        comment = content[97:127]
        if b'\x00\x00' < comment[-2:] < b'\x01\x00':
            if self.track is None:
                self._set_field('track', ord(comment[-1:]))
            comment = comment[:-2]
        if not self.comment:
            value = asciidecode(comment)
            if value:
                self._set_field('comment', value)
        if not self.genre:
            genre_id = ord(content[127:128])
            if genre_id < len(self._ID3V1_GENRES):
                self._set_field('genre', self._ID3V1_GENRES[genre_id])

    def __parse_custom_field(self, content: str) -> bool:
        custom_field_name, separator, value = content.partition('\x00')
        custom_field_name_lower = custom_field_name.lower()
        value = value.lstrip('\ufeff')
        if custom_field_name_lower and separator and value:
            field_name = self._ID3_MAPPING_CUSTOM.get(
                custom_field_name_lower,
                self._OTHER_PREFIX + custom_field_name_lower)
            self._set_field(field_name, value)
            return True
        return False

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
        image = Image(name, data)
        if mime_type:
            image.mime_type = mime_type
        if description:
            image.description = description
        return field_name, image

    def _parse_frame(self,
                     fh: BinaryIO,
                     total_size: int,
                     id3version: int | None = None) -> int:
        # ID3v2.2 especially ugly. see: http://id3.org/id3v2-00
        header_len = 6 if id3version == 2 else 10
        frame_size_bytes = 3 if id3version == 2 else 4
        is_synchsafe_int = id3version == 4
        header = fh.read(header_len)
        if len(header) != header_len:
            return 0
        frame_id = self._decode_string(header[:frame_size_bytes])
        frame_size: int
        if frame_size_bytes == 3:
            frame_size = unpack('>I', b'\x00' + header[3:6])[0]
        elif is_synchsafe_int:
            frame_size = self._unsynchsafe(unpack('4B', header[4:8]))
        else:
            frame_size = unpack('>I', header[4:8])[0]
        if _DEBUG:
            print(f'Found id3 Frame {frame_id} at '
                  f'{fh.tell()}-{fh.tell() + frame_size} of {self.filesize}')
        if frame_size > total_size:
            # invalid frame size, stop here
            return 0
        should_set_field = True
        if frame_id in self._ID3_MAPPING:
            if not self._parse_tags:
                return frame_size
            fieldname = self._ID3_MAPPING[frame_id]
            language = fieldname in {'comment', 'other.lyrics'}
            value = self._decode_string(fh.read(frame_size), language)
            if not value:
                return frame_size
            if fieldname == "comment":
                # check if comment is a key-value pair (used by iTunes)
                should_set_field = not self.__parse_custom_field(value)
            elif fieldname in {'track', 'disc'}:
                if '/' in value:
                    value, total = value.split('/')[:2]
                    if total.isdecimal():
                        self._set_field(f'{fieldname}_total', int(total))
                if value.isdecimal():
                    self._set_field(fieldname, int(value))
                should_set_field = False
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
            if should_set_field:
                self._set_field(fieldname, value)
        elif frame_id in self._CUSTOM_FRAME_IDS:
            # custom fields
            if self._parse_tags:
                value = self._decode_string(fh.read(frame_size))
                if value:
                    self.__parse_custom_field(value)
        elif frame_id in self._IMAGE_FRAME_IDS:
            if self._load_image:
                # See section 4.14: http://id3.org/id3v2.4.0-frames
                content = fh.read(frame_size)
                encoding = content[:1]
                if frame_id == 'PIC':  # ID3 v2.2:
                    imgformat = self._decode_string(content[1:4]).lower()
                    mime_type = self._ID3V2_2_IMAGE_FORMATS.get(imgformat)
                    # skip encoding (1), imgformat (3), pictype(1)
                    desc_start_pos = 5
                else:  # ID3 v2.3+
                    mime_end_pos = content.index(b'\x00', 1)
                    mime_type = self._decode_string(
                        content[1:mime_end_pos]).lower()
                    # skip mtype, pictype(1)
                    desc_start_pos = mime_end_pos + 2
                pic_type = content[desc_start_pos - 1]
                # latin1 and utf-8 are 1 byte
                if encoding in {b'\x00', b'\x03'}:
                    desc_end_pos = content.find(b'\x00', desc_start_pos) + 1
                else:
                    desc_end_pos = 0
                    for i in range(desc_start_pos, len(content), 2):
                        if content[i:i + 2] == b'\x00\x00':
                            desc_end_pos = i + 2
                            break
                    # skip stray null byte in broken file
                    if (desc_end_pos + 1 < len(content)
                            and content[desc_end_pos] == 0
                            and content[desc_end_pos + 1] != 0):
                        desc_end_pos += 1
                desc = self._decode_string(
                    encoding + content[desc_start_pos:desc_end_pos])
                field_name, image = self._create_tag_image(
                    content[desc_end_pos:], pic_type, mime_type, desc)
                # pylint: disable=protected-access
                self.images._set_field(field_name, image)
        elif frame_id not in self._IGNORED_FRAME_IDS:
            # unknown, try to add to other dict
            if self._parse_tags:
                value = self._decode_string(fh.read(frame_size))
                if value:
                    self._set_field(
                        self._OTHER_PREFIX + frame_id.lower(), value)
        else:  # skip frame
            fh.seek(frame_size, SEEK_CUR)
        return frame_size

    def _decode_string(self, value: bytes, language: bool = False) -> str:
        default_encoding = 'ISO-8859-1'
        if self._default_encoding:
            default_encoding = self._default_encoding
        # it's not my fault, this is the spec.
        first_byte = value[:1]
        if first_byte == b'\x00':  # ISO-8859-1
            value = value[1:]
            encoding = default_encoding
        elif first_byte == b'\x01':  # UTF-16 with BOM
            value = value[1:]
            # remove language (but leave BOM)
            if language:
                if value[3:5] in {b'\xfe\xff', b'\xff\xfe'}:
                    value = value[3:]
                if value[:3].isalpha():
                    value = value[3:]  # remove language
                # strip optional additional null bytes
                value = value.lstrip(b'\x00')
            # read byte order mark to determine endianness
            encoding = ('UTF-16be' if value.startswith(b'\xfe\xff')
                        else 'UTF-16le')
            # strip the bom if it exists
            if value.startswith(b'\xfe\xff') or value.startswith(b'\xff\xfe'):
                value = value[2:] if len(value) % 2 == 0 else value[2:-1]
            # remove ADDITIONAL OTHER BOM :facepalm:
            if value.startswith(b'\x00\x00\xff\xfe'):
                value = value[4:]
        elif first_byte == b'\x02':  # UTF-16 without BOM
            # strip optional null byte, if byte count uneven
            value = value[1:-1] if len(value) % 2 == 0 else value[1:]
            encoding = 'UTF-16be'
        elif first_byte == b'\x03':  # UTF-8
            value = value[1:]
            encoding = 'UTF-8'
        else:
            encoding = default_encoding  # wild guess
        if language and value[:3].isalpha():
            value = value[3:]  # remove language
        return self._unpad(value.decode(encoding, 'replace'))

    @staticmethod
    def _unsynchsafe(ints: tuple[int, ...]) -> int:
        return (ints[0] << 21) + (ints[1] << 14) + (ints[2] << 7) + ints[3]


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
    }

    def __init__(self) -> None:
        super().__init__()
        self._granule_pos = 0
        self._pre_skip = 0  # number of samples to skip in opus stream
        self._audio_size: int | None = None  # size of opus audio stream

    def _determine_duration(self, fh: BinaryIO) -> None:
        if not self._tags_parsed:
            self._parse_tag(fh)  # determine sample rate
        if self.duration is not None or not self.samplerate:
            return  # either ogg flac or invalid file
        self.duration = max(
            (self._granule_pos - self._pre_skip) / self.samplerate, 0
        )
        if self._audio_size is None or not self.duration:
            return  # not an opus file
        self.bitrate = self._audio_size * 8 / self.duration / 1000

    def _parse_tag(self, fh: BinaryIO) -> None:
        check_flac_second_packet = False
        check_speex_second_packet = False
        for packet in self._parse_pages(fh):
            if packet.startswith(b"\x01vorbis"):
                if self._parse_duration:
                    self.channels, self.samplerate = unpack(
                        "<Bi", packet[11:16])
                    self.bitrate = unpack("<i", packet[20:24])[0] / 1000
            elif packet.startswith(b"\x03vorbis"):
                if self._parse_tags:
                    walker = BytesIO(packet)
                    walker.seek(7)  # jump over header name
                    self._parse_vorbis_comment(walker)
            elif packet.startswith(b'OpusHead'):
                if self._parse_duration:  # parse opus header
                    # https://www.videolan.org/developers/vlc/modules/codec/opus_header.c
                    # https://mf4.xiph.org/jenkins/view/opus/job/opusfile-unix/ws/doc/html/structOpusHead.html
                    version, ch, pre_skip = unpack("<BBH", packet[8:12])
                    if (version & 0xF0) == 0:  # only major version 0 supported
                        self.channels = ch
                        self.samplerate = 48000
                        self._pre_skip = pre_skip
            elif packet.startswith(b'OpusTags'):
                if self._parse_tags:  # parse opus metadata:
                    walker = BytesIO(packet)
                    walker.seek(8)  # jump over header name
                    self._parse_vorbis_comment(walker)
                self._audio_size = 0  # start counting size of audio stream
            elif packet.startswith(b'\x7fFLAC'):
                # https://xiph.org/flac/ogg_mapping.html
                walker = BytesIO(packet)
                # jump over header name, version and number of headers
                walker.seek(9)
                # pylint: disable=protected-access
                flactag = _Flac()
                flactag._filehandler = walker
                flactag.filesize = self.filesize
                flactag._load(
                    tags=self._parse_tags, duration=self._parse_duration,
                    image=self._load_image)
                self._update(flactag)
                check_flac_second_packet = True
            elif check_flac_second_packet:
                # second packet contains FLAC metadata block
                if self._parse_tags:
                    walker = BytesIO(packet)
                    meta_header = walker.read(4)
                    block_type = meta_header[0] & 0x7f
                    # pylint: disable=protected-access
                    if block_type == _Flac._VORBIS_COMMENT:
                        self._parse_vorbis_comment(walker)
                check_flac_second_packet = False
            elif packet.startswith(b'Speex   '):
                # https://speex.org/docs/manual/speex-manual/node8.html
                if self._parse_duration:
                    self.samplerate = unpack("<i", packet[36:40])[0]
                    self.channels, self.bitrate = unpack("<ii", packet[48:56])
                check_speex_second_packet = True
            elif check_speex_second_packet:
                if self._parse_tags:
                    walker = BytesIO(packet)
                    # starts with a comment string
                    length = unpack('I', walker.read(4))[0]
                    comment = walker.read(length).decode('utf-8', 'replace')
                    self._set_field('comment', comment)
                    # other tags
                    self._parse_vorbis_comment(walker, has_vendor=False)
                check_speex_second_packet = False
            else:
                # Optimization: If we need to determine the duration, read
                # granule_pos of remaining pages, but skip contents of
                # segments. If we don't need the duration, stop here.
                self._tags_parsed = True
                if not self._parse_duration:
                    return
        self._tags_parsed = True

    def _parse_vorbis_comment(self,
                              fh: BinaryIO,
                              has_vendor: bool = True) -> None:
        # for the spec, see: http://xiph.org/vorbis/doc/v-comment.html
        # discnumber tag based on: https://en.wikipedia.org/wiki/Vorbis_comment
        # https://sno.phy.queensu.ca/~phil/exiftool/TagNames/Vorbis.html
        if has_vendor:
            vendor_length = unpack('I', fh.read(4))[0]
            fh.seek(vendor_length, SEEK_CUR)  # jump over vendor
        elements = unpack('I', fh.read(4))[0]
        for _i in range(elements):
            length = unpack('I', fh.read(4))[0]
            keyvalpair = fh.read(length).decode('utf-8', 'replace')
            if '=' in keyvalpair:
                key, value = keyvalpair.split('=', 1)
                key_lower = key.lower()
                if key_lower == "metadata_block_picture":
                    if self._load_image:
                        if _DEBUG:
                            print('Found Vorbis Image', key, value[:64])
                        # pylint: disable=protected-access
                        fieldname, fieldvalue = _Flac._parse_image(
                            BytesIO(a2b_base64(value)))
                        self.images._set_field(fieldname, fieldvalue)
                else:
                    if _DEBUG:
                        print('Found Vorbis Comment', key, value[:64])
                    fieldname = self._VORBIS_MAPPING.get(
                        key_lower, self._OTHER_PREFIX + key_lower)
                    if fieldname in {
                        'track', 'disc', 'track_total', 'disc_total'
                    }:
                        if fieldname in {'track', 'disc'} and '/' in value:
                            value, total = value.split('/')[:2]
                            if total.isdecimal():
                                self._set_field(
                                    f'{fieldname}_total', int(total))
                        if value.isdecimal():
                            self._set_field(fieldname, int(value))
                    elif value:
                        self._set_field(fieldname, value)

    def _parse_pages(self, fh: BinaryIO) -> Iterator[bytearray]:
        # for the spec, see: https://wiki.xiph.org/Ogg
        packet_data = bytearray()
        current_serial = None
        last_granule_pos = 0
        last_audio_size = 0
        header_len = 27
        page_header = fh.read(header_len)  # read ogg page header
        while len(page_header) == header_len:
            version = page_header[4]
            if page_header[:4] != b'OggS' or version != 0:
                raise ParseError('Invalid OGG header')
            # https://xiph.org/ogg/doc/framing.html
            header_type = page_header[5]
            eos = header_type & 0x04
            granule_pos, serial = unpack('<qI', page_header[6:18])
            if current_serial is None:
                current_serial = serial
            serial_match = serial == current_serial
            if serial_match and granule_pos > 0:
                if eos:
                    self._granule_pos = granule_pos
                else:
                    self._granule_pos = last_granule_pos
                    last_granule_pos = granule_pos
            segments = page_header[26]
            seg_sizes = unpack('B' * segments, fh.read(segments))
            read_size = 0
            audio_size = 0
            for seg_size in seg_sizes:  # read all segments
                read_size += seg_size
                if self._audio_size is not None:
                    audio_size += seg_size
                # less than 255 bytes means end of packet
                if seg_size < 255 and serial_match and not self._tags_parsed:
                    packet_data += fh.read(read_size)
                    yield packet_data
                    packet_data.clear()
                    read_size = 0
            if read_size:
                if not serial_match or self._tags_parsed:
                    fh.seek(read_size, SEEK_CUR)
                else:  # packet continues on next page
                    packet_data += fh.read(read_size)
            if serial_match and self._audio_size is not None:
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

    def _determine_duration(self, fh: BinaryIO) -> None:
        if not self._tags_parsed:
            self._parse_tag(fh)

    def _parse_tag(self, fh: BinaryIO) -> None:
        # http://www-mmsp.ece.mcgill.ca/Documents/AudioFormats/WAVE/WAVE.html
        # https://en.wikipedia.org/wiki/WAV
        header = fh.read(12)
        if header[:4] != b'RIFF' or header[8:12] != b'WAVE':
            raise ParseError('Invalid WAV header')
        if self._parse_duration:
            self.bitdepth = 16  # assume 16bit depth (CD quality)
        header_len = 8
        chunk_header = fh.read(header_len)
        while len(chunk_header) == header_len:
            subchunk_id = chunk_header[:4]
            subchunk_size = unpack('I', chunk_header[4:])[0]
            # IFF chunks are padded to an even number of bytes
            subchunk_size += subchunk_size % 2
            if subchunk_id == b'fmt ' and self._parse_duration:
                chunk = fh.read(subchunk_size)
                _format_tag, channels, samplerate = unpack('<HHI', chunk[:8])
                bitdepth = unpack('<H', chunk[14:16])[0]
                if bitdepth == 0:
                    # Certain codecs (e.g. GSM 6.10) give us a bit depth of
                    # zero. Avoid division by zero when calculating duration.
                    bitdepth = 1
                self.bitrate = samplerate * channels * bitdepth / 1000
                self.channels, self.samplerate, self.bitdepth = (
                    channels, samplerate, bitdepth)
            elif subchunk_id == b'data' and self._parse_duration:
                if (self.channels is not None and self.samplerate is not None
                        and self.bitdepth is not None):
                    self.duration = (
                        subchunk_size / self.channels / self.samplerate
                        / (self.bitdepth / 8))
                fh.seek(subchunk_size, SEEK_CUR)
            elif subchunk_id == b'LIST' and self._parse_tags:
                chunk = fh.read(subchunk_size)
                if chunk.startswith(b'INFO'):
                    walker = BytesIO(chunk)
                    walker.seek(4)  # skip header
                    field = walker.read(4)
                    while len(field) == 4:
                        data_length = unpack('I', walker.read(4))[0]
                        # IFF chunks are padded to an even size
                        data_length += data_length % 2
                        # strip zero-byte
                        data = walker.read(data_length).split(b'\x00', 1)[0]
                        if field in self._RIFF_MAPPING:
                            fieldname = self._RIFF_MAPPING[field]
                            value = data.decode('utf-8', 'replace')
                            if fieldname == 'track':
                                if value.isdecimal():
                                    self._set_field(fieldname, int(value))
                            else:
                                self._set_field(fieldname, value)
                        field = walker.read(4)
            elif subchunk_id in {b'id3 ', b'ID3 '} and self._parse_tags:
                # pylint: disable=protected-access
                id3 = _ID3()
                id3._filehandler = fh
                id3._load(tags=True, duration=False, image=self._load_image)
                self._update(id3)
            else:  # some other chunk, just skip the data
                fh.seek(subchunk_size, SEEK_CUR)
            chunk_header = fh.read(header_len)
        self._tags_parsed = True


class _Flac(TinyTag):
    """FLAC Parser."""

    _STREAMINFO = 0
    _VORBIS_COMMENT = 4
    _PICTURE = 6

    def _determine_duration(self, fh: BinaryIO) -> None:
        if not self._tags_parsed:
            self._parse_tag(fh)

    def _parse_tag(self, fh: BinaryIO) -> None:
        id3 = None
        header = fh.read(4)
        if header.startswith(b'ID3'):  # parse ID3 header if it exists
            fh.seek(-4, SEEK_CUR)
            # pylint: disable=protected-access
            id3 = _ID3()
            id3._parse_tags = self._parse_tags
            id3._load_image = self._load_image
            id3._parse_id3v2(fh)
            header = fh.read(4)  # after ID3 should be fLaC
        if header[:4] != b'fLaC':
            raise ParseError('Invalid FLAC header')
        # for spec, see https://xiph.org/flac/ogg_mapping.html
        header_len = 4
        block_header = fh.read(header_len)
        while len(block_header) == header_len:
            block_type = block_header[0] & 0x7f
            is_last_block = block_header[0] & 0x80
            size = unpack('>I', b'\x00' + block_header[1:])[0]
            # http://xiph.org/flac/format.html#metadata_block_streaminfo
            if block_type == self._STREAMINFO and self._parse_duration:
                head = fh.read(size)
                if len(head) < 34:  # invalid streaminfo
                    break
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
                sr = unpack('>I', b'\x00' + head[10:13])[0] >> 4
                self.channels = ((head[12] >> 1) & 0x07) + 1
                self.bitdepth = (
                    ((head[12] & 1) << 4) + ((head[13] & 0xF0) >> 4) + 1)
                tot_samples_b = bytes([head[13] & 0x0F]) + head[14:18]
                tot_samples = unpack('>Q', b'\x00\x00\x00' + tot_samples_b)[0]
                self.duration = duration = tot_samples / sr
                self.samplerate = sr
                if duration > 0:
                    self.bitrate = self.filesize * 8 / duration / 1000
            elif block_type == self._VORBIS_COMMENT and self._parse_tags:
                # pylint: disable=protected-access
                walker = BytesIO(fh.read(size))
                oggtag = _Ogg()
                oggtag._parse_vorbis_comment(walker)
                self._update(oggtag)
            elif block_type == self._PICTURE and self._load_image:
                fieldname, value = self._parse_image(fh)
                # pylint: disable=protected-access
                self.images._set_field(fieldname, value)
            else:
                fh.seek(size, SEEK_CUR)  # seek over this block
            if is_last_block:
                break
            block_header = fh.read(header_len)
        if id3 is not None:  # apply ID3 tags after vorbis
            self._update(id3)
        self._tags_parsed = True

    @classmethod
    def _parse_image(cls, fh: BinaryIO) -> tuple[str, Image]:
        # https://xiph.org/flac/format.html#metadata_block_picture
        pic_type, mime_type_len = unpack('>II', fh.read(8))
        mime_type = fh.read(mime_type_len).decode('utf-8', 'replace')
        description_len = unpack('>I', fh.read(4))[0]
        description = fh.read(description_len).decode('utf-8', 'replace')
        fh.seek(16, SEEK_CUR)  # jump over width, height, depth, colors
        pic_len = unpack('>I', fh.read(4))[0]
        # pylint: disable=protected-access
        return _ID3._create_tag_image(
            fh.read(pic_len), pic_type, mime_type, description)


class _Wma(TinyTag):
    """WMA Parser.

    http://web.archive.org/web/20131203084402/http://msdn.microsoft.com/en-us/library/bb643323.aspx
    http://uguisu.skr.jp/Windows/format_asf.html
    """

    _ASF_MAPPING = {
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
    }
    _UNPACK_FORMATS = {
        1: '<B',
        2: '<H',
        4: '<I',
        8: '<Q'
    }
    _ASF_CONTENT_DESC = b'3&\xb2u\x8ef\xcf\x11\xa6\xd9\x00\xaa\x00b\xcel'
    _ASF_EXT_CONTENT_DESC = (b'@\xa4\xd0\xd2\x07\xe3\xd2\x11\x97\xf0\x00'
                             b'\xa0\xc9^\xa8P')
    _STREAM_BITRATE_PROPS = (b'\xceu\xf8{\x8dF\xd1\x11\x8d\x82\x00`\x97\xc9'
                             b'\xa2\xb2')
    _ASF_FILE_PROP = b'\xa1\xdc\xab\x8cG\xa9\xcf\x11\x8e\xe4\x00\xc0\x0c Se'
    _ASF_STREAM_PROPS = (b'\x91\x07\xdc\xb7\xb7\xa9\xcf\x11\x8e\xe6\x00\xc0'
                         b'\x0c Se')
    _STREAM_TYPE_ASF_AUDIO_MEDIA = b'@\x9ei\xf8M[\xcf\x11\xa8\xfd\x00\x80_\\D+'

    def _determine_duration(self, fh: BinaryIO) -> None:
        if not self._tags_parsed:
            self._parse_tag(fh)

    def _parse_tag(self, fh: BinaryIO) -> None:
        # http://www.garykessler.net/library/file_sigs.html
        # http://web.archive.org/web/20131203084402/http://msdn.microsoft.com/en-us/library/bb643323.aspx#_Toc521913958
        header = fh.read(30)
        if (header[:16] != b'0&\xb2u\x8ef\xcf\x11\xa6\xd9\x00\xaa\x00b\xcel'
                or header[-1:] != b'\x02'):
            raise ParseError('Invalid WMA header')
        header_len = 24
        object_header = fh.read(header_len)
        while len(object_header) == header_len:
            object_size = unpack('<Q', object_header[16:])[0]
            if object_size == 0 or object_size > self.filesize:
                break  # invalid object, stop parsing.
            object_id = object_header[:16]
            if object_id == self._ASF_CONTENT_DESC and self._parse_tags:
                walker = BytesIO(fh.read(object_size - header_len))
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
            elif object_id == self._ASF_EXT_CONTENT_DESC and self._parse_tags:
                # http://web.archive.org/web/20131203084402/http://msdn.microsoft.com/en-us/library/bb643323.aspx#_Toc509555195
                walker = BytesIO(fh.read(object_size - header_len))
                descriptor_count = unpack('<H', walker.read(2))[0]
                for _ in range(descriptor_count):
                    name_len = unpack('<H', walker.read(2))[0]
                    name = self._unpad(
                        walker.read(name_len).decode('utf-16', 'replace'))
                    value_type, value_len = unpack('<HH', walker.read(4))
                    # Unicode string
                    if value_type == 0:
                        value = self._unpad(
                            walker.read(value_len).decode('utf-16', 'replace'))
                    # DWORD / QWORD / WORD
                    elif (1 < value_type < 6
                            and value_len in self._UNPACK_FORMATS):
                        fmt = self._UNPACK_FORMATS[value_len]
                        value = str(unpack(fmt, walker.read(value_len))[0])
                    else:
                        walker.seek(value_len, SEEK_CUR)  # skip other values
                        continue
                    # try to get normalized field name
                    if name in self._ASF_MAPPING:
                        field_name = self._ASF_MAPPING[name]
                    else:  # custom field
                        if name.startswith('WM/'):
                            name = name[3:]
                        field_name = self._OTHER_PREFIX + name.lower()
                    if field_name in {'track', 'disc'}:
                        if isinstance(value, int) or value.isdecimal():
                            self._set_field(field_name, int(value))
                    elif value:
                        self._set_field(field_name, value)
            elif object_id == self._ASF_FILE_PROP and self._parse_duration:
                data = fh.read(object_size - header_len)
                play_duration = unpack('<Q', data[40:48])[0] / 10000000
                preroll = unpack('<Q', data[56:64])[0] / 1000
                # subtract the preroll to get the actual duration
                self.duration = max(play_duration - preroll, 0.0)
            elif object_id == self._ASF_STREAM_PROPS and self._parse_duration:
                data = fh.read(object_size - header_len)
                stream_type = data[:16]
                if stream_type == self._STREAM_TYPE_ASF_AUDIO_MEDIA:
                    (codec_id_format_tag, self.channels, self.samplerate,
                     avg_bytes_per_second) = unpack('<HHII', data[54:66])
                    self.bitrate = avg_bytes_per_second * 8 / 1000
                    if codec_id_format_tag == 355:  # lossless
                        self.bitdepth = unpack('<H', data[68:70])[0]
            else:
                # skip unknown object ids
                fh.seek(object_size - header_len, SEEK_CUR)
            object_header = fh.read(header_len)
        self._tags_parsed = True


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

    def _parse_tag(self, fh: BinaryIO) -> None:
        header = fh.read(12)
        if header[:4] != b'FORM' or header[8:12] not in {b'AIFC', b'AIFF'}:
            raise ParseError('Invalid AIFF header')
        header_len = 8
        chunk_header = fh.read(header_len)
        while len(chunk_header) == header_len:
            subchunk_id = chunk_header[:4]
            subchunk_size = unpack('>I', chunk_header[4:])[0]
            # IFF chunks are padded to an even number of bytes
            subchunk_size += subchunk_size % 2
            if subchunk_id in self._AIFF_MAPPING and self._parse_tags:
                value = self._unpad(
                    fh.read(subchunk_size).decode('utf-8', 'replace'))
                self._set_field(self._AIFF_MAPPING[subchunk_id], value)
            elif subchunk_id == b'COMM' and self._parse_duration:
                chunk = fh.read(subchunk_size)
                channels, num_frames, bitdepth = unpack('>hLh', chunk[:8])
                self.channels, self.bitdepth = channels, bitdepth
                try:
                    # Extended precision
                    exp, mantissa = unpack('>HQ', chunk[8:18])
                    sr = int(mantissa * (2 ** (exp - 0x3FFF - 63)))
                    duration = num_frames / sr
                    bitrate = sr * channels * bitdepth / 1000
                    self.samplerate, self.duration, self.bitrate = (
                        sr, duration, bitrate)
                except OverflowError:
                    pass
            elif subchunk_id in {b'id3 ', b'ID3 '} and self._parse_tags:
                # pylint: disable=protected-access
                id3 = _ID3()
                id3._filehandler = fh
                id3._load(tags=True, duration=False, image=self._load_image)
                self._update(id3)
            else:  # some other chunk, just skip the data
                fh.seek(subchunk_size, SEEK_CUR)
            chunk_header = fh.read(header_len)
        self._tags_parsed = True

    def _determine_duration(self, fh: BinaryIO) -> None:
        if not self._tags_parsed:
            self._parse_tag(fh)
