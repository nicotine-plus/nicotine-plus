# -*- coding: utf-8 -*-
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

from os.path import exists

from logfacility import log
from utils import _, findBestEncoding

class Config:
	""" 
	This class holds configuration information and provides the 
	following methods:
	
	needConfig() - returns true if configuration information is incomplete
	readConfig() - reads configuration information from ~/.nicotine/config
	setConfig(config_info_dict) - sets configuration information
	writeConfiguration - writes configuration information to ~/.nicotine/config
	writeDownloadQueue - writes download queue to ~/.nicotine/config.transfers.pickle
	writeConfig - calls writeConfiguration followed by writeDownloadQueue
	
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
"server":{
	"server": ('server.slsknet.org', 2242),
	"login": '',
	"passw": '',
	"serverlist": ["server.slsknet.org:2242", "server.slsknet.org:2240"],
	"firewalled": 1,
	"ctcpmsgs": 0,
	"autosearch": [],
	"autoreply": "",
	"roomencoding": {},
	"fallbackencodings": ['utf-8', 'cp1252'], # Put the multi-byte encodings up front - they are the most likely to err
	"userencoding": {},
	"portrange": (2234,2239),
	"upnp": False,
	"enc": "utf-8",
	"userlist": [],
	"banlist": [],
	"ignorelist": [],
	"ipignorelist":{},
	"ipblocklist":{"72.172.88.*":"MediaDefender Bots"},
	"autojoin": ["nicotine"],
	"autoaway":15,
	"private_chatrooms": 0,
	"lastportstatuscheck": 0,
},

"transfers":{
	"incompletedir": os.path.join(os.path.expanduser("~"),'.nicotine','incompletefiles'),
	"downloaddir": os.path.join(os.path.expanduser("~"), 'nicotine-downloads'),
	"uploaddir": os.path.join(os.path.expanduser("~"), 'nicotine-uploads'),
	"sharedownloaddir": 1,
	"shared": [],
	"buddyshared": [],
	"uploadbandwidth": 10,
	"uselimit": 0,
	"uploadlimit": 150,
	"downloadlimit": 0,
	"preferfriends": 0,
	"useupslots": 0,
	"uploadslots": 2,
	"shownotification": 0,
	"shownotificationperfolder": 0,
	"afterfinish": "",
	"afterfolder": "",
	"lock": 1,
	"reverseorder": 0,
	"prioritize": 0,
	"fifoqueue": 0,
	"usecustomban": 0,
	"limitby": 1,
	"customban": "Banned, don't bother retrying",
	"queuelimit": 100,
	"filelimit": 1000,
	"friendsonly":0,
	"friendsnolimits":0,
	"enablebuddyshares": 0,
	"enabletransferbuttons": 1,
	"groupdownloads": 0,
	"groupuploads": 1,
	"geoblock": 0,
	"geopanic": 0,
	"geoblockcc": [""],
	"remotedownloads": 1,
	"uploadallowed": 2,
	"autoclear_uploads": 0,
	"autoretry_downloads": 0,
	"downloads":[],
	"sharedfiles":{},
	"sharedfilesstreams":{},
	"uploadsinsubdirs": 1,
	"wordindex":{},
	"fileindex":{},
	"sharedmtimes":{},
	"lowercase": {},
	"bsharedfiles":{},
	"bsharedfilesstreams":{},
	"bwordindex":{},
	"bfileindex":{},
	"bsharedmtimes":{},
	"blowercase": {},
	"rescanonstartup":0,
	"enablefilters": 1,
	"downloadregexp": "",
	"downloadfilters": [["desktop.ini",1], ["folder.jpg", 1], ["*.url", 1], ["thumbs.db", 1],
		["albumart(_{........-....-....-....-............}_)?(_?(large|small))?\.jpg", 0]],
	"download_doubleclick": 1,
	"upload_doubleclick": 1,
	"downloadsexpanded": True,
	"uploadsexpanded": True,
},

"userinfo":{
	"descr": "''",
	"pic":"",
	"descrutf8": 0,
},

"language":{
	"setlanguage": 0,
	"language": "",
},

"words": {
	"censored": [],
	"autoreplaced": {"teh ": "the ", "taht ": "that ", "tihng": "thing", "youre": "you're", "jsut": "just", "thier": "their", "tihs": "this"},
	"censorfill": "*",
	"censorwords": False,
	"replacewords": False,
	"tab": True,
	"cycle": False,
	"dropdown": True,
	"characters": 2,
	"roomnames": True,
	"buddies": True,
	"roomusers": True,
	"commands": True,
	"aliases": True,
	"onematch": True,
},

"logging": {
	"debug": False,
	"debugmodes": [0, 1],
	"logcollapsed": 0,
	"logsdir": os.path.expanduser(LOGDIR),
	"rooms_timestamp": "%H:%M:%S",
	"private_timestamp": "%Y-%m-%d %H:%M:%S",
	"log_timestamp": "%Y-%m-%d %H:%M:%S",
	"timestamps": 1,
	"privatechat":0,
	"chatrooms":0,
	"transfers":0,
	"roomlogsdir": os.path.expanduser(os.path.join(LOGDIR, "rooms")),
	"privatelogsdir": os.path.expanduser(os.path.join(LOGDIR, "private")),
	"readroomlogs": 1,
	"readroomlines": 15,
	"readprivatelines": 15,
	"rooms": [],
},

"privatechat":{
	"store": 0,
	"users":[],
},

"columns":{
	"userlist":[1,1,1,1,1,1,1,1,1,1],
	"chatrooms":{},
	"downloads":[1,1,1,1,1,1,1,1,1],
	"uploads":[1,1,1,1,1,1,1,1,1],
	"search":[1,1,1,1,1,1,1,1,1,1,1],
	"hideflags": False,
},

"searches":{
	"maxresults": 50,
	"re_filter": 0,
	"history": [],
	"enablefilters": 0,
	 "defilter":["","","","",0,""],
	 "filtercc":[],
	"reopen_tabs": False,
	"filterin":[],
	"filterout":[],
	"filtersize":[],
	"filterbr":[],
	"distrib_timer": 0,
	"distrib_ignore": 60,
	"search_results": 1,
	"max_displayed_results": 500,
	"max_stored_results": 1500,
},

"ui":{
	"icontheme": "",
	"chatme":"FOREST GREEN",
	"chatremote": "",
	"chatlocal":"BLUE",
	"chathilite":"red",
	"urlcolor": "#3D2B7F",
	"useronline":"BLACK",
	"useraway":"ORANGE",
	"useroffline":"#aa0000",
	"usernamehotspots":1,
	"usernamestyle": "bold",
	"textbg": "",
	"search":"",
	"searchq":"GREY",
	"inputcolor":"",
	"spellcheck": 1,
	"exitdialog": 1,
	"mozembed": 0,
	"open_in_mozembed": 0,
	"notexists": 1,
	"tab_colors": 0,
	"tab_default":"",
	"tab_hilite":"red",
	"tab_changed":"#0000ff",
	"tab_reorderable": 1,
	"tabmain": "top",
	"tabrooms": "top",
	"tabprivate": "top",
	"tabinfo": "top",
	"tabbrowse": "top",
	"tabsearch": "top",
	"tab_icons": 1,
	"tab_status_icons": 1,
	"chat_hidebuttons": 0,
	"labelmain": 0,
	"labelrooms": 0,
	"labelprivate": 0,
	"labelinfo": 0,
	"labelbrowse": 0,
	"labelsearch": 0,
	"decimalsep":",",
	"chatfont": "",
	"roomlistcollapsed": 0,
	"tabclosers": 1,
	"searchfont": "",
	"listfont": "",
	"browserfont": "",
	"transfersfont": "",
	"modes_visible": {"chatrooms":1, "private":1, "downloads":1, "uploads":1, "search":1, "userinfo":1, "userbrowse":1, "interests":1},
	"modes_order": ["chatrooms", "private", "downloads", "uploads", "search", "userinfo", "userbrowse", "interests", "userlist"],
	"searchoffline":"#aa0000",
	"showaway": 0,
	"tooltips": 1,
	"buddylistinchatrooms": 0,
	"trayicon": 1,
	"soundenabled": 1,
	"soundtheme": "",
	"soundcommand": "play -q",
	"filemanager": "xdg-open $",
	"enabletrans": 0,
	"speechenabled": 0,
	"speechprivate": "%(user)s told you.. %(message)s",
	"speechrooms": "In %(room)s, %(user)s said %(message)s",
	"speechcommand": "flite -t $",
	"transtint": "#aaaaaa",
	"transalpha": 150,
	"transfilter": 0x00000000L,
	"width": 800,
	"height": 600,
	"xposition": -1,
	"yposition": -1,
	"urgencyhint": True,
},

"private_rooms": {
	"rooms": {},
	"enabled": 0,
},

"urls":{
	"urlcatching":1,
	"protocols":{"http":"", "https":""},
	"humanizeurls":1,
},

"interests": {
	"likes":[],
	"dislikes":[],
},

"ticker": {
	"default": "",
	"rooms": {},
	"hide": 0,
},

"players": {
	"default": "xdg-open $",
	"npothercommand": "",
	"npplayer": "infopipe",
	"npformatlist": [],
	"npformat": ""
},
"plugins": {"enable": 1, "enabled": []},
}
		# OS Specific settings
		if sys.platform == 'darwin':
			self.sections["urls"]["protocols"] = {"http":"open -a Safari $", "https":"open -a Safari $"}
		if sys.platform.startswith('win'):
			self.sections['ui']['filemanager'] = 'explorer $'
			self.sections['transfers']['incompletedir'] = os.path.join(os.environ['APPDATA'], 'nicotine', 'incompletefiles')
			self.sections['transfers']['downloaddir'] = os.path.join(os.environ['APPDATA'], 'nicotine', 'uploads')
			self.sections['transfers']['uploaddir'] = os.path.join(os.environ['APPDATA'], 'nicotine', 'uploads')
		self.defaults = {}
		for key, value in self.sections.items():
			if type(value) is dict:
				if key not in self.defaults:
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
							self.frame.logMessage(_("Config option reset to default: Section: %(section)s, Option: %(option)s, to: %(default)s") % {'section':i, 'option':j, 'default':self.sections[i][j]})
							if errorlevel == 0:
								errorlevel = 1
						else:
							if errorlevel < 2:
								self.frame.logMessage(_("You need to configure your settings (Server, Username, Password, Download Directory) before connecting..."))
								errorlevel = 2
							
							self.frame.logMessage(_("Config option unset: Section: %(section)s, Option: %(option)s") % {'section':i, 'option':j})
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

		self.sections['transfers']['downloads'] = []
		if exists(self.filename+'.transfers.pickle'):
			# <1.2.13 stored transfers inside the main config
			try:
				handle = open(self.filename+'.transfers.pickle')
			except IOError, inst:
				log.addwarning(_("Something went wrong while opening your transfer list: %(error)s") % {'error':str(inst)})
			else:
				try:
					self.sections['transfers']['downloads'] = cPickle.load(handle)
				except (IOError, EOFError, ValueError), inst:
					log.addwarning(_("Something went wrong while reading your transfer list: %(error)s") % {'error':str(inst)})
			try:
				handle.close()
			except:
				pass
		path, fn = os.path.split(self.filename)
		try:
			if not os.path.isdir(path):
				os.makedirs(path)
		except OSError, msg:
			log.addwarning("Can't create directory '%s', reported error: %s" % (path, msg))
		
		unknown1 = ['login','passw','enc',  'downloaddir', 'uploaddir', 'customban','descr','pic','logsdir','roomlogsdir','privatelogsdir','incompletedir', 'autoreply', 'afterfinish', 'downloadregexp', 'afterfolder', 'default', 'chatfont', "npothercommand", "npplayer", "npformat", "private_timestamp", "rooms_timestamp", "log_timestamp"]
		unknown2 = {
			'ui':["roomlistcollapsed", "tabclosers", "tab_colors", 'tab_reorderable', 'buddylistinchatrooms', "trayicon", "showaway", "tooltips", "usernamehotspots", "exitdialog", "tab_icons", "spellcheck", "modes_order", "modes_visible", "chat_hidebuttons", "tab_status_icons", "notexists", "mozembed", "open_in_mozembed", "soundenabled", "transalpha",  "enabletrans", "speechenabled", "enablefilters",  "width", "height", "xposition", "yposition", "labelmain", "labelrooms", "labelprivate", "labelinfo", "labelbrowse", "labelsearch"],
			'words':["completion", "censorwords", "replacewords", "autoreplaced", "censored", "characters", "tab", "cycle", "dropdown", "roomnames", "buddies", "roomusers", "commands", "aliases", "onematch"],
			'language':["definelanguage", "setlanguage"],
		}
		
		for i in self.parser.sections():
			for j in self.parser.options(i):
				val = self.parser.get(i, j, raw = 1)
				if i not in self.sections:
					log.addwarning("Unknown config section '%s'" % (i,))
				elif j not in self.sections[i] and not (j == "filter" or i in ('plugins',)):
					log.addwarning("Unknown config option '%s' in section '%s'" % (j, i))
				elif j in unknown1 or (i in unknown2 and j not in unknown2[i]):
					if val is not None and val != "None":
						self.sections[i][j] = val
					else:
						self.sections[i][j] = None
				else:
					try:
						self.sections[i][j] = eval(val, {})
					except:
						self.sections[i][j] = None
						log.addwarning("CONFIG ERROR: Couldn't decode '%s' section '%s' value '%s'" % (str(j), str(i), str(val)))
		autojoin = self.sections["server"]["autojoin"]
		# Old config file format
		for user in self.sections["server"]["userlist"]:
			if len(user) == 2: 
				user += [0, 0, 0, "", ""]
		if len(self.sections["columns"]["userlist"]) < len(self.defaults["columns"]["userlist"]):
			self.sections["columns"]["userlist"] += [True] * (len(self.defaults["columns"]["userlist"]) - len(self.sections["columns"]["userlist"]))

		self.removeOldOption("private_rooms", "membership")
		self.removeOldOption("private_rooms", "owned")



		if type(self.sections["server"]["ipblocklist"]) is list:
			ipblocklist = self.sections["server"]["ipblocklist"][:]
			self.sections["server"]["ipblocklist"] = {}
			for ip in ipblocklist:
				self.sections["server"]["ipblocklist"][ip] = ""
				
		for i in ["%(user)s", "%(message)s"]:
			if i not in self.sections["ui"]["speechprivate"]:
				self.sections["ui"]["speechprivate"] = self.defaults["ui"]["speechprivate"]
			if i not in self.sections["ui"]["speechrooms"]:
				self.sections["ui"]["speechrooms"] = self.defaults["ui"]["speechrooms"]
				
		# Replacing old style %s with new $
		try:
			self.sections["ui"]["speechcommand"] = self.sections["ui"]["speechcommand"].replace('%s','$')
		except KeyError:
			pass
		try:
			for (protocol, command) in self.sections["urls"]["protocols"].iteritems():
				self.sections["urls"]["protocols"][protocol] = command.replace('%s','$')
		except KeyError:
			pass
		if "pyslsk" in autojoin and not "nicotine" in autojoin:
			autojoin.append("nicotine")
		
		# If we stored any of the following as bytes (pre 1.2.15, pre 1.2.16), convert them to unicode
		unicodes = [('ticker','default'), ('server','autoreply')]
		for (section, subsection) in unicodes:
			try:
				self.sections[section][subsection] = findBestEncoding(self.sections[section][subsection], ['utf-8'])
			except TypeError:
				pass # Already unicode
		
		for room in self.sections["ticker"]["rooms"]:
			encodings = ['utf-8']
			try:
				encodings.append(self.sections["server"]["roomencoding"][room])
			except KeyError:
				pass
			try:
				self.sections["ticker"]["rooms"][room] = findBestEncoding(self.sections["ticker"]["rooms"][room], encodings)
			except TypeError:
				pass # already unicode
		# decode the userinfo from local encoding to utf8 (1.0.3 -> 1.0.4 change)
		if not self.sections["userinfo"]["descrutf8"]:
			try:
				import locale
				descr = eval(self.sections["userinfo"]["descr"], {}).decode(locale.nl_langinfo(locale.CODESET), "replace").encode("utf-8", "replace")
				self.sections["userinfo"]["descr"] = descr.__repr__()
			except:
				pass
			self.sections["userinfo"]["descrutf8"] = 1
		# Convert fs-based shared to virtual shared (pre 1.2.17)
		def _convert_to_virtual(x):
			if isinstance(x, tuple):
				return x
			virtual = x.replace('/', '_').replace('\\', '_').strip('_')
			log.addwarning("Renaming shared folder '%s' to '%s'. A rescan of your share is required." % (x, virtual))
			return (virtual, x)
		self.sections["transfers"]["shared"] = [_convert_to_virtual(x) for x in self.sections["transfers"]["shared"]]
		self.sections["transfers"]["buddyshared"] = [_convert_to_virtual(x) for x in self.sections["transfers"]["buddyshared"]]

		sharedfiles =         None
		bsharedfiles =        None
		sharedfilesstreams =  None
		bsharedfilesstreams = None
		wordindex =           None
		bwordindex =          None
		fileindex =           None
		bfileindex =          None
		sharedmtimes =        None
		bsharedmtimes =       None
		lowercase =           None
		blowercase =          None
		

		shelves = [
				self.filename + ".files.db",
				self.filename + ".buddyfiles.db",
				self.filename + ".streams.db",
				self.filename + ".buddystreams.db",
				self.filename + ".wordindex.db",
				self.filename + ".buddywordindex.db",
				self.filename + ".fileindex.db",
				self.filename + ".buddyfileindex.db",
				self.filename + ".mtimes.db",
				self.filename + ".buddymtimes.db",
				self.filename + ".lowercase_mapping.db",
				self.filename + ".blowercase_mapping.db",
			]

		_opened_shelves = []
		_errors = []
		for shelvefile in shelves:
			try:
				_opened_shelves.append(shelve.open(shelvefile))
			except:
				_errors.append(shelvefile)
				try:
					os.unlink(shelvefile)
					_opened_shelves.append(shelve.open(shelvefile, flag='n'))
				except Exception, ex:
					print("Failed to unlink %s: %s" % (shelvefile, ex))
		sharedfiles =         _opened_shelves.pop(0)
		bsharedfiles =        _opened_shelves.pop(0)
		sharedfilesstreams =  _opened_shelves.pop(0)
		bsharedfilesstreams = _opened_shelves.pop(0)
		wordindex =           _opened_shelves.pop(0)
		bwordindex =          _opened_shelves.pop(0)
		fileindex =           _opened_shelves.pop(0)
		bfileindex =          _opened_shelves.pop(0)
		sharedmtimes =        _opened_shelves.pop(0)
		bsharedmtimes =       _opened_shelves.pop(0)
		lowercase =           _opened_shelves.pop(0)
		blowercase =          _opened_shelves.pop(0)

		if _errors:
			log.addwarning(_("Failed to process the following databases: %(names)s") % {'names': '\n'.join(_errors)})
			files = self.clearShares(sharedfiles, bsharedfiles, sharedfilesstreams, bsharedfilesstreams, wordindex, bwordindex, fileindex, bfileindex, sharedmtimes, bsharedmtimes)
			if files is not None:
				sharedfiles, bsharedfiles, sharedfilesstreams, bsharedfilesstreams, wordindex, bwordindex, fileindex, bfileindex, sharedmtimes, bsharedmtimes = files
			log.addwarning(_("Shared files database seems to be corrupted, rescan your shares"))
		
		self.sections["transfers"]["sharedfiles"] = sharedfiles
		self.sections["transfers"]["sharedfilesstreams"] = sharedfilesstreams
		self.sections["transfers"]["wordindex"] = wordindex
		self.sections["transfers"]["fileindex"] = fileindex
		self.sections["transfers"]["sharedmtimes"] = sharedmtimes
		self.sections["transfers"]["lowercase"] = lowercase
		
		self.sections["transfers"]["bsharedfiles"] = bsharedfiles
		self.sections["transfers"]["bsharedfilesstreams"] = bsharedfilesstreams
		self.sections["transfers"]["bwordindex"] = bwordindex
		self.sections["transfers"]["bfileindex"] = bfileindex
		self.sections["transfers"]["bsharedmtimes"] = bsharedmtimes
		self.sections["transfers"]["blowercase"] = blowercase
		
		if self.sections["server"]["server"][0] == "mail.slsknet.org":
			self.sections["server"]["server"] = ('server.slsknet.org', 2242)
		
		# Setting the port range in numerical order
		self.sections["server"]["portrange"] = (min(self.sections["server"]["portrange"]), max(self.sections["server"]["portrange"]))
		self.config_lock.release()

	def removeOldOption(self, section, option):
		if section in self.parser.sections():
			if option in self.parser.options(section):
				self.parser.remove_option(section, option)

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
			log.addwarning(_("Error while writing database files: %s") % error)
			return None
		return sharedfiles, bsharedfiles, sharedfilesstreams, bsharedfilesstreams, wordindex, bwordindex, fileindex, bfileindex, sharedmtimes, bsharedmtimes
	
	def writeConfig(self):
		self.writeConfiguration()
		self.writeDownloadQueue()
	def writeDownloadQueue(self):
		self.config_lock.acquire()
		realfile = self.filename + '.transfers.pickle'
		tmpfile = realfile + '.tmp'
		backupfile = realfile + ' .backup'
		try:
			handle = open(tmpfile, 'w')
		except Exception, inst:
			log.addwarning(_("Something went wrong while opening your transfer list: %(error)s") % {'error':str(inst)})
		else:
			try:
				cPickle.dump(self.sections['transfers']['downloads'], handle)
				handle.close()
				try:
					# Please let it be atomic...
					os.rename(tmpfile, realfile)
				except Exception, inst:
					# ...ugh. Okay, how about...
					try:
						os.unlink(backupfile)
					except:
						pass
					os.rename(realfile, backupfile)
					os.rename(tmpfile, realfile)
			except Exception, inst:
				log.addwarning(_("Something went wrong while writing your transfer list: %(error)s") % {'error':str(inst)})
		finally:
			try:
				handle.close()
			except:
				pass
		self.config_lock.release()
	def writeConfiguration(self):
		self.config_lock.acquire()

		external_sections =  ["sharedfiles", "sharedfilesstreams", "wordindex", "fileindex", "sharedmtimes", 'lowercase', "bsharedfiles", "bsharedfilesstreams", "bwordindex", "bfileindex", "bsharedmtimes", "blowercase", "downloads"]
		for i in self.sections.keys():
			if not self.parser.has_section(i):
				self.parser.add_section(i)
			for j in self.sections[i].keys():
				if j not in external_sections:
					self.parser.set(i, j, self.sections[i][j])
				else:
					self.parser.remove_option(i, j)
		
		path, fn = os.path.split(self.filename)
		try:
			if not os.path.isdir(path):
				os.makedirs(path)
		except OSError, msg:
			log.addwarning(_("Can't create directory '%(path)s', reported error: %(error)s") % {'path':path, 'error':msg})
		
		oldumask = os.umask(0077)
	
		try:
			f = open(self.filename + ".new", "w")
		except IOError, e:
			log.addwarning(_("Can't save config file, I/O error: %s") % e)
			self.config_lock.release()
			return
		else:
			try:
				self.parser.write(f)
			except IOError, e:
				log.addwarning(_("Can't save config file, I/O error: %s") % e)
				self.config_lock.release()
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
					log.addwarning(_("Can't remove %s" % self.filename + ".old"))
				try:
					os.rename(self.filename, self.filename + ".old")
				except OSError, error:
					log.addwarning(_("Can't back config file up, error: %s") % error)
		except OSError:
			pass
	
		try:
			os.rename(self.filename + ".new", self.filename)
		except OSError, error:
			log.addwarning(_("Can't rename config file, error: %s") % error)
		
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
				raise BaseException("File %s exists" % filename)
			import tarfile
			tar = tarfile.open(filename, "w:bz2")
			if not os.path.exists(self.filename):
				raise BaseException("Config file missing")
			tar.add(self.filename)
			if os.path.exists(self.filename+".alias"):
				tar.add(self.filename+".alias")

			tar.close()
		except Exception, e:
			print e
			self.config_lock.release()
			return (1, "Cannot write backup archive: %s" % e)
		self.config_lock.release()
		return (0, filename)
	
	def setBuddyShares(self, files, streams, wordindex, fileindex, mtimes, lowercase_mapping):
		if self.sections["transfers"]["bsharedfiles"] == files:
			return
		storable_objects = [
				(files,             "bsharedfiles",        ".buddyfiles.db"),
				(streams,           "bsharedfilesstreams", ".buddystreams.db"),
				(mtimes,            "bsharedmtimes",       ".buddymtimes.db"),
				(wordindex,         "bwordindex",          ".buddywordindex.db"),
				(fileindex,         "bfileindex",          ".buddyfileindex.db"),
				(lowercase_mapping, "blowercase",          ".buddylowercase_mapping.db"),
			]
		self.config_lock.acquire()
		self._storeObjects(storable_objects)
		self.config_lock.release()
		
	def setShares(self, files, streams, wordindex, fileindex, mtimes, lowercase_mapping):
		if self.sections["transfers"]["sharedfiles"] == files:
			return
		storable_objects = [
				(files,             "sharedfiles",        ".files.db"),
				(streams,           "sharedfilesstreams", ".streams.db"),
				(mtimes,            "sharedmtimes",       ".mtimes.db"),
				(wordindex,         "wordindex",          ".wordindex.db"),
				(fileindex,         "fileindex",          ".fileindex.db"),
				(lowercase_mapping, "lowercase",          ".lowercase_mapping.db"),
			]
		self.config_lock.acquire()
		self._storeObjects(storable_objects)
		self.config_lock.release()

	def _storeObjects(self, storable_objects):
		for (source, destination, prefix) in storable_objects:
			self.sections["transfers"][destination].close()
			self.sections["transfers"][destination] = shelve.open(self.filename + prefix, flag='n')
			for (key, value) in source.iteritems():
				self.sections["transfers"][destination][key] = value

	def writeShares(self):
		self.config_lock.acquire()
		self.sections["transfers"]["sharedfiles"].sync()
		self.sections["transfers"]["sharedfilesstreams"].sync()
		self.sections["transfers"]["wordindex"].sync()
		self.sections["transfers"]["fileindex"].sync()
		self.sections["transfers"]["sharedmtimes"].sync()
		self.sections["transfers"]["lowercase"].sync()
		
		self.sections["transfers"]["bsharedfiles"].sync()
		self.sections["transfers"]["bsharedfilesstreams"].sync()
		self.sections["transfers"]["bwordindex"].sync()
		self.sections["transfers"]["bfileindex"].sync()
		self.sections["transfers"]["bsharedmtimes"].sync()
		self.sections["transfers"]["blowercase"].sync()
		if sys.platform == 'darwin': # sync() doesn't seem to be enough on OS X
			self.sections["transfers"]["sharedfiles"].close()
			self.sections["transfers"]["sharedfilesstreams"].close()
			self.sections["transfers"]["sharedmtimes"].close()
			self.sections["transfers"]["wordindex"].close()
			self.sections["transfers"]["fileindex"].close()
			self.sections["transfers"]["sharedfiles"] = shelve.open(self.filename+".files.db")
			self.sections["transfers"]["sharedfilesstreams"] = shelve.open(self.filename+".streams.db")
			self.sections["transfers"]["sharedmtimes"] = shelve.open(self.filename+".mtimes.db")
			self.sections["transfers"]["wordindex"] = shelve.open(self.filename+".wordindex.db")
			self.sections["transfers"]["fileindex"] = shelve.open(self.filename+".fileindex.db")
			self.sections["transfers"]["lowercase"] = shelve.open(self.filename+".lowercase_mapping.db")
			self.sections["transfers"]["bsharedfiles"].close()
			self.sections["transfers"]["bsharedfilesstreams"].close()
			self.sections["transfers"]["bsharedmtimes"].close()
			self.sections["transfers"]["bwordindex"].close()
			self.sections["transfers"]["bfileindex"].close()
			self.sections["transfers"]["bsharedfiles"] = shelve.open(self.filename+".buddyfiles.db")
			self.sections["transfers"]["bsharedfilesstreams"] = shelve.open(self.filename+".buddystreams.db")
			self.sections["transfers"]["bsharedmtimes"] = shelve.open(self.filename+".buddymtimes.db")
			self.sections["transfers"]["bwordindex"] = shelve.open(self.filename+".buddywordindex.db")
			self.sections["transfers"]["bfileindex"] = shelve.open(self.filename+".buddyfileindex.db")
			self.sections["transfers"]["blowercase"] = shelve.open(self.filename+".buddylowercase_mapping.db")
				
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
			for (key, value) in self.aliases.iteritems():
				m = m + "%s: %s\n" % (key, value)
			return m+"\n"

	def Unalias(self, rest):
		if rest and rest in self.aliases:
			x = self.aliases[rest]
			del self.aliases[rest]
			self.writeAliases()
			return _("Removed alias %(alias)s: %(action)s\n") % {'alias':rest, 'action':x}
		else:
			return _("No such alias (%(alias)s)\n") % {'alias':rest}
