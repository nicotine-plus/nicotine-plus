# -*- coding: utf-8 -*-
#
# COPYRIGHT (C) 2016-2017 Michael Labouebe <gfarmerfr@free.fr>
# COPYRIGHT (C) 2008-2009 Quinox <quinox@users.sf.net>
# COPYRIGHT (C) 2006-2009 Daelstorm <daelstorm@gmail.com>
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

from gettext import gettext as _

import gi
from gi.repository import Gdk
from gi.repository import GObject as gobject
from gi.repository import Gtk as gtk

gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')


class MetaDialog(gtk.Dialog):

    def __init__(self, frame, message="", data=None, modal=True, Search=True):

        gtk.Dialog.__init__(self)
        self.connect("destroy", self.quit)
        self.connect("delete-event", self.quit)
        self.nicotine = frame

        if modal:
            self.set_modal(True)

        self.Search = Search

        self.box = gtk.VBox(spacing=10)
        self.box.set_border_width(10)
        self.box.show()
        self.vbox.pack_start(self.box, False, False, 0)

        if message:
            label = gtk.Label()
            label.set_markup(message)
            label.set_line_wrap(False)
            self.box.pack_start(label, False, False, 0)
            label.show()
            label.set_alignment(0, 0.5)

        self.current = 0
        self.data = data

        hbox2 = gtk.HBox(spacing=5)
        hbox2.show()

        self.UF = gtk.Frame()
        self.UF.show()
        self.UF.set_shadow_type(gtk.SHADOW_ETCHED_IN)
        self.box.pack_start(self.UF, False, False, 0)

        vbox3 = gtk.VBox(spacing=5)
        vbox3.set_border_width(5)
        vbox3.show()

        self.UF.add(vbox3)

        self.UsernameLabel, self.Username = self.MakeLabelStaticEntry(
            hbox2,
            "<b>%s:</b>" % _("Username"),
            "",
            expand=False
        )

        self.BrowseUser = self.nicotine.CreateIconButton(
            gtk.STOCK_HARDDISK,
            "stock",
            self.OnBrowseUser, _("Browse")
        )

        hbox2.pack_start(self.BrowseUser, False, False, 0)

        self.PositionLabel, self.Position = self.MakeLabelStaticEntry(
            hbox2,
            _("<b>List Position:</b>"),
            "",
            expand=False,
            width=7,
            xalign=1
        )

        vbox3.pack_start(hbox2, False, False, 0)

        hbox3 = gtk.HBox(spacing=5)
        hbox3.show()
        vbox3.pack_start(hbox3, False, False, 0)

        self.FilenameLabel, self.Filename = self.MakeLabelStaticEntry(
            hbox3,
            _("<b>File Name:</b>"),
            "",
            fill=True
        )

        hbox5 = gtk.HBox(spacing=5)
        hbox5.show()
        vbox3.pack_start(hbox5, False, False, 0)

        self.DirectoryLabel, self.Directory = self.MakeLabelStaticEntry(
            hbox5,
            _("<b>Directory:</b>"),
            "",
            fill=True
        )

        self.Media = gtk.Frame()
        self.Media.show()
        self.Media.set_shadow_type(gtk.SHADOW_ETCHED_IN)
        hbox6 = gtk.HBox(spacing=5, homogeneous=False)
        hbox6.set_border_width(5)
        hbox6.show()

        self.SizeLabel, self.Size = self.MakeLabelStaticEntry(
            hbox6,
            _("<b>File Size:</b>"),
            "",
            expand=False,
            width=11,
            xalign=1
        )

        self.LengthLabel, self.Length = self.MakeLabelStaticEntry(
            hbox6,
            _("<b>Length:</b>"),
            "",
            expand=False,
            width=7,
            xalign=0.5
        )

        self.BitrateLabel, self.Bitrate = self.MakeLabelStaticEntry(
            hbox6,
            _("<b>Bitrate:</b>"),
            "",
            expand=False,
            width=12,
            xalign=0.5
        )

        self.Media.add(hbox6)
        self.box.pack_start(self.Media, False, False, 0)

        hbox7 = gtk.HBox(spacing=5, homogeneous=False)
        hbox7.show()
        self.box.pack_start(hbox7, False, False, 0)

        self.ImmediateLabel, self.Immediate = self.MakeLabelStaticEntry(
            hbox7,
            _("<b>Immediate Downloads:</b>"),
            "",
            expand=False,
            width=6,
            xalign=0.5
        )

        self.QueueLabel, self.Queue = self.MakeLabelStaticEntry(
            hbox7,
            _("<b>Queue:</b>"),
            "",
            expand=False,
            width=6,
            xalign=1
        )

        hbox4 = gtk.HBox(spacing=5, homogeneous=False)
        hbox4.show()
        self.box.pack_start(hbox4, False, False, 0)

        self.SpeedLabel, self.Speed = self.MakeLabelStaticEntry(
            hbox4,
            _("<b>Last Speed:</b>"),
            "",
            expand=False,
            width=11,
            xalign=1
        )

        self.Country = gtk.Label()
        self.Country.hide()

        hbox4.pack_start(self.Country, False, False, 0)

        self.buttonbox = gtk.HBox(False, 2)
        self.buttonbox.show()
        self.buttonbox.set_spacing(2)

        self.box.pack_start(self.buttonbox, False, False, 0)

        # Download Button
        self.DownloadItem = self.nicotine.CreateIconButton(
            gtk.STOCK_GO_DOWN,
            "stock",
            self.OnDownloadItem,
            _("Download")
        )

        self.buttonbox.pack_start(self.DownloadItem, False, False, 0)

        # Download All Button
        self.DownloadAll = self.nicotine.CreateIconButton(
            gtk.STOCK_GO_DOWN,
            "stock",
            self.OnDownloadAll,
            _("Download All")
        )

        self.buttonbox.pack_start(self.DownloadAll, False, False, 0)

        self.Selected = self.MakeLabel(
            self.buttonbox,
            _("<b>%s</b> File(s) Selected") % len(list(self.data.keys())),
            expand=False,
            xalign=1
        )

        self.Previous = self.nicotine.CreateIconButton(
            gtk.STOCK_GO_BACK,
            "stock",
            self.OnPrevious,
            _("Previous")
        )

        self.Next = self.nicotine.CreateIconButton(
            gtk.STOCK_GO_FORWARD,
            "stock",
            self.OnNext,
            _("Next")
        )

        self.buttonbox.pack_end(self.Next, False, False)
        self.buttonbox.pack_end(self.Previous, False, False)

        button = self.nicotine.CreateIconButton(
            gtk.STOCK_CLOSE,
            "stock",
            self.click,
            _("Close")
        )

        button.props.can_default = True
        self.action_area.pack_start(button, False, False, 0)

        button.grab_default()

        self.ret = None

        self.Display(self.current)

    def OnDownloadItem(self, widget):
        meta = self.data[self.current]
        self.nicotine.np.transfers.getFile(meta["user"], meta["fn"], "")

    def OnBrowseUser(self, widget):
        meta = self.data[self.current]
        self.nicotine.BrowseUser(meta["user"])

    def OnDownloadAll(self, widget):
        for item, meta in list(self.data.items()):
            self.nicotine.np.transfers.getFile(meta["user"], meta["fn"], "")

    def OnPrevious(self, widget):

        if len(list(self.data.keys())) > 1:

            _list = list(self.data.keys())

            if self.current not in _list:
                ix -= 1  # noqa: F821
            else:
                ix = _list.index(self.current)
                ix -= 1

                if ix < 0:
                    ix = -1
                elif ix >= len(_list):
                    ix = 0

            if ix is not None:
                self.current = _list[ix]

        if self.current is None:
            return

        self.Display(self.current)

    def OnNext(self, widget):

        if len(list(self.data.keys())) > 1:

            _list = list(self.data.keys())

            if self.current not in _list:
                ix += 1  # noqa: F821
            else:
                ix = _list.index(self.current)
                ix += 1

                if ix < 0:
                    ix = -1
                elif ix >= len(_list):
                    ix = 0

            if ix is not None:
                self.current = _list[ix]

        if self.current is None:
            return

        self.Display(self.current)

    def Display(self, item):

        if item not in self.data:
            return

        if not self.Search:
            self.Immediate.hide()
            self.Position.hide()
            self.Country.hide()
            self.Queue.hide()
            self.Immediate.hide()
            self.ImmediateLabel.hide()
            self.PositionLabel.hide()
            self.QueueLabel.hide()
            self.ImmediateLabel.hide()
            self.DownloadItem.hide()
            self.DownloadAll.hide()
        else:
            self.Immediate.show()
            self.Position.show()
            self.Country.show()
            self.Queue.show()
            self.Immediate.show()
            self.ImmediateLabel.show()
            self.PositionLabel.show()
            self.QueueLabel.show()
            self.ImmediateLabel.show()
            self.DownloadItem.show()
            self.DownloadAll.show()

        self.current = item
        data = self.data[self.current]
        More = False

        if len(list(self.data.keys())) > 1:
            More = True

        self.Next.set_sensitive(More)
        self.Previous.set_sensitive(More)
        self.DownloadAll.set_sensitive(More)

        self.Username.set_text(data["user"])
        self.Filename.set_text(data["filename"])
        self.Directory.set_text(data["directory"])
        self.Size.set_text(str(data["size"]))
        self.Speed.set_text(data["speed"])
        self.Position.set_text(str(data["position"]))

        if data["bitrate"] not in ("", None):
            self.Bitrate.set_text(data["bitrate"])
        else:
            self.Bitrate.set_text("")

        self.Length.set_text(data["length"])
        self.Queue.set_text(data["queue"])
        self.Immediate.set_text(str(data["immediate"] == "Y"))

        country = data["country"]
        if country not in ("", None):
            self.Country.set_markup(_("<b>Country Code:</b> ") + country)
            self.Country.show()
        else:
            self.Country.set_text("")
            self.Country.hide()

    def quit(self, w=None, event=None):
        self.hide()
        self.destroy()
        gtk.main_quit()

    def click(self, button):
        self.quit()

    def MakeLabel(self, parent, labeltitle, expand=True, fill=False, xalign=0):

        label = gtk.Label()
        label.set_markup(labeltitle)
        label.show()
        parent.pack_start(label, expand, fill, 0)

        try:
            label.set_property("xalign", xalign)
        except Exception as e:
            print(e)
            pass

        return label

    def MakeLabelStaticEntry(self, parent, labeltitle, entrydata,
                             editable=False, expand=True, fill=False,
                             width=-1, xalign=0):

        label = gtk.Label()
        label.set_markup(labeltitle)
        label.show()

        parent.pack_start(label, False, False, 0)

        entry = gtk.Entry()
        entry.set_property("editable", editable)
        entry.set_property("width-chars", width)

        try:
            entry.set_property("xalign", xalign)
        except Exception:
            pass

        entry.show()
        if entrydata is not None:
            entry.set_text(entrydata)
        parent.pack_start(entry, expand, fill, 0)
        return label, entry


class EntryDialog(gtk.Dialog):

    def __init__(self, frame, message="", default_text="",
                 option=False, optionmessage="",
                 optionvalue=False, droplist=[]):

        gtk.Dialog.__init__(self)

        self.connect("destroy", self.quit)
        self.connect("delete-event", self.quit)

        self.gotoption = option

        box = gtk.VBox(spacing=10)
        box.set_border_width(10)
        self.vbox.pack_start(box, False, False, 0)
        box.show()

        if message:
            label = gtk.Label(message)
            box.pack_start(label, False, False, 0)
            label.set_line_wrap(True)
            label.show()

        self.combo_List = gtk.ListStore(gobject.TYPE_STRING)
        self.combo = gtk.ComboBox.new_with_model_and_entry(model=self.combo_List)
        self.combo.set_entry_text_column(0)

        for i in droplist:
            self.combo_List.append([i])

        self.combo.get_child().set_text(default_text)

        box.pack_start(self.combo, False, False, 0)

        self.combo.show()
        self.combo.grab_focus()

        if self.gotoption:

            self.option = gtk.CheckButton()
            self.option.set_active(optionvalue)
            self.option.set_label(optionmessage)
            self.option.show()

            box.pack_start(self.option, False, False, 0)

        button = gtk.Button(_("Cancel"))
        button.connect("clicked", self.quit)
        button.props.can_default = True
        self.action_area.pack_start(button, False, False, 0)

        button.show()

        button = gtk.Button(_("OK"))
        button.connect("clicked", self.click)
        button.props.can_default = True
        self.action_area.pack_start(button, False, False, 0)

        button.show()
        button.grab_default()

        # Set modal to True to avoid wrong window having the focus
        self.set_modal(True)

        self.ret = None

    def quit(self, w=None, event=None):
        self.hide()
        self.destroy()
        gtk.main_quit()

    def click(self, button):

        if self.gotoption:
            self.ret = [self.combo.get_child().get_text(), self.option.get_active()]
        else:
            self.ret = self.combo.get_child().get_text()

        self.quit()


def input_box(frame, title="Input Box", message="", default_text="",
              modal=True, option=False, optionmessage="",
              optionvalue=False, droplist=[]):

    win = EntryDialog(
        frame, message, default_text,
        option=option, optionmessage=optionmessage,
        optionvalue=optionvalue, droplist=droplist
    )

    win.set_title(title)
    win.set_icon(frame.images["n"])

    hints_geometry = Gdk.Geometry()
    hints_geometry.min_width = 300
    win.set_geometry_hints(None, hints_geometry, Gdk.WindowHints(Gdk.WindowHints.MIN_SIZE))
    win.show()

    gtk.main()

    return win.ret


class FindDialog(gtk.Dialog):

    def __init__(self, frame, message="", default_text='',
                 textview=None, modal=True):

        gtk.Dialog.__init__(self)

        # Test if the signal is already binded since we do not clear it
        # when we destroy FindDialog
        if not gobject.signal_lookup("find-click", gtk.Window):
            gobject.signal_new(
                "find-click",
                gtk.Window,
                gobject.SIGNAL_RUN_LAST,
                gobject.TYPE_NONE,
                (gobject.TYPE_STRING,)
            )

        self.textview = textview
        self.nicotine = frame

        self.connect("delete-event", self.quit)

        # The destroy event shoul clean up the reference to FindDialog
        # in the NicotineFrame object
        self.connect("destroy", self.destroy)

        self.nextPosition = None
        self.currentPosition = None
        self.lastdirection = "next"

        if modal:
            self.set_modal(True)

        box = gtk.VBox(spacing=10)
        box.set_border_width(10)
        self.vbox.pack_start(box, False, False, 0)
        box.show()

        if message:
            label = gtk.Label(message)
            box.pack_start(label, False, False, 0)
            label.set_line_wrap(True)
            label.show()

        self.entry = gtk.Entry()

        box.pack_start(self.entry, False, False, 0)
        self.entry.show()
        self.entry.grab_focus()
        self.entry.connect("activate", self.__next__)

        Cancelbutton = self.nicotine.CreateIconButton(
            gtk.STOCK_CANCEL,
            "stock",
            self.quit,
            _("Cancel")
        )
        Cancelbutton.props.can_default = True
        self.action_area.pack_start(Cancelbutton, False, False, 0)

        Previousbutton = self.nicotine.CreateIconButton(
            gtk.STOCK_GO_BACK,
            "stock",
            self.previous,
            _("Previous")
        )
        Previousbutton.props.can_default = True
        self.action_area.pack_start(Previousbutton, False, False, 0)

        Nextbutton = self.nicotine.CreateIconButton(
            gtk.STOCK_GO_FORWARD,
            "stock",
            self.__next__,
            _("Next")
        )
        Nextbutton.props.can_default = True
        self.action_area.pack_start(Nextbutton, False, False, 0)
        Nextbutton.grab_default()

    def next(self, button):
        self.emit("find-click", "next")

    def previous(self, button):
        self.emit("find-click", "previous")

    def quit(self, w=None, event=None):
        self.hide()

    def destroy(self, w=None, event=None):
        if "FindDialog" in self.nicotine.__dict__:
            del self.nicotine.FindDialog


def FolderDownload(frame, title="Option Box", message="", default_text='',
                   modal=True, data=None, callback=None):

    win = FolderDownloadDialog(frame, message, modal=modal)
    win.connect("response", callback, data)
    win.set_title(title)
    win.set_icon(frame.images["n"])
    win.show()


class FolderDownloadDialog(gtk.Dialog):

    def __init__(self, frame, message="", modal=False, ):

        gtk.Dialog.__init__(self)

        self.connect("destroy", self.quit)
        self.connect("delete-event", self.quit)

        self.nicotine = frame

        self.set_modal(modal)
        box = gtk.VBox(spacing=10)
        box.set_border_width(10)
        self.vbox.pack_start(box, False, False, 0)
        box.show()
        hbox = gtk.HBox(spacing=5)
        hbox.set_border_width(5)
        hbox.show()
        box.pack_start(hbox, False, False, 0)

        image = gtk.Image()
        image.set_padding(0, 0)
        icon = gtk.STOCK_DIALOG_QUESTION
        image.set_from_stock(icon, 4)
        image.show()
        hbox.pack_start(image, False, False, 0)

        if message:
            label = gtk.Label(message)
            hbox.pack_start(label, False, False, 0)
            label.set_line_wrap(True)
            label.show()

        hbox2 = gtk.HBox(spacing=5)
        hbox2.set_border_width(5)
        hbox2.show()
        box.pack_start(hbox2, False, False, 0)

        cancel_button = self.add_button(gtk.STOCK_CANCEL, gtk.ResponseType.CANCEL)  # noqa: F841
        ok_button = self.add_button(gtk.STOCK_OK, gtk.ResponseType.OK)
        ok_button.grab_default()

    def quit(self, *args):
        self.destroy()


def QuitBox(frame, title="Option Box", message="", default_text='',
            modal=True, status=None, tray=False, third=""):

    win = OptionDialog(frame, message, modal=modal, status=status,
                       option=tray, third=third, rememberbox=True)
    win.connect("response", frame.on_quit_response)
    win.set_title(title)
    win.set_icon(frame.images["n"])
    win.show()
    return win


class OptionDialog(gtk.Dialog):

    def __init__(self, frame, message="", modal=False, status=None,
                 option=False, third="", rememberbox=False):

        gtk.Dialog.__init__(self)

        self.connect("destroy", self.quit)
        self.connect("delete-event", self.quit)

        self.nicotine = frame

        self.set_modal(modal)
        box = gtk.VBox(spacing=10)
        box.set_border_width(10)
        self.vbox.pack_start(box, False, False, 0)
        box.show()
        hbox = gtk.HBox(spacing=5)
        hbox.set_border_width(5)
        hbox.show()
        box.pack_start(hbox, False, False, 0)

        if status:
            image = gtk.Image()
            image.set_padding(0, 0)
            if status == "warning":
                icon = gtk.STOCK_DIALOG_WARNING
            else:
                icon = gtk.STOCK_DIALOG_QUESTION
            image.set_from_stock(icon, 4)
            image.show()
            hbox.pack_start(image, False, False, 0)

        if message:
            label = gtk.Label(message)
            hbox.pack_start(label, False, False, 0)
            label.set_line_wrap(True)
            label.show()

        hbox2 = gtk.HBox(spacing=5)
        hbox2.set_border_width(5)
        hbox2.show()
        box.pack_start(hbox2, False, False, 0)

        # Storing under self. so we can find it easily later
        if rememberbox:
            self.checkbox = gtk.CheckButton("Remember choice")
            box.pack_start(self.checkbox, False, False, 0)
            self.checkbox.show()

        if option:
            Alignment = gtk.Alignment(xalign=0.5, yalign=0.5, xscale=0, yscale=0)
            Alignment.show()

            Hbox = gtk.HBox(False, 2)
            Hbox.show()
            Hbox.set_spacing(2)

            image = gtk.Image()
            image.set_padding(0, 0)

            image.set_from_stock(gtk.STOCK_GO_DOWN, 4)
            image.show()
            Hbox.pack_start(image, False, False, 0)
            Alignment.add(Hbox)

            if label:
                Label = gtk.Label(third)
                Label.set_padding(0, 0)
                Label.show()
                Hbox.pack_start(Label, False, False, 0)

            tray_button = self.add_button("", gtk.ResponseType.REJECT)
            tray_button.remove(tray_button.get_child())
            tray_button.add(Alignment)

        cancel_button = self.add_button(gtk.STOCK_CANCEL, gtk.ResponseType.CANCEL)  # noqa: F841
        ok_button = self.add_button(gtk.STOCK_OK, gtk.ResponseType.OK)
        ok_button.grab_default()

    def quit(self, *args):
        self.destroy()
