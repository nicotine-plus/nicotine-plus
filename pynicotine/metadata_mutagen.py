# COPYRIGHT (C) 2016-2017 Michael Labouebe <gfarmerfr@free.fr>
# COPYRIGHT (C) 2016 Josep Anguera <josep.anguera@gmail.com>
# COPYRIGHT (C) 2016 Mutnick <muhing@yahoo.com>
# COPYRIGHT (C) 2009-2010 Quinox <quinox@users.sf.net>
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

import mutagen
from mutagen.asf import ASFInfo
from mutagen.flac import StreamInfo
from mutagen.monkeysaudio import MonkeysAudioInfo
from mutagen.mp3 import MPEGInfo
from mutagen.mp4 import MP4Info
from mutagen.musepack import MusepackInfo
from mutagen.oggopus import OggOpusInfo
from mutagen.oggvorbis import OggVorbisInfo
from pynicotine.logfacility import log


def detect(path):

    try:
        audio = mutagen.File(path)
    except IOError:
        return None
    except Exception as e:
        log.addwarning("Mutagen crashed on '%s': %s" % (path, e))
        return None

    try:
        audio.info
    except Exception:
        # mutagen didn't think the file was audio
        return None

    if type(audio.info) == MPEGInfo:
        return processMPEG(audio)
    elif type(audio.info) == StreamInfo:
        return processFlac(audio)
    elif type(audio.info) == OggVorbisInfo:
        return processVorbis(audio)
    elif type(audio.info) == MusepackInfo:
        return processMusepack(audio)
    elif type(audio.info) == MonkeysAudioInfo:
        return processMonkeys(audio)
    elif type(audio.info) == MP4Info:
        return processMP4(audio)
    elif type(audio.info) == ASFInfo:
        return processASF(audio)
    elif type(audio.info) == OggOpusInfo:
        return processOpus(audio)
    else:
        print("EEK, what should I do with %(type)s (%(file)s)?" % {"type": str(type(audio.info)), "file": path})

    return processGeneric(audio)


def processGeneric(audio):

    try:
        return {
            "bitrate": (audio.info.bitrate / 1000),
            "vbr": False,
            "time": audio.info.length,
        }
    except AttributeError:
        return None


def processMusepack(audio):

    return {
        "bitrate": audio.info.bitrate,
        "vbr": True,
        "time": audio.info.length,
    }


def processMPEG(audio):

    if hasattr(audio.info, 'bitrate_mode'):
        from mutagen.mp3 import BitrateMode
        vbr = audio.info.bitrate_mode == BitrateMode.VBR
    else:
        if audio.info.bitrate % 1000 != 0:
            vbr = True
        else:
            rates = audio.info._MPEGInfo__BITRATE[(audio.info.version, audio.info.layer)]
            vbr = (audio.info.bitrate / 1000) not in rates

    return {
        "bitrate": (audio.info.bitrate / 1000),
        "vbr": vbr,
        "time": audio.info.length,
    }


def processFlac(audio):

    filesize = os.path.getsize(audio.filename)

    duration = audio.info.length

    if duration > 0:
        bitrate = filesize / duration * 8 / 1000
    else:
        bitrate = None

    return {
        "bitrate": bitrate,
        "vbr": False,
        "time": duration,
    }


def processVorbis(audio):

    return {
        "bitrate": (audio.info.bitrate / 1000),
        "vbr": True,
        "time": audio.info.length,
    }


def processMonkeys(audio):

    info = {
        "time": audio.info.length,
        "vbr": True,
        "bitrate": 0,
    }

    try:
        # Weirdly enough not all files have sample rates
        info['bitrate'] = audio.info.bits_per_sample * audio.info.sample_rate
    except AttributeError:
        pass

    return info


def processMP4(audio):

    return {
        "bitrate": (audio.info.bitrate / 1000),
        "vbr": True,
        "time": audio.info.length,
    }


def processASF(audio):

    filesize = os.path.getsize(audio.filename)

    duration = audio.info.length

    if duration > 0:
        bitrate = filesize / duration / 1000
    else:
        bitrate = None

    return {
        "bitrate": bitrate,
        "vbr": True,
        "time": duration,
    }


def processOpus(audio):

    duration = audio.info.length

    filesize = os.path.getsize(audio.filename)

    if duration != 0:
        bitrate = filesize / duration * 8 / 1000
    else:
        bitrate = None

    return {
        "bitrate": bitrate,
        "vbr": True,
        "time": duration,
    }
