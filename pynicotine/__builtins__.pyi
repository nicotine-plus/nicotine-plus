# SPDX-FileCopyrightText: 2026 Nicotine+ Contributors
# SPDX-License-Identifier: GPL-3.0-or-later

"""This stub informs Pyright-based type checkers of additional builtins. See the
modules in pynicotine for uses of _() and ngettext() translation functions."""

import gettext

_ = gettext.gettext
ngettext = gettext.ngettext
