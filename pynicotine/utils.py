# Copyright (C) 2007 daelstorm. All rights reserved.
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
#
# Based on code from Nicotine, previous copyright below:
# Copyright (c) 2003-2004 Hyriand. All rights reserved.
#
# Based on code from PySoulSeek, original copyright note:
# Copyright (c) 2001-2003 Alexander Kanavin. All rights reserved

"""
This module contains utility fuctions.
"""

from __future__ import division

version = "1.2.17svn"
latesturl = "http://nicotine-plus.sourceforge.net/LATEST"

import string
from UserDict import UserDict
from subprocess import Popen, PIPE
import os, dircache
import sys
import gobject

from logfacility import log as logfacility


win32 = sys.platform.startswith("win")
frame = 0
log = 0
language = ""

import gettext
tr_cache = {}

illegalpathchars = []
if win32:
	illegalpathchars += ["?", ":", ">", "<", "|", "*", '"']
illegafilechars = illegalpathchars + ["\\", "/"]
replacementchar = '_'

def CleanFile(filename):
	for char in illegafilechars:
		filename = filename.replace(char, replacementchar)
	return filename

def CleanPath(path, absolute=False):
	if win32:
		# Without hacks it is (up to Vista) not possible to have more
		# than 26 drives mounted, so we can assume a '[a-zA-Z]:\' prefix
		# for drives - we shouldn't escape that
		drive = ''
		if absolute and path[1:3] == ':\\' and path[0:1] and path[0].isalpha():
			drive = path[:3]
			path = path[3:]
		for char in illegalpathchars:
			path = path.replace(char, replacementchar)
		path = ''.join([drive, path])
		# Path can never end with a period on Windows machines
		path = path.rstrip('.')
	return path


def ChangeTranslation(lang):
	global language
	global tr_cache
	global langTranslation
	language = lang
	message = ""
	if language == "":
		langTranslation = gettext
		return
	try:
		langTranslation = gettext.translation('nicotine', languages=[language])
		langTranslation.install()
	except IOError, e:
		message = _("Translation not found for '%(language)s': %(error)s") % {'language':language, 'error':e}
		langTranslation = gettext
	except IndexError, e:
		message = _("Translation was corrupted for '%(language)s': %(error)s") % {'language':language, 'error':e}
		langTranslation = gettext
	else:
		# We need to force LC_ALL env variable to get buttons translated as well
		# On Windows we can't use os.environ, see pynicotine/libi18n.py
		if win32:
			import libi18n
			libi18n._putenv('LC_ALL',language)
			del libi18n
		# The Unix part is quite funny too...
		else:
			import locale
			# Let's try to force the locale with the right lang
			# locale.normalize will return bla_BLA.USUAL_ENCODINGS, so we first want to try to use unicode
			try:
				locale.setlocale(locale.LC_ALL, locale.normalize(language).split('.')[0]+'.UTF-8')
			except locale.Error, e:
				# If it fails we'll trust normalize() and use its encoding
				try:
					locale.setlocale(locale.LC_ALL, locale.normalize(language))
				# Sorry, please generate the right locales
				except locale.Error, e:
					message = _("Force lang failed: '%(language)s' (%(second)s and %(third)s tested)" ) % {'language':e, 'second':locale.normalize(language).split('.')[0]+'.UTF-8', 'third':locale.normalize(language)}
			del locale
	return message
ChangeTranslation(language)
# Translation Function
def _(s):
	global tr_cache
	global langTranslation
	# Don't translate empty strings
	# Poedit uses empty strings as metadata
	if s == "": return s
	if s not in tr_cache:
		tr_cache[s] = langTranslation.gettext(s)
	return tr_cache[s]

def getServerList(url):
	""" Parse server text file from http://www.slsk.org and 
	return a list of servers """
	import urllib, string
	try:
		f = urllib.urlopen(url)
		list = [string.strip(i) for i in f.readlines()]
	except:
		return []
	try:
		list = list[list.index("--servers")+1:]
	except:
		return []
	list = [string.split(i,":",2) for i in list]
	try:
		return [[i[0],i[2]]  for i in list]
	except:
		return []

def displayTraceback(exception=None):
	global log
	import traceback
	if exception is None:
		tb = traceback.format_tb(sys.exc_info()[2])
	else:
		tb = traceback.format_tb(exception)
	if log: log("Traceback: "+ str(sys.exc_info()[0].__name__) + ": "+str(sys.exc_info()[1]))
	for line in tb:
		if type(line) is tuple:
			xline = ""
			for item in line:
				xline += str(item) + " "
			line = xline

		line = line.strip("\n")
		if log:
			log(line)

	traceback.print_exc()

## Dictionary that's sorted alphabetically
# @param UserDict dictionary to be alphabetized
class SortedDict(UserDict):
	## Constructor
	# @param self SortedDict
	def __init__(self):
		self.__keys__ = []
		self.__sorted__ = True
		UserDict.__init__(self)
		
	## Set key
	# @param self SortedDict
	# @param key dict key
	# @param value dict value
	def __setitem__(self, key, value):
		if not self.__dict__.has_key(key):
			self.__keys__.append(key) 
			self.__sorted__ = False   
		UserDict.__setitem__(self, key, value)
	## Delete key
	# @param self SortedDict
	# @param key dict key
	def __delitem__(self, key):
		self.__keys__.remove(key)
		UserDict.__delitem__(self, key)
	## Get keys
	# @param self SortedDict
	# @return __keys__ 
	def keys(self):
		if not self.__sorted__:
			self.__keys__.sort()
			self.__sorted__ = True
		return self.__keys__
	## Get items
	# @param self SortedDict
	# @return list of keys and items
	def items(self):
		if not self.__sorted__:
			self.__keys__.sort()
			self.__sorted__ = True
		for key in self.__keys__:
			yield key, self[key]

def executeCommand(command, replacement=None, background=True, returnoutput=False, placeholder='$'):
	"""Executes a string with commands, with partial support for bash-style quoting and pipes
	
	The different parts of the command should be separated by spaces, a double
	quotation mark can be used to embed spaces in an argument. Pipes can be created
	using the bar symbol (|).

	If background is false the function will wait for all the launches processes to end
	before returning.

	If the 'replacement' argument is given, every occurance of 'placeholder'
	will be replaced by 'replacement'.
	
	If the command ends with the ampersand symbol background will be set to True. This should
	only be done by the request of the user, if you want background to be true set the function
	argument.

	The only expected error to be thrown is the RuntimeError in case something goes wrong
	while executing the command.

	Example commands:
	* "C:\Program Files\WinAmp\WinAmp.exe" --xforce "--title=My Window Title" 
	* mplayer $
	* echo $ | flite -t """
	# Example command: "C:\Program Files\WinAmp\WinAmp.exe" --xforce "--title=My Title" $ | flite -t
	if returnoutput:
		background = False
	command = command.strip()
	if command.endswith("&"):
		command = command[:-1]
		if returnoutput:
			print "Yikes, I was asked to return output but I'm also asked to launch the process in the background. returnoutput gets precedent."
		else:
			background = True
	unparsed = command
	arguments = []
	while unparsed.count('"') > 1:
		(pre, argument, post) = unparsed.split('"', 2)
		if pre:
			arguments += pre.rstrip(' ').split(' ')
		arguments.append(argument)
		unparsed = post.lstrip(' ')
	if unparsed:
		arguments += unparsed.split(' ')
	# arguments is now: ['C:\Program Files\WinAmp\WinAmp.exe', '--xforce', '--title=My Title', '$', '|', 'flite', '-t']
	subcommands = []
	current = []
	for argument in arguments:
		if argument in ('|',):
			subcommands.append(current)
			current = []
		else:
			current.append(argument)
	subcommands.append(current)
	# subcommands is now: [['C:\Program Files\WinAmp\WinAmp.exe', '--xforce', '--title=My Title', '$'], ['flite', '-t']]
	if replacement:
		for i in xrange(0, len(subcommands)):
			subcommands[i] = [x.replace(placeholder, replacement) for x in subcommands[i]]
	# Chaining commands...
	finalstdout = None
	if returnoutput:
		finalstdout = PIPE
	procs = []
	try:
		if len(subcommands) == 1: # no need to fool around with pipes
			procs.append(Popen(subcommands[0], stdout=finalstdout))
		else:
			procs.append(Popen(subcommands[0], stdout=PIPE))
			for subcommand in subcommands[1:-1]:
				procs.append(Popen(subcommand, stdin=procs[-1].stdout, stdout=PIPE))
			procs.append(Popen(subcommands[-1], stdin=procs[-1].stdout, stdout=finalstdout))
		if not background and not returnoutput:
			procs[-1].wait()
	except:
		raise RuntimeError("Problem while executing command %s (%s of %s)" % (subcommands[len(procs)], len(procs)+1, len(subcommands)))
	if not returnoutput:
		return True
	return procs[-1].communicate()[0]

def findBestEncoding(bytes, encodings, fallback=None):
	"""Tries to convert the bytes with the encodings, the first successful conversion is returned.
	
	If none match the fallback encoding will be used with the 'replace' argument. If no fallback is
	given the first encoding from the list is used."""
	for encoding in encodings:
		try:
			return unicode(bytes, encoding)
		except (UnicodeDecodeError, LookupError), e:
			pass
	# None were successful
	if fallback:
		return unicode(bytes, fallback, 'replace')
	else:
		return unicode(bytes, encodings[0], 'replace')

def strace(function):
	"""Decorator for debugging"""
	from itertools import chain
	def newfunc(*args, **kwargs):
		name = function.__name__
		print("%s(%s)" % (name, ", ".join(map(repr, chain(args, kwargs.values())))))
		retvalue = function(*args, **kwargs)
		print("%s(%s): %s" % (name, ", ".join(map(repr, chain(args, kwargs.values()))), repr(retvalue)))
		return retvalue
	return newfunc

