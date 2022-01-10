# COPYRIGHT (C) 2020-2022 Nicotine+ Team
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
from gi.repository import Pango

from pynicotine.config import config
from pynicotine.gtkgui.widgets.ui import GUI_DIR
from pynicotine.logfacility import log


""" Global Style """


SETTINGS_PORTAL = None

if "gi.repository.Adw" not in sys.modules:
    # GNOME 42+ system-wide dark mode for vanilla GTK (no libadwaita)
    try:
        SETTINGS_PORTAL = Gio.DBusProxy.new_for_bus_sync(Gio.BusType.SESSION,
                                                         Gio.DBusProxyFlags.NONE,
                                                         None,
                                                         "org.freedesktop.portal.Desktop",
                                                         "/org/freedesktop/portal/desktop",
                                                         "org.freedesktop.portal.Settings",
                                                         None)
    except Exception:
        pass

GTK_SETTINGS = Gtk.Settings.get_default()


def read_color_scheme():

    try:
        value = SETTINGS_PORTAL.call_sync("Read",
                                          GLib.Variant(
                                              "(ss)",
                                              ("org.freedesktop.appearance",
                                               "color-scheme")),
                                          Gio.DBusCallFlags.NONE,
                                          -1,
                                          None)

        return value.get_child_value(0).get_variant().get_variant().get_uint32()

    except Exception:
        return None


def on_color_scheme_changed(_proxy, _sender_name, signal_name, parameters):

    if signal_name != "SettingChanged":
        return

    namespace = parameters.get_child_value(0).get_string()
    name = parameters.get_child_value(1).get_string()

    if (config.sections["ui"]["dark_mode"]
            or namespace != "org.freedesktop.appearance" or name != "color-scheme"):
        return

    set_dark_mode()


def set_dark_mode(force=False):

    if "gi.repository.Adw" in sys.modules:
        from gi.repository import Adw  # pylint:disable=no-name-in-module

        color_scheme = Adw.ColorScheme.FORCE_DARK if force else Adw.ColorScheme.DEFAULT
        Adw.StyleManager.get_default().set_color_scheme(color_scheme)
        return

    enabled = force

    if not force:
        color_scheme = read_color_scheme()

        if color_scheme is not None:
            enabled = bool(color_scheme)

    GTK_SETTINGS.set_property("gtk-application-prefer-dark-theme", enabled)


def set_global_font(font_name):

    if font_name == "Normal":
        GTK_SETTINGS.reset_property("gtk-font-name")
        return

    GTK_SETTINGS.set_property("gtk-font-name", font_name)


def set_use_header_bar(enabled):
    GTK_SETTINGS.set_property("gtk-dialogs-use-header", enabled)


def set_visual_settings():

    if SETTINGS_PORTAL is not None:
        SETTINGS_PORTAL.connect("g-signal", on_color_scheme_changed)

    global_font = config.sections["ui"]["globalfont"]
    set_dark_mode(config.sections["ui"]["dark_mode"])

    if global_font and global_font != "Normal":
        set_global_font(global_font)

    if sys.platform == "darwin":
        # Left align window controls on macOS
        GTK_SETTINGS.set_property("gtk-decoration-layout", "close,minimize,maximize:")

    set_use_header_bar(config.sections["ui"]["header_bar"])


def set_global_css():

    css = b"""
    /* Tweaks */

    flowbox, flowboxchild {
        /* GTK adds unwanted padding to flowbox children by default */
        border: 0;
        background: inherit;
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

    .border-top,
    .preferences-border .dialog-action-box {
        border-top: 1px solid @borders;
    }

    .border-bottom {
        border-bottom: 1px solid @borders;
    }

    .border-start:dir(ltr),
    .border-end:dir(rtl) {
        /* Use box-shadow to avoid double window border in narrow flowbox */
        box-shadow: -1px 0 0 0 @borders;
    }

    .border-end:dir(ltr),
    .border-start:dir(rtl) {
        box-shadow: 1px 0 0 0 @borders;
    }

    /* Buttons */

    .circular {
        border-radius: 9999px;
    }

    .count {
        padding-left: 10px;
        padding-right: 10px;
    }
    """

    css_gtk3_20 = b"""
    /* Tweaks (GTK 3.20+) */

    flowboxchild:disabled label {
        /* Reset 'sensitive' widget style for preferences dialog */
        color: inherit;
        opacity: inherit;
    }

    .count {
        min-width: 12px;
    }
    """

    css_gtk4 = b"""
    /* Tweaks (GTK 4+) */

    flowboxchild:disabled label {
        /* Reset 'sensitive' widget style for preferences dialog */
        filter: inherit;
    }

    treeview.normal-icons {
        /* Country flag icon size in treeviews */
        -gtk-icon-size: 21px;
    }

    .dialog-action-area {
        /* Add missing spacing to dialog action buttons */
        border-spacing: 6px;
    }

    window.dialog.message .dialog-action-area {
        /* Undo spacing change for message dialogs */
        border-spacing: unset;
    }

    .image-text-button box {
        /* Remove unwanted spacing from buttons */
        border-spacing: 0;
    }
    """

    global_css_provider = Gtk.CssProvider()

    if Gtk.get_major_version() == 4:
        Gtk.StyleContext.add_provider_for_screen = Gtk.StyleContext.add_provider_for_display
        screen = Gdk.Display.get_default()
        css = css + css_gtk3_20 + css_gtk4
    else:
        screen = Gdk.Screen.get_default()

        if not Gtk.check_version(3, 20, 0):
            css = css + css_gtk3_20

    global_css_provider.load_from_data(css)

    Gtk.StyleContext.add_provider_for_screen(
        screen, global_css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
    )


def set_global_style():
    set_visual_settings()
    set_global_css()


""" Icons """


ICONS = {}

if Gtk.get_major_version() == 4:
    ICON_THEME = Gtk.IconTheme.get_for_display(Gdk.Display.get_default())
else:
    ICON_THEME = Gtk.IconTheme.get_default()


def get_icon(icon_name):
    return ICONS.get(icon_name)


def get_flag_icon_name(country):

    country = country.lower().replace("flag_", "")

    if not country:
        return ""

    return "nplus-flag-" + country


def get_status_icon(status):

    if status == 1:
        return get_icon("away")

    if status == 2:
        return get_icon("online")

    return get_icon("offline")


def load_ui_icon(name):
    """ Load icon required by the UI """

    path = os.path.join(GUI_DIR, "icons", name + ".svg")

    if os.path.isfile(path):
        return Gio.Icon.new_for_string(path)

    return None


def load_custom_icons(names):
    """ Load custom icon theme if one is selected """

    if not config.sections["ui"].get("icontheme"):
        return False

    log.add_debug("Loading custom icons when available")
    extensions = ["jpg", "jpeg", "bmp", "png", "svg"]

    for name in names:
        path = None
        exts = extensions[:]
        loaded = False

        while not path or (exts and not loaded):
            path = os.path.expanduser(os.path.join(config.sections["ui"]["icontheme"], "%s.%s" %
                                      (name, exts.pop())))

            try:
                if os.path.isfile(path):
                    ICONS[name] = Gio.Icon.new_for_string(path)
                    loaded = True

            except Exception as error:
                log.add(_("Error loading custom icon %(path)s: %(error)s"), {
                    "path": path,
                    "error": error
                })

        if name not in ICONS:
            ICONS[name] = load_ui_icon(name)

    return True


def load_icons():
    """ Load custom icons necessary for the application to function """

    names = (
        "away",
        "online",
        "offline",
        "hilite",
        "hilite3",
        "trayicon_away",
        "trayicon_connect",
        "trayicon_disconnect",
        "trayicon_msg",
        "n",
        "notify"
    )

    """ Load icons required by the application, such as status icons """

    if not load_custom_icons(names):
        for name in names:
            ICONS[name] = load_ui_icon(name)

    """ Load local app and tray icons, if available """

    paths = (
        os.path.join(GUI_DIR, "icons"),  # Support running from folder, as well as macOS and Windows
        os.path.join(sys.prefix, "share", "icons")  # Support Python venv
    )

    for path in paths:
        if Gtk.get_major_version() == 4:
            ICON_THEME.add_search_path(path)
        else:
            ICON_THEME.append_search_path(path)


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

    for column in listview.get_columns():
        for cell in column.get_cells():
            if isinstance(cell, (Gtk.CellRendererText, Gtk.CellRendererCombo)):
                set_widget_color(cell, color)


def set_list_font(listview, font):

    for column in listview.get_columns():
        for cell in column.get_cells():
            if isinstance(cell, (Gtk.CellRendererText, Gtk.CellRendererCombo)):
                set_widget_font(cell, font)


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
