"""
`__builtins__.pyi` informs Pyright-based type checkers of additional builtins.
See other scripts in `pynicotine/` for uses of `_` & `ngettext`.
"""

# SPDX-FileCopyrightText: 2026 Nicotine+ Contributors
# SPDX-License-Identifier: GPL-3.0-or-later

import gettext

_ = gettext.gettext
ngettext = gettext.ngettext
