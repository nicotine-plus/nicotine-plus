# COPYRIGHT (C) 2020-2024 Nicotine+ Contributors
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
import sys

from gi.repository import Gdk
from gi.repository import GLib
from gi.repository import Gtk

from pynicotine.config import config
from pynicotine.gtkgui.application import GTK_API_VERSION
from pynicotine.gtkgui.widgets.accelerator import Accelerator
from pynicotine.gtkgui.widgets.combobox import ComboBox
from pynicotine.gtkgui.widgets.textview import TextView
from pynicotine.gtkgui.widgets.theme import add_css_class
from pynicotine.gtkgui.widgets.window import Window


class Dialog(Window):

    def __init__(self, widget=None, parent=None, content_box=None, buttons_start=(), buttons_end=(),
                 default_button=None, show_callback=None, close_callback=None, title="", width=0, height=0,
                 modal=True, show_title=True, show_title_buttons=True):

        self.parent = parent
        self.modal = modal
        self.default_width = width
        self.default_height = height
        self.default_button = default_button

        self.show_callback = show_callback
        self.close_callback = close_callback

        if widget:
            super().__init__(widget=widget)
            self._set_dialog_properties()
            return

        container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, vexpand=True, visible=True)
        widget = Gtk.Window(
            destroy_with_parent=True,
            default_width=width,
            default_height=height,
            child=container
        )
        super().__init__(widget)
        Accelerator("Escape", widget, self.close)

        if GTK_API_VERSION == 3:
            if os.environ.get("GDK_BACKEND") == "broadway":
                # Workaround for dialogs being centered at (0,0) coords on startup
                position = Gtk.WindowPosition.CENTER
            else:
                position = Gtk.WindowPosition.CENTER_ON_PARENT

            widget.set_position(position)                    # pylint: disable=no-member
            widget.set_type_hint(Gdk.WindowTypeHint.DIALOG)  # pylint: disable=no-member

        if content_box:
            content_box.set_vexpand(True)

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

        self._unselect_focus_label()
        self._focus_default_button()

        if self.show_callback is not None:
            self.show_callback(self)

    def _on_close_request(self, *_args):

        if self not in Window.active_dialogs:
            return False

        Window.active_dialogs.remove(self)

        if self.close_callback is not None:
            self.close_callback(self)

        # Hide the dialog
        self.widget.set_visible(False)

        # "Soft-delete" the dialog. This is necessary to prevent the dialog from
        # appearing in window peek on Windows
        if sys.platform == "win32" and self.widget.get_titlebar() is None:
            self.widget.unrealize()

        return True

    def _set_dialog_properties(self):

        if GTK_API_VERSION >= 4:
            self.widget.connect("close-request", self._on_close_request)
        else:
            self.widget.connect("delete-event", self._on_close_request)

        self.widget.connect("show", self._on_show)

        # Make all dialogs resizable to fix positioning issue.
        # Workaround for https://gitlab.gnome.org/GNOME/mutter/-/issues/3099
        self.widget.set_resizable(True)

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

    def _unselect_focus_label(self):
        """Unselect default focus widget if it's a label."""

        focus_widget = self.widget.get_focus()

        if isinstance(focus_widget, Gtk.Label):
            focus_widget.select_region(start_offset=0, end_offset=0)
            self.widget.set_focus(None)

    def _finish_present(self, present_callback):
        self.widget.set_modal(self.modal and self.parent.is_visible())
        present_callback()

    def set_show_title_buttons(self, visible):

        header_bar = self.widget.get_titlebar()

        if header_bar is None:
            return

        if GTK_API_VERSION >= 4:
            header_bar.set_show_title_buttons(visible)    # pylint: disable=no-member
        else:
            header_bar.set_show_close_button(visible)     # pylint: disable=no-member

    def present(self):

        if self not in Window.active_dialogs:
            Window.active_dialogs.append(self)

        # Shrink the dialog if it's larger than the main window
        self._resize_dialog()

        # Show dialog after slight delay to work around issue where dialogs don't
        # close if another one is shown right after
        GLib.idle_add(self._finish_present, super().present, priority=GLib.PRIORITY_HIGH_IDLE)


class MessageDialog(Window):

    if GTK_API_VERSION == 3:
        class InternalMessageDialog(Gtk.Window):
            __gtype_name__ = "MessageDialog"

            def __init__(self, *args, **kwargs):
                self.set_css_name("messagedialog")
                super().__init__(*args, **kwargs)

    def __init__(self, parent, title, message, callback=None, callback_data=None, long_message=None,
                 buttons=None, destructive_response_id=None, selectable=False):

        # Prioritize non-message dialogs as parent
        for active_dialog in reversed(Window.active_dialogs):
            if isinstance(active_dialog, Dialog):
                parent = active_dialog
                break

        self.parent = parent
        self.callback = callback
        self.callback_data = callback_data
        self.destructive_response_id = destructive_response_id
        self.container = Gtk.Box(hexpand=True, orientation=Gtk.Orientation.VERTICAL, spacing=6, visible=False)
        self.message_label = None
        self.default_focus_widget = None

        if not buttons:
            buttons = [("cancel", _("Close"))]

        widget = self._create_dialog(title, message, buttons, selectable)
        super().__init__(widget=widget)

        self._add_long_message(long_message)

    def _create_dialog(self, title, message, buttons, selectable):

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, visible=True)
        add_css_class(vbox, "dialog-vbox")

        if GTK_API_VERSION >= 4:
            window_class = Gtk.Window
            window_child = Gtk.WindowHandle(child=vbox, visible=True)
        else:
            # Need to subclass Gtk.Window in GTK 3 to set CSS name
            window_class = self.InternalMessageDialog
            window_child = vbox

        widget = window_class(
            destroy_with_parent=True,
            transient_for=self.parent.widget if self.parent else None,
            title=title,
            resizable=False,
            child=window_child
        )

        Accelerator("Escape", widget, self.close)

        for css_class in ("dialog", "message", "messagedialog"):
            add_css_class(widget, css_class)

        header_bar = Gtk.Box(height_request=16, visible=True)
        box = Gtk.Box(margin_start=24, margin_end=24, visible=True)
        message_area = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10, hexpand=True, visible=True)
        action_box = Gtk.Box(visible=True)
        action_area = Gtk.Box(hexpand=True, homogeneous=True, visible=True)

        title_label = Gtk.Label(
            halign=Gtk.Align.CENTER, label=title, valign=Gtk.Align.START, wrap=True, max_width_chars=60, visible=True
        )
        self.message_label = Gtk.Label(
            margin_bottom=2, halign=Gtk.Align.CENTER, label=message, valign=Gtk.Align.START, vexpand=True, wrap=True,
            max_width_chars=60, selectable=selectable, visible=True
        )

        add_css_class(title_label, "title-2")
        add_css_class(action_box, "dialog-action-box")
        add_css_class(action_area, "dialog-action-area")

        if GTK_API_VERSION >= 4:
            header_bar_handle = Gtk.WindowHandle(child=header_bar, visible=True)
            widget.set_titlebar(header_bar_handle)
            widget.connect("close-request", self._on_close_request)

            internal_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, visible=True)

            vbox.append(internal_vbox)                                # pylint: disable=no-member
            vbox.append(action_box)                                   # pylint: disable=no-member
            internal_vbox.append(box)                                 # pylint: disable=no-member
            box.append(message_area)                                  # pylint: disable=no-member

            message_area.append(title_label)                          # pylint: disable=no-member
            message_area.append(self.message_label)                   # pylint: disable=no-member
            message_area.append(self.container)                       # pylint: disable=no-member

            action_box.append(action_area)                            # pylint: disable=no-member
        else:
            widget.set_position(Gtk.WindowPosition.CENTER_ON_PARENT)  # pylint: disable=no-member
            widget.set_skip_taskbar_hint(True)                        # pylint: disable=no-member
            widget.set_type_hint(Gdk.WindowTypeHint.DIALOG)           # pylint: disable=no-member
            widget.set_titlebar(header_bar)
            widget.connect("delete-event", self._on_close_request)

            vbox.set_spacing(20)
            vbox.add(box)                                             # pylint: disable=no-member
            vbox.add(action_box)                                      # pylint: disable=no-member
            box.add(message_area)                                     # pylint: disable=no-member

            message_area.add(title_label)                             # pylint: disable=no-member
            message_area.add(self.message_label)                      # pylint: disable=no-member
            message_area.add(self.container)                          # pylint: disable=no-member

            action_box.add(action_area)                               # pylint: disable=no-member

        for response_type, button_label in buttons:
            button = Gtk.Button(use_underline=True, hexpand=True, visible=True)
            button.connect("clicked", self._on_button_pressed, response_type)

            if GTK_API_VERSION >= 4:
                action_area.append(button)  # pylint: disable=no-member
            else:
                action_area.add(button)     # pylint: disable=no-member

            if response_type == self.destructive_response_id:
                add_css_class(button, "destructive-action")

            elif response_type in {"cancel", "ok"}:
                if GTK_API_VERSION >= 4:
                    widget.set_default_widget(button)  # pylint: disable=no-member
                else:
                    button.set_can_default(True)       # pylint: disable=no-member
                    widget.set_default(button)         # pylint: disable=no-member

                if response_type == "ok":
                    add_css_class(button, "suggested-action")

                self.message_label.set_mnemonic_widget(button)
                self.default_focus_widget = button

            # Set mnemonic widget before button label in order for screen reader to
            # read both labels
            button.set_label(button_label)

        return widget

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

        textview = self.default_focus_widget = TextView(scrolled_window, editable=False)
        textview.append_line(text)

        self.container.set_visible(True)

    def _on_close_request(self, *_args):

        if self in Window.active_dialogs:
            Window.active_dialogs.remove(self)

        self.destroy()

    def _on_button_pressed(self, _button, response_type):

        if self.callback and response_type != "cancel":
            self.callback(self, response_type, self.callback_data)

        # "Run in Background" response already closes all dialogs
        if response_type != "run_background":
            self.close()

    def _finish_present(self, present_callback):
        self.widget.set_modal(self.parent and self.parent.is_visible())
        present_callback()

    def present(self):

        if self not in Window.active_dialogs:
            Window.active_dialogs.append(self)

        if self.default_focus_widget:
            self.default_focus_widget.grab_focus()

        # Show dialog after slight delay to work around issue where dialogs don't
        # close if another one is shown right after
        GLib.idle_add(self._finish_present, super().present, priority=GLib.PRIORITY_HIGH_IDLE)


class OptionDialog(MessageDialog):

    def __init__(self, *args, option_label="", option_value=False, buttons=None, **kwargs):

        if not buttons:
            buttons = [
                ("cancel", _("_No")),
                ("ok", _("_Yes"))
            ]

        super().__init__(*args, buttons=buttons, **kwargs)

        self.toggle = None

        if option_label:
            self.toggle = self.default_focus_widget = self._add_option_toggle(option_label, option_value)

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

    def __init__(self, *args, default="", use_second_entry=False, second_entry_editable=True,
                 second_default="", action_button_label=_("_OK"), droplist=None, second_droplist=None,
                 visibility=True, show_emoji_icon=False, **kwargs):

        super().__init__(*args, buttons=[
            ("cancel", _("_Cancel")),
            ("ok", action_button_label)
        ], **kwargs)

        self.entry_container = None
        self.entry_combobox = None
        self.second_entry_combobox = None

        self.entry_combobox = self.default_focus_widget = self._add_entry_combobox(
            default, activates_default=not use_second_entry, visibility=visibility,
            show_emoji_icon=show_emoji_icon, droplist=droplist
        )

        if use_second_entry:
            self.second_entry_combobox = self._add_entry_combobox(
                second_default, has_entry=second_entry_editable, activates_default=False, visibility=visibility,
                show_emoji_icon=show_emoji_icon, droplist=second_droplist
            )

    def _add_combobox(self, items, has_entry=True, visibility=True, activates_default=True):

        combobox = ComboBox(container=self.entry_container, has_entry=has_entry, items=items)

        if has_entry:
            entry = combobox.entry
            entry.set_activates_default(activates_default)
            entry.set_width_chars(45)
            entry.set_visibility(visibility)

        if self.entry_combobox is None:
            self.message_label.set_mnemonic_widget(entry if has_entry else combobox.widget)

        self.container.set_visible(True)
        return combobox

    def _add_entry(self, visibility=True, show_emoji_icon=False, activates_default=True):

        if GTK_API_VERSION >= 4 and not visibility:
            entry = Gtk.PasswordEntry(
                activates_default=activates_default, show_peek_icon=True,
                width_chars=50, visible=True
            )
            text_widget = next(iter(entry))
            text_widget.set_truncate_multiline(True)
        else:
            entry = Gtk.Entry(
                activates_default=activates_default, visibility=visibility, show_emoji_icon=show_emoji_icon,
                truncate_multiline=(not visibility), width_chars=50, visible=True)

        if GTK_API_VERSION >= 4:
            self.entry_container.append(entry)  # pylint: disable=no-member
        else:
            self.entry_container.add(entry)     # pylint: disable=no-member

        if self.entry_combobox is None:
            self.message_label.set_mnemonic_widget(entry)

        self.container.set_visible(True)
        return entry

    def _add_entry_combobox(self, default, activates_default=True, has_entry=True, visibility=True,
                            show_emoji_icon=False, droplist=None):

        if self.entry_container is None:
            self.entry_container = Gtk.Box(hexpand=True, orientation=Gtk.Orientation.VERTICAL, spacing=12, visible=True)

            if GTK_API_VERSION >= 4:
                self.container.prepend(self.entry_container)                    # pylint: disable=no-member
            else:
                self.container.add(self.entry_container)                        # pylint: disable=no-member
                self.container.reorder_child(self.entry_container, position=0)  # pylint: disable=no-member

        if not has_entry or droplist:
            entry_combobox = self._add_combobox(
                droplist, has_entry=has_entry, activates_default=activates_default, visibility=visibility)
        else:
            entry_combobox = self._add_entry(
                activates_default=activates_default, visibility=visibility, show_emoji_icon=show_emoji_icon)

        entry_combobox.set_text(default)
        return entry_combobox

    def get_entry_value(self):
        return self.entry_combobox.get_text()

    def get_second_entry_value(self):

        if self.second_entry_combobox is not None:
            return self.second_entry_combobox.get_text()

        return None
