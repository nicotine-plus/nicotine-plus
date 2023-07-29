# COPYRIGHT (C) 2020-2023 Nicotine+ Contributors
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

from gi.repository import Gdk
from gi.repository import GLib
from gi.repository import Gtk

from pynicotine.config import config
from pynicotine.gtkgui.application import GTK_API_VERSION
from pynicotine.gtkgui.application import LIBADWAITA_API_VERSION
from pynicotine.gtkgui.widgets.accelerator import Accelerator
from pynicotine.gtkgui.widgets.textentry import ComboBox
from pynicotine.gtkgui.widgets.textview import TextView
from pynicotine.gtkgui.widgets.theme import add_css_class
from pynicotine.gtkgui.widgets.window import Window

""" Dialogs """


class Dialog(Window):

    def __init__(self, widget=None, parent=None, content_box=None, buttons_start=(), buttons_end=(),
                 default_button=None, show_callback=None, close_callback=None, title="", width=0, height=0,
                 modal=True, resizable=True, close_destroy=True, show_title=True, show_title_buttons=True):

        self.parent = parent
        self.modal = modal
        self.default_width = width
        self.default_height = height
        self.default_button = default_button
        self.close_destroy = close_destroy

        self.show_callback = show_callback
        self.close_callback = close_callback

        if widget:
            super().__init__(widget=widget)
            self._set_dialog_properties()
            return

        container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, vexpand=True, visible=True)
        widget = Gtk.Window(
            default_width=width,
            default_height=height,
            resizable=resizable,
            child=container
        )
        super().__init__(widget)
        Accelerator("Escape", widget, self.close)

        if GTK_API_VERSION == 3:
            widget.set_position(Gtk.WindowPosition.CENTER_ON_PARENT)  # pylint: disable=no-member
            widget.set_type_hint(Gdk.WindowTypeHint.DIALOG)           # pylint: disable=no-member

        if content_box:
            if GTK_API_VERSION >= 4:
                container.append(content_box)  # pylint: disable=no-member
            else:
                container.add(content_box)     # pylint: disable=no-member

        if config.sections["ui"]["header_bar"]:
            self._init_header_bar(buttons_start, buttons_end, show_title, show_title_buttons)
        else:
            self._init_action_area(container, buttons_start, buttons_end)

        if default_button:
            if GTK_API_VERSION >= 4:
                widget.set_default_widget(default_button)  # pylint: disable=no-member
            else:
                default_button.set_can_default(True)       # pylint: disable=no-member
                widget.set_default(default_button)         # pylint: disable=no-member

        self.set_title(title)
        self._set_dialog_properties()

    def _init_header_bar(self, buttons_start=(), buttons_end=(), show_title=True, show_title_buttons=True):

        header_bar = Gtk.HeaderBar()
        self.widget.set_titlebar(header_bar)

        if GTK_API_VERSION >= 4:
            header_bar.set_show_title_buttons(show_title_buttons)    # pylint: disable=no-member

            if not show_title:
                header_bar.set_title_widget(Gtk.Box())               # pylint: disable=no-member
                add_css_class(header_bar, "flat")
        else:
            header_bar.set_show_close_button(show_title_buttons)     # pylint: disable=no-member

            if not show_title:
                header_bar.set_custom_title(Gtk.Box(visible=False))  # pylint: disable=no-member

        for button in buttons_start:
            header_bar.pack_start(button)

        for button in reversed(buttons_end):
            header_bar.pack_end(button)

        header_bar.set_visible(True)

    def _init_action_area(self, container, buttons_start=(), buttons_end=()):

        if not buttons_start and not buttons_end:
            return

        action_area = Gtk.Box(visible=True)
        action_area_start = Gtk.Box(homogeneous=True, margin_start=6, margin_end=6, margin_top=6, margin_bottom=6,
                                    spacing=6, visible=True)
        action_area_end = Gtk.Box(halign=Gtk.Align.END, hexpand=True, homogeneous=True,
                                  margin_start=6, margin_end=6, margin_top=6, margin_bottom=6, spacing=6, visible=True)

        add_css_class(action_area, "action-area")

        if GTK_API_VERSION >= 4:
            container.append(action_area)             # pylint: disable=no-member
            action_area.append(action_area_start)     # pylint: disable=no-member
            action_area.append(action_area_end)       # pylint: disable=no-member
        else:
            container.add(action_area)                # pylint: disable=no-member
            action_area.add(action_area_start)        # pylint: disable=no-member
            action_area.add(action_area_end)          # pylint: disable=no-member

        for button in buttons_start:
            if GTK_API_VERSION >= 4:
                action_area_start.append(button)      # pylint: disable=no-member
            else:
                action_area_start.add(button)         # pylint: disable=no-member

        for button in buttons_end:
            if GTK_API_VERSION >= 4:
                action_area_end.append(button)        # pylint: disable=no-member
            else:
                action_area_end.add(button)           # pylint: disable=no-member

    def _on_show(self, *_args):
        if self.show_callback is not None:
            self.show_callback(self)

    def _on_close_request(self, *_args):

        if self not in Window.active_dialogs:
            return False

        Window.active_dialogs.remove(self)

        if self.close_callback is not None:
            self.close_callback(self)

        if self.close_destroy:
            return False

        # Hide the dialog
        self.widget.set_visible(False)

        # "Soft-delete" the dialog. This is necessary to prevent the dialog from
        # appearing in window peek on Windows
        self.widget.unrealize()

        return True

    def _set_dialog_properties(self):

        if GTK_API_VERSION >= 4:
            self.widget.connect("close-request", self._on_close_request)
        else:
            self.widget.connect("delete-event", self._on_close_request)

        self.widget.connect("show", self._on_show)

        if self.parent:
            self.widget.set_transient_for(self.parent.widget)

    def _resize_dialog(self):

        if self.widget.get_visible():
            return

        dialog_width = self.default_width
        dialog_height = self.default_height

        if not dialog_width and not dialog_height:
            return

        main_window_width = self.parent.get_width()
        main_window_height = self.parent.get_height()

        if main_window_width and dialog_width > main_window_width:
            dialog_width = main_window_width - 30

        if main_window_height and dialog_height > main_window_height:
            dialog_height = main_window_height - 30

        self.widget.set_default_size(dialog_width, dialog_height)

    def _focus_default_button(self):

        if not self.default_button:
            return

        if not self.default_button.get_visible():
            return

        self.default_button.grab_focus()

    def _finish_show(self):
        self.widget.set_modal(self.modal and self.parent.is_visible())
        self.widget.present()

    def show(self):

        if self not in Window.active_dialogs:
            Window.active_dialogs.append(self)

        # Shrink the dialog if it's larger than the main window
        self._resize_dialog()

        # Focus default button
        self._focus_default_button()

        if not self.parent.is_visible():
            # In case parent window appears a few frames later, ensure dialog is modal
            GLib.idle_add(self._finish_show, priority=GLib.PRIORITY_LOW)
            return

        # Show the dialog
        self._finish_show()

    def close(self, *_args):
        self.widget.close()


""" Message Dialogs """


class MessageDialog(Window):

    def __init__(self, parent, title, message, callback=None, callback_data=None, long_message=None,
                 buttons=None, destructive_response_id=None):

        # Prioritize modal non-message dialogs as parent
        for active_dialog in reversed(Window.active_dialogs):
            if isinstance(active_dialog, Dialog) and active_dialog.modal:
                parent = active_dialog
                break

        self.parent = parent
        self.callback = callback
        self.callback_data = callback_data
        self.destructive_response_id = destructive_response_id
        self.container = None
        self.response_ids = {}

        if not buttons:
            buttons = [("cancel", _("Close"))]

        widget = self._create_dialog(title, message, buttons)
        super().__init__(widget=widget)

        self._add_long_message(long_message)

    def _create_dialog_adw(self, title, message, buttons):

        from gi.repository import Adw  # pylint: disable=no-name-in-module

        self.container = Gtk.Box(hexpand=True, orientation=Gtk.Orientation.VERTICAL, spacing=6, visible=False)
        widget = Adw.MessageDialog(
            transient_for=self.parent.widget if self.parent else None, close_response="cancel",
            heading=title, body=message, body_use_markup=True, extra_child=self.container
        )
        self.response_ids["cancel"] = "cancel"

        for response_type, button_label in buttons:
            widget.add_response(response_type, button_label)
            self.response_ids[response_type] = response_type

            if response_type == self.destructive_response_id:
                widget.set_response_appearance(response_type, Adw.ResponseAppearance.DESTRUCTIVE)
                continue

            if response_type in ("cancel", "ok"):
                widget.set_default_response(response_type)

                if response_type == "ok":
                    widget.set_response_appearance(response_type, Adw.ResponseAppearance.SUGGESTED)

        return widget

    def _create_dialog_gtk(self, title, message, buttons):

        widget = Gtk.MessageDialog(
            transient_for=self.parent.widget if self.parent else None, destroy_with_parent=True,
            message_type=Gtk.MessageType.OTHER,
            text=title, secondary_text=message, secondary_use_markup=True
        )
        current_response_id = 0
        self.response_ids[Gtk.ResponseType.DELETE_EVENT] = "cancel"

        for response_type, button_label in buttons:
            response_id = current_response_id
            self.response_ids[response_id] = response_type
            current_response_id += 1

            if response_type == self.destructive_response_id:
                button = Gtk.Button(label=button_label, use_underline=True, visible=True)
                add_css_class(button, "destructive-action")
                widget.add_action_widget(button, response_id)
                continue

            widget.add_button(button_label, response_id)

            if response_type in ("cancel", "ok"):
                widget.set_default_response(response_id)

        self.container = widget.get_message_area()
        self._make_message_selectable()

        return widget

    def _create_dialog(self, title, message, buttons):

        if LIBADWAITA_API_VERSION:
            widget = self._create_dialog_adw(title, message, buttons)
        else:
            widget = self._create_dialog_gtk(title, message, buttons)

        widget.connect("response", self.on_response)
        return widget

    def _make_message_selectable(self):

        if GTK_API_VERSION >= 4:
            label = self.container.get_last_child()
        else:
            label = self.container.get_children()[-1]

        label.set_selectable(True)

    def _add_long_message(self, text):

        if not text:
            return

        box = Gtk.Box(visible=True)
        scrolled_window = Gtk.ScrolledWindow(min_content_height=75, max_content_height=200,
                                             hexpand=True, vexpand=True, propagate_natural_height=True, visible=True)
        frame = Gtk.Frame(child=box, margin_top=6, visible=True)

        if GTK_API_VERSION >= 4:
            box.append(scrolled_window)   # pylint: disable=no-member
            self.container.append(frame)  # pylint: disable=no-member
        else:
            box.add(scrolled_window)      # pylint: disable=no-member
            self.container.add(frame)     # pylint: disable=no-member

        textview = TextView(scrolled_window, editable=False)
        textview.append_line(text)

        self.container.set_visible(True)

    def on_response(self, _widget, response_id):

        if self not in Window.active_dialogs:
            return

        Window.active_dialogs.remove(self)
        response_id = self.response_ids[response_id]

        if self.callback and response_id != "cancel":
            self.callback(self, response_id, self.callback_data)

        self.widget.destroy()

    def _finish_show(self):
        self.widget.set_modal(self.parent and self.parent.is_visible())
        self.widget.present()

    def show(self):

        if self not in Window.active_dialogs:
            Window.active_dialogs.append(self)

        if self.parent and not self.parent.is_visible():
            # In case parent window appears a few frames later, ensure dialog is modal
            GLib.idle_add(self._finish_show, priority=GLib.PRIORITY_LOW)
            return

        # Show the dialog
        self._finish_show()

    def close(self):
        self.widget.close()


class OptionDialog(MessageDialog):

    def __init__(self, parent, title, message, callback, callback_data=None, long_message=None, option_label="",
                 option_value=False, buttons=None, destructive_response_id=None):

        if not buttons:
            buttons = [
                ("cancel", _("_No")),
                ("ok", _("_Yes"))
            ]

        super().__init__(parent=parent, title=title, message=message, long_message=long_message,
                         callback=callback, callback_data=callback_data, buttons=buttons,
                         destructive_response_id=destructive_response_id)

        self.toggle = None

        if option_label:
            self.toggle = self._add_option_toggle(option_label, option_value)

    def _add_option_toggle(self, option_label, option_value):

        toggle = Gtk.CheckButton(label=option_label, active=option_value, receives_default=True, visible=True)

        if option_label:
            if GTK_API_VERSION >= 4:
                self.container.append(toggle)  # pylint: disable=no-member
            else:
                self.container.add(toggle)     # pylint: disable=no-member

        self.container.set_visible(True)
        return toggle

    def get_option_value(self):

        if self.toggle is not None:
            return self.toggle.get_active()

        return None


class EntryDialog(OptionDialog):

    def __init__(self, parent, title, callback, message=None, callback_data=None, default="", use_second_entry=False,
                 second_default="", option_label="", option_value=False, action_button_label=_("_OK"), visibility=True,
                 droplist=None, second_droplist=None):

        super().__init__(parent=parent, title=title, message=message, callback=callback,
                         callback_data=callback_data, option_label=option_label,
                         option_value=option_value,
                         buttons=[
                             ("cancel", _("_Cancel")),
                             ("ok", action_button_label)])

        self.entry_container = None
        self.entry = self._add_entry_combobox(default, visibility, droplist, activates_default=not use_second_entry)
        self.second_entry = None

        if use_second_entry:
            self.second_entry = self._add_entry_combobox(
                second_default, visibility, second_droplist, activates_default=False)

    def _add_combobox(self, items, visibility=True):

        combobox = ComboBox(container=self.entry_container, has_entry=True)
        entry = combobox.entry
        entry.set_width_chars(45)
        entry.set_visibility(visibility)

        for item in items:
            combobox.append(item)

        self.container.set_visible(True)
        return entry

    def _add_entry(self, visibility=True):

        if GTK_API_VERSION >= 4 and not visibility:
            entry = Gtk.PasswordEntry(show_peek_icon=True, width_chars=50, visible=True)
        else:
            entry = Gtk.Entry(visibility=visibility, width_chars=50, visible=True)

        if GTK_API_VERSION >= 4:
            self.entry_container.append(entry)  # pylint: disable=no-member
        else:
            self.entry_container.add(entry)     # pylint: disable=no-member

        self.container.set_visible(True)
        return entry

    def _add_entry_combobox(self, default, visibility, droplist=None, activates_default=True):

        if self.entry_container is None:
            self.entry_container = Gtk.Box(hexpand=True, orientation=Gtk.Orientation.VERTICAL, spacing=12, visible=True)

            if GTK_API_VERSION >= 4:
                self.container.prepend(self.entry_container)                   # pylint: disable=no-member
            else:
                self.container.pack_start(self.entry_container, expand=False,  # pylint: disable=no-member
                                          fill=False, padding=0)

        if droplist:
            entry = self._add_combobox(droplist, visibility)
        else:
            entry = self._add_entry(visibility)

        entry.set_property("activates-default", activates_default)
        entry.set_text(default)

        return entry

    def get_entry_value(self):
        return self.entry.get_text()

    def get_second_entry_value(self):

        if self.second_entry is not None:
            return self.second_entry.get_text()

        return None
