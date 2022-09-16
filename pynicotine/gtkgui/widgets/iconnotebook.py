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

import sys

from gi.repository import Gdk
from gi.repository import GLib
from gi.repository import Gtk

from pynicotine.config import config
from pynicotine.gtkgui.application import GTK_API_VERSION
from pynicotine.gtkgui.widgets.dialogs import OptionDialog
from pynicotine.gtkgui.widgets.popupmenu import PopupMenu
from pynicotine.gtkgui.widgets.theme import get_status_icon_name
from pynicotine.gtkgui.widgets.theme import parse_color_string
from pynicotine.slskmessages import UserStatus


""" Icon Notebook """


class TabLabel(Gtk.Box):

    def __init__(self, label="", full_text="", close_button_visible=False, close_callback=None):

        Gtk.Box.__init__(self, hexpand=False, visible=True)

        self.highlighted = False
        self.mentioned = False
        self.centered = False
        self.gesture_click = None

        if GTK_API_VERSION >= 4:
            self.eventbox = Gtk.Box()
        else:
            self.eventbox = Gtk.EventBox(visible=True)
            self.eventbox.add_events(Gdk.EventMask.SCROLL_MASK | Gdk.EventMask.SMOOTH_SCROLL_MASK)

        self.box = Gtk.Box(spacing=6, visible=True)

        self.label = Gtk.Label(halign=Gtk.Align.START, hexpand=True, single_line_mode=True, visible=True)
        self.full_text = full_text
        self.set_text(label)

        self.close_button = None
        self.close_button_visible = close_button_visible
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
        self.remove(self.eventbox)

    def _add_close_button(self):

        if self.close_button is not None:
            return

        if not self.close_button_visible:
            return

        if GTK_API_VERSION >= 4:
            self.close_button = Gtk.Button.new_from_icon_name("window-close-symbolic")
            self.close_button.is_close_button = True
            self.close_button.get_child().is_close_button = True
            self.append(self.close_button)  # pylint: disable=no-member
        else:
            self.close_button = Gtk.Button.new_from_icon_name("window-close-symbolic",
                                                              Gtk.IconSize.BUTTON)  # pylint: disable=no-member
            self.add(self.close_button)  # pylint: disable=no-member
            self.close_button.add_events(Gdk.EventMask.SCROLL_MASK | Gdk.EventMask.SMOOTH_SCROLL_MASK)

        self.close_button.get_style_context().add_class("flat")
        self.close_button.set_tooltip_text(_("Close tab"))
        self.close_button.show()

        if self.close_callback is not None:
            self.close_button.connect("clicked", self.close_callback)

    def _remove_close_button(self):

        if self.close_button is not None:
            self.remove(self.close_button)
            self.close_button = None

    def _pack_children(self):

        self._remove_tab_label()
        self._remove_close_button()

        if sys.platform == "darwin":
            # Left align close button on macOS
            self._add_close_button()

        if GTK_API_VERSION >= 4:
            self.append(self.eventbox)        # pylint: disable=no-member
            self.eventbox.append(self.box)    # pylint: disable=no-member

            self.box.append(self.start_icon)  # pylint: disable=no-member
            self.box.append(self.label)       # pylint: disable=no-member
            self.box.append(self.end_icon)    # pylint: disable=no-member

        else:
            self.add(self.eventbox)           # pylint: disable=no-member
            self.eventbox.add(self.box)       # pylint: disable=no-member

            self.box.add(self.start_icon)     # pylint: disable=no-member
            self.box.add(self.label)          # pylint: disable=no-member
            self.box.add(self.end_icon)       # pylint: disable=no-member

        if sys.platform != "darwin":
            self._add_close_button()

        if self.centered:
            self.set_halign(Gtk.Align.CENTER)
        else:
            self.set_halign(Gtk.Align.FILL)

    def _set_text_color(self, color):

        color_hex = parse_color_string(color)

        if color_hex:
            from html import escape
            self.label.set_markup("<span foreground=\"%s\">%s</span>" % (color_hex, escape(self.text)))
            return

        self.label.set_text("%s" % self.text)

    def set_centered(self, centered):
        self.centered = centered
        self._pack_children()

    def set_close_button_visibility(self, visible):

        self.close_button_visible = visible

        if visible:
            self._add_close_button()
            return

        self._remove_close_button()

    def request_hilite(self, mentioned=False):

        self.highlighted = True

        # Chat mentions have priority over normal notifications
        if not self.mentioned:
            self.mentioned = mentioned

        color = config.sections["ui"]["tab_default"]

        if config.sections["notifications"]["notification_tab_colors"]:
            if self.mentioned:
                color = config.sections["ui"]["tab_hilite"]
            else:
                color = config.sections["ui"]["tab_changed"]

        self._set_text_color(color)

        icon_name = "nplus-hilite" if self.mentioned else "nplus-hilite3"
        self.end_icon.set_property("icon-name", icon_name)
        self.end_icon.show()

    def remove_hilite(self):

        self.highlighted = False
        self.mentioned = False

        self._set_text_color(config.sections["ui"]["tab_default"])

        self.end_icon.set_property("icon-name", None)
        self.end_icon.hide()

    def set_status_icon(self, status):
        icon_name = get_status_icon_name(status)
        self.set_start_icon_name(icon_name, visible=config.sections["ui"]["tab_status_icons"])

    def set_start_icon_name(self, icon_name, visible=True):
        self.start_icon.set_property("icon-name", icon_name)
        self.start_icon.set_visible(visible)

    def set_text(self, text):

        self.text = text

        if self.highlighted:
            self.request_hilite()
            return

        self._set_text_color(config.sections["ui"]["tab_default"])

    def get_text(self):
        return self.label.get_text()


class IconNotebook:
    """ This class extends the functionality of a Gtk.Notebook widget. On top of what a Gtk.Notebook provides:
    - Icons on tabs
    - Context (right-click) menus for tabs
    - Dropdown menu for unread tabs
    """

    def __init__(self, frame, core, widget, parent_page=None, switch_page_callback=None, reorder_page_callback=None):

        self.widget = widget
        self.widget.connect("page-reordered", self.on_reorder_page)
        self.widget.connect("page-removed", self.on_remove_page)
        self.widget.connect("switch-page", self.on_switch_page)

        self.frame = frame
        self.core = core
        self.parent_page = parent_page
        self.switch_page_callback = switch_page_callback
        self.reorder_page_callback = reorder_page_callback

        self.unread_button = Gtk.MenuButton(
            tooltip_text=_("Unread Tabs"),
            halign=Gtk.Align.CENTER, valign=Gtk.Align.CENTER, visible=False
        )
        self.pages = {}
        self.set_show_tabs(False)

        if GTK_API_VERSION >= 4:
            if parent_page is not None:
                content_box = parent_page.get_first_child()
                content_box.connect("show", self.on_show_parent_page)

            self.window = self.widget.get_root()
            self.unread_button.set_has_frame(False)                        # pylint: disable=no-member
            self.unread_button.set_icon_name("emblem-important-symbolic")  # pylint: disable=no-member

            self.scroll_controller = Gtk.EventControllerScroll(flags=Gtk.EventControllerScrollFlags.BOTH_AXES)
            self.scroll_controller.connect("scroll", self.on_tab_scroll)

            tab_bar = self.widget.get_first_child()
            tab_bar.add_controller(self.scroll_controller)

            # GTK 4 workaround to prevent notebook tabs from being activated when pressing close button
            # https://gitlab.gnome.org/GNOME/gtk/-/issues/4046

            self.close_button_pressed = False

            self.gesture_click = Gtk.GestureClick()
            self.gesture_click.set_button(Gdk.BUTTON_PRIMARY)
            self.gesture_click.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
            self.gesture_click.connect("pressed", self.on_notebook_click_pressed)
            self.gesture_click.connect("released", self.on_notebook_click_released)

            self.widget.add_controller(self.gesture_click)

        else:
            if parent_page is not None:
                content_box = parent_page.get_children()[0]
                content_box.connect("show", self.on_show_parent_page)

            self.window = self.widget.get_toplevel()
            self.unread_button.set_image(Gtk.Image(icon_name="emblem-important-symbolic"))  # pylint: disable=no-member

            self.widget.add_events(Gdk.EventMask.SCROLL_MASK | Gdk.EventMask.SMOOTH_SCROLL_MASK)
            self.widget.connect("scroll-event", self.on_tab_scroll_event)

            self.widget.popup_enable()

        style_context = self.unread_button.get_style_context()
        for style_class in ("circular", "flat"):
            style_context.add_class(style_class)

        self.widget.set_action_widget(self.unread_button, Gtk.PackType.END)

        self.popup_menu_unread = PopupMenu(self.frame, connect_events=False)
        self.unread_button.set_menu_model(self.popup_menu_unread.model)
        self.unread_pages = []

    """ Tabs """

    def get_labels(self, page):

        tab_label = self.widget.get_tab_label(page)
        menu_label = self.widget.get_menu_label(page)

        return tab_label, menu_label

    def get_tab_label_inner(self, page):
        tab_label, _menu_label = self.get_labels(page)
        return tab_label.eventbox

    def set_labels(self, page, tab_label, menu_label):
        self.widget.set_tab_label(page, tab_label)
        self.widget.set_menu_label(page, menu_label)

    def set_tab_closers(self):

        for i in range(self.get_n_pages()):
            page = self.get_nth_page(i)
            tab_label, _menu_label = self.get_labels(page)
            tab_label.set_close_button_visibility(config.sections["ui"]["tabclosers"])

    def set_tab_text_colors(self):

        for i in range(self.get_n_pages()):
            page = self.get_nth_page(i)
            tab_label, _menu_label = self.get_labels(page)
            tab_label.set_text(tab_label.get_text())

    def append_page_label(self, page, tab_label, menu_label):

        self.widget.append_page_menu(page, tab_label, menu_label)

        self.set_tab_reorderable(page, True)
        self.set_show_tabs(True)

    def append_page(self, page, text, focus_callback=None, close_callback=None, full_text=None, user=None):

        if full_text is None:
            full_text = text

        label_tab = TabLabel(text, full_text, config.sections["ui"]["tabclosers"], close_callback)
        label_tab.set_tooltip_text(full_text)

        if GTK_API_VERSION >= 4:
            label_tab.gesture_click = Gtk.GestureClick()
            label_tab.add_controller(label_tab.gesture_click)  # pylint: disable=no-member

            page.get_first_child().hide()
        else:
            label_tab.gesture_click = Gtk.GestureMultiPress(widget=label_tab)

            page.get_children()[0].hide()

        label_tab.gesture_click.set_button(Gdk.BUTTON_MIDDLE)
        label_tab.gesture_click.connect("pressed", label_tab.close_callback, page)

        # menu for all tabs
        label_tab_menu = TabLabel(text)

        page.focus_callback = focus_callback
        self.append_page_label(page, label_tab, label_tab_menu)

        if user is not None:
            status = self.core.user_statuses.get(user, UserStatus.OFFLINE)
            self.set_user_status(page, text, status)

    def remove_page(self, page):

        self.widget.remove_page(self.page_num(page))

        self.remove_unread_page(page)

        if self.get_n_pages() == 0:
            self.set_show_tabs(False)

    def remove_all_pages_response(self, dialog, response_id, _data):

        if response_id == 2:
            for i in reversed(range(self.get_n_pages())):
                page = self.get_nth_page(i)
                tab_label, _menu_label = self.get_labels(page)
                tab_label.close_callback(dialog)

    def remove_all_pages(self):

        OptionDialog(
            parent=self.window,
            title=_('Close All Tabs?'),
            message=_('Do you really want to close all tabs?'),
            callback=self.remove_all_pages_response
        ).show()

    def get_current_page(self):
        return self.get_nth_page(self.widget.get_current_page())

    def set_current_page(self, page):
        page_num = self.page_num(page)
        self.widget.set_current_page(page_num)

    def get_current_page_num(self):
        return self.widget.get_current_page()

    def set_current_page_num(self, page_num):
        self.widget.set_current_page(page_num)

    def set_show_tabs(self, visible):
        self.widget.set_show_tabs(visible)

    def set_tab_expand(self, page, expand):

        tab_label, _menu_label = self.get_labels(page)

        if GTK_API_VERSION >= 4:
            self.widget.get_page(page).set_property("tab-expand", expand)
        else:
            self.widget.child_set_property(page, "tab-expand", expand)

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

    def request_tab_hilite(self, page, mentioned=False):

        if self.parent_page is not None:
            page_active = (self.get_current_page() == page)

            if self.frame.current_page_id != self.parent_page.id or not page_active:
                # Highlight top-level tab
                self.frame.notebook.request_tab_hilite(self.parent_page, mentioned)

            if page_active:
                return

            self.append_unread_page(page)

        tab_label, menu_label = self.get_labels(page)
        tab_label.request_hilite(mentioned)
        menu_label.request_hilite(mentioned)

    def remove_tab_hilite(self, page):

        tab_label, menu_label = self.get_labels(page)
        tab_label.remove_hilite()
        menu_label.remove_hilite()

        if self.parent_page is not None:
            self.remove_unread_page(page)

    def append_unread_page(self, page):

        if page in self.unread_pages:
            return

        self.unread_pages.append(page)
        self.update_unread_pages_menu()
        self.unread_button.show()

    def remove_unread_page(self, page):

        if page in self.unread_pages:
            self.unread_pages.remove(page)
            self.update_unread_pages_menu()

        if self.unread_pages:
            return

        self.unread_button.hide()

        if self.parent_page is not None:
            self.frame.notebook.remove_tab_hilite(self.parent_page)

    def set_unread_page(self, _action, _state, page):
        self.set_current_page(page)

    def update_unread_pages_menu(self):

        self.popup_menu_unread.clear()

        for page in self.unread_pages:
            tab_label, _menu_label = self.get_labels(page)
            self.popup_menu_unread.add_items(
                ("#" + tab_label.get_text(), self.set_unread_page, page)
            )

        self.popup_menu_unread.update_model()

    """ Tab User Status """

    def set_user_status(self, page, user, status):

        if status == UserStatus.AWAY:
            status_text = _("Away")

        elif status == UserStatus.ONLINE:
            status_text = _("Online")

        else:
            status_text = _("Offline")

        if not config.sections["ui"]["tab_status_icons"]:
            tab_text = "%s (%s)" % (user[:15], status_text)
        else:
            tab_text = user

        tab_label, menu_label = self.get_labels(page)

        tab_label.set_status_icon(status)
        menu_label.set_status_icon(status)

        tab_label.set_text(tab_text)
        menu_label.set_text(tab_text)

        tab_label.set_tooltip_text("%s (%s)" % (user, status_text))

    """ Signals """

    def on_remove_page(self, _notebook, new_page, _page_num):
        self.remove_unread_page(new_page)

    def on_switch_page(self, _notebook, new_page, page_num):

        if self.switch_page_callback is not None:
            self.switch_page_callback(self, new_page, page_num)

        # Hide container widget on previous page for a performance boost
        current_page = self.get_current_page()

        if GTK_API_VERSION >= 4:
            current_page.get_first_child().hide()
            new_page.get_first_child().show()
        else:
            current_page.get_children()[0].hide()
            new_page.get_children()[0].show()

        if self.parent_page is None:
            return

        # Focus the default widget on the page
        if self.frame.current_page_id == self.parent_page.id:
            GLib.idle_add(new_page.focus_callback, priority=GLib.PRIORITY_HIGH_IDLE)

        # Dismiss tab highlight
        self.remove_tab_hilite(new_page)

    def on_reorder_page(self, _notebook, page, page_num):
        if self.reorder_page_callback is not None:
            self.reorder_page_callback(self, page, page_num)

    def on_show_parent_page(self, _widget):

        curr_page = self.get_current_page()
        curr_page_num = self.get_current_page_num()

        if curr_page_num >= 0:
            self.widget.emit("switch-page", curr_page, curr_page_num)

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

        widget = self.widget.pick(pressed_x, pressed_y, Gtk.PickFlags.DEFAULT)

        if not hasattr(widget, "is_close_button"):
            return False

        self.close_button_pressed = True
        controller.set_state(Gtk.EventSequenceState.CLAIMED)
        return True

    def on_notebook_click_released(self, _controller, _num_p, pressed_x, pressed_y):

        if not self.close_button_pressed:
            return False

        widget = self.widget.pick(pressed_x, pressed_y, Gtk.PickFlags.DEFAULT)
        self.close_button_pressed = False

        if not hasattr(widget, "is_close_button"):
            return False

        if isinstance(widget, Gtk.Image):
            widget = widget.get_parent()

        widget.emit("clicked")
        return True
