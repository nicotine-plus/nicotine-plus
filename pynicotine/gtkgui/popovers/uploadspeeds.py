# COPYRIGHT (C) 2022-2023 Nicotine+ Contributors
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

from pynicotine.core import core
from pynicotine.gtkgui.popovers.transferspeeds import TransferSpeeds


class UploadSpeeds(TransferSpeeds):

    def __init__(self, window):
        super().__init__(window=window, transfer_type="upload")
        self.set_menu_button(window.upload_status_button)

    @staticmethod
    def update_transfer_limits():
        core.uploads.update_transfer_limits()
