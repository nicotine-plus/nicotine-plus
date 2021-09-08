# tinytag - an audio meta info reader
# Copyright (c) 2014-2018 Tom Wallroth
#
# Sources on github:
# https://github.com/devsnd/tinytag/

# MIT License
#
# Copyright (c) 2020-2021 Nicotine+ Team
# Copyright (c) 2014-2019 Tom Wallroth
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.


import aifc
import codecs
import io
import operator
import os
import re
import struct
import sys

from chunk import Chunk
from collections import defaultdict
from collections.abc import MutableMapping
from functools import reduce
from io import BytesIO

DEBUG = os.environ.get('DEBUG', False)  # some of the parsers can print debug info


class TinyTagException(LookupError):  # inherit LookupError for backwards compat
    pass


def _read(fh, nbytes):  # helper function to check if we haven't reached EOF
    b = fh.read(nbytes)
    if len(b) < nbytes:
        raise TinyTagException('Unexpected end of file')
    return b


def stderr(*args):
    sys.stderr.write('%s\n' % ' '.join(repr(arg) for arg in args))
    sys.stderr.flush()


def _bytes_to_int_le(b):
    fmt = {1: '<B', 2: '<H', 4: '<I', 8: '<Q'}.get(len(b))
    return struct.unpack(fmt, b)[0] if fmt is not None else 0


def _bytes_to_int(b):
    return reduce(lambda accu, elem: (accu << 8) + elem, b, 0)


class TinyTag(object):
    def __init__(self, filehandler=None, filesize=0, ignore_errors=False):
        # This is required for compatibility between python2 and python3
        # in python2 there is a difference between `str` and `unicode`
        # whereas in python3 everything every string is `unicode` by default and
        # the type `unicode` is deprecated
        if type(filehandler).__name__ in ('str', 'unicode'):
            raise Exception('Use `TinyTag.get(filepath)` instead of `TinyTag(filepath)`')
        self._filehandler = filehandler
        self.filesize = filesize
        self.album = None
        self.albumartist = None
        self.artist = None
        self.audio_offset = None
        self.bitrate = None
        self.channels = None
        self.comment = None
        self.composer = None
        self.disc = None
        self.disc_total = None
        self.duration = None
        self.extra = defaultdict(lambda: None)
        self.genre = None
        self.samplerate = None
        self.title = None
        self.track = None
        self.track_total = None
        self.year = None
        self._load_image = False
        self._image_data = None
        self._ignore_errors = ignore_errors
        self._mapping = None

    def get_image(self):
        return self._image_data

    def get(self, filename, size, tags=True, duration=True, image=False, ignore_errors=False):
        parser_class = None
        if self._mapping is None:
            self._mapping = {
                ('.mp3',): ID3,
                ('.oga', '.ogg', '.opus'): Ogg,
                ('.wav',): Wave,
                ('.flac',): Flac,
                ('.wma',): Wma,
                ('.m4b', '.m4a', '.mp4'): MP4,
                ('.aiff', '.aifc', '.aif', '.afc'): Aiff,
            }
        for ext, tagclass in self._mapping.items():
            if filename.lower().endswith(ext):
                parser_class = tagclass
        if parser_class is None:
            return None
        with io.open(filename, 'rb') as af:
            tag = parser_class(af, size, ignore_errors=ignore_errors)
            tag.load(tags=tags, duration=duration, image=image)
            tag.extra = dict(tag.extra)  # turn default dict into dict so that it can throw KeyError
            return tag

    def __repr__(self):
        return str(self)

    def load(self, tags, duration, image=False):
        self._load_image = image
        if tags:
            self._parse_tag(self._filehandler)
        if duration:
            if tags:  # rewind file if the tags were already parsed
                self._filehandler.seek(0)
            self._determine_duration(self._filehandler)

    def _set_field(self, fieldname, bytestring, transfunc=None):
        """convienience function to set fields of the tinytag by name.
        the payload (bytestring) can be changed using the transfunc"""
        write_dest = self  # write into the TinyTag by default
        get_func = getattr
        set_func = setattr
        is_extra = fieldname.startswith('extra.')  # but if it's marked as extra field
        if is_extra:
            fieldname = fieldname[6:]
            write_dest = self.extra  # write into the extra field instead
            get_func = operator.getitem
            set_func = operator.setitem
        if get_func(write_dest, fieldname):  # do not overwrite existing data
            return
        value = bytestring if transfunc is None else transfunc(bytestring)
        if DEBUG:
            stderr('Setting field "%s" to "%s"' % (fieldname, value))
        if fieldname == 'genre':
            genre_id = 255
            if value.isdigit():  # funky: id3v1 genre hidden in a id3v2 field
                genre_id = int(value)
            else:  # funkier: the TCO may contain genres in parens, e.g. '(13)'
                genre_in_parens = re.match('^\\((\\d+)\\)$', value)
                if genre_in_parens:
                    genre_id = int(genre_in_parens.group(1))
            if 0 <= genre_id < len(ID3.ID3V1_GENRES):
                value = ID3.ID3V1_GENRES[genre_id]
        if fieldname in ("track", "disc"):
            if type(value).__name__ in ('str', 'unicode') and '/' in value:
                current, total = value.split('/')[:2]
                set_func(write_dest, "%s_total" % fieldname, total)
            else:
                # Converting 'track', 'disk' to string for type consistency.
                current = str(value) if isinstance(value, int) else value
            set_func(write_dest, fieldname, current)
        elif fieldname in ("track_total", "disc_total") and isinstance(value, int):
            # Converting to string 'track_total', 'disc_total' for type consistency.
            set_func(write_dest, fieldname, str(value))
        else:
            set_func(write_dest, fieldname, value)

    def _determine_duration(self, fh):
        raise NotImplementedError()

    def _parse_tag(self, fh):
        raise NotImplementedError()

    def update(self, other):
        # update the values of this tag with the values from another tag
        for key in ['track', 'track_total', 'title', 'artist',
                    'album', 'albumartist', 'year', 'duration',
                    'genre', 'disc', 'disc_total', 'comment', 'composer']:
            if not getattr(self, key) and getattr(other, key):
                setattr(self, key, getattr(other, key))

    @staticmethod
    def _unpad(s):
        # strings in mp3 and asf *may* be terminated with a zero byte at the end
        return s.replace('\x00', '')


class MP4(TinyTag):
    # see: https://developer.apple.com/library/mac/documentation/QuickTime/QTFF/Metadata/Metadata.html
    # and: https://developer.apple.com/library/mac/documentation/QuickTime/QTFF/QTFFChap2/qtff2.html

    class Parser:
        # https://developer.apple.com/library/mac/documentation/QuickTime/QTFF/Metadata/Metadata.html#//apple_ref/doc/uid/TP40000939-CH1-SW34
        ATOM_DECODER_BY_TYPE = {
            0: lambda x: x,  # 'reserved',
            1: lambda x: codecs.decode(x, 'utf-8', 'replace'),   # UTF-8
            2: lambda x: codecs.decode(x, 'utf-16', 'replace'),  # UTF-16
            3: lambda x: codecs.decode(x, 's/jis', 'replace'),   # S/JIS
            # 16: duration in millis
            13: lambda x: x,  # JPEG
            14: lambda x: x,  # PNG
            21: lambda x: struct.unpack('>b', x)[0],  # BE Signed int
            22: lambda x: struct.unpack('>B', x)[0],  # BE Unsigned int
            23: lambda x: struct.unpack('>f', x)[0],  # BE Float32
            24: lambda x: struct.unpack('>d', x)[0],  # BE Float64
            # 27: lambda x: x,  # BMP
            # 28: lambda x: x,  # QuickTime Metadata atom
            65: lambda x: struct.unpack('b', x)[0],   # 8-bit Signed int
            66: lambda x: struct.unpack('>h', x)[0],  # BE 16-bit Signed int
            67: lambda x: struct.unpack('>i', x)[0],  # BE 32-bit Signed int
            74: lambda x: struct.unpack('>q', x)[0],  # BE 64-bit Signed int
            75: lambda x: struct.unpack('B', x)[0],   # 8-bit Unsigned int
            76: lambda x: struct.unpack('>H', x)[0],  # BE 16-bit Unsigned int
            77: lambda x: struct.unpack('>I', x)[0],  # BE 32-bit Unsigned int
            78: lambda x: struct.unpack('>Q', x)[0],  # BE 64-bit Unsigned int
        }

        @classmethod
        def make_data_atom_parser(cls, fieldname):
            def parse_data_atom(data_atom):
                data_type = struct.unpack('>I', data_atom[:4])[0]
                conversion = cls.ATOM_DECODER_BY_TYPE.get(data_type)
                if conversion is None:
                    stderr('Cannot convert data type: %s' % data_type)
                    return {}  # don't know how to convert data atom
                # skip header & null-bytes, convert rest
                return {fieldname: conversion(data_atom[8:])}
            return parse_data_atom

        @classmethod
        def make_number_parser(cls, fieldname1, fieldname2):
            def _(data_atom):
                number_data = data_atom[8:14]
                numbers = struct.unpack('>HHH', number_data)
                # for some reason the first number is always irrelevant.
                return {fieldname1: numbers[1], fieldname2: numbers[2]}
            return _

        @classmethod
        def parse_id3v1_genre(cls, data_atom):
            # dunno why the genre is offset by -1 but that's how mutagen does it
            idx = struct.unpack('>H', data_atom[8:])[0] - 1
            if idx < len(ID3.ID3V1_GENRES):
                return {'genre': ID3.ID3V1_GENRES[idx]}
            return {'genre': None}

        @classmethod
        def parse_audio_sample_entry(cls, data):
            # this atom also contains the esds atom:
            # https://ffmpeg.org/doxygen/0.6/mov_8c-source.html
            # http://xhelmboyx.tripod.com/formats/mp4-layout.txt
            datafh = BytesIO(data)
            datafh.seek(16, os.SEEK_CUR)  # jump over version and flags
            channels = struct.unpack('>H', datafh.read(2))[0]
            datafh.seek(2, os.SEEK_CUR)   # jump over bit_depth
            datafh.seek(2, os.SEEK_CUR)   # jump over QT compr id & pkt size
            sr = struct.unpack('>I', datafh.read(4))[0]
            esds_atom_size = struct.unpack('>I', data[28:32])[0]
            esds_atom = BytesIO(data[36:36 + esds_atom_size])
            # http://sasperger.tistory.com/103
            esds_atom.seek(22, os.SEEK_CUR)  # jump over most data...
            esds_atom.seek(4, os.SEEK_CUR)   # jump over max bitrate
            avg_br = struct.unpack('>I', esds_atom.read(4))[0] / 1000.0  # kbit/s
            return {'channels': channels, 'samplerate': sr, 'bitrate': avg_br}

        @classmethod
        def parse_mvhd(cls, data):
            # http://stackoverflow.com/a/3639993/1191373
            walker = BytesIO(data)
            version = struct.unpack('b', walker.read(1))[0]
            walker.seek(3, os.SEEK_CUR)  # jump over flags
            if version == 0:  # uses 32 bit integers for timestamps
                walker.seek(8, os.SEEK_CUR)  # jump over create & mod times
                time_scale = struct.unpack('>I', walker.read(4))[0]
                duration = struct.unpack('>I', walker.read(4))[0]
            else:  # version == 1:  # uses 64 bit integers for timestamps
                walker.seek(16, os.SEEK_CUR)  # jump over create & mod times
                time_scale = struct.unpack('>I', walker.read(4))[0]
                duration = struct.unpack('>q', walker.read(8))[0]
            return {'duration': float(duration) / time_scale}

        @classmethod
        def debug_atom(cls, data):
            stderr(data)  # use this function to inspect atoms in an atom tree
            return {}

    # The parser tree: Each key is an atom name which is traversed if existing.
    # Leaves of the parser tree are callables which receive the atom data.
    # callables return {fieldname: value} which is updates the TinyTag.
    META_DATA_TREE = {b'moov': {b'udta': {b'meta': {b'ilst': {
        # see: http://atomicparsley.sourceforge.net/mpeg-4files.html
        b'\xa9alb': {b'data': Parser.make_data_atom_parser('album')},
        b'\xa9ART': {b'data': Parser.make_data_atom_parser('artist')},
        b'aART': {b'data': Parser.make_data_atom_parser('albumartist')},
        # b'cpil': {b'data': Parser.make_data_atom_parser('compilation')},
        b'\xa9cmt': {b'data': Parser.make_data_atom_parser('comment')},
        b'disk': {b'data': Parser.make_number_parser('disc', 'disc_total')},
        b'\xa9wrt': {b'data': Parser.make_data_atom_parser('composer')},
        b'\xa9day': {b'data': Parser.make_data_atom_parser('year')},
        b'\xa9gen': {b'data': Parser.make_data_atom_parser('genre')},
        b'gnre': {b'data': Parser.parse_id3v1_genre},
        b'\xa9nam': {b'data': Parser.make_data_atom_parser('title')},
        b'trkn': {b'data': Parser.make_number_parser('track', 'track_total')},
    }}}}}

    # see: https://developer.apple.com/library/mac/documentation/QuickTime/QTFF/QTFFChap3/qtff3.html
    AUDIO_DATA_TREE = {
        b'moov': {
            b'mvhd': Parser.parse_mvhd,
            b'trak': {b'mdia': {b"minf": {b"stbl": {b"stsd": {b'mp4a': Parser.parse_audio_sample_entry}}}}}
        }
    }

    IMAGE_DATA_TREE = {b'moov': {b'udta': {b'meta': {b'ilst': {
        b'covr': {b'data': Parser.make_data_atom_parser('_image_data')},
    }}}}}

    VERSIONED_ATOMS = {b'meta', b'stsd'}  # those have an extra 4 byte header
    FLAGGED_ATOMS = {b'stsd'}  # these also have an extra 4 byte header

    def _determine_duration(self, fh):
        self._traverse_atoms(fh, path=self.AUDIO_DATA_TREE)

    def _parse_tag(self, fh):
        self._traverse_atoms(fh, path=self.META_DATA_TREE)
        if self._load_image:           # A bit inefficient, we rewind the file
            self._filehandler.seek(0)  # to parse it again for the image
            self._traverse_atoms(fh, path=self.IMAGE_DATA_TREE)

    def _traverse_atoms(self, fh, path, stop_pos=None, curr_path=None):
        header_size = 8
        atom_header = fh.read(header_size)
        while len(atom_header) == header_size:
            atom_size = struct.unpack('>I', atom_header[:4])[0] - header_size
            atom_type = atom_header[4:]
            if curr_path is None:  # keep track how we traversed in the tree
                curr_path = [atom_type]
            if atom_size <= 0:  # empty atom, jump to next one
                atom_header = fh.read(header_size)
                continue
            if DEBUG:
                stderr('%s pos: %d atom: %s len: %d' %
                       (' ' * 4 * len(curr_path), fh.tell() - header_size, atom_type, atom_size + header_size))
            if atom_type in self.VERSIONED_ATOMS:  # jump atom version for now
                fh.seek(4, os.SEEK_CUR)
            if atom_type in self.FLAGGED_ATOMS:  # jump atom flags for now
                fh.seek(4, os.SEEK_CUR)
            sub_path = path.get(atom_type, None)
            # if the path leaf is a dict, traverse deeper into the tree:
            if issubclass(type(sub_path), MutableMapping):
                atom_end_pos = fh.tell() + atom_size
                self._traverse_atoms(fh, path=sub_path, stop_pos=atom_end_pos,
                                     curr_path=curr_path + [atom_type])
            # if the path-leaf is a callable, call it on the atom data
            elif callable(sub_path):
                for fieldname, value in sub_path(fh.read(atom_size)).items():
                    if DEBUG:
                        stderr(' ' * 4 * len(curr_path), 'FIELD: ', fieldname)
                    if fieldname:
                        self._set_field(fieldname, value)
            # if no action was specified using dict or callable, jump over atom
            else:
                fh.seek(atom_size, os.SEEK_CUR)
            # check if we have reached the end of this branch:
            if stop_pos and fh.tell() >= stop_pos:
                return  # return to parent (next parent node in tree)
            atom_header = fh.read(header_size)  # read next atom


class ID3(TinyTag):
    FRAME_ID_TO_FIELD = {  # Mapping from Frame ID to a field of the TinyTag
        'COMM': 'comment', 'COM': 'comment',
        'TRCK': 'track', 'TRK': 'track',
        'TYER': 'year', 'TYE': 'year',
        'TALB': 'album', 'TAL': 'album',
        'TPE1': 'artist', 'TP1': 'artist',
        'TIT2': 'title', 'TT2': 'title',
        'TCON': 'genre', 'TCO': 'genre',
        'TPOS': 'disc',
        'TPE2': 'albumartist', 'TCOM': 'composer',
        'WXXX': 'extra.url',
        'TSRC': 'extra.isrc',
        'TXXX': 'extra.text',
        'TKEY': 'extra.initial_key',
        'USLT': 'extra.lyrics',
    }
    IMAGE_FRAME_IDS = {'APIC', 'PIC'}
    PARSABLE_FRAME_IDS = set(FRAME_ID_TO_FIELD.keys()).union(IMAGE_FRAME_IDS)
    _MAX_ESTIMATION_SEC = 30
    _CBR_DETECTION_FRAME_COUNT = 5
    _USE_XING_HEADER = True  # much faster, but can be deactivated for testing

    ID3V1_GENRES = [
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
        'Big Band', 'Chorus', 'Easy Listening', 'Acoustic', 'Humour', 'Speech',
        'Chanson', 'Opera', 'Chamber Music', 'Sonata', 'Symphony', 'Booty Bass',
        'Primus', 'Porn Groove', 'Satire', 'Slow Jam', 'Club', 'Tango', 'Samba',
        'Folklore', 'Ballad', 'Power Ballad', 'Rhythmic Soul', 'Freestyle',
        'Duet', 'Punk Rock', 'Drum Solo', 'A capella', 'Euro-House',
        'Dance Hall', 'Goa', 'Drum & Bass',

        # according to https://de.wikipedia.org/wiki/Liste_der_ID3v1-Genres:
        'Club-House', 'Hardcore Techno', 'Terror', 'Indie', 'BritPop',
        '',  # don't use ethnic slur ("Negerpunk", WTF!)
        'Polsk Punk', 'Beat', 'Christian Gangsta Rap', 'Heavy Metal',
        'Black Metal', 'Contemporary Christian', 'Christian Rock',
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
        'Podcast', 'Indie Rock', 'G-Funk', 'Dubstep', 'Garage Rock', 'Psybient',
    ]

    def __init__(self, filehandler, filesize, *args, **kwargs):
        TinyTag.__init__(self, filehandler, filesize, *args, **kwargs)
        # save position after the ID3 tag for duration mesurement speedup
        self._bytepos_after_id3v2 = None

    @classmethod
    def set_estimation_precision(cls, estimation_in_seconds):
        cls._MAX_ESTIMATION_SEC = estimation_in_seconds

    # see this page for the magic values used in mp3:
    # http://www.mpgedit.org/mpgedit/mpeg_format/mpeghdr.htm
    samplerates = [
        [11025, 12000, 8000],   # MPEG 2.5
        [],                     # reserved
        [22050, 24000, 16000],  # MPEG 2
        [44100, 48000, 32000],  # MPEG 1
    ]
    v1l1 = [0, 32, 64, 96, 128, 160, 192, 224, 256, 288, 320, 352, 384, 416, 448, 0]
    v1l2 = [0, 32, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320, 384, 0]
    v1l3 = [0, 32, 40, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320, 0]
    v2l1 = [0, 32, 48, 56, 64, 80, 96, 112, 128, 144, 160, 176, 192, 224, 256, 0]
    v2l2 = [0, 8, 16, 24, 32, 40, 48, 56, 64, 80, 96, 112, 128, 144, 160, 0]
    v2l3 = v2l2
    bitrate_by_version_by_layer = [
        [None, v2l3, v2l2, v2l1],  # MPEG Version 2.5  # note that the layers go
        None,                      # reserved          # from 3 to 1 by design.
        [None, v2l3, v2l2, v2l1],  # MPEG Version 2    # the first layer id is
        [None, v1l3, v1l2, v1l1],  # MPEG Version 1    # reserved
    ]
    samples_per_frame = 1152  # the default frame size for mp3
    channels_per_channel_mode = [
        2,  # 00 Stereo
        2,  # 01 Joint stereo (Stereo)
        2,  # 10 Dual channel (2 mono channels)
        1,  # 11 Single channel (Mono)
    ]

    @staticmethod
    def _parse_xing_header(fh):
        # see: http://www.mp3-tech.org/programmer/sources/vbrheadersdk.zip
        fh.seek(4, os.SEEK_CUR)  # read over Xing header
        header_flags = struct.unpack('>i', fh.read(4))[0]
        frames = byte_count = toc = vbr_scale = None
        if header_flags & 1:  # FRAMES FLAG
            frames = struct.unpack('>i', fh.read(4))[0]
        if header_flags & 2:  # BYTES FLAG
            byte_count = struct.unpack('>i', fh.read(4))[0]
        if header_flags & 4:  # TOC FLAG
            toc = [struct.unpack('>i', fh.read(4))[0] for _ in range(100)]
        if header_flags & 8:  # VBR SCALE FLAG
            vbr_scale = struct.unpack('>i', fh.read(4))[0]
        return frames, byte_count, toc, vbr_scale

    def _determine_duration(self, fh):
        if self._bytepos_after_id3v2 is None:
            # tag reading was disabled, figure out the correct file position here
            header = self._get_id3v2_header(fh)
            if header:
                self._bytepos_after_id3v2 = self._calc_size(header[4:8], 7)
            else:
                self._bytepos_after_id3v2 = 0
        max_estimation_frames = (ID3._MAX_ESTIMATION_SEC * 44100) // ID3.samples_per_frame
        frame_size_accu = 0
        header_bytes = 4
        frames = 0  # count frames for determining mp3 duration
        bitrate_accu = 0    # add up bitrates to find average bitrate to detect
        last_bitrates = []  # CBR mp3s (multiple frames with same bitrates)
        # seek to first position after id3 tag (speedup for large header)
        fh.seek(self._bytepos_after_id3v2)
        while True:
            # reading through garbage until 11 '1' sync-bits are found
            b = fh.peek(4)
            if len(b) < 4:
                break  # EOF
            sync, conf, bitrate_freq, rest = struct.unpack('BBBB', b[0:4])
            br_id = (bitrate_freq >> 4) & 0x0F  # biterate id
            sr_id = (bitrate_freq >> 2) & 0x03  # sample rate id
            padding = 1 if bitrate_freq & 0x02 > 0 else 0
            mpeg_id = (conf >> 3) & 0x03
            layer_id = (conf >> 1) & 0x03
            channel_mode = (rest >> 6) & 0x03
            # check for eleven 1s, validate bitrate and sample rate
            if not b[:2] > b'\xFF\xE0' or br_id > 14 or br_id == 0 or sr_id == 3 or layer_id == 0 or mpeg_id == 1:
                idx = b.find(b'\xFF', 1)  # invalid frame, find next sync header
                if idx == -1:
                    idx = len(b)  # not found: jump over the current peek buffer
                fh.seek(max(idx, 1), os.SEEK_CUR)
                continue
            try:
                self.channels = self.channels_per_channel_mode[channel_mode]
                frame_bitrate = ID3.bitrate_by_version_by_layer[mpeg_id][layer_id][br_id]
                self.samplerate = ID3.samplerates[mpeg_id][sr_id]
            except (IndexError, TypeError):
                raise TinyTagException('mp3 parsing failed')
            # There might be a xing header in the first frame that contains
            # all the info we need, otherwise parse multiple frames to find the
            # accurate average bitrate
            if frames == 0 and ID3._USE_XING_HEADER:
                xing_header_offset = b.find(b'Xing')
                if xing_header_offset != -1:
                    fh.seek(xing_header_offset, os.SEEK_CUR)
                    xframes, byte_count, toc, vbr_scale = ID3._parse_xing_header(fh)
                    if xframes and xframes != 0 and byte_count:
                        self.duration = xframes * ID3.samples_per_frame / float(self.samplerate) / self.channels
                        self.bitrate = int(byte_count * 8 / self.duration / 1000)
                        self.audio_offset = fh.tell()
                        return
                    continue

            frames += 1  # it's most probably an mp3 frame
            bitrate_accu += frame_bitrate
            if frames == 1:
                self.audio_offset = fh.tell()
            if frames <= ID3._CBR_DETECTION_FRAME_COUNT:
                last_bitrates.append(frame_bitrate)
            fh.seek(4, os.SEEK_CUR)  # jump over peeked bytes

            frame_length = (144000 * frame_bitrate) // self.samplerate + padding
            frame_size_accu += frame_length
            # if bitrate does not change over time its probably CBR
            is_cbr = (frames == ID3._CBR_DETECTION_FRAME_COUNT
                      and len(set(last_bitrates)) == 1)
            if frames == max_estimation_frames or is_cbr:
                # try to estimate duration
                fh.seek(-128, 2)  # jump to last byte (leaving out id3v1 tag)
                audio_stream_size = fh.tell() - self.audio_offset
                est_frame_count = audio_stream_size / (frame_size_accu / float(frames))
                samples = est_frame_count * ID3.samples_per_frame
                self.duration = samples / float(self.samplerate)
                self.bitrate = int(bitrate_accu / frames)
                return

            if frame_length > 1:  # jump over current frame body
                fh.seek(frame_length - header_bytes, os.SEEK_CUR)
        if self.samplerate:
            self.duration = frames * ID3.samples_per_frame / float(self.samplerate)

    def _parse_tag(self, fh):
        self._parse_id3v2(fh)
        attrs = ['track', 'track_total', 'title', 'artist', 'album', 'albumartist', 'year', 'genre']
        has_all_tags = all(getattr(self, attr) for attr in attrs)
        if not has_all_tags and self.filesize > 128:
            fh.seek(-128, os.SEEK_END)  # try parsing id3v1 in last 128 bytes
            self._parse_id3v1(fh)

    def _get_id3v2_header(self, fh):
        header = struct.unpack('3sBBB4B', _read(fh, 10))
        tag = codecs.decode(header[0], 'ISO-8859-1')
        # check if there is an ID3v2 tag at the beginning of the file
        if tag == 'ID3':
            return header
        return None

    def _parse_id3v2(self, fh):
        # for info on the specs, see: http://id3.org/Developer%20Information
        header = self._get_id3v2_header(fh)
        if header:
            major, rev = header[1:3]
            if DEBUG:
                stderr('Found id3 v2.%s' % major)
            # unsync = (header[3] & 0x80) > 0
            extended = (header[3] & 0x40) > 0
            # experimental = (header[3] & 0x20) > 0
            # footer = (header[3] & 0x10) > 0
            size = self._calc_size(header[4:8], 7)
            self._bytepos_after_id3v2 = size
            end_pos = fh.tell() + size
            parsed_size = 0
            if extended:  # just read over the extended header.
                size_bytes = struct.unpack('4B', _read(fh, 6)[0:4])
                extd_size = self._calc_size(size_bytes, 7)
                fh.seek(extd_size - 6, os.SEEK_CUR)  # jump over extended_header
            while parsed_size < size:
                frame_size = self._parse_frame(fh, id3version=major)
                if frame_size == 0:
                    break
                parsed_size += frame_size
            fh.seek(end_pos, os.SEEK_SET)

    def _parse_id3v1(self, fh):
        if fh.read(3) == b'TAG':  # check if this is an ID3 v1 tag
            def asciidecode(x):
                return self._unpad(codecs.decode(x, 'latin1'))
            self._bytepos_after_id3v2 = 0
            fields = fh.read(30 + 30 + 30 + 4 + 30 + 1)
            self._set_field('title', fields[:30], transfunc=asciidecode)
            self._set_field('artist', fields[30:60], transfunc=asciidecode)
            self._set_field('album', fields[60:90], transfunc=asciidecode)
            self._set_field('year', fields[90:94], transfunc=asciidecode)
            comment = fields[94:124]
            if b'\x00\x00' < comment[-2:] < b'\x01\x00':
                self._set_field('track', str(ord(comment[-1:])))
                comment = comment[:-2]
            self._set_field('comment', comment, transfunc=asciidecode)
            genre_id = ord(fields[124:125])
            if genre_id < len(ID3.ID3V1_GENRES):
                self.genre = ID3.ID3V1_GENRES[genre_id]

    def _parse_frame(self, fh, id3version=False):
        # ID3v2.2 especially ugly. see: http://id3.org/id3v2-00
        frame_header_size = 6 if id3version == 2 else 10
        frame_size_bytes = 3 if id3version == 2 else 4
        binformat = '3s3B' if id3version == 2 else '4s4B2B'
        bits_per_byte = 7 if id3version == 4 else 8  # only id3v2.4 is synchsafe
        frame_header_data = fh.read(frame_header_size)
        if len(frame_header_data) != frame_header_size:
            return 0
        frame = struct.unpack(binformat, frame_header_data)
        frame_id = self._decode_string(frame[0])
        frame_size = self._calc_size(frame[1:1 + frame_size_bytes], bits_per_byte)
        if DEBUG:
            stderr('Found id3 Frame %s at %d-%d of %d' % (frame_id, fh.tell(), fh.tell() + frame_size, self.filesize))
        if frame_size > 0:
            # flags = frame[1+frame_size_bytes:] # dont care about flags.
            if frame_id not in ID3.PARSABLE_FRAME_IDS:  # jump over unparsable frames
                fh.seek(frame_size, os.SEEK_CUR)
                return frame_size
            content = fh.read(frame_size)
            fieldname = ID3.FRAME_ID_TO_FIELD.get(frame_id)
            if fieldname:
                self._set_field(fieldname, content, self._decode_string)
            elif frame_id in self.IMAGE_FRAME_IDS and self._load_image:
                # See section 4.14: http://id3.org/id3v2.4.0-frames
                if frame_id == 'PIC':  # ID3 v2.2:
                    desc_end_pos = content.index(b'\x00', 1) + 1
                else:  # ID3 v2.3+
                    textencoding = content[0]
                    mimetype_end_pos = content.index(b'\x00', 1) + 1
                    desc_start_pos = mimetype_end_pos + 1  # jump over picture type
                    if textencoding == 0:
                        desc_end_pos = content.index(b'\x00', desc_start_pos) + 1
                    else:
                        desc_end_pos = content.index(b'\x00\x00', desc_start_pos) + 2
                if content[desc_end_pos:desc_end_pos + 1] == b'\x00':
                    desc_end_pos += 1  # the description ends with 1 null byte
                self._image_data = content[desc_end_pos:]
            return frame_size
        return 0

    def _decode_string(self, bytestr):
        try:  # it's not my fault, this is the spec.
            first_byte = bytestr[:1]
            if first_byte == b'\x00':  # ISO-8859-1
                bytestr = bytestr[1:]
                encoding = 'ISO-8859-1'
            elif first_byte == b'\x01':  # UTF-16 with BOM
                bytestr = bytestr[1:]
                if bytestr[:5] == b'eng\xff\xfe':
                    bytestr = bytestr[3:]  # remove language (but leave BOM)
                if bytestr[:5] == b'eng\xfe\xff':
                    bytestr = bytestr[3:]  # remove language (but leave BOM)
                if bytestr[:4] == b'eng\x00':
                    bytestr = bytestr[4:]  # remove language
                if bytestr[:1] == b'\x00':
                    bytestr = bytestr[1:]  # strip optional additional null byte
                # read byte order mark to determine endianess
                encoding = 'UTF-16be' if bytestr[0:2] == b'\xfe\xff' else 'UTF-16le'
                # strip the bom and optional null bytes
                bytestr = bytestr[2:] if len(bytestr) % 2 == 0 else bytestr[2:-1]
                # remove ADDITIONAL EXTRA BOM :facepalm:
                if bytestr[:4] == b'\x00\x00\xff\xfe':
                    bytestr = bytestr[4:]
            elif first_byte == b'\x02':  # UTF-16LE
                # strip optional null byte, if byte count uneven
                bytestr = bytestr[1:-1] if len(bytestr) % 2 == 0 else bytestr[1:]
                encoding = 'UTF-16le'
            elif first_byte == b'\x03':  # UTF-8
                bytestr = bytestr[1:]
                encoding = 'UTF-8'
            else:
                bytestr = bytestr
                encoding = 'ISO-8859-1'  # wild guess
            if bytestr[:4] == b'eng\x00':
                bytestr = bytestr[4:]  # remove language
            errors = 'ignore' if self._ignore_errors else 'strict'
            return self._unpad(codecs.decode(bytestr, encoding, errors))
        except UnicodeDecodeError:
            raise TinyTagException('Error decoding ID3 Tag!')

    def _calc_size(self, bytestr, bits_per_byte):
        # length of some mp3 header fields is described by 7 or 8-bit-bytes
        return reduce(lambda accu, elem: (accu << bits_per_byte) + elem, bytestr, 0)


class Ogg(TinyTag):
    def __init__(self, filehandler, filesize, *args, **kwargs):
        TinyTag.__init__(self, filehandler, filesize, *args, **kwargs)
        self._tags_parsed = False
        self._max_samplenum = 0  # maximum sample position ever read

    def _determine_duration(self, fh):
        max_page_size = 65536  # https://xiph.org/ogg/doc/libogg/ogg_page.html
        if not self._tags_parsed:
            self._parse_tag(fh)  # determine sample rate
            fh.seek(0)           # and rewind to start
        if self.filesize > max_page_size:
            fh.seek(-max_page_size, 2)  # go to last possible page position
        while True:
            b = fh.peek(4)
            if len(b) == 0:
                return  # EOF
            if b[:4] == b'OggS':  # look for an ogg header
                for _ in self._parse_pages(fh):
                    pass  # parse all remaining pages
                self.duration = self._max_samplenum / float(self.samplerate)
            else:
                idx = b.find(b'OggS')  # try to find header in peeked data
                seekpos = idx if idx != -1 else len(b) - 3
                fh.seek(max(seekpos, 1), os.SEEK_CUR)

    def _parse_tag(self, fh):
        page_start_pos = fh.tell()  # set audio_offest later if its audio data
        for packet in self._parse_pages(fh):
            walker = BytesIO(packet)
            if packet[0:7] == b"\x01vorbis":
                (channels, self.samplerate, max_bitrate, bitrate,
                 min_bitrate) = struct.unpack("<B4i", packet[11:28])
                if not self.audio_offset:
                    self.bitrate = bitrate / 1024.0
                    self.audio_offset = page_start_pos
            elif packet[0:7] == b"\x03vorbis":
                walker.seek(7, os.SEEK_CUR)  # jump over header name
                self._parse_vorbis_comment(walker)
            elif packet[0:8] == b'OpusHead':  # parse opus header
                # https://www.videolan.org/developers/vlc/modules/codec/opus_header.c
                # https://mf4.xiph.org/jenkins/view/opus/job/opusfile-unix/ws/doc/html/structOpusHead.html
                walker.seek(8, os.SEEK_CUR)  # jump over header name
                (version, ch, _, sr, _, _) = struct.unpack("<BBHIHB", walker.read(11))
                if (version & 0xF0) == 0:  # only major version 0 supported
                    self.channels = ch
                    self.samplerate = 48000  # internally opus always uses 48khz
            elif packet[0:8] == b'OpusTags':  # parse opus metadata:
                walker.seek(8, os.SEEK_CUR)  # jump over header name
                self._parse_vorbis_comment(walker)
            else:
                if DEBUG:
                    stderr('Unsupported Ogg page type: ', packet[:16])
                break
            page_start_pos = fh.tell()

    def _parse_vorbis_comment(self, fh):
        # for the spec, see: http://xiph.org/vorbis/doc/v-comment.html
        # discnumber tag based on: https://en.wikipedia.org/wiki/Vorbis_comment
        # https://sno.phy.queensu.ca/~phil/exiftool/TagNames/Vorbis.html
        comment_type_to_attr_mapping = {
            'album': 'album',
            'albumartist': 'albumartist',
            'title': 'title',
            'artist': 'artist',
            'date': 'year',
            'tracknumber': 'track',
            'totaltracks': 'track_total',
            'discnumber': 'disc',
            'totaldiscs': 'disc_total',
            'genre': 'genre',
            'description': 'comment',
            'composer': 'composer',
        }
        vendor_length = struct.unpack('I', fh.read(4))[0]
        fh.seek(vendor_length, os.SEEK_CUR)  # jump over vendor
        elements = struct.unpack('I', fh.read(4))[0]
        for i in range(elements):
            length = struct.unpack('I', fh.read(4))[0]
            try:
                keyvalpair = codecs.decode(fh.read(length), 'UTF-8')
            except UnicodeDecodeError:
                continue
            if '=' in keyvalpair:
                key, value = keyvalpair.split('=', 1)
                if DEBUG:
                    stderr('Found Vorbis Comment', key, value[:64])
                fieldname = comment_type_to_attr_mapping.get(key.lower())
                if fieldname:
                    self._set_field(fieldname, value)

    def _parse_pages(self, fh):
        # for the spec, see: https://wiki.xiph.org/Ogg
        previous_page = b''  # contains data from previous (continuing) pages
        header_data = fh.read(27)  # read ogg page header
        while len(header_data) != 0:
            header = struct.unpack('<4sBBqIIiB', header_data)
            # https://xiph.org/ogg/doc/framing.html
            oggs, version, flags, pos, serial, pageseq, crc, segments = header
            self._max_samplenum = max(self._max_samplenum, pos)
            if oggs != b'OggS' or version != 0:
                raise TinyTagException('Not a valid ogg file!')
            segsizes = struct.unpack('B' * segments, fh.read(segments))
            total = 0
            for segsize in segsizes:  # read all segments
                total += segsize
                if total < 255:  # less than 255 bytes means end of page
                    yield previous_page + fh.read(total)
                    previous_page = b''
                    total = 0
            if total != 0:
                if total % 255 == 0:
                    previous_page += fh.read(total)
                else:
                    yield previous_page + fh.read(total)
                    previous_page = b''
            header_data = fh.read(27)


class Wave(TinyTag):
    # https://sno.phy.queensu.ca/~phil/exiftool/TagNames/RIFF.html
    riff_mapping = {
        b'INAM': 'title',
        b'TITL': 'title',
        b'IART': 'artist',
        b'ICMT': 'comment',
        b'ICRD': 'year',
        b'IGNR': 'genre',
        b'TRCK': 'track',
        b'PRT1': 'track',
        b'PRT2': 'track_number',
        b'YEAR': 'year',
        # riff format is lacking the composer field.
    }

    def __init__(self, filehandler, filesize, *args, **kwargs):
        TinyTag.__init__(self, filehandler, filesize, *args, **kwargs)
        self._duration_parsed = False

    def _determine_duration(self, fh):
        # see: https://ccrma.stanford.edu/courses/422/projects/WaveFormat/
        # and: https://en.wikipedia.org/wiki/WAV
        riff, size, fformat = struct.unpack('4sI4s', fh.read(12))
        if riff != b'RIFF' or fformat != b'WAVE':
            raise TinyTagException('not a wave file!')
        bitdepth = 16  # assume 16bit depth (CD quality)
        chunk_header = fh.read(8)
        while len(chunk_header) == 8:
            subchunkid, subchunksize = struct.unpack('4sI', chunk_header)
            if subchunkid == b'fmt ':
                _, self.channels, self.samplerate = struct.unpack('HHI', fh.read(8))
                _, _, bitdepth = struct.unpack('<IHH', fh.read(8))
                self.bitrate = self.samplerate * self.channels * bitdepth / 1024.0
            elif subchunkid == b'data':
                self.duration = float(subchunksize) / self.channels / self.samplerate / (bitdepth / 8)
                self.audio_offest = fh.tell() - 8  # rewind to data header
                fh.seek(subchunksize, 1)
            elif subchunkid == b'LIST':
                is_info = fh.read(4)  # check INFO header
                if is_info != b'INFO':  # jump over non-INFO sections
                    fh.seek(subchunksize - 4, os.SEEK_CUR)
                else:
                    sub_fh = BytesIO(fh.read(subchunksize - 4))
                    field = sub_fh.read(4)
                    while len(field) == 4:
                        data_length = struct.unpack('I', sub_fh.read(4))[0]
                        data = sub_fh.read(data_length).split(b'\x00', 1)[0]  # strip zero-byte
                        data = codecs.decode(data, 'utf-8')
                        fieldname = self.riff_mapping.get(field)
                        if fieldname:
                            self._set_field(fieldname, data)
                        field = sub_fh.read(4)
            elif subchunkid == b'id3 ' or subchunkid == b'ID3 ':
                id3 = ID3(fh, 0)
                id3._parse_id3v2(fh)
                self.update(id3)
            else:  # some other chunk, just skip the data
                fh.seek(subchunksize, 1)
            chunk_header = fh.read(8)
        self._duration_parsed = True

    def _parse_tag(self, fh):
        if not self._duration_parsed:
            self._determine_duration(fh)  # parse whole file to determine tags:(


class Flac(TinyTag):
    METADATA_STREAMINFO = 0
    METADATA_PADDING = 1
    METADATA_APPLICATION = 2
    METADATA_SEEKTABLE = 3
    METADATA_VORBIS_COMMENT = 4
    METADATA_CUESHEET = 5
    METADATA_PICTURE = 6

    def load(self, tags, duration, image=False):
        self._load_image = image
        header = self._filehandler.peek(4)
        if header[:3] == b'ID3':  # parse ID3 header if it exists
            id3 = ID3(self._filehandler, 0)
            id3._parse_id3v2(self._filehandler)
            self.update(id3)
            header = self._filehandler.peek(4)  # after ID3 should be fLaC
        if header[:4] != b'fLaC':
            raise TinyTagException('Invalid flac header')
        self._filehandler.seek(4, os.SEEK_CUR)
        self._determine_duration(self._filehandler, skip_tags=not tags)

    def _determine_duration(self, fh, skip_tags=False):
        # for spec, see https://xiph.org/flac/ogg_mapping.html
        header_data = fh.read(4)
        while len(header_data):
            meta_header = struct.unpack('B3B', header_data)
            block_type = meta_header[0] & 0x7f
            is_last_block = meta_header[0] & 0x80
            size = _bytes_to_int(meta_header[1:4])
            # http://xiph.org/flac/format.html#metadata_block_streaminfo
            if block_type == Flac.METADATA_STREAMINFO:
                stream_info_header = fh.read(size)
                if len(stream_info_header) < 34:  # invalid streaminfo
                    return
                header = struct.unpack('HH3s3s8B16s', stream_info_header)
                # From the ciph documentation:
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
                # min_blk, max_blk, min_frm, max_frm = header[0:4]
                # min_frm = _bytes_to_int(struct.unpack('3B', min_frm))
                # max_frm = _bytes_to_int(struct.unpack('3B', max_frm))
                #                 channels--.  bits      total samples
                # |----- samplerate -----| |-||----| |---------~   ~----|
                # 0000 0000 0000 0000 0000 0000 0000 0000 0000      0000
                # #---4---# #---5---# #---6---# #---7---# #--8-~   ~-12-#
                self.samplerate = _bytes_to_int(header[4:7]) >> 4
                self.channels = ((header[6] >> 1) & 0x07) + 1
                # bit_depth = ((header[6] & 1) << 4) + ((header[7] & 0xF0) >> 4)
                # bit_depth = (bit_depth + 1)
                total_sample_bytes = [(header[7] & 0x0F)] + list(header[8:12])
                total_samples = _bytes_to_int(total_sample_bytes)
                self.duration = float(total_samples) / self.samplerate
                if self.duration > 0:
                    self.bitrate = self.filesize / self.duration * 8 / 1024
            elif block_type == Flac.METADATA_VORBIS_COMMENT and not skip_tags:
                oggtag = Ogg(fh, 0)
                oggtag._parse_vorbis_comment(fh)
                self.update(oggtag)
            elif block_type == Flac.METADATA_PICTURE and self._load_image:
                # https://xiph.org/flac/format.html#metadata_block_picture
                pic_type, mime_len = struct.unpack('>2I', fh.read(8))
                mime = fh.read(mime_len)  # noqa
                description_len = struct.unpack('>I', fh.read(4))[0]
                description = fh.read(description_len)  # noqa
                width, height, depth, colors, pic_len = struct.unpack('>5I', fh.read(20))
                self._image_data = fh.read(pic_len)
            elif block_type >= 127:
                return  # invalid block type
            else:
                if DEBUG:
                    stderr('Unknown FLAC block type', block_type)
                fh.seek(size, 1)  # seek over this block

            if is_last_block:
                return
            header_data = fh.read(4)


class Wma(TinyTag):
    ASF_CONTENT_DESCRIPTION_OBJECT = b'3&\xb2u\x8ef\xcf\x11\xa6\xd9\x00\xaa\x00b\xcel'
    ASF_EXTENDED_CONTENT_DESCRIPTION_OBJECT = b'@\xa4\xd0\xd2\x07\xe3\xd2\x11\x97\xf0\x00\xa0\xc9^\xa8P'
    STREAM_BITRATE_PROPERTIES_OBJECT = b'\xceu\xf8{\x8dF\xd1\x11\x8d\x82\x00`\x97\xc9\xa2\xb2'
    ASF_FILE_PROPERTY_OBJECT = b'\xa1\xdc\xab\x8cG\xa9\xcf\x11\x8e\xe4\x00\xc0\x0c Se'
    ASF_STREAM_PROPERTIES_OBJECT = b'\x91\x07\xdc\xb7\xb7\xa9\xcf\x11\x8e\xe6\x00\xc0\x0c Se'
    STREAM_TYPE_ASF_AUDIO_MEDIA = b'@\x9ei\xf8M[\xcf\x11\xa8\xfd\x00\x80_\\D+'
    # see:
    # http://web.archive.org/web/20131203084402/http://msdn.microsoft.com/en-us/library/bb643323.aspx
    # and (japanese, but none the less helpful)
    # http://uguisu.skr.jp/Windows/format_asf.html

    def __init__(self, filehandler, filesize, *args, **kwargs):
        TinyTag.__init__(self, filehandler, filesize, *args, **kwargs)
        self.__tag_parsed = False

    def _determine_duration(self, fh):
        if not self.__tag_parsed:
            self._parse_tag(fh)

    def read_blocks(self, fh, blocks):
        # blocks are a list(tuple('fieldname', byte_count, cast_int), ...)
        decoded = {}
        for block in blocks:
            val = fh.read(block[1])
            if block[2]:
                val = _bytes_to_int_le(val)
            decoded[block[0]] = val
        return decoded

    def __bytes_to_guid(self, obj_id_bytes):
        return '-'.join([
            hex(_bytes_to_int_le(obj_id_bytes[:-12]))[2:].zfill(6),
            hex(_bytes_to_int_le(obj_id_bytes[-12:-10]))[2:].zfill(4),
            hex(_bytes_to_int_le(obj_id_bytes[-10:-8]))[2:].zfill(4),
            hex(_bytes_to_int(obj_id_bytes[-8:-6]))[2:].zfill(4),
            hex(_bytes_to_int(obj_id_bytes[-6:]))[2:].zfill(12),
        ])

    def __decode_string(self, bytestring):
        return self._unpad(codecs.decode(bytestring, 'utf-16'))

    def __decode_ext_desc(self, value_type, value):
        """ decode ASF_EXTENDED_CONTENT_DESCRIPTION_OBJECT values"""
        if value_type == 0:  # Unicode string
            return self.__decode_string(value)
        elif value_type == 1:  # BYTE array
            return value
        elif 1 < value_type < 6:  # DWORD / QWORD / WORD
            return _bytes_to_int_le(value)

    def _parse_tag(self, fh):
        self.__tag_parsed = True
        guid = fh.read(16)  # 128 bit GUID
        if guid != b'0&\xb2u\x8ef\xcf\x11\xa6\xd9\x00\xaa\x00b\xcel':
            return  # not a valid ASF container! see: http://www.garykessler.net/library/file_sigs.html
        struct.unpack('Q', fh.read(8))[0]  # size
        struct.unpack('I', fh.read(4))[0]  # obj_count
        if fh.read(2) != b'\x01\x02':
            # http://web.archive.org/web/20131203084402/http://msdn.microsoft.com/en-us/library/bb643323.aspx#_Toc521913958
            return  # not a valid asf header!
        while True:
            object_id = fh.read(16)
            object_size = _bytes_to_int_le(fh.read(8))
            if object_size == 0 or object_size > self.filesize:
                break  # invalid object, stop parsing.
            if object_id == Wma.ASF_CONTENT_DESCRIPTION_OBJECT:
                len_blocks = self.read_blocks(fh, [
                    ('title_length', 2, True),
                    ('author_length', 2, True),
                    ('copyright_length', 2, True),
                    ('description_length', 2, True),
                    ('rating_length', 2, True),
                ])
                data_blocks = self.read_blocks(fh, [
                    ('title', len_blocks['title_length'], False),
                    ('artist', len_blocks['author_length'], False),
                    ('', len_blocks['copyright_length'], True),
                    ('comment', len_blocks['description_length'], False),
                    ('', len_blocks['rating_length'], True),
                ])
                for field_name, bytestring in data_blocks.items():
                    if field_name:
                        self._set_field(field_name, bytestring, self.__decode_string)
            elif object_id == Wma.ASF_EXTENDED_CONTENT_DESCRIPTION_OBJECT:
                mapping = {
                    'WM/TrackNumber': 'track',
                    'WM/PartOfSet': 'disc',
                    'WM/Year': 'year',
                    'WM/AlbumArtist': 'albumartist',
                    'WM/Genre': 'genre',
                    'WM/AlbumTitle': 'album',
                    'WM/Composer': 'composer',
                }
                # see: http://web.archive.org/web/20131203084402/http://msdn.microsoft.com/
                # en-us/library/bb643323.aspx#_Toc509555195
                descriptor_count = _bytes_to_int_le(fh.read(2))
                for _ in range(descriptor_count):
                    name_len = _bytes_to_int_le(fh.read(2))
                    name = self.__decode_string(fh.read(name_len))
                    value_type = _bytes_to_int_le(fh.read(2))
                    value_len = _bytes_to_int_le(fh.read(2))
                    value = fh.read(value_len)
                    field_name = mapping.get(name)
                    if field_name:
                        field_value = self.__decode_ext_desc(value_type, value)
                        self._set_field(field_name, field_value)
            elif object_id == Wma.ASF_FILE_PROPERTY_OBJECT:
                blocks = self.read_blocks(fh, [
                    ('file_id', 16, False),
                    ('file_size', 8, False),
                    ('creation_date', 8, True),
                    ('data_packets_count', 8, True),
                    ('play_duration', 8, True),
                    ('send_duration', 8, True),
                    ('preroll', 8, True),
                    ('flags', 4, False),
                    ('minimum_data_packet_size', 4, True),
                    ('maximum_data_packet_size', 4, True),
                    ('maximum_bitrate', 4, False),
                ])
                self.duration = blocks.get('play_duration') / float(10000000)
            elif object_id == Wma.ASF_STREAM_PROPERTIES_OBJECT:
                blocks = self.read_blocks(fh, [
                    ('stream_type', 16, False),
                    ('error_correction_type', 16, False),
                    ('time_offset', 8, True),
                    ('type_specific_data_length', 4, True),
                    ('error_correction_data_length', 4, True),
                    ('flags', 2, True),
                    ('reserved', 4, False)
                ])
                already_read = 0
                if blocks['stream_type'] == Wma.STREAM_TYPE_ASF_AUDIO_MEDIA:
                    stream_info = self.read_blocks(fh, [
                        ('codec_id_format_tag', 2, True),
                        ('number_of_channels', 2, True),
                        ('samples_per_second', 4, True),
                        ('avg_bytes_per_second', 4, True),
                        ('block_alignment', 2, True),
                        ('bits_per_sample', 2, True),
                    ])
                    self.samplerate = stream_info['samples_per_second']
                    self.bitrate = stream_info['avg_bytes_per_second'] * 8 / float(1000)
                    already_read = 16
                fh.seek(blocks['type_specific_data_length'] - already_read, os.SEEK_CUR)
                fh.seek(blocks['error_correction_data_length'], os.SEEK_CUR)
            else:
                fh.seek(object_size - 24, os.SEEK_CUR)  # read over onknown object ids


class Aiff(ID3):
    #
    # AIFF is part of the IFF family of file formats.  That means it has a _wide_
    # variety of things that can appear in it.  However... Python natively
    # supports reading/writing the most common AIFF formats! But it does not
    # support pulling tags out of them.  Therefore, Python is going to do the
    # heavy lifting and this code just handles the metadata chunks.
    #
    # https://en.wikipedia.org/wiki/Audio_Interchange_File_Format#Data_format
    # https://web.archive.org/web/20171118222232/http://www-mmsp.ece.mcgill.ca/documents/audioformats/aiff/aiff.html
    # https://web.archive.org/web/20071219035740/http://www.cnpbagwell.com/aiff-c.txt
    #
    # A few things about the spec:
    #
    # * IFF strings are not supposed to be null terminated.  They sometimes are.
    # * The spec is a bit contradictory in terms of strings being ASCII or not. The assumption
    #   here is that they are.
    # * Some tools might throw more metadata into the ANNO chunk but it is
    #   wildly unreliable to count on it. In fact, the official spec recommends against
    #   using it. That said... this code throws the ANNO field into comment and hopes
    #   for the best.
    #
    # Additionally:
    #
    # * Python allegedly supports ALAW/alaw, G722, and ULAW/ulaw AIFF-C compression.
    #   However it does seem to have implementation bugs.
    #   Anything it doesn't understand (e.g., 'sowt') will throw an exception.
    #
    # The key thing here is that AIFF metadata is usually in a handful of fields
    # and the rest is an ID3 or XMP field.  XMP is too complicated and only Adobe-related
    # products support it. The vast majority use ID3. As such, this code inherits from
    # ID3 rather than TinyTag since it does everything that needs to be done here.
    #
    #
    def __init__(self, filehandler, filesize, *args, **kwargs):
        super(Aiff, self).__init__(filehandler, filesize, *args, **kwargs)
        self.__tag_parsed = False

    def _determine_duration(self, fh):
        fh.seek(0, 0)
        # NOTE: aifc will throw an exception if a compression
        # type is not supported, such as 'sowt'
        aiffobj = aifc.open(fh, 'rb')
        self.channels = aiffobj.getnchannels()
        self.samplerate = aiffobj.getframerate()
        self.duration = float(aiffobj.getnframes()) / float(self.samplerate)
        self.bitrate = self.samplerate * self.channels * 16.0 / 1024.0

    def _parse_tag(self, fh):
        fh.seek(0, 0)
        self.__tag_parsed = True
        chunk = Chunk(fh)
        if chunk.getname() != b'FORM':
            raise TinyTagException('not an aiff file!')

        formdata = chunk.read(4)
        if formdata not in (b'AIFC', b'AIFF'):
            raise TinyTagException('not an aiff file!')

        while True:
            try:
                chunk = Chunk(fh)
            except EOFError:
                break

            chunkname = chunk.getname()
            if chunkname == b'NAME':
                # "Name Chunk text contains the name of the sampled sound."
                self.title = self._unpad(chunk.read().decode('ascii'))
            elif chunkname == b'AUTH':
                # "Author Chunk text contains one or more author names.  An author in
                # this case is the creator of a sampled sound."
                self.artist = self._unpad(chunk.read().decode('ascii'))
            elif chunkname == b'ANNO':
                # "Annotation Chunk text contains a comment.  Use of this chunk is
                # discouraged within FORM AIFC." Some tools: "hold my beer"
                self._set_field('comment', self._unpad(chunk.read().decode('ascii')))
            elif chunkname == b'(c) ':
                # "The Copyright Chunk contains a copyright notice for the sound.  text
                #  contains a date followed by the copyright owner.  The chunk ID '[c] '
                # serves as the copyright character. " Some tools: "hold my beer"
                field = chunk.read().decode('utf-8')
                self._set_field('extra.copyright', field)
            elif chunkname == b'ID3 ':
                super(Aiff, self)._parse_tag(fh)
            elif chunkname == b'SSND':
                # probably the closest equivalent, but this isn't particular viable
                # for AIFF
                self.audio_offset = fh.tell()
                chunk.skip()
            else:
                chunk.skip()
