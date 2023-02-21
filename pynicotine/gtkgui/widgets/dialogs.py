# COPYRIGHT (C) 2020-2022 Nicotine+ Contributors
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
from pynicotine.core import core
from pynicotine.gtkgui.application import GTK_API_VERSION
from pynicotine.gtkgui.widgets.accelerator import Accelerator
from pynicotine.gtkgui.widgets.filechooser import FileChooserButton
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
                 message_type=Gtk.MessageType.OTHER, buttons=None, width=-1):

        # Prioritize modal non-message dialogs as parent
        for active_dialog in reversed(Window.active_dialogs):
            if isinstance(active_dialog, Dialog) and active_dialog.modal:
                parent = active_dialog
                break

        widget = Gtk.MessageDialog(
            transient_for=parent.widget if parent else None, destroy_with_parent=True, message_type=message_type,
            default_width=width, text=title, secondary_text=message
        )
        super().__init__(widget=widget)
        widget.connect("response", self.on_response, callback, callback_data)

        if not buttons:
            buttons = [(_("Close"), Gtk.ResponseType.CLOSE)]

        for button_label, response_type in buttons:
            widget.add_button(button_label, response_type)

        self.parent = parent
        self.container = self.widget.get_message_area()

        self._make_message_selectable()
        self._add_long_message(long_message)

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

    def _add_option_toggle(self, option_label, option_value):

        toggle = Gtk.CheckButton(label=option_label, active=option_value, visible=bool(option_label))

        if option_label:
            if GTK_API_VERSION >= 4:
                self.container.append(toggle)
            else:
                self.container.add(toggle)

        return toggle

    def on_response(self, _widget, response_id, callback, callback_data):

        if self not in Window.active_dialogs:
            return

        Window.active_dialogs.remove(self)

        if callback and response_id not in (Gtk.ResponseType.CANCEL, Gtk.ResponseType.CLOSE,
                                            Gtk.ResponseType.DELETE_EVENT):
            callback(self, response_id, callback_data)

        self.widget.close()

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


class EntryDialog(MessageDialog):

    def __init__(self, parent, title, callback, message=None, callback_data=None, default="", use_second_entry=False,
                 second_default="", option_label="", option_value=False, action_button_label=_("_OK"), visibility=True,
                 droplist=None, second_droplist=None):

        super().__init__(parent=parent, title=title, message=message, message_type=Gtk.MessageType.OTHER,
                         callback=callback, callback_data=callback_data, width=500,
                         buttons=[
                             (_("_Cancel"), Gtk.ResponseType.CANCEL),
                             (action_button_label, Gtk.ResponseType.OK)])

        self.toggle = self._add_option_toggle(option_label, option_value)
        self.entry = self._add_entry_combobox(default, visibility, droplist)
        self.second_entry = None

        if use_second_entry:
            self.second_entry = self._add_entry_combobox(second_default, visibility, second_droplist)

    def _add_combobox(self, items, visibility=True):

        dropdown = Gtk.ComboBoxText(has_entry=True, visible=True)
        entry = dropdown.get_child()
        entry.set_visibility(visibility)

        for item in items:
            dropdown.append_text(item)

        if GTK_API_VERSION >= 4:
            self.container.append(dropdown)
        else:
            self.container.add(dropdown)

        return entry

    def _add_entry(self, visibility=True):

        if GTK_API_VERSION >= 4 and not visibility:
            entry = Gtk.PasswordEntry(show_peek_icon=True, visible=True)
        else:
            entry = Gtk.Entry(visibility=visibility, visible=True)

        if GTK_API_VERSION >= 4:
            self.container.append(entry)
        else:
            self.container.add(entry)

        return entry

    def _add_entry_combobox(self, default, visibility, droplist=None):

        if droplist:
            entry = self._add_combobox(droplist, visibility)
        else:
            entry = self._add_entry(visibility)

        entry.connect("activate", self.on_activate_entry)
        entry.set_text(default)

        return entry

    def on_activate_entry(self, *_args):
        self.widget.response(Gtk.ResponseType.OK)

    def get_entry_value(self):
        return self.entry.get_text()

    def get_second_entry_value(self):
        return self.second_entry.get_text()

    def get_option_value(self):
        return self.toggle.get_active()


class OptionDialog(MessageDialog):

    def __init__(self, parent, title, message, callback, callback_data=None, long_message=None, option_label="",
                 option_value=False, first_button=_("_No"), second_button=_("_Yes"), third_button=""):

        buttons = []

        if first_button:
            buttons.append((first_button, 1))

        if second_button:
            buttons.append((second_button, 2))

        if third_button:
            buttons.append((third_button, 3))

        super().__init__(parent=parent, title=title, message=message, long_message=long_message,
                         message_type=Gtk.MessageType.OTHER, callback=callback, callback_data=callback_data,
                         buttons=buttons)

        self.toggle = self._add_option_toggle(option_label, option_value)

    def get_option_value(self):
        return self.toggle.get_active()


""" Plugin Settings Dialog """


class PluginSettingsDialog(Dialog):

    def __init__(self, application, plugin_id, plugin_settings):

        self.application = application
        self.plugin_id = plugin_id
        self.plugin_settings = plugin_settings
        self.option_widgets = {}

        plugin_name = core.pluginhandler.get_plugin_info(plugin_id).get("Name", plugin_id)

        cancel_button = Gtk.Button(label=_("_Cancel"), use_underline=True, visible=True)
        cancel_button.connect("clicked", self.on_cancel)

        ok_button = Gtk.Button(label=_("_OK"), use_underline=True, visible=True)
        ok_button.connect("clicked", self.on_ok)
        add_css_class(ok_button, "suggested-action")

        self.primary_container = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL, width_request=340, visible=True,
            margin_top=14, margin_bottom=14, margin_start=18, margin_end=18, spacing=12
        )
        scrolled_window = Gtk.ScrolledWindow(
            child=self.primary_container, hexpand=True, vexpand=True, min_content_height=300,
            hscrollbar_policy=Gtk.PolicyType.NEVER, vscrollbar_policy=Gtk.PolicyType.AUTOMATIC, visible=True
        )

        super().__init__(
            parent=application.preferences,
            content_box=scrolled_window,
            buttons_start=(cancel_button,),
            buttons_end=(ok_button,),
            default_button=ok_button,
            title=_("%s Settings") % plugin_name,
            width=600,
            height=425,
            close_destroy=True,
            show_title_buttons=False
        )

        self._add_options()

    @staticmethod
    def _generate_label(text):
        return Gtk.Label(label=text, use_markup=True, hexpand=True, wrap=True, xalign=0, visible=bool(text))

    def _generate_widget_container(self, description, child_widget, homogeneous=False,
                                   orientation=Gtk.Orientation.HORIZONTAL):

        container = Gtk.Box(homogeneous=homogeneous, orientation=orientation, spacing=12, visible=True)
        label = self._generate_label(description)

        if GTK_API_VERSION >= 4:
            container.append(label)                   # pylint: disable=no-member
            container.append(child_widget)            # pylint: disable=no-member
            self.primary_container.append(container)  # pylint: disable=no-member
        else:
            container.add(label)                   # pylint: disable=no-member
            container.add(child_widget)            # pylint: disable=no-member
            self.primary_container.add(container)  # pylint: disable=no-member

        return label

    def _add_numerical_option(self, option_name, option_value, description, minimum, maximum, stepsize, decimals):

        self.option_widgets[option_name] = button = Gtk.SpinButton(
            adjustment=Gtk.Adjustment(
                value=0, lower=minimum, upper=maximum, step_increment=stepsize, page_increment=10,
                page_size=0
            ),
            climb_rate=1, digits=decimals, valign=Gtk.Align.CENTER, visible=True
        )

        label = self._generate_widget_container(description, button)
        label.set_mnemonic_widget(button)
        self.application.preferences.set_widget(button, option_value)

    def _add_boolean_option(self, option_name, option_value, description):

        self.option_widgets[option_name] = button = Gtk.CheckButton(label=description, receives_default=True,
                                                                    visible=True)
        self._generate_widget_container("", button)
        self.application.preferences.set_widget(button, option_value)

        if GTK_API_VERSION >= 4:
            button.get_last_child().set_wrap(True)  # pylint: disable=no-member
        else:
            button.get_child().set_line_wrap(True)  # pylint: disable=no-member

    def _add_radio_option(self, option_name, option_value, description, items):

        box = Gtk.Box(spacing=6, orientation=Gtk.Orientation.VERTICAL, visible=True)
        label = self._generate_widget_container(description, box)

        last_radio = None
        group_radios = []

        for option_label in items:
            widget_class = Gtk.CheckButton if GTK_API_VERSION >= 4 else Gtk.RadioButton
            radio = widget_class(group=last_radio, label=option_label, receives_default=True, visible=True)

            if not last_radio:
                self.option_widgets[option_name] = radio

            last_radio = radio
            group_radios.append(radio)

            if GTK_API_VERSION >= 4:
                box.append(radio)  # pylint: disable=no-member
            else:
                box.add(radio)     # pylint: disable=no-member

        label.set_mnemonic_widget(self.option_widgets[option_name])
        self.option_widgets[option_name].group_radios = group_radios
        self.application.preferences.set_widget(self.option_widgets[option_name], option_value)

    def _add_dropdown_option(self, option_name, option_value, description, items):

        self.option_widgets[option_name] = combobox = Gtk.ComboBoxText(valign=Gtk.Align.CENTER, visible=True)
        label = self._generate_widget_container(description, combobox, homogeneous=True)
        label.set_mnemonic_widget(combobox)

        for text_label in items:
            combobox.append(id=text_label, text=text_label)

        self.application.preferences.set_widget(combobox, option_value)

    def _add_entry_option(self, option_name, option_value, description):

        self.option_widgets[option_name] = entry = Gtk.Entry(hexpand=True, valign=Gtk.Align.CENTER,
                                                             visible=True)
        label = self._generate_widget_container(description, entry, homogeneous=True)
        label.set_mnemonic_widget(entry)

        self.application.preferences.set_widget(entry, option_value)

    def _add_textview_option(self, option_name, option_value, description):

        box = Gtk.Box(visible=True)
        scrolled_window = Gtk.ScrolledWindow(hexpand=True, vexpand=True, min_content_height=125,
                                             visible=True)
        frame_container = Gtk.Frame(child=box, visible=True)

        if GTK_API_VERSION >= 4:
            box.append(scrolled_window)  # pylint: disable=no-member
        else:
            box.add(scrolled_window)     # pylint: disable=no-member

        self.option_widgets[option_name] = textview = TextView(scrolled_window)
        label = self._generate_widget_container(description, frame_container, orientation=Gtk.Orientation.VERTICAL)
        label.set_mnemonic_widget(textview.widget)
        self.application.preferences.set_widget(textview, option_value)

    def _add_list_option(self, option_name, option_value, description):

        scrolled_window = Gtk.ScrolledWindow(
            hexpand=True, vexpand=True, min_content_height=125,
            hscrollbar_policy=Gtk.PolicyType.AUTOMATIC, vscrollbar_policy=Gtk.PolicyType.AUTOMATIC, visible=True
        )
        frame_container = Gtk.Frame(child=scrolled_window, visible=True)
        container = Gtk.Box(spacing=6, visible=True)

        from pynicotine.gtkgui.widgets.treeview import TreeView
        self.option_widgets[option_name] = treeview = TreeView(
            self.application.window, parent=scrolled_window,
            columns={
                "description": {
                    "column_type": "text",
                    "title": description
                }
            }
        )
        self.application.preferences.set_widget(treeview, option_value)

        box = Gtk.Box(spacing=6, visible=True)

        add_button = Gtk.Button(label=_("Add…"), visible=True)
        add_button.connect("clicked", self.on_add, treeview, description)

        edit_button = Gtk.Button(label=_("Edit…"), visible=True)
        edit_button.connect("clicked", self.on_edit, treeview, description)

        remove_button = Gtk.Button(label=_("Remove"), visible=True)
        remove_button.connect("clicked", self.on_remove, treeview)

        if GTK_API_VERSION >= 4:
            box.append(add_button)                    # pylint: disable=no-member
            box.append(edit_button)                   # pylint: disable=no-member
            box.append(remove_button)                 # pylint: disable=no-member

            self.primary_container.append(container)  # pylint: disable=no-member
            self.primary_container.append(box)        # pylint: disable=no-member

            container.append(frame_container)         # pylint: disable=no-member
        else:
            box.add(add_button)                    # pylint: disable=no-member
            box.add(edit_button)                   # pylint: disable=no-member
            box.add(remove_button)                 # pylint: disable=no-member

            self.primary_container.add(container)  # pylint: disable=no-member
            self.primary_container.add(box)        # pylint: disable=no-member

            container.add(frame_container)         # pylint: disable=no-member

    def _add_file_option(self, option_name, option_value, description, file_chooser_type):

        button_widget = Gtk.Button(hexpand=True, valign=Gtk.Align.CENTER, visible=True)
        label = self._generate_widget_container(description, button_widget, homogeneous=True)

        self.option_widgets[option_name] = FileChooserButton(button_widget, self.widget, file_chooser_type)
        label.set_mnemonic_widget(button_widget)

        self.application.preferences.set_widget(self.option_widgets[option_name], option_value)

    def _add_options(self):

        for option_name, data in self.plugin_settings.items():
            option_type = data.get("type")

            if not option_type:
                continue

            description = data.get("description", "")
            option_value = config.sections["plugins"][self.plugin_id.lower()][option_name]

            if option_type in ("integer", "int", "float"):
                self._add_numerical_option(
                    option_name, option_value, description, minimum=data.get("minimum", 0),
                    maximum=data.get("maximum", 99999), stepsize=data.get("stepsize", 1),
                    decimals=(0 if option_type in ("integer", "int") else 2)
                )

            elif option_type in ("bool",):
                self._add_boolean_option(option_name, option_value, description)

            elif option_type in ("radio",):
                self._add_radio_option(
                    option_name, option_value, description, items=data.get("options", []))

            elif option_type in ("dropdown",):
                self._add_dropdown_option(
                    option_name, option_value, description, items=data.get("options", []))

            elif option_type in ("str", "string"):
                self._add_entry_option(option_name, option_value, description)

            elif option_type in ("textview",):
                self._add_textview_option(option_name, option_value, description)

            elif option_type in ("list string",):
                self._add_list_option(option_name, option_value, description)

            elif option_type in ("file",):
                self._add_file_option(
                    option_name, option_value, description, file_chooser_type=data.get("chooser"))

    def on_add_response(self, window, _response_id, treeview):

        value = window.get_entry_value()

        if not value:
            return

        treeview.add_row([value])

    def on_add(self, _widget, treeview, description):

        EntryDialog(
            parent=self,
            title=description,
            callback=self.on_add_response,
            callback_data=treeview
        ).show()

    def on_edit_response(self, window, _response_id, data):

        value = window.get_entry_value()

        if not value:
            return

        treeview, iterator, column_id = data
        treeview.set_row_value(iterator, column_id, value)

    def on_edit(self, _widget, treeview, description):

        for iterator in treeview.get_selected_rows():
            value = treeview.get_row_value(iterator, description)

            EntryDialog(
                parent=self,
                title=description,
                callback=self.on_edit_response,
                callback_data=(treeview, iterator, description),
                default=value
            ).show()
            return

    def on_remove(self, _widget, treeview):
        for iterator in reversed(treeview.get_selected_rows()):
            treeview.remove_row(iterator)

    def on_cancel(self, *_args):
        self.close()

    def on_ok(self, *_args):

        for name in self.plugin_settings:
            value = self.application.preferences.get_widget_data(self.option_widgets[name])

            if value is not None:
                config.sections["plugins"][self.plugin_id.lower()][name] = value

        core.pluginhandler.plugin_settings(
            self.plugin_id, core.pluginhandler.enabled_plugins[self.plugin_id])

        self.close()
