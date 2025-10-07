# SPDX-FileCopyrightText: 2022-2023 Nicotine+ Contributors
# SPDX-License-Identifier: GPL-3.0-or-later

from pynicotine.core import core
from pynicotine.gtkgui.popovers.transferspeeds import TransferSpeeds


class UploadSpeeds(TransferSpeeds):

    def __init__(self, window):
        super().__init__(window=window, transfer_type="upload")
        self.set_menu_button(window.upload_status_button)

    @staticmethod
    def update_transfer_limits():
        core.uploads.update_transfer_limits()
