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
from gi.repository import Gtk

from pynicotine.config import config
from pynicotine.gtkgui.application import GTK_API_VERSION
from pynicotine.gtkgui.widgets.filechooser import FileChooserButton

""" Dialogs """


def generic_dialog(parent=None, content_box=None, buttons=None, default_response=None, quit_callback=None,
                   title="Dialog", width=400, height=400, modal=True):

    dialog = Gtk.Dialog(
        use_header_bar=config.sections["ui"]["header_bar"],
        title=title,
        default_width=width,
        default_height=height
    )
    dialog.get_style_context().add_class("generic-dialog")

    if content_box:
        if GTK_API_VERSION >= 4:
            dialog.get_content_area().append(content_box)
        else:
            dialog.get_content_area().add(content_box)

    if buttons:
        for button, response_type in buttons:
            if GTK_API_VERSION == 3 and response_type == default_response:
                button.set_can_default(True)

            dialog.add_action_widget(button, response_type)

    if default_response:
        dialog.set_default_response(default_response)

    set_dialog_properties(dialog, parent, quit_callback, modal)
    return dialog


def set_dialog_properties(dialog, parent, quit_callback=None, modal=True):

    if GTK_API_VERSION >= 4:
        if quit_callback:
            dialog.connect("close-request", quit_callback)
    else:
        dialog.set_property("window-position", Gtk.WindowPosition.CENTER_ON_PARENT)
        dialog.set_type_hint(Gdk.WindowTypeHint.DIALOG)

        if quit_callback:
            dialog.connect("delete-event", quit_callback)

        if isinstance(dialog, Gtk.Dialog):
            content_area = dialog.get_content_area()
            content_area.set_border_width(0)

    dialog.set_modal(modal)
    dialog.set_transient_for(parent)


def dialog_show(dialog):

    parent = dialog.get_transient_for()

    # Shrink the dialog if it's larger than the main window
    if GTK_API_VERSION >= 4:
        main_window_width = parent.get_width()
        main_window_height = parent.get_height()
        dialog_width, dialog_height = dialog.get_default_size()
    else:
        main_window_width, main_window_height = parent.get_size()
        dialog_width, dialog_height = dialog.get_size()

    if dialog_width > main_window_width:
        dialog_width = main_window_width - 30

    if dialog_height > main_window_height:
        dialog_height = main_window_height - 30

    if dialog_width > 0 and dialog_height > 0:
        if GTK_API_VERSION >= 4:
            dialog.set_default_size(dialog_width, dialog_height)
        else:
            dialog.resize(dialog_width, dialog_height)

    # Show the dialog
    dialog.present()

    if GTK_API_VERSION == 3:
        dialog.get_window().set_functions(
            Gdk.WMFunction.RESIZE | Gdk.WMFunction.MOVE | Gdk.WMFunction.CLOSE
        )


def dialog_hide(dialog):

    # Hide the dialog
    dialog.hide()

    # "Soft-delete" the dialog. This is necessary to prevent the dialog from
    # appearing in window peek on Windows
    dialog.unrealize()


""" Message Dialogs """


class MessageDialog:

    def __init__(self, parent, title, message, callback=None, callback_data=None,
                 message_type=Gtk.MessageType.OTHER, buttons=None, width=-1):

        self.dialog = Gtk.MessageDialog(
            transient_for=parent, destroy_with_parent=True, modal=True,
            message_type=message_type, default_width=width,
            text=title, secondary_text=message
        )
        self.container = self.dialog.get_message_area()
        self.dialog.connect("response", self.on_response, callback, callback_data)

        if not buttons:
            buttons = [(_("Close"), Gtk.ResponseType.CLOSE)]

        for button_label, response_type in buttons:
            self.dialog.add_button(button_label, response_type)

        if GTK_API_VERSION >= 4:
            label = self.container.get_last_child()
        else:
            label = self.container.get_children()[-1]

        label.set_selectable(True)

    def on_response(self, dialog, response_id, callback, callback_data):

        if callback and response_id not in (Gtk.ResponseType.CANCEL, Gtk.ResponseType.CLOSE,
                                            Gtk.ResponseType.DELETE_EVENT):
            callback(self, response_id, callback_data)

        dialog.destroy()

    def show(self):
        self.dialog.present()


class EntryDialog(MessageDialog):

    def __init__(self, parent, title, message, callback, callback_data=None, default="",
                 option_label="", option_value=False, visibility=True, droplist=None):

        super().__init__(parent=parent, title=title, message=message, message_type=Gtk.MessageType.OTHER,
                         callback=callback, callback_data=callback_data, width=500,
                         buttons=[
                             (_("Cancel"), Gtk.ResponseType.CANCEL),
                             (_("OK"), Gtk.ResponseType.OK)])

        if droplist:
            dropdown = Gtk.ComboBoxText(has_entry=True, visible=True)
            self.entry = dropdown.get_child()
            self.entry.set_visibility(visibility)

            for i in droplist:
                dropdown.append_text(i)

            if GTK_API_VERSION >= 4:
                self.container.append(dropdown)
            else:
                self.container.add(dropdown)
        else:
            if GTK_API_VERSION >= 4 and not visibility:
                self.entry = Gtk.PasswordEntry(show_peek_icon=True, visible=True)
            else:
                self.entry = Gtk.Entry(visibility=visibility, visible=True)

            if GTK_API_VERSION >= 4:
                self.container.append(self.entry)
            else:
                self.container.add(self.entry)

        self.entry.connect("activate", self.on_activate_entry)
        self.entry.set_text(default)

        self.option = Gtk.CheckButton(label=option_label, active=option_value, visible=bool(option_label))

        if option_label:
            if GTK_API_VERSION >= 4:
                self.container.append(self.option)
            else:
                self.container.add(self.option)

    def on_activate_entry(self, *_args):
        self.dialog.response(Gtk.ResponseType.OK)

    def get_response_value(self):
        return self.entry.get_text()

    def get_second_response_value(self):
        return self.option.get_active()


class OptionDialog(MessageDialog):

    def __init__(self, parent, title, message, callback, callback_data=None, option_label="", option_value=False,
                 first_button=_("_No"), second_button=_("_Yes"), third_button=""):

        buttons = []

        if first_button:
            buttons.append((first_button, 1))

        if second_button:
            buttons.append((second_button, 2))

        if third_button:
            buttons.append((third_button, 3))

        super().__init__(parent=parent, title=title, message=message, message_type=Gtk.MessageType.OTHER,
                         callback=callback, callback_data=callback_data, buttons=buttons)

        self.option = Gtk.CheckButton(label=option_label, active=option_value, visible=bool(option_label))

        if option_label:
            if GTK_API_VERSION >= 4:
                self.container.append(self.option)
            else:
                self.container.add(self.option)


""" Plugin Settings Dialog """


class PluginSettingsDialog:

    def __init__(self, frame, preferences, plugin_id, plugin_settings):

        self.frame = frame
        self.preferences = preferences
        self.plugin_id = plugin_id
        self.plugin_settings = plugin_settings
        self.option_widgets = {}

        plugin_name = frame.core.pluginhandler.get_plugin_info(plugin_id).get("Name", plugin_id)

        cancel_button = Gtk.Button(label=_("_Cancel"), use_underline=True, visible=True)
        cancel_button.connect("clicked", self.on_cancel)

        ok_button = Gtk.Button(label=_("_OK"), use_underline=True, visible=True)
        ok_button.connect("clicked", self.on_ok)

        self.primary_container = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL, width_request=340, visible=True,
            margin_top=14, margin_bottom=14, margin_start=18, margin_end=18, spacing=12
        )
        scrolled_window = Gtk.ScrolledWindow(
            hexpand=True, vexpand=True, min_content_height=300,
            hscrollbar_policy=Gtk.PolicyType.NEVER, vscrollbar_policy=Gtk.PolicyType.AUTOMATIC, visible=True
        )
        scrolled_window.set_property("child", self.primary_container)

        self.dialog = generic_dialog(
            parent=preferences.dialog,
            content_box=scrolled_window,
            buttons=[(cancel_button, Gtk.ResponseType.CANCEL),
                     (ok_button, Gtk.ResponseType.OK)],
            default_response=Gtk.ResponseType.OK,
            quit_callback=self.on_cancel,
            title=_("%s Settings") % plugin_name,
            width=600,
            height=425
        )
        self.dialog.get_style_context().add_class("preferences")

        self._add_options()

    @staticmethod
    def _generate_label(text):
        return Gtk.Label(label=text, use_markup=True, hexpand=True, wrap=True, xalign=0, visible=bool(text))

    def _generate_widget_container(self, description, child_widget, vertical=False):

        container = Gtk.Box(spacing=12, visible=True)

        if vertical:
            container.set_orientation(Gtk.Orientation.VERTICAL)

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
        self.preferences.set_widget(button, option_value)

    def _add_boolean_option(self, option_name, option_value, description):

        self.option_widgets[option_name] = button = Gtk.CheckButton(label=description, receives_default=True,
                                                                    visible=True)
        self._generate_widget_container("", button)
        self.preferences.set_widget(button, option_value)

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
        self.preferences.set_widget(self.option_widgets[option_name], option_value)

    def _add_dropdown_option(self, option_name, option_value, description, items):

        self.option_widgets[option_name] = combobox = Gtk.ComboBoxText(valign=Gtk.Align.CENTER, visible=True)
        label = self._generate_widget_container(description, combobox)
        label.set_mnemonic_widget(combobox)

        for text_label in items:
            combobox.append(id=text_label, text=text_label)

        self.preferences.set_widget(combobox, option_value)

    def _add_entry_option(self, option_name, option_value, description):

        self.option_widgets[option_name] = entry = Gtk.Entry(hexpand=True, valign=Gtk.Align.CENTER,
                                                             visible=True)
        label = self._generate_widget_container(description, entry)
        label.set_mnemonic_widget(entry)

        self.preferences.set_widget(entry, option_value)

    def _add_textview_option(self, option_name, option_value, description):

        frame_container = Gtk.Frame(visible=True)
        self.option_widgets[option_name] = textview = Gtk.TextView(
            accepts_tab=False, pixels_above_lines=1, pixels_below_lines=1,
            left_margin=8, right_margin=8, top_margin=5, bottom_margin=5,
            wrap_mode=Gtk.WrapMode.WORD_CHAR, visible=True
        )
        label = self._generate_widget_container(description, frame_container, vertical=True)
        label.set_mnemonic_widget(textview)
        self.preferences.set_widget(textview, option_value)

        scrolled_window = Gtk.ScrolledWindow(hexpand=True, vexpand=True, min_content_height=125,
                                             visible=True)

        frame_container.set_property("child", scrolled_window)
        scrolled_window.set_property("child", textview)

    def _add_list_option(self, option_name, option_value, description):

        container = Gtk.Box(spacing=6, visible=True)
        frame_container = Gtk.Frame(visible=True)

        scrolled_window = Gtk.ScrolledWindow(
            hexpand=True, vexpand=True, min_content_height=125,
            hscrollbar_policy=Gtk.PolicyType.AUTOMATIC, vscrollbar_policy=Gtk.PolicyType.AUTOMATIC, visible=True
        )

        self.option_widgets[option_name] = treeview = Gtk.TreeView(model=Gtk.ListStore(str), visible=True)

        scrolled_window.set_property("child", treeview)
        frame_container.set_property("child", scrolled_window)

        from pynicotine.gtkgui.widgets.treeview import initialise_columns
        cols = initialise_columns(
            self.frame, None, treeview,
            [description, description, -1, "edit", None]
        )
        self.preferences.set_widget(treeview, option_value)

        renderers = cols[description].get_cells()
        for render in renderers:
            render.connect('edited', self.cell_edited_callback, treeview)

        box = Gtk.Box(spacing=6, visible=True)

        add_button = Gtk.Button(label=_("Add…"), visible=True)
        add_button.connect("clicked", self.on_add, treeview)

        remove_button = Gtk.Button(label=_("Remove"), visible=True)
        remove_button.connect("clicked", self.on_remove, treeview)

        if GTK_API_VERSION >= 4:
            box.append(add_button)                    # pylint: disable=no-member
            box.append(remove_button)                 # pylint: disable=no-member

            self.primary_container.append(container)  # pylint: disable=no-member
            self.primary_container.append(box)        # pylint: disable=no-member

            container.append(frame_container)         # pylint: disable=no-member
        else:
            box.add(add_button)                    # pylint: disable=no-member
            box.add(remove_button)                 # pylint: disable=no-member

            self.primary_container.add(container)  # pylint: disable=no-member
            self.primary_container.add(box)        # pylint: disable=no-member

            container.add(frame_container)         # pylint: disable=no-member

    def _add_file_option(self, option_name, option_value, description, file_chooser_type):

        button_widget = Gtk.Button(hexpand=True, valign=Gtk.Align.CENTER, visible=True)
        label = self._generate_widget_container(description, button_widget)

        self.option_widgets[option_name] = FileChooserButton(button_widget, self.dialog, file_chooser_type)
        label.set_mnemonic_widget(button_widget)

        self.preferences.set_widget(self.option_widgets[option_name], option_value)

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

    @staticmethod
    def cell_edited_callback(_widget, index, value, treeview):

        store = treeview.get_model()
        iterator = store.get_iter(index)
        store.set(iterator, 0, value)

    @staticmethod
    def on_add(_widget, treeview):

        iterator = treeview.get_model().append([""])
        col = treeview.get_column(0)

        treeview.set_cursor(treeview.get_model().get_path(iterator), col, True)

    @staticmethod
    def on_remove(_widget, treeview):

        selection = treeview.get_selection()
        iterator = selection.get_selected()[1]
        if iterator is not None:
            treeview.get_model().remove(iterator)

    def on_cancel(self, *_args):
        self.dialog.destroy()

    def on_ok(self, *_args):

        for name in self.plugin_settings:
            value = self.preferences.get_widget_data(self.option_widgets[name])

            if value is not None:
                config.sections["plugins"][self.plugin_id.lower()][name] = value

        self.frame.core.pluginhandler.plugin_settings(
            self.plugin_id, self.frame.core.pluginhandler.enabled_plugins[self.plugin_id])

        self.dialog.destroy()

    def show(self):
        dialog_show(self.dialog)
