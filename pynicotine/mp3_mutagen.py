#!/usr/bin/env python
import mutagen

from mutagen.mp3 import MP3, MPEGInfo
from mutagen.mp4 import MP4StreamInfoError
from mutagen.flac import FLAC, StreamInfo
#from mutagen.apev2 import APEv2, APEv2File
from mutagen.oggvorbis import OggVorbisInfo
from mutagen.musepack import MusepackInfo



def detect_mp3(path):
	try:
		audio = mutagen.File(path)
	except IOError:
		return None
	# mutagen didn't think the file was audio
	if not audio:
		return None
	if type(audio.info) == MPEGInfo:
		return processMPEG(audio)
	elif type(audio.info) == StreamInfo:
		return processFlac(audio)
	elif type(audio.info) == OggVorbisInfo:
		return processVorbis(audio)
	elif type(audio.info) == MusepackInfo:
		return processMusepack(audio)
	else:
		print "EEK, wat moet ik met " + str(type(audio.info)) + " aan?"
		return processGeneric(audio)
def processGeneric(audio):
	return {
		"bitrate": (audio.info.bitrate/1000),
		"vbr": 0,
		"time": int(audio.info.length),
	}
def processMusepack(audio):
	return {
		"bitrate": (audio.info.bitrate/1000),
		"vbr": 1,
		"time": int(audio.info.length),
	}
def processMPEG(audio):
	vbr = False
	if audio.info.bitrate % 1000 != 0:
		vbr = True
	else:
		rates = audio.info._MPEGInfo__BITRATE[(audio.info.version, audio.info.layer)]
		vbr = (audio.info.bitrate / 1000) not in rates
	if vbr:
		vbr = 1
	else:
		vbr = 0
	return {
		"bitrate": (audio.info.bitrate/1000),
		"vbr": vbr,
		"time": int(audio.info.length),
	}
def processFlac(audio):
	return {
		"bitrate": (audio.info.bits_per_sample * audio.info.sample_rate / 1000),
		"vbr": 0,
		"time": int(audio.info.length),
	}
def processVorbis(audio):
	return {
		"bitrate": (audio.info.bitrate/1000),
		"vbr": 1,
		"time": int(audio.info.length),
	}
