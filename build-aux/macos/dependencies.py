#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2020-2025 Nicotine+ Contributors
# SPDX-License-Identifier: GPL-3.0-or-later

import subprocess
import sys


def install_brew():
    """Install dependencies from the main Homebrew repos."""

    packages = ["gettext",
                "gobject-introspection",
                "gtk4",
                "libadwaita",
                "librsvg",
                # GStreamer multimedia support for preview functionality
                "gstreamer",
                "gst-plugins-base",
                "gst-plugins-good",
                "gst-plugins-ugly",
                "gst-plugins-bad",
                "gst-libav"]

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
