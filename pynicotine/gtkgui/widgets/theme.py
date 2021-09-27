# COPYRIGHT (C) 2020-2021 Nicotine+ Team
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
from gi.repository import Pango

from pynicotine.config import config


""" Global Style """


GTK_SETTINGS = Gtk.Settings.get_default()


def set_dark_mode(enabled):
    GTK_SETTINGS.set_property("gtk-application-prefer-dark-theme", enabled)


def set_global_font(font_name):

    if font_name == "Normal":
        GTK_SETTINGS.reset_property("gtk-font-name")
        return

    GTK_SETTINGS.set_property("gtk-font-name", font_name)


def set_use_header_bar(enabled):
    GTK_SETTINGS.set_property("gtk-dialogs-use-header", enabled)


def set_visual_settings():

    dark_mode = config.sections["ui"]["dark_mode"]
    global_font = config.sections["ui"]["globalfont"]

    if dark_mode:
        set_dark_mode(dark_mode)

    if global_font and global_font != "Normal":
        set_global_font(global_font)

    if sys.platform == "darwin":
        # Left align window controls on macOS
        GTK_SETTINGS.set_property("gtk-decoration-layout", "close,minimize,maximize:")

        # Disable header bar in macOS for now due to GTK 3 performance issues
        set_use_header_bar(False)
        return

    set_use_header_bar(config.sections["ui"]["header_bar"])


def set_global_css():

    css = b"""
    /* Tweaks */

    flowboxchild {
        /* GTK adds unwanted padding to flowbox children by default */
        padding: 0;
    }

    scrollbar {
        /* Workaround for themes breaking scrollbar hitbox with margins */
        margin: 0;
    }

    .preferences .dialog-action-box {
        /* Add missing spacing to dialog action buttons */
        padding: 6px;
    }

    /* Borders */

    .background-border {
        background: @borders;
    }

    .border-top {
        border-top: 1px solid @borders;
    }

    .border-bottom {
        border-bottom: 1px solid @borders;
    }

    .preferences-border .dialog-action-box {
        border-top: 1px solid @borders;
    }
    """

    css_gtk4 = b"""
    /* Tweaks */

    .dialog-action-area {
        /* Add missing spacing to dialog action buttons */
        border-spacing: 6px;
    }

    menubutton box {
        /* Remove unwanted spacing from menu buttons */
        border-spacing: 0;
    }
    """

    global_css_provider = Gtk.CssProvider()

    if Gtk.get_major_version() == 4:
        Gtk.StyleContext.add_provider_for_screen = Gtk.StyleContext.add_provider_for_display
        screen = Gdk.Display.get_default()
        css = css + css_gtk4
    else:
        screen = Gdk.Screen.get_default()

    global_css_provider.load_from_data(css)

    Gtk.StyleContext.add_provider_for_screen(
        screen, global_css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
    )


def set_global_style():
    set_visual_settings()
    set_global_css()


""" Widget Fonts and Colors """


def get_user_status_color(status):

    if status == 1:
        color = "useraway"
    elif status == 2:
        color = "useronline"
    else:
        color = "useroffline"

    return color


def parse_color_string(color_string):
    """ Take a color string, e.g. BLUE, and return a HEX color code """

    if color_string:
        color_rgba = Gdk.RGBA()

        if color_rgba.parse(color_string):
            color_hex = "#%02X%02X%02X" % (
                round(color_rgba.red * 255), round(color_rgba.green * 255), round(color_rgba.blue * 255))
            return color_hex

    return None


def set_list_color(listview, color):

    for c in listview.get_columns():
        for r in c.get_cells():
            if isinstance(r, (Gtk.CellRendererText, Gtk.CellRendererCombo)):
                set_widget_color(r, color)


def set_list_font(listview, font):

    for c in listview.get_columns():
        for r in c.get_cells():
            if isinstance(r, (Gtk.CellRendererText, Gtk.CellRendererCombo)):
                set_widget_font(r, font)


def set_widget_color(widget, color):

    if color:
        widget.set_property("foreground", color)
    else:
        widget.set_property("foreground-set", False)


css_providers = {}


def set_widget_fg_bg_css(widget, bg_color=None, fg_color=None):

    class_name = "widget_custom_color"
    css = "." + class_name + " {"

    bg_color_hex = parse_color_string(bg_color)
    fg_color_hex = parse_color_string(fg_color)

    if bg_color_hex is not None:
        css += "background: " + bg_color_hex + ";"

    if fg_color_hex is not None:
        css += "color: " + fg_color_hex + ";"

    css += "}"

    context = widget.get_style_context()

    if widget not in css_providers:
        css_providers[widget] = Gtk.CssProvider()
        context.add_provider(css_providers[widget], Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        context.add_class(class_name)

    css_providers[widget].load_from_data(css.encode('utf-8'))


def set_widget_font(widget, font):
    widget.set_property("font", font)


def update_tag_visuals(tag, color=None, font=None):

    config_ui = config.sections["ui"]

    if font:
        set_widget_font(tag, config_ui[font])

    if color is None:
        return

    set_widget_color(tag, config_ui[color])

    # URLs
    if color == "urlcolor":
        tag.set_property("underline", Pango.Underline.SINGLE)

    # Hotspots
    if color in ("useraway", "useronline", "useroffline"):

        usernamestyle = config_ui["usernamestyle"]

        if usernamestyle == "bold":
            tag.set_property("weight", Pango.Weight.BOLD)
        else:
            tag.set_property("weight", Pango.Weight.NORMAL)

        if usernamestyle == "italic":
            tag.set_property("style", Pango.Style.ITALIC)
        else:
            tag.set_property("style", Pango.Style.NORMAL)

        if usernamestyle == "underline":
            tag.set_property("underline", Pango.Underline.SINGLE)
        else:
            tag.set_property("underline", Pango.Underline.NONE)


def update_widget_visuals(widget, list_font_target="listfont"):

    from pynicotine.gtkgui.widgets.textview import TextView
    config_ui = config.sections["ui"]

    if isinstance(widget, Gtk.ComboBox) and widget.get_has_entry() or isinstance(widget, Gtk.Entry):
        if isinstance(widget, Gtk.ComboBox):
            widget = widget.get_child()

        set_widget_fg_bg_css(
            widget,
            bg_color=config_ui["textbg"],
            fg_color=config_ui["inputcolor"]
        )

    elif isinstance(widget, TextView):
        # Update URL tag colors
        widget.update_tags()

    elif isinstance(widget, Gtk.TreeView):
        set_list_color(widget, config_ui["search"])
        set_list_font(widget, config_ui[list_font_target])
