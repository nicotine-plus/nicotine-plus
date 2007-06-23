# Copyright (c) 2003-2004 Hyriand. All rights reserved.
#
import gtk
import gobject
import settings_glade
import locale
import re
from dirchooser import *
from utils import InputDialog, InitialiseColumns, recode, recode2, popupWarning, ImportWinSlskConfig
from entrydialog import *
import os, sys
win32 = sys.platform.startswith("win")
if win32:
	pass
else:
	import pwd
from pynicotine.utils import _

class ServerFrame(settings_glade.ServerFrame):
	def __init__(self, parent, encodings):
		self.p = parent
		self.frame = parent.frame
		settings_glade.ServerFrame.__init__(self, False)
		self.Server.append_text("server.slsknet.org:2240")
		self.Server.append_text("server.slsknet.org:2242")

		self.Elist = {}
		self.EncodingStore = gtk.ListStore(gobject.TYPE_STRING, gobject.TYPE_STRING)
		self.Encoding.set_model(self.EncodingStore)
		cell2 = gtk.CellRendererText()
		self.Encoding.pack_start(cell2, False)
		self.Encoding.add_attribute(cell2, 'text', 1)
		for item in encodings:
			self.Elist[item[1]] = self.EncodingStore.append([item[1], item[0] ])

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
		if str(self.Login.get_text()) == "None":
			popupWarning(self.p.SettingsWindow, _("Warning: Bad Username"), _("Username 'None' is not a good one, please pick another."), self.frame.images["n"] )
			raise UserWarning
		try:
			firstport = int(self.FirstPort.get_text())
			lastport = int(self.LastPort.get_text())
			portrange = (firstport, lastport)
		except:
			portrange = None
			popupWarning(self.p.SettingsWindow, _("Warning: Invalid ports"), _("Client ports are invalid."), self.frame.images["n"] )
			raise UserWarning
		
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
	def __init__(self, parent):
		self.p = parent
		self.frame = parent.frame
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
		
		if transfers["incompletedir"] is not None:
			self.IncompleteDir.set_text(recode(transfers["incompletedir"]))
		if transfers["downloaddir"] is not None:
			self.DownloadDir.set_text(recode(transfers["downloaddir"]))
		if transfers["sharedownloaddir"] is not None:
			
			self.ShareDownloadDir.set_active(transfers["sharedownloaddir"])
		self.shareslist.clear()
		self.bshareslist.clear()
		
		if transfers["shared"] is not None:
			for share in transfers["shared"]:
				self.shareslist.append([recode(share), share])
			self.shareddirs = transfers["shared"][:]
		if transfers["buddyshared"] is not None:
			for share in transfers["buddyshared"]:
				self.bshareslist.append([recode(share), share])
			self.bshareddirs = transfers["buddyshared"][:]
		if transfers["rescanonstartup"] is not None:
			self.RescanOnStartup.set_active(transfers["rescanonstartup"])
		if transfers["enablebuddyshares"] is not None:
			self.enableBuddyShares.set_active(transfers["enablebuddyshares"])
		self.OnEnabledBuddySharesToggled(self.enableBuddyShares)
		self.needrescan = 0

	def GetSettings(self):
		if win32:
			place = "Windows"
			homedir = "C:\windows"
		else:
			place = "Home"
			homedir = pwd.getpwuid(os.getuid())[5]
		if homedir == recode2(self.DownloadDir.get_text()) and self.ShareDownloadDir.get_active():
			popupWarning(self.p.SettingsWindow, _("Warning"),_("Security Risk: you should not share your %s directory!")  %place, self.frame.images["n"])
			raise UserWarning
		for share in self.shareddirs+self.bshareddirs:
			if homedir == share:
				popupWarning(self.p.SettingsWindow, _("Warning"),_("Security Risk: you should not share your %s directory!") %place, self.frame.images["n"])
				raise UserWarning
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
		dir1 = ChooseDir(self.Main.get_toplevel(), self.IncompleteDir.get_text())
		if dir1 is not None:
			for directory in dir1: # iterate over selected files
				self.incompletedir = directory
				self.IncompleteDir.set_text(recode(directory))

	def OnChooseDownloadDir(self, widget):
		dir1 = ChooseDir(self.Main.get_toplevel(), self.DownloadDir.get_text())
		if dir1 is not None:
			for directory in dir1: # iterate over selected files
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
	def __init__(self, parent):
		self.p = parent
		self.frame = parent.frame
		settings_glade.TransfersFrame.__init__(self, False)
		self.UploadsAllowed_List.clear()
		self.alloweduserslist = [_("No one"), _("Everyone"), _("Users in list"), _("Trusted Users")]

		for item in self.alloweduserslist:
			self.UploadsAllowed_List.append([item])

		self.filterlist = gtk.ListStore(gobject.TYPE_STRING, gobject.TYPE_BOOLEAN )
		self.downloadfilters = []
		
		cols = InitialiseColumns(self.FilterView,
			[_("Filter"), 250, "text"],
			[_("Escaped"), 40, "toggle"],
		)
		cols[0].set_sort_column_id(0)
		cols[1].set_sort_column_id(1)
		renderers = cols[1].get_cell_renderers()
		for render in renderers:
			render.connect('toggled', self.cell_toggle_callback, self.frame.UserList, 1)
		self.FilterView.set_model(self.filterlist)
		self.FilterView.get_selection().set_mode(gtk.SELECTION_MULTIPLE)
		
	def cell_toggle_callback(self, widget, index, treeview, pos):
		
		iter = self.filterlist.get_iter(index)
		#user = self.usersmodel.get_value(iter, 1)
		value = self.filterlist.get_value(iter, pos)
		self.filterlist.set(iter, pos, not value)
		
		self.OnVerifyFilter(self.VerifyFilters)
		
		
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
		if transfers["uploadallowed"] is not None:
			self.UploadsAllowed.set_active(transfers["uploadallowed"])
		
		self.OnQueueUseSlotsToggled(self.QueueUseSlots)
		self.OnLimitToggled(self.Limit)
		self.OnFriendsOnlyToggled(self.FriendsOnly)
		if transfers["enablefilters"] is not None:
			self.DownloadFilter.set_active(transfers["enablefilters"])
		
		self.filtersiters = {}
		self.filterlist.clear()
		if transfers["downloadfilters"] != []:
			for dfilter in transfers["downloadfilters"]:
				filter, escaped = dfilter
				self.filtersiters[filter] = self.filterlist.append([filter, escaped])
		self.OnEnableFiltersToggle(self.DownloadFilter)
		

			
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
		try:
			uploadallowed =  self.UploadsAllowed.get_active()
		except:
			uploadallowed = 0
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
				"uploadallowed": uploadallowed,
				"downloadfilters": self.GetFilterList(),
				"enablefilters": self.DownloadFilter.get_active(),
			},
		}

	def OnQueueUseSlotsToggled(self, widget):
		sensitive = widget.get_active()
		self.QueueSlots.set_sensitive(sensitive)
		self.QueueBandwidth.set_sensitive(not sensitive)
		self.label185.set_sensitive(not sensitive)
		self.label186.set_sensitive(not sensitive)
		
	def OnLimitToggled(self, widget):
		sensitive = widget.get_active()
		for w in self.LimitSpeed, self.LimitPerTransfer, self.LimitTotalTransfers:
			w.set_sensitive(sensitive)
	
	def OnFriendsOnlyToggled(self, widget):
		sensitive = not widget.get_active()
		self.PreferFriends.set_sensitive(sensitive)

	def OnEnableFiltersToggle(self, widget):
		sensitive = widget.get_active()
		self.VerifyFilters.set_sensitive(sensitive)
		self.VerifiedLabel.set_sensitive(sensitive)
		self.DefaultFilters.set_sensitive(sensitive)
		self.RemoveFilter.set_sensitive(sensitive)
		self.EditFilter.set_sensitive(sensitive)
		self.AddFilter.set_sensitive(sensitive)
		self.FilterView.set_sensitive(sensitive)
	
	def OnAddFilter(self, widget):
		response = input_box(self.frame, title=_('Nicotine+: Add a download filter'),		message=_('Enter a new download filter:'),
		default_text='', option=True, optionvalue=True, optionmessage="Escape this filter?", droplist=self.filtersiters.keys())
		if type(response) is list:
			filter = response[0]
			escaped = response[1]
			if filter in self.filtersiters.keys():
				self.filterlist.set(self.filtersiters[filter], 0, filter, 1, escaped)
			else:
				self.filtersiters[filter] = self.filterlist.append([filter, escaped])
			self.OnVerifyFilter(self.VerifyFilters)
	def GetFilterList(self):
		self.downloadfilters = []
		df = self.filtersiters.keys()
		df.sort()
		for filter in df :
			iter = self.filtersiters[filter]
			dfilter = self.filterlist.get_value(iter, 0)
			escaped = self.filterlist.get_value(iter, 1)
			self.downloadfilters.append([dfilter, int(escaped)])
		return self.downloadfilters
			
	
	def OnEditFilter(self, widget):
		dfilter = self.GetSelectedFilter()
		if dfilter:
			iter = self.filtersiters[dfilter]
			escapedvalue = self.filterlist.get_value(iter, 1)
			response = input_box(self.frame, title=_('Nicotine+: Edit a download filter'), message=_('Modify this download filter:'),
			default_text=dfilter, option=True, optionvalue=escapedvalue, optionmessage="Escape this filter?", droplist=self.filtersiters.keys())
			if type(response) is list:
				filter, escaped = response
				if filter in self.filtersiters.keys():
					self.filterlist.set(self.filtersiters[filter], 0, filter, 1, escaped)
				else:
					self.filtersiters[filter] = self.filterlist.append([filter, escaped])
					del self.filtersiters[dfilter]
					self.filterlist.remove(iter)
				self.OnVerifyFilter(self.VerifyFilters)

	
	def _SelectedFilter(self, model, path, iter, list):
		list.append(iter)
		
	def GetSelectedFilter(self):
		iters = []
		self.FilterView.get_selection().selected_foreach(self._SelectedFilter, iters)
		if iters == []:
			return None
		dfilter = self.filterlist.get_value(iters[0], 0)
		return dfilter
	
	def OnRemoveFilter(self, widget):
		dfilter = self.GetSelectedFilter()
		if dfilter:
			iter = self.filtersiters[dfilter]
			self.filterlist.remove(iter)
			del self.filtersiters[dfilter]
			self.OnVerifyFilter(self.VerifyFilters)
			
	
	def OnDefaultFilters(self, widget):
		self.filtersiters = {}
		self.filterlist.clear()
		default_filters = [["desktop.ini", 1], ["folder.jpg", 1], ["*.url", 1], ["thumbs.db", 1], ["albumart(_{........-....-....-....-............}_)?(_?(large|small))?\.jpg", 0]]
		for dfilter in default_filters:
			filter, escaped = dfilter
			self.filtersiters[filter] = self.filterlist.append([filter, escaped])
		self.OnVerifyFilter(self.VerifyFilters)
		
	def OnVerifyFilter(self, widget):

		outfilter = "(\\\\("
		df = self.filtersiters.keys()
		df.sort()
		proccessedfilters = []
		failed = {}
		for filter in df :
			iter = self.filtersiters[filter]
			dfilter = self.filterlist.get_value(iter, 0)
			escaped = self.filterlist.get_value(iter, 1)
			if escaped:
				dfilter = re.escape(dfilter)
				dfilter = dfilter.replace("\*", ".*")
			try:
				re.compile("("+dfilter+")")
				outfilter += dfilter
				proccessedfilters.append(dfilter)
			except Exception, e:
				failed[dfilter] = e
				
			
			
			if filter is not df[-1]:
				outfilter += "|"
		outfilter += ")$)"
		
		try:
			re.compile(outfilter)
			
		except Exception, e:
			failed[outfilter] = e
			
		if len(failed.keys()) >= 1:
			errors = ""
			for filter, error in failed.items():
				errors += "Filter: %(filter)s Error: %(error)s " % {'filter':filter, 'error':error}
			error = _("%(num)d Failed! %(error)s " %{'num':len(failed.keys()), 'error':errors} )
			self.VerifiedLabel.set_markup("<span color=\"red\" weight=\"bold\">%s</span>" % error)
		else:
			self.VerifiedLabel.set_markup("<b>Filters Successful</b>")

	
class GeoBlockFrame(settings_glade.GeoBlockFrame):
	def __init__(self, parent):
		self.p = parent
		self.frame = parent.frame
		settings_glade.GeoBlockFrame.__init__(self, False)
		try:
			import GeoIP
			
		except ImportError:
			try:
				import _GeoIP
			except ImportError:
				self.GeoBlock.set_sensitive(False)
				self.GeoPanic.set_sensitive(False)
				self.GeoBlockCC.set_sensitive(False)
				self.CountryCodesLabel.set_sensitive(False)
			
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
	def __init__(self, parent):
		self.p = parent
		self.frame = parent.frame
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
		dlg = ChooseImage(initialfile=self.Image.get_text())
		if dlg:
			for file in dlg:
				self.Image.set_text(file)
				break

class BanFrame(settings_glade.BanFrame):
	def __init__(self, parent):
		self.p = parent
		self.frame = parent.frame
		settings_glade.BanFrame.__init__(self, False)
		self.banned = []
		self.banlist = gtk.ListStore(gobject.TYPE_STRING)
		column = gtk.TreeViewColumn(_("Users"), gtk.CellRendererText(), text = 0)
		self.Banned.append_column(column)
		self.Banned.set_model(self.banlist)
		self.Banned.get_selection().set_mode(gtk.SELECTION_MULTIPLE)

		self.ignored = []
		self.ignorelist = gtk.ListStore(gobject.TYPE_STRING)
		column = gtk.TreeViewColumn(_("Users"), gtk.CellRendererText(), text = 0)
		self.Ignored.append_column(column)
		self.Ignored.set_model(self.ignorelist)
		self.Ignored.get_selection().set_mode(gtk.SELECTION_MULTIPLE)

		self.blocked = []
		self.blockedlist = gtk.ListStore(gobject.TYPE_STRING)
		column = gtk.TreeViewColumn(_("Addresses"), gtk.CellRendererText(), text = 0)
		self.Blocked.append_column(column)
		self.Blocked.set_model(self.blockedlist)
		self.Blocked.get_selection().set_mode(gtk.SELECTION_MULTIPLE)
		
	def SetSettings(self, config):
		server = config["server"]
		transfers = config["transfers"]
		self.banlist.clear()
		self.ignorelist.clear()
		self.blockedlist.clear()
		if server["banlist"] is not None:
			self.banned = server["banlist"][:]
			for banned in server["banlist"]:
				self.banlist.append([banned])
		if server["ignorelist"] is not None:
			self.ignored = server["ignorelist"][:]
			for ignored in server["ignorelist"]:
				self.ignorelist.append([ignored])
		if server["ipblocklist"] is not None:
			self.blocked = server["ipblocklist"][:]
			for blocked in server["ipblocklist"]:
				self.blockedlist.append([blocked])
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
				"ipblocklist": self.blocked[:],
			},
			"transfers": {
				"usecustomban": self.UseCustomBan.get_active(),
				"customban": self.CustomBan.get_text(),
			}
		}
	
	def OnAddBanned(self, widget):
		user = InputDialog(self.Main.get_toplevel(), _("Ban user..."), _("User:") )
		if user and user not in self.banned:
			self.banned.append(user)
			self.banlist.append([user])
	
	def _AppendItem(self, model, path, iter, l):
		l.append(iter)
	
	def OnRemoveBanned(self, widget):
		iters = []
		self.Banned.get_selection().selected_foreach(self._AppendItem, iters)
		for iter in iters:
			user = self.banlist.get_value(iter, 0)
			self.banned.remove(user)
			self.banlist.remove(iter)

	def OnClearBanned(self, widget):
		self.banned = []
		self.banlist.clear()

	def OnAddIgnored(self, widget):
		user = InputDialog(self.Main.get_toplevel(), _("Ignore user..."), _("User:") )
		if user and user not in self.ignored:
			self.ignored.append(user)
			self.ignorelist.append([user])
	
	def OnRemoveIgnored(self, widget):
		iters = []
		self.Ignored.get_selection().selected_foreach(self._AppendItem, iters)
		for iter in iters:
			user = self.ignorelist.get_value(iter, 0)
			self.ignored.remove(user)
			self.ignorelist.remove(iter)

	def OnClearIgnored(self, widget):
		self.ignored = []
		self.ignorelist.clear()

	def OnUseCustomBanToggled(self, widget):
		self.CustomBan.set_sensitive(widget.get_active())

	def OnAddBlocked(self, widget):
		ip = InputDialog(self.Main.get_toplevel(), _("Block IP Address..."), _("IP:") )
		if ip and ip not in self.blocked:
			self.blocked.append(ip)
			self.blockedlist.append([ip])
	
	def OnRemoveBlocked(self, widget):
		iters = []
		self.Blocked.get_selection().selected_foreach(self._AppendItem, iters)
		for iter in iters:
			ip = self.blockedlist.get_value(iter, 0)
			self.blocked.remove(ip)
			self.blockedlist.remove(iter)

	def OnClearBlocked(self, widget):
		self.blocked = []
		self.blockedlist.clear()
		
class SoundsFrame(settings_glade.SoundsFrame):
	def __init__(self, parent):
		self.p = parent
		self.frame = parent.frame
		settings_glade.SoundsFrame.__init__(self, False)
		for executable in ["xmms -e $", "audacious -e $", "amarok -a $"]:
			self.audioPlayerCombo.append_text( executable )
		for item in ["play -q", "ogg123 -q", "Gstreamer (gst-python)"]:
			self.SoundCommand.append_text(item)
		self.SoundButton.connect("clicked", self.OnChooseSoundDir)
		self.DefaultSoundCommand.connect("clicked", self.DefaultSound, self.SoundCommand)
			
	def OnSoundCheckToggled(self, widget):
		sensitive = widget.get_active()
		self.SoundCommand.set_sensitive(sensitive)
		self.SoundDirectory.set_sensitive(sensitive)
		self.SoundButton.set_sensitive(sensitive)
		self.DefaultSoundCommand.set_sensitive(sensitive)
		self.sndcmdLabel.set_sensitive(sensitive)
		self.snddirLabel.set_sensitive(sensitive)
		
	def DefaultSound(self, widget, combo):
		combo.child.set_text("play -q")
		
	def SetSettings(self, config):
		ui = config["ui"]
		
		if ui["soundcommand"] is not None:
			self.SoundCommand.child.set_text(ui["soundcommand"])
		if ui["soundenabled"] is not None:
			self.SoundCheck.set_active(ui["soundenabled"])
		if ui["soundtheme"] is not None:
			self.SoundDirectory.set_text(ui["soundtheme"])
		self.OnSoundCheckToggled(self.SoundCheck)
		
		if config["players"]["default"] is not None:
			self.audioPlayerCombo.child.set_text(config["players"]["default"])
			self.audioPlayerCombo.append_text( config["players"]["default"] )
	def GetSettings(self):

		soundcommand = self.SoundCommand.child.get_text()
		if soundcommand == "Gstreamer (gst-python)":
			if self.frame.gstreamer.player is None:
				popupWarning(self.p.SettingsWindow, _("Warning"), _("Gstreamer-python is not installed") , self.frame.images["n"] )
				raise UserWarning
		
		return {
			"ui": {
				"soundcommand": soundcommand,
				"soundtheme": self.SoundDirectory.get_text(),
				"soundenabled": self.SoundCheck.get_active(),
			},
			"players": {
				"default": self.audioPlayerCombo.child.get_text(),
			},
		}

	
	def OnChooseSoundDir(self, widget):
		dir = ChooseDir(self.Main.get_toplevel(), self.SoundDirectory.get_text())
		if dir is not None: 
			for directory in dir: # iterate over selected files
				self.SoundDirectory.set_text(recode(directory))
				
class IconsFrame(settings_glade.IconsFrame):
	def __init__(self, parent):
		self.p = parent
		self.frame = parent.frame
		settings_glade.IconsFrame.__init__(self, False)
		self.ThemeButton.connect("clicked", self.OnChooseThemeDir)
		self.DefaultTheme.connect("clicked", self.OnDefaultTheme)
		self.N.set_from_pixbuf(self.frame.images["n"])
		self.Away.set_from_pixbuf(self.frame.images["away"])
		self.Away2.set_from_pixbuf(self.frame.images["away2"])
		self.Online.set_from_pixbuf(self.frame.images["online"])
		self.Offline.set_from_pixbuf(self.frame.images["offline"])
		self.Hilite.set_from_pixbuf(self.frame.images["hilite"])
		self.Hilite2.set_from_pixbuf(self.frame.images["hilite2"])
		self.Connect.set_from_pixbuf(self.frame.images["connect"])
		self.Disconnect.set_from_pixbuf(self.frame.images["disconnect"])
		
	def SetSettings(self, config):
		ui = config["ui"]
		if ui["tabclosers"] is not None:
			self.TabClosers.set_active(ui["tabclosers"])
		if ui["trayicon"] is not None:
			self.TrayiconCheck.set_active(ui["trayicon"])
		if ui["icontheme"] is not None:
			self.IconTheme.set_text(ui["icontheme"])
			
	def OnDefaultTheme(self, widget):
		self.IconTheme.set_text("")
		
	def OnChooseThemeDir(self, widget):
		dir = ChooseDir(self.Main.get_toplevel(), self.IconTheme.get_text())
		if dir is not None:
			for directory in dir: # iterate over selected files
				self.IconTheme.set_text(recode(directory))
			
	def GetSettings(self):
		return {
			"ui": {
				"icontheme": self.IconTheme.get_text(),
				"tabclosers": self.TabClosers.get_active(),
				"trayicon": self.TrayiconCheck.get_active(),
		
			},
		}

class BloatFrame(settings_glade.BloatFrame):
	def __init__(self, parent):
		self.p = parent
		self.frame = parent.frame
		self.needcolors = 0
		settings_glade.BloatFrame.__init__(self, False)
		for item in ["<None>", ",", ".", "<space>"]:
			self.DecimalSep.append_text(item)
		
		for item in ["bold", "italic", "underline", "normal"]:
			self.UsernameStyle.append_text(item)
		self.UsernameStyle.child.set_editable(False)

		for item in ["", "de", "dk", "fi", "fr",  "hu", "it", "lt", "nl", "pl", "pt_BR", "sk", "sv" ]:
			self.TranslationCombo.append_text(item)
		#self.UsernameStyle.child.set_editable(False)
		
		
		self.PickRemote.connect("clicked", self.PickColour, self.Remote)
		self.PickLocal.connect("clicked", self.PickColour, self.Local)
		self.PickMe.connect("clicked", self.PickColour, self.Me)
		self.PickHighlight.connect("clicked", self.PickColour, self.Highlight)
		self.PickImmediate.connect("clicked", self.PickColour, self.Immediate)
		self.PickQueue.connect("clicked", self.PickColour, self.Queue)
		
		self.PickAway.connect("clicked", self.PickColour, self.AwayColor)
		self.PickOnline.connect("clicked", self.PickColour, self.OnlineColor)
		self.PickOffline.connect("clicked", self.PickColour, self.OfflineColor)
		
		self.DefaultAway.connect("clicked", self.DefaultColour, self.AwayColor)
		self.DefaultOnline.connect("clicked", self.DefaultColour, self.OnlineColor)
		self.DefaultOffline.connect("clicked", self.DefaultColour, self.OfflineColor)
		
		self.PickBackground.connect("clicked", self.PickColour, self.BackgroundColor)
		self.DefaultBackground.connect("clicked", self.DefaultColour, self.BackgroundColor)
		
		self.PickInput.connect("clicked", self.PickColour, self.InputColor)
		self.DefaultInput.connect("clicked", self.DefaultColour, self.InputColor)
		
		self.DefaultRemote.connect("clicked", self.DefaultColour, self.Remote)
		self.DefaultLocal.connect("clicked", self.DefaultColour, self.Local)
		self.DefaultMe.connect("clicked", self.DefaultColour, self.Me)
		self.DefaultHighlight.connect("clicked", self.DefaultColour, self.Highlight)
		self.DefaultImmediate.connect("clicked", self.DefaultColour, self.Immediate)
		self.DefaultQueue.connect("clicked", self.DefaultColour, self.Queue)
		self.DefaultQueue.connect("clicked", self.DefaultColour, self.Queue)
		
		
		# Tint
		self.PickTint.connect("clicked", self.PickColour, self.TintColor)
		self.DefaultTint.connect("clicked", self.DefaultColour, self.TintColor)
		
		# To set needcolors flag
		self.SelectChatFont.connect("font-set", self.FontsColorsChanged)
		self.Local.connect("changed", self.FontsColorsChanged)
		self.Remote.connect("changed", self.FontsColorsChanged)
		self.Me.connect("changed", self.FontsColorsChanged)
		self.Highlight.connect("changed", self.FontsColorsChanged)
		self.BackgroundColor.connect("changed", self.FontsColorsChanged)
		self.Immediate.connect("changed", self.FontsColorsChanged)
		self.Queue.connect("changed", self.FontsColorsChanged)
		self.AwayColor.connect("changed", self.FontsColorsChanged)
		self.OnlineColor.connect("changed", self.FontsColorsChanged)
		self.OfflineColor.connect("changed", self.FontsColorsChanged)
		self.UsernameStyle.child.connect("changed", self.FontsColorsChanged)
		self.InputColor.connect("changed", self.FontsColorsChanged)
		
	def FontsColorsChanged(self, widget):
		self.needcolors = 1
		

	def SetSettings(self, config):
		ui = config["ui"]
		private = config["privatechat"]
		transfers = config["transfers"]
		language = config["language"]

		if language["setlanguage"] is not None:
			self.TranslationCheck.set_active(int(language["setlanguage"]))
		if language["language"] is not None:
			self.TranslationComboEntry.set_text(language["language"])
			
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
		
		if ui["useraway"] is not None:
			self.AwayColor.set_text(ui["useraway"])
		if ui["useronline"] is not None:
			self.OnlineColor.set_text(ui["useronline"])
		if ui["useroffline"] is not None:
			self.OfflineColor.set_text(ui["useroffline"])
		if ui["usernamehotspots"] is not None:
			self.UsernameHotspots.set_active(ui["usernamehotspots"])
		if ui["textbg"] is not None:
			self.BackgroundColor.set_text(ui["textbg"])
		if ui["inputcolor"] is not None:
			self.InputColor.set_text(ui["inputcolor"])
		self.OnUsernameHotspotsToggled(self.UsernameHotspots)
		if ui["search"] is not None:
			self.Immediate.set_text(ui["search"])
		if ui["searchq"] is not None:
			self.Queue.set_text(ui["searchq"])
		if ui["decimalsep"] is not None:
			self.DecimalSep.child.set_text(ui["decimalsep"])
		if ui["exitdialog"] is not None:
			self.ExitDialog.set_active(ui["exitdialog"])
		if ui["spellcheck"] is not None:
			self.SpellCheck.set_active(ui["spellcheck"])
		if not self.frame.SEXY:
			self.SpellCheck.set_sensitive(False)
		if private["store"] is not None:
			self.ReopenPrivateChats.set_active(private["store"])


		if ui["usernamestyle"] is not None:
			self.UsernameStyle.child.set_text(ui["usernamestyle"])
		if transfers["enabletransferbuttons"] is not None:
			self.ShowTransferButtons.set_active(transfers["enabletransferbuttons"])
		if ui["enabletrans"] is not None:
			self.EnableTransparent.set_active(ui["enabletrans"])
		self.OnEnableTransparentToggled(self.EnableTransparent)
		self.OnTranslationCheckToggled(self.TranslationCheck)
		self.settingup = 1
		if ui["transtint"] is not None:
			self.TintColor.set_text(ui["transtint"])
		if ui["transalpha"] is not None:
			self.TintAlpha.set_value(ui["transalpha"])
		
		self.ColourScale("")
		self.settingup = 0
		self.needcolors = 0
		
	def GetSettings(self):
		
		try:
			import gettext
			message = ""
			language = self.TranslationComboEntry.get_text()
			if language != "":
				langTranslation = gettext.translation('nicotine', languages=[language])
				langTranslation.install()
		except IOError, e:
			message = _("Translation not found for '%s': %s") % (language, e)
			langTranslation = gettext
		except IndexError, e:
			message = _("Translation was corrupted for '%s': %s") % (language, e)
			langTranslation = gettext
		if message is not None and message != "":
			popupWarning(self.p.SettingsWindow, _("Warning: Missing translation"), _("Nicotine+ could not find your selected translation.\n%s") % message, self.frame.images["n"] )
			raise UserWarning
	
		return {
			"ui": {
				
				"chatfont": self.SelectChatFont.get_font_name(),
				"chatlocal": self.Local.get_text(),
				"chatremote": self.Remote.get_text(),
				"chatme": self.Me.get_text(),
				"chathilite": self.Highlight.get_text(),
				"textbg": self.BackgroundColor.get_text(),
				"inputcolor": self.InputColor.get_text(),
				"search": self.Immediate.get_text(),
				"searchq": self.Queue.get_text(),
				"decimalsep": self.DecimalSep.child.get_text(),
				"spellcheck": self.SpellCheck.get_active(),
				"exitdialog": self.ExitDialog.get_active(),
				"useraway": self.AwayColor.get_text(),
				"useronline": self.OnlineColor.get_text(),
				"useroffline": self.OfflineColor.get_text(),
				"usernamehotspots": self.UsernameHotspots.get_active(),
				"usernamestyle": self.UsernameStyle.child.get_text(),
				"enabletrans": self.EnableTransparent.get_active(),
				"transtint": self.TintColor.get_text(),
				"transalpha": self.TintAlpha.get_value(),
			},
			"transfers": {
				"enabletransferbuttons": self.ShowTransferButtons.get_active(),
			},
			"privatechat": {
				"store": self.ReopenPrivateChats.get_active(),
			},
			"language": {
				"setlanguage": self.TranslationCheck.get_active(),
				"language": self.TranslationComboEntry.get_text(),
			}
		}
		
	def OnTranslationCheckToggled(self, widget):
		sensitive = widget.get_active()
		self.TranslationCombo.set_sensitive(sensitive)
		
	def OnEnableTransparentToggled(self, widget):
		sensitive = widget.get_active()
		self.PickTint.set_sensitive(sensitive)
		
		self.TintAlpha.set_sensitive(sensitive)
		self.DefaultTint.set_sensitive(sensitive)
		self.TintColor.set_sensitive(sensitive)
		self.Blue.set_sensitive(sensitive)
		self.Red.set_sensitive(sensitive)
		self.Green.set_sensitive(sensitive)
		self.label346.set_sensitive(sensitive)
		self.label348.set_sensitive(sensitive)
		self.label349.set_sensitive(sensitive)
		self.label347.set_sensitive(sensitive)
		
		
	def OnUsernameHotspotsToggled(self, widget):
		sensitive = widget.get_active()
		self.AwayColor.set_sensitive(sensitive)
		self.OnlineColor.set_sensitive(sensitive)
		self.OfflineColor.set_sensitive(sensitive)
		
		self.DefaultAway.set_sensitive(sensitive)
		self.DefaultOnline.set_sensitive(sensitive)
		self.DefaultOffline.set_sensitive(sensitive)
		
		self.PickAway.set_sensitive(sensitive)
		self.PickOnline.set_sensitive(sensitive)
		self.PickOffline.set_sensitive(sensitive)

		
	def PickColour(self, widget, entry):
		dlg = gtk.ColorSelectionDialog(_("Pick a colour, any colour"))
		colour = entry.get_text()
		if entry is self.TintColor:
			dlg.colorsel.set_has_opacity_control(True)
			dlg.colorsel.set_current_alpha(int(self.TintAlpha.get_value()) * 256)
		if colour != None and colour !='':
			colour = gtk.gdk.color_parse(colour)
			dlg.colorsel.set_current_color(colour)
			
		if dlg.run() == gtk.RESPONSE_OK:
			colour = dlg.colorsel.get_current_color()
			#print colour.red, colour.red / 256, colour.green,  colour.green / 256, colour.blue, colour.blue / 256
			colour = "#%02X%02X%02X" % (colour.red / 256, colour.green / 256, colour.blue / 256)
			entry.set_text(colour)
			
		
		if entry is self.TintColor:
			alpha = dlg.colorsel.get_current_alpha()

			self.TintAlpha.set_value(alpha /256)
			self.ColourScale("")
		dlg.destroy()
		
	def ColourScale(self, widget):
		tint = self.TintColor.get_text()
		if tint != "":
			if tint[0] == "#" and len(tint) == 7:
				try:
					red   = int(tint[1:3], 16)
					green = int(tint[3:5], 16)
					blue  = int(tint[5:], 16)
	
					self.Red.set_value(red)
					self.Blue.set_value(blue)
					self.Green.set_value(green)
				except Exception, e:
					print e
	def ScaleColour(self, widget):
		if self.settingup:
			return
		red = int(self.Red.get_value() )
		green = int(self.Green.get_value())
		blue = int(self.Blue.get_value())

		colour = "#%02X%02X%02X" % (red, green, blue)

		self.TintColor.set_text(colour)
		
	def DefaultColour(self, widget, entry):
		entry.set_text("")
		

			
class LogFrame(settings_glade.LogFrame):
	def __init__(self, parent):
		self.p = parent
		self.frame = parent.frame
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
	def __init__(self, parent):
		self.p = parent
		self.frame = parent.frame
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
	def __init__(self, parent):
		self.p = parent
		self.frame = parent.frame
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
	def __init__(self, parent):
		self.p = parent
		self.frame = parent.frame
		settings_glade.EventsFrame.__init__(self, False) 
		
		for executable in ["rox $", "konqueror $", "nautilus --no-desktop $", "thunar $", "xterm -e mc $", "emelfm2 -1 $", "krusader --left $", "gentoo -1 $" ]:
			self.FileManagerCombo.append_text( executable ) 
		
	def SetSettings(self, config):
		if self.frame.np.transfers is not None and self.frame.np.transfers.pynotify is not  None:
			self.ShowNotification.set_sensitive(True)
		else:
			self.ShowNotification.set_sensitive(False)
		transfers = config["transfers"]
		if transfers["shownotification"] is not None: 
			self.ShowNotification.set_active(transfers["shownotification"])
		if transfers["afterfinish"] is not None:
			self.AfterDownload.set_text(transfers["afterfinish"])
		if transfers["afterfolder"] is not None:
			self.AfterFolder.set_text(transfers["afterfolder"])

		if config["ui"]["filemanager"] is not None:
			self.FileManagerCombo.child.set_text(config["ui"]["filemanager"])
			
	def GetSettings(self):
		return {
			"transfers": {
				"shownotification" : self.ShowNotification.get_active(),
				"afterfinish": self.AfterDownload.get_text(),
				"afterfolder": self.AfterFolder.get_text(),
				
			},
			"ui": {
				"filemanager": self.FileManagerCombo.child.get_text(),
			},
		
		}


class ImportFrame(settings_glade.ImportFrame):
	def __init__(self, parent):
		self.p = parent
		self.frame = parent.frame
		settings_glade.ImportFrame.__init__(self, False)
	
	def SetSettings(self, config):

		self.config = self.frame.np.config
		path = "C:\Program Files\SoulSeek"
		if os.path.exists(path):
			self.ImportPath.set_text(path)
			

	def GetSettings(self):
		return {}
		
	def OnImportDirectory(self, widget):
		dir1 = ChooseDir(self.Main.get_toplevel(), self.ImportPath.get_text())
		if dir1 is not None:
			for directory in dir1: # iterate over selected files
				self.ImportPath.set_text(recode(directory))
	
	def OnImportConfig(self, widget):
		Path = self.ImportPath.get_text()
		Queue = self.ImportQueue.get_active()
		Login = self.ImportLogin.get_active()
		Rooms = self.ImportRooms.get_active()
		BuddyList = self.ImportBuddyList.get_active()
		BanList = self.ImportBanList.get_active()
		IgnoreList = self.ImportIgnoreList.get_active()
		UserInfo = self.ImportUserInfo.get_active()
		UserImage = self.ImportUserImage.get_active()

		Import = ImportWinSlskConfig(self.config, Path, Queue, Login, Rooms, BuddyList, BanList, IgnoreList, UserInfo, UserImage)
		response = Import.Run()
		if response == 0:
			popupWarning(self.p.SettingsWindow, _("Nothing Imported"), _("Config files for the official Soulseek client not found in \"%s\"") % Path , self.frame.images["n"])
		elif response == 1:
			popupWarning(self.p.SettingsWindow, _("Imported Soulseek Config"), _("Config was imported. You may need to restart for changes to take effect. If you changed your user name, buddy list or queue then you should restart immediately."), self.frame.images["n"] )
			self.p.SetSettings(self.frame.np.config.sections)
		elif response == 2:
			popupWarning(self.p.SettingsWindow, _("Nothing Imported"), _("No options were selected") , self.frame.images["n"])


class UrlCatchFrame(settings_glade.UrlCatchFrame):
	def __init__(self, parent):
		self.frame = parent.frame
		self.p = parent
		settings_glade.UrlCatchFrame.__init__(self, False)
		self.protocolmodel = gtk.ListStore(gobject.TYPE_STRING, gobject.TYPE_STRING)
		self.protocols = {}
		cols = InitialiseColumns(self.ProtocolHandlers,
			[_("Protocol"), -1, "text"],
			[_("Handler"), -1, "text"],
		)
		self.ProtocolHandlers.set_model(self.protocolmodel)
		self.ProtocolHandlers.get_selection().connect("changed", self.OnSelect)
		self.handlermodel = gtk.ListStore(gobject.TYPE_STRING)
		for item in ["firefox \"%s\"", "firefox -a firefox --remote 'openURL(%s,new-tab)'", "mozilla \"%s\"", "opera \"%s\"", "links -g \"%s\"", "dillo \"%s\"", "konqueror \"%s\"", "\"c:\Program Files\Mozilla Firefox\Firefox.exe\" %s"]:
			self.handlermodel.append([item])
		self.Handler.set_model(self.handlermodel)
		
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
				if urls["protocols"][key] == "firefox \"%s\" &":
					command = "firefox %s"
				elif urls["protocols"][key][-1] == "&":
					command = urls["protocols"][key][:-1]
				else:
					command = urls["protocols"][key]
				
				iter = self.protocolmodel.append([key, command])
				self.protocols[key] = [iter, command]

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
			self.Handler.child.set_text(handler)

	def OnUpdate(self, widget):
		key = self.Protocol.get_text()
		value = self.Handler.child.get_text()
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

class CensorFrame(settings_glade.CensorFrame):
	def __init__(self, parent):
		self.p = parent
		self.frame = parent.frame
		settings_glade.CensorFrame.__init__(self, False)

		self.censorlist = gtk.ListStore(gobject.TYPE_STRING)
		cols = InitialiseColumns(self.CensorList,
			[_("Pattern"), -1, "edit", self.frame.CellDataFunc],
		)
		cols[0].set_sort_column_id(0)

		self.CensorList.set_model(self.censorlist)

		
		renderers = cols[0].get_cell_renderers()
		for render in renderers:
			render.connect('edited', self.cell_edited_callback, self.CensorList, 0)

		for letter in ["#", "$", "!", " ", "x", "*" ]:
			self.CensorReplaceCombo.append_text( letter )
			
	def cell_edited_callback(self, widget, index, value, treeview, pos):
		#print index, value, treeview, pos
		store = treeview.get_model()
		iter = store.get_iter(index)
		#print iter, index, value
		store.set(iter, pos, value)
		
	def SetSettings(self, config):
		self.censorlist.clear()
		words = config["words"]
		if words["censored"] is not None:
			for word in words["censored"]:
				self.censorlist.append([word])
		if words["censorwords"] is not None:
			self.CensorCheck.set_active(words["censorwords"])
		if words["censorfill"] is not None:
			self.CensorReplaceEntry.set_text(words["censorfill"])


	def GetSettings(self):
		censored = []
		try:
			iter = self.censorlist.get_iter_root()
			while iter is not None:
				word = self.censorlist.get_value(iter, 0)
				censored.append(word)
				iter = self.censorlist.iter_next(iter)
			
		except:
			pass
			
		return {
			
			"words": {
				"censorfill": self.CensorReplaceEntry.get_text(),
				"censored": censored,
				"censorwords": self.CensorCheck.get_active(),
			}
		}
	def OnAdd(self, widget):
		iter = self.censorlist.append([""])
		selection = self.CensorList.get_selection()
		selection.unselect_all()
		selection.select_iter(iter)
		col = self.CensorList.get_column(0)
		render = col.get_cell_renderers()[0]

		self.CensorList.set_cursor(self.censorlist.get_path(iter), focus_column=col, start_editing=True)

	def OnRemove(self, widget):
		selection = self.CensorList.get_selection()
		iter = selection.get_selected()[1]
		if iter is not None:
			self.censorlist.remove(iter)

	def OnClear(self, widget):
		self.censorlist.clear()
	
class AutoReplaceFrame(settings_glade.AutoReplaceFrame):
	def __init__(self, parent):
		self.p = parent
		self.frame = parent.frame
		settings_glade.AutoReplaceFrame.__init__(self, False)
	
		self.replacelist = gtk.ListStore(gobject.TYPE_STRING, gobject.TYPE_STRING)
		cols = InitialiseColumns(self.ReplacementList,
			[_("Pattern"), 150, "edit", self.frame.CellDataFunc],
			[_("Replacement"), -1, "edit", self.frame.CellDataFunc],
		)
		cols[0].set_sort_column_id(0)
		cols[1].set_sort_column_id(1)
		self.ReplacementList.set_model(self.replacelist)

		for column in cols:
			renderers = column.get_cell_renderers()
			for render in renderers:
				render.connect('edited', self.cell_edited_callback, self.ReplacementList, cols.index(column))
				
	def cell_edited_callback(self, widget, index, value, treeview, pos):
		
		store = treeview.get_model()
		iter = store.get_iter(index)
		store.set(iter, pos, value)
			
	def SetSettings(self, config):
		self.replacelist.clear()
		words = config["words"]
		if words["autoreplaced"] is not None:
			for word, replacement in words["autoreplaced"].items():
				self.replacelist.append([word, replacement])
		if words["replacewords"] is not None:
			self.ReplaceCheck.set_active(words["replacewords"])
		
	def GetSettings(self):
		autoreplaced = {}
		try:
			iter = self.replacelist.get_iter_root()
			while iter is not None:
				word = self.replacelist.get_value(iter, 0)
				replacement = self.replacelist.get_value(iter, 1)
				autoreplaced[word] = replacement
				iter = self.replacelist.iter_next(iter)
			
		except:
			autoreplaced.clear()
			
		return {
			
			"words": {
				"autoreplaced": autoreplaced,
				"replacewords": self.ReplaceCheck.get_active(),
			}
		}
		
	def OnAdd(self, widget):
		iter = self.replacelist.append(["", ""])
		selection = self.ReplacementList.get_selection()
		selection.unselect_all()
		selection.select_iter(iter)
		col = self.ReplacementList.get_column(0)
		render = col.get_cell_renderers()[0]

		self.ReplacementList.set_cursor(self.replacelist.get_path(iter), focus_column=col, start_editing=True)

	def OnRemove(self, widget):
		selection = self.ReplacementList.get_selection()
		iter = selection.get_selected()[1]
		if iter is not None:
			self.replacelist.remove(iter)

	def OnClear(self, widget):
		self.replacelist.clear()

	def OnDefaults(self, widget):
		self.replacelist.clear()
		defaults = {"teh ": "the ", "taht ": "that ", "tihng": "thing", "youre": "you're", "jsut": "just", "thier": "their", "tihs": "this"}
		for word, replacement in defaults.items():
			self.replacelist.append([word, replacement])
    


class ChatFrame(settings_glade.ChatFrame):
	def __init__(self):
		settings_glade.ChatFrame.__init__(self, False)
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
		self.SettingsWindow.set_geometry_hints(None, min_width=600, min_height=400)
		self.SettingsWindow.set_default_size(700, 550)
		self.SettingsWindow.connect("delete-event", self.OnDelete)
		self.frame = frame
		self.empty_label = gtk.Label("")
		self.empty_label.show()
		self.viewport1.add(self.empty_label)
		self.tree = {}
		self.pages = p = {}
		model = gtk.TreeStore(str, str)

		self.tree["Server"] = model.append(None, [_("Server"), "Server"])
		self.tree["Shares"] = model.append(None, [_("Shares"), "Shares"])
		
		self.tree["Transfers"] = row = model.append(None, [_("Transfers"), "Transfers"])
		
		self.tree["Events"] = model.append(row, [_("Events"), "Events"])
		self.tree["Geo Block"] = model.append(row, [_("Geo Block"), "Geo Block"])
		
					
		self.tree["Interface"] = row =  model.append(None, [_("Interface"), "Interface"])
		self.tree["Icons"] = model.append(row, [_("Icons"), "Icons"])
		
		
		self.tree["Chat"] = row = model.append(None, [_("Chat"), "Chat"])
		self.tree["Away mode"] = model.append(row, [_("Away mode"), "Away mode"])
		self.tree["Logging"] = model.append(row, [_("Logging"), "Logging"])
		self.tree["Censor List"] = model.append(row, [_("Censor List"), "Censor List"])
		self.tree["Auto-Replace"] = model.append(row, [_("Auto-Replace"), "Auto-Replace"])
		self.tree["URL Catching"] = model.append(row, [_("URL Catching"), "URL Catching"])
		
		self.tree["Misc"] = row = model.append(None, [_("Misc"), "Misc"])
		self.tree["Ban / ignore"] = model.append(row, [_("Ban / ignore"), "Ban / ignore"])
		self.tree["Sounds"] = model.append(row, [_("Sounds"), "Sounds"])
		self.tree["Searches"] = model.append(row, [_("Searches"), "Searches"])
		self.tree["User info"] = model.append(row, [_("User info"), "User info"])
		self.tree["Import Config"] = model.append(row, [_("Import Config"), "Import Config"])
		
		p["Server"] = ServerFrame(self, frame.np.getencodings())
		p["Shares"] = SharesFrame(self)
		p["Transfers"] = TransfersFrame(self)
		p["Geo Block"] = GeoBlockFrame(self)
		p["User info"] = UserinfoFrame(self)
		p["Ban / ignore"] = BanFrame(self)
		p["Interface"] = BloatFrame(self)
		p["Sounds"] = SoundsFrame(self)
		p["Icons"] = IconsFrame(self)
		p["URL Catching"] = UrlCatchFrame(self)
		p["Logging"] = LogFrame(self)
		p["Searches"] = SearchFrame(self)
		p["Away mode"] = AwayFrame(self)
		p["Censor List"] = CensorFrame(self)
		p["Auto-Replace"] = AutoReplaceFrame(self)
		p["Chat"] = ChatFrame()
		p["Events"] = EventsFrame(self)
		p["Import Config"] = ImportFrame(self)
		
		p["Misc"] = MiscFrame()
		
		column = gtk.TreeViewColumn(_("Categories"), gtk.CellRendererText(), text = 0)

		self.SettingsTreeview.set_model(model)
		self.SettingsTreeview.append_column(column)

		self.SettingsTreeview.expand_row((0,), True)
		self.SettingsTreeview.expand_row((1,), True)
		self.SettingsTreeview.expand_row((2,), True)
		self.SettingsTreeview.expand_row((3,), True)
		self.SettingsTreeview.expand_row((4,), True)

		self.SettingsTreeview.get_selection().connect("changed", self.switch_page)
	
	def switch_page(self, widget):
		child = self.viewport1.get_child()
		if child:
			self.viewport1.remove(child)
		model, iter = widget.get_selected()
		if iter is None:
			self.viewport1.add(self.empty_label)
			return
		page = model.get_value(iter, 1)
		if self.pages.has_key(page):
			self.viewport1.add(self.pages[page].Main)
		else:
			self.viewport1.add(self.empty_label)
			
	def SwitchToPage(self, page):

		child = self.viewport1.get_child()
		if child:
			self.viewport1.remove(child)
	
		if self.tree[page] is None:
			self.viewport1.add(self.empty_label)
			return
		model = self.SettingsTreeview.get_model()
		sel = self.SettingsTreeview.get_selection()
		sel.unselect_all()
		path = model.get_path(self.tree[page])
		if path is not None:
			sel.select_path(path)

			
	def OnApply(self, widget):
		self.SettingsWindow.emit("settings-closed", "apply")

	def OnOk(self, widget):
		self.SettingsWindow.emit("settings-closed", "ok")

	def OnCancel(self, widget):
		self.SettingsWindow.emit("settings-closed", "cancel")
		
	def OnDelete(self, widget, event):
		self.OnCancel(widget)
		widget.emit_stop_by_name("delete-event")
		return True

	def SetSettings(self, config):
		for page in self.pages.values():
			page.SetSettings(config)

	def GetSettings(self):
		try:
			config = {
				"server": {},
				"transfers": {},
				"userinfo": {},
				"logging": {},
				"searches": {},
				"privatechat": {},
				"ui": {},
				"urls": {},
				"players": {},
				"words": {},
				"language": {},
				
			}
			
			for page in self.pages.values():
				sub = page.GetSettings()
				for (key,data) in sub.items():
					config[key].update(data)
			return self.pages["Shares"].GetNeedRescan(), self.pages["Interface"].needcolors, config
		except UserWarning, warning:
			return None
