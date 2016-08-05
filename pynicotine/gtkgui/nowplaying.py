# Copyright (C) 2007-2009 daelstorm. All rights reserved.
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

import gtk, gobject
import os, sys, re, thread, threading
import copy
import sys

if sys.platform == "win32":
	HAS_WIN32GUI = False
	try: 
		from win32gui import *
		HAS_WIN32GUI = True
	except: 
		pass

from pynicotine.utils import executeCommand
from pynicotine.logfacility import log

class NowPlaying:
	def __init__(self, frame, fake=False):
		"""Create NowPlayer interface

If faked=True it will only create a partial instance, enough to debug NP-code with from the command line"""
		# Only configure things here that are required for a faked instance
		self.frame = frame
		try:
			import dbus
			import dbus.glib
			self.bus = dbus.SessionBus()
		except Exception, e:
			self.bus = None
		if fake:
			return
		# All things that aren't needed for a faked instance
		self.accel_group = gtk.AccelGroup()
		self.wTree = gtk.glade.XML(os.path.join(os.path.dirname(os.path.realpath(__file__)), "nowplaying.glade"), None)
		widgets = self.wTree.get_widget_prefix("")
		for i in widgets:
			name = gtk.glade.get_widget_name(i)
			self.__dict__[name] = i

		self.wTree.signal_autoconnect(self)

		self.NowPlaying.set_icon(self.frame.images["n"])
		self.NowPlaying.set_position(gtk.WIN_POS_NONE)
		#self.NowPlaying.set_modal(True)
		self.NowPlaying.set_transient_for(self.frame.MainWindow)
		self.NowPlaying.add_accel_group(self.accel_group)
	
		self.NowPlaying.connect("destroy", self.quit)
		self.NowPlaying.connect("destroy-event", self.quit)
		self.NowPlaying.connect("delete-event", self.quit)
		self.NowPlaying.set_resizable(False)

		self.defaultlist = [ "$n", "$a - $t", "[$a] $t", "Now $s: [$a] $t", "Now $s: $n", "$a - $b - $t", "$a - $b - $t ($l/$rKBps) from $y $c" ]
		self.title_clear()
		self.player_replacers = []
		self.NPFormat_List = gtk.ListStore(gobject.TYPE_STRING)
		self.NPFormat.set_model(self.NPFormat_List)
		self.NPFormat.set_text_column(0)
		self.NPFormat.child.connect("activate", self.OnAddFormat)
		self.NPFormat.child.connect("changed", self.OnModifyFormat)
		self.OnNPPlayer(None)
	
		#self.NowPlaying.add(self.vbox1)
		
		# Set the active radio button
		config = self.frame.np.config.sections
		self.SetPlayer(config["players"]["npplayer"])
		if config["players"]["npformat"] != "":
			self.NPFormat.child.set_text(config["players"]["npformat"])
		if config["players"]["npformatlist"] != []:
			if config["players"]["npformat"] == "":
				self.NPFormat.child.set_text(str(config["players"]["npformatlist"][0]))
			for item in config["players"]["npformatlist"]:
				self.NPFormat_List.append([item])
		if config["players"]["npformat"] == "":
			self.NPFormat.child.set_text(str(self.defaultlist[0]))
		self.NPCommand.set_text(config["players"]["npothercommand"])
		
		for item in self.defaultlist:
			self.NPFormat_List.append([str(item)])
		
		
	def SetTextBG(self, widget, bgcolor="", fgcolor=""):
		if bgcolor == "":
			colour = None
		else:
			colour = gtk.gdk.color_parse(bgcolor)
		widget.modify_base(gtk.STATE_NORMAL, colour)
		widget.modify_bg(gtk.STATE_NORMAL, colour)

		if type(widget) in (gtk.Entry, gtk.SpinButton):
			if fgcolor == "":
				colour = None
			else:
				colour = gtk.gdk.color_parse(fgcolor)
			widget.modify_text(gtk.STATE_NORMAL, colour)
			widget.modify_fg(gtk.STATE_NORMAL, colour)

	def title_clear(self):
		self.Example.set_text("")
		self.title = { "title": "", "artist": "", "comment": "", "year": "", "album": "", "track":"", "length": "", "nowplaying": "", "status": "", "bitrate": "", "filename": ""}
		
	def SetPlayer(self, player):
		if player == "infopipe":
			self.NP_infopipe.set_active(1)
		elif player == "amarok":
			self.NP_amarok.set_active(1)
		elif player == "amarok2":
			self.NP_amarok2.set_active(1)
		elif player == "audacious":
			self.NP_audacious.set_active(1)
		elif player == "mpd":
			self.NP_mpd.set_active(1)
		elif player == "banshee":
			self.NP_banshee.set_active(1)
		#elif player == "mp3blaster":
		#	self.NP_mp3blaster.set_active(1)
		elif player == "rhythmbox":
			self.NP_rhythmbox.set_active(1)
		elif player == "bmpx":
			self.NP_bmpx.set_active(1)
		elif player == "exaile":
			self.NP_exaile.set_active(1)
		elif player == "lastfm":
			self.NP_lastfm.set_active(1)
		elif player == "foobar":
			self.NP_foobar.set_active(1)
		elif player == "mpris":
			self.NP_mpris.set_active(1)
		elif player == "other":
			self.NP_other.set_active(1)
			self.player_replacers = ["$n"]
		else:
			self.NP_other.set_active(1)
			
	def OnModifyFormat(self, widget):
		text = self.NPFormat.child.get_text().strip()
		replacers = []
		for replacer in ["$n", "$t", "$l", "$a", "$b", "$c", "$k", "$y", "$r", "$f", "$s", "$p"]:
			if replacer in text:
				replacers.append(replacer)
		for replacer in replacers:
			if replacer not in self.player_replacers:
				self.frame.SetTextBG(self.NPFormat.child, "red", "white")
				return
		self.frame.SetTextBG(self.NPFormat.child, "", "")
			
	def OnAddFormat(self, widget):
		text = self.NPFormat.child.get_text().strip()
		if text.isspace() or text == "":
			return
		items = self.frame.np.config.sections["players"]["npformatlist"]
		if text in self.defaultlist:
			return
		if text in items:
			items.remove(text)
		items.insert(0, text)
		self.frame.np.config.sections["players"]["npformat"] = text
		del items[15:]
		self.frame.np.config.writeConfiguration()
		# Repopulate the combo list
		self.NPFormat.get_model().clear()
		templist = []
		for i in items:
			if i not in templist:
				templist.append(i)
		templist += self.defaultlist
		for i in templist:
			self.NPFormat.append_text(i)
			
	def OnNPPlayer(self, widget):
		isset = False
		if self.NP_infopipe.get_active():
			self.player_replacers = ["$n",  "$l", "$b", "$c", "$k", "$r", "$f", "$s"]
			isset = True
		elif self.NP_mpd.get_active():
			self.player_replacers = ["$n", "$t", "$a", "$b",  "$f", "$k"]
			isset = True
		elif self.NP_banshee.get_active():
			self.player_replacers = ["$n", "$t", "$l", "$a", "$b", "$k", "$y", "$r", "$f", "$s"]
			isset = True
		elif self.NP_amarok.get_active():
			self.player_replacers = ["$n", "$t", "$l", "$a", "$b", "$c", "$k", "$y", "$r", "$f", "$s"]
			isset = True
		elif self.NP_amarok2.get_active():
			self.player_replacers = ["$n", "$t", "$l", "$a", "$b", "$c", "$k", "$y", "$r", "$f", "$s"]
			isset = True
		elif self.NP_audacious.get_active():
			self.player_replacers = ["$n", "$t", "$l", "$a", "$b", "$c", "$k", "$y", "$r", "$f", "$s"]
			isset = True
		elif self.NP_rhythmbox.get_active():
			self.player_replacers = ["$n", "$t", "$l", "$a", "$b", "$c", "$k", "$y", "$r", "$f", "$s"]
			isset = True
		elif self.NP_bmpx.get_active():
			self.player_replacers = ["$n", "$t", "$l", "$a", "$b", "$k", "$y", "$r", "$f"]
			isset = True
		elif self.NP_exaile.get_active():
			self.player_replacers = ["$t", "$l", "$a", "$b"]
			isset = True
		elif self.NP_lastfm.get_active():
			self.player_replacers = ["$n", "$s", "$t", "$a"]
			self.player_input.set_text(_("Username:"))
			isset = True
		elif self.NP_foobar.get_active():
			self.player_replacers = ["$n"]
			isset = True
		elif self.NP_mpris.get_active():
			self.player_replacers = ['$p', '$a', '$b', '$t', '$c', '$r', '$k', '$l']
			self.player_input.set_text(_("Client name (empty = auto):"))
			isset = True
		elif self.NP_other.get_active():
			self.player_replacers = ["$n"]
			self.player_input.set_text(_("Command:"))
			isset = True

		self.NPCommand.set_sensitive(
			self.NP_lastfm.get_active() or
			self.NP_other.get_active() or
			self.NP_mpris.get_active()
		)
		
		legend = ""
		for item in self.player_replacers:
			legend += item + "\t"
			if item == "$t":
				legend += _("Title")
			elif item == "$n":
				legend += _("Now Playing (typically \"%(artist)s - %(title)s\")") % {'artist':_("Artist"), 'title':_("Title")}
			elif item == "$l":
				legend += _("Length")
			elif item == "$r":
				legend += _("Bitrate")
			elif item == "$c":
				legend += _("Comment")
			elif item == "$a":
				legend += _("Artist")
			elif item == "$b":
				legend += _("Album")
			elif item == "$k":
				legend += _("Track Number")
			elif item == "$y":
				legend += _("Year")
			elif item == "$f":
				legend += _("Filename (URI)")
			elif item == "$s":
				legend += _("Status")
			elif item == "$p":
				legend += _("Program")
			legend += "\n"
		self.Legend.set_text(legend)
		if not isset:
			self.Legend.set_text("")
		self.OnModifyFormat(self.NPFormat.child)
			
	def OnNPCancel(self, widget):
		self.quit(None)
		
	def quit(self, widget, s=None):
		self.NowPlaying.hide()
		return True
		
	def OnNPTest(self, widget):

		self.DisplayNowPlaying(None, 1)
		
	def DisplayNowPlaying(self, widget, test=0, callback=None):

		if (self.NP_rhythmbox.get_active() or
				self.NP_bmpx.get_active() or
				self.NP_mpris.get_active()):
			# dbus (no threads, please)
			self.GetNP(None, test, callback)
		else:
			# thread (command execution)
			thread.start_new_thread(self.GetNP, (None, test, callback))
			
	def GetNP(self, widget, test=None, callback=None):
		self.title_clear()
		try:
			if self.NP_infopipe.get_active(): 
					result = self.xmms() 
			elif self.NP_amarok.get_active(): 
					result = self.amarok() 
			elif self.NP_amarok2.get_active(): 
					result = self.amarok2() 
			elif self.NP_audacious.get_active(): 
					result = self.audacious() 
			elif self.NP_mpd.get_active(): 
					result = self.mpd() 
			elif self.NP_banshee.get_active(): 
					result = self.banshee() 
			elif self.NP_rhythmbox.get_active():
				result = self.rhythmbox()
			elif self.NP_bmpx.get_active():
				result = self.bmpx()
			elif self.NP_exaile.get_active(): 
					result = self.exaile() 
			elif self.NP_lastfm.get_active(): 
					result = self.lastfm() 
			elif self.NP_foobar.get_active(): 
					result = self.foobar() 
			elif self.NP_other.get_active(): 
					result = self.other() 
			elif self.NP_mpris.get_active():
				result = self.mpris()
		except RuntimeError:
			log.addwarning("ERROR: Could not execute now playing code. Are you sure you picked the right player?")
			result = None
		if not result:
			return None
		# Since we need unicode instead of bytes we'll try to force such a
		# conversion. Individual player commands should have done this already
		# - this is a failsafe.
		oldtitle = copy.copy(self.title)
		self.title_clear()
		for key, value in oldtitle.iteritems():
			try:
				self.title[key] = unicode(value, "UTF-8", "replace")
			except TypeError:
				self.title[key] = value # already unicode
		title = self.NPFormat.child.get_text()
		title = title.replace("%", "%%") # Escaping user supplied % symbols
		#print "Title1: " + title
		title = title.replace("$t", "%(title)s")
		title = title.replace("$a", "%(artist)s")
		title = title.replace("$b", "%(album)s")
		title = title.replace("$c", "%(comment)s")
		title = title.replace("$n", "%(nowplaying)s")
		title = title.replace("$k", "%(track)s")
		title = title.replace("$l", "%(length)s")
		title = title.replace("$y", "%(year)s")
		title = title.replace("$r", "%(bitrate)s")
		title = title.replace("$s", "%(status)s")
		title = title.replace("$f", "%(filename)s")
		title = title.replace("$p", "%(program)s")
		#print "Title2: " + title
		title = title % self.title
		title = ' '.join([x for x in title.replace('\r', '\n').split('\n') if x])
		
		if test:
			self.Example.set_text(title)
			return None
		if title:
			if callback:
				callback(title)
			return title
		return None
		
	def OnNPSave(self, widget):
		if self.NP_infopipe.get_active():
			player = "infopipe"
		elif self.NP_amarok.get_active():
			player = "amarok"
		elif self.NP_amarok2.get_active():
			player = "amarok2"
		elif self.NP_audacious.get_active():
			player = "audacious"
		elif self.NP_mpd.get_active():
			player = "mpd"
		elif self.NP_banshee.get_active():
			player = "banshee"
		#elif self.NP_mp3blaster.get_active():
		#	player = "mp3blaster"
		elif self.NP_rhythmbox.get_active():
			player = "rhythmbox"
		elif self.NP_bmpx.get_active():
			player = "bmpx"
		elif self.NP_exaile.get_active():
			player = "exaile"
		elif self.NP_lastfm.get_active():
			player = "lastfm"
		elif self.NP_foobar.get_active():
			player = "foobar"
		elif self.NP_mpris.get_active():
			player = "mpris"
		elif self.NP_other.get_active():
			player = "other"
			
		self.frame.np.config.sections["players"]["npplayer"] = player
		self.frame.np.config.sections["players"]["npothercommand"] = self.NPCommand.get_text()
		self.frame.np.config.sections["players"]["npformat"] = self.NPFormat.child.get_text()
		self.frame.np.config.writeConfiguration()
		self.quit(None)
		
	
	def get_custom_widget(self, id, string1, string2, int1, int2):
		w = gtk.Label(_("(custom widget: %s)") % id)
		return w
	
	def bmpx(self):
		if self.bus is None:
			self.frame.logMessage(_("ERROR: DBus not available:")+" "+"BMPx"+ " "+ _("cannot be contacted"))
			return
		try:
			bmp_object = self.bus.get_object('org.beepmediaplayer.bmp', '/Core')
			bmp_iface = self.bus.Interface(bmp_object, 'org.beepmediaplayer.bmp')
		except Exception, error:
			self.frame.logMessage(_("ERROR while accessing the %(program)s DBus interface: %(error)s") % {"program": "BMPx", "error": error})
			return
		try:
			if bmp_iface.GetCurrentSource() == -1:
				return None
			metadata = bmp_iface.GetMetadataFromSource(bmp_iface.GetCurrentSource())
			self.title["bitrate"] = str(metadata["bitrate"])
			self.title["track"] = str(metadata["tracknumber"])
			self.title["title"] = metadata["title"]
			self.title["artist"] = metadata["artist"]
			self.title["length"] = self.get_length_time(metadata["time"])
			self.title["nowplaying"] = metadata["artist"] + " - " +metadata["title"] 
			self.title["year"] = str(metadata["date"])
			self.title["album"] = metadata["album"]
			self.title["filename"] = metadata["location"]
			return True
		except Exception, error:
			self.frame.logMessage(_("ERROR while reading data from the %(program)s DBus interface: %(error)s") % {"program": "BMPx", "error": error})
			return None
		
	
	def mpd(self):
		format = self.NPFormat.child.get_text()
		if "$a" in format:
			output = self.mpd_command("%artist%")
			if output:
				self.title["artist"] = output
		if "$t" in format:
			output = self.mpd_command("%title%")
			if output:
				self.title["title"] = output
		if "$n" in format:
			output = self.mpd_command("%artist% - %title%")
			if output:
				self.title["nowplaying"] = output
		if "$f" in format:
			output = self.mpd_command("%file%")
			if output:
				self.title["filename"] = output
		if "$b" in format:
			output = self.mpd_command("%album%")
			if output:
				self.title["album"] = output	

		return True
	def mpd_command(self, command):
		#output = commands.getoutput("mpc --format %s" % command).split('\n')[0]
		output = executeCommand("mpc --format $", command, returnoutput=True).split('\n')[0]
		if output == '' or output.startswith("MPD_HOST") or output.startswith("volume: "):
			return None
		return output
	
	def banshee(self):
		slist = self.NPFormat.child.get_text()
		if "$n" in slist:
			commandlist = ["--query-artist", "--query-title"]
		else:
			commandlist = []
			if "$t" in slist:
				commandlist.append("--query-title")
			if "$a" in slist:
				commandlist.append("--query-artist")
			if "$b" in slist:
				commandlist.append("--query-album")
			if "$k" in slist:
				commandlist.append("--query-track-count")
			if "$l" in slist:
				commandlist.append("--query-duration")
			if "$y" in slist:
				commandlist.append("--query-year")
			if "$r" in slist:
				commandlist.append("--query-bit-rate")
			if "$f" in slist:
				commandlist.append("--query-uri")
		
		if not commandlist:
			return False
		
		output = self.banshee_command(commandlist)

		#print "'"+output+"'"
		matches = {}
		[ matches.__setitem__(i[0].split(':')[0], filter(len, i[1:])[0]) for i in re.findall(r"(?m)^(title: (?P<title>.*?)|artist: (?P<artist>.*?)|album: (?P<album>.*?)|track-number: (?P<track>.*?)|duration: (?P<length>.*?)|year: (?P<year>.*?)|bit-rate: (?P<bitrate>.*?)|uri: (?P<filename>.*?))$", output) ]
		#print matches

		if matches:
			print matches
			if "$n" in slist:
				self.title["nowplaying"] = "%(artist)s - %(title)s" % matches

			for key, value in matches.iteritems():
				if key == "duration":
					# Convert seconds to minutes:seconds
					self.title[key] = "%s:%02d" % (int(round(float(value)/60)), float(value)-(round(float(value)/60)*60))
				elif key == "filename":
					# Convert URI path to normal path
					self.title[key] = value.split('%')[0]+''.join([i[:2].decode('hex')+i[2:] for i in value.split('%')[1:] ]).split('://')[1]
				else:
					self.title[key] = value
			return True
		else:
			return False
	
	def banshee_command(self, commands):
		return executeCommand(" ".join(["banshee"] + commands), returnoutput=True)
		
	def exaile(self):
		slist = self.NPFormat.child.get_text()
		output = executeCommand('exaile --get-album --get-artist --get-length --get-title', returnoutput=True)
		output = output.split('\n')
		self.title["title"] =  output[0]
		self.title["artist"] = output[1]
		self.title["album"] =  output[2]
		self.title["length"] = output[3]
		return True
		
	def amarok2(self):
		slist = self.NPFormat.child.get_text()
		if not self.bus:
			log.addwarning("Failed to import DBus, cannot read out Amarok2")
			return
		player = self.bus.get_object('org.mpris.amarok', '/Player')
		md = player.GetMetadata()
		for key, value in md.iteritems():
			if key == 'mtime':
				# Convert seconds to minutes:seconds
				value = float(value) / 1000
				m, s = divmod(value, 60)
				self.title['length'] = "%d:%02d" % (m, s)
			elif key == 'audio-bitrate':
				self.title['bitrate'] = value
			elif key == "location":
				self.title['filename']
			else:
				self.title[key] = value
			self.title['nowplaying'] = self.title['artist']+' - '+self.title['title']
		return True
	
	def amarok(self):
		slist = self.NPFormat.child.get_text()
		
		if "$n" in slist:
			output = self.amarok_command("nowPlaying")
			if output: self.title["nowplaying"] = output
		if "$t" in slist:
			output = self.amarok_command("title")
			if output: self.title["title"] = output
		if "$l" in slist:
			output = self.amarok_command("totalTime")
			if output: self.title["length"] = output
		if "$a" in slist:
			output = self.amarok_command("artist")
			if output: self.title["artist"] = output
		if "$b" in slist:
			output = self.amarok_command("album")
			if output:
				self.title["album"] = output
		if "$c" in slist:
			output = self.amarok_command("comment")
			if output: self.title["comment"] = output
		if "$k" in slist:
			output = self.amarok_command("track")
			if output: self.title["track"] = output
		if "$y" in slist:
			output = self.amarok_command("year")
			if output and not output == "0":
				self.title["year"] = output
		if "$r" in slist:
			output = self.amarok_command("bitrate")
			if output: self.title["bitrate"] = output
		if "$f" in slist:
			output = self.amarok_command("path")
			if output: self.title["filename"] = output
		if "$s" in slist:
			output = self.amarok_command("status")
			if output:
				status = output
				if status == "0":
					self.title["status"] = "stopped"
				elif status == "1":
					self.title["status"] = "paused"
				elif status == "2":
					self.title["status"] = "playing"
				else:
					self.title["status"] = "unknown"
		return True
		
	def amarok_command(self, command):
		output = executeCommand("dcop amarok player $", command, returnoutput=True).split('\n')[0]
		if output == 'call failed':
			output = None
		return output

	def audacious(self):
		slist = self.NPFormat.child.get_text()
		output = ""
		self.audacious_running = True
		if "$n" in slist:
			artist = self.audacious_command('current-song-tuple-data', 'artist')
			title = self.audacious_command('current-song-tuple-data', 'title')
			if artist and title: self.title["nowplaying"] = artist + ' - ' + title
		if "$t" in slist:
			output = self.audacious_command('current-song-tuple-data', 'title')
			if output: self.title["title"] = output
		if "$l" in slist:
			output = self.audacious_command('current-song-length')
			if output: self.title["length"] = output
		if "$a" in slist:
			output = self.audacious_command('current-song-tuple-data', 'artist')
			if output: self.title["artist"] = output
		if "$b" in slist:
			output = self.audacious_command('current-song-tuple-data', 'album')
			if output: self.title["album"] = output
		if "$c" in slist:
			output = self.audacious_command('current-song-tuple-data', 'comment')
			if output: self.title["comment"] = output
		if "$k" in slist:
			output = self.audacious_command('current-song-tuple-data', 'track-number')
			if output: self.title["track"] = output
		if "$y" in slist:
			output = self.audacious_command('current-song-tuple-data', 'year')
			if output and not output == "0":
				self.title["year"] = output
		if "$r" in slist:
			output = self.audacious_command('current-song-bitrate-kbps')
			if output: self.title["bitrate"] = output
		if "$f" in slist:
			path = self.audacious_command('current-song-filename')
		if "$s" in slist:
			output = self.audacious_command('playback-status')
			if output: self.title["status"] = output
		if not self.audacious_running:
			self.frame.logMessage(_("ERROR: audtool didn't detect a running Audacious session."))
			return False
		return True
		
	def audacious_command(self, command, subcommand = ''):
		#output = commands.getoutput("audtool %s %s" % (command, subcommand)).split('\n')[0]
		try:
			output = executeCommand("audtool %s %s" % (command, subcommand), returnoutput=True).split('\n')[0]
		except RuntimeError:
			output = executeCommand("audtool2 %s %s" % (command, subcommand), returnoutput=True).split('\n')[0]
		if output.startswith('audtool'):
			output = None
			self.audacious_running = False
		return output

	def mp3blaster(self):
		return None
	
	def mpris(self):
		from dbus import Interface
		player = self.NPCommand.get_text()
		dbus_mpris_service = u'org.mpris.MediaPlayer2.'
		dbus_mpris_player_service = u'org.mpris.MediaPlayer2.Player'
		dbus_mpris_path = u'/org/mpris/MediaPlayer2'
		dbus_property = u'org.freedesktop.DBus.Properties'
		if not player:
			names = self.bus.list_names()
			players = []
			for name in names:
				if name.startswith(dbus_mpris_service):
					players.append(name[len(dbus_mpris_service):])
			if not players:
				self.frame.logMessage(_("Could not find a suitable MPRIS player."))
				return None
			player = players[0]
			if len(players) > 1:
				self.frame.logMessage(_("Found multiple MPRIS players: %(players)s. Using: %(player)s") % {'players': players, 'player': player})
			else:
				self.frame.logMessage(_("Auto-detected MPRIS player: %s.") % player)
		try:
			player_obj          = self.bus.get_object(dbus_mpris_service + player, dbus_mpris_path)
			player_property_obj = Interface(player_obj, dbus_interface=dbus_property)
			metadata            = player_property_obj.Get(dbus_mpris_player_service, "Metadata")
		except Exception, exception:
			self.frame.logMessage(_("Something went wrong while querying %(player)s: %(exception)s") % {'player': player, 'exception': exception})
			return None
		print(metadata)
		# See: http://mms2.org/wiki/MPRIS_Metadata
		self.title['program'] = player
		list_mapping = [('xesam:artist', 'artist')]
		for (source, dest) in list_mapping:
			try:
				self.title[dest] = '+'.join(metadata[source])
			except KeyError:
				self.title[dest] = '?'
		mapping = [
				('xesam:title', 'title'),
				('xesam:album', 'album'),
				('xesam:comment', 'comment'),
				('xesam:audioBitrate', 'bitrate'),
				('xesak:trackNumber', 'track'),
			]
		for (source, dest) in mapping:
			try:
				self.title[dest] = unicode(metadata[source])
			except KeyError:
				self.title[dest] = '?'
		# Misc
		try:
			self.title['length'] = self.get_length_time(metadata['mpris:length'] / 1000)
		except KeyError:
			self.title['length'] = '?'
		#
		return True

	def rhythmbox(self):
		from dbus import Interface
		
		if self.bus is None:
			self.frame.logMessage(_("ERROR: DBus not available:")+" "+"Rhythmbox"+ " "+ _("cannot be contacted"))
			return None
		try:
			proxyobj = self.bus.get_object("org.gnome.Rhythmbox", "/org/gnome/Rhythmbox/Shell")
			rbshell = Interface(proxyobj, "org.gnome.Rhythmbox.Shell")
			proxyobj = self.bus.get_object('org.gnome.Rhythmbox', '/org/gnome/Rhythmbox/Player')
			rbplayer = Interface(proxyobj, 'org.gnome.Rhythmbox.Player')
		except Exception, error:
			self.frame.logMessage(_("ERROR while accessing the %(program)s DBus interface: %(error)s") % {"program": "Rhythmbox", "error": error })
			return None

		try:
			metadata = rbshell.getSongProperties(rbplayer.getPlayingUri())
			self.title["bitrate"] = str(metadata["bitrate"])
			self.title["track"] = str(metadata["track-number"])
			self.title["title"] = metadata["title"]
			self.title["artist"] = metadata["artist"]
			self.title["comment"] = metadata["description"]
			self.title["length"] = self.get_length_time(metadata["duration"])
			self.title["nowplaying"] = metadata["artist"] + " - " +metadata["title"] 
			self.title["year"] = str(metadata["year"])
			self.title["album"] = metadata["album"]
			self.title["filename"] = metadata["location"]
			if rbplayer.getPlaying(): 
				self.title["status"] = "playing"
			else:
				self.title["status"] = "paused"
			return True
		except Exception, error:
			self.frame.logMessage(_("ERROR while accessing the %(program)s DBus interface: %(error)s") % {"program": "Rhythmbox", "error": error })
			return None
	
	def foobar(self):
		if HAS_WIN32GUI:
			wnd_ids = [
				'{DA7CD0DE-1602-45e6-89A1-C2CA151E008E}',
				'{97E27FAA-C0B3-4b8e-A693-ED7881E99FC1}',
				'{E7076D1C-A7BF-4f39-B771-BCBE88F2A2A8}'
			]
		
			metadata = None
			
			for wnd_id in wnd_ids:
				wnd_txt = GetWindowText(FindWindow(wnd_id, None))
				if wnd_txt:
					m = re.match("(.*)\s+\[foobar.*", wnd_txt)
					if m:
						metadata = m.groups(0)[0].strip()
						
			if metadata:
				self.title["nowplaying"] = "now playing: " + metadata
				return True
			else:
				return None
		else:
			return None
				
	def get_length_time(self, length):
		if length != '' and length != None:
			minutes = int(length)/60
			seconds = str( int(length) - (60 * minutes))
			if len(seconds) < 2:
				seconds = '0' + seconds
			length = str(minutes)+":"+str(seconds)
		else:
			length = "0:00"
		return length
		
	def lastfm(self):
		def lastfm_parse(buf):
			from time import time, altzone
			try:
				i = buf.index("<artist")
				i = buf[i+1:].index(">") + i + 2
				j = buf[i:].index("<") + i

				artist = buf[i:j];

				i = buf[j:].index("<name>") + j + 6
				j = buf[i:].index("</name>") + i

				title = buf[i:j]
	
				i = buf[j:].index("<date") + j
				j = buf[i:].index('"') + i + 1
				i = buf[j:].index('"') + j

				date = int(buf[j:i]) # utc
				utc_now = time() + altzone
				playing = utc_now - date < 300

				return (playing, artist, title)
			except:
				return (None, None, None)

		try:
			from socket import socket, AF_INET, SOCK_STREAM
		except Exception, error:
			self.frame.logMessage(_("ERROR while loading socket module: %(error)s") % {"command": othercommand, "error": error})
			return None
		
		user = self.NPCommand.get_text()
		host = ("ws.audioscrobbler.com", 80)
		req  = 'GET /2.0/user/%s/recenttracks.xml HTTP/1.1\r\n' \
		       'Host: %s\r\n\r\n' % (user, host[0])

		sock = socket(AF_INET, SOCK_STREAM)

		try:
			sock.connect(host)
		except Exception, error:
			self.frame.logMessage(_("ERROR: could not connect to audioscrobbler: %s")) % error[1]
			return None
					
		sock.send(req)
		data = sock.recv(1024)
		sock.close()

		(status, artist, title) = lastfm_parse(data)

		if status is None:
			return None
		
		slist = self.NPFormat.child.get_text()

		if "$n" in slist:
			self.title["nowplaying"] = "%s: %s - %s" % ((_("Last played"), _("Now playing"))[status], artist, title)
		if "$t" in slist:
			self.title["title"] = title
		if "$a" in slist:
			self.title["artist"] = artist
		if "$s" in slist:
			self.title["status"] = (_("paused"), _("playing"))[status]
		return True

	def other(self):
		try:
			othercommand = self.NPCommand.get_text()
			if othercommand == "":
				return None
			output = executeCommand(othercommand, returnoutput=True)
			self.title["nowplaying"] = output 
			return True
		except Exception, error:
			self.frame.logMessage(_("ERROR: Executing '%(command)s' failed: %(error)s") % {"command": othercommand, "error": error})
			return None
	
	def xmms(self):
		if not os.path.exists("/tmp/xmms-info"):
			self.frame.logMessage(_("ERROR: /tmp/xmms-info does not exist. Is the Infopipe plugin installed and is XMMS running?"))
			return None
		try:
			fsock = file("/tmp/xmms-info")
			do = fsock.read().split("\n")
			fsock.close()
		
			if len(do) == 0:
				self.frame.logMessage(_("ERROR: /tmp/xmms-info is empty. Is the Infopipe plugin installed and is XMMS running?"))
			infolist = []
			for i in do:
				if i == "":
					continue
				infolist.append( i )
			#protocol  = infolist[0][29:]
			#version = infolist[1][25:]
			status = infolist[2][8:]
			#playlist_count = infolist[3][20:]
			#playlist_position = infolist[4][20:]
			#millisec_position = infolist[5][15:]
			position = infolist[6][10:]
			#millisec_time = infolist[7][15:]
			time = infolist[8][6:]
			bitrate = str(int(infolist[9][17:])/1024)
			frequency = infolist[10][20:]
			channels = infolist[11][10:]
			title = infolist[12][7:]
			filename = infolist[13][7:]
			self.title = { "title": "",  "artist": "", "comment": "", "year": "", "album": "", "track":"", "nowplaying": title, "length": time, "bitrate": bitrate, "channels": channels, "position": position, "filename": filename, "status": status}

			return True
		except:
			return None

if __name__ == "__main__":
	print("Debug mode.")
	class FakeInputBox(object):
		def __init__(self, text=''):
			self.set_text(text)
		def get_text(self):
			return self.text
		def set_text(self, text):
			self.text = text
	class FakeFrame(object):
		@classmethod
		def logMessage(cls, text):
			print("logMessage: %s" % text)
	fakenp = NowPlaying(FakeFrame(), fake=True)
	fakenp.NPCommand = FakeInputBox('') # if not empty specifies the player
	fakenp.Example = FakeInputBox()
	fakenp.title_clear()
	answer = fakenp.mpris()
	print("MPIS answered: %s" % answer)
	print("Meta-info: %s" % fakenp.title)
