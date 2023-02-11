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
from pynicotine.shares import FileTypes
from pynicotine.slskmessages import UserStatus
from pynicotine.utils import encode_path


""" Global Style """


LIBADWAITA = None
try:
    if os.getenv("NICOTINE_LIBADWAITA") == "1":
        import gi
        gi.require_version("Adw", "1")

        from gi.repository import Adw
        LIBADWAITA = Adw

except (ImportError, ValueError):
    pass

CUSTOM_CSS_PROVIDER = Gtk.CssProvider()
GTK_SETTINGS = Gtk.Settings.get_default()
USE_COLOR_SCHEME_PORTAL = (sys.platform not in ("win32", "darwin") and not LIBADWAITA)

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
        USE_COLOR_SCHEME_PORTAL = None


def set_dark_mode(enabled):

    if LIBADWAITA:
        color_scheme = LIBADWAITA.ColorScheme.FORCE_DARK if enabled else LIBADWAITA.ColorScheme.DEFAULT
        LIBADWAITA.StyleManager.get_default().set_color_scheme(color_scheme)
        return

    if USE_COLOR_SCHEME_PORTAL and not enabled:
        color_scheme = read_color_scheme()

        if color_scheme is not None:
            enabled = (color_scheme == ColorScheme.PREFER_DARK)

    GTK_SETTINGS.set_property("gtk-application-prefer-dark-theme", enabled)


def set_use_header_bar(enabled):
    GTK_SETTINGS.set_property("gtk-dialogs-use-header", enabled)


def set_visual_settings():

    if sys.platform == "darwin":
        # Left align window controls on macOS
        GTK_SETTINGS.set_property("gtk-decoration-layout", "close,minimize,maximize:")

    set_dark_mode(config.sections["ui"]["dark_mode"])
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

    .search-view treeview:disabled {
        /* Search results with no free slots have no style by default */
        color: unset;
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

    .border-end:dir(ltr),
    .border-start:dir(rtl) {
        box-shadow: 1px 0 0 0 @borders;
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
        font-size: 20pt;
    }

    .title-2 {
        font-weight: 800;
        font-size: 15pt;
    }

    .heading {
        font-weight: bold;
        font-size: initial;
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

    .generic-popover contents {
        /* Remove unwanted spacing from popovers */
        padding: 0;
    }
    """

    global_css_provider = Gtk.CssProvider()

    if GTK_API_VERSION >= 4:
        css = css + css_gtk4

        try:
            global_css_provider.load_from_data(css)

        except TypeError:
            # https://gitlab.gnome.org/GNOME/pygobject/-/merge_requests/231
            global_css_provider.load_from_data(css.decode("utf-8"), length=-1)

        Gtk.StyleContext.add_provider_for_display(  # pylint: disable=no-member
            Gdk.Display.get_default(), global_css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

    else:
        css = css + css_gtk3
        global_css_provider.load_from_data(css)

        Gtk.StyleContext.add_provider_for_screen(  # pylint: disable=no-member
            Gdk.Screen.get_default(), global_css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )


def set_global_style():
    set_visual_settings()
    set_global_css()
    update_custom_css()


""" Icons """


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
    "x-office-document-symbolic": _("Document/Text")
}
USER_STATUS_ICON_NAMES = {
    UserStatus.ONLINE: "nplus-status-online",
    UserStatus.AWAY: "nplus-status-away",
    UserStatus.OFFLINE: "nplus-status-offline"
}


def load_custom_icons(update=False):
    """ Load custom icon theme if one is selected """

    if update:
        GTK_SETTINGS.reset_property("gtk-icon-theme-name")

    icon_theme_path = os.path.join(config.data_dir, CUSTOM_ICON_THEME_NAME)
    icon_theme_path_encoded = encode_path(icon_theme_path)

    parent_icon_theme_name = GTK_SETTINGS.get_property("gtk-icon-theme-name")

    if parent_icon_theme_name == CUSTOM_ICON_THEME_NAME:
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
        ("away", USER_STATUS_ICON_NAMES[UserStatus.AWAY]),
        ("online", USER_STATUS_ICON_NAMES[UserStatus.ONLINE]),
        ("offline", USER_STATUS_ICON_NAMES[UserStatus.OFFLINE]),
        ("hilite", "nplus-tab-highlight"),
        ("hilite3", "nplus-tab-changed"),
        ("trayicon_away", "nplus-tray-away"),
        ("trayicon_away", f"{config.application_id}-away"),
        ("trayicon_connect", "nplus-tray-connect"),
        ("trayicon_connect", f"{config.application_id}-connect"),
        ("trayicon_disconnect", "nplus-tray-disconnect"),
        ("trayicon_disconnect", f"{config.application_id}-disconnect"),
        ("trayicon_msg", "nplus-tray-msg"),
        ("trayicon_msg", f"{config.application_id}-msg"),
        ("n", config.application_id),
        ("n", f"{config.application_id}-symbolic")
    )
    extensions = [".jpg", ".jpeg", ".bmp", ".png", ".svg"]

    # Move custom icons to internal icon theme location
    for (original_name, replacement_name) in icon_names:
        path = None
        exts = extensions[:]
        loaded = False

        while not path or (exts and not loaded):
            extension = exts.pop()
            path = os.path.join(user_icon_theme_path, original_name + extension)

            try:
                path_encoded = encode_path(path)

                if os.path.isfile(path_encoded):
                    os.symlink(
                        path_encoded,
                        encode_path(os.path.join(icon_theme_path, replacement_name + extension))
                    )
                    loaded = True

            except Exception as error:
                log.add(_("Error loading custom icon %(path)s: %(error)s"), {
                    "path": path,
                    "error": error
                })

    # Enable custom icon theme
    GTK_SETTINGS.set_property("gtk-icon-theme-name", CUSTOM_ICON_THEME_NAME)


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


def get_flag_icon_name(country_code):

    if not country_code:
        return ""

    return f"nplus-flag-{country_code.lower()}"


def get_file_type_icon_name(filename):

    result = filename.rsplit(".", 1)

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

    if extension in FileTypes.DOCUMENT_TEXT:
        return "x-office-document-symbolic"

    if extension in FileTypes.EXECUTABLE:
        return "application-x-executable-symbolic"

    return "text-x-generic-symbolic"


def on_icon_theme_changed(*_args):
    load_custom_icons()


ICON_THEME.connect("changed", on_icon_theme_changed)


""" Fonts and Colors """


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


def _get_custom_font_css():

    css = bytearray()

    for css_selector, font in (
        ("window, popover", config.sections["ui"]["globalfont"]),
        ("treeview", config.sections["ui"]["listfont"]),
        ("textview", config.sections["ui"]["textviewfont"]),
        (".chat-view", config.sections["ui"]["chatfont"]),
        (".search-view", config.sections["ui"]["searchfont"]),
        (".transfers-view", config.sections["ui"]["transfersfont"]),
        (".userbrowse-view", config.sections["ui"]["browserfont"])
    ):
        font_description = Pango.FontDescription.from_string(font)

        if font_description.get_set_fields() & (Pango.FontMask.FAMILY | Pango.FontMask.SIZE):
            css.extend(
                f"""
                {css_selector} {{
                    font-family: {font_description.get_family()};
                    font-size: {font_description.get_size() // 1024}pt;
                    font-style: {PANGO_STYLES.get(font_description.get_style(), "normal")};
                    font-weight: {PANGO_WEIGHTS.get(font_description.get_weight(), "normal")};
                }}
                """.encode("utf-8")
            )

    return css


def _get_custom_color_css():

    css = bytearray()

    # User status colors
    online_color = config.sections["ui"]["useronline"]
    away_color = config.sections["ui"]["useraway"]
    offline_color = config.sections["ui"]["useroffline"]

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
        if color:
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
        if color:
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

    using_custom_icon_theme = (GTK_SETTINGS.get_property("gtk-icon-theme-name") == CUSTOM_ICON_THEME_NAME)
    css = bytearray(
        f"""
        .colored-icon {{
            -gtk-icon-style: {"regular" if using_custom_icon_theme else "symbolic"};
        }}
        """.encode("utf-8")
    )
    css.extend(_get_custom_font_css())
    css.extend(_get_custom_color_css())

    try:
        CUSTOM_CSS_PROVIDER.load_from_data(css)

    except TypeError:
        # https://gitlab.gnome.org/GNOME/pygobject/-/merge_requests/231
        CUSTOM_CSS_PROVIDER.load_from_data(css.decode("utf-8"), length=-1)

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
    is_hotspot_tag = (color_id in ("useraway", "useronline", "useroffline"))
    color_hex = config.sections["ui"].get(color_id)

    if is_hotspot_tag and not enable_colored_usernames:
        color_hex = None

    if not color_hex:
        tag.set_property("foreground-set", False)
    else:
        tag.set_property("foreground", color_hex)

    # URLs
    if color_id == "urlcolor":
        tag.set_property("underline", Pango.Underline.SINGLE)

    # Hotspots
    if not is_hotspot_tag:
        return

    usernamestyle = config.sections["ui"]["usernamestyle"]

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
