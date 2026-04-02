#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Nicotine+ Contributors
# SPDX-License-Identifier: GPL-3.0-or-later

import os
import subprocess
import sys

MIN_MACOS_VERSION = (11, 0)
CURRENT_PATH = os.path.dirname(os.path.abspath(__file__))

if sys.platform == "win32":
    EXECUTABLE_PATH = os.path.join(
        CURRENT_PATH, "build", "package", "Nicotine+", "Nicotine+-debug.exe"
    )
elif sys.platform == "darwin":
    EXECUTABLE_PATH = os.path.join(
        CURRENT_PATH, "build", "dist", "Nicotine+.app", "Contents", "MacOS", "Nicotine+-debug"
    )
else:
    EXECUTABLE_PATH = None


def verify_min_macos_version():
    """Verify minimum supported macOS version."""

    if sys.platform != "darwin":
        return

    output = subprocess.check_output(["vtool", "-show-build", EXECUTABLE_PATH], encoding="utf-8")
    min_version = next(line.split()[1] for line in output.splitlines() if "minos" in line)

    if tuple(int(x) for x in min_version.split(".")) <= MIN_MACOS_VERSION:
        print(f"Minimum supported macOS version is {min_version}")
        return

    expected_version = ".".join(str(x) for x in MIN_MACOS_VERSION)
    print(
        f"Detected minimum supported macOS version of {min_version}. "
        f"Required version is <= {expected_version}."
    )
    sys.exit(1)


def testrun():
    """Verify the packaged application starts and keeps running."""

    command = [EXECUTABLE_PATH, "--ci-mode"]

    with subprocess.Popen(command) as process:
        try:
            process.wait(timeout=5)

        except subprocess.TimeoutExpired:
            # Success, still running
            process.terminate()
            return

    sys.exit(1)


if __name__ == "__main__":
    verify_min_macos_version()
    testrun()
