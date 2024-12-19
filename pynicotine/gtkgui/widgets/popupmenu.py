# COPYRIGHT (C) 2020-2024 Nicotine+ Contributors
# COPYRIGHT (C) 2016-2017 Michael Labouebe <gfarmerfr@free.fr>
# COPYRIGHT (C) 2008-2009 quinox <quinox@users.sf.net>
# COPYRIGHT (C) 2006-2009 daelstorm <daelstorm@gmail.com>
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
import sys

from gi.repository import Gdk
from gi.repository import Gio
from gi.repository import GLib
from gi.repository import Gtk

from pynicotine.config import config
from pynicotine.core import core
from pynicotine.gtkgui.application import GTK_API_VERSION
from pynicotine.gtkgui.widgets import clipboard
from pynicotine.gtkgui.widgets.accelerator import Accelerator
from pynicotine.utils import TRANSLATE_PUNCTUATION


class PopupMenu:

    popup_id_counter = 0

    def __init__(self, application, parent=None, callback=None, connect_events=True):

        self.model = Gio.Menu()
        self.application = application
        self.parent = parent
        self.callback = callback

        self.popup_menu = None
        self.menu_button = None
        self.gesture_click = None
        self.gesture_press = None
        self.valid_parent_widgets = Gtk.Box if GTK_API_VERSION >= 4 else (Gtk.Box, Gtk.EventBox)

        if connect_events and parent:
            self.connect_events(parent)

        self.pending_items = []
        self.actions = {}
        self.items = {}
        self.submenus = []

        self.menu_section = None
        self.editing = False

        PopupMenu.popup_id_counter += 1
        self.popup_id = PopupMenu.popup_id_counter

    def destroy(self):
        self.clear()
        self.__dict__.clear()

    def set_parent(self, parent):

        if parent:
            self.connect_events(parent)
            self.parent = parent

    def set_menu_button(self, button):

        if self.menu_button is not None:
            self.menu_button.set_menu_model(None)

        self.menu_button = button

        if button is None:
            return

        button.set_menu_model(self.model)

        # Workaround for GTK bug where clicks stop working after clicking inside popover once
        if GTK_API_VERSION >= 4 and os.environ.get("GDK_BACKEND") == "broadway":
            popover = list(button)[-1]
            popover.set_has_arrow(False)

    def create_context_menu(self, parent):

        if self.popup_menu:
            return self.popup_menu

        # Menus can only attach to a Gtk.Box/Gtk.EventBox parent, otherwise sizing and theming issues may occur
        while not isinstance(parent, self.valid_parent_widgets):
            parent = parent.get_parent()

        if GTK_API_VERSION >= 4:
            self.popup_menu = Gtk.PopoverMenu.new_from_model_full(self.model,  # pylint: disable=no-member
                                                                  Gtk.PopoverMenuFlags.NESTED)
            self.popup_menu.set_parent(parent)
            self.popup_menu.set_halign(Gtk.Align.START)
            self.popup_menu.set_has_arrow(False)

            # Workaround for wrong widget receiving focus after closing menu in GTK 4
            self.popup_menu.connect("closed", lambda *_args: self.parent.child_focus(Gtk.DirectionType.TAB_FORWARD))
        else:
            self.popup_menu = Gtk.Menu.new_from_model(self.model)
            self.popup_menu.attach_to_widget(parent)

        return self.popup_menu

    def _create_action(self, action_id, stateful=False):

        state = GLib.Variant.new_boolean(False) if stateful else None
        action = Gio.SimpleAction(name=action_id, state=state)

        self.application.add_action(action)
        return action

    def _create_menu_item(self, item):
        """
        Types of menu items:
            > - submenu
            $ - boolean
            O - choice
            # - regular
            = - hidden when disabled
            ^ - hidden in macOS menu bar
        """

        submenu = False
        boolean = False
        choice = False
        item_type = item[0][0]
        label = item[0][1:]

        if item_type == ">":
            submenu = True

        elif item_type == "$":
            boolean = True

        elif item_type == "O":
            choice = True

        if isinstance(item[1], str):
            # Action name provided, don't create action here
            action_id = item[1]
            action = None

        else:
            normalized_label = "-".join(label.translate(TRANSLATE_PUNCTUATION).lower().split())
            action_id = f"app.menu-{normalized_label}-{self.popup_id}"
            action = self._create_action(action_id.replace("app.", "", 1), (boolean or choice))

        if choice and len(item) > 2 and isinstance(item[2], str):
            # Choice target name
            action_id = f"{action_id}::{item[2]}"

        menuitem = Gio.MenuItem.new(label, action_id)

        if item_type == "=":
            menuitem.set_attribute_value("hidden-when", GLib.Variant.new_string("action-disabled"))

        elif item_type == "^":
            menuitem.set_attribute_value("hidden-when", GLib.Variant.new_string("macos-menubar"))

        if submenu:
            menuitem.set_submenu(item[1].model)
            self.submenus.append(item[1])

            if GTK_API_VERSION == 3:
                # Ideally, we wouldn't hide disabled submenus, but a GTK limitation forces us to
                # https://discourse.gnome.org/t/question-how-do-i-disable-a-menubar-menu-in-gtk-is-it-even-possible/906/9
                menuitem.set_attribute_value("hidden-when", GLib.Variant.new_string("action-disabled"))

        elif action and item[1]:
            # Callback
            action_name = "change-state" if boolean or choice else "activate"
            action.connect(action_name, *item[1:])

        self.items[label] = menuitem

        if action is not None:
            self.actions[label] = action

        return menuitem

    def _add_item_to_section(self, item):

        if not self.menu_section or not item[0]:
            # Create new section

            self.menu_section = Gio.Menu()
            menuitem = Gio.MenuItem.new_section(label=None, section=self.menu_section)
            self.model.append_item(menuitem)

            if not item[0]:
                return

        menuitem = self._create_menu_item(item)
        self.menu_section.append_item(menuitem)

    def update_model(self):
        """This function is called before a menu model needs to be manipulated
        (enabling/disabling actions, showing a menu in the GUI)"""

        if not self.pending_items:
            return

        for item in self.pending_items:
            self._add_item_to_section(item)

        self.pending_items.clear()

        for submenu in self.submenus:
            submenu.update_model()

    def add_items(self, *items):
        for item in items:
            self.pending_items.append(item)

    def clear(self):

        for submenu in self.submenus:
            # Ensure we remove all submenu actions
            submenu.clear()

        self.submenus.clear()
        self.model.remove_all()

        for action in self.actions.values():
            self.application.remove_action(action.get_name())

        self.actions.clear()
        self.items.clear()

        self.menu_section = None

    def popup(self, pos_x, pos_y, controller=None, menu=None):

        if menu is None:
            menu = self.create_context_menu(self.parent)

        if GTK_API_VERSION >= 4:
            if not pos_x and not pos_y:
                pos_x = pos_y = 0

            rectangle = Gdk.Rectangle()
            rectangle.x = pos_x
            rectangle.y = pos_y

            # Width/height 4 instead of 1 to work around this GTK bug in most cases:
            # https://gitlab.gnome.org/GNOME/gtk/-/issues/5712
            rectangle.width = rectangle.height = 4

            menu.set_pointing_to(rectangle)
            menu.popup()
            return

        event = None

        if controller is not None:
            sequence = controller.get_current_sequence()

            if sequence is not None:
                event = controller.get_last_event(sequence)

        menu.popup_at_pointer(event)

    # Events #

    def _callback(self, controller=None, pos_x=None, pos_y=None):

        menu = None
        menu_model = self
        callback = self.callback
        self.update_model()

        if isinstance(self.parent, Gtk.TreeView):
            if pos_x and pos_y:
                from pynicotine.gtkgui.widgets.treeview import set_treeview_selected_row

                bin_x, bin_y = self.parent.convert_widget_to_bin_window_coords(pos_x, pos_y)
                set_treeview_selected_row(self.parent, bin_x, bin_y)

                if not self.parent.get_path_at_pos(bin_x, bin_y):
                    # Special case for column header menu

                    menu_model = self.parent.column_menu
                    menu = menu_model.create_context_menu(menu_model.parent)
                    callback = menu_model.callback

            elif not self.parent.get_selection().count_selected_rows():
                # No rows selected, don't show menu
                return False

        if callback is not None:
            callback(menu_model, self.parent)

        self.popup(pos_x, pos_y, controller, menu=menu)
        return True

    def _callback_click_gtk4(self, controller, _num_p, pos_x, pos_y):
        return self._callback(controller, pos_x, pos_y)

    def _callback_click_gtk4_darwin(self, controller, _num_p, pos_x, pos_y):

        try:
            event = controller.get_last_event()
        except TypeError:
            # PyGObject <3.48.0
            return False

        if event.triggers_context_menu():
            return self._callback(controller, pos_x, pos_y)

        return False

    def _callback_click_gtk3(self, controller, _num_p, pos_x, pos_y):

        sequence = controller.get_current_sequence()

        if sequence is not None:
            event = controller.get_last_event(sequence)
            show_context_menu = event.triggers_context_menu()
        else:
            # Workaround for GTK 3.22.30
            show_context_menu = (controller.get_current_button() == Gdk.BUTTON_SECONDARY)

        if show_context_menu:
            return self._callback(controller, pos_x, pos_y)

        return False

    def _callback_menu(self, *_args):
        return self._callback()

    def connect_events(self, parent):

        if GTK_API_VERSION >= 4:
            self.gesture_click = Gtk.GestureClick()
            self.gesture_click.set_button(Gdk.BUTTON_SECONDARY)
            self.gesture_click.connect("pressed", self._callback_click_gtk4)
            parent.add_controller(self.gesture_click)

            self.gesture_press = Gtk.GestureLongPress()
            parent.add_controller(self.gesture_press)

            Accelerator("<Shift>F10", parent, self._callback_menu)

            if sys.platform == "darwin":
                gesture_click_darwin = Gtk.GestureClick()
                parent.add_controller(gesture_click_darwin)

                gesture_click_darwin.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
                gesture_click_darwin.connect("pressed", self._callback_click_gtk4_darwin)

        else:
            self.gesture_click = Gtk.GestureMultiPress(widget=parent)
            self.gesture_click.set_button(0)
            self.gesture_click.connect("pressed", self._callback_click_gtk3)

            self.gesture_press = Gtk.GestureLongPress(widget=parent)

            # Shift+F10
            parent.connect("popup-menu", self._callback_menu)

        self.gesture_click.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)

        self.gesture_press.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        self.gesture_press.set_touch_only(True)
        self.gesture_press.connect("pressed", self._callback)


class FilePopupMenu(PopupMenu):

    def __init__(self, application, parent=None, callback=None, connect_events=True):

        super().__init__(application=application, parent=parent, callback=callback,
                         connect_events=connect_events)

        self._setup_file_menu()

    def _setup_file_menu(self):

        self.add_items(
            ("#" + "selected_files", None),
            ("", None)
        )

    def set_num_selected_files(self, num_files):

        self.actions["selected_files"].set_enabled(False)
        self.items["selected_files"].set_label(_("%s File(s) Selected") % num_files)
        self.model.remove(0)
        self.model.prepend_item(self.items["selected_files"])


class UserPopupMenu(PopupMenu):

    def __init__(self, application, parent=None, callback=None, connect_events=True, username=None,
                 tab_name=None):

        super().__init__(application=application, parent=parent, callback=callback,
                         connect_events=connect_events)

        self.username = username
        self.tab_name = tab_name
        self.popup_menu_private_rooms = None

        if tab_name != "private_rooms":
            self.popup_menu_private_rooms = UserPopupMenu(self.application, username=username, tab_name="private_rooms")
            self.setup_user_menu(username)

    def setup_user_menu(self, username):

        self.set_user(username)

        self.add_items(
            ("#" + "username", self.on_copy_user),
            ("", None)
        )

        if self.tab_name != "userinfo":
            self.add_items(("#" + _("View User _Profile"), self.on_user_profile))

        if self.tab_name != "privatechat":
            self.add_items(("#" + _("_Send Message"), self.on_send_message))

        if self.tab_name != "userbrowse":
            self.add_items(("#" + _("_Browse Files"), self.on_browse_user))

        if self.tab_name != "userlist":
            self.add_items(("$" + _("_Add Buddy"), self.on_add_to_list))

        self.add_items(
            ("", None),
            ("$" + _("Ban User"), self.on_ban_user),
            ("$" + _("Ignore User"), self.on_ignore_user),
            ("", None),
            ("$" + _("Ban IP Address"), self.on_ban_ip),
            ("$" + _("Ignore IP Address"), self.on_ignore_ip),
            ("#" + _("Show IP A_ddress"), self.on_show_ip_address),
            ("", None),
            (">" + _("Private Rooms"), self.popup_menu_private_rooms)
        )

    def update_username_item(self):

        if not self.username:
            return

        user_item = self.items.get("username")

        if not user_item:
            return

        user_item.set_label(self.username.replace("_", "__"))  # Escape underscores to disable mnemonics
        self.model.remove(0)
        self.model.prepend_item(user_item)

    def set_user(self, username):

        if username == self.username:
            return

        self.username = username
        self.update_username_item()

        if self.popup_menu_private_rooms is not None:
            self.popup_menu_private_rooms.set_user(self.username)

    def toggle_user_items(self):

        self.editing = True

        local_username = core.users.login_username or config.sections["server"]["login"]
        add_to_list = _("_Add Buddy")

        if add_to_list in self.actions:
            self.actions[add_to_list].set_state(GLib.Variant.new_boolean(self.username in core.buddies.users))

        for action_id, value in (
            (_("Ban User"), core.network_filter.is_user_banned(self.username)),
            (_("Ignore User"), core.network_filter.is_user_ignored(self.username)),
            (_("Ban IP Address"), core.network_filter.is_user_ip_banned(self.username)),
            (_("Ignore IP Address"), core.network_filter.is_user_ip_ignored(self.username))
        ):
            # Disable menu item if it's our own username and we haven't banned ourselves before
            self.actions[action_id].set_enabled(GLib.Variant.new_boolean(self.username != local_username or value))
            self.actions[action_id].set_state(GLib.Variant.new_boolean(value))

        self.popup_menu_private_rooms.populate_private_rooms()
        self.popup_menu_private_rooms.update_model()

        self.actions[_("Private Rooms")].set_enabled(bool(self.popup_menu_private_rooms.items))
        self.editing = False

    def populate_private_rooms(self):

        self.clear()

        for room, data in core.chatrooms.private_rooms.items():
            is_owned = core.chatrooms.is_private_room_owned(room)
            is_operator = core.chatrooms.is_private_room_operator(room)

            if not is_owned and not is_operator:
                continue

            if self.username == data.owner:
                continue

            is_user_member = (self.username in data.members)
            is_user_operator = (self.username in data.operators)

            if not is_user_operator:
                if is_user_member:
                    self.add_items(
                        ("#" + _("Remove from Private Room %s") % room, self.on_private_room_remove_user, room))
                else:
                    self.add_items(
                        ("#" + _("Add to Private Room %s") % room, self.on_private_room_add_user, room))

            if not is_owned:
                continue

            if is_user_operator:
                self.add_items(
                    ("#" + _("Remove as Operator of %s") % room, self.on_private_room_remove_operator, room))

            elif is_user_member:
                self.add_items(
                    ("#" + _("Add as Operator of %s") % room, self.on_private_room_add_operator, room))

            self.add_items(("", None))

    def update_model(self):
        super().update_model()
        self.update_username_item()

    # Events #

    def on_search_user(self, *_args):

        self.application.window.lookup_action("search-mode").change_state(GLib.Variant.new_string("user"))
        self.application.window.user_search_entry.set_text(self.username)
        self.application.window.change_main_page(self.application.window.search_page)
        GLib.idle_add(lambda: self.application.window.search_entry.grab_focus() == -1, priority=GLib.PRIORITY_HIGH_IDLE)

    def on_send_message(self, *_args):
        core.privatechat.show_user(self.username)

    def on_show_ip_address(self, *_args):
        core.users.request_ip_address(self.username, notify=True)

    def on_user_profile(self, *_args):
        core.userinfo.show_user(self.username)

    def on_browse_user(self, *_args):
        core.userbrowse.browse_user(self.username)

    def on_private_room_add_user(self, _action, _parameter, room):
        core.chatrooms.add_user_to_private_room(room, self.username)

    def on_private_room_remove_user(self, _action, _parameter, room):
        core.chatrooms.remove_user_from_private_room(room, self.username)

    def on_private_room_add_operator(self, _action, _parameter, room):
        core.chatrooms.add_operator_to_private_room(room, self.username)

    def on_private_room_remove_operator(self, _action, _parameter, room):
        core.chatrooms.remove_operator_from_private_room(room, self.username)

    def on_add_to_list(self, action, state):

        if self.editing:
            return

        if state.get_boolean():
            core.buddies.add_buddy(self.username)
        else:
            core.buddies.remove_buddy(self.username)

        action.set_state(state)

    def on_ban_user(self, action, state):

        if self.editing:
            return

        if state.get_boolean():
            core.network_filter.ban_user(self.username)
        else:
            core.network_filter.unban_user(self.username)

        action.set_state(state)

    def on_ban_ip(self, action, state):

        if self.editing:
            return

        if state.get_boolean():
            core.network_filter.ban_user_ip(self.username)
        else:
            core.network_filter.unban_user_ip(self.username)

        action.set_state(state)

    def on_ignore_ip(self, action, state):

        if self.editing:
            return

        if state.get_boolean():
            core.network_filter.ignore_user_ip(self.username)
        else:
            core.network_filter.unignore_user_ip(self.username)

        action.set_state(state)

    def on_ignore_user(self, action, state):

        if self.editing:
            return

        if state.get_boolean():
            core.network_filter.ignore_user(self.username)
        else:
            core.network_filter.unignore_user(self.username)

        action.set_state(state)

    def on_copy_user(self, *_args):
        clipboard.copy_text(self.username)
