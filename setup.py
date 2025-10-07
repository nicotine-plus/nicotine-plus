#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2023-2025 Nicotine+ Contributors
# SPDX-License-Identifier: GPL-3.0-or-later

import os
import subprocess

from setuptools import setup  # pylint: disable=import-error


def build_translations():
    """Builds .mo translation files in the 'locale' folder of the package."""

    base_path = os.path.dirname(os.path.realpath(__file__))
    locale_path = os.path.join(base_path, "pynicotine", "locale")

    with open(os.path.join(base_path, "po", "LINGUAS"), encoding="utf-8") as file_handle:
        languages = file_handle.read().splitlines()

    for language_code in languages:
        lang_folder_path = os.path.join(locale_path, language_code)
        lc_messages_folder_path = os.path.join(lang_folder_path, "LC_MESSAGES")
        po_file_path = os.path.join(base_path, "po", f"{language_code}.po")
        mo_file_path = os.path.join(lc_messages_folder_path, "nicotine.mo")

        if not os.path.exists(lc_messages_folder_path):
            os.makedirs(lc_messages_folder_path)

        for path in (locale_path, lang_folder_path, lc_messages_folder_path):
            with open(os.path.join(path, "__init__.py"), "wb") as file_handle:
                # Create empty file
                pass

        subprocess.check_call(["msgfmt", "--check", po_file_path, "-o", mo_file_path])

    # Merge translations into .desktop and appdata files
    with os.scandir(os.path.join(base_path, "data")) as entries:
        for entry in entries:
            if entry.name.endswith(".desktop.in"):
                subprocess.check_call(["msgfmt", "--desktop", f"--template={entry.path}", "-d", "po",
                                       "-o", entry.path[:-3]])

            elif entry.name.endswith(".appdata.xml.in"):
                subprocess.check_call(["msgfmt", "--xml", f"--template={entry.path}", "-d", "po",
                                       "-o", entry.path[:-3]])


if __name__ == "__main__":
    build_translations()
    setup()
