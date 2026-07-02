# COPYRIGHT (C) 2026 Nicotine+ Contributors
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

import os

from unittest import TestCase

from pynicotine.utils import clean_file
from pynicotine.utils import safe_path_join


class UtilsTest(TestCase):

    def test_clean_file(self):
        """Verify that file path components are sanitized correctly."""

        self.assertEqual(
            clean_file("/basename-with-illegal-?chars?-?:><|*\"-extra-\\/"),
            "_basename-with-illegal-_chars_-_______-extra-__"
        )
        self.assertEqual(
            clean_file(
                "/basename-with-control-?chars?-\u0000\u0001\u0002\u0003\u0004\u0005\u0006\u0007\u0008"
                "\u0009\u000A\u000B\u000C\u000D\u000E\u000F\u0010\u0011\u0012\u0013\u0014\u0015\u0016"
                "\u0017\u0018\u0019\u001A\u001B\u001C\u001D\u001E\u001F"
            ),
            "_basename-with-control-_chars_-________________________________"
        )
        self.assertEqual(clean_file(" .path. "), ".path")
        self.assertEqual(clean_file(" . . . . "), "_________")
        self.assertEqual(clean_file("..."), "___")
        self.assertEqual(clean_file(".."), "__")
        self.assertEqual(clean_file(" .."), "___")
        self.assertEqual(clean_file(".. "), "___")
        self.assertEqual(clean_file(" .. "), "____")
        self.assertEqual(clean_file("."), "_")
        self.assertEqual(clean_file(" ."), "__")
        self.assertEqual(clean_file(". "), "__")
        self.assertEqual(clean_file(" . "), "___")
        self.assertEqual(clean_file(" "), "_")
        self.assertEqual(clean_file(""), "")
        self.assertEqual(clean_file("/"), "_")
        self.assertEqual(clean_file("/absolute"), "_absolute")
        self.assertEqual(clean_file("\\absolute"), "_absolute")

    def test_safe_path_join(self):
        """Verify that path components are joined and sanitized correctly."""

        base = os.path.abspath(".")

        self.assertEqual(
            safe_path_join(
                os.sep.join(["C:", "basepath", "folder"]),
                "..", ".", " .. ", "\\", "", "\\name", "", "D:relative", "", "C:\\absolute"
            ),
            os.path.abspath(
                os.sep.join(["C:", "basepath", "folder", "__", "_", "____", "_", "_name", "D_relative", "C__absolute"])
            )
        )
        self.assertEqual(
            safe_path_join(
                os.sep.join(["relative", "basepath", "folder"]),
                "..", ".", " .. ", "/", "", "/name", "", "relative", "", "/absolute"
            ),
            os.sep.join([
                base, "relative", "basepath", "folder", "__", "_", "____", "_", "_name", "relative", "_absolute"
            ])
        )
        self.assertEqual(
            safe_path_join(
                os.sep.join(["", "absolute", "basepath", "folder"]),
                "..", ".", " .. ", "/", "", "/name", "", "relative", "", "/absolute"
            ),
            os.path.abspath(
                os.sep.join([
                    "", "absolute", "basepath", "folder", "__", "_", "____", "_", "_name", "relative", "_absolute"
                ])
            )
        )
        self.assertEqual(
            safe_path_join(
                os.sep.join(["base", "path"]),
                "/basename-with-illegal-?chars?-?:><|*\"-extra-\\/", "//", "/absolute"
            ),
            os.sep.join([base, "base", "path", "_basename-with-illegal-_chars_-_______-extra-__", "__", "_absolute"])
        )
        self.assertEqual(
            safe_path_join(
                os.sep.join(["base", "path"]),
                "/basename-with-control-?chars?-\u0000\u0001\u0002\u0003\u0004\u0005\u0006\u0007\u0008"
                "\u0009\u000A\u000B\u000C\u000D\u000E\u000F\u0010\u0011\u0012\u0013\u0014\u0015\u0016"
                "\u0017\u0018\u0019\u001A\u001B\u001C\u001D\u001E\u001F",
                "/absolute"
            ),
            os.sep.join([
                base, "base", "path", "_basename-with-control-_chars_-________________________________", "_absolute"
            ])
        )
        self.assertEqual(
            safe_path_join(
                os.sep.join(["base", "path"]),
                " .path. ", " . . . . ", "...", "..", " ..", ".. ", " .. ", ".", " .", ". ", " . ", " ", "", "/",
                "/absolute"
            ),
            os.sep.join([
                base, "base", "path", ".path", "_________", "___", "__", "___", "___", "____", "_", "__", "__", "___",
                "_", "_", "_absolute"
            ])
        )
        self.assertEqual(
            safe_path_join(os.sep.join(["base", "path"]), "/absolute", "..", "."),
            os.sep.join([base, "base", "path", "_absolute", "__", "_"])
        )
        self.assertEqual(
            safe_path_join(os.sep.join(["base", "path"]), "\\absolute", "..", "."),
            os.sep.join([base, "base", "path", "_absolute", "__", "_"])
        )
