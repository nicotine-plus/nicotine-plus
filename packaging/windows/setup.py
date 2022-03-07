#!/usr/bin/env python3
# COPYRIGHT (C) 2021-2022 Nicotine+ Team
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
from cx_Freeze import Executable, setup


if sys.platform == "win32":
    gui_base = "Win32GUI"
    sys_base = sys.prefix

else:
    raise RuntimeError("Only Windows is supported")

include_files = []
plugin_packages = []

gtk_version = os.environ.get("NICOTINE_GTK_VERSION") or 3
pynicotine_path = os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", ".."))
sys.path.append(pynicotine_path)


def add_files_by_pattern(rel_path, starts_with, ends_with, output_path=None, recursive=False):

    for full_path in glob.glob(os.path.join(sys_base, rel_path, '**'), recursive=recursive):
        short_path = os.path.relpath(full_path, os.path.join(sys_base, rel_path))

        if not short_path.startswith(starts_with):
            continue

        if not short_path.endswith(ends_with):
            continue

        if output_path is None:
            output_path = rel_path

        include_files.append((full_path, os.path.join(output_path, short_path)))


def add_gtk():

    # This also includes all dlls required by GTK
    add_files_by_pattern("bin", "libgtk-" + str(gtk_version), ".dll", output_path="lib")
    include_files.append((os.path.join(sys_base, "share/glib-2.0/schemas/gschemas.compiled"),
                         "share/glib-2.0/schemas/gschemas.compiled"))

    # gdbus required for single-instance application
    include_files.append((os.path.join(sys_base, "bin/gdbus.exe"), "lib/gdbus.exe"))

    # Pixbuf loaders
    temp_dir = tempfile.mkdtemp()
    loaders_file = "lib/gdk-pixbuf-2.0/2.10.0/loaders.cache"
    temp_loaders_file = os.path.join(temp_dir, "loaders.cache")

    with open(temp_loaders_file, "w") as file_handle:
        data = open(os.path.join(sys_base, loaders_file)).read()
        data = data.replace("lib\\\\gdk-pixbuf-2.0\\\\2.10.0\\\\loaders\\\\", "lib\\\\")
        file_handle.write(data)

    include_files.append((temp_loaders_file, loaders_file))
    add_files_by_pattern("lib/gdk-pixbuf-2.0/2.10.0/loaders", "libpixbufloader-", ".dll", output_path="lib")

    # Typelibs
    required_typelibs = (
        "Gtk-" + str(gtk_version),
        "Gio-",
        "Gdk-" + str(gtk_version),
        "GLib-",
        "Atk-",
        "HarfBuzz-",
        "Pango-",
        "GObject-",
        "GdkPixbuf-",
        "cairo-",
        "GModule-"
    )
    add_files_by_pattern("lib/girepository-1.0", required_typelibs, ".typelib")


def add_icon_packs():

    required_icon_packs = (
        "Adwaita",
        "hicolor"
    )
    add_files_by_pattern("share/icons", required_icon_packs, (".theme", ".svg"), recursive=True)


def add_themes():

    # "Mac" is required for macOS-specific keybindings in GTK
    required_themes = (
        "Default",
        "Mac"
    )
    add_files_by_pattern("share/themes", required_themes, ".css", recursive=True)


def add_ssl_certs():
    ssl_paths = ssl.get_default_verify_paths()
    include_files.append((ssl_paths.openssl_cafile, "share/ssl/cert.pem"))


def add_translations():

    from pynicotine.i18n import build_translations  # noqa: E402
    languages = build_translations()

    include_files.append((os.path.join(pynicotine_path, "mo"), "share/locale"))
    add_files_by_pattern("share/locale", tuple(languages), "gtk" + str(gtk_version) + "0.mo", recursive=True)


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
    name="Nicotine+",
    author="Nicotine+ Team",
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
            target_name="Nicotine+-%s.msi" % config.version,
            upgrade_code="{8ffb9dbb-7106-41fc-9e8a-b2469aa1fe9f}"
        )
    },
    executables=[
        Executable(
            script=os.path.join(pynicotine_path, "nicotine"),
            target_name="Nicotine+",
            base=gui_base,
            icon=os.path.join(pynicotine_path, "packaging/windows/nicotine.ico"),
            shortcut_name="Nicotine+",
            shortcut_dir="StartMenuFolder"
        )
    ],
)
