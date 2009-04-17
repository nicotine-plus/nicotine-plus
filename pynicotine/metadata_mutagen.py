#!/usr/bin/env python
import mutagen

from mutagen.mp3 import MP3, MPEGInfo
from mutagen.mp4 import MP4StreamInfoError
from mutagen.flac import FLAC, StreamInfo
#from mutagen.apev2 import APEv2, APEv2File
from mutagen.oggvorbis import OggVorbisInfo
from mutagen.musepack import MusepackInfo
from mutagen.monkeysaudio import MonkeysAudioInfo
from mutagen.mp4 import MP4Info

def detect(path):
	try:
		audio = mutagen.File(path)
	except IOError:
		return None
	# mutagen didn't think the file was audio
	if not audio:
		return None
	if type(audio.info) == MPEGInfo:
		return processMPEG(audio)
	if type(audio.info) == StreamInfo:
		return processFlac(audio)
	if type(audio.info) == OggVorbisInfo:
		return processVorbis(audio)
	if type(audio.info) == MusepackInfo:
		return processMusepack(audio)
	if type(audio.info) == MonkeysAudioInfo:
		return processMonkeys(audio)
	if type(audio.info) == MP4Info:
		return processMP4(audio)
	print "EEK, what should I do with " + str(type(audio.info)) + "?"
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
		"bitrate": (audio.info.bitrate/1000),
		"vbr": True,
		"time": audio.info.length,
	}
def processMPEG(audio):
	vbr = False
	if audio.info.bitrate % 1000 != 0:
		vbr = True
	else:
		rates = audio.info._MPEGInfo__BITRATE[(audio.info.version, audio.info.layer)]
		vbr = (audio.info.bitrate / 1000) not in rates
	if vbr:
		vbr = True
	else:
		vbr = False
	return {
		"bitrate": (audio.info.bitrate/1000),
		"vbr": vbr,
		"time": audio.info.length,
	}
def processFlac(audio):
	return {
		"bitrate": (audio.info.bits_per_sample * audio.info.sample_rate / 1000),
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
		"bitrate": audio.info.bitrate,
		"vbr": True,
		"time": audio.info.length,
	}
