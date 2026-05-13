#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2021-2026 Nicotine+ Contributors
# SPDX-License-Identifier: GPL-3.0-or-later

import hashlib
import os

BASE_PATH = os.path.normpath(os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", ".."))
DIST_PATH = os.path.join(BASE_PATH, "dist")


def generate_sha256_hashes():
    """Generates SHA256 checksums for files placed in the dist folder."""

    for entry in os.scandir(DIST_PATH):
        if not entry.is_file():
            continue

        if entry.name.endswith(".sha256"):
            continue

        sha256_hash = hashlib.sha256()

        with open(entry.path, "rb") as file_handle:
            sha256_hash.update(file_handle.read())

        with open(entry.path + ".sha256", "w", encoding="utf-8") as file_handle:
            output = sha256_hash.hexdigest() + "  " + os.path.basename(entry.name)
            file_handle.write(output)


if __name__ == "__main__":
    generate_sha256_hashes()
