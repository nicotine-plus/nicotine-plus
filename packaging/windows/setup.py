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
import re
import ssl
import sys
import tempfile

from pkgutil import walk_packages
from subprocess import check_call
from cx_Freeze import Executable, setup


if sys.platform == "win32":
    gui_base = "Win32GUI"
    sys_base = sys.prefix
    lib_folder = "bin"
    lib_extension = ".dll"

elif sys.platform == "darwin":
    gui_base = None
    sys_base = "/usr/local"
    lib_folder = "lib"
    lib_extension = (".dylib", ".so")

else:
    raise RuntimeError("Only Windows and macOS are supported")

include_files = []
plugin_packages = []
temp_folder = tempfile.mkdtemp()

gtk_version = os.environ.get("NICOTINE_GTK_VERSION") or '3'
use_libadwaita = gtk_version == '4' and os.environ.get("NICOTINE_LIBADWAITA") == '1'

pynicotine_path = os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", ".."))
sys.path.append(pynicotine_path)


def process_files(rel_path, starts_with, ends_with, callback, callback_data=None,
                  recursive=False, temporary=False):

    folder_path = temp_folder if temporary else os.path.join(sys_base, rel_path)

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
    temp_loaders_file = os.path.join(temp_folder, "loaders.cache")

    with open(temp_loaders_file, "w") as temp_file_handle, \
         open(os.path.join(sys_base, loaders_file), "r") as real_file_handle:
        data = real_file_handle.read()

        if sys.platform == "win32":
            data = data.replace("lib\\\\gdk-pixbuf-2.0\\\\2.10.0\\\\loaders", "lib")

        elif sys.platform == "darwin":
            data = data.replace(os.path.join(sys_base, "lib/gdk-pixbuf-2.0/2.10.0/loaders"), "@executable_path/lib")

        temp_file_handle.write(data)

    include_files.append((temp_loaders_file, loaders_file))
    add_files("lib/gdk-pixbuf-2.0/2.10.0/loaders", "libpixbufloader-", lib_extension, output_path="lib")


def _add_typelibs_callback(full_path, short_path, callback_data=None):

    temp_file_gir = os.path.join(temp_folder, short_path)
    temp_file_typelib = os.path.join(temp_folder, short_path.replace(".gir", ".typelib"))

    with open(temp_file_gir, "w") as temp_file_handle, \
         open(full_path, "r") as real_file_handle:
        data = real_file_handle.read()
        data = data.replace('shared-library="lib', 'shared-library="@loader_path/lib')
        temp_file_handle.write(data)

    check_call(["g-ir-compiler", "--output=%s" % temp_file_typelib, temp_file_gir])


def add_typelibs():

    required_typelibs = [
        "Gtk-%s" % gtk_version,
        "Gio-",
        "Gdk-%s" % gtk_version,
        "GLib-",
        "HarfBuzz-",
        "Pango-",
        "GObject-",
        "GdkPixbuf-",
        "cairo-",
        "GModule-"
    ]

    if gtk_version == '4':
        required_typelibs += [
            "Graphene-",
            "Gsk-",
            "PangoCairo-"
        ]
    else:
        required_typelibs += [
            "Atk-"
        ]

    if use_libadwaita:
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
        include_files.append((os.path.join(sys_base, lib_folder, "gdbus.exe"), "lib/gdbus.exe"))
        lib_output_path = "lib"

    elif sys.platform == "darwin":
        # .dylib files are in the same folder as the executable
        lib_output_path = ""

    # This also includes all dlls required by GTK
    add_files(lib_folder, "libgtk-%s" % gtk_version, lib_extension, output_path=lib_output_path)

    if use_libadwaita:
        add_files(lib_folder, "libadwaita-", lib_extension, output_path=lib_output_path)

    include_files.append((os.path.join(sys_base, "share/glib-2.0/schemas/gschemas.compiled"),
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

    from pynicotine.i18n import build_translations  # noqa: E402
    languages = build_translations()

    include_files.append((os.path.join(pynicotine_path, "mo"), "share/locale"))
    add_files("share/locale", tuple(languages), "gtk%s0.mo" % gtk_version, recursive=True)


def add_plugin_packages():

    import pynicotine.plugins  # noqa: E402

    for importer, name, ispkg in walk_packages(path=pynicotine.plugins.__path__, prefix="pynicotine.plugins."):
        if ispkg:
            plugin_packages.append(name)


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
from pynicotine.config import config  # noqa: E402

setup(
    name=config.application_name,
    author=config.author,
    version=re.sub(r".(dev|rc)(.*)", "", config.version),
    options={
        "build_exe": dict(
            packages=["gi"] + plugin_packages,
            excludes=["pygtkcompat", "tkinter"],
            include_files=include_files,
            zip_include_packages=["*"],
            zip_exclude_packages=["pynicotine"]
        ),
        "bdist_msi": dict(
            all_users=True,
            install_icon=os.path.join(pynicotine_path, "packaging/windows/nicotine.ico"),
            target_name="%s-%s.msi" % (config.application_name, config.version),
            upgrade_code="{8ffb9dbb-7106-41fc-9e8a-b2469aa1fe9f}"
        ),
        "bdist_mac": dict(
            iconfile=os.path.join(pynicotine_path, "packaging/macos/nicotine.icns"),
            bundle_name=config.application_name
        ),
        "bdist_dmg": dict(
            applications_shortcut=True
        )
    },
    executables=[
        Executable(
            script=os.path.join(pynicotine_path, "nicotine"),
            target_name=config.application_name,
            base=gui_base,
            icon=os.path.join(pynicotine_path, "packaging/windows/nicotine.ico"),
            shortcut_name=config.application_name,
            shortcut_dir="StartMenuFolder"
        )
    ],
)
