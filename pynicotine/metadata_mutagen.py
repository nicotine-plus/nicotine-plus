# Python core
from __future__ import division

# Python modules
import mutagen
import os

from mutagen.mp3 import MP3, MPEGInfo
from mutagen.mp4 import MP4StreamInfoError
from mutagen.flac import FLAC, StreamInfo
#from mutagen.apev2 import APEv2, APEv2File
from mutagen.oggvorbis import OggVorbisInfo
from mutagen.musepack import MusepackInfo
from mutagen.asf import ASFInfo
from mutagen.monkeysaudio import MonkeysAudioInfo
from mutagen.mp4 import MP4Info

# Application specific
from logfacility import log


def detect(path):
	try:
		audio = mutagen.File(path)
	except IOError:
		return None
	except Exception, e:
		log.addwarning("Mutagen crashed on '%s': %s" % (path, e))
		return None
	try:
		audio.info
	except:
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
	else:
		print "EEK, what should I do with %(type)s (%(file)s)?" %{"type": str(type(audio.info)), "file":path} 
	return processGeneric(audio)
def processGeneric(audio):
	try:
		return {
			"bitrate": (audio.info.bitrate/1000),
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
		"bitrate": (audio.info.bitrate/1000),
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
		"time": audio.info.length,
	}
def processVorbis(audio):
	return {
		"bitrate": (audio.info.bitrate/1000),
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
		"bitrate": (audio.info.bitrate/1000),
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
		"time": audio.info.length,
	}
