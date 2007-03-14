## src/systraywin32.py
##
## Contributors for this file:
## - daelstorm <daelstorm@gmail.com> (removed lots of stuff)
##	- Yann Le Boulanger <asterix@lagaule.org>
##	- Nikos Kouremenos <kourem@gmail.com>
##	- Dimitur Kirov <dkirov@gmail.com>
##
## code initially based on 
## http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/334779
## with some ideas/help from pysystray.sf.net
##
## Copyright (C) 2003-2004 Yann Le Boulanger <asterix@lagaule.org>
##                         Vincent Hanquez <tab@snarc.org>
## Copyright (C) 2005 Yann Le Boulanger <asterix@lagaule.org>
##                    Vincent Hanquez <tab@snarc.org>
##                    Nikos Kouremenos <nkour@jabber.org>
##                    Dimitur Kirov <dkirov@gmail.com>
##                    Travis Shirk <travis@pobox.com>
##                    Norman Rasmussen <norman@rasmussen.co.za>
##
## This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published
## by the Free Software Foundation; version 2 only.
##
## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.
##


import win32gui
import pywintypes
import win32con # winapi constants

import gtk
import os

WM_TASKBARCREATED = win32gui.RegisterWindowMessage('TaskbarCreated')
WM_TRAYMESSAGE = win32con.WM_USER + 20

class SystrayWINAPI:
	def __init__(self, gtk_window):
		self._window = gtk_window
		self._hwnd = gtk_window.window.handle
		self._message_map = {}

		self.notify_icon = None            

		# Sublass the window and inject a WNDPROC to process messages.
		self._oldwndproc = win32gui.SetWindowLong(self._hwnd,
			win32con.GWL_WNDPROC, self._wndproc)


	def add_notify_icon(self, menu, hicon=None, tooltip=None):
		""" Creates a notify icon for the gtk window. """
		if not self.notify_icon:
			if not hicon:
				hicon = win32gui.LoadIcon(0, win32con.IDI_APPLICATION)
			self.notify_icon = NotifyIcon(self._hwnd, hicon, tooltip)

			# Makes redraw if the taskbar is restarted.   
			self.message_map({WM_TASKBARCREATED: self.notify_icon._redraw})


	def message_map(self, msg_map={}):
		""" Maps message processing to callback functions ala win32gui. """
		if msg_map:
			if self._message_map:
				duplicatekeys = [key for key in msg_map.keys()
								if self._message_map.has_key(key)]
				
				for key in duplicatekeys:
					new_value = msg_map[key]
					
					if isinstance(new_value, list):
						raise TypeError('Dict cannot have list values')
					
					value = self._message_map[key]
					
					if new_value != value:
						new_value = [new_value]
						
						if isinstance(value, list):
							value += new_value
						else:
							value = [value] + new_value
						
						msg_map[key] = value
			self._message_map.update(msg_map)

	def remove_notify_icon(self):
		""" Removes the notify icon. """
		if self.notify_icon:
			self.notify_icon.remove()
			self.notify_icon = None

	def remove(self, *args):
		""" Unloads the extensions. """
		self._message_map = {}
		self.remove_notify_icon()
		self = None

	def show_balloon_tooltip(self, title, text, timeout=10, icon=win32gui.NIIF_NONE):
		""" Shows a baloon tooltip. """
		if not self.notify_icon:
			self.add_notifyicon()
		self.notify_icon.show_balloon(title, text, timeout, icon)

	def _wndproc(self, hwnd, msg, wparam, lparam):
		""" A WINDPROC to process window messages. """
		if self._message_map.has_key(msg):
			callback = self._message_map[msg]
			if isinstance(callback, list):
				for cb in callback:
					cb(hwnd, msg, wparam, lparam)
			else:
				callback(hwnd, msg, wparam, lparam)

		return win32gui.CallWindowProc(self._oldwndproc, hwnd, msg, wparam, lparam)
									

class NotifyIcon:

	def __init__(self, hwnd, hicon, tooltip=None):
		self._hwnd = hwnd
		self._id = 0
		self._flags = win32gui.NIF_MESSAGE | win32gui.NIF_ICON
		self._callbackmessage = WM_TRAYMESSAGE
		self._hicon = hicon

		try:
			win32gui.Shell_NotifyIcon(win32gui.NIM_ADD, self._get_nid())
		except pywintypes.error:
			pass
		if tooltip: self.set_tooltip(tooltip)


	def _get_nid(self):
		""" Function to initialise & retrieve the NOTIFYICONDATA Structure. """
		nid = [self._hwnd, self._id, self._flags, self._callbackmessage, self._hicon]

		if not hasattr(self, '_tip'): self._tip = ''
		nid.append(self._tip)

		if not hasattr(self, '_info'): self._info = ''
		nid.append(self._info)
			
		if not hasattr(self, '_timeout'): self._timeout = 0
		nid.append(self._timeout)

		if not hasattr(self, '_infotitle'): self._infotitle = ''
		nid.append(self._infotitle)
			
		if not hasattr(self, '_infoflags'):self._infoflags = win32gui.NIIF_NONE
		nid.append(self._infoflags)

		return tuple(nid)
	
	def remove(self):
		""" Removes the tray icon. """
		try:
			win32gui.Shell_NotifyIcon(win32gui.NIM_DELETE, self._get_nid())
		except pywintypes.error:
			pass


	def set_tooltip(self, tooltip):
		""" Sets the tray icon tooltip. """
		self._flags = self._flags | win32gui.NIF_TIP
		self._tip = tooltip
		try:
			win32gui.Shell_NotifyIcon(win32gui.NIM_MODIFY, self._get_nid())
		except pywintypes.error:
			pass
		
		
	def show_balloon(self, title, text, timeout=10, icon=win32gui.NIIF_NONE):
		""" Shows a balloon tooltip from the tray icon. """
		self._flags = self._flags | win32gui.NIF_INFO
		self._infotitle = title
		self._info = text
		self._timeout = timeout * 1000
		self._infoflags = icon
		try:
			win32gui.Shell_NotifyIcon(win32gui.NIM_MODIFY, self._get_nid())
		except pywintypes.error:
			pass

	def _redraw(self, *args):
		""" Redraws the tray icon. """
		self.remove()
		try:
			win32gui.Shell_NotifyIcon(win32gui.NIM_ADD, self._get_nid())
		except pywintypes.error:
			pass


class TrayIcon:
	def __init__(self, name, frame):
		# Note: gtk window must be realized before installing extensions.
		self.tray_ico_imgs  = {}
		self.jids = []
		self.frame = frame
		self.name = name
		self.status = 'offline'
		self.systray_context_menu = gtk.Menu()
		self.menu = self.frame.TrayApp.tray_popup_menu
		self.added_hide_menuitem = False

		w = gtk.Window() # just a window to pass
		w.realize() # realize it so gtk window exists
		self.systray_winapi = SystrayWINAPI(w)

		# Set up the callback messages
		self.systray_winapi.message_map({
			WM_TRAYMESSAGE: self.on_clicked
			}) 
		#self.show_icon()
        def show_all(self):
		pass
		#self.systray_winapi._window.show_all()
	def get_size(self):
		return self.systray_winapi._window.get_size()

	def show_icon(self):
		self.systray_winapi.add_notify_icon(self.systray_context_menu, tooltip = 'Nicotine+')
		#self.systray_winapi.notify_icon.menu = self.systray_context_menu
		# do not remove set_img does both above. 
		# maybe I can only change img without readding
		# the notify icon? HOW??
		self.set_img(self.frame.TrayApp.tray_status["last"] )

	def hide_icon(self):
		self.systray_winapi.remove()

	def on_clicked(self, hwnd, message, wparam, lparam):
		if lparam == win32con.WM_RBUTTONUP: # Right click
			items = self.frame.TrayApp.tray_popup_menu.get_children()
			if self.frame.TrayApp.tray_status["status"] == "disconnect":
				items[3].set_sensitive(False)
				items[4].set_sensitive(False)
				items[5].set_sensitive(False)
				items[6].set_sensitive(False)
			else:
				
				items[3].set_sensitive(True)
				items[4].set_sensitive(True)
				items[5].set_sensitive(True)
				items[6].set_sensitive(True)
			self.frame.TrayApp.tray_popup_menu.popup(None, None, None, 0, 0)
		elif lparam == win32con.WM_MBUTTONUP: # Middle click
			pass
		elif lparam == win32con.WM_LBUTTONUP: # Left click
			self.frame.TrayApp.HideUnhideWindow(None)

	def add(self, icon):
		pass
		
	def set_img(self, icon):
		import tempfile
		hinst = win32gui.GetModuleHandle(None)
		img_flags = win32con.LR_LOADFROMFILE | win32con.LR_DEFAULTSIZE

		icon_data = self.frame.icons[icon]

		image = 0
		tempicon  = tempfile.mktemp()
		tempfile = open(tempicon,"wb")
		tempfile.write(icon_data)
		tempfile.close()
		try:
			image  =   win32gui.LoadImage(hinst, tempfile.name, win32con.IMAGE_ICON, 0, 0, img_flags)
		except Exception, e:
			print Exception, e
		os.remove(tempfile.name)
		if image:
			hicon = image
		else:
			hicon = 0
		self.systray_winapi.remove_notify_icon()
		if hicon:
			self.systray_winapi.add_notify_icon(self.systray_context_menu, hicon,
			'Nicotine+')
			self.systray_winapi.notify_icon.menu = self.systray_context_menu
			
		return

