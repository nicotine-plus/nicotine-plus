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

import unittest

from pynicotine.i18n import build_translations
from pynicotine.i18n import get_translation_paths

LANGUAGES = ("ca", "cs", "da", "de", "eo", "es_CL", "es_ES", "eu", "fi", "fr", "hu", "it", "lt", "lv", "nb_NO", "nl",
             "pl", "pt_BR", "ru", "sk", "sv", "tr", "uk", "zh_Hans")


class I18nTest(unittest.TestCase):

    def test_build_translations(self):

        languages = build_translations()
        mo_files = get_translation_paths()

        for lang in LANGUAGES:
            self.assertIn(lang, languages)
            self.assertIn(
                ("share/locale/" + lang + "/LC_MESSAGES", ["mo/" + lang + "/LC_MESSAGES/nicotine.mo"]),
                mo_files)
