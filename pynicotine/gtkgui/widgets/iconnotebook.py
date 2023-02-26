# COPYRIGHT (C) 2020-2022 Nicotine+ Contributors
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

import sys

from gi.repository import Gdk
from gi.repository import GLib
from gi.repository import Gtk

from pynicotine.config import config
from pynicotine.core import core
from pynicotine.gtkgui.application import GTK_API_VERSION
from pynicotine.gtkgui.widgets.dialogs import OptionDialog
from pynicotine.gtkgui.widgets.popupmenu import PopupMenu
from pynicotine.gtkgui.widgets.theme import USER_STATUS_ICON_NAMES
from pynicotine.gtkgui.widgets.theme import add_css_class
from pynicotine.gtkgui.widgets.theme import remove_css_class
from pynicotine.slskmessages import UserStatus


""" Icon Notebook """


class TabLabel:

    def __init__(self, label="", full_text="", close_button_visible=False, close_callback=None):

        self.container = Gtk.Box(hexpand=False, visible=True)
        add_css_class(self.container, "notebook-tab")

        self.is_important = False
        self.centered = False

        if GTK_API_VERSION >= 4:
            self.gesture_click = Gtk.GestureClick()
            self.container.add_controller(self.gesture_click)  # pylint: disable=no-member

            self.eventbox = Gtk.Box()
        else:
            self.gesture_click = Gtk.GestureMultiPress(widget=self.container)

            self.eventbox = Gtk.EventBox(visible=True)
            self.eventbox.add_events(Gdk.EventMask.SCROLL_MASK | Gdk.EventMask.SMOOTH_SCROLL_MASK)

        self.box = Gtk.Box(spacing=6, visible=True)

        self.label = Gtk.Label(halign=Gtk.Align.START, hexpand=True, single_line_mode=True, visible=True)
        self.full_text = full_text
        self.set_tooltip_text(full_text)
        self.set_text(label)

        self.close_button = None
        self.close_button_visible = close_button_visible and close_callback
        self.close_callback = close_callback

        self.start_icon = Gtk.Image(visible=False)
        self.end_icon = Gtk.Image(visible=False)

        self._pack_children()

    def _remove_tab_label(self):

        if self.eventbox.get_parent() is None:
            return

        for widget in (self.start_icon, self.label, self.end_icon):
            self.box.remove(widget)

        self.eventbox.remove(self.box)
        self.container.remove(self.eventbox)

    def _add_close_button(self):

        if self.close_button is not None:
            return

        if not self.close_button_visible:
            return

        if GTK_API_VERSION >= 4:
            self.close_button = Gtk.Button(icon_name="window-close-symbolic")
            self.close_button.is_close_button = True
            self.close_button.get_child().is_close_button = True
            self.container.append(self.close_button)  # pylint: disable=no-member
        else:
            self.close_button = Gtk.Button(image=Gtk.Image(icon_name="window-close-symbolic"))
            self.container.add(self.close_button)     # pylint: disable=no-member
            self.close_button.add_events(             # pylint: disable=no-member
                Gdk.EventMask.SCROLL_MASK | Gdk.EventMask.SMOOTH_SCROLL_MASK)

        add_css_class(self.close_button, "flat")
        self.close_button.set_tooltip_text(_("Close Tab"))
        self.close_button.set_visible(True)

        if self.close_callback is not None:
            self.close_button.connect("clicked", self.close_callback)

    def _remove_close_button(self):

        if self.close_button is not None:
            self.container.remove(self.close_button)
            self.close_button = None

    def _pack_children(self):

        self._remove_tab_label()
        self._remove_close_button()

        if sys.platform == "darwin":
            # Left align close button on macOS
            self._add_close_button()

        if GTK_API_VERSION >= 4:
            self.container.append(self.eventbox)  # pylint: disable=no-member
            self.eventbox.append(self.box)        # pylint: disable=no-member

            self.box.append(self.start_icon)      # pylint: disable=no-member
            self.box.append(self.label)           # pylint: disable=no-member
            self.box.append(self.end_icon)        # pylint: disable=no-member

        else:
            self.container.add(self.eventbox)     # pylint: disable=no-member
            self.eventbox.add(self.box)           # pylint: disable=no-member

            self.box.add(self.start_icon)         # pylint: disable=no-member
            self.box.add(self.label)              # pylint: disable=no-member
            self.box.add(self.end_icon)           # pylint: disable=no-member

        if sys.platform != "darwin":
            self._add_close_button()

        if self.centered:
            self.container.set_halign(Gtk.Align.CENTER)
        else:
            self.container.set_halign(Gtk.Align.FILL)

    def set_centered(self, centered):
        self.centered = centered
        self._pack_children()

    def set_close_button_visibility(self, visible):

        self.close_button_visible = visible

        if visible:
            self._add_close_button()
            return

        self._remove_close_button()

    def request_changed(self, is_important=False):

        self.remove_changed()

        # Chat mentions have priority over normal notifications
        if not self.is_important:
            self.is_important = is_important

        if self.is_important:
            add_css_class(self.container, "notebook-tab-highlight")
        else:
            add_css_class(self.container, "notebook-tab-changed")

        icon_name = "nplus-tab-highlight" if self.is_important else "nplus-tab-changed"
        self.end_icon.set_property("icon-name", icon_name)
        self.end_icon.set_visible(True)
        add_css_class(self.end_icon, "colored-icon")

    def remove_changed(self):

        self.is_important = False

        remove_css_class(self.container, "notebook-tab-changed")
        remove_css_class(self.container, "notebook-tab-highlight")

        self.end_icon.set_property("icon-name", None)
        self.end_icon.set_visible(False)
        remove_css_class(self.end_icon, "colored-icon")

    def set_status_icon(self, status):

        icon_name = USER_STATUS_ICON_NAMES.get(status)

        if not icon_name:
            return

        self.set_start_icon_name(icon_name)
        add_css_class(self.start_icon, "colored-icon")
        add_css_class(self.start_icon, "user-status")

    def set_start_icon_name(self, icon_name):
        self.start_icon.set_property("icon-name", icon_name)
        self.start_icon.set_visible(True)

    def set_tooltip_text(self, text):
        self.container.set_tooltip_text(text)

    def set_text(self, text):
        self.label.set_text(text)

    def get_text(self):
        return self.label.get_text()


class IconNotebook:
    """ This class extends the functionality of a Gtk.Notebook widget. On top of what a Gtk.Notebook provides:
    - Icons on tabs
    - Context (right-click) menus for tabs
    - Dropdown menu for unread tabs
    """

    def __init__(self, window, parent, parent_page=None, switch_page_callback=None, reorder_page_callback=None):

        self.window = window
        self.parent = parent
        self.parent_page = parent_page
        self.switch_page_callback = switch_page_callback
        self.reorder_page_callback = reorder_page_callback

        self.pages = {}
        self.tab_labels = {}
        self.unread_pages = []

        self.widget = Gtk.Notebook(scrollable=True, show_border=False, visible=True)

        self.pages_button_container = Gtk.Box(visible=(self.parent_page is not None))
        self.widget.set_action_widget(self.pages_button_container, Gtk.PackType.END)

        if GTK_API_VERSION >= 4:
            parent.append(self.widget)

            if parent_page is not None:
                content_box = parent_page.get_first_child()
                content_box.connect("show", self.on_show_parent_page)

            self.pages_button = Gtk.MenuButton(halign=Gtk.Align.CENTER, valign=Gtk.Align.CENTER, visible=True)
            self.pages_button.set_has_frame(False)                 # pylint: disable=no-member
            self.pages_button_container.append(self.pages_button)  # pylint: disable=no-member

            self.scroll_controller = Gtk.EventControllerScroll(flags=Gtk.EventControllerScrollFlags.BOTH_AXES)
            self.scroll_controller.connect("scroll", self.on_tab_scroll)

            tab_bar = self.widget.get_first_child()                # pylint: disable=no-member
            tab_bar.add_controller(self.scroll_controller)

            # GTK 4 workaround to prevent notebook tabs from being activated when pressing close button
            # https://gitlab.gnome.org/GNOME/gtk/-/issues/4046

            self.close_button_pressed = False

            self.gesture_click = Gtk.GestureClick()
            self.gesture_click.set_button(Gdk.BUTTON_PRIMARY)
            self.gesture_click.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
            self.gesture_click.connect("pressed", self.on_notebook_click_pressed)
            self.gesture_click.connect("released", self.on_notebook_click_released)

            self.widget.add_controller(self.gesture_click)         # pylint: disable=no-member

        else:
            parent.add(self.widget)

            if parent_page is not None:
                content_box = parent_page.get_children()[0]
                content_box.connect("show", self.on_show_parent_page)

            self.pages_button = Gtk.Button(halign=Gtk.Align.CENTER, valign=Gtk.Align.CENTER, visible=True)
            self.pages_button.connect("clicked", self.on_pages_button_pressed)
            self.pages_button_container.add(self.pages_button)  # pylint: disable=no-member

            self.widget.add_events(  # pylint: disable=no-member
                Gdk.EventMask.SCROLL_MASK | Gdk.EventMask.SMOOTH_SCROLL_MASK)
            self.widget.connect("scroll-event", self.on_tab_scroll_event)

        for style_class in ("circular", "flat"):
            add_css_class(self.pages_button, style_class)

        self.popup_menu_pages = PopupMenu(self.window.application, self.pages_button, connect_events=False)
        self.update_pages_menu_button()

        if GTK_API_VERSION >= 4:
            self.pages_button.set_menu_model(self.popup_menu_pages.model)
            self.pages_button.get_popover().connect("notify::visible", self.on_pages_button_pressed)

    def grab_focus(self):
        self.widget.grab_focus()

    """ Tabs """

    def get_tab_label(self, page):
        return self.tab_labels.get(page)

    def get_tab_label_inner(self, page):
        return self.get_tab_label(page).eventbox

    def set_tab_closers(self):

        for i in range(self.get_n_pages()):
            page = self.get_nth_page(i)
            tab_label = self.get_tab_label(page)
            tab_label.set_close_button_visibility(config.sections["ui"]["tabclosers"])

    def set_tab_text_colors(self):

        for i in range(self.get_n_pages()):
            page = self.get_nth_page(i)
            tab_label = self.get_tab_label(page)
            tab_label.set_text(tab_label.get_text())

    def append_page(self, page, text, focus_callback=None, close_callback=None, full_text=None, user=None):

        if full_text is None:
            full_text = text

        self.tab_labels[page] = tab_label = TabLabel(
            text, full_text, close_button_visible=config.sections["ui"]["tabclosers"], close_callback=close_callback)

        if close_callback:
            tab_label.gesture_click.set_button(Gdk.BUTTON_MIDDLE)
            tab_label.gesture_click.connect("pressed", close_callback, page)

        if GTK_API_VERSION >= 4:
            page.get_first_child().set_visible(False)
        else:
            page.get_children()[0].set_visible(False)

        page.focus_callback = focus_callback

        self.widget.append_page(page, tab_label.container)
        self.set_tab_reorderable(page, True)
        self.parent.set_visible(True)

        if user is not None:
            status = core.user_statuses.get(user, UserStatus.OFFLINE)
            self.set_user_status(page, text, status)

    def remove_page(self, page):

        self.widget.remove_page(self.page_num(page))
        self.remove_unread_page(page)
        del self.tab_labels[page]

        if self.get_n_pages() == 0:
            self.parent.set_visible(False)

    def remove_all_pages_response(self, dialog, response_id, _data):

        if response_id == 2:
            for i in reversed(range(self.get_n_pages())):
                page = self.get_nth_page(i)
                tab_label = self.get_tab_label(page)
                tab_label.close_callback(dialog)

    def remove_all_pages(self):

        OptionDialog(
            parent=self.window,
            title=_("Close All Tabs?"),
            message=_("Do you really want to close all tabs?"),
            callback=self.remove_all_pages_response
        ).show()

    def _update_pages_menu_button(self, icon_name, tooltip_text):

        if self.pages_button.get_tooltip_text() == tooltip_text:
            return

        if GTK_API_VERSION >= 4:
            self.pages_button.set_icon_name(icon_name)                   # pylint: disable=no-member
        else:
            self.pages_button.set_image(Gtk.Image(icon_name=icon_name))  # pylint: disable=no-member

        self.pages_button.set_tooltip_text(tooltip_text)

    def update_pages_menu_button(self):

        if self.unread_pages:
            icon_name = "emblem-important-symbolic"
            tooltip_text = _("Unread Tabs")
        else:
            icon_name = "pan-down-symbolic"
            tooltip_text = _("All Tabs")

        self._update_pages_menu_button(icon_name, tooltip_text)

    def get_current_page(self):
        return self.get_nth_page(self.widget.get_current_page())

    def set_current_page(self, page):
        page_num = self.page_num(page)
        self.widget.set_current_page(page_num)

    def get_current_page_num(self):
        return self.widget.get_current_page()

    def set_current_page_num(self, page_num):
        self.widget.set_current_page(page_num)

    def set_tab_expand(self, page, expand):

        tab_label = self.get_tab_label(page)

        if GTK_API_VERSION >= 4:
            self.widget.get_page(page).set_property("tab-expand", expand)  # pylint: disable=no-member
        else:
            self.widget.child_set_property(page, "tab-expand", expand)     # pylint: disable=no-member

        tab_label.set_centered(expand)

    def set_tab_reorderable(self, page, reorderable):
        self.widget.set_tab_reorderable(page, reorderable)

    def set_tab_pos(self, pos):
        self.widget.set_tab_pos(pos)

    def get_n_pages(self):
        return self.widget.get_n_pages()

    def get_nth_page(self, page_num):
        return self.widget.get_nth_page(page_num)

    def page_num(self, page):
        return self.widget.page_num(page)

    def next_page(self):
        return self.widget.next_page()

    def prev_page(self):
        return self.widget.prev_page()

    def reorder_child(self, page, order):
        self.widget.reorder_child(page, order)

    """ Tab Highlights """

    def request_tab_changed(self, page, is_important=False):

        if self.parent_page is not None:
            page_active = (self.get_current_page() == page)

            if self.window.current_page_id != self.parent_page.id or not page_active:
                # Highlight top-level tab
                self.window.notebook.request_tab_changed(self.parent_page, is_important)

            if page_active:
                return

            self.append_unread_page(page)

        tab_label = self.get_tab_label(page)
        tab_label.request_changed(is_important)

    def remove_tab_changed(self, page):

        tab_label = self.get_tab_label(page)
        tab_label.remove_changed()

        if self.parent_page is not None:
            self.remove_unread_page(page)

    def append_unread_page(self, page):

        if page in self.unread_pages:
            return

        self.unread_pages.append(page)
        self.update_pages_menu_button()

    def remove_unread_page(self, page):

        if page in self.unread_pages:
            self.unread_pages.remove(page)
            self.update_pages_menu_button()

        if self.unread_pages:
            return

        if self.parent_page is not None:
            self.window.notebook.remove_tab_changed(self.parent_page)

    """ Tab User Status """

    def set_user_status(self, page, user, status):

        if status == UserStatus.AWAY:
            status_text = _("Away")

        elif status == UserStatus.ONLINE:
            status_text = _("Online")

        else:
            status_text = _("Offline")

        tab_label = self.get_tab_label(page)
        tab_label.set_status_icon(status)
        tab_label.set_text(user)
        tab_label.set_tooltip_text(f"{user} ({status_text})")

    """ Signals """

    def emit_switch_page_signal(self):

        curr_page = self.get_current_page()
        curr_page_num = self.get_current_page_num()

        if curr_page_num >= 0:
            self.widget.emit("switch-page", curr_page, curr_page_num)

    def connect_signals(self):

        self.widget.connect("page-reordered", self.on_reorder_page)
        self.widget.connect("page-removed", self.on_remove_page)
        self.widget.connect("switch-page", self.on_switch_page)

        if self.parent_page is None:
            # Show active page and focus default widget
            self.emit_switch_page_signal()

    def on_remove_page(self, _notebook, new_page, _page_num):
        self.remove_unread_page(new_page)

    def on_remove_all_pages(self, *_args):
        self.remove_all_pages()

    def on_switch_page(self, _notebook, new_page, page_num):

        if self.switch_page_callback is not None:
            self.switch_page_callback(self, new_page, page_num)

        # Hide container widget on previous page for a performance boost
        current_page = self.get_current_page()

        if GTK_API_VERSION >= 4:
            current_page.get_first_child().set_visible(False)
            new_page.get_first_child().set_visible(True)
        else:
            current_page.get_children()[0].set_visible(False)
            new_page.get_children()[0].set_visible(True)

        if self.parent_page is None:
            return

        # Focus the default widget on the page
        if self.window.current_page_id == self.parent_page.id:
            GLib.idle_add(new_page.focus_callback, priority=GLib.PRIORITY_HIGH_IDLE)

        # Dismiss tab highlight
        self.remove_tab_changed(new_page)

    def on_reorder_page(self, _notebook, page, page_num):
        if self.reorder_page_callback is not None:
            self.reorder_page_callback(self, page, page_num)

    def on_show_page(self, _action, _state, page):
        self.set_current_page(page)

    def on_show_parent_page(self, *_args):
        self.emit_switch_page_signal()

    def on_pages_button_pressed(self, *args):

        if GTK_API_VERSION >= 4:
            popover, *_unused = args

            if not popover.is_visible():
                return

        self.popup_menu_pages.clear()

        # Unread pages
        for page in self.unread_pages:
            tab_label = self.get_tab_label(page)
            self.popup_menu_pages.add_items(
                ("#*  " + tab_label.get_text(), self.on_show_page, page)
            )

        # Separator
        if self.unread_pages:
            self.popup_menu_pages.add_items(("", None))

        # All pages
        for i in range(self.get_n_pages()):
            page = self.get_nth_page(i)
            tab_label = self.get_tab_label(page)

            self.popup_menu_pages.add_items(
                ("#" + tab_label.get_text(), self.on_show_page, page)
            )

        self.popup_menu_pages.add_items(
            ("", None),
            ("#" + _("Close All Tabs…"), self.on_remove_all_pages)
        )

        self.popup_menu_pages.update_model()

        if GTK_API_VERSION == 3:
            self.popup_menu_pages.popup(pos_x=0, pos_y=0)

    def on_tab_scroll_event(self, _widget, event):

        current_page = self.get_current_page()

        if not current_page:
            return False

        if Gtk.get_event_widget(event).is_ancestor(current_page):
            return False

        if event.direction == Gdk.ScrollDirection.SMOOTH:
            return self.on_tab_scroll(scroll_x=event.delta_x, scroll_y=event.delta_y)

        if event.direction in (Gdk.ScrollDirection.RIGHT, Gdk.ScrollDirection.DOWN):
            self.next_page()

        elif event.direction in (Gdk.ScrollDirection.LEFT, Gdk.ScrollDirection.UP):
            self.prev_page()

        return True

    def on_tab_scroll(self, _controller=None, scroll_x=0, scroll_y=0):

        if scroll_x > 0 or scroll_y > 0:
            self.next_page()

        elif scroll_x < 0 or scroll_y < 0:
            self.prev_page()

        return True

    def on_tab_popup(self, widget, page):
        # Dummy implementation
        pass

    """ Signals (GTK 4) """

    def on_notebook_click_pressed(self, controller, _num_p, pressed_x, pressed_y):

        widget = self.widget.pick(pressed_x, pressed_y, Gtk.PickFlags.DEFAULT)  # pylint: disable=no-member

        if not hasattr(widget, "is_close_button"):
            return False

        self.close_button_pressed = True
        controller.set_state(Gtk.EventSequenceState.CLAIMED)
        return True

    def on_notebook_click_released(self, _controller, _num_p, pressed_x, pressed_y):

        if not self.close_button_pressed:
            return False

        widget = self.widget.pick(pressed_x, pressed_y, Gtk.PickFlags.DEFAULT)  # pylint: disable=no-member
        self.close_button_pressed = False

        if not hasattr(widget, "is_close_button"):
            return False

        if isinstance(widget, Gtk.Image):
            widget = widget.get_parent()

        widget.emit("clicked")
        return True
