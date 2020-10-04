# COPYRIGHT (C) 2020 Nicotine+ Team
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

from gi.repository import GObject as gobject
from gi.repository import Gtk as gtk


def combo_box_dialog(parent, title, message, default_text="",
                     option=False, optionmessage="",
                     optionvalue=False, droplist=[]):

    self = gtk.MessageDialog(
        transient_for=parent,
        flags=0,
        message_type=gtk.MessageType.QUESTION,
        buttons=gtk.ButtonsType.OK_CANCEL,
        text=title
    )
    self.set_default_size(500, -1)
    self.set_modal(True)
    self.format_secondary_text(message)

    self.gotoption = option

    self.combo_list = gtk.ListStore(gobject.TYPE_STRING)
    self.combo = gtk.ComboBox.new_with_model_and_entry(model=self.combo_list)
    self.combo.set_entry_text_column(0)

    for i in droplist:
        self.combo_list.append([i])

    self.combo.get_child().set_text(default_text)

    self.get_message_area().pack_start(self.combo, False, False, 0)

    self.combo.show()
    self.combo.grab_focus()

    if self.gotoption:

        self.option = gtk.CheckButton()
        self.option.set_active(optionvalue)
        self.option.set_label(optionmessage)
        self.option.show()

        self.get_message_area().pack_start(self.option, False, False, 0)

    result = None
    if self.run() == gtk.ResponseType.OK:
        if self.gotoption:
            result = [self.combo.get_child().get_text(), self.option.get_active()]
        else:
            result = self.combo.get_child().get_text()

    self.destroy()

    return result


def entry_dialog(parent, title, message, default=""):

    self = gtk.MessageDialog(
        transient_for=parent,
        flags=0,
        message_type=gtk.MessageType.QUESTION,
        buttons=gtk.ButtonsType.OK_CANCEL,
        text=title
    )
    self.set_default_size(500, -1)
    self.set_modal(True)
    self.format_secondary_text(message)

    entry = gtk.Entry()
    entry.set_activates_default(True)
    entry.set_text(default)
    self.get_message_area().pack_start(entry, True, True, 0)
    entry.show()

    result = None
    if self.run() == gtk.ResponseType.OK:
        result = entry.get_text()

    self.destroy()

    return result


def option_dialog(parent, title, message, callback, callback_data=None, checkbox_label="", third=""):

    self = gtk.MessageDialog(
        transient_for=parent,
        flags=0,
        message_type=gtk.MessageType.QUESTION,
        buttons=gtk.ButtonsType.OK_CANCEL,
        text=title
    )
    self.connect("response", callback, callback_data)
    self.set_modal(True)
    self.format_secondary_text(message)

    if checkbox_label:
        self.checkbox = gtk.CheckButton()
        self.checkbox.set_label(checkbox_label)
        self.get_message_area().pack_start(self.checkbox, False, False, 0)
        self.checkbox.show()

    if third:
        self.add_button(third, gtk.ResponseType.REJECT)

    self.show()


class MetaDialog(gtk.Dialog):

    def __init__(self, frame, message="", data=None, modal=True, search=True):

        gtk.Dialog.__init__(self)
        self.connect("destroy", self.quit)
        self.connect("delete-event", self.quit)
        self.nicotine = frame

        self.set_transient_for(frame.MainWindow)

        if modal:
            self.set_modal(True)

        self.search = search

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
        self.UF.set_shadow_type(gtk.ShadowType.ETCHED_IN)
        self.box.pack_start(self.UF, False, False, 0)

        vbox3 = gtk.VBox(spacing=5)
        vbox3.set_border_width(5)
        vbox3.show()

        self.UF.add(vbox3)

        self.username_label, self.username = self.make_label_static_entry(
            hbox2,
            "<b>%s:</b>" % _("Username"),
            "",
            expand=False
        )

        self.browse_user = self.nicotine.create_icon_button(
            gtk.STOCK_HARDDISK,
            "stock",
            self.on_browse_user, _("Browse")
        )

        hbox2.pack_start(self.browse_user, False, False, 0)

        self.position_label, self.position = self.make_label_static_entry(
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

        self.filename_label, self.filename = self.make_label_static_entry(
            hbox3,
            _("<b>File Name:</b>"),
            "",
            fill=True
        )

        hbox5 = gtk.HBox(spacing=5)
        hbox5.show()
        vbox3.pack_start(hbox5, False, False, 0)

        self.directory_label, self.directory = self.make_label_static_entry(
            hbox5,
            _("<b>Directory:</b>"),
            "",
            fill=True
        )

        self.media = gtk.Frame()
        self.media.show()
        self.media.set_shadow_type(gtk.ShadowType.ETCHED_IN)
        hbox6 = gtk.HBox(spacing=5, homogeneous=False)
        hbox6.set_border_width(5)
        hbox6.show()

        self.size_label, self.size = self.make_label_static_entry(
            hbox6,
            _("<b>File Size:</b>"),
            "",
            expand=False,
            width=11,
            xalign=1
        )

        self.length_label, self.length = self.make_label_static_entry(
            hbox6,
            _("<b>Length:</b>"),
            "",
            expand=False,
            width=7,
            xalign=0.5
        )

        self.bitrate_label, self.bitrate = self.make_label_static_entry(
            hbox6,
            _("<b>Bitrate:</b>"),
            "",
            expand=False,
            width=12,
            xalign=0.5
        )

        self.media.add(hbox6)
        self.box.pack_start(self.media, False, False, 0)

        hbox7 = gtk.HBox(spacing=5, homogeneous=False)
        hbox7.show()
        self.box.pack_start(hbox7, False, False, 0)

        self.immediate_label, self.immediate = self.make_label_static_entry(
            hbox7,
            _("<b>Immediate Downloads:</b>"),
            "",
            expand=False,
            width=6,
            xalign=0.5
        )

        self.queue_label, self.queue = self.make_label_static_entry(
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

        self.speed_label, self.speed = self.make_label_static_entry(
            hbox4,
            _("<b>Last Speed:</b>"),
            "",
            expand=False,
            width=11,
            xalign=1
        )

        self.country = gtk.Label()
        self.country.hide()

        hbox4.pack_start(self.country, False, False, 0)

        self.buttonbox = gtk.HBox(False, 2)
        self.buttonbox.show()
        self.buttonbox.set_spacing(2)

        self.box.pack_start(self.buttonbox, False, False, 0)

        # Download Button
        self.download_item = self.nicotine.create_icon_button(
            gtk.STOCK_GO_DOWN,
            "stock",
            self.on_download_item,
            _("Download")
        )

        self.buttonbox.pack_start(self.download_item, False, False, 0)

        # Download All Button
        self.download_all = self.nicotine.create_icon_button(
            gtk.STOCK_GO_DOWN,
            "stock",
            self.on_download_all,
            _("Download All")
        )

        self.buttonbox.pack_start(self.download_all, False, False, 0)

        self.selected = self.make_label(
            self.buttonbox,
            _("<b>%s</b> File(s) Selected") % len(self.data),
            expand=False,
            xalign=1
        )

        self.previous = self.nicotine.create_icon_button(
            gtk.STOCK_GO_BACK,
            "stock",
            self.on_previous,
            _("Previous")
        )

        self.next = self.nicotine.create_icon_button(
            gtk.STOCK_GO_FORWARD,
            "stock",
            self.on_next,
            _("Next")
        )

        self.buttonbox.pack_end(self.next, False, False, 0)
        self.buttonbox.pack_end(self.previous, False, False, 0)

        button = self.nicotine.create_icon_button(
            gtk.STOCK_CLOSE,
            "stock",
            self.click,
            _("Close")
        )

        button.props.can_default = True
        self.action_area.pack_start(button, False, False, 0)

        button.grab_default()

        self.ret = None

        self.display(self.current)

    def on_download_item(self, widget):
        meta = self.data[self.current]
        self.nicotine.np.transfers.get_file(meta["user"], meta["fn"], "", checkduplicate=True)

    def on_browse_user(self, widget):
        meta = self.data[self.current]
        self.nicotine.browse_user(meta["user"])

    def on_download_all(self, widget):
        for item, meta in list(self.data.items()):
            self.nicotine.np.transfers.get_file(meta["user"], meta["fn"], "", checkduplicate=True)

    def on_previous(self, widget):

        if len(self.data) > 1:

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

        self.display(self.current)

    def on_next(self, widget):

        if len(self.data) > 1:

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

        self.display(self.current)

    def display(self, item):

        if item not in self.data:
            return

        if not self.search:
            self.immediate.hide()
            self.position.hide()
            self.country.hide()
            self.queue.hide()
            self.immediate.hide()
            self.immediate_label.hide()
            self.position_label.hide()
            self.queue_label.hide()
            self.immediate_label.hide()
            self.download_item.hide()
            self.download_all.hide()
        else:
            self.immediate.show()
            self.position.show()
            self.country.show()
            self.queue.show()
            self.immediate.show()
            self.immediate_label.show()
            self.position_label.show()
            self.queue_label.show()
            self.immediate_label.show()
            self.download_item.show()
            self.download_all.show()

        self.current = item
        data = self.data[self.current]
        more = False

        if len(self.data) > 1:
            more = True

        self.next.set_sensitive(more)
        self.previous.set_sensitive(more)
        self.download_all.set_sensitive(more)

        self.username.set_text(data["user"])
        self.filename.set_text(data["filename"])
        self.directory.set_text(data["directory"])
        self.size.set_text(str(data["size"]))
        self.speed.set_text(data["speed"])
        self.position.set_text(str(data["position"]))

        if data["bitrate"] not in ("", None):
            self.bitrate.set_text(data["bitrate"])
        else:
            self.bitrate.set_text("")

        self.length.set_text(data["length"])
        self.queue.set_text(data["queue"])
        self.immediate.set_text(str(data["immediate"] == "Y"))

        country = data["country"]
        if country not in ("", None):
            self.country.set_markup(_("<b>Country Code:</b> ") + country)
            self.country.show()
        else:
            self.country.set_text("")
            self.country.hide()

    def quit(self, w=None, event=None):
        self.hide()
        self.destroy()
        gtk.main_quit()

    def click(self, button):
        self.quit()

    def make_label(self, parent, labeltitle, expand=True, fill=False, xalign=0):

        label = gtk.Label()
        label.set_markup(labeltitle)
        label.show()
        parent.pack_start(label, expand, fill, 0)

        try:
            label.set_property("xalign", xalign)
        except Exception as e:
            print(e)

        return label

    def make_label_static_entry(self, parent, labeltitle, entrydata,
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
