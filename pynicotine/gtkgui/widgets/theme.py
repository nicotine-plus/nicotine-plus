# COPYRIGHT (C) 2020-2022 Nicotine+ Contributors
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
from pynicotine.gtkgui.application import GTK_API_VERSION
from pynicotine.gtkgui.application import GTK_GUI_DIR
from pynicotine.logfacility import log
from pynicotine.slskmessages import UserStatus
from pynicotine.utils import encode_path


""" Global Style """


GTK_SETTINGS = Gtk.Settings.get_default()

if not hasattr(GTK_SETTINGS, "reset_property"):
    SYSTEM_FONT = GTK_SETTINGS.get_property("gtk-font-name")
    SYSTEM_ICON_THEME = GTK_SETTINGS.get_property("gtk-icon-theme-name")

USE_LIBADWAITA = ("gi.repository.Adw" in sys.modules)
USE_COLOR_SCHEME_PORTAL = (sys.platform not in ("win32", "darwin") and not USE_LIBADWAITA)


if USE_COLOR_SCHEME_PORTAL:
    # GNOME 42+ system-wide dark mode for GTK without libadwaita
    SETTINGS_PORTAL = None

    class ColorScheme:
        NO_PREFERENCE = 0
        PREFER_DARK = 1
        PREFER_LIGHT = 2

    def read_color_scheme():

        try:
            result = SETTINGS_PORTAL.call_sync(
                "Read", GLib.Variant("(ss)", ("org.freedesktop.appearance", "color-scheme")),
                Gio.DBusCallFlags.NONE, -1, None
            )

            return result.unpack()[0]

        except Exception as error:
            log.add_debug("Cannot read color scheme, falling back to GTK theme preference: %s", error)
            return None

    def on_color_scheme_changed(_proxy, _sender_name, signal_name, parameters):

        if signal_name != "SettingChanged":
            return

        namespace, name, color_scheme, *_unused = parameters.unpack()

        if (config.sections["ui"]["dark_mode"]
                or namespace != "org.freedesktop.appearance" or name != "color-scheme"):
            return

        set_dark_mode(color_scheme == ColorScheme.PREFER_DARK)

    try:
        SETTINGS_PORTAL = Gio.DBusProxy.new_for_bus_sync(
            Gio.BusType.SESSION, Gio.DBusProxyFlags.NONE, None,
            "org.freedesktop.portal.Desktop", "/org/freedesktop/portal/desktop",
            "org.freedesktop.portal.Settings", None
        )
        SETTINGS_PORTAL.connect("g-signal", on_color_scheme_changed)

    except Exception as portal_error:
        log.add_debug("Cannot start color scheme settings portal, falling back to GTK theme preference: %s",
                      portal_error)
        USE_PORTAL_COLOR_SCHEME = None


def set_dark_mode(enabled):

    if USE_LIBADWAITA:
        from gi.repository import Adw  # pylint:disable=no-name-in-module

        color_scheme = Adw.ColorScheme.FORCE_DARK if enabled else Adw.ColorScheme.DEFAULT
        Adw.StyleManager.get_default().set_color_scheme(color_scheme)
        return

    if USE_COLOR_SCHEME_PORTAL and not enabled:
        color_scheme = read_color_scheme()

        if color_scheme is not None:
            enabled = (color_scheme == ColorScheme.PREFER_DARK)

    GTK_SETTINGS.set_property("gtk-application-prefer-dark-theme", enabled)


def set_global_font(font_name):

    if font_name == "Normal":
        if hasattr(GTK_SETTINGS, "reset_property"):
            GTK_SETTINGS.reset_property("gtk-font-name")
            return

        font_name = SYSTEM_FONT

    GTK_SETTINGS.set_property("gtk-font-name", font_name)


def set_use_header_bar(enabled):
    GTK_SETTINGS.set_property("gtk-dialogs-use-header", enabled)


def set_visual_settings():

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

    .generic-dialog .dialog-action-area {
        /* Add missing spacing to dialog action buttons */
        padding: 0;
        margin: 0 6px;
    }

    .generic-dialog .dialog-action-area button {
        /* Add missing spacing to dialog action buttons */
        margin: 6px 0;
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

    .count {
        padding-left: 10px;
        padding-right: 10px;
    }

    /* Headings */

    .title-1 {
        font-weight: 800;
        font-size: 20pt;
    }

    .title-2 {
        font-weight: 800;
        font-size: 15pt;
    }
    """

    css_gtk3 = b"""
    /* Tweaks (GTK 3) */

    treeview {
        /* Set spacing for dropdown menu items */
        -GtkTreeView-horizontal-separator: 12;
        -GtkTreeView-vertical-separator: 6;
    }

    filechooser treeview,
    fontchooser treeview {
        /* Restore default item spacing in GTK choosers */
        -GtkTreeView-horizontal-separator: 2;
        -GtkTreeView-vertical-separator: 2;
    }

    .treeview-spacing {
        /* Disable GTK's built-in item spacing in custom treeviews */
        -GtkTreeView-horizontal-separator: 0;
        -GtkTreeView-vertical-separator: 0;
    }
    """

    css_gtk3_20 = b"""
    /* Tweaks (GTK 3.20+) */

    .count {
        min-width: 12px;
    }
    """

    css_gtk3_22_28 = b"""
    /* Tweaks (GTK 3.22.28+) */

    .dropdown-scrollbar {
        /* Enable dropdown list with a scrollbar */
        -GtkComboBox-appears-as-list: 1;
    }
    """

    css_gtk4 = b"""
    /* Tweaks (GTK 4+) */

    treeview.normal-icons {
        /* Country flag icon size in treeviews */
        -gtk-icon-size: 21px;
    }

    window.dialog:not(.message) .dialog-action-area {
        /* Add missing spacing to dialog action buttons */
        border-spacing: 6px;
    }

    .image-text-button box {
        /* Remove unwanted spacing from buttons */
        border-spacing: 0;
    }
    """

    global_css_provider = Gtk.CssProvider()

    if GTK_API_VERSION >= 4:
        css = css + css_gtk3_20 + css_gtk4
        global_css_provider.load_from_data(css)

        Gtk.StyleContext.add_provider_for_display(  # pylint: disable=no-member
            Gdk.Display.get_default(), global_css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

    else:
        css = css + css_gtk3

        if not Gtk.check_version(3, 20, 0):
            css = css + css_gtk3_20

        if not Gtk.check_version(3, 22, 28):
            css = css + css_gtk3_22_28

        global_css_provider.load_from_data(css)

        Gtk.StyleContext.add_provider_for_screen(  # pylint: disable=no-member
            Gdk.Screen.get_default(), global_css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )


def set_global_style():
    set_visual_settings()
    set_global_css()


""" Icons """


if GTK_API_VERSION >= 4:
    ICON_THEME = Gtk.IconTheme.get_for_display(Gdk.Display.get_default())  # pylint: disable=no-member
else:
    ICON_THEME = Gtk.IconTheme.get_default()  # pylint: disable=no-member


def load_custom_icons(update=False):
    """ Load custom icon theme if one is selected """

    if update:
        if hasattr(GTK_SETTINGS, "reset_property"):
            GTK_SETTINGS.reset_property("gtk-icon-theme-name")
        else:
            GTK_SETTINGS.set_property("gtk-icon-theme-name", SYSTEM_ICON_THEME)

    icon_theme_name = ".nicotine-icon-theme"
    icon_theme_path = os.path.join(config.data_dir, icon_theme_name)
    icon_theme_path_encoded = encode_path(icon_theme_path)

    parent_icon_theme_name = GTK_SETTINGS.get_property("gtk-icon-theme-name")

    if icon_theme_name == parent_icon_theme_name:
        return

    try:
        # Create internal icon theme folder
        if os.path.exists(icon_theme_path_encoded):
            import shutil
            shutil.rmtree(icon_theme_path_encoded)

    except Exception as error:
        log.add_debug("Failed to remove custom icon theme folder %(theme)s: %(error)s",
                      {"theme": icon_theme_path, "error": error})
        return

    user_icon_theme_path = config.sections["ui"]["icontheme"]

    if not user_icon_theme_path:
        return

    log.add_debug("Loading custom icon theme from %s", user_icon_theme_path)

    theme_file_path = os.path.join(icon_theme_path, "index.theme")
    theme_file_contents = (
        "[Icon Theme]\n"
        "Name=Nicotine+ Icon Theme\n"
        "Inherits=" + parent_icon_theme_name + "\n"
        "Directories=.\n"
        "\n"
        "[.]\n"
        "Size=16\n"
        "MinSize=8\n"
        "MaxSize=512\n"
        "Type=Scalable"
    )

    try:
        # Create internal icon theme folder
        os.makedirs(icon_theme_path_encoded)

        # Create icon theme index file
        with open(encode_path(theme_file_path), "w", encoding="utf-8") as file_handle:
            file_handle.write(theme_file_contents)

    except Exception as error:
        log.add_debug("Failed to enable custom icon theme %(theme)s: %(error)s",
                      {"theme": user_icon_theme_path, "error": error})
        return

    icon_names = (
        ("away", "nplus-status-away"),
        ("online", "nplus-status-online"),
        ("offline", "nplus-status-offline"),
        ("hilite", "nplus-hilite"),
        ("hilite3", "nplus-hilite3"),
        ("trayicon_away", "nplus-tray-away"),
        ("trayicon_away", config.application_id + "-away"),
        ("trayicon_connect", "nplus-tray-connect"),
        ("trayicon_connect", config.application_id + "-connect"),
        ("trayicon_disconnect", "nplus-tray-disconnect"),
        ("trayicon_disconnect", config.application_id + "-disconnect"),
        ("trayicon_msg", "nplus-tray-msg"),
        ("trayicon_msg", config.application_id + "-msg"),
        ("n", config.application_id),
        ("n", config.application_id + "-symbolic")
    )
    extensions = ["jpg", "jpeg", "bmp", "png", "svg"]

    # Move custom icons to internal icon theme location
    for (original_name, replacement_name) in icon_names:
        path = None
        exts = extensions[:]
        loaded = False

        while not path or (exts and not loaded):
            extension = exts.pop()
            path = os.path.join(user_icon_theme_path, "%s.%s" % (original_name, extension))

            try:
                path_encoded = encode_path(path)

                if os.path.isfile(path_encoded):
                    os.symlink(
                        path_encoded,
                        encode_path(os.path.join(icon_theme_path, "%s.%s" % (replacement_name, extension)))
                    )
                    loaded = True

            except Exception as error:
                log.add(_("Error loading custom icon %(path)s: %(error)s"), {
                    "path": path,
                    "error": error
                })

    # Enable custom icon theme
    GTK_SETTINGS.set_property("gtk-icon-theme-name", icon_theme_name)


def load_icons():
    """ Load custom icons necessary for the application to function """

    paths = (
        config.data_dir,  # Custom internal icon theme
        os.path.join(GTK_GUI_DIR, "icons"),  # Support running from folder, as well as macOS and Windows
        os.path.join(sys.prefix, "share", "icons")  # Support Python venv
    )

    for path in paths:
        if GTK_API_VERSION >= 4:
            ICON_THEME.add_search_path(path)
        else:
            ICON_THEME.append_search_path(path)

    load_custom_icons()


def get_flag_icon_name(country):

    country = country.lower().replace("flag_", "")

    if not country:
        return ""

    return "nplus-flag-" + country


def get_status_icon_name(status):

    if status == UserStatus.AWAY:
        return "nplus-status-away"

    if status == UserStatus.ONLINE:
        return "nplus-status-online"

    return "nplus-status-offline"


def on_icon_theme_changed(*_args):
    load_custom_icons()


ICON_THEME.connect("changed", on_icon_theme_changed)


""" Widget Fonts and Colors """


COLOR_RGBA = Gdk.RGBA()


def get_user_status_color(status):

    if status == UserStatus.AWAY:
        return "useraway"

    if status == UserStatus.ONLINE:
        return "useronline"

    return "useroffline"


def parse_color_string(color_string):
    """ Take a color string, e.g. BLUE, and return a HEX color code """

    if color_string and COLOR_RGBA.parse(color_string):
        color_hex = "#%02X%02X%02X" % (
            round(COLOR_RGBA.red * 255), round(COLOR_RGBA.green * 255), round(COLOR_RGBA.blue * 255))
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
