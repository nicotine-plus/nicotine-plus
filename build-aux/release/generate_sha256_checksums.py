#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2021-2025 Nicotine+ Contributors
# SPDX-License-Identifier: GPL-3.0-or-later

import hashlib
import os


def generate_sha256_hashes():
    """Generates SHA256 checksums for files placed in the same folder as
    this script."""

    current_folder_path = os.path.dirname(os.path.realpath(__file__))
    current_script_name = os.path.basename(os.path.realpath(__file__))

    for entry in os.scandir(current_folder_path):
        if not entry.is_file():
            continue

        if entry.name == current_script_name:
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
