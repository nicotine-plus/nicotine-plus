# -*- coding: utf-8 -*-

from pynicotine.pluginsystem import BasePlugin, returncode
from pynicotine import slskmessages
import re, os
from pynicotine.gtkgui.utils import fixpath, WriteLog #ah- drill into subdirs via lambda (.) #this fails, so we just manually implement it (below)
import gobject
import random, time
import sys
from threading import Timer

def enable(frame):
	global PLUGIN
	PLUGIN = Plugin(frame)
	#PLUGIN.fixupmetasettings()

def disable(frame):
	global PLUGIN
	PLUGIN = None

class Plugin(BasePlugin):
	__name__ = "soulblock"
	
	# Note:  	In order to reload prefs, after the user changes a setting, we're trapping access to 'settings' via a property getter/setter.
	# 			This brings certain consequences, like *Heavy* sequential access when loading the settings window; and recursive/race conditions,
	#			when we try and adjust 'settings' from inside the pref reloading (which we do). So, there's a fair bit of logic to
	#			our otherwise simple getter.
	@property
	def settings(self):
		caller = sys._getframe(1).f_code.co_name ##inspect.stack()[1][3]  #this would get all frames, so we'll go with sys._getframe(n) instead.
		caller = sys._getframe(1).f_code.co_name ##inspect.stack()[1][3]
		#self.log('settings.getter - caller:  %s' % (caller))
		#self.log('settings.getter - callee:  %s' % (callee))
		if self.__ServerConnectNotification_complete and (caller != self._pref_compiling_function_name): 
			cur_settings_string = `self._settings`
			if self._last_settings_string != cur_settings_string:
				self._last_settings_string = cur_settings_string
				#self.compilelocalprefs()
				#self.log('reloaded prefs:  %s' % (cur_settings_string))
				oldtimer = self._pref_reload_timer
				self._pref_reload_timer = Timer(2, self.reloadprefs)
				self._pref_reload_timer.start()
				oldtimer.cancel()
		return self._settings

	@settings.setter
	def settings(self, value):
		#self.log('settings.setter') ##:  %s' % (`value`))
		self._settings = value

	@settings.deleter
	def settings(self):
		del self._settings
      
	_last_settings_string = ''
	_settings = {	
		'enabled':				True,
		'maxspamuntilautoblock':4,
		'minlength':			200,
		'maxlength':			400, #this is also used to limit echoed loglines, so don't discard without adjusting.
		'maxdiffcharacters':	10,
		'maxrepeatcharacters':	16,
		'logtoconsole':			True,
		'logtofile':			True,
		'echoallpm':			False,
		'echoblockedpm':		True,
		'echoblockedpublic':	True,
		'echoblocked':			True,
		'iplookuppm':			True,
		'iplookuppublic':		True,
		'badcontent':			[' fuk', 'cunt', 'kitchenwallet', 'k i t c h e n w a l l e t', 'bandcamp', 'ctcp', 'buy viagra now','mybrute.com','mybrute.es','0daymusic.biz'],
		'badnicks':				['fuk', 'phiz', 'arkie', 'fuck'],
		'screenpublicnicks':	True,
		'autoblockcache':		{},
	}
	metasettings = {
		#'enabled': 			{"description": 'Enabled', 'type':'bool'} ,
		'maxspamuntilautoblock':{"description": 'Maximum times a user may spam, before everything they say is autoblocked', 'type':'integer'},
		#'minlength': 			{"description": 'Blocked ascii art: min line length', 'type':'integer'} ,
		#'maxdiffcharacters': 	{"description": 'Blocked ascii art: max unique chars', 'type':'integer'},
		#'maxlength': 			{"description": 'Max line length', 'type':'integer'},
		#'maxrepeatcharacters': {"description": 'Maximum times a character may repeat serially, in a line', 'type':'integer'},
		'logtoconsole': 		{"description": 'Log spam to console', 'type':'bool'},
		#'logtofile': 			{"description": 'Log spam to file', 'type':'bool'},
		'echoblocked': 			{"description": 'Echo spam back', 'type':'bool'},
		#'echoallpm': 			{"description": 'Echo all Private Messages back- fast', 'type':'bool'},
		#'echoblockedpm': 		{"description": 'Echo Private spam', 'type':'bool'},
		#'echoblockedpublic': 	{"description": 'Echo Public spam', 'type':'bool'},
		#'iplookuppm': 			{"description": 'Track Public spam IPs', 'type':'bool'},
		#'iplookuppublic': 		{"description": 'Track Private spam IPs', 'type':'bool'},
		#'iplookup': 			{"description": 'Track IPs', 'type':'bool'},
		'badcontent': 			{"description": 'Public + Private Messages containing text below are spam', 'type':'list string'},
		#'badnicks': 			{"description":	'Private Messages from usernames containing text below will be blocked', 'type':'list string'},
		'badnicks': 			{"description":	'Nicks containing text below are blocked', 'type':'list string'},
		#'screenpublicnicks': 	{"description": 'Also screen Public usernames', 'type':'bool'},
	}
 	metasettings_order = ['enabled','maxspamuntilautoblock','minlength','maxdiffcharacters','maxlength','maxrepeatcharacters','logtoconsole','logtofile','echoblocked','echoallpm','echoblockedpm','echoblockedpublic','iplookuppm','iplookuppublic','iplookup','badcontent','badnicks','screenpublicnicks']

	userstocheck = {}
	blockedips = {}
	autoblockcache = {}
	blocktypes={1:'content',2:'nick',3:'repetition',4:'ascii art',5:'excessive length',6:'series of non-letters',7:'user'}

	#XXX TODO: 
	#			[x]	exempt buddy list (self.parent.frame.np.userlist ?) [actually, it required reading the pref directly -test1234567654321]
	#			[x]	autoblock new nicks for previous spammers, when they have more than N postings of spam, historically
	#					[ ]	store the new block, in a separate pref, with a datestamp, and delete it after a known period of time
	#					[ ]	have autoblock list updated even when ip-tracking is disabled (with a pref, storing just the blocked-nicks, too?)
	#			[x]	double echo control: preventing two users from bouncing one original blocked message between each other
	#			[x]	flood control: prevent a flood of outgoing echoes, when too many users present block-worthy text, at (nearly) the same time
	#					[ ]	use a queue and dual timers to space the echoes evenly, and echo as much spam back as possible
	#			[x]	force pref-window ordering, by replacing 'metasettings' with an ordered dict (python 2.7+)
	#			[x]	re-initialize local settings after any of our prefs change (via 'settings' getter)
	
	def init(self): #this runs twice when the plugin loads -- once, for the default settings, and once when the saved prefs are pushed in.
		self.__ServerConnectNotification_complete = False
		self._pref_reload_timer = Timer(2, self.reloadprefs) #placeholder -- this will be re-set from our 'settings' getter
		self.fixupmetasettings() #huh. this stopped working, when run from 'LoadNotification', if we un-commented any disabled metasettings
		self.executingcallback = False
		self.compilelocalprefs() 
	def LoadNotification(self):
		#self.log('A line should be at least %s characters long, with less than %s unique characters before it\'s considered ASCII spam.' % (self.settings['minlength'], self.settings['maxdiffcharacters']))
		self.log('Everything running smooth.')
	def ServerConnectNotification(self):
		#self.log('self.frame.np.userlist.userlist[0][0]:  %s' % (self.frame.np.userlist.userlist[0][0]))
		self.__ServerConnectNotification_complete = True
		pass
	def reloadprefs(self):
		self.compilelocalprefs()
		self.log('reloaded prefs')
	def compilelocalprefs(self):
		if not hasattr(self, '_pref_compiling_function_name'): 
			self._pref_compiling_function_name = sys._getframe(0).f_code.co_name
		self.repeatchars_RE = re.compile(r'.*(\S)\1{%s,}.*' % (self.settings['maxrepeatcharacters'])) #prefixing a string with 'r' keeps python from stripping any prefix-backslashes
		self.onlyspaces_or_numbers_RE = re.compile(r'( |\d)+') #prefixing a string with 'r' keeps python from stripping any prefix-backslashes
		self.onlynonwords_RE = re.compile(r'\w*([^ \w][^ \W]*){3}') #ah- we forgot the initial '\w*' to account for valid letters preceeding the first non-letter
		self.blank_RE = re.compile('^$') #prefixing a string with 'r' keeps python from stripping any prefix-backslashes
		self.badcontent_RE = re.compile('.*('+'|'.join(str(x) for x in self.settings['badcontent'])+').*', re.I)
		self.badnicks_RE = re.compile('.*('+'|'.join(str(x) for x in self.settings['badnicks'])+').*', re.I)
		self.settings['echoblockedpm'] = self.settings['echoblocked']
		self.settings['echoblockedpublic'] = self.settings['echoblocked']
		#self.log('badnicks: %s' % ('.*('+'|'.join(str(x) for x in self.settings['badnicks'])+').*'))
		#self.log("compile prefs completed.")
	metasettings_adjusted = False
	def fixupmetasettings(self):
		if (sys.version_info < (2, 7)) or self.metasettings_adjusted: return
		from collections import OrderedDict
		newmetasettings = OrderedDict()
		for m in self.metasettings_order:
			if m in self.metasettings:
				newmetasettings[m] = self.metasettings[m]
		self.metasettings = newmetasettings
		self.metasettings_adjusted = True
		#self.log('newmetasettings: %s' % (newmetasettings.items()))
		#self.log('metasettings adjusted: %s' % (self.metasettings.items()))
	def IncomingPublicChatEvent(self, room, user, line):
		if not self.settings['enabled']: return #not enabled
		if user == self.parent.frame.np.config.sections["server"]["login"]: return #ignore ourselves (apparently, we also trigger an incoming event)
		if self.checkbuddylist(user): return   ##if self.buddylist_RE.match(user): return   ##if user in self.buddylist: return
		if self.settings['iplookuppublic']:
			self.userstocheck[user] = {'user':user}
			self.parent.frame.np.queue.put(slskmessages.GetPeerAddress(user)) #hopefully now, we'll catch ip's even before quick disconnections (spammers- gotta love 'em)
		blocktypecode = self.checkautoblock(user)
		if (not blocktypecode): blocktypecode = self.checkcontent(line)
		if (not blocktypecode) and (self.settings['screenpublicnicks']): blocktypecode = self.checkname(user)
		if blocktypecode:
			if self.settings['iplookuppublic']: self.prelimresolve(user,line,blocktypecode,'room '+room)    #,room)    #,'#'+room)
			else:
				logline = self.generatespamlog('', user, 'room '+room, blocktypecode, line)
				if self.settings['echoblockedpublic']: self.msguserdirect(user,logline)
				self.writespamlog(room,logline)
			return returncode['zap']
		elif (user in self.userstocheck): del self.userstocheck[user] #..if we didn't delete it, we could log info about the history/frequency of spam, ip's used, cross-referenced nick-to-ip-datasets (and reverse), etc.
	def IncomingPrivateChatEvent(self, user, line):
		#self.log('badcontent: %s' % ('.*('+'|'.join(str(x) for x in self.settings['badcontent'])+').*'))
		if not self.settings['enabled']: return #not enabled
		if self.checkbuddylist(user): return   ##if self.buddylist_RE.match(user): return   ##if user in self.buddylist: return
		if self.settings['echoallpm']: self.msguserdirect(user,line)
		if self.settings['iplookuppm']:
			self.userstocheck[user] = {'user':user,'location':'private msg'}
			self.parent.frame.np.queue.put(slskmessages.GetPeerAddress(user)) #hopefully now, we'll catch ip's even before quick disconnections (spammers- gotta love 'em)
		#self.log('self.onlynonwords_RE.match(line) ->   %s' % (self.onlynonwords_RE.match(line)))
		blocktypecode = self.checkautoblock(user)
		if (not blocktypecode) and ((not self.getprivatelog(user)) and (self.onlyspaces_or_numbers_RE.match(line) or (len(line)==0) or self.onlynonwords_RE.match(line))): blocktypecode = 6
		if (not blocktypecode): blocktypecode = (self.checkcontent(line) or self.checkname(user))
		if blocktypecode:
			if self.settings['iplookuppm']: self.prelimresolve(user,line,blocktypecode,'private msg')
			else: 
				logline = self.generatespamlog('', user, 'private msg', blocktypecode, line)
				if self.settings['echoblockedpm']: self.msguserdirect(user,logline)
				self.writespamlog('private msg',logline)
			return returncode['zap']
		elif (user in self.userstocheck): del self.userstocheck[user] #..if we didn't delete it, we could log info about the history/frequency of spam, ip's used, cross-referenced nick-to-ip-datasets (and reverse), etc.
	def checkbuddylist(self, user):
		for b in self.frame.np.userlist.userlist:  #Note: the list wont exist, until at least one server connection has completed.
			if b[0] == user: return True
		return False
	def checkautoblock(self, user):
		if user in self.autoblockcache: return 7
	def checkcontent(self, line):
		if self.repeatchars_RE.match(line): return 3
		if len(line) >= self.settings['minlength'] and len(set(line)) < self.settings['maxdiffcharacters']: return 4
		if len(line) > self.settings['maxlength']: return 5
		if (self.badcontent_RE.match(line)): return 1
	def checkname(self, user):
		if (self.badnicks_RE.match(user)): return 2
	def prelimresolve(self, user, line, blocktypecode, location):
		if user in self.userstocheck: #and ('ip' not in self.userstocheck[user]) : 
			_ = self.userstocheck[user], 	line,	 		blocktypecode, 			location 				#pack the tuple..
			cache, 							cache['line'],	cache['blocktypecode'],	cache['location'] = _ 	#..and unpack it.
			if 'ip' in cache: #..because UserResolveNotification beat us, to the punch
				self.finalresolve(cache)
	def UserResolveNotification(self, user, ip, port, country): #this is async to prelimresolve(), and potentially finalresolve()
		#self.log('1: %s %s' % (user in self.userstocheck, ip in self.blockedips))
		if self.checkbuddylist(user): return returncode['pass']   ##if self.buddylist_RE.match(user): return returncode['pass']   ##if user in self.buddylist: return returncode['pass']
		elif user in self.userstocheck: #and ('ip' not in self.userstocheck[user]) : 
			cache = self.userstocheck[user]
			cache['ip'] = ip
			if 'blocktypecode' in cache: self.finalresolve(cache)
		elif (ip in self.blockedips) and (not (user in self.blockedips[ip])):  #we should read/write a separate ip-cache file, to consult here
			if user == self.parent.frame.np.config.sections["server"]["login"]: return returncode['pass'] #ignore ourselves (test-spam from other local clients, etc. might trigger this)
			logline = 'New username detected, for previous spammer %s ->   %s ->   %s' % (ip, user, ', '.join(str(x) for x in self.blockedips[ip] if x != 'totalblocks')) #using a generator expression, for list-join (..there's other approaches)
			if self.settings['logtoconsole']: self.log(logline)
			if self.settings['echoblockedpublic']: self.msguserdirect(user,logline)
			##self.blockedips[ip][user]=0   #so, 0 will be our designation for 'not-yet-spamming-new-nicks-for-bad-ips'
			self.blockedips[ip][user] = {'count':0, 'lastlogline':None}  #just leave empty fields for 'not-yet-spamming-new-nicks-for-bad-ips'
			## we should initiate an auto-block, after a certain number of new nicks, within a certain time, and perhaps some additional heuristics (too few lines posted, perhaps) are satisfied
		return returncode['pass']
	def finalresolve(self, c):
		del self.userstocheck[c['user']]
		ip = c['ip']
		user = c['user']
		location = c['location']
		blocktypecode = c['blocktypecode']
		logline = self.generatespamlog(ip, user, location, blocktypecode, c['line'])
		self.writespamlog(location,logline)
		
		if ip == '0.0.0.0': return
		if len(logline) > self.settings['maxlength']: logline = logline[0:self.settings['maxlength']] #prevent triggering server flood controls, if the spam is too long
		lastlogline = None
		##if (blocktypecode == 2) or (blocktypecode == 7): bcount = 0 #don't count nick-blocks or autoblocks against the total 'blocked spam count', since they might not have been spam, and nick-block is redundant to autoblock
		##else: bcount = 1 #legitimate spam -- counted.
		bcount = 1
		if not (ip in self.blockedips): self.blockedips[ip] = {user:{'count':bcount,'lastlogline':logline},'totalblocks':bcount}   #now, we're good, with a conditional expression in the generator (above).  #totalblocks will show in the logstring, if enabled.
		else: 
			ipsubcache = self.blockedips[ip]
			if user in ipsubcache: 
				lastlogline = ipsubcache[user]['lastlogline']
				ipsubcache[user]['count']+=bcount
				ipsubcache[user]['lastlogline']=logline
			else: ipsubcache[user]={'count':bcount,'lastlogline':logline}
			ipsubcache['totalblocks']+=1   #totalblocks will show in the logstring, if enabled.
			if ipsubcache['totalblocks'] >= self.settings['maxspamuntilautoblock']: self.autoblockcache[user]=0 #three strikes and you're out (...well, ok: maybe four).
			
		if ((location == 'private msg') and self.settings['echoblockedpm']) or ((location != 'private msg') and self.settings['echoblockedpublic']):
			doubleecho = False #we need to prevent double-echoing between two plugins, so we'll test each newly blocked message against the last sent -- in the least resource-intensive manner possible.
			if lastlogline:
				l1 = len(lastlogline)
				l2 = len(logline)
				samplecount = 5
				if (l1 < l2) and (l1 > samplecount): #if the line is shorter than '5', there's just no point in pretending we could match.
					offset = l2-l1
					sampling = random.sample( xrange(0,l1), samplecount ) #'xrange' produces ranges on-demand, reducing resource usage; 5 is our random-sample count
					samplematched = True
					for s in sampling:
						if lastlogline[s] != logline[s+offset]:
							samplematched=False
							break
					if samplematched and logline.find(lastlogline) > -1:  #the random samples matched, so proceed with a more resource-heavy '.find()'
						ipsubcache[user]['lastlogline']=lastlogline #set it back to the last non-echo spam -- better than duplicating all the "find if the user exists in the subcache" code (above)
						doubleecho = True
			if not doubleecho: self.msguserdirect(user,logline)
	def startautoblock(self,user,ip):
		pass
	def stopautoblock(self,user,ip):
		pass
	def pruneautoblock(self,user,ip):
		pass
	msgdirect_lasttimesent = time.time()
	msgdirect_queue = []
	def msguserdirect(self,user,line):
		curtime = time.time()
		#self.log('lasttimesent: %0.3f   ->   curtime: %0.3f   ->   diff: %0.3f' % (self.msgdirect_lasttimesent, curtime, curtime-self.msgdirect_lasttimesent))
		if (curtime-self.msgdirect_lasttimesent) >= 1: 
			self.msgdirect_lasttimesent = curtime
			self.parent.frame.np.queue.put(slskmessages.MessageUser(user, line.encode("utf-8",'replace'))) #hmm..?
	def generatespamlog(self, ip, user, location, blocktypecode, line):
		if blocktypecode == 7: 
			logline = 'Autoblocked '
			if location != 'private message': logline += 'posting in '
		else: logline = 'Blocked %s in ' % (self.blocktypes[blocktypecode])
		logline += '%s ' % (location)
		if ip != '0.0.0.0' and ip != '': logline += 'from %s ' % (ip)
		logline += '->	  %s: %s' % (user, line)
		return logline
	def writespamlog(self,location,logline):
		if self.settings['logtoconsole']: self.log(logline) #only show in the console if the pref is set.
		if self.settings['logtofile']:
			logfilename=__name__ #named after us!
			if location == 'private msg': target_logdir='privatelogsdir'
			else: target_logdir='roomlogsdir'
			WriteLog(None, self.parent.frame.np.config.sections["logging"][target_logdir], logfilename, logline) #sections["logging"]["privatelogsdir"]
	def getprivatelog(self, user): # Read log file -- from privatechat.py
		config = self.frame.np.config.sections
		log = os.path.join(config["logging"]["privatelogsdir"], fixpath(user.replace(os.sep, "-")) + ".log") #fixpath(user.replace(os.sep, "-")) + ".log")
		return os.path.isfile(log)
