#!/usr/bin/env python3
# COPYRIGHT (C) 2021-2022 Nicotine+ Contributors
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
import ssl
import subprocess
import sys
import tempfile

from cx_Freeze import Executable, setup  # pylint: disable=import-error


if sys.platform == "win32":
    GUI_BASE = "Win32GUI"
    SYS_BASE = sys.prefix
    LIB_FOLDER = "bin"
    LIB_EXTENSION = ".dll"
    ICON_NAME = "icon.ico"

elif sys.platform == "darwin":
    GUI_BASE = None
    SYS_BASE = "/usr/local"
    LIB_FOLDER = "lib"
    LIB_EXTENSION = (".dylib", ".so")
    ICON_NAME = "icon.icns"

else:
    raise RuntimeError("Only Windows and macOS are supported")

TEMP_PATH = tempfile.mkdtemp()
CURRENT_PATH = os.path.dirname(os.path.abspath(__file__))
BUILD_PATH = os.path.join(CURRENT_PATH, "build")
PROJECT_PATH = os.path.abspath(os.path.join(CURRENT_PATH, "..", ".."))
sys.path.append(PROJECT_PATH)

from pynicotine.config import config  # noqa: E402  # pylint: disable=import-error,wrong-import-position

APPLICATION_NAME = config.application_name
APPLICATION_ID = config.application_id
VERSION = config.version
AUTHOR = config.author
COPYRIGHT = config.copyright

SCRIPT_NAME = "nicotine"
MODULE_NAME = "pynicotine"
GTK_VERSION = os.environ.get("NICOTINE_GTK_VERSION") or '3'
USE_LIBADWAITA = GTK_VERSION == '4' and os.environ.get("NICOTINE_LIBADWAITA") == '1'

include_files = []


def process_files(rel_path, starts_with, ends_with, callback, callback_data=None,
                  recursive=False, temporary=False):

    folder_path = TEMP_PATH if temporary else os.path.join(SYS_BASE, rel_path)

    for full_path in glob.glob(os.path.join(folder_path, '**'), recursive=recursive):
        short_path = os.path.relpath(full_path, folder_path)

        if not short_path.startswith(starts_with):
            continue

        if not short_path.endswith(ends_with):
            continue

        callback(full_path, short_path, callback_data)


def _add_files_callback(full_path, short_path, output_path):
    include_files.append((full_path, os.path.join(output_path, short_path)))


def add_files(rel_path, starts_with, ends_with, output_path=None,
              recursive=False, temporary=False):

    if output_path is None:
        output_path = rel_path

    process_files(rel_path, starts_with, ends_with,
                  _add_files_callback, callback_data=output_path,
                  recursive=recursive, temporary=temporary)


def add_pixbuf_loaders():

    loaders_file = "lib/gdk-pixbuf-2.0/2.10.0/loaders.cache"
    temp_loaders_file = os.path.join(TEMP_PATH, "loaders.cache")

    with open(temp_loaders_file, "w", encoding="utf-8") as temp_file_handle, \
         open(os.path.join(SYS_BASE, loaders_file), "r", encoding="utf-8") as real_file_handle:
        data = real_file_handle.read()

        if sys.platform == "win32":
            data = data.replace("lib\\\\gdk-pixbuf-2.0\\\\2.10.0\\\\loaders", "lib")

        elif sys.platform == "darwin":
            data = data.replace(os.path.join(SYS_BASE, "lib/gdk-pixbuf-2.0/2.10.0/loaders"), "@executable_path/lib")

        temp_file_handle.write(data)

    include_files.append((temp_loaders_file, loaders_file))
    add_files("lib/gdk-pixbuf-2.0/2.10.0/loaders", "libpixbufloader-", LIB_EXTENSION, output_path="lib")


def _add_typelibs_callback(full_path, short_path, _callback_data=None):

    temp_file_gir = os.path.join(TEMP_PATH, short_path)
    temp_file_typelib = os.path.join(TEMP_PATH, short_path.replace(".gir", ".typelib"))

    with open(temp_file_gir, "w", encoding="utf-8") as temp_file_handle, \
         open(full_path, "r", encoding="utf-8") as real_file_handle:
        data = real_file_handle.read()
        data = data.replace('shared-library="lib', 'shared-library="@loader_path/lib')
        temp_file_handle.write(data)

    subprocess.check_call(["g-ir-compiler", "--output=%s" % temp_file_typelib, temp_file_gir])


def add_typelibs():

    required_typelibs = [
        "Gtk-%s" % GTK_VERSION,
        "Gio-",
        "Gdk-%s" % GTK_VERSION,
        "GLib-",
        "HarfBuzz-",
        "Pango-",
        "GObject-",
        "GdkPixbuf-",
        "cairo-",
        "GModule-"
    ]

    if GTK_VERSION == '4':
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
    temporary_folder = False

    if sys.platform == "darwin":
        # Remove absolute paths added by Homebrew (macOS)
        process_files("share/gir-1.0", required_typelibs, ".gir", _add_typelibs_callback)
        temporary_folder = True

    add_files("lib/girepository-1.0", required_typelibs, ".typelib", temporary=temporary_folder)


def add_gtk():

    if sys.platform == "win32":
        # gdbus required for single-instance application (Windows)
        include_files.append((os.path.join(SYS_BASE, LIB_FOLDER, "gdbus.exe"), "lib/gdbus.exe"))
        lib_output_path = "lib"

    elif sys.platform == "darwin":
        # .dylib files are in the same folder as the executable
        lib_output_path = ""

    # This also includes all dlls required by GTK
    add_files(LIB_FOLDER, "libgtk-%s" % GTK_VERSION, LIB_EXTENSION, output_path=lib_output_path)

    if USE_LIBADWAITA:
        add_files(LIB_FOLDER, "libadwaita-", LIB_EXTENSION, output_path=lib_output_path)

    include_files.append((os.path.join(SYS_BASE, "share/glib-2.0/schemas/gschemas.compiled"),
                         "share/glib-2.0/schemas/gschemas.compiled"))

    # Pixbuf loaders
    add_pixbuf_loaders()

    # Typelibs
    add_typelibs()


def add_icon_packs():

    required_icon_packs = (
        "Adwaita",
        "hicolor"
    )
    add_files("share/icons", required_icon_packs, (".theme", ".svg"), recursive=True)


def add_themes():

    # "Mac" is required for macOS-specific keybindings in GTK
    required_themes = (
        "Default",
        "Mac"
    )
    add_files("share/themes", required_themes, ".css", recursive=True)


def add_ssl_certs():
    ssl_paths = ssl.get_default_verify_paths()
    include_files.append((ssl_paths.openssl_cafile, "share/ssl/cert.pem"))


def add_translations():

    from pynicotine.i18n import build_translations  # noqa: E402  # pylint: disable=import-error
    languages = build_translations()

    include_files.append((os.path.join(PROJECT_PATH, "mo"), "share/locale"))
    add_files("share/locale", tuple(languages), "gtk%s0.mo" % GTK_VERSION, recursive=True)


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
    name=APPLICATION_NAME,
    description=APPLICATION_NAME,
    author=AUTHOR,
    version=VERSION,
    options={
        "build": dict(
            build_base=BUILD_PATH,
            build_exe=os.path.join(BUILD_PATH, "package", APPLICATION_NAME)
        ),
        "build_exe": dict(
            packages=[MODULE_NAME, "gi"],
            excludes=["tkinter"],
            include_files=include_files,
            zip_include_packages=["*"],
            zip_exclude_packages=[MODULE_NAME]
        ),
        "bdist_msi": dict(
            all_users=True,
            dist_dir=BUILD_PATH,
            install_icon=os.path.join(CURRENT_PATH, ICON_NAME),
            upgrade_code="{8ffb9dbb-7106-41fc-9e8a-b2469aa1fe9f}"
        ),
        "bdist_mac": dict(
            bundle_name=APPLICATION_NAME,
            iconfile=os.path.join(CURRENT_PATH, ICON_NAME),
            plist_items=[
                ("CFBundleName", APPLICATION_NAME),
                ("CFBundleIdentifier", APPLICATION_ID),
                ("CFBundleShortVersionString", VERSION),
                ("CFBundleVersion", VERSION),
                ("CFBundleInfoDictionaryVersion", "6.0"),
                ("NSHumanReadableCopyright", COPYRIGHT)
            ]
        ),
        "bdist_dmg": dict(
            applications_shortcut=True
        )
    },
    packages=[],
    executables=[
        Executable(
            script=os.path.join(PROJECT_PATH, SCRIPT_NAME),
            base=GUI_BASE,
            target_name=APPLICATION_NAME,
            icon=os.path.join(CURRENT_PATH, ICON_NAME),
            copyright=COPYRIGHT,
            shortcut_name=APPLICATION_NAME,
            shortcut_dir="ProgramMenuFolder"
        )
    ],
)
