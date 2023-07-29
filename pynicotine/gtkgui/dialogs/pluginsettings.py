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

from gi.repository import Gtk

from pynicotine.config import config
from pynicotine.core import core
from pynicotine.gtkgui.application import GTK_API_VERSION
from pynicotine.gtkgui.widgets.dialogs import Dialog
from pynicotine.gtkgui.widgets.dialogs import EntryDialog
from pynicotine.gtkgui.widgets.filechooser import FileChooserButton
from pynicotine.gtkgui.widgets.textentry import ComboBox
from pynicotine.gtkgui.widgets.textview import TextView
from pynicotine.gtkgui.widgets.theme import add_css_class


class PluginSettings(Dialog):

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

    def _generate_widget_container(self, description, child_widget=None, homogeneous=False,
                                   orientation=Gtk.Orientation.HORIZONTAL):

        container = Gtk.Box(homogeneous=homogeneous, orientation=orientation, spacing=12, visible=True)
        label = self._generate_label(description)

        if GTK_API_VERSION >= 4:
            container.append(label)                   # pylint: disable=no-member
            self.primary_container.append(container)  # pylint: disable=no-member

            if child_widget:
                container.append(child_widget)        # pylint: disable=no-member
        else:
            container.add(label)                      # pylint: disable=no-member
            self.primary_container.add(container)     # pylint: disable=no-member

            if child_widget:
                container.add(child_widget)           # pylint: disable=no-member

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

        label = self._generate_widget_container(description, homogeneous=True)
        self.option_widgets[option_name] = combobox = ComboBox(
            container=label.get_parent(), label=label)

        for item in items:
            combobox.append(item)

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
        container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, visible=True)
        frame_container = Gtk.Frame(child=container, visible=True)
        add_css_class(scrolled_window, "border-bottom")

        from pynicotine.gtkgui.widgets.treeview import TreeView
        self.option_widgets[option_name] = treeview = TreeView(
            self.application.window, parent=scrolled_window, activate_row_callback=self.on_row_activated,
            delete_accelerator_callback=self.on_delete_accelerator,
            columns={
                "description": {
                    "column_type": "text",
                    "title": description
                }
            }
        )
        treeview.description = description
        self.application.preferences.set_widget(treeview, option_value)

        button_container = Gtk.Box(margin_end=6, margin_bottom=6, margin_start=6, margin_top=6,
                                   spacing=6, visible=True)

        for icon_name, label_text, callback in (
            ("list-add-symbolic", _("Add…"), self.on_add),
            ("document-edit-symbolic", _("Edit…"), self.on_edit),
            ("list-remove-symbolic", _("Remove"), self.on_remove)
        ):
            button = Gtk.Button(visible=True)
            label_container = Gtk.Box(spacing=6, visible=True)
            icon = Gtk.Image(icon_name=icon_name, visible=True)
            label = Gtk.Label(label=label_text, mnemonic_widget=button, visible=True)

            button.set_property("child", label_container)
            button.connect("clicked", callback, treeview)
            add_css_class(button, "flat")

            if GTK_API_VERSION >= 4:
                label_container.append(icon)                # pylint: disable=no-member
                label_container.append(label)               # pylint: disable=no-member
                button_container.append(button)             # pylint: disable=no-member
            else:
                label_container.add(icon)                   # pylint: disable=no-member
                label_container.add(label)                  # pylint: disable=no-member
                button_container.add(button)                # pylint: disable=no-member

        if GTK_API_VERSION >= 4:
            self.primary_container.append(frame_container)  # pylint: disable=no-member

            container.append(scrolled_window)               # pylint: disable=no-member
            container.append(button_container)              # pylint: disable=no-member
        else:
            self.primary_container.add(frame_container)     # pylint: disable=no-member

            container.add(scrolled_window)                  # pylint: disable=no-member
            container.add(button_container)                 # pylint: disable=no-member

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

    @staticmethod
    def _get_widget_data(widget):

        if isinstance(widget, Gtk.SpinButton):
            if widget.get_digits() > 0:
                return widget.get_value()

            return widget.get_value_as_int()

        if isinstance(widget, Gtk.Entry):
            return widget.get_text()

        if isinstance(widget, TextView):
            return widget.get_text()

        if isinstance(widget, Gtk.CheckButton):
            try:
                # Radio button
                for radio in widget.group_radios:
                    if radio.get_active():
                        return widget.group_radios.index(radio)

                return 0

            except (AttributeError, TypeError):
                # Regular check button
                return widget.get_active()

        if isinstance(widget, ComboBox):
            return widget.get_selected_id()

        from pynicotine.gtkgui.widgets.treeview import TreeView
        if isinstance(widget, TreeView):
            return [
                widget.get_row_value(iterator, "description") for iterator in widget.iterators.values()
            ]

        if isinstance(widget, FileChooserButton):
            return widget.get_path()

        return None

    def on_add_response(self, window, _response_id, treeview):

        value = window.get_entry_value()

        if not value:
            return

        treeview.add_row([value])

    def on_add(self, _button, treeview):

        EntryDialog(
            parent=self,
            title=_("Add Item"),
            message=treeview.description,
            callback=self.on_add_response,
            callback_data=treeview
        ).show()

    def on_edit_response(self, window, _response_id, data):

        value = window.get_entry_value()

        if not value:
            return

        treeview, iterator = data
        treeview.set_row_value(iterator, "description", value)

    def on_edit(self, _button=None, treeview=None):

        for iterator in treeview.get_selected_rows():
            value = treeview.get_row_value(iterator, "description")

            EntryDialog(
                parent=self,
                title=_("Edit Item"),
                message=treeview.description,
                callback=self.on_edit_response,
                callback_data=(treeview, iterator),
                default=value
            ).show()
            return

    def on_remove(self, _button=None, treeview=None):
        for iterator in reversed(treeview.get_selected_rows()):
            treeview.remove_row(iterator)

    def on_row_activated(self, treeview, *_args):
        self.on_edit(treeview=treeview)

    def on_delete_accelerator(self, treeview):
        self.on_remove(treeview=treeview)

    def on_cancel(self, *_args):
        self.close()

    def on_ok(self, *_args):

        for name in self.plugin_settings:
            value = self._get_widget_data(self.option_widgets[name])

            if value is not None:
                config.sections["plugins"][self.plugin_id.lower()][name] = value

        core.pluginhandler.plugin_settings(
            self.plugin_id, core.pluginhandler.enabled_plugins[self.plugin_id])

        self.close()
