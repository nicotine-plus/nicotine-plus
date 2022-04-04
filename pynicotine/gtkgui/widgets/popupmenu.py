# COPYRIGHT (C) 2020-2022 Nicotine+ Contributors
# COPYRIGHT (C) 2016-2017 Michael Labouebe <gfarmerfr@free.fr>
# COPYRIGHT (C) 2008-2009 Quinox <quinox@users.sf.net>
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

import random
import string

from gi.repository import Gdk
from gi.repository import Gio
from gi.repository import GLib
from gi.repository import Gtk

from pynicotine import slskmessages
from pynicotine.config import config
from pynicotine.gtkgui.application import GTK_API_VERSION
from pynicotine.gtkgui.utils import copy_text
from pynicotine.gtkgui.widgets.accelerator import Accelerator
from pynicotine.gtkgui.widgets.dialogs import EntryDialog


""" Popup/Context Menu """


class PopupMenu:

    def __init__(self, frame, parent=None, callback=None, connect_events=True):

        self.model = Gio.Menu()
        self.frame = frame
        self.core = frame.core
        self.parent = parent
        self.callback = callback

        self.popup_menu = None
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

        self.popup_id = ''.join(random.choice(string.digits) for _ in range(8))

        self.user = None
        self.useritem = None

    def set_parent(self, parent):

        if parent:
            self.connect_events(parent)
            self.parent = parent

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
        else:
            self.popup_menu = Gtk.Menu.new_from_model(self.model)
            self.popup_menu.attach_to_widget(parent, None)

        return self.popup_menu

    def _create_action(self, action_id, stateful=False):

        state = GLib.Variant("b", False) if stateful else None
        action = Gio.SimpleAction(name=action_id, state=state)

        self.frame.window.add_action(action)
        return action

    def _create_menu_item(self, item):
        """
        Types of menu items:
            > - submenu
            $ - boolean
            O - choice
            # - regular
            U - user
        """

        submenu = False
        boolean = False
        choice = False
        label = item[0][1:]

        if item[0][0] == ">":
            submenu = True

        elif item[0][0] == "$":
            boolean = True

        elif item[0][0] == "O":
            choice = True

        if isinstance(item[1], str):
            # Action name provided, don't create action here
            action_id = item[1]
            action = None

        else:
            action_id = "win." + (label + self.popup_id).replace(" ", "").lower().translate(
                str.maketrans(dict.fromkeys(string.punctuation)))

            action = self._create_action(action_id[4:], (boolean or choice))

        if choice and len(item) > 2 and isinstance(item[2], str):
            # Choice target name
            action_id = action_id + "::" + item[2]

        menuitem = Gio.MenuItem.new(label, action_id)

        if item[0][0] == "U":
            self.useritem = menuitem

        if submenu:
            menuitem.set_submenu(item[1].model)
            self.submenus.append(item[1])

            if GTK_API_VERSION == 3:
                # Ideally, we wouldn't hide disabled submenus, but a GTK limitation forces us to
                # https://discourse.gnome.org/t/question-how-do-i-disable-a-menubar-menu-in-gtk-is-it-even-possible/906/9
                menuitem.set_attribute_value("hidden-when", GLib.Variant("s", "action-disabled"))

        elif action and item[1]:
            # Callback
            action_name = "change-state" if boolean or choice else "activate"
            action.connect(action_name, *item[1:])

        self.items[label] = menuitem
        self.actions[label] = action

        return menuitem

    def _add_item_to_section(self, item):

        if not self.menu_section or not item[0]:
            # Create new section

            self.menu_section = Gio.Menu()
            menuitem = Gio.MenuItem.new_section(None, self.menu_section)
            self.model.append_item(menuitem)

            if not item[0]:
                return

        menuitem = self._create_menu_item(item)
        self.menu_section.append_item(menuitem)

    def update_model(self):
        """ This function is called before a menu model needs to be manipulated
        (enabling/disabling actions, showing a menu in the GUI) """

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

        for action in self.actions:
            self.frame.window.remove_action(action)

        self.actions.clear()
        self.items.clear()

        self.menu_section = None
        self.useritem = None

    def popup(self, pos_x, pos_y, controller=None, button=3, menu=None):

        if menu is None:
            menu = self.create_context_menu(self.parent)

        if GTK_API_VERSION >= 4:
            if not pos_x and not pos_y:
                pos_x = pos_y = 0

            menu.set_offset(pos_x, pos_y)
            menu.set_pointing_to(Gdk.Rectangle(pos_x, pos_y, 1, 1))
            menu.popup()
            return

        try:
            if controller:
                sequence = controller.get_current_sequence()
                event = controller.get_last_event(sequence)
            else:
                event = None

            menu.popup_at_pointer(event)

        except (AttributeError, TypeError):
            time = Gtk.get_current_event_time()
            menu.popup(None, None, None, None, button, time)

    """ Events """

    def _callback(self, controller, pos_x, pos_y):

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

        if callback:
            cancel = callback(menu_model, self.parent)

            if cancel:
                return False

        self.popup(pos_x, pos_y, controller, menu=menu)
        return False

    def _callback_click(self, controller, _num_p, pos_x, pos_y):
        return self._callback(controller, pos_x, pos_y)

    def _callback_menu(self, *_args):
        self._callback(None, None, None)
        return True

    def connect_events(self, parent):

        if GTK_API_VERSION >= 4:
            self.gesture_click = Gtk.GestureClick()
            parent.add_controller(self.gesture_click)

            self.gesture_press = Gtk.GestureLongPress()
            parent.add_controller(self.gesture_press)

            Accelerator("<Shift>F10", parent, self._callback_menu)

        else:
            self.gesture_click = Gtk.GestureMultiPress(widget=parent)
            self.gesture_press = Gtk.GestureLongPress(widget=parent)

            # Shift+F10
            parent.connect("popup-menu", self._callback_menu)

        self.gesture_click.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        self.gesture_click.set_button(Gdk.BUTTON_SECONDARY)
        self.gesture_click.connect("pressed", self._callback_click)

        self.gesture_press.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        self.gesture_press.set_touch_only(True)
        self.gesture_press.connect("pressed", self._callback)


class FilePopupMenu(PopupMenu):

    def set_num_selected_files(self, num_files):

        self.actions["selected_files"].set_enabled(False)
        self.items["selected_files"].set_label(_("%s File(s) Selected") % num_files)
        self.model.remove(0)
        self.model.prepend_item(self.items["selected_files"])


class UserPopupMenu(PopupMenu):

    def setup_user_menu(self, user=None, page=""):

        user_label = "U"

        if user is not None:
            self.user = user
            user_label += self.user

        self.add_items(
            (user_label, self.on_copy_user),
            ("", None)
        )

        if page != "privatechat":
            self.add_items(("#" + _("Send M_essage"), self.on_send_message))

        if page != "userinfo":
            self.add_items(("#" + _("Show User I_nfo"), self.on_get_user_info))

        if page != "userbrowse":
            self.add_items(("#" + _("_Browse Files"), self.on_browse_user))

        if page != "userlist":
            self.add_items(("$" + _("_Add to Buddy List"), self.on_add_to_list))

        self.add_items(
            ("#" + _("_Gift Privileges…"), self.on_give_privileges),
            ("", None),
            ("$" + _("Ban User"), self.on_ban_user),
            ("$" + _("Ignore User"), self.on_ignore_user),
            ("", None),
            ("$" + _("Ban IP Address"), self.on_block_user),
            ("$" + _("Ignore IP Address"), self.on_ignore_ip),
            ("#" + _("Show IP A_ddress"), self.on_show_ip_address)
        )

    def set_user(self, user):

        if not user or self.user == user:
            return

        self.user = user

        if not self.useritem:
            return

        self.useritem.set_label(user)
        self.model.remove(0)
        self.model.prepend_item(self.useritem)

    def get_user(self):
        return self.user

    def toggle_user_items(self):

        self.editing = True
        self.actions[_("_Gift Privileges…")].set_enabled(bool(self.core.privileges_left))

        add_to_list = _("_Add to Buddy List")

        if add_to_list in self.actions:
            self.actions[add_to_list].set_state(
                GLib.Variant("b", self.user in (i[0] for i in config.sections["server"]["userlist"]))
            )

        self.actions[_("Ban User")].set_state(GLib.Variant("b", self.core.network_filter.is_user_banned(self.user)))
        self.actions[_("Ignore User")].set_state(
            GLib.Variant("b", self.core.network_filter.is_user_ignored(self.user)))
        self.actions[_("Ban IP Address")].set_state(
            GLib.Variant("b", self.core.network_filter.get_cached_blocked_user_ip(self.user) or False))
        self.actions[_("Ignore IP Address")].set_state(
            GLib.Variant("b", self.core.network_filter.get_cached_ignored_user_ip(self.user) or False))

        self.editing = False

    def populate_private_rooms(self, popup):

        popup.clear()

        if self.user is None:
            return

        popup.set_user(self.user)

        for room, data in self.core.chatrooms.private_rooms.items():
            is_owned = self.core.chatrooms.is_private_room_owned(room)
            is_operator = self.core.chatrooms.is_private_room_operator(room)

            if not is_owned and not is_operator:
                continue

            if self.user in data["users"]:
                popup.add_items(
                    ("#" + _("Remove from Private Room %s") % room, popup.on_private_room_remove_user, room))
            else:
                popup.add_items(("#" + _("Add to Private Room %s") % room, popup.on_private_room_add_user, room))

            if not is_owned:
                continue

            if self.user in data["operators"]:
                popup.add_items(
                    ("#" + _("Remove as Operator of %s") % room, popup.on_private_room_remove_operator, room))
            else:
                popup.add_items(("#" + _("Add as Operator of %s") % room, popup.on_private_room_add_operator, room))

            popup.add_items(("", None))

        popup.update_model()

    """ Events """

    def on_search_user(self, *_args):

        self.frame.search_mode_action.change_state(GLib.Variant("s", "user"))
        self.frame.user_search_entry.set_text(self.user)
        self.frame.change_main_page(self.frame.search_page)

    def on_send_message(self, *_args):
        self.core.privatechats.show_user(self.user)
        self.frame.change_main_page(self.frame.private_page)

    def on_show_ip_address(self, *_args):
        self.core.request_ip_address(self.user)

    def on_get_user_info(self, *_args):
        self.core.userinfo.request_user_info(self.user)

    def on_browse_user(self, *_args):
        self.core.userbrowse.browse_user(self.user)

    def on_private_room_add_user(self, *args):
        room = args[-1]
        self.core.queue.append(slskmessages.PrivateRoomAddUser(room, self.user))

    def on_private_room_remove_user(self, *args):
        room = args[-1]
        self.core.queue.append(slskmessages.PrivateRoomRemoveUser(room, self.user))

    def on_private_room_add_operator(self, *args):
        room = args[-1]
        self.core.queue.append(slskmessages.PrivateRoomAddOperator(room, self.user))

    def on_private_room_remove_operator(self, *args):
        room = args[-1]
        self.core.queue.append(slskmessages.PrivateRoomRemoveOperator(room, self.user))

    def on_add_to_list(self, action, state):

        if self.editing:
            return

        if state.get_boolean():
            self.core.userlist.add_user(self.user)
        else:
            self.core.userlist.remove_user(self.user)

        action.set_state(state)

    def on_ban_user(self, action, state):

        if self.editing:
            return

        if state.get_boolean():
            self.core.network_filter.ban_user(self.user)
        else:
            self.core.network_filter.unban_user(self.user)

        action.set_state(state)

    def on_block_user(self, action, state):

        if self.editing:
            return

        if state.get_boolean():
            self.core.network_filter.block_user_ip(self.user)
        else:
            self.core.network_filter.unblock_user_ip(self.user)

        action.set_state(state)

    def on_ignore_ip(self, action, state):

        if self.editing:
            return

        if state.get_boolean():
            self.core.network_filter.ignore_user_ip(self.user)
        else:
            self.core.network_filter.unignore_user_ip(self.user)

        action.set_state(state)

    def on_ignore_user(self, action, state):

        if self.editing:
            return

        if state.get_boolean():
            self.core.network_filter.ignore_user(self.user)
        else:
            self.core.network_filter.unignore_user(self.user)

        action.set_state(state)

    def on_copy_user(self, *_args):
        copy_text(self.user)

    def on_give_privileges_response(self, dialog, _response_id, _data):

        days = dialog.get_response_value()

        if not days:
            return

        try:
            days = int(days)
            self.core.request_give_privileges(self.user, days)

        except ValueError:
            self.on_give_privileges(error=_("Please enter number of days!"))

    def on_give_privileges(self, *_args, error=None):

        self.core.request_check_privileges()

        if self.core.privileges_left is None:
            days = _("Unknown")
        else:
            days = self.core.privileges_left // 60 // 60 // 24

        message = (_("Gift days of your Soulseek privileges to user %(user)s (%(days_left)s):") %
                   {"user": self.user, "days_left": _("%(days)s days left") % {"days": days}})

        if error:
            message += "\n\n" + error

        EntryDialog(
            parent=self.frame.window,
            title=_("Gift Privileges"),
            message=message,
            callback=self.on_give_privileges_response
        ).show()
