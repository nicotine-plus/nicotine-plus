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

import sys

from collections import deque

from gi.repository import Gdk
from gi.repository import GLib
from gi.repository import Gtk

from pynicotine.config import config
from pynicotine.core import core
from pynicotine.gtkgui.application import GTK_API_VERSION
from pynicotine.gtkgui.widgets.accelerator import Accelerator
from pynicotine.gtkgui.widgets.dialogs import OptionDialog
from pynicotine.gtkgui.widgets.popupmenu import PopupMenu
from pynicotine.gtkgui.widgets.theme import USER_STATUS_ICON_NAMES
from pynicotine.gtkgui.widgets.theme import add_css_class
from pynicotine.gtkgui.widgets.theme import remove_css_class
from pynicotine.slskmessages import UserStatus


class TabLabel:

    def __init__(self, label, full_text=None, close_button_visible=False, close_callback=None):

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
            self.eventbox.add_events(int(Gdk.EventMask.SCROLL_MASK | Gdk.EventMask.SMOOTH_SCROLL_MASK))

        self.box = Gtk.Box(spacing=6, visible=True)

        self.label = Gtk.Label(halign=Gtk.Align.START, hexpand=True, single_line_mode=True, visible=True)
        self.full_text = full_text
        self.set_tooltip_text(full_text)
        self.set_text(label)

        self.close_button = None
        self.close_button_visible = close_button_visible and close_callback
        self.close_callback = close_callback

        if close_callback:
            self.gesture_click.set_button(Gdk.BUTTON_MIDDLE)
            self.gesture_click.connect("pressed", close_callback)

        self.start_icon = Gtk.Image(visible=False)
        self.end_icon = Gtk.Image(visible=False)

        self._pack_children()

    def destroy(self):
        self.__dict__.clear()

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
                int(Gdk.EventMask.SCROLL_MASK | Gdk.EventMask.SMOOTH_SCROLL_MASK))

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

        # Chat mentions have priority over normal notifications
        if not self.is_important:
            self.is_important = is_important

        icon_name = "nplus-tab-highlight" if self.is_important else "nplus-tab-changed"

        if self.end_icon.get_icon_name() == icon_name:
            return

        if self.is_important:
            remove_css_class(self.box, "notebook-tab-changed")
            add_css_class(self.box, "notebook-tab-highlight")
        else:
            remove_css_class(self.box, "notebook-tab-highlight")
            add_css_class(self.box, "notebook-tab-changed")

        add_css_class(self.label, "bold")

        icon_args = (Gtk.IconSize.BUTTON,) if GTK_API_VERSION == 3 else ()  # pylint: disable=no-member

        self.end_icon.set_from_icon_name(icon_name, *icon_args)
        self.end_icon.set_visible(True)
        add_css_class(self.end_icon, "colored-icon")

    def remove_changed(self):

        if not self.end_icon.get_icon_name():
            return

        self.is_important = False

        remove_css_class(self.box, "notebook-tab-changed")
        remove_css_class(self.box, "notebook-tab-highlight")
        remove_css_class(self.label, "bold")

        icon_name = None
        icon_args = (Gtk.IconSize.BUTTON,) if GTK_API_VERSION == 3 else ()  # pylint: disable=no-member

        self.end_icon.set_from_icon_name(icon_name, *icon_args)
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

        icon_args = (Gtk.IconSize.BUTTON,) if GTK_API_VERSION == 3 else ()  # pylint: disable=no-member

        self.start_icon.set_from_icon_name(icon_name, *icon_args)
        self.start_icon.set_visible(True)

    def set_tooltip_text(self, text):

        text = text.strip() if text else None

        if self.container.get_tooltip_text() == text:
            return

        # Hide widget to keep tooltips for other widgets visible
        self.container.set_visible(False)
        self.container.set_tooltip_text(text)
        self.container.set_visible(True)

    def set_text(self, text):
        self.label.set_text(text.strip())

    def get_text(self):
        return self.label.get_text()


class IconNotebook:
    """This class extends the functionality of a Gtk.Notebook widget. On top of
    what a Gtk.Notebook provides:

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
        self.switch_page_handler = None
        self.reorder_page_handler = None

        self.pages = {}
        self.tab_labels = {}
        self.unread_pages = {}
        self.recently_removed_pages = deque(maxlen=5)  # Low limit to prevent excessive server traffic
        self.scroll_x = self.scroll_y = 0
        self.should_focus_page = True

        self.widget = Gtk.Notebook(enable_popup=False, scrollable=True, show_border=False, visible=True)

        self.pages_button_container = Gtk.Box(halign=Gtk.Align.CENTER, visible=(self.parent_page is not None))
        self.pages_button = Gtk.MenuButton(halign=Gtk.Align.CENTER, valign=Gtk.Align.CENTER, visible=True)
        self.widget.set_action_widget(self.pages_button_container, Gtk.PackType.END)

        if parent_page is not None:
            content_box = next(iter(parent_page))
            content_box.connect("show", self.on_show_parent_page)

        if GTK_API_VERSION >= 4:
            parent.append(self.widget)

            self.pages_button.set_has_frame(False)                                 # pylint: disable=no-member
            self.pages_button.set_create_popup_func(self.on_pages_button_pressed)  # pylint: disable=no-member
            self.pages_button_container.append(self.pages_button)                  # pylint: disable=no-member

            self.scroll_controller = Gtk.EventControllerScroll(
                flags=int(Gtk.EventControllerScrollFlags.BOTH_AXES | Gtk.EventControllerScrollFlags.DISCRETE)
            )
            self.scroll_controller.connect("scroll", self.on_tab_scroll)

            tab_bar = next(iter(self.widget))
            tab_bar.add_controller(self.scroll_controller)

            # GTK 4 workaround to prevent notebook tabs from being activated when pressing close button
            # https://gitlab.gnome.org/GNOME/gtk/-/issues/4046

            self.close_button_pressed = False

            self.gesture_click = Gtk.GestureClick(
                button=Gdk.BUTTON_PRIMARY, propagation_phase=Gtk.PropagationPhase.CAPTURE
            )
            self.gesture_click.connect("pressed", self.on_notebook_click_pressed)
            self.gesture_click.connect("released", self.on_notebook_click_released)

            self.widget.add_controller(self.gesture_click)                         # pylint: disable=no-member

        else:
            parent.add(self.widget)

            self.pages_button.set_use_popover(False)            # pylint: disable=no-member
            self.pages_button.connect("toggled", self.on_pages_button_pressed)
            self.pages_button_container.add(self.pages_button)  # pylint: disable=no-member

            self.widget.add_events(  # pylint: disable=no-member
                int(Gdk.EventMask.SCROLL_MASK | Gdk.EventMask.SMOOTH_SCROLL_MASK))
            self.widget.connect("scroll-event", self.on_tab_scroll_event)

        for style_class in ("circular", "flat"):
            add_css_class(self.pages_button, style_class)

        Accelerator("Left", self.widget, self.on_arrow_accelerator)
        Accelerator("Right", self.widget, self.on_arrow_accelerator)

        self.popup_menu_pages = PopupMenu(self.window.application)
        self.update_pages_menu_button()

        self.popup_menu_pages.set_menu_button(self.pages_button)

    def destroy(self):

        if self.switch_page_handler is not None:
            self.widget.disconnect(self.switch_page_handler)

        if self.reorder_page_handler is not None:
            self.widget.disconnect(self.reorder_page_handler)

        for i in reversed(range(self.get_n_pages())):
            page = self.get_nth_page(i)
            self.remove_page(page)

        self.__dict__.clear()

    def grab_focus(self):
        self.widget.grab_focus()

    # Tabs #

    def freeze(self):
        """Use when adding/removing many tabs at once, to stop unnecessary updates."""

        self.widget.set_visible(False)
        self.widget.set_show_tabs(False)
        self.widget.set_scrollable(False)

    def unfreeze(self):

        self.widget.set_visible(True)
        self.widget.set_show_tabs(True)
        self.widget.set_scrollable(True)

    def get_tab_label(self, page):
        return self.tab_labels.get(page)

    def get_tab_label_inner(self, page):
        return self.get_tab_label(page).eventbox

    def set_tab_closers(self):

        for i in range(self.get_n_pages()):
            page = self.get_nth_page(i)
            tab_label = self.get_tab_label(page)
            tab_label.set_close_button_visibility(config.sections["ui"]["tabclosers"])

    def append_page(self, page, text, focus_callback=None, close_callback=None, user=None):
        self.insert_page(page, text, focus_callback, close_callback, user, position=-1)

    def insert_page(self, page, text, focus_callback=None, close_callback=None, user=None,
                    position=None):

        full_text = text
        text = (text[:25] + "…") if len(text) > 25 else text

        self.tab_labels[page] = tab_label = TabLabel(
            text, full_text, close_button_visible=config.sections["ui"]["tabclosers"], close_callback=close_callback)

        if focus_callback:
            page.focus_callback = focus_callback

        first_child = next(iter(page))
        first_child.set_visible(False)

        if position is None:
            # Open new tab adjacent to current tab
            position = self.widget.get_current_page() + 1

        self.widget.insert_page(page, None, position)
        self.widget.set_tab_label(page, tab_label.container)  # Tab label widget leaks when passed to insert_page()
        self.set_tab_reorderable(page, True)
        self.parent.set_visible(True)

        if user is not None:
            status = core.users.statuses.get(user, UserStatus.OFFLINE)
            self.set_user_status(page, text, status)

    def prepend_page(self, page, text, focus_callback=None, close_callback=None, user=None):
        self.insert_page(page, text, focus_callback, close_callback, user, position=0)

    def restore_removed_page(self, *_args):
        if self.recently_removed_pages:
            self.on_restore_removed_page(page_args=self.recently_removed_pages.pop())

    def remove_page(self, page, page_args=None):

        self.widget.remove_page(self.page_num(page))
        self._remove_unread_page(page)
        self.popup_menu_pages.clear()

        if hasattr(page, "focus_callback"):
            del page.focus_callback

        tab_label = self.tab_labels.pop(page)
        tab_label.destroy()

        if page_args:
            # Allow for restoring page after closing it
            self.recently_removed_pages.append(page_args)

        if self.parent_page is not None and self.get_n_pages() <= 0:
            if self.window.current_page_id == self.parent_page.id:
                self.window.notebook.grab_focus()

            self.parent.set_visible(False)

    def remove_all_pages(self, *_args):

        OptionDialog(
            parent=self.window,
            title=_("Close All Tabs?"),
            message=_("Do you really want to close all tabs?"),
            destructive_response_id="ok",
            callback=self._on_remove_all_pages
        ).present()

    def _update_pages_menu_button(self, icon_name, tooltip_text):

        if self.pages_button.get_tooltip_text() == tooltip_text:
            return

        if GTK_API_VERSION >= 4:
            self.pages_button.set_icon_name(icon_name)                   # pylint: disable=no-member
        else:
            self.pages_button.set_image(Gtk.Image(icon_name=icon_name))  # pylint: disable=no-member

        # Hide widget to keep tooltips for other widgets visible
        self.pages_button.set_visible(False)
        self.pages_button.set_tooltip_text(tooltip_text)
        self.pages_button.set_visible(True)

    def update_pages_menu_button(self):

        if self.unread_pages:
            icon_name = "emblem-important-symbolic"
            tooltip_text = _("%i Unread Tab(s)") % len(self.unread_pages)
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
            self.widget.get_page(page).props.tab_expand = expand        # pylint: disable=no-member
        else:
            self.widget.child_set_property(page, "tab-expand", expand)  # pylint: disable=no-member

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

    # Tab Highlights #

    def request_tab_changed(self, page, is_important=False, is_quiet=False):

        if self.parent_page is not None:
            has_tab_changed = False
            is_current_parent = (self.window.current_page_id == self.parent_page.id)
            is_current_page = (self.get_current_page() == page)

            if is_current_parent and is_current_page:
                return has_tab_changed

            if not is_quiet or is_important:
                # Highlight top-level tab, but don't for global feed unless mentioned
                self.window.notebook.request_tab_changed(self.parent_page, is_important)
                has_tab_changed = self._append_unread_page(page, is_important)
        else:
            has_tab_changed = True

        tab_label = self.get_tab_label(page)
        tab_label.request_changed(is_important)

        return has_tab_changed

    def remove_tab_changed(self, page):

        tab_label = self.get_tab_label(page)
        tab_label.remove_changed()

        if self.parent_page is not None:
            self._remove_unread_page(page)

    def _append_unread_page(self, page, is_important=False):

        # Remove existing page and move it to the end of the dict
        is_currently_important = self.unread_pages.pop(page, None)

        if is_currently_important and not is_important:
            # Important pages are persistent
            self.unread_pages[page] = is_currently_important
            return False

        self.unread_pages[page] = is_important

        if is_currently_important == is_important:
            return False

        self.update_pages_menu_button()
        return True

    def _remove_unread_page(self, page):

        if page not in self.unread_pages:
            return

        important_page_removed = self.unread_pages.pop(page)
        self.update_pages_menu_button()

        if self.parent_page is None:
            return

        if not self.unread_pages:
            self.window.notebook.remove_tab_changed(self.parent_page)
            return

        # No important unread pages left, reset top-level tab highlight
        if important_page_removed and not any(is_important for is_important in self.unread_pages.values()):
            self.window.notebook.remove_tab_changed(self.parent_page)
            self.window.notebook.request_tab_changed(self.parent_page, is_important=False)

    # Tab User Status #

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

    # Signals #

    def emit_switch_page_signal(self):

        curr_page = self.get_current_page()
        curr_page_num = self.get_current_page_num()

        if curr_page_num >= 0:
            self.widget.emit("switch-page", curr_page, curr_page_num)

    def connect_signals(self):

        self.reorder_page_handler = self.widget.connect("page-reordered", self.on_reorder_page)
        self.switch_page_handler = self.widget.connect("switch-page", self.on_switch_page)
        self.widget.connect("page-removed", self.on_remove_page)

        if self.parent_page is None:
            # Show active page and focus default widget
            self.emit_switch_page_signal()

    def on_focus_page(self, page):

        if not hasattr(page, "focus_callback"):
            return

        if not page.focus_callback():
            # Page didn't grab focus, fall back to the notebook
            self.widget.grab_focus()

    def on_restore_removed_page(self, page_args):
        raise NotImplementedError

    def on_remove_page(self, _notebook, new_page, _page_num):
        self._remove_unread_page(new_page)

    def _on_remove_all_pages(self, *args):

        self.freeze()
        self.on_remove_all_pages(args)
        self.unfreeze()

        # Don't allow restoring tabs after removing all
        self.recently_removed_pages.clear()

    def on_remove_all_pages(self, *_args):
        raise NotImplementedError

    def on_switch_page(self, _notebook, new_page, page_num):

        if self.switch_page_callback is not None:
            self.switch_page_callback(self, new_page, page_num)

        # Hide container widget on previous page for a performance boost
        current_page = self.get_current_page()
        current_first_child = next(iter(current_page))
        new_first_child = next(iter(new_page))

        current_first_child.set_visible(False)
        new_first_child.set_visible(True)

        # Focus the default widget on the page
        if (self.should_focus_page
                and (self.parent_page is None or self.window.current_page_id == self.parent_page.id
                     and self.window.notebook.should_focus_page)):
            GLib.idle_add(self.on_focus_page, new_page, priority=GLib.PRIORITY_HIGH_IDLE)

        # Dismiss tab highlight
        if self.parent_page is not None:
            self.remove_tab_changed(new_page)

        self.should_focus_page = True

    def on_reorder_page(self, _notebook, page, page_num):
        if self.reorder_page_callback is not None:
            self.reorder_page_callback(self, page, page_num)

    def on_show_page(self, _action, _state, page):
        self.set_current_page(page)

    def on_show_parent_page(self, *_args):
        self.emit_switch_page_signal()

    def on_pages_button_pressed(self, *_args):

        if GTK_API_VERSION == 3 and not self.pages_button.get_active():
            return

        self.popup_menu_pages.clear()

        # Unread pages (most recently changed first)
        for page in reversed(list(self.unread_pages)):
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

            if page in self.unread_pages:
                continue

            tab_label = self.get_tab_label(page)
            self.popup_menu_pages.add_items(
                ("#" + tab_label.get_text(), self.on_show_page, page)
            )

        self.popup_menu_pages.add_items(
            ("", None),
            ("#" + _("Re_open Closed Tab"), self.restore_removed_page),
            ("#" + _("Close All Tabs…"), self.remove_all_pages)
        )

        self.popup_menu_pages.update_model()
        self.popup_menu_pages.actions[_("Re_open Closed Tab")].set_enabled(bool(self.recently_removed_pages))

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

        # Simulate discrete scrolling with touchpad in GTK 3
        self.scroll_x += scroll_x
        self.scroll_y += scroll_y

        if self.scroll_x >= 1 or self.scroll_y >= 1:
            self.next_page()
            self.scroll_x = self.scroll_y = 0

        elif self.scroll_x <= -1 or self.scroll_y <= -1:
            self.prev_page()
            self.scroll_x = self.scroll_y = 0

        return True

    def on_arrow_accelerator(self, *_args):
        """Left, Right - disable page focus callback when moving through tabs."""
        self.should_focus_page = False

    # Signals (GTK 4) #

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
