# SPDX-FileCopyrightText: 2026 Nicotine+ Contributors
# SPDX-License-Identifier: GPL-3.0-or-later

import os

from unittest import TestCase

from pynicotine.utils import clean_file
from pynicotine.utils import clean_path


class UtilsTest(TestCase):

    def test_clean_file(self):
        """Verify that file basenames are sanitized correctly."""

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
        self.assertEqual(
            clean_file(". . . ."),
            "_"
        )

    def test_clean_path(self):
        """Verify that file paths are sanitized correctly."""

        self.assertEqual(
            clean_path(os.sep.join([":path", "with", "forbidden", "?chars?", "?:><|*\""])),
            os.sep.join(["_path", "with", "forbidden", "_chars_", "_______"])
        )
        self.assertEqual(
            clean_path(os.sep.join([
                ":path", "with", "control", "?chars?", "\u0000\u0001\u0002\u0003\u0004\u0005\u0006\u0007\u0008"
                "\u0009\u000A\u000B\u000C\u000D\u000E\u000F\u0010\u0011\u0012\u0013\u0014\u0015\u0016"
                "\u0017\u0018\u0019\u001A\u001B\u001C\u001D\u001E\u001F"
            ])),
            os.sep.join(["_path", "with", "control", "_chars_", "________________________________"])
        )
        self.assertEqual(
            clean_path(os.sep.join(["C:", ":winpath", "with", "forbidden", "?chars?", "?:><|*\""])),
            os.sep.join(["C:", "_winpath", "with", "forbidden", "_chars_", "_______"])
        )
        self.assertEqual(
            clean_path(os.sep.join(["path", "with", "trailing", "period", "space. "])),
            os.sep.join(["path", "with", "trailing", "period", "space"])
        )
        self.assertEqual(
            clean_path(os.sep.join(["path", "with", "trailing", "period", "space", ". . . .   "])),
            os.sep.join(["path", "with", "trailing", "period", "space", "_"])
        )
        self.assertEqual(
            clean_path(
                os.sep.join(["", "..", "normalized", "", "", "..", ".", "path", ".", "..", ""]) + "/end///"
            ),
            os.sep.join(["", "__", "normalized", "__", "_", "path", "_", "__", "end"])
        )
