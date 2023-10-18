#!/usr/bin/env python3
# COPYRIGHT (C) 2021-2023 Nicotine+ Contributors
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

import glob
import os
import platform
import ssl
import subprocess
import sys
import tempfile

from cx_Freeze import Executable, setup  # pylint: disable=import-error

# pylint: disable=duplicate-code


if sys.platform == "win32":
    GUI_BASE = "Win32GUI"
    SYS_BASE_PATH = sys.prefix
    LIB_PATH = os.path.join(SYS_BASE_PATH, "bin")
    LIB_EXTENSION = ".dll"
    UNAVAILABLE_MODULES = [
        "fcntl", "grp", "nis", "ossaudiodev", "posix", "pwd", "readline", "resource", "spwd", "syslog", "termios"
    ]
    ICON_NAME = "icon.ico"

elif sys.platform == "darwin":
    GUI_BASE = None
    SYS_BASE_PATH = "/opt/homebrew" if platform.machine() == "arm64" else "/usr/local"
    LIB_PATH = os.path.join(SYS_BASE_PATH, "lib")
    LIB_EXTENSION = (".dylib", ".so")
    UNAVAILABLE_MODULES = ["msilib", "msvcrt", "nt", "nturl2path", "ossaudiodev", "spwd", "winreg", "winsound"]
    ICON_NAME = "icon.icns"

else:
    raise RuntimeError("Only Windows and macOS are supported")

TEMP_PATH = tempfile.mkdtemp()
CURRENT_PATH = os.path.dirname(os.path.abspath(__file__))
BUILD_PATH = os.path.join(CURRENT_PATH, "build")
PROJECT_PATH = os.path.abspath(os.path.join(CURRENT_PATH, "..", ".."))
sys.path.append(PROJECT_PATH)

import pynicotine  # noqa: E402  # pylint: disable=import-error,wrong-import-position

SCRIPT_NAME = "nicotine"
MODULE_NAME = "pynicotine"
GTK_VERSION = os.environ.get("NICOTINE_GTK_VERSION") or "4"
USE_LIBADWAITA = GTK_VERSION == "4" and os.environ.get("NICOTINE_LIBADWAITA") == "1"

# Include (almost) all standard library modules for plugins
EXCLUDED_MODULES = UNAVAILABLE_MODULES + [
    "ensurepip", "idlelib", "pip", "tkinter", "turtle", "turtledemo", "venv", "zoneinfo"
]
INCLUDED_MODULES = [MODULE_NAME, "gi"] + list(
    # pylint: disable=no-member
    {module for module in sys.stdlib_module_names if not module.startswith("_")}.difference(EXCLUDED_MODULES)
)

include_files = []


def process_files(folder_path, callback, callback_data=None, starts_with=None, ends_with=None, recursive=False):

    for full_path in glob.glob(os.path.join(folder_path, "**"), recursive=recursive):
        short_path = os.path.relpath(full_path, folder_path)

        if starts_with and not short_path.startswith(starts_with):
            continue

        if ends_with and not short_path.endswith(ends_with):
            continue

        callback(full_path, short_path, callback_data)


def add_file(file_path, output_path):
    include_files.append((file_path, output_path))


def _add_files_callback(full_path, short_path, output_path):
    add_file(full_path, os.path.join(output_path, short_path))


def add_files(folder_path, output_path, starts_with=None, ends_with=None, recursive=False):

    process_files(
        folder_path, _add_files_callback, callback_data=output_path,
        starts_with=starts_with, ends_with=ends_with, recursive=recursive
    )


def add_pixbuf_loaders():

    loaders_file = "lib/gdk-pixbuf-2.0/2.10.0/loaders.cache"
    temp_loaders_file = os.path.join(TEMP_PATH, "loaders.cache")

    with open(temp_loaders_file, "w", encoding="utf-8") as temp_file_handle, \
         open(os.path.join(SYS_BASE_PATH, loaders_file), "r", encoding="utf-8") as real_file_handle:
        data = real_file_handle.read()

        if sys.platform == "win32":
            data = data.replace("lib\\\\gdk-pixbuf-2.0\\\\2.10.0\\\\loaders", "lib")

        elif sys.platform == "darwin":
            data = data.replace(
                os.path.join(SYS_BASE_PATH, "lib/gdk-pixbuf-2.0/2.10.0/loaders"), "@executable_path/lib")

        temp_file_handle.write(data)

    add_file(file_path=temp_loaders_file, output_path="lib/pixbuf-loaders.cache")
    add_files(
        folder_path=os.path.join(SYS_BASE_PATH, "lib/gdk-pixbuf-2.0/2.10.0/loaders"), output_path="lib",
        starts_with="libpixbufloader-", ends_with=LIB_EXTENSION
    )


def _add_typelibs_callback(full_path, short_path, _callback_data=None):

    temp_file_gir = os.path.join(TEMP_PATH, short_path)
    temp_file_typelib = os.path.join(TEMP_PATH, short_path.replace(".gir", ".typelib"))

    with open(temp_file_gir, "w", encoding="utf-8") as temp_file_handle, \
         open(full_path, "r", encoding="utf-8") as real_file_handle:
        data = real_file_handle.read()
        data = data.replace('shared-library="lib', 'shared-library="@loader_path/lib')
        temp_file_handle.write(data)

    subprocess.check_call(["g-ir-compiler", f"--output={temp_file_typelib}", temp_file_gir])


def add_typelibs():

    required_typelibs = [
        f"Gtk-{GTK_VERSION}",
        "Gio-",
        f"Gdk-{GTK_VERSION}",
        f"GdkWin32-{GTK_VERSION}",
        "GLib-",
        "HarfBuzz-",
        "Pango-",
        "GObject-",
        "GdkPixbuf-",
        "cairo-",
        "GModule-",
        "freetype2-",
        "win32-"
    ]

    if GTK_VERSION == "4":
        required_typelibs += [
            "Graphene-",
            "Gsk-",
            "PangoCairo-"
        ]
    else:
        required_typelibs += [
            "Atk-"
        ]

    if USE_LIBADWAITA:
        required_typelibs.append("Adw-")

    required_typelibs = tuple(required_typelibs)
    folder_path = os.path.join(SYS_BASE_PATH, "lib/girepository-1.0")

    if sys.platform == "darwin":
        # Remove absolute paths added by Homebrew (macOS)
        process_files(
            folder_path=os.path.join(SYS_BASE_PATH, "share/gir-1.0"),
            callback=_add_typelibs_callback, starts_with=required_typelibs, ends_with=".gir"
        )
        folder_path = TEMP_PATH

    add_files(
        folder_path=folder_path, output_path="lib/typelibs",
        starts_with=required_typelibs, ends_with=".typelib"
    )


def add_gtk():

    if sys.platform == "win32":
        # gdbus required for single-instance application (Windows)
        add_file(file_path=os.path.join(LIB_PATH, "gdbus.exe"), output_path="lib/gdbus.exe")

    # This also includes all dlls required by GTK
    add_files(
        folder_path=LIB_PATH, output_path="lib",
        starts_with=f"libgtk-{GTK_VERSION}", ends_with=LIB_EXTENSION
    )

    if GTK_VERSION == "4":
        # ANGLE (OpenGL ES)
        add_files(
            folder_path=LIB_PATH, output_path="lib",
            starts_with=("libEGL", "libGLESv1", "libGLESv2.", "libfeature"), ends_with=LIB_EXTENSION
        )

    if USE_LIBADWAITA:
        add_files(
            folder_path=LIB_PATH, output_path="lib",
            starts_with="libadwaita-", ends_with=LIB_EXTENSION
        )

    # Schemas
    add_file(
        file_path=os.path.join(SYS_BASE_PATH, "share/glib-2.0/schemas/gschemas.compiled"),
        output_path="lib/schemas/gschemas.compiled"
    )

    # Fontconfig
    add_files(
        folder_path=os.path.join(SYS_BASE_PATH, "etc/fonts"), output_path="share/fonts",
        ends_with=".conf", recursive=True
    )

    # Pixbuf loaders
    add_pixbuf_loaders()

    # Typelibs
    add_typelibs()


def add_icon_packs():

    required_icon_packs = (
        "Adwaita",
        "hicolor"
    )
    add_files(
        folder_path=os.path.join(SYS_BASE_PATH, "share/icons"), output_path="share/icons",
        starts_with=required_icon_packs, ends_with=(".theme", ".svg"), recursive=True
    )


def add_themes():

    # "Mac" is required for macOS-specific keybindings in GTK
    required_themes = (
        "Default",
        "Mac"
    )
    add_files(
        folder_path=os.path.join(SYS_BASE_PATH, "share/themes"), output_path="share/themes",
        starts_with=required_themes, ends_with=".css", recursive=True
    )


def add_ssl_certs():
    ssl_paths = ssl.get_default_verify_paths()
    add_file(file_path=ssl_paths.openssl_cafile, output_path="lib/cert.pem")


def add_translations():

    from pynicotine.i18n import LANGUAGES           # noqa: E402  # pylint: disable=import-error
    from pynicotine.i18n import build_translations  # noqa: E402  # pylint: disable=import-error
    build_translations()

    add_files(
        folder_path=os.path.join(SYS_BASE_PATH, "share/locale"), output_path="share/locale",
        starts_with=tuple(i[0] for i in LANGUAGES), ends_with=f"gtk{GTK_VERSION}0.mo", recursive=True
    )


# GTK
add_gtk()
add_icon_packs()
add_themes()

# SSL
add_ssl_certs()

# Translations
add_translations()

# Setup
setup(
    name=pynicotine.__application_name__,
    description=pynicotine.__application_name__,
    author=pynicotine.__author__,
    version=pynicotine.__version__,
    options={
        "build": {
            "build_base": BUILD_PATH
        },
        "build_exe": {
            "build_exe": os.path.join(BUILD_PATH, "package", pynicotine.__application_name__),
            "packages": INCLUDED_MODULES,
            "excludes": EXCLUDED_MODULES,
            "include_files": include_files,
            "zip_include_packages": ["*"],
            "zip_exclude_packages": [MODULE_NAME]
        },
        "bdist_msi": {
            "all_users": True,
            "dist_dir": BUILD_PATH,
            "install_icon": os.path.join(CURRENT_PATH, ICON_NAME),
            "upgrade_code": "{8ffb9dbb-7106-41fc-9e8a-b2469aa1fe9f}"
        },
        "bdist_mac": {
            "bundle_name": pynicotine.__application_name__,
            "iconfile": os.path.join(CURRENT_PATH, ICON_NAME),
            "plist_items": [
                ("CFBundleName", pynicotine.__application_name__),
                ("CFBundleIdentifier", pynicotine.__application_id__),
                ("CFBundleShortVersionString", pynicotine.__version__),
                ("CFBundleVersion", pynicotine.__version__),
                ("CFBundleInfoDictionaryVersion", "6.0"),
                ("NSHumanReadableCopyright", pynicotine.__copyright__)
            ],
            "codesign_identity": "-",
            "codesign_deep": True,
            "codesign_entitlements": os.path.join(CURRENT_PATH, "codesign-entitlements.plist"),
            "codesign_options": "runtime",
            "codesign_strict": "all",
            "codesign_timestamp": True,
            "codesign_verify": True
        },
        "bdist_dmg": {
            "applications_shortcut": True
        }
    },
    packages=[],
    executables=[
        Executable(
            script=os.path.join(PROJECT_PATH, SCRIPT_NAME),
            base=GUI_BASE,
            target_name=pynicotine.__application_name__,
            icon=os.path.join(CURRENT_PATH, ICON_NAME),
            copyright=pynicotine.__copyright__,
            shortcut_name=pynicotine.__application_name__,
            shortcut_dir="ProgramMenuFolder"
        )
    ],
)
