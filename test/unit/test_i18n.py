# COPYRIGHT (C) 2021-2022 Nicotine+ Contributors
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

import glob
import os

from unittest import TestCase

from pynicotine.i18n import LANGUAGES
from pynicotine.i18n import LOCALE_PATH
from pynicotine.i18n import build_translations


class I18nTest(TestCase):

    def test_build_translations(self):

        build_translations()
        mo_file_paths = glob.glob(os.path.join(LOCALE_PATH, "**", "*.mo"), recursive=True)

        for language_code, _language_name in LANGUAGES:
            if language_code == "en":
                # English is the default language
                continue

            self.assertIn(os.path.join(LOCALE_PATH, language_code, "LC_MESSAGES", "nicotine.mo"), mo_file_paths)
