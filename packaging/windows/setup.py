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
import pkgutil
import re
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

elif sys.platform == "darwin":
    GUI_BASE = None
    SYS_BASE = "/usr/local"
    LIB_FOLDER = "lib"
    LIB_EXTENSION = (".dylib", ".so")

else:
    raise RuntimeError("Only Windows and macOS are supported")

INCLUDE_FILES = []
PLUGIN_PACKAGES = []
TEMP_FOLDER = tempfile.mkdtemp()

GTK_VERSION = os.environ.get("NICOTINE_GTK_VERSION") or '3'
USE_LIBADWAITA = GTK_VERSION == '4' and os.environ.get("NICOTINE_LIBADWAITA") == '1'

PYNICOTINE_PATH = os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", ".."))
sys.path.append(PYNICOTINE_PATH)


def process_files(rel_path, starts_with, ends_with, callback, callback_data=None,
                  recursive=False, temporary=False):

    folder_path = TEMP_FOLDER if temporary else os.path.join(SYS_BASE, rel_path)

    for full_path in glob.glob(os.path.join(folder_path, '**'), recursive=recursive):
        short_path = os.path.relpath(full_path, folder_path)

        if not short_path.startswith(starts_with):
            continue

        if not short_path.endswith(ends_with):
            continue

        callback(full_path, short_path, callback_data)


def _add_files_callback(full_path, short_path, output_path):
    INCLUDE_FILES.append((full_path, os.path.join(output_path, short_path)))


def add_files(rel_path, starts_with, ends_with, output_path=None,
              recursive=False, temporary=False):

    if output_path is None:
        output_path = rel_path

    process_files(rel_path, starts_with, ends_with,
                  _add_files_callback, callback_data=output_path,
                  recursive=recursive, temporary=temporary)


def add_pixbuf_loaders():

    loaders_file = "lib/gdk-pixbuf-2.0/2.10.0/loaders.cache"
    temp_loaders_file = os.path.join(TEMP_FOLDER, "loaders.cache")

    with open(temp_loaders_file, "w", encoding="utf-8") as temp_file_handle, \
         open(os.path.join(SYS_BASE, loaders_file), "r", encoding="utf-8") as real_file_handle:
        data = real_file_handle.read()

        if sys.platform == "win32":
            data = data.replace("lib\\\\gdk-pixbuf-2.0\\\\2.10.0\\\\loaders", "lib")

        elif sys.platform == "darwin":
            data = data.replace(os.path.join(SYS_BASE, "lib/gdk-pixbuf-2.0/2.10.0/loaders"), "@executable_path/lib")

        temp_file_handle.write(data)

    INCLUDE_FILES.append((temp_loaders_file, loaders_file))
    add_files("lib/gdk-pixbuf-2.0/2.10.0/loaders", "libpixbufloader-", LIB_EXTENSION, output_path="lib")


def _add_typelibs_callback(full_path, short_path, _callback_data=None):

    temp_file_gir = os.path.join(TEMP_FOLDER, short_path)
    temp_file_typelib = os.path.join(TEMP_FOLDER, short_path.replace(".gir", ".typelib"))

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
        INCLUDE_FILES.append((os.path.join(SYS_BASE, LIB_FOLDER, "gdbus.exe"), "lib/gdbus.exe"))
        lib_output_path = "lib"

    elif sys.platform == "darwin":
        # .dylib files are in the same folder as the executable
        lib_output_path = ""

    # This also includes all dlls required by GTK
    add_files(LIB_FOLDER, "libgtk-%s" % GTK_VERSION, LIB_EXTENSION, output_path=lib_output_path)

    if USE_LIBADWAITA:
        add_files(LIB_FOLDER, "libadwaita-", LIB_EXTENSION, output_path=lib_output_path)

    INCLUDE_FILES.append((os.path.join(SYS_BASE, "share/glib-2.0/schemas/gschemas.compiled"),
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
    INCLUDE_FILES.append((ssl_paths.openssl_cafile, "share/ssl/cert.pem"))


def add_translations():

    from pynicotine.i18n import build_translations  # noqa: E402  # pylint: disable=import-error
    languages = build_translations()

    INCLUDE_FILES.append((os.path.join(PYNICOTINE_PATH, "mo"), "share/locale"))
    add_files("share/locale", tuple(languages), "gtk%s0.mo" % GTK_VERSION, recursive=True)


def add_plugin_packages():

    import pynicotine.plugins  # noqa: E402  # pylint: disable=import-error

    for _importer, name, ispkg in pkgutil.walk_packages(path=pynicotine.plugins.__path__, prefix="pynicotine.plugins."):
        if ispkg:
            PLUGIN_PACKAGES.append(name)


# GTK
add_gtk()
add_icon_packs()
add_themes()

# SSL
add_ssl_certs()

# Translations
add_translations()

# Plugins
add_plugin_packages()

# Setup
from pynicotine.config import config  # noqa: E402  # pylint: disable=import-error,wrong-import-position

setup(
    name=config.application_name,
    author=config.author,
    version=re.sub(r".(dev|rc)(.*)", "", config.version),
    options={
        "build_exe": dict(
            packages=["gi"] + PLUGIN_PACKAGES,
            excludes=["pygtkcompat", "tkinter"],
            include_files=INCLUDE_FILES,
            zip_include_packages=["*"],
            zip_exclude_packages=["pynicotine"]
        ),
        "bdist_msi": dict(
            all_users=True,
            install_icon=os.path.join(PYNICOTINE_PATH, "packaging/windows/nicotine.ico"),
            target_name="%s-%s.msi" % (config.application_name, config.version),
            upgrade_code="{8ffb9dbb-7106-41fc-9e8a-b2469aa1fe9f}"
        ),
        "bdist_mac": dict(
            iconfile=os.path.join(PYNICOTINE_PATH, "packaging/macos/nicotine.icns"),
            bundle_name=config.application_name
        ),
        "bdist_dmg": dict(
            applications_shortcut=True
        )
    },
    executables=[
        Executable(
            script=os.path.join(PYNICOTINE_PATH, "nicotine"),
            target_name=config.application_name,
            base=GUI_BASE,
            icon=os.path.join(PYNICOTINE_PATH, "packaging/windows/nicotine.ico"),
            shortcut_name=config.application_name,
            shortcut_dir="StartMenuFolder"
        )
    ],
)
