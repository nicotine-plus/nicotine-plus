#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2021-2025 Nicotine+ Contributors
# SPDX-License-Identifier: GPL-3.0-or-later

import glob
import os
import subprocess


def update_translation_template():
    """Update .pot translation template."""

    pot_file_path = "po/nicotine.pot"

    # Desktop files
    files = sorted(glob.glob("data/**/*.desktop.in", recursive=True), key=os.path.abspath)
    subprocess.check_call(
        ["xgettext", "-k", "--keyword=GenericName", "--keyword=Comment", "--keyword=Keywords",
         "-o", pot_file_path] + files
     )

    # Python and GtkBuilder files
    files = (sorted(glob.glob("data/**/*.xml.in", recursive=True), key=os.path.abspath)
             + sorted(glob.glob("pynicotine/**/*.py", recursive=True), key=os.path.abspath)
             + sorted(glob.glob("pynicotine/**/*.ui", recursive=True), key=os.path.abspath))

    subprocess.check_call(["xgettext", "-j", "-o", pot_file_path] + files)

    # PLUGININFO files
    files = sorted(glob.glob("pynicotine/plugins/**/PLUGININFO", recursive=True))
    subprocess.check_call(["xgettext", "--join-existing", "-L", "Python", "-o", pot_file_path] + files)


if __name__ == "__main__":
    update_translation_template()
