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
from pynicotine.gtkgui.utils import setup_accelerator
from pynicotine.gtkgui.widgets.dialogs import entry_dialog


""" Popup/Context Menu """


class PopupMenu:

    def __init__(self, frame=None, widget=None, callback=None, connect_events=True):

        self.model = Gio.Menu()
        self.frame = frame
        self.widget = widget
        self.callback = callback

        self.popup_menu = None
        self.gesture_click = None
        self.gesture_press = None
        self.last_controller = None

        if connect_events and widget:
            self.connect_events(widget)

        self.actions = {}
        self.items = {}
        self.submenus = []

        self.menu_section = None
        self.editing = False

        self.popup_id = ''.join(random.choice(string.digits) for _ in range(8))

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
            self.widget = widget

    def create_context_menu(self, widget):

        if self.popup_menu:
            return self.popup_menu

        # Popovers can only attach to a Gtk.Box parent, otherwise sizing and theming issues may occur
        while not isinstance(widget, Gtk.Box):
            widget = widget.get_parent()

        if Gtk.get_major_version() == 4:
            self.popup_menu = Gtk.PopoverMenu.new_from_model_full(self.model, Gtk.PopoverMenuFlags.NESTED)
            self.popup_menu.set_parent(widget)
            self.popup_menu.set_halign(Gtk.Align.START)
            self.popup_menu.set_has_arrow(False)

            return self.popup_menu

        self.popup_menu = Gtk.Menu.new_from_model(self.model)
        self.popup_menu.attach_to_widget(widget, None)

        return self.popup_menu

    def create_action(self, action_id, stateful=False):

        if not stateful:
            action = Gio.SimpleAction.new(action_id, None)
        else:
            action = Gio.SimpleAction.new_stateful(action_id, None, GLib.Variant.new_boolean(False))

        self.get_window().add_action(action)
        return action

    def create_menu_item(self, item):
        """
        Types of menu items:
            > - submenu
            $ - boolean
            O - choice
            # - regular
        """

        submenu = False
        boolean = False
        choice = False

        if item[0][0] in (">", "$", "#", "O"):
            label = item[0][1:]
        else:
            label = "dummy"

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

            action = self.create_action(action_id[4:], (boolean or choice))

        if choice and len(item) > 2 and isinstance(item[2], str):
            # Choice target name
            action_id = action_id + "::" + item[2]

        menuitem = Gio.MenuItem.new(label, action_id)

        if item[0] == "USER":
            self.useritem = menuitem

        if submenu:
            menuitem.set_submenu(item[1].model)
            self.submenus.append(item[1])

            if Gtk.get_major_version() == 3:
                # Ideally, we wouldn't hide disabled submenus, but a GTK limitation forces us to
                # https://discourse.gnome.org/t/question-how-do-i-disable-a-menubar-menu-in-gtk-is-it-even-possible/906/9
                menuitem.set_attribute_value("hidden-when", GLib.Variant.new_string("action-disabled"))

        elif action and item[1]:
            # Callback
            action_name = "change-state" if boolean or choice else "activate"
            action.connect(action_name, *item[1:])

        self.items[label] = menuitem
        self.actions[label] = action

        return menuitem

    def append_item(self, item):

        if not self.menu_section or not item[0]:
            # Create new section

            self.menu_section = Gio.Menu()
            menuitem = Gio.MenuItem.new_section(None, self.menu_section)
            self.model.append_item(menuitem)

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
            self.append_item(("#" + _("Send M_essage"), self.on_send_message))

        if page != "userinfo":
            self.append_item(("#" + _("Show User I_nfo"), self.on_get_user_info))

        if page != "userbrowse":
            self.append_item(("#" + _("_Browse Files"), self.on_browse_user))

        self.setup(
            ("#" + _("Show IP A_ddress"), self.on_show_ip_address),
            ("#" + _("_Gift Privileges…"), self.on_give_privileges),
            ("", None)
        )

        if page != "userlist":
            self.append_item(("$" + _("_Add to Buddy List"), self.on_add_to_list))

        self.setup(
            ("$" + _("Ban User"), self.on_ban_user),
            ("$" + _("Ignore User"), self.on_ignore_user),
            ("$" + _("Block User's IP Address"), self.on_block_user),
            ("$" + _("Ignore User's IP Address"), self.on_ignore_ip),
        )

        self.set_user(user)

    def set_num_selected_files(self, num_files):

        self.actions["selected_files"].set_enabled(False)
        self.items["selected_files"].set_label(_("%s File(s) Selected") % num_files)

        # Rather ugly solution, but otherwise the label update doesn't display
        self.model.remove(0)
        self.model.prepend_item(self.items["selected_files"])

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
        section = self.model.get_item_link(0, Gio.MENU_LINK_SECTION)
        section.remove(0)
        section.prepend_item(self.useritem)

    def get_user(self):
        return self.user

    def toggle_user_items(self):

        self.editing = True
        self.actions[_("_Gift Privileges…")].set_enabled(bool(self.frame.np.privileges_left))

        add_to_list = _("_Add to Buddy List")

        if add_to_list in self.actions:
            self.actions[add_to_list].set_state(
                GLib.Variant.new_boolean(
                    self.user in (i[0] for i in config.sections["server"]["userlist"])
                )
            )

        self.actions[_("Ban User")].set_state(
            GLib.Variant.new_boolean(self.frame.np.network_filter.is_user_banned(self.user))
        )
        self.actions[_("Ignore User")].set_state(
            GLib.Variant.new_boolean(self.frame.np.network_filter.is_user_ignored(self.user))
        )
        self.actions[_("Block User's IP Address")].set_state(
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

        for room, data in self.frame.np.chatrooms.private_rooms.items():
            is_owned = self.frame.np.chatrooms.is_private_room_owned(room)
            is_operator = self.frame.np.chatrooms.is_private_room_operator(room)

            if not is_owned and not is_operator:
                continue

            if self.user in data["users"]:
                popup.append_item(
                    ("#" + _("Remove from Private Room %s") % room, popup.on_private_room_remove_user, room))
            else:
                popup.append_item(("#" + _("Add to Private Room %s") % room, popup.on_private_room_add_user, room))

            if not is_owned:
                continue

            if self.user in data["operators"]:
                popup.append_item(
                    ("#" + _("Remove as Operator of %s") % room, popup.on_private_room_remove_operator, room))
            else:
                popup.append_item(("#" + _("Add as Operator of %s") % room, popup.on_private_room_add_operator, room))

    def clear(self):

        for submenu in self.submenus:
            # Ensure we remove all submenu actions
            submenu.clear()

        self.submenus.clear()
        self.model.remove_all()

        for action in self.actions:
            self.get_window().remove_action(action)

        self.actions.clear()
        self.items.clear()

        self.menu_section = None
        self.useritem = None

    def popup(self, x, y, controller=None, button=3, menu=None):

        if menu is None:
            menu = self.create_context_menu(self.widget)

        if Gtk.get_major_version() == 4:
            if not x and not y:
                x = y = 0

            menu.set_offset(x, y)
            menu.set_pointing_to(Gdk.Rectangle(x, y, 1, 1))
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

    def _callback(self, controller, x, y):

        menu = None
        menu_model = self
        callback = self.callback

        if isinstance(self.widget, Gtk.TreeView):
            if x and y:
                from pynicotine.gtkgui.widgets.treeview import set_treeview_selected_row

                bin_x, bin_y = self.widget.convert_widget_to_bin_window_coords(x, y)
                set_treeview_selected_row(self.widget, bin_x, bin_y)

                if not self.widget.get_path_at_pos(bin_x, bin_y):
                    # Special case for column header menu

                    menu_model = self.widget.column_menu
                    menu = menu_model.create_context_menu(menu_model.widget)
                    callback = menu_model.callback

            elif not self.widget.get_selection().count_selected_rows():
                # No rows selected, don't show menu
                return

        if callback:
            cancel = callback(menu_model, self.widget)

            if cancel:
                return

        self.popup(x, y, controller, menu=menu)

        if controller:
            controller.set_state(Gtk.EventSequenceState.CLAIMED)

    def _callback_click(self, controller, num_p, x, y):
        self._callback(controller, x, y)

    def _callback_menu(self, *args):
        self._callback(None, None, None)
        return True

    def connect_events(self, widget):

        if Gtk.get_major_version() == 4:
            self.gesture_click = Gtk.GestureClick()
            widget.add_controller(self.gesture_click)

            self.gesture_press = Gtk.GestureLongPress()
            widget.add_controller(self.gesture_press)

            setup_accelerator("<Shift>F10", widget, self._callback_menu)

        else:
            self.gesture_click = Gtk.GestureMultiPress.new(widget)
            self.gesture_press = Gtk.GestureLongPress.new(widget)

            # Shift+F10
            widget.connect("popup-menu", self._callback_menu)

        self.gesture_click.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        self.gesture_click.set_button(Gdk.BUTTON_SECONDARY)
        self.gesture_click.connect("pressed", self._callback_click)

        self.gesture_press.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        self.gesture_press.set_touch_only(True)
        self.gesture_press.connect("pressed", self._callback)

    def on_search_user(self, *args):

        self.frame.search_mode_action.change_state(GLib.Variant.new_string("user"))
        self.frame.UserSearchEntry.set_text(self.user)
        self.frame.change_main_page("search")

    def on_send_message(self, *args):
        self.frame.np.privatechats.show_user(self.user)
        self.frame.change_main_page("private")

    def on_show_ip_address(self, *args):
        self.frame.np.request_ip_address(self.user)

    def on_get_user_info(self, *args):
        self.frame.np.userinfo.request_user_info(self.user)

    def on_browse_user(self, *args):
        self.frame.np.userbrowse.browse_user(self.user)

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
            self.frame.np.userlist.add_user(self.user)
        else:
            self.frame.np.userlist.remove_user(self.user)

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

    def on_copy_user(self, *args):
        copy_text(self.user)

    def on_give_privileges_response(self, dialog, response_id, data):

        days = dialog.get_response_value()
        dialog.destroy()

        if not days:
            return

        try:
            days = int(days)
            self.frame.np.request_give_privileges(self.user, days)

        except ValueError:
            self.on_give_privileges(error=_("Please enter number of days!"))

    def on_give_privileges(self, *args, error=None):

        self.frame.np.request_check_privileges()

        if self.frame.np.privileges_left is None:
            days = _("Unknown")
        else:
            days = self.frame.np.privileges_left // 60 // 60 // 24

        message = (_("Gift days of your Soulseek privileges to user %(user)s (%(days_left)s):") %
                   {"user": self.user, "days_left": _("%(days)s days left") % {"days": days}})

        if error:
            message += "\n\n" + error

        entry_dialog(
            parent=self.get_window(),
            title=_("Gift Privileges"),
            message=message,
            callback=self.on_give_privileges_response
        )
