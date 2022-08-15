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
    LIB_FOLDER = os.path.join(SYS_BASE, "bin")
    LIB_EXTENSION = ".dll"
    ICON_NAME = "icon.ico"

elif sys.platform == "darwin":
    GUI_BASE = None
    SYS_BASE = "/usr/local"
    LIB_FOLDER = os.path.join(SYS_BASE, "lib")
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
include_resources = []


def add_file(file_path, output_path, resource=False):

    # macOS has a separate 'Resources' location used for data files
    file_list = include_resources if resource and sys.platform == "darwin" else include_files
    file_list.append((file_path, output_path))


def process_files(folder_path, callback, callback_data=None, starts_with=None, ends_with=None, recursive=False):

    for full_path in glob.glob(os.path.join(folder_path, '**'), recursive=recursive):
        short_path = os.path.relpath(full_path, folder_path)

        if starts_with and not short_path.startswith(starts_with):
            continue

        if ends_with and not short_path.endswith(ends_with):
            continue

        callback(full_path, short_path, callback_data)


def _add_files_callback(full_path, short_path, callback_data):

    output_path, resource = callback_data
    add_file(full_path, os.path.join(output_path, short_path), resource=resource)


def add_files(folder_path, output_path, starts_with=None, ends_with=None, recursive=False, resource=False):

    process_files(
        folder_path, _add_files_callback, callback_data=(output_path, resource),
        starts_with=starts_with, ends_with=ends_with, recursive=recursive
    )


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

    add_file(file_path=temp_loaders_file, output_path="lib/pixbuf-loaders.cache")
    add_files(
        folder_path=os.path.join(SYS_BASE, "lib/gdk-pixbuf-2.0/2.10.0/loaders"), output_path="lib",
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
        "GModule-",
        "freetype2-"
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
    folder_path = os.path.join(SYS_BASE, "lib/girepository-1.0")

    if sys.platform == "darwin":
        # Remove absolute paths added by Homebrew (macOS)
        process_files(
            folder_path=os.path.join(SYS_BASE, "share/gir-1.0"),
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
        add_file(file_path=os.path.join(LIB_FOLDER, "gdbus.exe"), output_path="lib/gdbus.exe")
        lib_output_path = "lib"

    elif sys.platform == "darwin":
        # .dylib files are in the same folder as the executable
        lib_output_path = ""

    # This also includes all dlls required by GTK
    add_files(
        folder_path=LIB_FOLDER, output_path=lib_output_path,
        starts_with="libgtk-%s" % GTK_VERSION, ends_with=LIB_EXTENSION
    )

    if USE_LIBADWAITA:
        add_files(
            folder_path=LIB_FOLDER, output_path=lib_output_path,
            starts_with="libadwaita-", ends_with=LIB_EXTENSION
        )

    # Schemas
    add_file(
        file_path=os.path.join(SYS_BASE, "share/glib-2.0/schemas/gschemas.compiled"),
        output_path="lib/schemas/gschemas.compiled"
    )

    # Fontconfig
    add_files(
        folder_path=os.path.join(SYS_BASE, "etc/fonts"), output_path="lib/fonts",
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
        folder_path=os.path.join(SYS_BASE, "share/icons"), output_path="share/icons",
        starts_with=required_icon_packs, ends_with=(".theme", ".svg"), recursive=True, resource=True
    )


def add_themes():

    # "Mac" is required for macOS-specific keybindings in GTK
    required_themes = (
        "Default",
        "Mac"
    )
    add_files(
        folder_path=os.path.join(SYS_BASE, "share/themes"), output_path="share/themes",
        starts_with=required_themes, ends_with=".css", recursive=True, resource=True
    )


def add_ssl_certs():
    ssl_paths = ssl.get_default_verify_paths()
    add_file(file_path=ssl_paths.openssl_cafile, output_path="lib/cert.pem")


def add_translations():

    from pynicotine.i18n import build_translations  # noqa: E402  # pylint: disable=import-error
    languages = tuple(build_translations())

    add_files(
        folder_path=os.path.join(PROJECT_PATH, "mo"), output_path="share/locale",
        starts_with=languages, ends_with="nicotine.mo", recursive=True, resource=True
    )
    add_files(
        folder_path=os.path.join(SYS_BASE, "share/locale"), output_path="share/locale",
        starts_with=languages, ends_with="gtk%s0.mo" % GTK_VERSION, recursive=True, resource=True
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
            ],
            include_resources=include_resources,
            codesign_identity='-',
            codesign_deep=True
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
