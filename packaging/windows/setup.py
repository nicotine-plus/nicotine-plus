#!/usr/bin/env python3
# COPYRIGHT (C) 2021 Nicotine+ Team
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
import sys

from pkgutil import walk_packages
from cx_Freeze import Executable, setup


if sys.platform == "win32":
    gui_base = "Win32GUI"
    sys_base = sys.prefix

elif sys.platform == "darwin":
    gui_base = None
    sys_base = "/usr/local"

else:
    raise RuntimeError("Only Windows and macOS is supported")

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


def add_plugin_packages():

    import pynicotine.plugins  # noqa: E402

    for importer, name, ispkg in walk_packages(path=pynicotine.plugins.__path__, prefix="pynicotine.plugins."):
        if ispkg:
            plugin_packages.append(name)


def add_translations():

    from pynicotine.i18n import generate_translations  # noqa: E402
    _mo_entries, languages = generate_translations()

    include_files.append((os.path.join(pynicotine_path, "mo"), "share/locale"))
    add_files_by_pattern("share/locale", tuple(languages), "gtk" + str(gtk_version) + "0.mo", recursive=True)


def add_ssl_certs():

    ssl_paths = ssl.get_default_verify_paths()
    include_files.append((ssl_paths.openssl_cafile, "etc/ssl/cert.pem"))

    if os.path.exists(ssl_paths.openssl_capath):
        include_files.append((ssl_paths.openssl_capath, "etc/ssl/certs"))


# Translations
add_translations()

# Plugins
add_plugin_packages()

# SSL support
add_ssl_certs()

# GTK-related files
required_dlls = (
    "libgtk-" + str(gtk_version),
    "libgdk-" + str(gtk_version),
    "libepoxy-",
    "libgdk_pixbuf-",
    "libpango-",
    "libpangocairo-",
    "libpangoft2-",
    "libpangowin32-",
    "libatk-",
    "libxml2-",
    "librsvg-"
)
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
required_icon_packs = (
    "Adwaita",
    "hicolor"
)
required_themes = (
    "Default",
    "Mac"
)

if sys.platform == "win32":
    add_files_by_pattern("bin", required_dlls, ".dll", output_path="")

elif sys.platform == "darwin":
    add_files_by_pattern("lib", required_dlls, ".dylib", output_path="")

add_files_by_pattern("lib/girepository-1.0", required_typelibs, ".typelib")
include_files.append((os.path.join(sys_base, "lib/gdk-pixbuf-2.0"), "lib/gdk-pixbuf-2.0"))
add_files_by_pattern("share/glib-2.0/schemas", "gschemas", ".compiled")
add_files_by_pattern("share/icons", required_icon_packs, (".theme", ".svg"), recursive=True)
add_files_by_pattern("share/themes", required_themes, ".css", recursive=True)

# Setup
from pynicotine.config import config  # noqa: E402

setup(
    name="Nicotine+",
    author="Nicotine+ Team",
    version=config.version.replace("dev", "").replace("rc", ""),
    options={
        "build_exe": dict(
            packages=["gi"] + plugin_packages,
            excludes=["pygtkcompat", "tkinter"],
            include_files=include_files,
        ),
        "bdist_msi": dict(
            all_users=True,
            install_icon=os.path.join(pynicotine_path, "packaging/windows/nicotine.ico"),
            target_name="Nicotine+-%s.msi" % config.version,
            upgrade_code="{8ffb9dbb-7106-41fc-9e8a-b2469aa1fe9f}"
        ),
        "bdist_mac": dict(
            iconfile=os.path.join(pynicotine_path, "packaging/macos/nicotine.icns"),
            bundle_name="Nicotine+"
        ),
        "bdist_dmg": dict(
            applications_shortcut=True
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
