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

import unittest

from pynicotine.i18n import generate_translations

LANGUAGES = ("cs", "da", "de", "es_CL", "es_ES", "eu", "fi", "fr", "hu",
             "it", "lt", "nb_NO", "nl", "pl", "pt_BR", "sk", "sv", "tr")


class I18nTest(unittest.TestCase):

    @staticmethod
    def test_generate_translations():

        mo_files, languages = generate_translations()

        for lang in LANGUAGES:
            assert lang in languages
            assert ("share/locale/" + lang + "/LC_MESSAGES", ["mo/" + lang + "/LC_MESSAGES/nicotine.mo"]) in mo_files
