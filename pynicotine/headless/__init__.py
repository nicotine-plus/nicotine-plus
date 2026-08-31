# SPDX-FileCopyrightText: 2022-2023 Nicotine+ Contributors
# SPDX-License-Identifier: GPL-3.0-or-later


def run(isolated_mode=False):
    """Run application in headless (no GUI) mode."""

    from pynicotine.headless.application import Application
    return Application(isolated_mode).run()
