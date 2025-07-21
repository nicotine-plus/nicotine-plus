#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2020-2025 Nicotine+ Contributors
# SPDX-License-Identifier: GPL-3.0-or-later

import os
import subprocess


def install_pacman():
    """Install dependencies from the main MinGW repos."""

    arch = os.environ.get("ARCH", "x86_64")
    prefix = "mingw-w64-clang-aarch64" if arch == "arm64" else "mingw-w64-clang-x86_64"

    packages = [f"{prefix}-ca-certificates",
                f"{prefix}-gettext-tools",
                f"{prefix}-gtk4",
                f"{prefix}-libadwaita",
                f"{prefix}-python-build",
                f"{prefix}-python-cx-freeze",
                f"{prefix}-python-gobject",
                f"{prefix}-python-pycodestyle",
                f"{prefix}-python-pylint",
                f"{prefix}-python-setuptools",
                f"{prefix}-python-wheel",
                f"{prefix}-webp-pixbuf-loader"]

    subprocess.check_call(["pacman", "--noconfirm", "-S", "--needed"] + packages)


if __name__ == "__main__":
    install_pacman()
