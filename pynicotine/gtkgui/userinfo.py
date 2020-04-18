# -*- coding: utf-8 -*-
#
# COPYRIGHT (C) 2016-2017 Michael Labouebe <gfarmerfr@free.fr>
# COPYRIGHT (C) 2008-2010 Quinox <quinox@users.sf.net>
# COPYRIGHT (C) 2006-2009 Daelstorm <daelstorm@gmail.com>
# COPYRIGHT (C) 2003-2004 Hyriand <hyriand@thegraveyard.org>
#
# GNU GENERAL PUBLIC LICENSE
#    Version 3, 29 June 2007
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

import os
import tempfile
import time
from gettext import gettext as _

import gi
from gi.repository import Gdk
from gi.repository import GdkPixbuf
from gi.repository import GObject as gobject
from gi.repository import Gtk as gtk

from pynicotine import slskmessages
from pynicotine.gtkgui.utils import AppendLine
from pynicotine.gtkgui.utils import EncodingsMenu
from pynicotine.gtkgui.utils import Humanize
from pynicotine.gtkgui.utils import IconNotebook
from pynicotine.gtkgui.utils import InitialiseColumns
from pynicotine.gtkgui.utils import PopupMenu
from pynicotine.gtkgui.utils import SaveEncoding
from pynicotine.logfacility import log
from pynicotine.utils import CleanFile

gi.require_version('Gtk', '3.0')


# User Info and User Browse Notebooks
class UserTabs(IconNotebook):

    def __init__(self, frame, subwindow, notebookraw):

        self.frame = frame

        ui = frame.np.config.sections["ui"]

        IconNotebook.__init__(
            self,
            self.frame.images,
            angle=ui["labelinfo"],
            tabclosers=ui["tabclosers"],
            show_image=ui["tab_icons"],
            reorderable=ui["tab_reorderable"],
            show_status_image=ui["tab_status_icons"],
            notebookraw=notebookraw
        )

        self.popup_enable()

        self.subwindow = subwindow

        self.users = {}
        self.mytab = None

    def SetTabLabel(self, mytab):
        self.mytab = mytab

    def GetUserStats(self, msg):

        if msg.user in self.users:
            tab = self.users[msg.user]
            tab.speed.set_text(_("Speed: %s") % Humanize(msg.avgspeed))
            tab.filesshared.set_text(_("Files: %s") % Humanize(msg.files))
            tab.dirsshared.set_text(_("Directories: %s") % Humanize(msg.dirs))

    def GetUserStatus(self, msg):

        if msg.user in self.users:

            tab = self.users[msg.user]
            tab.status = msg.status
            status = [_("Offline"), _("Away"), _("Online")][msg.status]

            if not self.frame.np.config.sections["ui"]["tab_status_icons"]:
                self.set_text(tab.Main, "%s (%s)" % (msg.user[:15], status))
            else:
                self.set_text(tab.Main, msg.user)

            self.set_status_image(tab.Main, msg.status)

    def InitWindow(self, user, conn):

        if user in self.users:
            self.users[user].conn = conn
            self.frame.np.queue.put(slskmessages.GetUserStats(user))
        else:
            w = self.subwindow(self, user, conn)
            self.append_page(w.Main, user[:15], w.OnClose)
            self.users[user] = w
            self.frame.np.queue.put(slskmessages.AddUser(user))

    def ShowLocalInfo(self, user, descr, has_pic, pic, totalupl, queuesize, slotsavail, uploadallowed):

        self.InitWindow(user, None)
        self.users[user].ShowUserInfo(descr, has_pic, pic, totalupl, queuesize, slotsavail, uploadallowed)
        self.request_changed(self.users[user].Main)

        if self.mytab is not None:
            self.frame.RequestIcon(self.mytab)

    def ShowInfo(self, user, msg):

        self.InitWindow(user, msg.conn)
        self.users[user].ShowInfo(msg)
        self.request_changed(self.users[user].Main)

        if self.mytab is not None:
            self.frame.RequestIcon(self.mytab)

        self.frame.ShowTab(None, ['userinfo', self.frame.userinfovbox])

    def ShowInterests(self, msg):

        if msg.user in self.users:
            self.users[msg.user].ShowInterests(msg.likes, msg.hates)

    def UpdateGauge(self, msg):

        for i in list(self.users.values()):
            if i.conn == msg.conn.conn:
                i.UpdateGauge(msg)

    def UpdateColours(self):

        for i in list(self.users.values()):
            i.ChangeColours()

    def TabPopup(self, user):

        popup = PopupMenu(self.frame)
        popup.setup(
            ("#" + _("Send _message"), popup.OnSendMessage),
            ("#" + _("Show IP a_ddress"), popup.OnShowIPaddress),
            ("#" + _("Get user i_nfo"), popup.OnGetUserInfo),
            ("#" + _("Brow_se files"), popup.OnBrowseUser),
            ("#" + _("Gi_ve privileges"), popup.OnGivePrivileges),
            ("#" + _("Client Version"), popup.OnVersion),
            ("", None),
            ("$" + _("Add user to list"), popup.OnAddToList),
            ("$" + _("Ban this user"), popup.OnBanUser),
            ("$" + _("Ignore this user"), popup.OnIgnoreUser),
            ("", None),
            ("#" + _("Detach this tab"), self.users[user].Detach),
            ("#" + _("Close this tab"), self.users[user].OnClose)
        )
        popup.set_user(user)

        items = popup.get_children()

        items[7].set_active(user in [i[0] for i in self.frame.np.config.sections["server"]["userlist"]])
        items[8].set_active(user in self.frame.np.config.sections["server"]["banlist"])
        items[9].set_active(user in self.frame.np.config.sections["server"]["ignorelist"])

        return popup

    def on_tab_click(self, widget, event, child):

        if event.type == Gdk.EventType.BUTTON_PRESS:

            n = self.page_num(child)
            page = self.get_nth_page(n)
            username = [user for user, tab in list(self.users.items()) if tab.Main is page][0]

            if event.button == 2:
                self.users[username].OnClose(widget)
                return True

            if event.button == 3:
                menu = self.TabPopup(username)
                menu.popup(None, None, None, None, event.button, event.time)
                return True

            return False

        return False

    def ConnClose(self):

        self.connected = 0
        for user in self.users:
            self.users[user].ConnClose()
            tab = self.users[user]
            tab.status = 0
            status = _("Offline")
            self.set_text(tab.Main, "%s (%s)" % (user[:15], status))


class UserInfo:

    def __init__(self, userinfos, user, conn):

        # Build the window
        builder = gtk.Builder()

        builder.set_translation_domain('nicotine')
        builder.add_from_file(os.path.join(os.path.dirname(os.path.realpath(__file__)), "ui", "userinfo.ui"))

        self.UserInfoTab = builder.get_object("UserInfoTab")

        for i in builder.get_objects():
            try:
                self.__dict__[gtk.Buildable.get_name(i)] = i
            except TypeError:
                pass

        self.UserInfoTab.remove(self.Main)
        self.UserInfoTab.destroy()

        builder.connect_signals(self)

        self.userinfos = userinfos
        self.frame = userinfos.frame

        self.frame.np.queue.put(slskmessages.UserInterests(user))
        self.user = user
        self.conn = conn
        self._descr = ""
        self.image_pixbuf = None
        self.zoom_factor = 5
        self.actual_zoom = 0
        self.status = 0

        self.hatesStore = gtk.ListStore(gobject.TYPE_STRING)
        self.Hates.set_model(self.hatesStore)
        cols = InitialiseColumns(self.Hates, [_("Hates"), 0, "text", self.CellDataFunc])
        cols[0].set_sort_column_id(0)
        self.hatesStore.set_sort_column_id(0, gtk.SortType.ASCENDING)

        self.likesStore = gtk.ListStore(gobject.TYPE_STRING)
        self.Likes.set_model(self.likesStore)
        cols = InitialiseColumns(self.Likes, [_("Likes"), 0, "text", self.CellDataFunc])
        cols[0].set_sort_column_id(0)
        self.likesStore.set_sort_column_id(0, gtk.SortType.ASCENDING)

        # Encoding Combobox
        self.Elist = {}
        self.encoding, m = EncodingsMenu(self.frame.np, "userencoding", user)
        self.EncodingStore = gtk.ListStore(gobject.TYPE_STRING, gobject.TYPE_STRING)
        self.Encoding.set_model(self.EncodingStore)

        cell = gtk.CellRendererText()
        self.Encoding.pack_start(cell, True)
        self.Encoding.add_attribute(cell, 'text', 0)

        cell2 = gtk.CellRendererText()
        self.Encoding.pack_start(cell2, False)
        self.Encoding.add_attribute(cell2, 'text', 1)

        for item in m:
            self.Elist[item[1]] = self.EncodingStore.append([item[1], item[0]])
            if self.encoding == item[1]:
                self.Encoding.set_active_iter(self.Elist[self.encoding])

        self.tag_local = self.makecolour("chatremote")  # noqa: F821
        self.ChangeColours()

        self.InterestsExpander.connect("activate", self.ExpanderStatus)
        self.InformationExpander.connect("activate", self.ExpanderStatus)
        self.DescriptionExpander.connect("activate", self.ExpanderStatus)

        self.likes_popup_menu = popup = PopupMenu(self)
        popup.setup(
            ("$" + _("I _like this"), self.frame.OnLikeRecommendation),
            ("$" + _("I _don't like this"), self.frame.OnDislikeRecommendation),
            ("", None),
            ("#" + _("_Search for this item"), self.frame.OnRecommendSearch)
        )
        self.Likes.connect("button_press_event", self.OnPopupLikesMenu)

        self.hates_popup_menu = popup = PopupMenu(self)
        popup.setup(
            ("$" + _("I _like this"), self.frame.OnLikeRecommendation),
            ("$" + _("I _don't like this"), self.frame.OnDislikeRecommendation),
            ("", None),
            ("#" + _("_Search for this item"), self.frame.OnRecommendSearch)
        )
        self.Hates.connect("button_press_event", self.OnPopupHatesMenu)

        self.image_menu = popup = PopupMenu(self)
        popup.setup(
            ("#" + _("Zoom 1:1"), self.MakeZoomNormal),
            ("#" + _("Zoom In"), self.MakeZoomIn),
            ("#" + _("Zoom Out"), self.MakeZoomOut),
            ("", None),
            ("#" + _("Save Image"), self.OnSavePicture)
        )

    def OnPopupLikesMenu(self, widget, event):

        if event.button != 3:
            return

        d = self.Likes.get_path_at_pos(int(event.x), int(event.y))
        if not d:
            return

        path, column, x, y = d

        iter = self.likesStore.get_iter(path)
        thing = self.likesStore.get_value(iter, 0)
        items = self.likes_popup_menu.get_children()

        self.likes_popup_menu.set_user(thing)

        items[0].set_active(thing in self.frame.np.config.sections["interests"]["likes"])
        items[1].set_active(thing in self.frame.np.config.sections["interests"]["dislikes"])

        self.likes_popup_menu.popup(None, None, None, None, event.button, event.time)

    def OnPopupHatesMenu(self, widget, event):

        if event.button != 3:
            return

        d = self.Hates.get_path_at_pos(int(event.x), int(event.y))
        if not d:
            return

        path, column, x, y = d

        iter = self.hatesStore.get_iter(path)
        thing = self.hatesStore.get_value(iter, 0)
        items = self.hates_popup_menu.get_children()

        self.hates_popup_menu.set_user(thing)

        items[0].set_active(thing in self.frame.np.config.sections["interests"]["likes"])
        items[1].set_active(thing in self.frame.np.config.sections["interests"]["dislikes"])

        self.hates_popup_menu.popup(None, None, None, None, event.button, event.time)

    def ConnClose(self):
        pass

    def Attach(self, widget=None):
        self.userinfos.attach_tab(self.Main)

    def Detach(self, widget=None):
        self.userinfos.detach_tab(
            self.Main,
            _("Nicotine+ Userinfo: %(user)s (%(status)s)") % {
                'user': self.user,
                'status': [_("Offline"), _("Away"), _("Online")][self.status]
            }
        )

    def CellDataFunc(self, column, cellrenderer, model, iter, dummy="dummy"):

        colour = self.frame.np.config.sections["ui"]["search"]
        if colour == "":
            colour = None

        cellrenderer.set_property("foreground", colour)

    def ExpanderStatus(self, widget):

        if widget.get_property("expanded"):
            self.InfoVbox.set_child_packing(widget, False, True, 0, 0)
        else:
            self.InfoVbox.set_child_packing(widget, True, True, 0, 0)

    def makecolour(self, colour):

        buffer = self.descr.get_buffer()
        colour = self.frame.np.config.sections["ui"][colour]
        font = self.frame.np.config.sections["ui"]["chatfont"]

        if colour:
            return buffer.create_tag(foreground=colour, font=font)
        else:
            return buffer.create_tag(font=font)

    def changecolour(self, tag, colour):

        if colour in self.frame.np.config.sections["ui"]:
            color = self.frame.np.config.sections["ui"][colour]
        else:
            color = None

        font = self.frame.np.config.sections["ui"]["chatfont"]

        if color:
            if color == "":
                color = None

            tag.set_property("foreground", color)
            tag.set_property("font", font)
        else:
            tag.set_property("font", font)

    def ChangeColours(self):

        self.changecolour(self.tag_local, "chatremote")

        self.frame.SetTextBG(self.descr)
        self.frame.SetTextBG(self.Likes)
        self.frame.SetTextBG(self.Hates)

        self.frame.ChangeListFont(self.Likes, self.frame.np.config.sections["ui"]["listfont"])
        self.frame.ChangeListFont(self.Hates, self.frame.np.config.sections["ui"]["listfont"])

    def ShowInterests(self, likes, hates):

        self.likesStore.clear()
        self.hatesStore.clear()

        for like in likes:
            self.likesStore.append([like])

        for hate in hates:
            self.hatesStore.append([hate])

    def ShowUserInfo(self, descr, has_pic, pic, totalupl, queuesize, slotsavail, uploadallowed):

        self.conn = None
        self._descr = descr
        self.image_pixbuf = None
        self.descr.get_buffer().set_text("")

        AppendLine(self.descr, self.frame.np.decode(descr, self.encoding), self.tag_local, showstamp=False, scroll=False)

        self.uploads.set_text(_("Total uploads allowed: %i") % totalupl)
        self.queuesize.set_text(_("Queue size: %i") % queuesize)

        if slotsavail:
            slots = _("Yes")
        else:
            slots = _("No")

        self.slotsavail.set_text(_("Slots free: %s") % slots)

        if uploadallowed == 0:
            allowed = _("No one")
        elif uploadallowed == 1:
            allowed = _("Everyone")
        elif uploadallowed == 2:
            allowed = _("Users in list")
        elif uploadallowed == 3:
            allowed = _("Trusted Users")
        else:
            allowed = _("unknown")

        self.AcceptUploads.set_text(_("%s") % allowed)

        if has_pic and pic is not None:
            try:
                import gc
                loader = GdkPixbuf.PixbufLoader()
                loader.write(pic)
                loader.close()
                self.image_pixbuf = loader.get_pixbuf()
                self.image.set_from_pixbuf(self.image_pixbuf)
                del pic, loader
                gc.collect()
                self.actual_zoom = 0
                self.SavePicture.set_sensitive(True)
            except TypeError as e:  # noqa: F841
                name = tempfile.mktemp()
                f = open(name, "w")
                f.write(pic)
                f.close()
                self.image.set_from_file(name)
                os.remove(name)
            except Exception as e:  # noqa: F841
                self.image.set_from_pixbuf(None)
                self.SavePicture.set_sensitive(False)
        else:
            self.image.set_from_pixbuf(None)
            self.SavePicture.set_sensitive(False)

    def ShowInfo(self, msg):
        self.ShowUserInfo(msg.descr, msg.has_pic, msg.pic, msg.totalupl, msg.queuesize, msg.slotsavail, msg.uploadallowed)

    def UpdateGauge(self, msg):

        if msg.total == 0 or msg.bytes == 0:
            fraction = 0.0
        elif msg.bytes >= msg.total:
            fraction = 1.0
        else:
            fraction = float(msg.bytes) / msg.total

        self.progressbar.set_fraction(fraction)

    def OnSendMessage(self, widget):
        self.frame.privatechats.SendMessage(self.user)

    def OnShowIPaddress(self, widget):

        if self.user not in self.frame.np.ip_requested:
            self.frame.np.ip_requested.append(self.user)

        self.frame.np.queue.put(slskmessages.GetPeerAddress(self.user))

    def OnRefresh(self, widget):
        self.frame.LocalUserInfoRequest(self.user)

    def OnBrowseUser(self, widget):
        self.frame.BrowseUser(self.user)

    def OnAddToList(self, widget):
        self.frame.np.userlist.AddToList(self.user)

    def OnBanUser(self, widget):
        self.frame.BanUser(self.user)

    def OnIgnoreUser(self, widget):
        self.frame.IgnoreUser(self.user)

    def OnClose(self, widget):

        del self.userinfos.users[self.user]
        self.frame.np.ClosePeerConnection(self.conn)

        if self.userinfos.is_tab_detached(self.Main):
            self.Main.get_parent_window().destroy()
        else:
            self.userinfos.remove_page(self.Main)
            self.Main.destroy()

    def OnSavePicture(self, widget):

        if self.image is None or self.image_pixbuf is None:
            return

        filename = "%s %s.jpg" % (self.user, time.strftime("%Y-%m-%d %H:%M:%S"))
        pathname = os.path.join(self.frame.np.config.sections["transfers"]["downloaddir"], CleanFile(filename))

        if not os.path.exists(pathname):
            self.image_pixbuf.save(pathname, "jpeg", {"quality": "100"})
            log.add(_("Picture saved to %s") % pathname)
        else:
            log.add(_("Picture not saved, %s already exists.") % pathname)

    def OnEncodingChanged(self, widget):

        encoding = self.Encoding.get_model().get(self.Encoding.get_active_iter(), 0)[0]

        if encoding != self.encoding:
            self.encoding = encoding
            buffer = self.descr.get_buffer()
            buffer.set_text(self.frame.np.decode(self._descr, self.encoding))
            SaveEncoding(self.frame.np, "userencoding", self.user, self.encoding)

    def OnImageClick(self, widget, event):

        if event.type != Gdk.EventType.BUTTON_PRESS or event.button != 3:
            return False

        act = True

        if self.image is None or self.image_pixbuf is None:
            act = False

        items = self.image_menu.get_children()
        for item in items:
            item.set_sensitive(act)

        self.image_menu.popup(None, None, None, None, event.button, event.time)

        return True  # Don't scroll the gtk.ScrolledWindow

    def OnScrollEvent(self, widget, event):

        if event.direction == Gdk.SCROLL_UP:
            self.MakeZoomIn()
        else:
            self.MakeZoomOut()

        return True  # Don't scroll the gtk.ScrolledWindow

    def MakeZoomNormal(self, widget):
        self.MakeZoomIn(zoom=True)

    def MakeZoomIn(self, widget=None, zoom=None):

        def CalcZoomIn(a):
            return a + a * self.actual_zoom / 100 + a * self.zoom_factor / 100

        import gc

        if self.image is None or self.image_pixbuf is None or self.actual_zoom > 100:
            return

        x = self.image_pixbuf.get_width()
        y = self.image_pixbuf.get_height()

        if zoom:
            self.actual_zoom = 0
        else:
            self.actual_zoom += self.zoom_factor

        pixbuf_zoomed = self.image_pixbuf.scale_simple(CalcZoomIn(x), CalcZoomIn(y), Gdk.INTERP_TILES)
        self.image.set_from_pixbuf(pixbuf_zoomed)

        del pixbuf_zoomed

        gc.collect()

    def MakeZoomOut(self, widget=None):

        def CalcZoomOut(a):
            return a + a * self.actual_zoom / 100 - a * self.zoom_factor / 100

        import gc

        if self.image is None or self.image_pixbuf is None:
            return

        x = self.image_pixbuf.get_width()
        y = self.image_pixbuf.get_height()

        self.actual_zoom -= self.zoom_factor

        if CalcZoomOut(x) < 10 or CalcZoomOut(y) < 10:
            self.actual_zoom += self.zoom_factor
            return

        pixbuf_zoomed = self.image_pixbuf.scale_simple(CalcZoomOut(x), CalcZoomOut(y), Gdk.INTERP_TILES)
        self.image.set_from_pixbuf(pixbuf_zoomed)

        del pixbuf_zoomed

        gc.collect()
