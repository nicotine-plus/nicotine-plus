# COPYRIGHT (C) 2022 Nicotine+ Team
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
import unittest

from collections import deque
from unittest.mock import Mock

from pynicotine.config import config
from pynicotine.transfers import Transfers, Transfer


class GetUploadCandidateTest(unittest.TestCase):

    def setUp(self):

        config.data_dir = os.path.dirname(os.path.realpath(__file__))
        config.filename = os.path.join(config.data_dir, "temp_config")

        config.load_config()

        self.transfers = Transfers(Mock(), config, deque(), Mock())
        self.transfers.privileged_users = {"puser1", "puser2"}

    def add_transfers(self, users, status):

        transfer_list = []

        for user in users:
            filename = "%s/%i" % (user, len(self.transfers.uploads))
            transfer = Transfer(user=user, path=filename, status=status)

            transfer_list.append(transfer)
            self.transfers.append_upload(user, filename, transfer)

        return transfer_list

    def set_finished(self, transfer):

        transfer.status = "Finished"
        self.transfers.update_user_counter(transfer.user)
        self.transfers.uploads.remove(transfer)

    def consume_transfers(self, queued, in_progress, clear_first=False):
        """Call self.transfers.get_upload_candidate until no uploads are left.

        Transfers should be added to self.transfers in the desired starting
        states already.

        One in progress upload will be removed each time get_upload_candidate
        is called.

        `queued` and `in_progress` should contain the transfers in those states.

        `clear_first` indicates whether the upload candidate should be
        generated after the in progress upload is marked finished or before.

        All candidates received are returned in a list.
        """

        candidates = []
        none_count = 0  # prevent infinite loop in case of bug or bad test setup
        num_allowed_nones = 2

        while len(self.transfers.uploads) > 0 and none_count < num_allowed_nones:

            # "finish" one in progress transfer, if any
            if clear_first and in_progress:
                self.set_finished(in_progress.pop(0))

            candidate = self.transfers.get_upload_candidate()

            if not clear_first and in_progress:
                self.set_finished(in_progress.pop(0))

            if not candidate:
                none_count += 1
                print("none_count: %i" % none_count)

                if queued:
                    print("Found no transfer candidates out of %i queued uploads" % len(queued))

                candidates.append(None)
                continue

            none_count = 0
            print("Transfer candidate: %s" % candidate.user)

            candidates.append(candidate)
            queued.remove(candidate)
            in_progress.append(candidate)

            candidate.status = "Getting status"

        return candidates

    def base_test(self, queued, in_progress, expected, round_robin=False, clear_first=False):

        config.sections["transfers"]["fifoqueue"] = not round_robin

        queued_transfers = self.add_transfers(queued, status="Queued")
        in_progress_transfers = self.add_transfers(in_progress, status="Getting status")

        candidates = self.consume_transfers(queued_transfers, in_progress_transfers, clear_first=clear_first)
        users = [transfer.user if transfer else None for transfer in candidates]

        # `expected` should contain `None` in cases where there aren't
        # expected to be any queued users without existing in progress uploads
        self.assertEqual(users, expected)

    def test_round_robin_basic(self):

        self.base_test(
            queued=[
                "user1",
                "user1",
                "user2",
                "user2",
                "user3",
                "user3"
            ],
            in_progress=[],
            expected=[
                "user1",
                "user2",
                "user3",
                "user1",
                "user2",
                "user3",
                None
            ],
            round_robin=True
        )

    def test_round_robin_no_contention(self):

        self.base_test(
            queued=[
                "user1",
                "user1",
                "user2",
                "user2",
                "user3",
                "user3"
            ],
            in_progress=[],
            expected=[
                "user1",
                "user2",
                "user3",
                "user1",
                "user2",
                "user3",
                None
            ],
            round_robin=True,
            clear_first=True
        )

    def test_round_robin_one_user(self):

        self.base_test(
            queued=[
                "user1",
                "user1"
            ],
            in_progress=[],
            expected=[
                "user1",
                None,
                "user1",
                None
            ],
            round_robin=True
        )

    def test_round_robin_returning_user(self):

        self.base_test(
            queued=[
                "user1",
                "user1",
                "user2",
                "user2",
                "user2",
                "user3",
                "user3",
                "user3",
                "user1",
                "user1"
            ],
            in_progress=[],
            expected=[
                "user1",
                "user2",
                "user3",
                "user1",
                "user2",
                "user3",
                "user1",
                "user2",
                "user3",
                "user1",
                None
            ],
            round_robin=True
        )

    def test_round_robin_in_progress(self):

        self.base_test(
            queued=[
                "user1",
                "user1",
                "user2",
                "user2"
            ],
            in_progress=[
                "user1"
            ],
            expected=[
                "user2",
                "user1",
                "user2",
                "user1",
                None
            ],
            round_robin=True
        )

    def test_round_robin_privileged(self):

        self.base_test(
            queued=[
                "user1",
                "user2",
                "puser1",
                "puser1"
            ],
            in_progress=[],
            expected=[
                "puser1",
                None,
                "puser1",
                "user1",
                "user2",
                None
            ],
            round_robin=True
        )

    def test_fifo_basic(self):

        self.base_test(
            queued=[
                "user1",
                "user1",
                "user2",
                "user2",
                "user3",
                "user3"
            ],
            in_progress=[],
            expected=[
                "user1",
                "user2",
                "user1",
                "user2",
                "user3",
                None,
                "user3",
                None
            ]
        )

    def test_fifo_robin_no_contention(self):

        self.base_test(
            queued=[
                "user1",
                "user1",
                "user2",
                "user2",
                "user3",
                "user3"
            ],
            in_progress=[],
            expected=[
                "user1",
                "user1",
                "user2",
                "user2",
                "user3",
                "user3",
                None
            ],
            clear_first=True
        )

    def test_fifo_one_user(self):

        self.base_test(
            queued=[
                "user1",
                "user1"
            ],
            in_progress=[],
            expected=[
                "user1",
                None,
                "user1",
                None
            ]
        )

    def test_fifo_returning_user(self):

        self.base_test(
            queued=[
                "user1",
                "user1",
                "user2",
                "user2",
                "user2",
                "user3",
                "user3",
                "user3",
                "user1",
                "user1"
            ],
            in_progress=[],
            expected=[
                "user1",
                "user2",
                "user1",
                "user2",
                "user3",
                "user2",
                "user3",
                "user1",
                "user3",
                "user1",
                None
            ]
        )

    def test_fifo_in_progress(self):

        self.base_test(
            queued=[
                "user1",
                "user1",
                "user2",
                "user2"
            ],
            in_progress=[
                "user1"
            ],
            expected=[
                "user2",
                "user1",
                "user2",
                "user1",
                None
            ]
        )

    def test_fifo_privileged(self):

        self.base_test(
            queued=[
                "user1",
                "user2",
                "puser1",
                "puser1"
            ],
            in_progress=[],
            expected=[
                "puser1",
                None,
                "puser1",
                "user1",
                "user2",
                None
            ]
        )
