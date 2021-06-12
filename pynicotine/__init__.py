# COPYRIGHT (C) 2021 Nicotine+ Team
#
# GNU GENERAL PUBLIC LICENSE
#    Version 3, 29 June 2007
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import importlib.util
import sys

from pynicotine.i18n import apply_translation
from pynicotine.utils import rename_process


def check_core_dependencies():

    # Require Python >= 3.6
    try:
        assert sys.version_info[:2] >= (3, 6), '.'.join(
            map(str, sys.version_info[:3])
        )

    except AssertionError as e:
        return _("""You are using an unsupported version of Python (%(old_version)s).
You should install Python %(min_version)s or newer.""") % {
            "old_version": e,
            "min_version": "3.6"
        }

    # Require gdbm or semidbm, for faster loading of shelves
    if not importlib.util.find_spec("_gdbm") and \
            not importlib.util.find_spec("semidbm"):
        return _("Cannot find %(option1)s or %(option2)s, please install either one.") % {
            "option1": "gdbm",
            "option2": "semidbm"
        }

    return None


rename_process(b'nicotine')
apply_translation()

error = check_core_dependencies()

if error:
    print(error)
    sys.exit(1)
