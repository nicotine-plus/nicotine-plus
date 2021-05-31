# COPYRIGHT (C) 2020-2021 Nicotine+ Team
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
from pynicotine.gtkgui.utils import copy_text
from pynicotine.gtkgui.widgets.dialogs import entry_dialog


""" Popup/Context Menu """


class PopupMenu(Gio.Menu):

    def __init__(self, frame=None, widget=None, callback=None):

        Gio.Menu.__init__(self)

        self.frame = frame
        self.widget = widget
        self.callback = callback

        self.popup_menu = None
        self.gesture_click = None
        self.gesture_press = None
        self.last_controller = None
        self.menu_open = False

        if widget:
            self.connect_events(widget)
            self.create_context_menu(widget)

        self.actions = {}
        self.items = {}
        self.submenus = []

        self.menu_section = None
        self.editing = False

        self.popup_id = ''.join(random.choice(string.digits) for i in range(8))

        self.user = None
        self.useritem = None

    def get_window(self):

        if self.frame:
            return self.frame.MainWindow

        if Gtk.get_major_version() == 4:
            return self.widget.get_root()

        return self.widget.get_toplevel()

    def set_widget(self, widget):

        if widget:
            self.connect_events(widget)
            self.create_context_menu(widget)
            self.widget = widget

    def create_context_menu(self, widget):

        if Gtk.get_major_version() == 4:
            if isinstance(widget, Gtk.TreeView):
                widget = widget.get_next_sibling()

            self.popup_menu = Gtk.PopoverMenu.new_from_model_full(self, Gtk.PopoverMenuFlags.NESTED)
            self.popup_menu.set_parent(widget)
            self.popup_menu.set_has_arrow(False)
            self.popup_menu.present()
            return

        self.popup_menu = Gtk.Menu.new_from_model(self)
        self.popup_menu.attach_to_widget(widget, None)

    def create_action(self, action_id, stateful=False):

        if not stateful:
            action = Gio.SimpleAction.new(action_id, None)
        else:
            action = Gio.SimpleAction.new_stateful(action_id, None, GLib.Variant.new_boolean(False))

        self.get_window().add_action(action)
        return action

    def create_menu_item(self, item):

        submenu = False
        stateful = False

        if item[0][0] == ">":
            label = item[0][1:]
            submenu = True

        elif item[0][0] == "$":
            label = item[0][1:]
            stateful = True

        elif item[0][0] == "#":
            label = item[0][1:]

        else:
            label = "dummy"

        action_id = (label + self.popup_id).replace(" ", "").lower().translate(str.maketrans(dict.fromkeys(string.punctuation)))
        action = self.create_action(action_id, stateful)

        menuitem = Gio.MenuItem.new(label, "win." + action_id)

        if item[0] == "USER":
            self.useritem = menuitem

        if submenu:
            menuitem.set_submenu(item[1])
            self.submenus.append(item[1])

            if Gtk.get_major_version() == 3:
                # Ideally, we wouldn't hide disabled submenus, but a GTK limitation forces us to
                # https://discourse.gnome.org/t/question-how-do-i-disable-a-menubar-menu-in-gtk-is-it-even-possible/906/9
                menuitem.set_attribute_value("hidden-when", GLib.Variant.new_string("action-disabled"))

        elif item[1]:
            action_name = "change-state" if stateful else "activate"
            action.connect(action_name, *item[1:])

        self.items[label] = menuitem
        self.actions[label] = action

        return menuitem

    def append_item(self, item):

        if not self.menu_section or not item[0]:
            # Create new section

            self.menu_section = Gio.Menu.new()
            menuitem = Gio.MenuItem.new_section(None, self.menu_section)
            Gio.Menu.append_item(self, menuitem)

            if not item[0]:
                return menuitem

        menuitem = self.create_menu_item(item)
        self.menu_section.append_item(menuitem)

    def get_actions(self):
        return self.actions

    def get_items(self):
        return self.items

    def setup(self, *items):
        for item in items:
            self.append_item(item)

    def setup_user_menu(self, user=None, page=""):

        self.setup(
            ("USER", self.on_copy_user),
            ("", None)
        )

        if page != "privatechat":
            self.append_item(("#" + _("Send _Message"), self.on_send_message))

        if page != "userinfo":
            self.append_item(("#" + _("Show User I_nfo"), self.on_get_user_info))

        if page != "userbrowse":
            self.append_item(("#" + _("Brow_se Files"), self.on_browse_user))

        self.setup(
            ("#" + _("Gi_ve Privileges..."), self.on_give_privileges),
            ("", None),
            ("#" + _("Show IP A_ddress"), self.on_show_ip_address),
            ("#" + _("Client Version"), self.on_version),
            ("", None)
        )

        if page != "userlist":
            self.append_item(("$" + _("_Add to Buddy List"), self.on_add_to_list))

        self.setup(
            ("$" + _("_Ban User"), self.on_ban_user),
            ("$" + _("_Ignore User"), self.on_ignore_user),
            ("$" + _("B_lock User's IP Address"), self.on_block_user),
            ("$" + _("Ignore User's IP Address"), self.on_ignore_ip),
        )

        self.set_user(user)

    def set_num_selected_files(self, num_files):

        self.actions["selected_files"].set_enabled(False)
        self.items["selected_files"].set_label(_("%s File(s) Selected") % num_files)

        # Rather ugly solution, but otherwise the label update doesn't display
        self.remove(0)
        self.prepend_item(self.items["selected_files"])

    def set_user(self, user):

        if not user:
            return

        self.user = user

        if not self.useritem:
            return

        if Gtk.get_major_version() == 4:
            from html import escape
            user = escape(user)

        self.useritem.set_label(user)

        # Rather ugly solution, but otherwise the label update doesn't display
        section = self.get_item_link(0, Gio.MENU_LINK_SECTION)
        section.remove(0)
        section.prepend_item(self.useritem)

    def get_user(self):
        return self.user

    def toggle_user_items(self):

        self.editing = True
        add_to_list = _("_Add to Buddy List")

        if add_to_list in self.actions:
            self.actions[add_to_list].set_state(
                GLib.Variant.new_boolean(
                    self.user in (i[0] for i in config.sections["server"]["userlist"])
                )
            )

        self.actions[_("_Ban User")].set_state(
            GLib.Variant.new_boolean(self.frame.np.network_filter.is_user_banned(self.user))
        )
        self.actions[_("_Ignore User")].set_state(
            GLib.Variant.new_boolean(self.frame.np.network_filter.is_user_ignored(self.user))
        )
        self.actions[_("B_lock User's IP Address")].set_state(
            GLib.Variant.new_boolean(self.frame.np.network_filter.get_cached_blocked_user_ip(self.user) or False)
        )
        self.actions[_("Ignore User's IP Address")].set_state(
            GLib.Variant.new_boolean(self.frame.np.network_filter.get_cached_ignored_user_ip(self.user) or False)
        )

        self.editing = False

    def populate_private_rooms(self, popup):

        popup.clear()

        if self.user is None:
            return

        popup.set_user(self.user)

        for room in self.frame.chatrooms.private_rooms:

            if not self.frame.chatrooms.roomlist.is_private_room_owned(room) and \
                    not self.frame.chatrooms.roomlist.is_private_room_operator(room):
                continue

            if self.user in self.frame.chatrooms.private_rooms[room]["users"]:
                popup.append_item(("#" + _("Remove from Private Room %s") % room, popup.on_private_room_remove_user, room))
            else:
                popup.append_item(("#" + _("Add to Private Room %s") % room, popup.on_private_room_add_user, room))

            if not self.frame.chatrooms.roomlist.is_private_room_owned(room):
                continue

            if self.user in self.frame.chatrooms.private_rooms[room]["operators"]:
                popup.append_item(("#" + _("Remove as Operator of %s") % room, popup.on_private_room_remove_operator, room))
            else:
                popup.append_item(("#" + _("Add as Operator of %s") % room, popup.on_private_room_add_operator, room))

    def clear(self):

        for submenu in self.submenus:
            # Ensure we remove all submenu actions
            submenu.clear()

        self.submenus.clear()
        self.remove_all()

        for action in self.actions:
            self.get_window().remove_action(action)

        self.actions.clear()
        self.items.clear()

        self.menu_section = None
        self.useritem = None

    def popup(self, x, y, button=3):

        if Gtk.get_major_version() == 4:
            self.popup_menu.set_offset(x, y)
            self.popup_menu.set_pointing_to(Gdk.Rectangle(x, y, 1, 1))
            self.popup_menu.popup()

        else:
            if self.last_controller:
                sequence = self.last_controller.get_current_sequence()
                event = self.last_controller.get_last_event(sequence)
            else:
                event = None

            try:
                self.popup_menu.popup_at_pointer(event)

            except AttributeError:
                time = Gtk.get_current_event_time()
                self.popup_menu.popup(None, None, None, None, button, time)

    """ Events """

    def _callback(self, controller, x, y, bin_coords=False):

        self.last_controller = controller

        if x and y and isinstance(self.widget, Gtk.TreeView):
            from pynicotine.gtkgui.widgets.treeview import set_treeview_selected_row

            if bin_coords:
                bin_x, bin_y = x, y
            else:
                bin_x, bin_y = self.widget.convert_widget_to_bin_window_coords(x, y)

            set_treeview_selected_row(self.widget, bin_x, bin_y)

        if self.callback:
            cancel = self.callback(self, self.widget)

            if cancel:
                return

        self.popup(x, y)

    def _callback_legacy(self, controller, event):
        """ Gtk.TextView: Prevent GTK's built-in context menu from showing
            Gtk.TreeView: Preserve multi-row selection when showing menu """

        if self.menu_open:
            self.menu_open = False
            return True

    def _callback_click_gtk4(self, controller, num_p, x, y):

        self._callback(controller, x, y)
        self.menu_open = True

    def _callback_click_gtk3(self, widget, event):

        if event.triggers_context_menu():
            self._callback(None, event.x, event.y, bin_coords=True)
            return True

    def _callback_menu_gtk3(self, widget):
        self._callback(None, None, None)
        return True

    def connect_events(self, widget):

        if Gtk.get_major_version() == 4:
            if isinstance(self.widget, (Gtk.TextView, Gtk.TreeView)):
                self.legacy_controller = Gtk.EventControllerLegacy()
                self.legacy_controller.connect("event", self._callback_legacy)
                widget.add_controller(self.legacy_controller)

            self.gesture_click = Gtk.GestureClick()
            self.gesture_click.set_button(Gdk.BUTTON_SECONDARY)
            self.gesture_click.connect("pressed", self._callback_click_gtk4)
            widget.add_controller(self.gesture_click)

            self.gesture_press = Gtk.GestureLongPress()
            widget.add_controller(self.gesture_press)

        else:
            self.gesture_press = Gtk.GestureLongPress.new(widget)

            widget.connect("button-press-event", self._callback_click_gtk3)
            widget.connect("popup-menu", self._callback_menu_gtk3)

        self.gesture_press.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        self.gesture_press.set_touch_only(True)
        self.gesture_press.connect("pressed", self._callback)

    def on_search_user(self, *args):
        self.frame.SearchMethod.set_active_id("user")
        self.frame.UserSearchEntry.set_text(self.user)
        self.frame.change_main_page("search")

    def on_send_message(self, *args):
        self.frame.privatechats.send_message(self.user, show_user=True)
        self.frame.change_main_page("private")

    def on_show_ip_address(self, *args):
        self.frame.np.ip_requested.add(self.user)
        self.frame.np.queue.append(slskmessages.GetPeerAddress(self.user))

    def on_get_user_info(self, *args):
        self.frame.local_user_info_request(self.user)

    def on_browse_user(self, *args):
        self.frame.browse_user(self.user)

    def on_private_room_add_user(self, *args):
        room = args[-1]
        self.frame.np.queue.append(slskmessages.PrivateRoomAddUser(room, self.user))

    def on_private_room_remove_user(self, *args):
        room = args[-1]
        self.frame.np.queue.append(slskmessages.PrivateRoomRemoveUser(room, self.user))

    def on_private_room_add_operator(self, *args):
        room = args[-1]
        self.frame.np.queue.append(slskmessages.PrivateRoomAddOperator(room, self.user))

    def on_private_room_remove_operator(self, *args):
        room = args[-1]
        self.frame.np.queue.append(slskmessages.PrivateRoomRemoveOperator(room, self.user))

    def on_add_to_list(self, action, state):

        if self.editing:
            return

        if state.get_boolean():
            self.frame.userlist.add_to_list(self.user)
        else:
            self.frame.userlist.remove_from_list(self.user)

        action.set_state(state)

    def on_ban_user(self, action, state):

        if self.editing:
            return

        if state.get_boolean():
            self.frame.np.network_filter.ban_user(self.user)
        else:
            self.frame.np.network_filter.unban_user(self.user)

        action.set_state(state)

    def on_block_user(self, action, state):

        if self.editing:
            return

        if state.get_boolean():
            self.frame.np.network_filter.block_user_ip(self.user)
        else:
            self.frame.np.network_filter.unblock_user_ip(self.user)

        action.set_state(state)

    def on_ignore_ip(self, action, state):

        if self.editing:
            return

        if state.get_boolean():
            self.frame.np.network_filter.ignore_user_ip(self.user)
        else:
            self.frame.np.network_filter.unignore_user_ip(self.user)

        action.set_state(state)

    def on_ignore_user(self, action, state):

        if self.editing:
            return

        if state.get_boolean():
            self.frame.np.network_filter.ignore_user(self.user)
        else:
            self.frame.np.network_filter.unignore_user(self.user)

        action.set_state(state)

    def on_version(self, *args):
        self.frame.privatechats.send_message(self.user, "\x01VERSION\x01", bytestring=True)

    def on_copy_user(self, *args):
        copy_text(self.user)

    def on_give_privileges_response(self, dialog, response_id, data):

        days = dialog.get_response_value()
        dialog.destroy()

        if not days:
            return

        try:
            days = int(days)
            self.frame.np.queue.append(slskmessages.GivePrivileges(self.user, days))

        except ValueError:
            self.on_give_privileges(error=_("Please enter a whole number!"))

    def on_give_privileges(self, *args, error=None):

        self.frame.np.queue.append(slskmessages.CheckPrivileges())

        if self.frame.np.privileges_left is None:
            days = _("Unknown")
        else:
            days = self.frame.np.privileges_left // 60 // 60 // 24

        message = _("How many days of privileges should user %s be gifted?") % self.user + " (" + _("%(days)s days left") % {'days': days} + ")"

        if error:
            message += "\n\n" + error

        entry_dialog(
            parent=self.get_window(),
            title=_("Give Privileges"),
            message=message,
            callback=self.on_give_privileges_response
        )
