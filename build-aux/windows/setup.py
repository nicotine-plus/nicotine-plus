#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2021-2025 Nicotine+ Contributors
# SPDX-License-Identifier: GPL-3.0-or-later

import glob
import os
import platform
import ssl
import subprocess
import sys
import tempfile

from cx_Freeze import Executable, setup     # pylint: disable=import-error
from cx_Freeze.hooks import _gi_ as gi      # pylint: disable=import-private-name

# pylint: disable=duplicate-code


class DummyHook:
    pass


# Disable cx_Freeze's gi hook, since it conflicts with our script
gi.Hook = DummyHook

if sys.platform == "win32":
    SYS_BASE_PATH = sys.prefix
    LIB_PATH = os.path.join(SYS_BASE_PATH, "bin")
    UNAVAILABLE_MODULES = [
        "fcntl", "grp", "nis", "ossaudiodev", "posix", "pwd", "readline", "resource", "spwd", "syslog", "termios"
    ]
    ICON_NAME = "icon.ico"

elif sys.platform == "darwin":
    SYS_BASE_PATH = "/opt/homebrew" if platform.machine() == "arm64" else "/usr/local"
    LIB_PATH = os.path.join(SYS_BASE_PATH, "lib")
    UNAVAILABLE_MODULES = ["msvcrt", "nt", "nturl2path", "ossaudiodev", "spwd", "winreg", "winsound"]
    ICON_NAME = "icon.icns"

else:
    raise RuntimeError("Only Windows and macOS are supported")

TEMP_PATH = tempfile.mkdtemp()
CURRENT_PATH = os.path.dirname(os.path.abspath(__file__))
BUILD_PATH = os.path.join(CURRENT_PATH, "build")
PROJECT_PATH = os.path.abspath(os.path.join(CURRENT_PATH, "..", ".."))
sys.path.insert(0, PROJECT_PATH)

import pynicotine  # noqa: E402  # pylint: disable=import-error,wrong-import-position

SCRIPT_NAME = "nicotine"
MODULE_NAME = "pynicotine"
MANIFEST_NAME = os.path.join(CURRENT_PATH, f"{SCRIPT_NAME}.manifest") if sys.platform == "win32" else None

# Include (almost) all standard library modules for plugins
EXCLUDED_MODULES = UNAVAILABLE_MODULES + [
    f"{MODULE_NAME}.plugins.examplars", f"{MODULE_NAME}.tests",
    "ctypes.test", "distutils", "ensurepip", "idlelib", "lib2to3", "msilib", "pip", "pydoc", "pydoc_data",
    "pygtkcompat", "tkinter", "turtle", "turtledemo", "unittest.test", "venv", "zoneinfo"
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

    pixbuf_loaders_path = os.path.join(SYS_BASE_PATH, "lib/gdk-pixbuf-2.0/2.10.0/loaders")
    loader_extension = "dll" if sys.platform == "win32" else "so"

    add_file(file_path=os.path.join(CURRENT_PATH, "pixbuf-loaders.cache"), output_path="lib/pixbuf-loaders.cache")

    for image_format in ("bmp", "gif", "svg", "webp"):
        basename = f"libpixbufloader-{image_format}"

        if image_format == "svg":
            if sys.platform == "win32":
                basename = basename.replace("lib", "")
            basename = basename.replace("-", "_")

        add_file(
            file_path=os.path.realpath(os.path.join(pixbuf_loaders_path, f"{basename}.{loader_extension}")),
            output_path=f"lib/libpixbufloader-{image_format}.{loader_extension}"
        )


def _add_typelibs_callback(full_path, short_path, _callback_data=None):

    from xml.etree import ElementTree

    ElementTree.register_namespace("", "http://www.gtk.org/introspection/core/1.0")
    ElementTree.register_namespace("c", "http://www.gtk.org/introspection/c/1.0")
    ElementTree.register_namespace("glib", "http://www.gtk.org/introspection/glib/1.0")

    temp_file_gir = os.path.join(TEMP_PATH, short_path)
    temp_file_typelib = os.path.join(TEMP_PATH, short_path.replace(".gir", ".typelib"))

    with open(temp_file_gir, "w", encoding="utf-8") as temp_file_handle, \
         open(full_path, "r", encoding="utf-8") as real_file_handle:
        xml = ElementTree.fromstring(real_file_handle.read())

        for namespace in xml.findall(".//{*}namespace[@shared-library]"):
            paths = []

            for path in namespace.attrib["shared-library"].split(","):
                updated_path = os.path.join("@loader_path", os.path.basename(path))
                paths.append(updated_path)

            namespace.attrib["shared-library"] = ",".join(paths)

        data = ElementTree.tostring(xml, encoding="unicode")
        temp_file_handle.write(data)

    subprocess.check_call(["g-ir-compiler", f"--output={temp_file_typelib}", temp_file_gir])


def add_typelibs():

    required_typelibs = [
        "Adw-",
        "Gtk-4",
        "Gio-",
        "Gdk-4",
        "GLib-",
        "Graphene-",
        "Gsk-",
        "HarfBuzz-",
        "Pango-",
        "PangoCairo-",
        "GObject-",
        "GdkPixbuf-",
        "cairo-",
        "GModule-",
        "freetype2-"
    ]

    if sys.platform == "win32":
        required_typelibs.append("GdkWin32-4")
        required_typelibs.append("win32-")

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

    # Libraries
    if sys.platform == "win32":
        add_file(
            file_path=os.path.join(LIB_PATH, "libgtk-4-1.dll"),
            output_path="lib/libgtk-4-1.dll"
        )
        add_file(
            file_path=os.path.join(LIB_PATH, "libadwaita-1-0.dll"),
            output_path="lib/libadwaita-1-0.dll"
        )
        # gdbus required for single-instance application (Windows)
        add_file(file_path=os.path.join(LIB_PATH, "gdbus.exe"), output_path="lib/gdbus.exe")

    elif sys.platform == "darwin":
        add_file(
            file_path=os.path.join(LIB_PATH, "libgtk-4.1.dylib"),
            output_path="lib/libgtk-4.1.dylib"
        )
        add_file(
            file_path=os.path.join(LIB_PATH, "libadwaita-1.0.dylib"),
            output_path="lib/libadwaita-1.0.dylib"
        )

    # Schemas
    add_file(
        file_path=os.path.join(SYS_BASE_PATH, "share/glib-2.0/schemas/gschemas.compiled"),
        output_path="lib/schemas/gschemas.compiled"
    )

    # Pixbuf loaders
    add_pixbuf_loaders()

    # Typelibs
    add_typelibs()


def add_ssl_certs():
    ssl_paths = ssl.get_default_verify_paths()
    add_file(file_path=ssl_paths.openssl_cafile, output_path="lib/cert.pem")


def add_translations():

    from setup import build_translations  # noqa: E402  # pylint: disable=import-self,no-name-in-module
    build_translations()

    add_files(
        folder_path=os.path.join(SYS_BASE_PATH, "share/locale"), output_path="share/locale",
        starts_with=tuple(i[0] for i in pynicotine.i18n.LANGUAGES), ends_with="gtk40.mo", recursive=True
    )


# GTK
add_gtk()

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
            "zip_exclude_packages": [MODULE_NAME],
            "optimize": 2
        },
        "bdist_msi": {
            "all_users": True,
            "launch_on_finish": True,
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
                ("NSHumanReadableCopyright", pynicotine.__copyright__),
                ("NSSupportsAutomaticGraphicsSwitching", True)  # Prefer integrated GPU
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
    data_files=[],
    packages=[],
    executables=[
        Executable(
            script=os.path.join(PROJECT_PATH, SCRIPT_NAME),
            base="gui",
            target_name=pynicotine.__application_name__,
            icon=os.path.join(CURRENT_PATH, ICON_NAME),
            manifest=MANIFEST_NAME,
            copyright=pynicotine.__copyright__,
            shortcut_name=pynicotine.__application_name__,
            shortcut_dir="ProgramMenuFolder"
        )
    ],
)
