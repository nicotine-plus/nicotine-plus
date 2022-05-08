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
from gi.repository import Gtk

from pynicotine.gtkgui.widgets.dialogs import OptionDialog
from pynicotine.gtkgui.widgets.popupmenu import PopupMenu
from pynicotine.gtkgui.widgets.theme import get_icon
from pynicotine.gtkgui.widgets.theme import get_status_icon
from pynicotine.gtkgui.widgets.theme import parse_color_string
from pynicotine.config import config


""" Icon Notebook """


class TabLabel(Gtk.Box):

    def __init__(self, label="", full_text="", close_button_visible=False, close_callback=None):

        Gtk.Box.__init__(self, hexpand=False, visible=True)

        self.highlighted = False
        self.mentioned = False
        self.centered = False
        self.gesture_click = None

        if Gtk.get_major_version() >= 4:
            self.eventbox = Gtk.Box()
        else:
            self.eventbox = Gtk.EventBox(visible=True)
            self.eventbox.add_events(Gdk.EventMask.SCROLL_MASK | Gdk.EventMask.SMOOTH_SCROLL_MASK)

        self.box = Gtk.Box(spacing=6, visible=True)

        self.label = Gtk.Label(halign=Gtk.Align.START, hexpand=True, visible=True)
        self.full_text = full_text
        self.set_text(label)

        self.close_button = None
        self.close_button_visible = close_button_visible
        self.close_callback = close_callback

        self.start_icon = Gtk.Image(visible=False)
        self.start_icon_data = None

        self.end_icon = Gtk.Image(visible=False)
        self.end_icon_data = None

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

        if Gtk.get_major_version() >= 4:
            self.close_button = Gtk.Button.new_from_icon_name("window-close-symbolic")
            self.append(self.close_button)  # pylint: disable=no-member

            # GTK 4 workaround to prevent notebook tabs from being activated when pressing close button
            gesture_click = Gtk.GestureClick()
            gesture_click.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
            gesture_click.connect(
                "pressed", lambda controller, *args: controller.set_state(Gtk.EventSequenceState.CLAIMED))
            self.close_button.add_controller(gesture_click)

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

        if Gtk.get_major_version() >= 4:
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

        if self.mentioned:
            icon_data = get_icon("hilite")
        else:
            icon_data = get_icon("hilite3")

        if icon_data is self.end_icon_data:
            return

        self.end_icon_data = icon_data
        self.end_icon.set_property("gicon", icon_data)
        self.end_icon.show()

    def remove_hilite(self):

        self.highlighted = False
        self.mentioned = False

        self._set_text_color(config.sections["ui"]["tab_default"])

        self.end_icon_data = None
        self.end_icon.set_property("gicon", None)
        self.end_icon.hide()

    def set_status_icon(self, status):

        icon_data = get_status_icon(status) or get_status_icon(0)

        if icon_data is self.start_icon_data:
            return

        self.start_icon_data = icon_data
        self.start_icon.set_property("gicon", icon_data)
        self.start_icon.set_visible(config.sections["ui"]["tab_status_icons"])

    def set_start_icon_name(self, icon_name):
        self.start_icon.set_property("icon-name", icon_name)
        self.start_icon.show()

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

    def __init__(self, frame, core, notebook, parent_page):

        self.notebook = notebook
        self.notebook.set_show_tabs(False)
        self.notebook.connect("page-removed", self.on_remove_page)
        self.notebook.connect("switch-page", self.on_switch_page)

        self.frame = frame
        self.core = core
        self.parent_page = parent_page
        self.unread_button = Gtk.MenuButton(
            tooltip_text=_("Unread Tabs"),
            halign=Gtk.Align.CENTER, valign=Gtk.Align.CENTER, visible=False
        )
        self.pages = {}

        if Gtk.get_major_version() >= 4:
            self.window = self.notebook.get_root()
            self.unread_button.set_has_frame(False)                        # pylint: disable=no-member
            self.unread_button.set_icon_name("emblem-important-symbolic")  # pylint: disable=no-member

            # GTK 4 workaround to prevent notebook tabs from being activated when pressing close button
            controllers = self.notebook.observe_controllers()

            for num in range(controllers.get_n_items()):
                item = controllers.get_item(num)

                if isinstance(item, Gtk.GestureClick):
                    item.set_propagation_phase(Gtk.PropagationPhase.BUBBLE)
                    break

            self.scroll_controller = Gtk.EventControllerScroll(flags=Gtk.EventControllerScrollFlags.BOTH_AXES)
            self.scroll_controller.connect("scroll", self.on_tab_scroll)

            tab_bar = self.notebook.get_first_child()
            tab_bar.add_controller(self.scroll_controller)

        else:
            self.window = self.notebook.get_toplevel()
            self.unread_button.set_image(Gtk.Image(icon_name="emblem-important-symbolic"))  # pylint: disable=no-member

            self.notebook.add_events(Gdk.EventMask.SCROLL_MASK | Gdk.EventMask.SMOOTH_SCROLL_MASK)
            self.notebook.connect("scroll-event", self.on_tab_scroll_event)

        style_context = self.unread_button.get_style_context()
        for style_class in ("circular", "flat"):
            style_context.add_class(style_class)

        self.notebook.set_action_widget(self.unread_button, Gtk.PackType.END)

        self.popup_menu_unread = PopupMenu(self.frame, connect_events=False)
        self.unread_button.set_menu_model(self.popup_menu_unread.model)
        self.unread_pages = []

        self.notebook.popup_enable()

    """ Tabs """

    def get_labels(self, page):
        tab_label = self.notebook.get_tab_label(page)
        menu_label = self.notebook.get_menu_label(page)

        return tab_label, menu_label

    def get_tab_label_inner(self, page):
        return self.notebook.get_tab_label(page).eventbox

    def set_tab_closers(self):

        for i in range(self.notebook.get_n_pages()):
            page = self.notebook.get_nth_page(i)
            tab_label, _menu_label = self.get_labels(page)
            tab_label.set_close_button_visibility(config.sections["ui"]["tabclosers"])

    def set_tab_text_colors(self):

        for i in range(self.notebook.get_n_pages()):
            page = self.notebook.get_nth_page(i)
            tab_label, _menu_label = self.get_labels(page)
            tab_label.set_text(tab_label.get_text())

    def append_page(self, page, text, close_callback=None, full_text=None, user=None):

        if full_text is None:
            full_text = text

        label_tab = TabLabel(text, full_text, config.sections["ui"]["tabclosers"], close_callback)
        label_tab.set_tooltip_text(full_text)

        if Gtk.get_major_version() >= 4:
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

        self.notebook.append_page_menu(page, label_tab, label_tab_menu)

        if user is not None:
            status = 0

            if user in self.core.user_statuses:
                status = self.core.user_statuses[user] or 0

            self.set_user_status(page, text, status)

        self.notebook.set_tab_reorderable(page, True)
        self.notebook.set_show_tabs(True)

    def remove_page(self, page):

        self.notebook.remove_page(self.page_num(page))

        self.remove_unread_page(page)

        if self.notebook.get_n_pages() == 0:
            self.notebook.set_show_tabs(False)

    def remove_all_pages_response(self, dialog, response_id, _data):

        dialog.destroy()

        if response_id == 2:
            for i in reversed(range(self.notebook.get_n_pages())):
                page = self.notebook.get_nth_page(i)
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
        return self.notebook.get_current_page()

    def set_current_page(self, page_num):
        return self.notebook.set_current_page(page_num)

    def set_tab_pos(self, pos):
        self.notebook.set_tab_pos(pos)

    def get_n_pages(self):
        return self.notebook.get_n_pages()

    def get_nth_page(self, page_num):
        return self.notebook.get_nth_page(page_num)

    def page_num(self, page):
        return self.notebook.page_num(page)

    def next_page(self):
        return self.notebook.next_page()

    def prev_page(self):
        return self.notebook.prev_page()

    """ Tab Highlights """

    def request_tab_hilite(self, page, mentioned=False):

        page_active = (self.get_nth_page(self.get_current_page()) == page)

        if self.frame.current_page_id != self.parent_page.id or not page_active:
            # Highlight top-level tab
            self.frame.request_tab_hilite(self.parent_page, mentioned)

        if page_active:
            return

        tab_label, menu_label = self.get_labels(page)
        tab_label.request_hilite(mentioned)
        menu_label.request_hilite(mentioned)

        self.append_unread_page(page)

    def remove_tab_hilite(self, page):

        tab_label, menu_label = self.get_labels(page)
        tab_label.remove_hilite()
        menu_label.remove_hilite()

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

        if not self.unread_pages:
            self.unread_button.hide()
            self.frame.remove_tab_hilite(self.parent_page)

    def set_unread_page(self, _action, _state, page):
        self.notebook.set_current_page(self.page_num(page))

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

        if status is None:
            return

        if status == 1:
            status_text = _("Away")
        elif status == 2:
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

    def on_switch_page(self, _notebook, new_page, _page_num):

        # Hide container widget on previous page for a performance boost
        current_page = self.get_nth_page(self.get_current_page())

        if Gtk.get_major_version() >= 4:
            current_page.get_first_child().hide()
            new_page.get_first_child().show()
        else:
            current_page.get_children()[0].hide()
            new_page.get_children()[0].show()

        # Dismiss tab highlight
        self.remove_tab_hilite(new_page)

    def on_tab_scroll_event(self, _widget, event):

        current_page = self.get_nth_page(self.get_current_page())

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
