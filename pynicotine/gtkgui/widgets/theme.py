# COPYRIGHT (C) 2020-2023 Nicotine+ Contributors
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
import shutil
import sys

from gi.repository import Gdk
from gi.repository import Gio
from gi.repository import GLib
from gi.repository import Gtk
from gi.repository import Pango

import pynicotine
from pynicotine.config import config
from pynicotine.gtkgui.application import GTK_API_VERSION
from pynicotine.gtkgui.application import GTK_GUI_FOLDER_PATH
from pynicotine.gtkgui.application import LIBADWAITA_API_VERSION
from pynicotine.gtkgui.application import LIBADWAITA_MINOR_VERSION
from pynicotine.logfacility import log
from pynicotine.shares import FileTypes
from pynicotine.slskmessages import UserStatus
from pynicotine.utils import encode_path


# Global Style #


CUSTOM_CSS_PROVIDER = Gtk.CssProvider()
GTK_SETTINGS = Gtk.Settings.get_default()
USE_COLOR_SCHEME_PORTAL = (sys.platform not in {"win32", "darwin"} and not LIBADWAITA_API_VERSION)

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
        USE_COLOR_SCHEME_PORTAL = False


def set_dark_mode(enabled):

    if LIBADWAITA_API_VERSION:
        from gi.repository import Adw  # pylint: disable=no-name-in-module

        color_scheme = Adw.ColorScheme.FORCE_DARK if enabled else Adw.ColorScheme.DEFAULT
        Adw.StyleManager.get_default().set_color_scheme(color_scheme)
        return

    if USE_COLOR_SCHEME_PORTAL and not enabled:
        color_scheme = read_color_scheme()

        if color_scheme is not None:
            enabled = (color_scheme == ColorScheme.PREFER_DARK)

    GTK_SETTINGS.props.gtk_application_prefer_dark_theme = enabled


def set_use_header_bar(enabled):
    GTK_SETTINGS.props.gtk_dialogs_use_header = enabled


def set_visual_settings():

    if sys.platform == "darwin":
        # Left align window controls on macOS
        GTK_SETTINGS.props.gtk_decoration_layout = "close,minimize,maximize:"

    set_dark_mode(config.sections["ui"]["dark_mode"])
    set_use_header_bar(config.sections["ui"]["header_bar"])


def set_global_css():

    css = bytearray()
    css_default = b"""
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

    .search-view treeview:disabled {
        /* Search results with no free slots have no style by default */
        color: unset;
    }

    treeview button > box {
        /* Column header padding to match rows */
        padding-right: 11px;
    }

    treeview button {
        /* Column header padding to match rows */
        padding-left: 11px;
        padding-right: 1px;
    }

    infobar box {
        /* Remove unwanted padding from info bars */
        padding: 0;
    }

    progressbar.osd trough,
    progressbar.osd progress {
        /* Make overlay progress bars slightly more legible */
        min-height: 4px;
    }

    treeview button {
        /* Remove bottom border from column headers */
        border: 0;
        padding-bottom: 3px;
        padding-top: 3px;
    }

    treeview button:not(:last-child):dir(ltr) > box,
    treeview button:not(:first-child):dir(rtl) > box {
        /* Add column header separators */
        box-shadow: 1px 0 0 0 alpha(@borders, 2.8);
    }

    /* Borders */

    .border-top,
    .preferences-border .action-area {
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

    .border-start-dim:dir(ltr),
    .border-end-dim:dir(rtl) {
        box-shadow: -1px 0 0 0 alpha(@borders, 0.75);
    }

    .border-end:dir(ltr),
    .border-start:dir(rtl) {
        box-shadow: 1px 0 0 0 @borders;
    }

    .border-end-dim:dir(ltr),
    .border-start-dim:dir(rtl) {
        box-shadow: 1px 0 0 0 alpha(@borders, 0.75);
    }

    /* Buttons */

    .count {
        min-width: 12px;
        padding-left: 10px;
        padding-right: 10px;
    }

    /* Headings */

    .title-1 {
        font-weight: 800;
        font-size: 1.83em;
    }

    .title-2 {
        font-weight: 800;
        font-size: 1.35em;
    }

    .heading {
        font-weight: bold;
        font-size: inherit;
    }

    /* Text Formatting */

    .bold {
        font-weight: bold;
    }

    .italic {
        font-style: italic;
    }

    .normal {
        font-weight: normal;
    }

    .underline {
        text-decoration-line: underline;
    }
    """

    css_gtk3 = b"""
    /* Tweaks (GTK 3) */

    treeview {
        /* Set spacing for dropdown menu/entry completion items */
        -GtkTreeView-horizontal-separator: 12;
        -GtkTreeView-vertical-separator: 5;
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

    .dropdown-scrollbar {
        /* Enable dropdown list with a scrollbar */
        -GtkComboBox-appears-as-list: 1;
    }
    """

    css_gtk4 = b"""
    /* Tweaks (GTK 4+) */

    * {
        /* Unset line height due to it resulting in blurry text */
        line-height: unset;
    }

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

    .generic-popover *:not(image) {
        /* Remove unwanted spacing from popovers */
        margin: 0;
    }

    .generic-popover contents {
        /* Remove unwanted spacing from popovers */
        padding: 0;
    }
    """

    css_libadwaita = b"""
    /* Tweaks (libadwaita) */

    treeview > header > button > box {
        /* Use relative font size for column headers */
        font-size: 0.92em;
    }
    """

    css_libadwaita_1_4 = b"""
    /* Tweaks (libadwaita 1.4+) */

    window:not(.filechooser):not(.preferences-border):not(.titlebar-border) headerbar.titlebar,
    window:not(.menubar-border) menubar {
        /* Make title/header bars flat to match other libadwaita apps */
        background: none;
        box-shadow: none;
        color: inherit;
    }
    """

    global_css_provider = Gtk.CssProvider()
    css.extend(css_default)

    if GTK_API_VERSION >= 4:
        css.extend(css_gtk4)

        if LIBADWAITA_API_VERSION:
            css.extend(css_libadwaita)

        if (LIBADWAITA_API_VERSION, LIBADWAITA_MINOR_VERSION) >= (1, 4):
            css.extend(css_libadwaita_1_4)

        load_css(global_css_provider, css)

        Gtk.StyleContext.add_provider_for_display(  # pylint: disable=no-member
            Gdk.Display.get_default(), global_css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

    else:
        css.extend(css_gtk3)
        load_css(global_css_provider, css)

        Gtk.StyleContext.add_provider_for_screen(  # pylint: disable=no-member
            Gdk.Screen.get_default(), global_css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )


def set_global_style():
    set_visual_settings()
    set_global_css()
    update_custom_css()


# Icons #


if GTK_API_VERSION >= 4:
    ICON_THEME = Gtk.IconTheme.get_for_display(Gdk.Display.get_default())  # pylint: disable=no-member
else:
    ICON_THEME = Gtk.IconTheme.get_default()  # pylint: disable=no-member

CUSTOM_ICON_THEME_NAME = ".nicotine-icon-theme"
FILE_TYPE_ICON_LABELS = {
    "application-x-executable-symbolic": _("Executable"),
    "audio-x-generic-symbolic": _("Audio"),
    "image-x-generic-symbolic": _("Image"),
    "package-x-generic-symbolic": _("Archive"),
    "text-x-generic-symbolic": _("Miscellaneous"),
    "video-x-generic-symbolic": _("Video"),
    "x-office-document-symbolic": _("Document"),
    "emblem-documents-symbolic": _("Text")
}
USER_STATUS_ICON_NAMES = {
    UserStatus.ONLINE: "nplus-status-online",
    UserStatus.AWAY: "nplus-status-away",
    UserStatus.OFFLINE: "nplus-status-offline"
}


def load_custom_icons(update=False):
    """Load custom icon theme if one is selected."""

    if update:
        GTK_SETTINGS.reset_property("gtk-icon-theme-name")

    icon_theme_path = os.path.join(config.data_folder_path, CUSTOM_ICON_THEME_NAME)
    icon_theme_path_encoded = encode_path(icon_theme_path)

    parent_icon_theme_name = GTK_SETTINGS.props.gtk_icon_theme_name

    if parent_icon_theme_name == CUSTOM_ICON_THEME_NAME:
        return

    try:
        # Create internal icon theme folder
        if os.path.exists(icon_theme_path_encoded):
            shutil.rmtree(icon_theme_path_encoded)

    except Exception as error:
        log.add_debug("Failed to remove custom icon theme folder %(theme)s: %(error)s",
                      {"theme": icon_theme_path, "error": error})
        return

    user_icon_theme_path = config.sections["ui"]["icontheme"]

    if not user_icon_theme_path:
        return

    user_icon_theme_path = os.path.normpath(user_icon_theme_path)
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
        ("away", USER_STATUS_ICON_NAMES[UserStatus.AWAY]),
        ("online", USER_STATUS_ICON_NAMES[UserStatus.ONLINE]),
        ("offline", USER_STATUS_ICON_NAMES[UserStatus.OFFLINE]),
        ("hilite", "nplus-tab-highlight"),
        ("hilite3", "nplus-tab-changed"),
        ("trayicon_away", "nplus-tray-away"),
        ("trayicon_away", f"{pynicotine.__application_id__}-away"),
        ("trayicon_connect", "nplus-tray-connect"),
        ("trayicon_connect", f"{pynicotine.__application_id__}-connect"),
        ("trayicon_disconnect", "nplus-tray-disconnect"),
        ("trayicon_disconnect", f"{pynicotine.__application_id__}-disconnect"),
        ("trayicon_msg", "nplus-tray-msg"),
        ("trayicon_msg", f"{pynicotine.__application_id__}-msg"),
        ("n", pynicotine.__application_id__),
        ("n", f"{pynicotine.__application_id__}-symbolic")
    )
    extensions = (".png", ".svg", ".jpg", ".jpeg", ".bmp")

    # Move custom icons to internal icon theme location
    for original_name, replacement_name in icon_names:
        for extension in extensions:
            file_path = os.path.join(user_icon_theme_path, original_name + extension)
            file_path_encoded = encode_path(file_path)

            if not os.path.isfile(file_path_encoded):
                continue

            try:
                shutil.copyfile(
                    file_path_encoded,
                    encode_path(os.path.join(icon_theme_path, replacement_name + extension))
                )
                break

            except OSError as error:
                log.add(_("Error loading custom icon %(path)s: %(error)s"), {
                    "path": file_path,
                    "error": error
                })

    # Enable custom icon theme
    GTK_SETTINGS.props.gtk_icon_theme_name = CUSTOM_ICON_THEME_NAME


def load_icons():
    """Load custom icons necessary for the application to function."""

    paths = (
        config.data_folder_path,  # Custom internal icon theme
        os.path.join(GTK_GUI_FOLDER_PATH, "icons"),  # Support running from folder, as well as macOS and Windows
        os.path.join(sys.prefix, "share", "icons")  # Support Python venv
    )

    for path in paths:
        if GTK_API_VERSION >= 4:
            ICON_THEME.add_search_path(path)
        else:
            ICON_THEME.append_search_path(path)

    load_custom_icons()


def get_flag_icon_name(country_code):

    if not country_code:
        return ""

    return f"nplus-flag-{country_code.lower()}"


def get_file_type_icon_name(basename):

    result = basename.rsplit(".", 1)

    if len(result) < 2:
        return "text-x-generic-symbolic"

    extension = result[-1].lower()

    if extension in FileTypes.AUDIO:
        return "audio-x-generic-symbolic"

    if extension in FileTypes.IMAGE:
        return "image-x-generic-symbolic"

    if extension in FileTypes.VIDEO:
        return "video-x-generic-symbolic"

    if extension in FileTypes.ARCHIVE:
        return "package-x-generic-symbolic"

    if extension in FileTypes.DOCUMENT:
        return "x-office-document-symbolic"

    if extension in FileTypes.TEXT:
        return "emblem-documents-symbolic"

    if extension in FileTypes.EXECUTABLE:
        return "application-x-executable-symbolic"

    return "text-x-generic-symbolic"


def on_icon_theme_changed(*_args):
    load_custom_icons()


ICON_THEME.connect("changed", on_icon_theme_changed)


# Fonts and Colors #


PANGO_STYLES = {
    Pango.Style.NORMAL: "normal",
    Pango.Style.ITALIC: "italic"
}
PANGO_WEIGHTS = {
    Pango.Weight.THIN: 100,
    Pango.Weight.ULTRALIGHT: 200,
    Pango.Weight.LIGHT: 300,
    Pango.Weight.SEMILIGHT: 350,
    Pango.Weight.BOOK: 380,
    Pango.Weight.NORMAL: 400,
    Pango.Weight.MEDIUM: 500,
    Pango.Weight.SEMIBOLD: 600,
    Pango.Weight.BOLD: 700,
    Pango.Weight.ULTRABOLD: 800,
    Pango.Weight.HEAVY: 900,
    Pango.Weight.ULTRAHEAVY: 1000
}
USER_STATUS_COLORS = {
    UserStatus.ONLINE: "useronline",
    UserStatus.AWAY: "useraway",
    UserStatus.OFFLINE: "useroffline"
}


def add_css_class(widget, css_class):

    if GTK_API_VERSION >= 4:
        widget.add_css_class(css_class)              # pylint: disable=no-member
        return

    widget.get_style_context().add_class(css_class)  # pylint: disable=no-member


def remove_css_class(widget, css_class):

    if GTK_API_VERSION >= 4:
        widget.remove_css_class(css_class)              # pylint: disable=no-member
        return

    widget.get_style_context().remove_class(css_class)  # pylint: disable=no-member


def load_css(css_provider, data):

    try:
        css_provider.load_from_string(data.decode("utf-8"))

    except AttributeError:
        try:
            css_provider.load_from_data(data.decode("utf-8"), length=-1)

        except TypeError:
            css_provider.load_from_data(data)


def _get_custom_font_css():

    css = bytearray()

    for css_selector, font in (
        ("window, popover", config.sections["ui"]["globalfont"]),
        ("treeview", config.sections["ui"]["listfont"]),
        ("textview", config.sections["ui"]["textviewfont"]),
        (".chat-view textview", config.sections["ui"]["chatfont"]),
        (".search-view treeview", config.sections["ui"]["searchfont"]),
        (".transfers-view treeview", config.sections["ui"]["transfersfont"]),
        (".userbrowse-view treeview", config.sections["ui"]["browserfont"])
    ):
        font_description = Pango.FontDescription.from_string(font)

        if font_description.get_set_fields() & (Pango.FontMask.FAMILY | Pango.FontMask.SIZE):
            css.extend(
                f"""
                {css_selector} {{
                    font-family: '{font_description.get_family()}';
                    font-size: {font_description.get_size() // 1024}pt;
                    font-style: {PANGO_STYLES.get(font_description.get_style(), "normal")};
                    font-weight: {PANGO_WEIGHTS.get(font_description.get_weight(), "normal")};
                }}
                """.encode("utf-8")
            )

    return css


def _is_color_valid(color_hex):
    return color_hex and Gdk.RGBA().parse(color_hex)


def _get_custom_color_css():

    css = bytearray()

    # User status colors
    online_color = config.sections["ui"]["useronline"]
    away_color = config.sections["ui"]["useraway"]
    offline_color = config.sections["ui"]["useroffline"]

    if _is_color_valid(online_color) and _is_color_valid(away_color) and _is_color_valid(offline_color):
        css.extend(
            f"""
            .user-status {{
                -gtk-icon-palette: success {online_color}, warning {away_color}, error {offline_color};
            }}
            """.encode("utf-8")
        )

    # Text colors
    treeview_text_color = config.sections["ui"]["search"]

    for css_selector, color in (
        (".notebook-tab", config.sections["ui"]["tab_default"]),
        (".notebook-tab-changed", config.sections["ui"]["tab_changed"]),
        (".notebook-tab-highlight", config.sections["ui"]["tab_hilite"]),
        ("entry", config.sections["ui"]["inputcolor"]),
        ("treeview", treeview_text_color),
        (".search-view treeview:disabled", config.sections["ui"]["searchq"])
    ):
        if _is_color_valid(color):
            css.extend(
                f"""
                {css_selector} {{
                    color: {color};
                }}
                """.encode("utf-8")
            )

    # Background colors
    for css_selector, color in (
        ("entry", config.sections["ui"]["textbg"]),
    ):
        if _is_color_valid(color):
            css.extend(
                f"""
                {css_selector} {{
                    background: {color};
                }}
                """.encode("utf-8")
            )

    # Reset treeview column header colors
    if treeview_text_color:
        css.extend(
            b"""
            treeview header {
                color: initial;
            }
            """
        )

    return css


def update_custom_css():

    using_custom_icon_theme = (GTK_SETTINGS.props.gtk_icon_theme_name == CUSTOM_ICON_THEME_NAME)
    css = bytearray(
        f"""
        .colored-icon {{
            -gtk-icon-style: {"regular" if using_custom_icon_theme else "symbolic"};
        }}
        """.encode("utf-8")
    )
    css.extend(_get_custom_font_css())
    css.extend(_get_custom_color_css())

    load_css(CUSTOM_CSS_PROVIDER, css)

    if GTK_API_VERSION >= 4:
        Gtk.StyleContext.add_provider_for_display(  # pylint: disable=no-member
            Gdk.Display.get_default(), CUSTOM_CSS_PROVIDER, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )
    else:
        Gtk.StyleContext.add_provider_for_screen(  # pylint: disable=no-member
            Gdk.Screen.get_default(), CUSTOM_CSS_PROVIDER, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )


def update_tag_visuals(tag, color_id):

    enable_colored_usernames = config.sections["ui"]["usernamehotspots"]
    is_hotspot_tag = (color_id in {"useraway", "useronline", "useroffline"})
    color_hex = config.sections["ui"].get(color_id)
    tag_props = tag.props

    if is_hotspot_tag and not enable_colored_usernames:
        color_hex = None

    if not color_hex:
        if tag_props.foreground_set:
            tag_props.foreground_set = False
    else:
        current_rgba = tag_props.foreground_rgba
        new_rgba = Gdk.RGBA()
        new_rgba.parse(color_hex)

        if current_rgba is None or not new_rgba.equal(current_rgba):
            tag_props.foreground_rgba = new_rgba

    # URLs
    if color_id == "urlcolor" and tag_props.underline != Pango.Underline.SINGLE:
        tag_props.underline = Pango.Underline.SINGLE

    # Hotspots
    if not is_hotspot_tag:
        return

    username_style = config.sections["ui"]["usernamestyle"]

    weight_style = Pango.Weight.BOLD if username_style == "bold" else Pango.Weight.NORMAL
    if tag_props.weight != weight_style:
        tag_props.weight = weight_style

    italic_style = Pango.Style.ITALIC if username_style == "italic" else Pango.Style.NORMAL
    if tag_props.style != italic_style:
        tag_props.style = italic_style

    underline_style = Pango.Underline.SINGLE if username_style == "underline" else Pango.Underline.NONE
    if tag_props.underline != underline_style:
        tag_props.underline = underline_style
