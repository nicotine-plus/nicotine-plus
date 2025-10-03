#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2020-2025 Nicotine+ Contributors
# SPDX-License-Identifier: GPL-3.0-or-later

import os
import subprocess
import sys


def install_brew():
    """Install dependencies from the main Homebrew repos."""

    # Workaround for https://github.com/Homebrew/homebrew-core/issues/139497
    os.environ["HOMEBREW_NO_INSTALL_FROM_API"] = "1"

    packages = ["gettext",
                "gobject-introspection",
                "gtk4",
                "libadwaita",
                "webp-pixbuf-loader"]

    subprocess.check_call(["brew", "install", "--quiet"] + packages)


def install_pypi():
    """Install dependencies from PyPi."""

    subprocess.check_call([
        sys.executable, "-m", "pip", "install",

        # For consistency, avoid including pre-built binaries from PyPI
        # in the application.
        "--no-binary", "cx_Freeze",
        "--no-binary", "PyGObject",
        "--no-binary", "pycairo",

        "-e", ".[packaging,tests]",
        "build",
        "setuptools",
        "wheel"
    ])


if __name__ == "__main__":
    install_brew()
    install_pypi()
