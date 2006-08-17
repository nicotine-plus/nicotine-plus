# Copyright (c) 2003-2004 Hyriand. All rights reserved.
#
import gtk
import gobject
import settings_glade
import locale

from dirchooser import ChooseDir
from utils import InputDialog, InitialiseColumns, recode, recode2, popupWarning
import os, pwd
from pynicotine.utils import _

class ServerFrame(settings_glade.ServerFrame):
	def __init__(self, encodings):
		settings_glade.ServerFrame.__init__(self, False)
		self.Server.append_text("server.slsknet.org:2240")
		for code in encodings:
			self.Encoding.append_text(code)

	def SetSettings(self, config):
		server = config["server"]
		if server["server"] is not None:
			self.Server.child.set_text("%s:%i" % (server["server"][0], server["server"][1]))
		else:
			self.Server.child.set_text("server.slsknet.org:2240")
		if server["login"] is not None:
			self.Login.set_text(server["login"])
		if server["passw"] is not None:
			self.Password.set_text(server["passw"])
		if server["enc"] is not None:
			self.Encoding.child.set_text(server["enc"])
		if server["portrange"] is not None:
			self.FirstPort.set_text(str(server["portrange"][0]))
			self.LastPort.set_text(str(server["portrange"][1]))
		if server["firewalled"] is not None:
			self.DirectConnection.set_active(not server["firewalled"])
		if server["ctcpmsgs"] is not None:
			self.ctcptogglebutton.set_active(not server["ctcpmsgs"])
			
	def GetSettings(self):
		try:
			server = self.Server.child.get_text().split(":")
			server[1] = int(server[1])
			server = tuple(server)
		except:
			server = None

		try:
			firstport = int(self.FirstPort.get_text())
			lastport = int(self.LastPort.get_text())
			portrange = (firstport, lastport)
		except:
			portrange = None
		
		return {
			"server": {
				"server": server,
				"login": self.Login.get_text(),
				"passw": self.Password.get_text(),
				"enc": self.Encoding.child.get_text(),
				"portrange": portrange,
				"firewalled": not self.DirectConnection.get_active(),
				"ctcpmsgs": not self.ctcptogglebutton.get_active(),
			}
		}

class SharesFrame(settings_glade.SharesFrame):
	def __init__(self):
		settings_glade.SharesFrame.__init__(self, False)
		self.needrescan = 0
		self.shareslist = gtk.ListStore(gobject.TYPE_STRING, gobject.TYPE_STRING)
		self.shareddirs = []
		
		self.bshareslist = gtk.ListStore(gobject.TYPE_STRING, gobject.TYPE_STRING)
		self.bshareddirs = []

		column = gtk.TreeViewColumn("Shared dirs", gtk.CellRendererText(), text = 0)
		self.Shares.append_column(column)
		self.Shares.set_model(self.shareslist)
		self.Shares.get_selection().set_mode(gtk.SELECTION_MULTIPLE)
		
		bcolumn = gtk.TreeViewColumn("Buddy Shared dirs", gtk.CellRendererText(), text = 0)
		self.BuddyShares.append_column(bcolumn)
		self.BuddyShares.set_model(self.bshareslist)
		self.BuddyShares.get_selection().set_mode(gtk.SELECTION_MULTIPLE)

	def SetSettings(self, config):
		transfers = config["transfers"]
		homedir = pwd.getpwuid(os.getuid())[5]
		if transfers["incompletedir"] is not None:
			self.IncompleteDir.set_text(recode(transfers["incompletedir"]))
		if transfers["downloaddir"] is not None:
			self.DownloadDir.set_text(recode(transfers["downloaddir"]))
		if transfers["sharedownloaddir"] is not None:
			if homedir == transfers["downloaddir"] and transfers["sharedownloaddir"]:
				popupWarning(None, "Warning","Security Risk: you should not share your home directory!")
			self.ShareDownloadDir.set_active(transfers["sharedownloaddir"])
		self.shareslist.clear()
		self.bshareslist.clear()
		
		if transfers["shared"] is not None:
			for share in transfers["shared"]:
				if homedir == share:
					popupWarning(None, "Warning","Security Risk: you should not share your home directory!")
				self.shareslist.append([recode(share), share])
			self.shareddirs = transfers["shared"][:]
		if transfers["buddyshared"] is not None:
			for share in transfers["buddyshared"]:
				if homedir == share:
					popupWarning(None, "Warning","Security Risk: you should not share your home directory!")
				self.bshareslist.append([recode(share), share])
			self.bshareddirs = transfers["buddyshared"][:]
		if transfers["rescanonstartup"] is not None:
			self.RescanOnStartup.set_active(transfers["rescanonstartup"])
		if transfers["enablebuddyshares"] is not None:
			self.enableBuddyShares.set_active(transfers["enablebuddyshares"])
		self.OnEnabledBuddySharesToggled(self.enableBuddyShares)
		self.needrescan = 0

	def GetSettings(self):
		return {
			"transfers": {
				"incompletedir": recode2(self.IncompleteDir.get_text()),
				"downloaddir": recode2(self.DownloadDir.get_text()),
				"sharedownloaddir": self.ShareDownloadDir.get_active(),
				"shared": self.shareddirs[:],
				"rescanonstartup": self.RescanOnStartup.get_active(),
				"buddyshared": self.bshareddirs[:],
				"enablebuddyshares": self.enableBuddyShares.get_active(),
			}
		}
	def OnEnabledBuddySharesToggled(self, widget):
		sensitive = widget.get_active()
		self.BuddyShares.set_sensitive(sensitive)
		self.addBuddySharesButton.set_sensitive(sensitive)
		self.removeBuddySharesButton.set_sensitive(sensitive)
		
	def GetNeedRescan(self):
		return self.needrescan
	
	def OnChooseIncompleteDir(self, widget):
		dir = ChooseDir(self.Main.get_toplevel(), self.IncompleteDir.get_text())
		if dir is not None:
			for directory in dir: # iterate over selected files
				self.incompletedir = directory
				self.IncompleteDir.set_text(recode(directory))

	def OnChooseDownloadDir(self, widget):
		dir = ChooseDir(self.Main.get_toplevel(), self.DownloadDir.get_text())

		if dir is not None:
			for directory in dir: # iterate over selected files
				self.DownloadDir.set_text(recode(directory))
				if self.ShareDownloadDir.get_active():
					self.needrescan = 1

	def OnAddSharedDir(self, widget):
		dir1 = ChooseDir(self.Main.get_toplevel())
		if dir1 is not None:
		    for directory in dir1:
			if directory not in self.shareddirs:
			    self.shareslist.append([recode(directory), directory])
			    self.shareddirs.append(directory)
			    self.needrescan = 1
			    
	def OnAddSharedBuddyDir(self, widget):
		dir1 = ChooseDir(self.Main.get_toplevel())
		if dir1 is not None:
		    for directory in dir1:
			if directory not in self.bshareddirs:
			    self.bshareslist.append([recode(directory), directory])
			    self.bshareddirs.append(directory)
			    self.needrescan = 1
			    
	def _RemoveSharedDir(self, model, path, iter, list):
		list.append(iter)

	def OnRemoveSharedDir(self, widget):
		iters = []
		self.Shares.get_selection().selected_foreach(self._RemoveSharedDir, iters)
		for iter in iters:
			dir = self.shareslist.get_value(iter, 1)
			self.shareddirs.remove(dir)
			self.shareslist.remove(iter)
		if iters:
			self.needrescan =1
			
	def OnRemoveSharedBuddyDir(self, widget):
		iters = []
		self.BuddyShares.get_selection().selected_foreach(self._RemoveSharedDir, iters)
		for iter in iters:
			dir = self.bshareslist.get_value(iter, 1)
			self.bshareddirs.remove(dir)
			self.bshareslist.remove(iter)
		if iters:
			self.needrescan =1
			
	def OnShareDownloadDirToggled(self, widget):
		self.needrescan = 1

class TransfersFrame(settings_glade.TransfersFrame):
	def __init__(self):
		settings_glade.TransfersFrame.__init__(self, False)

	def SetSettings(self, config):
		transfers = config["transfers"]
		server = config["server"]
		if transfers["uploadbandwidth"] is not None:
			self.QueueBandwidth.set_text(str(transfers["uploadbandwidth"]))
		if transfers["useupslots"] is not None:
			self.QueueUseSlots.set_active(transfers["useupslots"])
		if transfers["uploadslots"] is not None:
			self.QueueSlots.set_text(str(transfers["uploadslots"]))
		if transfers["uselimit"] is not None:
			self.Limit.set_active(transfers["uselimit"])
		if transfers["uploadlimit"] is not None:
			self.LimitSpeed.set_text(str(transfers["uploadlimit"]))
		if transfers["limitby"] is not None:
			if transfers["limitby"] == 0:
				self.LimitPerTransfer.set_active(1)
			else:
				self.LimitTotalTransfers.set_active(1)
		if transfers["queuelimit"] is not None:
			self.MaxUserQueue.set_text(str(transfers["queuelimit"]))
		if transfers["friendsnolimits"] is not None:
			self.FriendsNoLimits.set_active(transfers["friendsnolimits"])
		if transfers["friendsonly"] is not None:
			self.FriendsOnly.set_active(transfers["friendsonly"])
		if transfers["preferfriends"] is not None:
			self.PreferFriends.set_active(transfers["preferfriends"])
		if transfers["lock"] is not None:
			self.LockIncoming.set_active(transfers["lock"])
		if transfers["remotedownloads"] is not None:
			self.RemoteDownloads.set_active(transfers["remotedownloads"])
		if transfers["fifoqueue"] is not None:
			self.FirstInFirstOut.set_active(transfers["fifoqueue"])
		self.OnQueueUseSlotsToggled(self.QueueUseSlots)
		self.OnLimitToggled(self.Limit)
		self.OnFriendsOnlyToggled(self.FriendsOnly)
	
	def GetSettings(self):
		try:
			uploadbandwidth = int(self.QueueBandwidth.get_text())
		except:
			uploadbandwidth = None
		
		try:
			uploadslots = int(self.QueueSlots.get_text())
		except:
			uploadslots = None
		
		try:
			uploadlimit = int(self.LimitSpeed.get_text())
		except:
			uploadlimit = None
			self.Limit.set_active(0)
		try:
			queuelimit = int(self.MaxUserQueue.get_text())
		except:
			queuelimit = None
		
		return {
			"transfers": {
				"uploadbandwidth": uploadbandwidth,
				"useupslots": self.QueueUseSlots.get_active(),
				"uploadslots": uploadslots,
				"uselimit": self.Limit.get_active(),
				"uploadlimit": uploadlimit,
				"fifoqueue": self.FirstInFirstOut.get_active(),
				"limitby": self.LimitTotalTransfers.get_active(),
				"queuelimit": queuelimit,
				"friendsnolimits": self.FriendsNoLimits.get_active(),
				"friendsonly": self.FriendsOnly.get_active(),
				"preferfriends": self.PreferFriends.get_active(),
				"lock": self.LockIncoming.get_active(),
				"remotedownloads": self.RemoteDownloads.get_active(),
			},
		}

	def OnQueueUseSlotsToggled(self, widget):
		sensitive = widget.get_active()
		self.QueueSlots.set_sensitive(sensitive)
	
	def OnLimitToggled(self, widget):
		sensitive = widget.get_active()
		for w in self.LimitSpeed, self.LimitPerTransfer, self.LimitTotalTransfers:
			w.set_sensitive(sensitive)
	
	def OnFriendsOnlyToggled(self, widget):
		sensitive = not widget.get_active()
		self.PreferFriends.set_sensitive(sensitive)

class GeoBlockFrame(settings_glade.GeoBlockFrame):
	def __init__(self):
		settings_glade.GeoBlockFrame.__init__(self, False)
	
	def SetSettings(self, config):
		transfers = config["transfers"]
		if transfers["geoblock"] is not None:
			self.GeoBlock.set_active(transfers["geoblock"])
		if transfers["geopanic"] is not None:
			self.GeoPanic.set_active(transfers["geopanic"])
		if transfers["geoblockcc"] is not None:
			self.GeoBlockCC.set_text(transfers["geoblockcc"][0])
		self.OnGeoBlockToggled(self.GeoBlock)
	
	def GetSettings(self):
		return {
			"transfers": {
				"geoblock": self.GeoBlock.get_active(),
				"geopanic": self.GeoPanic.get_active(),
				"geoblockcc": [self.GeoBlockCC.get_text().upper()],
			}
		}

	def OnGeoBlockToggled(self, widget):
		sensitive = widget.get_active()
		self.GeoPanic.set_sensitive(sensitive)
		self.GeoBlockCC.set_sensitive(sensitive)

class UserinfoFrame(settings_glade.UserinfoFrame):
	def __init__(self):
		settings_glade.UserinfoFrame.__init__(self, False)

	def SetSettings(self, config):
		userinfo = config["userinfo"]
		if userinfo["descr"] is not None:
			descr = eval(userinfo["descr"], {})
			self.Description.get_buffer().set_text(descr)
		if userinfo["pic"] is not None:
			self.Image.set_text(userinfo["pic"])

	def GetSettings(self):
		buffer = self.Description.get_buffer()
		start = buffer.get_start_iter()
		end = buffer.get_end_iter()
		descr = buffer.get_text(start, end).replace("; ", ", ").__repr__()
		return {
			"userinfo": {
				"descr": descr,
				"pic": recode2(self.Image.get_text()),
				"descrutf8": 1,
			}
		}
		
	def OnChooseImage(self, widget):
		dlg = gtk.FileSelection()
		dlg.set_filename(self.Image.get_text())
		result = dlg.run()
		if result == gtk.RESPONSE_OK:
			self.Image.set_text(dlg.get_filename())
		dlg.destroy()

class BanFrame(settings_glade.BanFrame):
	def __init__(self):
		settings_glade.BanFrame.__init__(self, False)
		self.banned = []
		self.banlist = gtk.ListStore(gobject.TYPE_STRING)
		column = gtk.TreeViewColumn("Users", gtk.CellRendererText(), text = 0)
		self.Banned.append_column(column)
		self.Banned.set_model(self.banlist)
		self.Banned.get_selection().set_mode(gtk.SELECTION_MULTIPLE)

		self.ignored = []
		self.ignorelist = gtk.ListStore(gobject.TYPE_STRING)
		column = gtk.TreeViewColumn("Users", gtk.CellRendererText(), text = 0)
		self.Ignored.append_column(column)
		self.Ignored.set_model(self.ignorelist)
		self.Ignored.get_selection().set_mode(gtk.SELECTION_MULTIPLE)
		
	def SetSettings(self, config):
		server = config["server"]
		transfers = config["transfers"]
		self.banlist.clear()
		self.ignorelist.clear()
		if server["banlist"] is not None:
			self.banned = server["banlist"][:]
			for banned in server["banlist"]:
				self.banlist.append([banned])
		if server["ignorelist"] is not None:
			self.ignored = server["ignorelist"][:]
			for ignored in server["ignorelist"]:
				self.ignorelist.append([ignored])
		if transfers["usecustomban"] is not None:
			self.UseCustomBan.set_active(transfers["usecustomban"])
		if transfers["customban"] is not None:
			self.CustomBan.set_text(transfers["customban"])
			
		self.OnUseCustomBanToggled(self.UseCustomBan)
	
	def GetSettings(self):
		return {
			"server": {
				"banlist": self.banned[:],
				"ignorelist": self.ignored[:],
			},
			"transfers": {
				"usecustomban": self.UseCustomBan.get_active(),
				"customban": self.CustomBan.get_text(),
			}
		}
	
	def OnAddBanned(self, widget):
		user = InputDialog(self.Main.get_toplevel(), "Ban user...", "User:")
		if user and user not in self.banned:
			self.banned.append(user)
			self.banlist.append([user])
	
	def _RemoveBanned(self, model, path, iter, l):
		l.append(iter)
	
	def OnRemoveBanned(self, widget):
		iters = []
		self.Banned.get_selection().selected_foreach(self._RemoveBanned, iters)
		for iter in iters:
			user = self.banlist.get_value(iter, 0)
			self.banned.remove(user)
			self.banlist.remove(iter)

	def OnClearBanned(self, widget):
		self.banned = []
		self.banlist.clear()

	def OnAddIgnored(self, widget):
		user = InputDialog(self.Main.get_toplevel(), "Ignore user...", "User:")
		if user and user not in self.ignored:
			self.ignored.append(user)
			self.ignorelist.append([user])
	
	def OnRemoveIgnored(self, widget):
		iters = []
		self.Ignored.get_selection().selected_foreach(self._RemoveBanned, iters)
		for iter in iters:
			user = self.ignorelist.get_value(iter, 0)
			self.ignored.remove(user)
			self.ignorelist.remove(iter)

	def OnClearIgnored(self, widget):
		self.ignored = []
		self.ignorelist.clear()

	def OnUseCustomBanToggled(self, widget):
		self.CustomBan.set_sensitive(widget.get_active())

class BloatFrame(settings_glade.BloatFrame):
	def __init__(self):
		settings_glade.BloatFrame.__init__(self, False)
		for item in ["<None>", ",", ".", "<space>"]:
			self.DecimalSep.append_text(item)
		#self.font =""
		self.ThemeButton.connect("clicked", self.OnChooseThemeDir)
		#self.SelectChatFont.connect("font-set", self.OnChooseChatFont)
		
		self.PickRemote.connect("clicked", self.PickColour, self.Remote)
		self.PickLocal.connect("clicked", self.PickColour, self.Local)
		self.PickMe.connect("clicked", self.PickColour, self.Me)
		self.PickHighlight.connect("clicked", self.PickColour, self.Highlight)
		self.PickImmediate.connect("clicked", self.PickColour, self.Immediate)
		self.PickQueue.connect("clicked", self.PickColour, self.Queue)

		self.DefaultRemote.connect("clicked", self.DefaultColour, self.Remote)
		self.DefaultLocal.connect("clicked", self.DefaultColour, self.Local)
		self.DefaultMe.connect("clicked", self.DefaultColour, self.Me)
		self.DefaultHighlight.connect("clicked", self.DefaultColour, self.Highlight)
		self.DefaultImmediate.connect("clicked", self.DefaultColour, self.Immediate)
		self.DefaultQueue.connect("clicked", self.DefaultColour, self.Queue)
		
	def OnChooseThemeDir(self, widget):
		dir = ChooseDir(self.Main.get_toplevel(), self.IconTheme.get_text())
		if dir is not None:
			for directory in dir: # iterate over selected files
				self.IconTheme.set_text(recode(directory))
				
	def SetSettings(self, config):
		ui = config["ui"]
		transfers = config["transfers"]
		if ui["icontheme"] is not None:
			self.IconTheme.set_text(ui["icontheme"])
		if ui["chatfont"] is not None:
			self.SelectChatFont.set_font_name(ui["chatfont"])
			
		if ui["chatlocal"] is not None:
			self.Local.set_text(ui["chatlocal"])
		if ui["chatremote"] is not None:
			self.Remote.set_text(ui["chatremote"])
		if ui["chatme"] is not None:
			self.Me.set_text(ui["chatme"])
		if ui["chathilite"] is not None:
			self.Highlight.set_text(ui["chathilite"])
		if ui["search"] is not None:
			self.Immediate.set_text(ui["search"])
		if ui["searchq"] is not None:
			self.Queue.set_text(ui["searchq"])
		if ui["decimalsep"] is not None:
			self.DecimalSep.child.set_text(ui["decimalsep"])
		if ui["tabclosers"] is not None:
			self.TabClosers.set_active(ui["tabclosers"])

	def GetSettings(self):
		return {
			"ui": {
				"icontheme": self.IconTheme.get_text(),
				"chatfont": self.SelectChatFont.get_font_name(),
				"chatlocal": self.Local.get_text(),
				"chatremote": self.Remote.get_text(),
				"chatme": self.Me.get_text(),
				"chathilite": self.Highlight.get_text(),
				"search": self.Immediate.get_text(),
				"searchq": self.Queue.get_text(),
				"decimalsep": self.DecimalSep.child.get_text(),
				"tabclosers": self.TabClosers.get_active(),
			},
		}
	
	def PickColour(self, widget, entry):
		dlg = gtk.ColorSelectionDialog("Pick a colour, any colour")
		colour = entry.get_text()
		if colour != None and colour !='':
			colour = gtk.gdk.color_parse(colour)
			dlg.colorsel.set_current_color(colour)
		if dlg.run() == gtk.RESPONSE_OK:
			colour = dlg.colorsel.get_current_color()
			colour = "#%02X%02X%02X" % (colour.red / 256, colour.green / 256, colour.blue / 256)
			entry.set_text(colour)
		dlg.destroy()
		
	def DefaultColour(self, widget, entry):
		entry.set_text("")
			
class LogFrame(settings_glade.LogFrame):
	def __init__(self):
		settings_glade.LogFrame.__init__(self, False)

	def SetSettings(self, config):
		logging = config["logging"]
		if logging["privatechat"] is not None:
			self.LogPrivate.set_active(logging["privatechat"])
		if logging["chatrooms"] is not None:
			self.LogRooms.set_active(logging["chatrooms"])
		if logging["transfers"] is not None:
			self.LogTransfers.set_active(logging["transfers"])
		if logging["logsdir"] is not None:
			self.LogDir.set_text(recode(logging["logsdir"]))

	def GetSettings(self):
		return {
			"logging": {
				"privatechat": self.LogPrivate.get_active(),
				"chatrooms": self.LogRooms.get_active(),
				"logsdir": recode2(self.LogDir.get_text()),
				"transfers": self.LogTransfers.get_active(),
			}
		}

	def OnChooseLogDir(self, widget):
		dir = ChooseDir(self.Main.get_toplevel(), self.LogDir.get_text())
		if dir is not None:
			for directory in dir: # iterate over selected files
				self.LogDir.set_text(recode(directory))


class SearchFrame(settings_glade.SearchFrame):
	def __init__(self):
		settings_glade.SearchFrame.__init__(self, False)

	def SetSettings(self, config):
		try:
			searches = config["searches"]
		except:
			searches = None
		
		if searches["maxresults"] is not None:
			self.MaxResults.set_text(str(searches["maxresults"]))
		if searches["enablefilters"] is not None:
			self.EnableFilters.set_active(searches["enablefilters"])
		if searches["re_filter"] is not None:
			self.RegexpFilters.set_active(searches["re_filter"])
		if searches["defilter"] is not None:
			self.FilterIn.set_text(searches["defilter"][0])
			self.FilterOut.set_text(searches["defilter"][1])
			self.FilterSize.set_text(searches["defilter"][2])
			self.FilterBR.set_text(searches["defilter"][3])
			self.FilterFree.set_active(searches["defilter"][4])
			if(len(searches["defilter"]) > 5):
				self.FilterCC.set_text(searches["defilter"][5])

	def GetSettings(self):
		maxresults = int(self.MaxResults.get_text())
		return {
			"searches": {
				"maxresults": maxresults,
				"enablefilters": self.EnableFilters.get_active(),
				"re_filter": self.RegexpFilters.get_active(),
				"defilter": [
					self.FilterIn.get_text(),
					self.FilterOut.get_text(),
					self.FilterSize.get_text(),
					self.FilterBR.get_text(),
					self.FilterFree.get_active(),
					self.FilterCC.get_text(),
				],
			}
		}

	def OnEnableFiltersToggled(self, widget):
		active = widget.get_active()
		for w in self.FilterIn, self.FilterOut, self.FilterSize, self.FilterBR, self.FilterFree:
			w.set_sensitive(active)

class AwayFrame(settings_glade.AwayFrame):
	def __init__(self):
		settings_glade.AwayFrame.__init__(self, False)
	
	def SetSettings(self, config):		
		server = config["server"]
		if server["autoreply"] is not None:
			self.AutoReply.set_text(server["autoreply"])
		if server["autoaway"] is not None:
			self.AutoAway.set_text(str(server["autoaway"]))

	def GetSettings(self):
		try:
			autoaway = int(self.AutoAway.get_text())
		except:
			autoaway = None
		return {
			"server": {
				"autoaway": autoaway,
				"autoreply": self.AutoReply.get_text(),
			}
		}

class EventsFrame(settings_glade.EventsFrame):
	def __init__(self):
		settings_glade.EventsFrame.__init__(self, False)
	
	def SetSettings(self, config):
		transfers = config["transfers"]
		if transfers["afterfinish"] is not None:
			self.AfterDownload.set_text(transfers["afterfinish"])
		if transfers["afterfolder"] is not None:
			self.AfterFolder.set_text(transfers["afterfolder"])
		if config["players"]["default"] is not None:
			self.audioPlayerCombo.child.set_text(config["players"]["default"])
			self.audioPlayerCombo.append_text( config["players"]["default"] ) 
	def GetSettings(self):
		return {
			"transfers": {
				"afterfinish": self.AfterDownload.get_text(),
				"afterfolder": self.AfterFolder.get_text(),
				
			},
			"players": { 
				"default": self.audioPlayerCombo.child.get_text(),
			}
		}

class UrlCatchFrame(settings_glade.UrlCatchFrame):
	def __init__(self):
		settings_glade.UrlCatchFrame.__init__(self, False)
		self.protocolmodel = gtk.ListStore(gobject.TYPE_STRING, gobject.TYPE_STRING)
		self.protocols = {}
		cols = InitialiseColumns(self.ProtocolHandlers,
			[_("Protocol"), -1, "text"],
			[_("Handler"), -1, "text"],
		)
		self.ProtocolHandlers.set_model(self.protocolmodel)
		self.ProtocolHandlers.get_selection().connect("changed", self.OnSelect)

	def SetSettings(self, config):
		self.protocolmodel.clear()
		self.protocols = {}
		urls = config["urls"]
		if urls["urlcatching"] is not None:
			self.URLCatching.set_active(urls["urlcatching"])
		if urls["humanizeurls"] is not None:
			self.HumanizeURLs.set_active(urls["humanizeurls"])
		if urls["protocols"] is not None:
			for key in urls["protocols"].keys():
				iter = self.protocolmodel.append([key, urls["protocols"][key]])
				self.protocols[key] = [iter, urls["protocols"][key]]

		self.OnURLCatchingToggled(self.URLCatching)

	def GetSettings(self):
		protocols = {}
		for key in self.protocols.keys():
			protocols[key] = self.protocols[key][1]
		return {
			"urls": {
				"urlcatching": self.URLCatching.get_active(),
				"humanizeurls": self.HumanizeURLs.get_active(),
				"protocols": protocols,
			}
		}

	def OnURLCatchingToggled(self, widget):
		self.HumanizeURLs.set_active(widget.get_active())

	def OnSelect(self, selection):
		model, iter = selection.get_selected()
		if iter == None:
			self.Protocol.set_text("")
		else:
			protocol = model.get_value(iter, 0)
			handler = model.get_value(iter, 1)
			self.Protocol.set_text(protocol)
			self.Handler.set_text(handler)

	def OnUpdate(self, widget):
		key = self.Protocol.get_text()
		value = self.Handler.get_text()
		if self.protocols.has_key(key):
			self.protocols[key][1] = value
			self.protocolmodel.set(self.protocols[key][0], 1, value)
		else:
			iter = self.protocolmodel.append([key, value])
			self.protocols[key] = [iter, value]

	def OnRemove(self, widget):
		key = self.Protocol.get_text()
		if not self.protocols.has_key(key):
			return
		self.protocolmodel.remove(self.protocols[key][0])
		del self.protocols[key]

class ConnectionFrame(settings_glade.ConnectionFrame):
	def __init__(self):
		settings_glade.ConnectionFrame.__init__(self, False)
	def SetSettings(self, config):
		return {}
	def GetSettings(self):
		return {}
		
class UIFrame(settings_glade.UIFrame):
	def __init__(self):
		settings_glade.UIFrame.__init__(self, False)
	def SetSettings(self, config):
		return {}
	def GetSettings(self):
		return {}

class MiscFrame(settings_glade.MiscFrame):
	def __init__(self):
		settings_glade.MiscFrame.__init__(self, False)
	def SetSettings(self, config):
		return {}
	def GetSettings(self):
		return {}
		
		
		
class SettingsWindow(settings_glade.SettingsWindow):
	def __init__(self, frame):
		settings_glade.SettingsWindow.__init__(self)

		gobject.signal_new("settings-closed", gtk.Window, gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_STRING,))
		
		self.SettingsWindow.set_transient_for(frame.MainWindow)

		self.SettingsWindow.connect("delete-event", self.OnDelete)
		
		self.empty_label = gtk.Label("")
		self.empty_label.show()
		self.viewport1.add(self.empty_label)
		
		self.pages = p = {}
		model = gtk.TreeStore(gobject.TYPE_STRING)

		row = model.append(None, [_("Connection")])
		model.append(row, [_("Server")])
		model.append(row, [_("Shares")])
		model.append(row, [_("Transfers")])
		try:
			import GeoIP
			model.append(row, [_("Geo Block")])
		except ImportError:
			try:
				import _GeoIP
				model.append(row, [_("Geo Block")])
			except ImportError:
				pass

		row = model.append(None, [_("UI")])
		model.append(row, [_("Interface")])
		model.append(row, [_("URL Catching")])
		
		row = model.append(None, [_("Misc")])
		model.append(row, [_("Away mode")])
		model.append(row, [_("User info")])
		model.append(row, [_("Ban / ignore")])
		model.append(row, [_("Logging")])
		model.append(row, [_("Searches")])
		model.append(row, [_("Events")])
		
		p[_("Server")] = ServerFrame(frame.np.getencodings())
		p[_("Shares")] = SharesFrame()
		p[_("Connection")] = ConnectionFrame()
		p[_("Transfers")] = TransfersFrame()
		p[_("Geo Block")] = GeoBlockFrame()
		p[_("User info")] = UserinfoFrame()
		p[_("Ban / ignore")] = BanFrame()
		p[_("UI")] = UIFrame()
		p[_("Interface")] = BloatFrame()
		p[_("URL Catching")] = UrlCatchFrame()
		p[_("Misc")] = MiscFrame()
		p[_("Logging")] = LogFrame()
		p[_("Searches")] = SearchFrame()
		p[_("Away mode")] = AwayFrame()
		p[_("Events")] = EventsFrame()
		
		column = gtk.TreeViewColumn(_("Categories"), gtk.CellRendererText(), text = 0)

		self.SettingsTreeview.set_model(model)
		self.SettingsTreeview.append_column(column)

		self.SettingsTreeview.expand_row((0,), True)
		self.SettingsTreeview.expand_row((1,), True)
		self.SettingsTreeview.expand_row((2,), True)

		self.SettingsTreeview.get_selection().connect("changed", self.switch_page)
	
	def switch_page(self, widget):
		child = self.viewport1.get_child()
		if child:
			self.viewport1.remove(child)
		model, iter = widget.get_selected()
		if iter is None:
			self.viewport1.add(self.empty_label)
			return
		page = model.get_value(iter, 0)
		if self.pages.has_key(page):
			self.viewport1.add(self.pages[page].Main)
		else:
			self.viewport1.add(self.empty_label)

	def OnApply(self, widget):
		self.SettingsWindow.emit("settings-closed", "apply")

	def OnOk(self, widget):
		self.SettingsWindow.hide()
		self.SettingsWindow.emit("settings-closed", "ok")

	def OnCancel(self, widget):
		self.SettingsWindow.hide()
		self.SettingsWindow.emit("settings-closed", "cancel")
		
	def OnDelete(self, widget, event):
		self.OnCancel(widget)
		widget.emit_stop_by_name("delete-event")
		return True

	def SetSettings(self, config):
		for page in self.pages.values():
			page.SetSettings(config)

	def GetSettings(self):
		config = {
			"server": {},
			"transfers": {},
			"userinfo": {},
			"logging": {},
			"searches": {},
			"ui": {},
			"urls": {},
			"players": {},
		}
		
		for page in self.pages.values():
			sub = page.GetSettings()
			for (key,data) in sub.items():
				config[key].update(data)
		return self.pages[_("Shares")].GetNeedRescan(), config
