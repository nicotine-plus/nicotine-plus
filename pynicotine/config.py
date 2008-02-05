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
# Previous copyright below
# Copyright (c) 2003-2004 Hyriand. All rights reserved.
#
# Based on code from PySoulSeek, original copyright note:
# Copyright (c) 2001-2003 Alexander Kanavin. All rights reserved.

"""
This module contains configuration classes for Nicotine.
"""

import ConfigParser
import string
import os, time
import cPickle, bz2
import shelve
import sys
import thread

from utils import _

class Config:
	""" 
	This class holds configuration information and provides the 
	following methods:
	
	needConfig() - returns true if configuration information is incomplete
	readConfig() - reads configuration information from ~/.nicotine/config
	setConfig(config_info_dict) - sets configuration information
	writeConfig - writes configuration information to ~/.nicotine/config
	
	The actual configuration information is stored as a two-level dictionary.
	First-level keys are config sections, second-level keys are config 
	parameters.
	"""
	def __init__(self, filename):
		self.config_lock = thread.allocate_lock()
		self.config_lock.acquire()
		self.frame = None
		self.filename = filename
		self.parser = ConfigParser.ConfigParser()
		self.parser.read([self.filename])
		
		
		LOGDIR=os.path.join(self.filename.rsplit(os.sep, 1)[0], "logs")
		self.sections = {
"server":{ \
	"server": ('server.slsknet.org', 2240), \
	"login": None, \
	"passw": None, \
	"firewalled": 1,  \
	"ctcpmsgs": 0,  \
	"autosearch": [], \
	"autoreply": "", \
	"roomencoding": {}, \
	"userencoding": {}, \
	"portrange": (2234,2239), \
	"enc": "utf-8", \
	"userlist": [], \
	"banlist": [], \
	"ignorelist": [], \
	"ipblocklist":[], \
	"autojoin": ["nicotine"], \
	"autoaway":15, \
	}, \
\
"transfers":{ \
	"downloaddir": None, \
	"uploaddir": None, \
	"sharedownloaddir": 1, \
	"shared": None, \
	"buddyshared": [], \
	"uploadbandwidth": 10, \
	"uselimit": 0, \
	"uploadlimit": 150, \
	"preferfriends": 0, \
	"useupslots": 0, \
	"uploadslots": 2, \
	"incompletedir": "", \
	"shownotification": 0, \
	"afterfinish": "", \
	"afterfolder": "", \
	"lock": 1, \
	"fifoqueue": 0, \
	"usecustomban": 0, \
	"limitby": 1, \
	"customban": "Banned, don't bother retrying", \
	"queuelimit": 100, \
	"filelimit": 1000, \
	"friendsonly":0, \
	"friendsnolimits":0, \
	"enablebuddyshares": 0, \
	"enabletransferbuttons": 1, \
	"groupdownloads": 0, \
	"groupuploads": 1, \
	"geoblock": 0, \
	"geopanic": 0, \
	"geoblockcc": [""], \
	"remotedownloads": 1, \
	"uploadallowed": 2, \
	"autoclear_uploads": 0, \
	"autoretry_downloads": 0, \
	"downloads":[], \
	"sharedfiles":{}, \
	"sharedfilesstreams":{}, \
	"uploadsinsubdirs": 1, \
	"wordindex":{}, \
	"fileindex":{}, \
	"sharedmtimes":{}, \
	"bsharedfiles":{}, \
	"bsharedfilesstreams":{}, \
	"bwordindex":{}, \
	"bfileindex":{}, \
	"bsharedmtimes":{}, \
	"rescanonstartup":0, \
	"enablefilters": 1, \
	"downloadregexp": "", \
	"downloadfilters": [["desktop.ini",1], ["folder.jpg", 1], ["*.url", 1], ["thumbs.db", 1], \
		["albumart(_{........-....-....-....-............}_)?(_?(large|small))?\.jpg", 0]]}, \
\
"userinfo":{ \
	"descr": "''", \
	"pic":"", \
	"descrutf8": 0, \
	}, \
\
"language":{ \
	"setlanguage": 0, \
	"language": "", \
	},
\
"words": { \
	"censored": [], \
	"autoreplaced": {"teh ": "the ", "taht ": "that ", "tihng": "thing", "youre": "you're", "jsut": "just", "thier": "their", "tihs": "this"},  \
	"censorfill": "*", \
	"censorwords": False, \
	"replacewords": False, \
	"tab": True, \
	"dropdown": True, \
	"characters": 2, \
	"roomnames": True, \
	"buddies": True, \
	"roomusers": True, \
	"commands": True, \
	"aliases": True, \
	"onematch": True, \
	}, \
\
"logging": { \
	"logcollapsed": 0, \
	"logsdir": os.path.expanduser(LOGDIR), \
	"rooms_timestamp": "%H:%M:%S", \
	"private_timestamp": "%Y-%m-%d %H:%M:%S", \
	"log_timestamp": "%Y-%m-%d %H:%M:%S", \
	"timestamps": 1, \
	"privatechat":0, \
	"chatrooms":0, \
	"transfers":0, \
	"roomlogsdir": os.path.expanduser(os.path.join(LOGDIR, "rooms")), \
	"privatelogsdir": os.path.expanduser(os.path.join(LOGDIR, "private")), \
	"readroomlogs": 1, \
	"readroomlines": 15, \
	"readprivatelines": 15, \
	}, \
\
"privatechat":{ \
	"store": 0,
	"users":[], \
	}, \
\
"columns":{ \
	"userlist":[1,1,1,1,1,1,1,1,1,1], \
	"chatrooms":{}, \
	"downloads":[1,1,1,1,1,1,1,1,1], \
	"uploads":[1,1,1,1,1,1,1,1,1], \
	"search":[1,1,1,1,1,1,1,1,1,1,1], \
	"hideflags": False, \
	 }, \
\
"searches":{ \
	"maxresults": 50,
	"re_filter": 0, \
	"history": [], \
	"enablefilters": 0, \
	 "defilter":["","","","",0,""], \
	 "filtercc":[], \
	"reopen_tabs": 1, \
	"filterin":[], \
	"filterout":[], \
	"filtersize":[], \
	"filterbr":[], \
	"distrib_timer": 0, \
	"distrib_ignore": 60, \
	}, \
\
"ui":{ \
	"icontheme": "", \
	"chatme":"FOREST GREEN", \
	"chatremote": "", \
	"chatlocal":"BLUE", \
	"chathilite":"red", \
	"urlcolor": "#3D2B7F", \
	"useronline":"BLACK", \
	"useraway":"ORANGE", \
	"useroffline":"#aa0000", \
	"tab_colors": 0, \
	"tab_default":"", \
	"tab_hilite":"red", \
	"tab_changed":"#0000ff", \
	"usernamehotspots":1, \
	"usernamestyle": "bold", \
	"textbg": "", \
	"search":"", \
	"searchq":"GREY", \
	"inputcolor":"", \
	"spellcheck": 1, \
	"exitdialog": 1, \
	"notexists": 1, \
	"tabmain": "top", \
	"tabrooms": "top", \
	"tabprivate": "top", \
	"tabinfo": "top", \
	"tabbrowse": "top", \
	"tabsearch": "top", \
	"tab_icons": 1, \
	"chat_hidebuttons": 0, \
	"labelmain": 0, \
	"labelrooms": 0, \
	"labelprivate": 0, \
	"labelinfo": 0, \
	"labelbrowse": 0, \
	"labelsearch": 0,\
	"decimalsep":",", \
	"chatfont": "", \
	"roomlistcollapsed": 0, \
	"tabclosers": 1, \
	"searchfont": "", \
	"listfont": "", \
	"browserfont": "", \
	"transfersfont": "", \
	"searchoffline":"#aa0000", \
	"showaway": 0, \
	"tooltips": 1, \
	"buddylistinchatrooms": 0, \
	"trayicon": 1, \
	"soundenabled": 1, \
	"soundtheme": "", \
	"soundcommand": "play -q", \
	"filemanager": "rox $", \
	"enabletrans": 0, \
	"speechenabled": 0, \
	"speechprivate": "%(user)s told you.. %(message)s", \
	"speechrooms": "In %(room)s, %(user)s said %(message)s", \
	"speechcommand": "flite -t \"%s\"", \
	"transtint": "#aaaaaa", \
	"transalpha": 150, \
	"transfilter": 0x00000000L, \
	"width": 800, \
	"height": 600, \
	}, \
\
"private_rooms": { \
	"membership": [], \
	"owned": [], \
	"enabled": 0, \
	}, \
\
"urls":{
	"urlcatching":1, \
	"protocols":{"http":"firefox \"%s\"", "https":"firefox \"%s\""}, \
	"humanizeurls":1, \
	}, \
\
"interests": { \
	"likes":[], \
	"dislikes":[], \
	}, \
\
"ticker": { \
	"default": "", \
	"rooms": {}, \
	"hide": 0, \
	}, \
\
"players": { \
	"default": "xmms -e $", \
	"npothercommand": "", \
	"npplayer": "infopipe", \
 	"npformatlist": [], \
	 "npformat": "" \
	} \
}
		self.defaults = {}
		for key, value in self.sections.items():
			if type(value) is dict:
				if key not in self.defaults.keys():
					self.defaults[key] = {}
				
				for key2, value2 in value.items():
					self.defaults[key][key2] = value2
			else:
				self.defaults[key] = value
		try:
			f = open(filename+".alias")
			self.aliases = cPickle.load(f)
			f.close()
		except:
			self.aliases = {}
		self.config_lock.release()
    
    
	def needConfig(self):
		errorlevel = 0
		try:
			for i in self.sections.keys():
				for j in self.sections[i].keys():
			# 		print self.sections[i][j]
					if type(self.sections[i][j]) not in [type(None), type("")]:
						continue
					if self.sections[i][j] is None or self.sections[i][j] == '' and i not in ("userinfo", "ui", "ticker", "players", "language") and j not in ("incompletedir", "autoreply", 'afterfinish', 'afterfolder', 'geoblockcc', 'downloadregexp', "language"):
						# Repair options set to None with defaults
						if self.sections[i][j] is None and self.defaults[i][j] is not None:
							self.sections[i][j] = self.defaults[i][j]
							self.frame.logMessage(_("Config option reset to default: Section: %s, Option: %s, to: %s") % (i, j, self.sections[i][j]))
							if errorlevel == 0:
								errorlevel = 1
						else:
							if errorlevel < 2:
								self.frame.logMessage(_("You need to configure your settings (Server, Username, Password, Download Directory) before connecting..."))
								errorlevel = 2
							
							self.frame.logMessage(_("Config option unset: Section: %s, Option: %s") % (i, j))
							self.frame.settingswindow.InvalidSettings(i, j)
			
		except Exception, error:
			message = _("Config error: %s") % error
			self.frame.logMessage(message)
			if errorlevel < 3:
				errorlevel = 3
		if errorlevel > 1:
			self.frame.settingswindow.SetSettings(self.sections)
		return errorlevel

	def readConfig(self):
		self.config_lock.acquire()
		path, fn = os.path.split(self.filename)
		try:
			if not os.path.isdir(path):
				os.makedirs(path)
		except OSError, msg:
			message = "Can't create directory '%s', reported error: %s" % (path, msg)
			print message
			if self.frame:
				self.frame.logMessage(message)
		
		for i in self.parser.sections():
			for j in self.parser.options(i):
				val = self.parser.get(i, j, raw = 1)
				if i not in self.sections.keys():
					message = "Unknown config section:", i
					print message
					if self.frame:
						self.frame.logMessage(message)
				elif j not in self.sections[i].keys() and j != "filter":
					message = "Unknown config option '%s' in section '%s'" %(j, i)
					print message
					if self.frame:
						self.frame.logMessage(message)
				elif j in ['login','passw','enc',  'downloaddir', 'uploaddir', 'customban','descr','pic','logsdir','roomlogsdir','privatelogsdir','incompletedir', 'autoreply', 'afterfinish', 'downloadregexp', 'afterfolder', 'default', 'chatfont', "npothercommand", "npplayer", "npformat", "private_timestamp", "rooms_timestamp", "log_timestamp"] or (i == "ui" and j not in ["roomlistcollapsed", "tabclosers", "tab_colors", 'buddylistinchatrooms', "trayicon", "showaway", "tooltips", "usernamehotspots", "exitdialog", "tab_icons", "spellcheck", "chat_hidebuttons", "notexists", "soundenabled", "transalpha",  "enabletrans", "speechenabled", "enablefilters",  "width", "height", "labelmain", "labelrooms", "labelprivate", "labelinfo", "labelbrowse", "labelsearch"]) or (i == "words" and j not in ["completion", "censorwords", "replacewords", "autoreplaced", "censored", "characters", "tab", "dropdown", "roomnames", "buddies", "roomusers", "commands", "aliases", "onematch"]) or (i == "language" and j not in ["definelanguage", "setlanguage"]):

					if val is not None and val != "None":
						self.sections[i][j] = val
					else:
						self.sections[i][j] = None
				else:
					try:
						self.sections[i][j] = eval(val, {})
					except:
						self.sections[i][j] = None
						message = "CONFIG ERROR: Couldn't decode %s section %s value %s" % (str(j), str(i), str(val))
						print message
						if self.frame:
							self.frame.logMessage(message)
		autojoin = self.sections["server"]["autojoin"]
		# Old config file format
		for user in self.sections["server"]["userlist"]:
			if len(user) == 2: 
				user += [0, 0, 0, "", ""]
		if len(self.sections["columns"]["userlist"]) < len(self.defaults["columns"]["userlist"]):
			self.sections["columns"]["userlist"] += [True] * (len(self.defaults["columns"]["userlist"]) - len(self.sections["columns"]["userlist"]))
			
		for i in ["%(user)s", "%(message)s"]:
			if i not in self.sections["ui"]["speechprivate"]:
				self.sections["ui"]["speechprivate"] = self.defaults["ui"]["speechprivate"]
			if i not in self.sections["ui"]["speechrooms"]:
				self.sections["ui"]["speechrooms"] = self.defaults["ui"]["speechrooms"]
				
		if "pyslsk" in autojoin and not "nicotine" in autojoin:
			autojoin.append("nicotine")
		
		# decode the userinfo from local encoding to utf8 (1.0.3 -> 1.0.4 change)
		if not self.sections["userinfo"]["descrutf8"]:
			try:
				import locale
				descr = eval(self.sections["userinfo"]["descr"], {}).decode(locale.nl_langinfo(locale.CODESET), "replace").encode("utf-8", "replace")
				self.sections["userinfo"]["descr"] = descr.__repr__()
			except:
				pass
			self.sections["userinfo"]["descrutf8"] = 1
			
		sharedfiles = None
		bsharedfiles = None
		sharedfilesstreams = None
		bsharedfilesstreams = None
		wordindex = None
		bwordindex = None
		fileindex = None
		bfileindex = None
		sharedmtimes = None
		bsharedmtimes = None
		
		try:
			sharedfiles = shelve.open(self.filename+".files.db")
			bsharedfiles = shelve.open(self.filename+".buddyfiles.db")
			sharedfilesstreams =shelve.open(self.filename+".streams.db")
			bsharedfilesstreams =shelve.open(self.filename+".buddystreams.db")
			wordindex = shelve.open(self.filename+".wordindex.db")
			bwordindex = shelve.open(self.filename+".buddywordindex.db")
			fileindex = shelve.open(self.filename+".fileindex.db")
			bfileindex = shelve.open(self.filename+".buddyfileindex.db")
			sharedmtimes = shelve.open(self.filename+".mtimes.db")
			bsharedmtimes = shelve.open(self.filename+".buddymtimes.db")
		except:
			message = _("Shared files database seems to be corrupted, rescan your shares")
			print message
			if self.frame:
				self.frame.logMessage(message)
			files = self.clearShares(sharedfiles, bsharedfiles, sharedfilesstreams, bsharedfilesstreams, wordindex, bwordindex, fileindex, bfileindex, sharedmtimes, bsharedmtimes)
			if files is not None:
				sharedfiles, bsharedfiles, sharedfilesstreams, bsharedfilesstreams, wordindex, bwordindex, fileindex, bfileindex, sharedmtimes, bsharedmtimes = files
			
		self.sections["transfers"]["sharedfiles"] = sharedfiles
		self.sections["transfers"]["sharedfilesstreams"] = sharedfilesstreams
		self.sections["transfers"]["wordindex"] = wordindex
		self.sections["transfers"]["fileindex"] = fileindex
		self.sections["transfers"]["sharedmtimes"] = sharedmtimes
		
		self.sections["transfers"]["bsharedfiles"] = bsharedfiles
		self.sections["transfers"]["bsharedfilesstreams"] = bsharedfilesstreams
		self.sections["transfers"]["bwordindex"] = bwordindex
		self.sections["transfers"]["bfileindex"] = bfileindex
		self.sections["transfers"]["bsharedmtimes"] = bsharedmtimes
			
		if self.sections["server"]["server"][0] == "mail.slsknet.org":
			self.sections["server"]["server"] = ('server.slsknet.org', 2240)
		
		self.config_lock.release()
		
	def clearShares(self, sharedfiles, bsharedfiles, sharedfilesstreams, bsharedfilesstreams, wordindex, bwordindex, fileindex, bfileindex, sharedmtimes, bsharedmtimes):
		try:
			if sharedfiles:
				sharedfiles.close()
			try:
				os.unlink(self.filename+'.files.db')
			except:
				pass
			sharedfiles = shelve.open(self.filename+".files.db", flag='n')
			if bsharedfiles:
				bsharedfiles.close()
			try:
				os.unlink(self.filename+'.buddyfiles.db')
			except:
				pass
			bsharedfiles = shelve.open(self.filename+".buddyfiles.db", flag='n')
		
			if sharedfilesstreams:
				sharedfilesstreams.close()
			try:
				os.unlink(self.filename+'.streams.db')
			except:
				pass
			sharedfilesstreams =shelve.open(self.filename+".streams.db", flag='n')
			if bsharedfilesstreams:
				bsharedfilesstreams.close()
			try:
				os.unlink(self.filename+'.buddystreams.db')
			except:
				pass
			bsharedfilesstreams =shelve.open(self.filename+".buddystreams.db", flag='n')
		
			if wordindex:
				wordindex.close()
			try:
				os.unlink(self.filename+'.wordindex.db')
			except:
				pass
			wordindex = shelve.open(self.filename+".wordindex.db", flag='n')
			if bwordindex:
				bwordindex.close()
			try:
				os.unlink(self.filename+'.buddywordindex.db')
			except:
				pass
			bwordindex = shelve.open(self.filename+".buddywordindex.db", flag='n')
		
			if fileindex:
				fileindex.close()
			try:
				os.unlink(self.filename+'.fileindex.db')
			except:
				pass
			fileindex = shelve.open(self.filename+".fileindex.db", flag='n')
			if bfileindex:
				bfileindex.close()
			try:
				os.unlink(self.filename+'.buddyfileindex.db')
			except:
				pass
			bfileindex = shelve.open(self.filename+".buddyfileindex.db", flag='n')
		
			if sharedmtimes:
				sharedmtimes.close()
			try:
				os.unlink(self.filename+'.mtimes.db')
			except:
				pass
			sharedmtimes = shelve.open(self.filename+".mtimes.db", flag='n')
			if bsharedmtimes:
				bsharedmtimes.close()
			try:
				os.unlink(self.filename+'.buddymtimes.db')
			except:
				pass
			bsharedmtimes = shelve.open(self.filename+".buddymtimes.db", flag='n')
		except Exception, error:
			message = _("Error while writing database files: %s") % error
			print message
			if self.frame:
				self.frame.logMessage(message)
			return None
		return sharedfiles, bsharedfiles, sharedfilesstreams, bsharedfilesstreams, wordindex, bwordindex, fileindex, bfileindex, sharedmtimes, bsharedmtimes
			
	def writeConfig(self):
		self.config_lock.acquire()
		for i in self.sections.keys():
			if not self.parser.has_section(i):
				self.parser.add_section(i)
			for j in self.sections[i].keys():
				if j not in ["sharedfiles", "sharedfilesstreams", "wordindex", "fileindex", "sharedmtimes", "bsharedfiles", "bsharedfilesstreams", "bwordindex", "bfileindex", "bsharedmtimes"]:
					self.parser.set(i, j, self.sections[i][j])
				else:
					self.parser.remove_option(i, j)
	
		path, fn = os.path.split(self.filename)
		try:
			if not os.path.isdir(path):
				os.makedirs(path)
		except OSError, msg:
			message = _("Can't create directory '%(path)s', reported error: %(error)s") % {'path':path, 'error':msg}
			print message
			if self.frame:
				self.frame.logMessage(message)
		
		oldumask = os.umask(0077)
	
		try:
			f = open(self.filename + ".new", "w")
		except IOError, e:
			message = _("Can't save config file, I/O error: %s") % e
			print message
			if self.frame:
				self.frame.logMessage(message)
			return
		else:
			try:
				self.parser.write(f)
			except IOError, e:
				message = _("Can't save config file, I/O error: %s") % e
				print message
				if self.frame:
					self.frame.logMessage(message)
				return
			else:
				f.close()
		os.umask(oldumask)
		# A paranoid precaution since config contains the password
		try:
			os.chmod(self.filename, 0600)
		except:
			pass
	
		try:
			s = os.stat(self.filename)
			if s.st_size > 0:
				try:
					if os.path.exists(self.filename + ".old"):
						os.remove(self.filename + ".old")
				except OSError, error:
					message = _("Can't remove %s" % self.filename + ".old")
					print message
					if self.frame:
						self.frame.logMessage(message)
		
				try:
					os.rename(self.filename, self.filename + ".old")
				except OSError, error:
					message = _("Can't back config file up, error: %s") % error
					print message
					if self.frame:
						self.frame.logMessage(message)
		except OSError:
			pass
	
		try:
			os.rename(self.filename + ".new", self.filename)
		except OSError, error:
			message = _("Can't rename config file, error: %s") % error
			print message
			if self.frame:
				self.frame.logMessage(message)
	
		self.config_lock.release()
	
	def writeConfigBackup(self, filename=None):
		
		self.config_lock.acquire()
		
		if filename is None:
			filename = "%s backup %s.tar.bz2" %(self.filename, time.strftime("%Y-%m-%d %H:%M:%S") )
		else:
			if filename[-8:-1] != ".tar.bz2":
				filename += ".tar.bz2"
		try:
			if os.path.exists(filename):
				raise "File %s exists" % filename
			import tarfile
			tar = tarfile.open(filename, "w:bz2")
			if not os.path.exists(self.filename):
				raise "Config file missing"
			tar.add(self.filename)
			if os.path.exists(self.filename+".alias"):
				tar.add(self.filename+".alias")

			tar.close()
		except Exception, e:
			print e
			self.config_lock.release()
			return (1, "Cannot write backup archive")
		self.config_lock.release()
		return (0, filename)
	
	def setBuddyShares(self, files, streams, wordindex, fileindex, mtimes):
		if self.sections["transfers"]["bsharedfiles"] == files:
			return
		self.config_lock.acquire()
		self.sections["transfers"]["bsharedfiles"].close()
		self.sections["transfers"]["bsharedfilesstreams"].close()
		self.sections["transfers"]["bsharedmtimes"].close()
		self.sections["transfers"]["bwordindex"].close()
		self.sections["transfers"]["bfileindex"].close()
		
		self.sections["transfers"]["bsharedfiles"] = shelve.open(self.filename+".buddyfiles.db",'n')
		self.sections["transfers"]["bsharedfilesstreams"] = shelve.open(self.filename+".buddystreams.db",'n')
		self.sections["transfers"]["bsharedmtimes"] = shelve.open(self.filename+".buddymtimes.db",'n')
		self.sections["transfers"]["bwordindex"] = shelve.open(self.filename+".buddywordindex.db",'n')
		self.sections["transfers"]["bfileindex"] = shelve.open(self.filename+".buddyfileindex.db",'n')
		
		for (i, j) in files.items():
			self.sections["transfers"]["bsharedfiles"][i] = j
		for (i, j) in streams.items():
			self.sections["transfers"]["bsharedfilesstreams"][i] = j
		for (i, j) in mtimes.items():
			self.sections["transfers"]["bsharedmtimes"][i] = j
		for (i, j) in wordindex.items():
			self.sections["transfers"]["bwordindex"][i] = j
		for (i, j) in fileindex.items():
			self.sections["transfers"]["bfileindex"][i] = j
		self.config_lock.release()
		
	def setShares(self, files, streams, wordindex, fileindex, mtimes):
		if self.sections["transfers"]["sharedfiles"] == files:
			return
		
		self.config_lock.acquire()
		self.sections["transfers"]["sharedfiles"].close()
		self.sections["transfers"]["sharedfilesstreams"].close()
		self.sections["transfers"]["sharedmtimes"].close()
		self.sections["transfers"]["wordindex"].close()
		self.sections["transfers"]["fileindex"].close()
		self.sections["transfers"]["sharedfiles"] = shelve.open(self.filename+".files.db",'n')
		self.sections["transfers"]["sharedfilesstreams"] = shelve.open(self.filename+".streams.db",'n')
		self.sections["transfers"]["sharedmtimes"] = shelve.open(self.filename+".mtimes.db",'n')
		self.sections["transfers"]["wordindex"] = shelve.open(self.filename+".wordindex.db",'n')
		self.sections["transfers"]["fileindex"] = shelve.open(self.filename+".fileindex.db",'n')
	
		for (i, j) in files.items():
			self.sections["transfers"]["sharedfiles"][i] = j
		for (i, j) in streams.items():
			self.sections["transfers"]["sharedfilesstreams"][i] = j
		for (i, j) in mtimes.items():
			self.sections["transfers"]["sharedmtimes"][i] = j
		for (i, j) in wordindex.items():
			self.sections["transfers"]["wordindex"][i] = j
		for (i, j) in fileindex.items():
			self.sections["transfers"]["fileindex"][i] = j
	
		self.config_lock.release()

	def writeShares(self):
		self.config_lock.acquire()
		self.sections["transfers"]["sharedfiles"].sync()
		self.sections["transfers"]["sharedfilesstreams"].sync()
		self.sections["transfers"]["wordindex"].sync()
		self.sections["transfers"]["fileindex"].sync()
		self.sections["transfers"]["sharedmtimes"].sync()
		
		self.sections["transfers"]["bsharedfiles"].sync()
		self.sections["transfers"]["bsharedfilesstreams"].sync()
		self.sections["transfers"]["bwordindex"].sync()
		self.sections["transfers"]["bfileindex"].sync()
		self.sections["transfers"]["bsharedmtimes"].sync()
		self.config_lock.release()

	def pushHistory(self, history, text, max):
		if text in history:
			history.remove(text)
		elif len(history) >= max:
			del history[-1]
		history.insert(0, text)
		self.writeConfig()
	
	def writeAliases(self):
		self.config_lock.acquire()
		f = open(self.filename+".alias","w")
		cPickle.dump(self.aliases, f, 1)
		f.close()
		self.config_lock.release()

	def AddAlias(self, rest):
		if rest:
			args = rest.split(" ", 1)
			if len(args) == 2:
				if args[0] in ("alias", "unalias"):
					return "I will not alias that!\n"
				self.aliases[args[0]] = args[1]
				self.writeAliases()
			if args[0] in self.aliases:
				return "Alias %s: %s\n" % (args[0], self.aliases[args[0]])
			else:
				return _("No such alias (%s)") % rest + "\n"
		else:
			m = "\n" + _("Aliases:") + "\n"
			for i in self.aliases.keys():
				m = m + "%s: %s\n" % (i, self.aliases[i])
			return m+"\n"

	def Unalias(self, rest):
		if rest and rest in self.aliases:
			x = self.aliases[rest]
			del self.aliases[rest]
			self.writeAliases()
			return _("Removed alias %(alias)s: %(action)s\n") % {'alias':rest, 'action':x}
		else:
			return _("No such alias (%(alias)s)\n") % {'alias':rest}
