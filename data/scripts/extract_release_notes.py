#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Nicotine+ Contributors
# SPDX-License-Identifier: GPL-3.0-or-later

import os
import sys

BASE_PATH = os.path.normpath(os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", ".."))
NEWS_FILE_PATH = os.path.join(BASE_PATH, "NEWS.md")


def extract_release_notes():
    """Extracts release notes for the specified version from NEWS.md."""

    if len(sys.argv) < 2:
        print("No version provided")
        sys.exit(1)

    output = bytearray()
    version = sys.argv[1]
    reading_notes = False

    with open(NEWS_FILE_PATH, "rb") as file_handle:
        for line in file_handle:
            if reading_notes:
                if line.startswith(b"## "):
                    break

                output += line
                continue

            if line.startswith(f"## Version {version} ".encode()):
                reading_notes = True

    print(output.decode().strip())


if __name__ == "__main__":
    extract_release_notes()
